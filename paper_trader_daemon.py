# =====================================================================
# V2 PAPER TRADER DAEMON: PUBLIC TESTBED (NO TELEGRAM, NO GSHEETS)
# =====================================================================
import os
import sys
import json
import logging
import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import numpy as np
import yfinance as yf

from strategy_engine import (
    DEFAULT_STAGE1_ETF_CONFIG,
    DEFAULT_STAGE2_STOCK_CONFIG,
    evaluate_market_metrics,
    get_top_conviction_candidates,
    validate_trade_execution,
    evaluate_trade_exits,
    extract_ticker_df
)
from ml_optimizer import (
    load_ai_trades,
    save_ai_trades,
    get_ai_rag_conviction_candidates
)

IST = ZoneInfo("Asia/Kolkata")
LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(LOCAL_DATA_DIR, exist_ok=True)

LOCAL_TRADES_CSV = os.path.join(LOCAL_DATA_DIR, "paper_trades.csv")
LOCAL_AUDIT_CSV = os.path.join(LOCAL_DATA_DIR, "execution_audit_log.csv")
LOG_FILE_PATH = os.path.join(LOCAL_DATA_DIR, "daemon_execution.log")

# Setup clean console and file logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
    ]
)
logger = logging.getLogger("PaperTraderDaemon_V2")

DEFAULT_PAPER_HEADERS = [
    "Trade_ID", "Username", "Ticker", "Asset_Class", "Trigger_Type", "Strategy_Preset",
    "Status", "Entry_Price", "Executed_Qty", "Stop_Loss", "Target",
    "Execution_Timestamp", "PnL_Rs", "PnL_Pct", "Invested_Value"
]

DEFAULT_AUDIT_HEADERS = [
    "Timestamp_IST", "Trigger_Source", "Preset", "Recommended_BUY",
    "Recommended_SELL", "Execution_Status", "Reason_Summary"
]

# =====================================================================
# LOCAL LEDGER PERSISTENCE
# =====================================================================
def load_trades():
    if os.path.exists(LOCAL_TRADES_CSV) and os.path.getsize(LOCAL_TRADES_CSV) > 0:
        try:
            return pd.read_csv(LOCAL_TRADES_CSV)
        except Exception:
            pass
    return pd.DataFrame(columns=DEFAULT_PAPER_HEADERS)

def save_trades(df):
    for c in DEFAULT_PAPER_HEADERS:
        if c not in df.columns:
            df[c] = ""
    df["Status"] = df["Status"].fillna("ACTIVE").astype(str)
    df.to_csv(LOCAL_TRADES_CSV, index=False)

def save_audit(entry_dict):
    existing = pd.DataFrame(columns=DEFAULT_AUDIT_HEADERS)
    if os.path.exists(LOCAL_AUDIT_CSV) and os.path.getsize(LOCAL_AUDIT_CSV) > 0:
        try:
            existing = pd.read_csv(LOCAL_AUDIT_CSV)
        except Exception:
            pass
    combined = pd.concat([existing, pd.DataFrame([entry_dict])], ignore_index=True).drop_duplicates()
    combined.to_csv(LOCAL_AUDIT_CSV, index=False)

# =====================================================================
# MARKET DATA FETCHER
# =====================================================================
def download_market_data(all_tickers):
    symbols = list(set(all_tickers)) + ["^CRSLDX", "^NSEI", "^INDIAVIX"]
    logger.info(f"Downloading historical market data for {len(symbols)} tickers...")
    try:
        raw_data = yf.download(
            tickers=symbols,
            period="1y",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False
        )
        logger.info("Market data successfully fetched.")
        return raw_data
    except Exception as e:
        logger.error(f"Market data download error: {e}")
        return pd.DataFrame()

# =====================================================================
# MAIN V2 DAEMON EXECUTION
# =====================================================================
def run_paper_trader_daemon(mode_override=None):
    now_ist = datetime.datetime.now(IST)
    now_str = now_ist.strftime("%Y-%m-%d %H:%M:%S")
    time_str = now_ist.strftime("%H:%M")

    if mode_override:
        mode = mode_override
    else:
        env_mode = os.getenv("MANUAL_MODE", "").strip()
        if env_mode:
            mode = env_mode
        elif "09:15" <= time_str <= "10:30":
            mode = "INTRADAY_ENTRY"
        elif "15:05" <= time_str <= "15:25":
            mode = "INTRADAY_SQUAREOFF"
        else:
            mode = "PAPER_TRADE_3PM"

    logger.info("==================================================")
    logger.info(f"STARTING V2 DAEMON EXECUTION: MODE = {mode} (IST: {now_str})")
    logger.info("==================================================")

    # 1. Fetch Universe & Market Data
    all_tickers = [x["ticker"] for x in (DEFAULT_STAGE1_ETF_CONFIG + DEFAULT_STAGE2_STOCK_CONFIG)]
    raw_data = download_market_data(all_tickers)

    if raw_data.empty:
        logger.error("Daemon aborting: Market data unavailable.")
        return

    # 2. Evaluate Indicators & Market Regime
    etfs_market_df, etf_regime = evaluate_market_metrics(raw_data, DEFAULT_STAGE1_ETF_CONFIG, is_stock_mode=False)
    stocks_market_df, stock_regime = evaluate_market_metrics(raw_data, DEFAULT_STAGE2_STOCK_CONFIG, is_stock_mode=True)
    regime_name = etf_regime.get("regime", "Normal")

    logger.info(f"[REGIME] Current Market Regime: {regime_name} | VIX: {etf_regime.get('vix', 15.0)}")

    # 3. Check and Process Inbuilt Exits First
    all_trades = load_trades()
    active_before = len(all_trades[all_trades["Status"] == "ACTIVE"]) if not all_trades.empty else 0

    force_squareoff = (mode == "INTRADAY_SQUAREOFF")
    updated_trades = evaluate_trade_exits(all_trades, raw_data, force_squareoff_intraday=force_squareoff)
    active_after = len(updated_trades[updated_trades["Status"] == "ACTIVE"]) if not updated_trades.empty else 0

    exited_count = active_before - active_after
    if exited_count > 0:
        save_trades(updated_trades)
        logger.info(f"[EXITS] Successfully processed {exited_count} exits/square-offs.")

    active_positions = updated_trades[updated_trades["Status"] == "ACTIVE"] if not updated_trades.empty else pd.DataFrame()
    active_ticker_set = set(active_positions["Ticker"].astype(str).str.replace(".NS", "").str.upper()) if not active_positions.empty else set()

    created_records = []

    # =================================================================
    # MODE 1: INTRADAY ENTRY (09:45 AM IST)
    # =================================================================
    if mode == "INTRADAY_ENTRY":
        logger.info("[MODE] Executing Intraday Entry (Top 3 Stocks + Top 3 ETFs)...")

        # Top 3 Stocks for Intraday
        stk_buy, _ = get_top_conviction_candidates(stocks_market_df, preset_name="Intraday", is_stock_mode=True, limit=3)
        for _, r in stk_buy.iterrows():
            sym = str(r["Ticker"]).replace(".NS", "").strip()
            cmp_val = float(r["CMP (₹)"])
            if sym in active_ticker_set or cmp_val <= 0:
                logger.info(f"[SKIP] [STOCK] {sym}: Already active in ledger or invalid CMP.")
                continue

            qty = max(1, int(15000 // cmp_val))
            can_trade, final_qty, _ = validate_trade_execution(sym, "BUY", "Intraday", qty, active_positions)
            if can_trade:
                trade_id = f"V2_INT_{int(datetime.datetime.now(IST).timestamp())}_{sym}"
                rec = {
                    "Trade_ID": trade_id, "Username": "V2_Daemon", "Ticker": sym,
                    "Asset_Class": "Stock", "Trigger_Type": "INTRADAY_BUY", "Strategy_Preset": "Intraday",
                    "Status": "ACTIVE", "Entry_Price": cmp_val, "Executed_Qty": final_qty,
                    "Stop_Loss": r["Stop_Loss"], "Target": r["Target"],
                    "Execution_Timestamp": now_str, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                    "Invested_Value": round(cmp_val * final_qty, 2)
                }
                created_records.append(rec)
                active_ticker_set.add(sym)
                logger.info(f"[STOCK] [INTRADAY] {sym}: BUY @ ₹{cmp_val:.2f} | Qty: {final_qty} | SL: ₹{r['Stop_Loss']:.2f} | Tgt: ₹{r['Target']:.2f}")

        # Top 3 ETFs for Intraday
        etf_buy, _ = get_top_conviction_candidates(etfs_market_df, preset_name="Intraday", is_stock_mode=False, limit=3)
        for _, r in etf_buy.iterrows():
            sym = str(r["Ticker"]).replace(".NS", "").strip()
            cmp_val = float(r["CMP (₹)"])
            if sym in active_ticker_set or cmp_val <= 0:
                logger.info(f"[SKIP] [ETF] {sym}: Already active in ledger or invalid CMP.")
                continue

            qty = max(1, int(15000 // cmp_val))
            can_trade, final_qty, _ = validate_trade_execution(sym, "BUY", "Intraday", qty, active_positions)
            if can_trade:
                trade_id = f"V2_INT_{int(datetime.datetime.now(IST).timestamp())}_{sym}"
                rec = {
                    "Trade_ID": trade_id, "Username": "V2_Daemon", "Ticker": sym,
                    "Asset_Class": "ETF", "Trigger_Type": "INTRADAY_BUY", "Strategy_Preset": "Intraday",
                    "Status": "ACTIVE", "Entry_Price": cmp_val, "Executed_Qty": final_qty,
                    "Stop_Loss": r["Stop_Loss"], "Target": r["Target"],
                    "Execution_Timestamp": now_str, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                    "Invested_Value": round(cmp_val * final_qty, 2)
                }
                created_records.append(rec)
                active_ticker_set.add(sym)
                logger.info(f"[ETF] [INTRADAY] {sym}: BUY @ ₹{cmp_val:.2f} | Qty: {final_qty} | SL: ₹{r['Stop_Loss']:.2f} | Tgt: ₹{r['Target']:.2f}")

    # =================================================================
    # MODE 2: 3 PM MULTI-PRESET & AI ACCUMULATION (03:00 PM IST)
    # =================================================================
    elif mode == "PAPER_TRADE_3PM":
        logger.info("[MODE] Executing 3 PM Accumulation Routine (Stocks, ETFs & AI/RAG)...")

        # 1. AI / RAG Top 3 Trades
        try:
            ai_stk_buy, _ = get_ai_rag_conviction_candidates(stocks_market_df, is_stock_mode=True, limit=3)
            for _, r in ai_stk_buy.iterrows():
                sym = str(r["Ticker"]).replace(".NS", "").strip()
                cmp_val = float(r["CMP (₹)"])
                if sym in active_ticker_set or cmp_val <= 0:
                    continue

                qty = max(1, int(15000 // cmp_val))
                trade_id = f"V2_AI_{int(datetime.datetime.now(IST).timestamp())}_{sym}"
                rec = {
                    "Trade_ID": trade_id, "Username": "V2_Daemon", "Ticker": sym,
                    "Asset_Class": "Stock", "Trigger_Type": "AI_RAG_CONFLUENCE_BUY", "Strategy_Preset": "AI / RAG",
                    "Status": "ACTIVE", "Entry_Price": cmp_val, "Executed_Qty": qty,
                    "Stop_Loss": r["Stop_Loss"], "Target": r["Target"],
                    "Execution_Timestamp": now_str, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                    "Invested_Value": round(cmp_val * qty, 2)
                }
                created_records.append(rec)
                active_ticker_set.add(sym)
                logger.info(f"[AI/RAG] [STOCK] {sym}: BUY @ ₹{cmp_val:.2f} | Conf: {r.get('AI_Confidence_Score', '85%')} | Qty: {qty}")
        except Exception as ex:
            logger.error(f"AI/RAG routine error: {ex}")

        # 2. Multi-Preset Routine: Default, Long-Term, Swing / Positional
        for p_name in ["Default", "Long-Term", "Swing / Positional"]:
            logger.info(f"[PRESET] Evaluating '{p_name}' for Top 3 ETFs and Top 3 Stocks...")

            # ETFs
            etf_buy, _ = get_top_conviction_candidates(etfs_market_df, preset_name=p_name, is_stock_mode=False, limit=3)
            for _, r in etf_buy.iterrows():
                sym = str(r["Ticker"]).replace(".NS", "").strip()
                cmp_val = float(r["CMP (₹)"])
                if sym in active_ticker_set or cmp_val <= 0:
                    continue

                qty = max(1, int(15000 // cmp_val))
                can_trade, final_qty, _ = validate_trade_execution(sym, "BUY", p_name, qty, active_positions)
                if can_trade:
                    trade_id = f"V2_TRADE_{int(datetime.datetime.now(IST).timestamp())}_{sym}"
                    rec = {
                        "Trade_ID": trade_id, "Username": "V2_Daemon", "Ticker": sym,
                        "Asset_Class": "ETF", "Trigger_Type": "AUTO_3PM_BUY", "Strategy_Preset": p_name,
                        "Status": "ACTIVE", "Entry_Price": cmp_val, "Executed_Qty": final_qty,
                        "Stop_Loss": r["Stop_Loss"], "Target": r["Target"],
                        "Execution_Timestamp": now_str, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                        "Invested_Value": round(cmp_val * final_qty, 2)
                    }
                    created_records.append(rec)
                    active_ticker_set.add(sym)
                    logger.info(f"[ETF] [{p_name}] {sym}: BUY @ ₹{cmp_val:.2f} | Qty: {final_qty} | SL: ₹{r['Stop_Loss']} | Tgt: ₹{r['Target']}")

            # Stocks
            stk_buy, _ = get_top_conviction_candidates(stocks_market_df, preset_name=p_name, is_stock_mode=True, limit=3)
            for _, r in stk_buy.iterrows():
                sym = str(r["Ticker"]).replace(".NS", "").strip()
                cmp_val = float(r["CMP (₹)"])
                if sym in active_ticker_set or cmp_val <= 0:
                    continue

                qty = max(1, int(15000 // cmp_val))
                can_trade, final_qty, _ = validate_trade_execution(sym, "BUY", p_name, qty, active_positions)
                if can_trade:
                    trade_id = f"V2_TRADE_{int(datetime.datetime.now(IST).timestamp())}_{sym}"
                    rec = {
                        "Trade_ID": trade_id, "Username": "V2_Daemon", "Ticker": sym,
                        "Asset_Class": "Stock", "Trigger_Type": "AUTO_3PM_BUY", "Strategy_Preset": p_name,
                        "Status": "ACTIVE", "Entry_Price": cmp_val, "Executed_Qty": final_qty,
                        "Stop_Loss": r["Stop_Loss"], "Target": r["Target"],
                        "Execution_Timestamp": now_str, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                        "Invested_Value": round(cmp_val * final_qty, 2)
                    }
                    created_records.append(rec)
                    active_ticker_set.add(sym)
                    logger.info(f"[STOCK] [{p_name}] {sym}: BUY @ ₹{cmp_val:.2f} | Qty: {final_qty} | SL: ₹{r['Stop_Loss']} | Tgt: ₹{r['Target']}")

    # 4. Save New Trades to Local CSV
    if created_records:
        new_trades_df = pd.DataFrame(created_records)
        combined_trades = pd.concat([updated_trades, new_trades_df], ignore_index=True) if not updated_trades.empty else new_trades_df
        save_trades(combined_trades)
        logger.info(f"[SUCCESS] Recorded {len(created_records)} new paper trades into {LOCAL_TRADES_CSV}.")

    # 5. Log Execution Audit
    buy_tickers = [r["Ticker"] for r in created_records if "BUY" in r.get("Trigger_Type", "")]
    audit_entry = {
        "Timestamp_IST": now_str,
        "Trigger_Source": f"V2_CRON_{mode}",
        "Preset": "Multi-Asset (Top 3 per Category)",
        "Recommended_BUY": ", ".join(buy_tickers) if buy_tickers else "None",
        "Recommended_SELL": "None",
        "Execution_Status": f"🟢 Executed ({len(created_records)} Orders)" if created_records else "⚪ Completed (No Orders)",
        "Reason_Summary": f"V2 Routine {mode} finished. New Orders: {len(created_records)}, Exits: {exited_count}."
    }
    save_audit(audit_entry)

    logger.info("==================================================")
    logger.info(f"V2 DAEMON COMPLETED AT {now_str}")
    logger.info("==================================================")

if __name__ == "__main__":
    mode_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_paper_trader_daemon(mode_override=mode_arg)
