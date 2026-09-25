# =====================================================================
# V2 ML OPTIMIZER & AI QUANT ADVISOR (PUBLIC TESTBED - NO GSHEETS)
# =====================================================================
import os
import json
import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger("MLOptimizer_V2")
IST = ZoneInfo("Asia/Kolkata")

LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(LOCAL_DATA_DIR, exist_ok=True)

LOCAL_TRADES_CSV = os.path.join(LOCAL_DATA_DIR, "paper_trades.csv")
LOCAL_AI_TRADES_CSV = os.path.join(LOCAL_DATA_DIR, "ai_paper_trades.csv")
LOCAL_SUGGESTIONS_CSV = os.path.join(LOCAL_DATA_DIR, "ai_strategy_suggestions.csv")
LOCAL_AI_LOG_CSV = os.path.join(LOCAL_DATA_DIR, "ai_execution_log.csv")
CONFIG_JSON_PATH = os.path.join(os.path.dirname(__file__), "runtime_config.json")

AI_PAPER_HEADERS = [
    "Trade_ID", "Username", "Ticker", "Asset_Class", "Trigger_Type", "Strategy_Preset",
    "Status", "Entry_Price", "Executed_Qty", "Stop_Loss", "Target",
    "Execution_Timestamp", "PnL_Rs", "PnL_Pct", "Invested_Value", "AI_Confidence_Score",
    "Market_Regime", "RSI_At_Entry", "Composite_Score_At_Entry"
]

AI_LOG_HEADERS = ["Timestamp_IST", "Evaluation_Status", "Reason_Summary", "Bought_Tickers", "Sold_Tickers"]

# =====================================================================
# RUNTIME CONFIGURATION ENGINE (PERSISTENT & ZERO-SECRET)
# =====================================================================
DEFAULT_RUNTIME_CONFIG = {
    "weights": {
        "Default": {"w_dma": 35, "w_rsi": 30, "w_low": 20, "w_exp": 15},
        "Long-Term": {"w_dma": 45, "w_rsi": 15, "w_low": 25, "w_exp": 15},
        "Swing / Positional": {"w_dma": 15, "w_rsi": 55, "w_low": 25, "w_exp": 5},
        "Intraday": {"w_dma": 5, "w_rsi": 65, "w_low": 5, "w_exp": 25},
        "AI / RAG": {"w_dma": 25, "w_rsi": 35, "w_low": 20, "w_exp": 20}
    },
    "risk_parameters": {
        "intraday_sl_multiplier": 1.0,
        "intraday_target_multiplier": 1.8,
        "swing_sl_multiplier": 1.5,
        "swing_target_multiplier": 3.0,
        "longterm_sl_multiplier": 2.5,
        "longterm_target_multiplier": 5.0,
        "trailing_stop_activation_pct": 3.0,
        "trailing_stop_lock_pct": 0.5
    },
    "last_optimized_timestamp": "None",
    "optimization_status": "V2 Public Testbed Active"
}

def load_runtime_config():
    if os.path.exists(CONFIG_JSON_PATH):
        try:
            with open(CONFIG_JSON_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    with open(CONFIG_JSON_PATH, "w") as f:
        json.dump(DEFAULT_RUNTIME_CONFIG, f, indent=4)
    return DEFAULT_RUNTIME_CONFIG

def save_runtime_config(config_dict):
    try:
        with open(CONFIG_JSON_PATH, "w") as f:
            json.dump(config_dict, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Failed to save runtime config: {e}")
        return False

# =====================================================================
# DATA PERSISTENCE (PURE LOCAL FILE-BASED - ZERO CLOUD AUTH NEEDED)
# =====================================================================
def load_ai_trades():
    if os.path.exists(LOCAL_AI_TRADES_CSV) and os.path.getsize(LOCAL_AI_TRADES_CSV) > 0:
        try:
            return pd.read_csv(LOCAL_AI_TRADES_CSV)
        except Exception:
            pass
    return pd.DataFrame(columns=AI_PAPER_HEADERS)

def save_ai_trades(df):
    for col in AI_PAPER_HEADERS:
        if col not in df.columns:
            df[col] = ""
    df["Status"] = df["Status"].fillna("ACTIVE").astype(str)
    df.to_csv(LOCAL_AI_TRADES_CSV, index=False)

def log_ai_execution(status, reason, bought_tickers="None", sold_tickers="None"):
    timestamp_str = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "Timestamp_IST": timestamp_str,
        "Evaluation_Status": status,
        "Reason_Summary": reason,
        "Bought_Tickers": str(bought_tickers),
        "Sold_Tickers": str(sold_tickers)
    }
    existing = pd.DataFrame(columns=AI_LOG_HEADERS)
    if os.path.exists(LOCAL_AI_LOG_CSV) and os.path.getsize(LOCAL_AI_LOG_CSV) > 0:
        try:
            existing = pd.read_csv(LOCAL_AI_LOG_CSV)
        except Exception:
            pass
    combined = pd.concat([existing, pd.DataFrame([entry])], ignore_index=True).drop_duplicates()
    combined.to_csv(LOCAL_AI_LOG_CSV, index=False)

# =====================================================================
# AI / RAG CONFLUENCE CANDIDATE SYNTHESIZER
# =====================================================================
def get_ai_rag_conviction_candidates(metrics_df, is_stock_mode=False, limit=3):
    """
    Synthesizes AI / RAG Top 3 BUY and Top 3 SELL candidates by fusing:
    - RSI Oversold/Overbought dynamics
    - Volume surge anomalies
    - Bollinger Band compression
    - MACD histogram momentum
    """
    if metrics_df is None or metrics_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    df = metrics_df.copy()

    vol_surge = pd.to_numeric(df.get("Volume Surge Ratio", 1.0), errors="coerce").fillna(1.0)
    rsi_val = pd.to_numeric(df.get("RSI (14D)", 50.0), errors="coerce").fillna(50.0)
    bb_b = pd.to_numeric(df.get("Bollinger %B", 0.5), errors="coerce").fillna(0.5)
    macd_hist = pd.to_numeric(df.get("MACD Hist", 0.0), errors="coerce").fillna(0.0)

    # Bullish Confluence Score
    bull_score = (
        (100.0 - rsi_val) * 0.35 +
        (1.0 - bb_b.clip(0, 1)) * 100.0 * 0.25 +
        (vol_surge.clip(0.5, 3.0) / 3.0) * 100.0 * 0.25 +
        np.where(macd_hist > 0, 15.0, 0.0)
    ).clip(15.0, 98.0)

    # Bearish Confluence Score
    bear_score = (
        rsi_val * 0.35 +
        bb_b.clip(0, 1) * 100.0 * 0.25 +
        np.where(df.get("Dist 200DMA %", 0) > 15.0, 20.0, 0.0) +
        np.where(macd_hist < 0, 20.0, 0.0)
    ).clip(15.0, 98.0)

    df["AI_Buy_Confidence"] = round(bull_score, 1)
    df["AI_Sell_Confidence"] = round(bear_score, 1)

    buy_list = []
    sell_list = []

    for _, r in df.iterrows():
        sym = r.get("Ticker", r.get("symbol", ""))
        cmp_val = float(r.get("CMP (₹)", 0.0))
        atr_val = float(r.get("14D ATR (₹)", cmp_val * 0.02))
        if cmp_val <= 0:
            continue

        buy_list.append({
            "Ticker": sym, "symbol": sym, "Name": r.get("Name", sym), "Category": r.get("Category", "AI/RAG"),
            "Signal": "BUY", "CMP (₹)": cmp_val, "RSI (14D)": float(r.get("RSI (14D)", 50.0)),
            "Composite Score": round(100.0 - float(r["AI_Buy_Confidence"]), 1),
            "AI_Confidence_Pct": float(r["AI_Buy_Confidence"]),
            "AI_Confidence_Score": f"{float(r['AI_Buy_Confidence']):.1f}%",
            "Stop_Loss": round(max(0.01, cmp_val - (1.6 * atr_val)), 2),
            "Target": round(cmp_val + (3.2 * atr_val), 2),
            "Preset": "AI / RAG", "Asset_Class": "Stock" if is_stock_mode else "ETF"
        })

        sell_list.append({
            "Ticker": sym, "symbol": sym, "Name": r.get("Name", sym), "Category": r.get("Category", "AI/RAG"),
            "Signal": "SELL", "CMP (₹)": cmp_val, "RSI (14D)": float(r.get("RSI (14D)", 50.0)),
            "Composite Score": round(float(r["AI_Sell_Confidence"]), 1),
            "AI_Confidence_Pct": float(r["AI_Sell_Confidence"]),
            "AI_Confidence_Score": f"{float(r['AI_Sell_Confidence']):.1f}%",
            "Stop_Loss": round(cmp_val + (1.6 * atr_val), 2),
            "Target": round(max(0.01, cmp_val - (3.2 * atr_val)), 2),
            "Preset": "AI / RAG", "Asset_Class": "Stock" if is_stock_mode else "ETF"
        })

    b_df = pd.DataFrame(buy_list)
    s_df = pd.DataFrame(sell_list)

    top_buy = b_df.sort_values(by="AI_Confidence_Pct", ascending=False).head(limit).reset_index(drop=True) if not b_df.empty else pd.DataFrame()
    top_sell = s_df.sort_values(by="AI_Confidence_Pct", ascending=False).head(limit).reset_index(drop=True) if not s_df.empty else pd.DataFrame()

    return top_buy, top_sell

# =====================================================================
# AI TRADE PERFORMANCE REVIEWER & STRATEGY TUNER
# =====================================================================
def evaluate_strategy_performance_and_suggest_tweaks():
    """
    Analyzes historical trade ledger to compute win rates, profit factor,
    and asset class differences, producing empirical tuning advice.
    """
    timestamp_str = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

    trades_df = pd.DataFrame()
    if os.path.exists(LOCAL_TRADES_CSV) and os.path.getsize(LOCAL_TRADES_CSV) > 0:
        try:
            trades_df = pd.read_csv(LOCAL_TRADES_CSV)
        except Exception:
            pass

    suggestions = []

    if trades_df.empty or "Status" not in trades_df.columns:
        suggestions.append({
            "Timestamp": timestamp_str,
            "Category": "V2 Baseline Setup",
            "Target Preset": "All Presets",
            "Current Parameter": "Factory Defaults Active",
            "Suggested Adjustment": "Run initial paper trading cycles to gather statistical performance.",
            "Confidence Edge": "Prior Model",
            "Actionable_Key": "INIT",
            "Rationale": "Public testbed initial baseline. Quantitative models active with default ATR boundaries."
        })
        sug_df = pd.DataFrame(suggestions)
        sug_df.to_csv(LOCAL_SUGGESTIONS_CSV, index=False)
        return sug_df

    closed_df = trades_df[trades_df["Status"].isin(["TARGET_ACHIEVED", "STOP_LOSS_HIT", "TIME_EXPIRED", "INTRADAY_SQUAREOFF", "OVERBOUGHT_EXIT"])].copy()
    if "PnL_Rs" not in closed_df.columns:
        closed_df["PnL_Rs"] = 0.0
    if "Strategy_Preset" not in closed_df.columns:
        closed_df["Strategy_Preset"] = "Default"

    if closed_df.empty or len(closed_df) < 2:
        suggestions.append({
            "Timestamp": timestamp_str,
            "Category": "Risk-Reward Alignment",
            "Target Preset": "Intraday & Swing",
            "Current Parameter": "Standard 1.5x SL / 3.0x Tgt",
            "Suggested Adjustment": "Calibrate Stop Loss to 1.3x ATR and widen Target to 3.3x ATR",
            "Confidence Edge": "Medium (Model Prior)",
            "Actionable_Key": "TIGHTEN_SL_WIDEN_TGT",
            "Rationale": "Statistical priors demonstrate improved profit factor by reducing stop loss margin in liquid equities."
        })
        suggestions.append({
            "Timestamp": timestamp_str,
            "Category": "Momentum Confluence",
            "Target Preset": "AI / RAG",
            "Current Parameter": "RSI Oversold Filter at 40",
            "Suggested Adjustment": "Prioritize Volume Surge confirmation (>1.5x 20D Avg)",
            "Confidence Edge": "High (Quantitative Prior)",
            "Actionable_Key": "ENABLE_VOL_FILTER",
            "Rationale": "Filtering with volume confirmation prevents premature entries during trend breakdowns."
        })
    else:
        closed_df["Clean_PnL"] = pd.to_numeric(closed_df["PnL_Rs"], errors="coerce").fillna(0.0)

        for preset_name, grp in closed_df.groupby("Strategy_Preset"):
            total_n = len(grp)
            wins = (grp["Clean_PnL"] > 0).sum()
            win_rate = (wins / total_n) * 100.0 if total_n > 0 else 0.0
            gross_win = grp[grp["Clean_PnL"] > 0]["Clean_PnL"].sum()
            gross_loss = abs(grp[grp["Clean_PnL"] < 0]["Clean_PnL"].sum())
            profit_factor = round(gross_win / gross_loss, 2) if gross_loss > 0 else 9.99

            if win_rate < 50.0 and total_n >= 2:
                suggestions.append({
                    "Timestamp": timestamp_str,
                    "Category": "Risk Calibration",
                    "Target Preset": str(preset_name),
                    "Current Parameter": f"Win Rate: {win_rate:.1f}% | PF: {profit_factor}",
                    "Suggested Adjustment": f"Increase RSI Weight by +15% and tighten SL to 1.2x ATR",
                    "Confidence Edge": f"High (Observed Win Rate: {win_rate:.1f}%)",
                    "Actionable_Key": f"OPTIMIZE_{str(preset_name).upper().replace(' ', '_')}",
                    "Rationale": f"Preset '{preset_name}' win rate is {win_rate:.1f}%. Tighter risk parameters prevent large single-trade drawdowns."
                })
            elif win_rate >= 65.0:
                suggestions.append({
                    "Timestamp": timestamp_str,
                    "Category": "Target Expansion",
                    "Target Preset": str(preset_name),
                    "Current Parameter": f"Win Rate: {win_rate:.1f}% | PF: {profit_factor}",
                    "Suggested Adjustment": "Expand target multiplier to 3.6x ATR to let winning trends run",
                    "Confidence Edge": f"Strong ({win_rate:.1f}% Win Rate)",
                    "Actionable_Key": f"EXPAND_TARGET_{str(preset_name).upper().replace(' ', '_')}",
                    "Rationale": f"Strong win rate in '{preset_name}'. Expanding target multiplier maximizes positive expectancy."
                })

    sug_df = pd.DataFrame(suggestions)
    sug_df.to_csv(LOCAL_SUGGESTIONS_CSV, index=False)
    return sug_df

# =====================================================================
# ONE-CLICK OPTIMIZATION APPLIER (TESTBED BUTTON)
# =====================================================================
def apply_suggested_optimizations():
    """Applies recommended strategy tweaks directly into runtime_config.json."""
    config = load_runtime_config()
    now_str = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

    sug_df = pd.read_csv(LOCAL_SUGGESTIONS_CSV) if os.path.exists(LOCAL_SUGGESTIONS_CSV) and os.path.getsize(LOCAL_SUGGESTIONS_CSV) > 0 else evaluate_strategy_performance_and_suggest_tweaks()

    applied = []
    for _, row in sug_df.iterrows():
        key = str(row.get("Actionable_Key", ""))
        if "TIGHTEN_SL" in key or "INIT" in key:
            config["risk_parameters"]["intraday_sl_multiplier"] = 1.1
            config["risk_parameters"]["swing_sl_multiplier"] = 1.3
            config["risk_parameters"]["swing_target_multiplier"] = 3.3
            applied.append("Tuned Risk Multipliers (Intraday SL: 1.1x, Swing SL: 1.3x, Swing Target: 3.3x)")
        if "ENABLE_VOL_FILTER" in key:
            config["weights"]["AI / RAG"]["w_rsi"] = 40
            config["weights"]["AI / RAG"]["w_dma"] = 30
            applied.append("Optimized AI / RAG Weights (RSI: 40%, 200DMA: 30%)")
        if "EXPAND_TARGET" in key:
            config["risk_parameters"]["swing_target_multiplier"] = 3.6
            applied.append("Expanded swing target multiplier to 3.6x")

    if not applied:
        config["risk_parameters"]["swing_target_multiplier"] = 3.3
        config["risk_parameters"]["swing_sl_multiplier"] = 1.35
        applied.append("Fine-tuned default parameters applied.")

    config["last_optimized_timestamp"] = now_str
    config["optimization_status"] = f"🟢 V2 Optimizations Live ({now_str})"
    save_runtime_config(config)

    # Log into audit CSV
    audit_path = os.path.join(LOCAL_DATA_DIR, "execution_audit_log.csv")
    audit_entry = {
        "Timestamp_IST": now_str,
        "Trigger_Source": "V2_ONE_CLICK_OPTIMIZER_BUTTON",
        "Preset": "Strategy Tuning",
        "Recommended_BUY": "Parameters Updated",
        "Recommended_SELL": "None",
        "Execution_Status": "🟢 Applied",
        "Reason_Summary": " | ".join(applied)
    }
    existing_audit = pd.read_csv(audit_path) if os.path.exists(audit_path) and os.path.getsize(audit_path) > 0 else pd.DataFrame()
    combined_audit = pd.concat([existing_audit, pd.DataFrame([audit_entry])], ignore_index=True).drop_duplicates()
    combined_audit.to_csv(audit_path, index=False)

    return {
        "status": "success",
        "timestamp": now_str,
        "changes": applied,
        "active_config": config
    }
