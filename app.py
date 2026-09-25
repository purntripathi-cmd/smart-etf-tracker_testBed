# =====================================================================
# V2 AGY QUANT PLATFORM: PUBLIC TESTBED TERMINAL (ZERO-SECRET)
# =====================================================================
import os
import json
import logging
import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
import streamlit.components.v1 as components

from strategy_engine import (
    DEFAULT_STAGE1_ETF_CONFIG,
    DEFAULT_STAGE2_STOCK_CONFIG,
    DEFAULT_PRESETS,
    PRESETS,
    evaluate_market_metrics,
    get_top_conviction_candidates,
    validate_trade_execution,
    evaluate_trade_exits,
    calculate_rsi_series,
    extract_ticker_df
)
from ml_optimizer import (
    load_ai_trades,
    save_ai_trades,
    get_ai_rag_conviction_candidates,
    evaluate_strategy_performance_and_suggest_tweaks,
    apply_suggested_optimizations,
    load_runtime_config,
    save_runtime_config
)

# Page Setup
st.set_page_config(
    page_title="AGY Quant Platform V2 (Public Testbed)",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

IST = ZoneInfo("Asia/Kolkata")
LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(LOCAL_DATA_DIR, exist_ok=True)

LOCAL_TRADES_CSV = os.path.join(LOCAL_DATA_DIR, "paper_trades.csv")
LOCAL_AUDIT_CSV = os.path.join(LOCAL_DATA_DIR, "execution_audit_log.csv")
LOCAL_USERS_CSV = os.path.join(LOCAL_DATA_DIR, "users_auth.csv")
CONFIG_JSON_PATH = os.path.join(os.path.dirname(__file__), "runtime_config.json")

DEFAULT_PAPER_HEADERS = [
    "Trade_ID", "Username", "Ticker", "Asset_Class", "Trigger_Type", "Strategy_Preset",
    "Status", "Entry_Price", "Executed_Qty", "Stop_Loss", "Target",
    "Execution_Timestamp", "PnL_Rs", "PnL_Pct", "Invested_Value"
]

DEFAULT_AUDIT_HEADERS = [
    "Timestamp_IST", "Trigger_Source", "Preset", "Recommended_BUY",
    "Recommended_SELL", "Execution_Status", "Reason_Summary"
]

# Custom CSS for Sleek Modern Terminal
st.markdown("""
<style>
    .main .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
    .rec-card { border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
    .rec-badge { font-size: 0.70rem; font-weight: 700; border-radius: 4px; padding: 2px 6px; }
    div[data-testid="stMetricValue"] { font-size: 1.4rem; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# LOCAL AUTHENTICATION & USER MANAGEMENT
# =====================================================================
DEFAULT_USERS = [
    {"Username": "demo", "Password": "DemoPassword123!", "Role": "Admin", "Name": "Public Testbed User", "Email": "demo@quant.local", "Mobile": "9999999999"},
]

def load_users():
    if os.path.exists(LOCAL_USERS_CSV) and os.path.getsize(LOCAL_USERS_CSV) > 0:
        try:
            return pd.read_csv(LOCAL_USERS_CSV)
        except Exception:
            pass
    df = pd.DataFrame(DEFAULT_USERS)
    df.to_csv(LOCAL_USERS_CSV, index=False)
    return df

def save_users(users_df):
    users_df.to_csv(LOCAL_USERS_CSV, index=False)

users_df = load_users()

if "logged_user" not in st.session_state:
    st.session_state.logged_user = "demo"
if "logged_role" not in st.session_state:
    st.session_state.logged_role = "Admin"
if "strategy_toast" not in st.session_state:
    st.session_state.strategy_toast = None

current_user = st.session_state.logged_user
is_admin = (st.session_state.logged_role == "Admin")

# =====================================================================
# LOCAL DATA PERSISTENCE
# =====================================================================
@st.cache_data(ttl=300)
def load_historical_market_data(all_tickers):
    download_list = list(set(all_tickers)) + ["^CRSLDX", "^NSEI", "^INDIAVIX"]
    try:
        return yf.download(
            download_list,
            period="1y",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False
        )
    except Exception as e:
        st.error(f"Market download error: {e}")
        return pd.DataFrame()

def load_paper_trades():
    if os.path.exists(LOCAL_TRADES_CSV) and os.path.getsize(LOCAL_TRADES_CSV) > 0:
        try:
            return pd.read_csv(LOCAL_TRADES_CSV)
        except Exception:
            pass
    return pd.DataFrame(columns=DEFAULT_PAPER_HEADERS)

def save_paper_trades(df):
    for c in DEFAULT_PAPER_HEADERS:
        if c not in df.columns:
            df[c] = ""
    df.to_csv(LOCAL_TRADES_CSV, index=False)

def load_audit_log():
    if os.path.exists(LOCAL_AUDIT_CSV) and os.path.getsize(LOCAL_AUDIT_CSV) > 0:
        try:
            return pd.read_csv(LOCAL_AUDIT_CSV)
        except Exception:
            pass
    return pd.DataFrame(columns=DEFAULT_AUDIT_HEADERS)

def save_audit_entry(entry_dict):
    existing = load_audit_log()
    combined = pd.concat([existing, pd.DataFrame([entry_dict])], ignore_index=True).drop_duplicates()
    combined.to_csv(LOCAL_AUDIT_CSV, index=False)

# Load Universe Data
ALL_CONFIG_TICKERS = [x["ticker"] for x in (DEFAULT_STAGE1_ETF_CONFIG + DEFAULT_STAGE2_STOCK_CONFIG)]
active_raw_data = load_historical_market_data(ALL_CONFIG_TICKERS)

# Load Adaptive Configuration
runtime_cfg = load_runtime_config()

# Evaluate Indicators
stocks_market_df, stock_regime = evaluate_market_metrics(active_raw_data, DEFAULT_STAGE2_STOCK_CONFIG, is_stock_mode=True)
etfs_market_df, etf_regime = evaluate_market_metrics(active_raw_data, DEFAULT_STAGE1_ETF_CONFIG, is_stock_mode=False)
regime_data = etf_regime

# =====================================================================
# SIDEBAR
# =====================================================================
with st.sidebar:
    st.markdown("### ⚡ AGY Terminal V2 (Public)")
    st.caption(f"👤 Active Profile: **{current_user}** ({st.session_state.logged_role})")
    st.info("🌐 Public Testbed: Zero GSheets/Telegram tokens required.")

    st.markdown("---")
    active_tab = st.radio(
        "Navigation:",
        [
            "🎯 Tactical Screener & Ladder Planner",
            "📈 Paper Trading & Audit",
            "🤖 AI Quant Advisor",
            "📊 Advanced Quant Hub",
            "🌐 Quant Ecosystem",
            "👤 Profile"
        ],
        index=0
    )

    st.markdown("---")
    st.markdown("##### ⚙️ Universe & Sizing")
    asset_mode_choice = st.radio("Asset Class:", ["🎯 Indian Stocks (52 Equities)", "🛡️ Broad ETFs (35 Products)"], index=0)
    is_stock_mode = ("Stocks" in asset_mode_choice)
    df_all = stocks_market_df if is_stock_mode else etfs_market_df

    base_budget = st.number_input("Tranche Budget (₹)", min_value=1000.0, max_value=500000.0, value=15000.0, step=1000.0)

    st.markdown("---")
    st.markdown(f"**Market Regime:** {regime_data.get('regime', 'Normal')}")
    st.caption(f"{regime_data.get('desc', '')}")
    st.caption(f"**India VIX:** {regime_data.get('vix', 15.0):.1f} | {regime_data.get('vix_advice', '')}")

    if st.session_state.strategy_toast:
        st.toast(st.session_state.strategy_toast)
        st.session_state.strategy_toast = None

# =====================================================================
# TAB 1: TACTICAL SCREENER (TOP 3 BUY / SELL MATRIX)
# =====================================================================
if active_tab == "🎯 Tactical Screener & Ladder Planner":
    st.markdown("### 🎯 Tactical Screener & Ladder Execution Matrix (V2)")

    m_col1, m_col2 = st.columns([3, 1])
    with m_col1:
        st.markdown(
            "##### 🌟 High-Conviction Matrix &nbsp;<span style='font-size:0.82rem; font-weight:normal; color:#64748b;'>"
            "(Top 3 BUY + Top 3 SELL per Category & Preset)</span>",
            unsafe_allow_html=True
        )
    with m_col2:
        matrix_is_etf = st.checkbox("🔄 Show ETF Matrix (Default: Stocks)", value=(not is_stock_mode), key="v2_matrix_toggle")

    target_matrix_source = etfs_market_df if matrix_is_etf else stocks_market_df
    categories_list = ["AI / RAG", "Default", "Long-Term", "Swing / Positional", "Intraday"]
    category_picks = {}
    ticker_match_count = {}

    for cat_name in categories_list:
        if cat_name == "AI / RAG":
            cat_buy, cat_sell = get_ai_rag_conviction_candidates(target_matrix_source, is_stock_mode=(not matrix_is_etf), limit=3)
        else:
            cat_buy, cat_sell = get_top_conviction_candidates(target_matrix_source, preset_name=cat_name, is_stock_mode=(not matrix_is_etf), limit=3)
        category_picks[cat_name] = {"buy": cat_buy, "sell": cat_sell}

        for sub_df in [cat_buy, cat_sell]:
            if sub_df is not None and not sub_df.empty:
                for sym in sub_df["Ticker"].values:
                    ticker_match_count[sym] = ticker_match_count.get(sym, 0) + 1

    matrix_cols = st.columns(5)
    for idx, cat_name in enumerate(categories_list):
        with matrix_cols[idx]:
            cat_icon = "🤖" if "AI" in cat_name else ("📌" if cat_name == "Default" else ("🏛️" if "Long" in cat_name else ("⚡" if "Swing" in cat_name else "⏱️")))
            st.markdown(
                f"<div style='font-size:0.84rem; font-weight:700; color:#1E88E5; border-bottom: 2px solid #1E88E5; padding-bottom: 2px; margin-bottom: 8px;'>"
                f"{cat_icon} {cat_name}</div>",
                unsafe_allow_html=True
            )

            # TOP 3 BUY
            st.markdown("<div style='font-size:0.75rem; font-weight:700; color:#155724; margin-bottom:4px;'>🟢 TOP 3 BUY</div>", unsafe_allow_html=True)
            top_buy_df = category_picks[cat_name]["buy"]
            if top_buy_df is not None and not top_buy_df.empty:
                for rank_i, (_, t_row) in enumerate(top_buy_df.iterrows()):
                    sym = t_row["Ticker"]
                    freq = ticker_match_count.get(sym, 1)
                    card_border = "#f59e0b" if freq >= 3 else ("#0284c7" if freq == 2 else "#22c55e")
                    card_bg = "#fffbeb" if freq >= 3 else ("#f0f9ff" if freq == 2 else "#ffffff")
                    badge_info = f"Conf: {t_row.get('AI_Confidence_Score', '')}" if "AI" in cat_name else f"Score: {t_row.get('Composite Score', 0):.1f}"

                    st.markdown(
                        f"""
                        <div class="rec-card" style="background-color: {card_bg}; border: 1.2px solid {card_border};">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-weight:700; font-size:0.80rem;">#{rank_i+1} {sym}</span>
                                <span class="rec-badge" style="background-color: #dcfce7; color: #15803d;">BUY | {badge_info}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color:#475569; margin-top:3px;">
                                <span>₹{t_row['CMP (₹)']:.2f}</span>
                                <span>RSI: {t_row['RSI (14D)']:.1f}</span>
                                <span>Tgt: ₹{t_row['Target']:.1f}</span>
                            </div>
                            <div style="font-size:0.68rem; color:#64748b; margin-top:2px;">
                                SL: ₹{t_row['Stop_Loss']:.1f} | {f'★ Multi-Match ({freq}x)' if freq > 1 else ''}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.caption("No qualified BUY setups.")

            # TOP 3 SELL
            st.markdown("<div style='font-size:0.75rem; font-weight:700; color:#991b1b; margin-top:8px; margin-bottom:4px;'>🔴 TOP 3 SELL</div>", unsafe_allow_html=True)
            top_sell_df = category_picks[cat_name]["sell"]
            if top_sell_df is not None and not top_sell_df.empty:
                for rank_i, (_, t_row) in enumerate(top_sell_df.iterrows()):
                    sym = t_row["Ticker"]
                    freq = ticker_match_count.get(sym, 1)
                    card_border = "#f59e0b" if freq >= 3 else ("#0284c7" if freq == 2 else "#ef4444")
                    card_bg = "#fffbeb" if freq >= 3 else ("#f0f9ff" if freq == 2 else "#ffffff")
                    badge_info = f"Conf: {t_row.get('AI_Confidence_Score', '')}" if "AI" in cat_name else f"Score: {t_row.get('Composite Score', 0):.1f}"

                    st.markdown(
                        f"""
                        <div class="rec-card" style="background-color: {card_bg}; border: 1.2px solid {card_border};">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-weight:700; font-size:0.80rem;">#{rank_i+1} {sym}</span>
                                <span class="rec-badge" style="background-color: #fee2e2; color: #b91c1c;">SELL | {badge_info}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color:#475569; margin-top:3px;">
                                <span>₹{t_row['CMP (₹)']:.2f}</span>
                                <span>RSI: {t_row['RSI (14D)']:.1f}</span>
                                <span>Cover: ₹{t_row['Target']:.1f}</span>
                            </div>
                            <div style="font-size:0.68rem; color:#64748b; margin-top:2px;">
                                Stop: ₹{t_row['Stop_Loss']:.1f} | {f'★ Multi-Match ({freq}x)' if freq > 1 else ''}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.caption("No qualified SELL setups.")

    st.markdown("---")

    # Interactive Screener Table
    f1, f2 = st.columns([1, 1])
    with f1:
        depth = st.radio("Screening Depth:", ["🎯 Top 10 High-Conviction", "⚡ Top 15 Ranked", f"🌐 Full Universe ({len(df_all)})"], horizontal=True)
    with f2:
        cat_choices = ["All"] + sorted(list(df_all["Category"].unique())) if not df_all.empty else ["All"]
        sel_cat = st.selectbox("Category Filter:", cat_choices)

    v_df = df_all.copy() if sel_cat == "All" else df_all[df_all["Category"] == sel_cat].copy()
    sorted_df = v_df.sort_values(by="Composite Buy Score", ascending=True)
    limit_n = 10 if "Top 10" in depth else (15 if "Top 15" in depth else len(sorted_df))
    slice_df = sorted_df.head(limit_n)

    cols_render = [
        "Ticker", "Name", "Category", "CMP (₹)", "Composite Buy Score", "Technical Score", "Fundamental Score",
        "RSI (14D)", "Bollinger %B", "Dist VWAP %", "Dist 20DMA %", "Dist 50DMA %", "Dist 100DMA %", "Dist 200DMA %",
        "14D ATR (₹)", "Volume Surge Ratio", "Falling Knife Guard", "Structural Guard / iNAV"
    ]
    present = [c for c in cols_render if c in slice_df.columns]
    st.dataframe(
        slice_df[present].style.format({
            "CMP (₹)": "₹{:.2f}",
            "Composite Buy Score": "{:.1f}",
            "Technical Score": "{:.1f}",
            "Fundamental Score": "{:.1f}",
            "RSI (14D)": "{:.1f}",
            "Bollinger %B": "{:.2f}",
            "Dist VWAP %": "{:+.2f}%",
            "Dist 20DMA %": "{:+.2f}%",
            "Dist 50DMA %": "{:+.2f}%",
            "Dist 100DMA %": "{:+.2f}%",
            "Dist 200DMA %": "{:+.2f}%",
            "14D ATR (₹)": "₹{:.2f}",
            "Volume Surge Ratio": "{:.2f}x"
        }),
        use_container_width=True,
        height=380
    )

# =====================================================================
# TAB 2: PAPER TRADING & AUDIT (LEDGER & EXITS)
# =====================================================================
elif active_tab == "📈 Paper Trading & Audit":
    raw_trades = load_paper_trades()
    trades_df = raw_trades.copy()

    st.markdown("### 📈 V2 Paper Trading Ledger & Execution Hub")

    with st.expander("⚡ Run Manual Strategy Routine Test", expanded=True):
        ec1, ec2, ec3 = st.columns([2, 1, 1])
        with ec1:
            exec_mode = st.selectbox(
                "Select Scheduled Routine to Trigger:",
                [
                    "03:00 PM IST - Multi-Preset Accumulation (Top 3 Stocks & ETFs for All Presets)",
                    "09:45 AM IST - Intraday Entry (Top 3 Stocks + Top 3 ETFs)",
                    "03:10 PM IST - Intraday Auto-Squareoff (Market Close MTM)"
                ]
            )
        with ec2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            run_btn = st.button("🚀 Execute Strategy Run", use_container_width=True, type="primary")
        with ec3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            with st.popover("🗑️ Reset V2 Data", use_container_width=True):
                st.warning("⚠️ This will clear all local paper trades and audit logs.")
                if st.button("🚨 Confirm Clear", type="primary", use_container_width=True):
                    save_paper_trades(pd.DataFrame(columns=DEFAULT_PAPER_HEADERS))
                    save_audit_entry({"Timestamp_IST": datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"), "Trigger_Source": "RESET", "Preset": "All", "Recommended_BUY": "None", "Recommended_SELL": "None", "Execution_Status": "Reset", "Reason_Summary": "Ledger cleared."})
                    st.cache_data.clear()
                    st.session_state.strategy_toast = "Ledgers reset clean."
                    st.rerun()

        if run_btn:
            now_str = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
            created = []
            all_t = load_paper_trades()
            active_t = all_t[all_t["Status"] == "ACTIVE"] if not all_t.empty else pd.DataFrame()
            active_syms = set(active_t["Ticker"].astype(str).str.replace(".NS", "")) if not active_t.empty else set()

            if "09:45" in exec_mode:
                stk_b, _ = get_top_conviction_candidates(stocks_market_df, preset_name="Intraday", is_stock_mode=True, limit=3)
                for _, r in stk_b.iterrows():
                    sym = str(r["Ticker"]).replace(".NS", "")
                    cmp_v = float(r["CMP (₹)"])
                    if sym in active_syms or cmp_v <= 0: continue
                    q = max(1, int(15000 // cmp_v))
                    created.append({"Trade_ID": f"V2_INT_{int(datetime.datetime.now(IST).timestamp())}_{sym}", "Username": current_user, "Ticker": sym, "Asset_Class": "Stock", "Trigger_Type": "MANUAL_INTRADAY", "Strategy_Preset": "Intraday", "Status": "ACTIVE", "Entry_Price": cmp_v, "Executed_Qty": q, "Stop_Loss": r["Stop_Loss"], "Target": r["Target"], "Execution_Timestamp": now_str, "PnL_Rs": 0.0, "PnL_Pct": "0.0%", "Invested_Value": round(cmp_v * q, 2)})
                    active_syms.add(sym)

                etf_b, _ = get_top_conviction_candidates(etfs_market_df, preset_name="Intraday", is_stock_mode=False, limit=3)
                for _, r in etf_b.iterrows():
                    sym = str(r["Ticker"]).replace(".NS", "")
                    cmp_v = float(r["CMP (₹)"])
                    if sym in active_syms or cmp_v <= 0: continue
                    q = max(1, int(15000 // cmp_v))
                    created.append({"Trade_ID": f"V2_INT_{int(datetime.datetime.now(IST).timestamp())}_{sym}", "Username": current_user, "Ticker": sym, "Asset_Class": "ETF", "Trigger_Type": "MANUAL_INTRADAY", "Strategy_Preset": "Intraday", "Status": "ACTIVE", "Entry_Price": cmp_v, "Executed_Qty": q, "Stop_Loss": r["Stop_Loss"], "Target": r["Target"], "Execution_Timestamp": now_str, "PnL_Rs": 0.0, "PnL_Pct": "0.0%", "Invested_Value": round(cmp_v * q, 2)})
                    active_syms.add(sym)

            elif "03:00" in exec_mode:
                ai_b, _ = get_ai_rag_conviction_candidates(stocks_market_df, is_stock_mode=True, limit=3)
                for _, r in ai_b.iterrows():
                    sym = str(r["Ticker"]).replace(".NS", "")
                    cmp_v = float(r["CMP (₹)"])
                    if sym in active_syms or cmp_v <= 0: continue
                    q = max(1, int(15000 // cmp_v))
                    created.append({"Trade_ID": f"V2_AI_{int(datetime.datetime.now(IST).timestamp())}_{sym}", "Username": current_user, "Ticker": sym, "Asset_Class": "Stock", "Trigger_Type": "AI_CONFLUENCE", "Strategy_Preset": "AI / RAG", "Status": "ACTIVE", "Entry_Price": cmp_v, "Executed_Qty": q, "Stop_Loss": r["Stop_Loss"], "Target": r["Target"], "Execution_Timestamp": now_str, "PnL_Rs": 0.0, "PnL_Pct": "0.0%", "Invested_Value": round(cmp_v * q, 2)})
                    active_syms.add(sym)

                for p in ["Default", "Long-Term", "Swing / Positional"]:
                    etf_b, _ = get_top_conviction_candidates(etfs_market_df, preset_name=p, is_stock_mode=False, limit=3)
                    for _, r in etf_b.iterrows():
                        sym = str(r["Ticker"]).replace(".NS", "")
                        cmp_v = float(r["CMP (₹)"])
                        if sym in active_syms or cmp_v <= 0: continue
                        q = max(1, int(15000 // cmp_v))
                        created.append({"Trade_ID": f"V2_TR_{int(datetime.datetime.now(IST).timestamp())}_{sym}", "Username": current_user, "Ticker": sym, "Asset_Class": "ETF", "Trigger_Type": "MANUAL_3PM", "Strategy_Preset": p, "Status": "ACTIVE", "Entry_Price": cmp_v, "Executed_Qty": q, "Stop_Loss": r["Stop_Loss"], "Target": r["Target"], "Execution_Timestamp": now_str, "PnL_Rs": 0.0, "PnL_Pct": "0.0%", "Invested_Value": round(cmp_v * q, 2)})
                        active_syms.add(sym)

                    stk_b, _ = get_top_conviction_candidates(stocks_market_df, preset_name=p, is_stock_mode=True, limit=3)
                    for _, r in stk_b.iterrows():
                        sym = str(r["Ticker"]).replace(".NS", "")
                        cmp_v = float(r["CMP (₹)"])
                        if sym in active_syms or cmp_v <= 0: continue
                        q = max(1, int(15000 // cmp_v))
                        created.append({"Trade_ID": f"V2_TR_{int(datetime.datetime.now(IST).timestamp())}_{sym}", "Username": current_user, "Ticker": sym, "Asset_Class": "Stock", "Trigger_Type": "MANUAL_3PM", "Strategy_Preset": p, "Status": "ACTIVE", "Entry_Price": cmp_v, "Executed_Qty": q, "Stop_Loss": r["Stop_Loss"], "Target": r["Target"], "Execution_Timestamp": now_str, "PnL_Rs": 0.0, "PnL_Pct": "0.0%", "Invested_Value": round(cmp_v * q, 2)})
                        active_syms.add(sym)
            else:
                all_t = evaluate_trade_exits(all_t, active_raw_data, force_squareoff_intraday=True)

            if created:
                combined = pd.concat([all_t, pd.DataFrame(created)], ignore_index=True)
                save_paper_trades(combined)

            save_audit_entry({
                "Timestamp_IST": now_str, "Trigger_Source": f"V2_MANUAL_{exec_mode}",
                "Preset": "Multi-Asset", "Recommended_BUY": ", ".join([r["Ticker"] for r in created]) or "None",
                "Recommended_SELL": "None", "Execution_Status": f"🟢 Logged ({len(created)} Orders)",
                "Reason_Summary": f"Manual test logged {len(created)} orders."
            })
            st.cache_data.clear()
            st.session_state.strategy_toast = f"Manual execution approved {len(created)} trades!"
            st.rerun()

    # MTM Ledger Table
    if not trades_df.empty and "Status" in trades_df.columns:
        trades_df = evaluate_trade_exits(trades_df, active_raw_data)
        open_trades = trades_df[trades_df["Status"] == "ACTIVE"].copy()
        closed_trades = trades_df[trades_df["Status"] != "ACTIVE"].copy()

        live_cmps, unrealized_rs = [], []
        for _, r in open_trades.iterrows():
            sym = str(r["Ticker"]).replace(".NS", "")
            t_df = extract_ticker_df(active_raw_data, sym)
            c_p = float(t_df["Close"].dropna().iloc[-1]) if (not t_df.empty and "Close" in t_df.columns) else float(r.get("Entry_Price", 0))
            ep = float(r.get("Entry_Price", c_p))
            q = float(r.get("Executed_Qty", 1))
            live_cmps.append(c_p)
            unrealized_rs.append(round((c_p - ep) * q, 2))

        open_trades["Live CMP (₹)"] = live_cmps
        open_trades["Unrealized PnL (₹)"] = unrealized_rs

        cap_deployed = float(pd.to_numeric(open_trades["Invested_Value"], errors="coerce").sum()) if not open_trades.empty else 0.0
        tot_unrealized = sum(unrealized_rs)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Live Unrealized PnL", f"₹{tot_unrealized:+,.2f}")
        m2.metric("Active Capital Deployed", f"₹{cap_deployed:,.2f}", f"{len(open_trades)} Open Positions")
        closed_pnl = float(pd.to_numeric(closed_trades["PnL_Rs"], errors="coerce").sum()) if not closed_trades.empty else 0.0
        m3.metric("Closed Realized PnL", f"₹{closed_pnl:+,.2f}", f"{len(closed_trades)} Trades")
        m4.metric("Win Rate", f"{(closed_trades['PnL_Rs'] > 0).mean()*100:.1f}%" if not closed_trades.empty else "N/A")

        st.markdown("##### 📋 Open Active Positions")
        if not open_trades.empty:
            st.dataframe(open_trades[["Trade_ID", "Ticker", "Asset_Class", "Strategy_Preset", "Entry_Price", "Live CMP (₹)", "Executed_Qty", "Stop_Loss", "Target", "Unrealized PnL (₹)"]], use_container_width=True)
        else:
            st.info("No active open positions in ledger.")

        st.markdown("##### 📜 Closed Positions")
        if not closed_trades.empty:
            st.dataframe(closed_trades[["Trade_ID", "Ticker", "Asset_Class", "Strategy_Preset", "Status", "Entry_Price", "Executed_Qty", "PnL_Rs", "PnL_Pct"]], use_container_width=True, height=180)
    else:
        st.info("No paper trades found. Run a manual strategy test above to populate trades.")

    # Audit Log
    st.markdown("---")
    st.markdown("##### 📋 Execution Audit Log")
    aud_df = load_audit_log()
    if not aud_df.empty:
        st.dataframe(aud_df.sort_values(by="Timestamp_IST", ascending=False), use_container_width=True, height=160)

# =====================================================================
# TAB 3: AI QUANT ADVISOR (TRADE REVIEW & ONE-CLICK STRATEGY TUNER)
# =====================================================================
elif active_tab == "🤖 AI Quant Advisor":
    st.markdown("### 🤖 V2 AI Quant Advisor & Strategy Optimization")
    st.caption("Empirically evaluates open/closed trades and dynamically calibrates stop loss, target, and conviction weights.")

    sug_df = evaluate_strategy_performance_and_suggest_tweaks()

    ac1, ac2, ac3 = st.columns([2, 1, 1])
    with ac1:
        st.markdown(f"**Optimization Status:** `{runtime_cfg.get('optimization_status', 'Active')}`")
    with ac2:
        if st.button("🔄 Refresh Analysis", use_container_width=True):
            sug_df = evaluate_strategy_performance_and_suggest_tweaks()
            st.session_state.strategy_toast = "Refreshed recommendations."
            st.rerun()
    with ac3:
        if st.button("⚡ Apply Suggested Changes", use_container_width=True, type="primary"):
            res = apply_suggested_optimizations()
            st.success(f"Applied {len(res['changes'])} optimizations!")
            st.cache_data.clear()
            st.rerun()

    st.markdown("##### 📊 Empirical Recommendations")
    st.dataframe(sug_df, use_container_width=True)

    with st.expander("🔬 View runtime_config.json", expanded=False):
        st.json(runtime_cfg)

# =====================================================================
# TAB 4: ADVANCED QUANT HUB
# =====================================================================
elif active_tab == "📊 Advanced Quant Hub":
    st.markdown("### 📊 Advanced Quantitative Distributions")
    sorted_df = df_all.sort_values(by="Composite Buy Score", ascending=True).reset_index(drop=True)
    opts = [f"#{i+1} | {r['Ticker']} - {r['Name']}" for i, r in sorted_df.iterrows()]
    sel_item = st.selectbox("Select Asset for Statistical Breakdown:", opts)
    chosen_t = sorted_df.iloc[opts.index(sel_item)]["Ticker"]

    raw_sub = extract_ticker_df(active_raw_data, chosen_t)
    if not raw_sub.empty and "Close" in raw_sub.columns:
        c_c = raw_sub["Close"].dropna()
        f_rsi = calculate_rsi_series(c_c)
        st.metric(f"Current 14D RSI for {chosen_t}", f"{float(f_rsi.iloc[-1]):.1f}")

# =====================================================================
# TAB 5: QUANT ECOSYSTEM
# =====================================================================
elif active_tab == "🌐 Quant Ecosystem":
    st.markdown("### 🌐 Quantitative Ecosystem & External Terminals")
    terminals = {
        "TradingView Advanced Charts": "https://in.tradingview.com/chart/",
        "Screener.in Financials": "https://www.screener.in/"
    }
    sel_term = st.selectbox("Select Terminal:", list(terminals.keys()))
    st.link_button(f"↗️ Open {sel_term} in New Tab", terminals[sel_term])
    components.iframe(src=terminals[sel_term], height=800, scrolling=True)

# =====================================================================
# TAB 6: PROFILE
# =====================================================================
elif active_tab == "👤 Profile":
    st.markdown("### 👤 User Profile & Credentials")
    st.write(f"Logged in as: **{current_user}**")
