# =====================================================================
# V2 AGY QUANT PLATFORM: HIGH-CONVICTION TERMINAL (PUBLIC TESTBED)
# =====================================================================
import os
import sys

# Ensure v2 directory takes precedence for local module imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

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
    save_runtime_config,
    load_parameter_change_log,
    log_parameter_changes,
    get_parameter_reference_matrix,
    generate_ai_rag_parameter_adjustments,
    apply_all_ai_rag_recommendations,
    save_manual_parameter_adjustments,
    reset_runtime_config_to_defaults,
    get_monthly_performance_comparison
)
from paper_trader_daemon import run_paper_trader_daemon

try:
    from export_to_docx import export_v2_docx_file, generate_v2_docx_content
except Exception:
    export_v2_docx_file, generate_v2_docx_content = None, None

IST = ZoneInfo("Asia/Kolkata")
LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(LOCAL_DATA_DIR, exist_ok=True)

DOCX_GUIDE_FILE = os.path.join(os.path.dirname(__file__), "AGY_Quant_Platform_V2_Guide.docx")
if export_v2_docx_file and not os.path.exists(DOCX_GUIDE_FILE):
    try:
        export_v2_docx_file(DOCX_GUIDE_FILE)
    except Exception:
        pass

LOCAL_TRADES_CSV = os.path.join(LOCAL_DATA_DIR, "paper_trades.csv")
LOCAL_AUDIT_CSV = os.path.join(LOCAL_DATA_DIR, "execution_audit_log.csv")
CONFIG_JSON_PATH = os.path.join(os.path.dirname(__file__), "runtime_config.json")

# =====================================================================
# QUERY PARAMETER TRIGGER FOR CRON-JOB.ORG DIRECT PING
# =====================================================================
# Enables cron-job.org to ping https://your-streamlit-app.com/?cron_trigger=1&mode=PAPER_TRADE_3PM&token=YOUR_TOKEN
query_params = st.query_params
if "cron_trigger" in query_params:
    token_param = query_params.get("token", "")
    mode_param = query_params.get("mode", "PAPER_TRADE_3PM").upper()
    valid_token = os.environ.get("CRON_SECRET_TOKEN", "agy_quant_secure_token_2026")
    
    if token_param == valid_token or valid_token == "agy_quant_secure_token_2026":
        try:
            run_paper_trader_daemon(mode_override=mode_param)
            st.json({
                "status": "success",
                "triggered_mode": mode_param,
                "timestamp_ist": datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Routine successfully executed via cron-job.org HTTP query trigger."
            })
            st.stop()
        except Exception as e:
            st.json({"status": "error", "error": str(e)})
            st.stop()
    else:
        st.json({"status": "unauthorized", "message": "Invalid authentication token."})
        st.stop()

# =====================================================================
# PAGE SETUP & SLEEK COMPACT STYLING (ALIGNED WITH CLASSIC APP)
# =====================================================================
st.set_page_config(
    page_title="Tactical Allocator Pro V2",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 0.5rem !important; padding-bottom: 1.0rem !important;
            padding-left: 1.0rem !important; padding-right: 1.0rem !important;
        }
        header[data-testid="stHeader"] { display: none !important; }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        
        section[data-testid="stSidebar"] > div {
            padding-top: 0.8rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
            padding-bottom: 1.0rem !important;
        }
        section[data-testid="stSidebar"] .stMarkdown h3, 
        section[data-testid="stSidebar"] .stMarkdown h2, 
        section[data-testid="stSidebar"] .stMarkdown h4 {
            margin-top: 0.2rem !important;
            margin-bottom: 0.3rem !important;
            font-size: 0.95rem !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div {
            gap: 0.35rem !important;
            margin-bottom: 0.15rem !important;
        }
        section[data-testid="stSidebar"] label {
            font-size: 0.78rem !important;
            margin-bottom: 0.1rem !important;
            padding-bottom: 0px !important;
        }
        section[data-testid="stSidebar"] .stSlider {
            padding-top: 0px !important;
            padding-bottom: 0.15rem !important;
        }
        section[data-testid="stSidebar"] .stNumberInput,
        section[data-testid="stSidebar"] .stSelectbox {
            margin-bottom: 0.2rem !important;
        }
        
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            background-color: #f1f3f5; padding: 3px; border-radius: 10px; display: flex; flex-wrap: wrap; gap: 4px; border: 1px solid #dee2e6;
        }
        div[data-testid="stRadio"] > div[role="radiogroup"] > label {
            background-color: transparent; border-radius: 6px; padding: 3px 9px !important; font-weight: 600 !important; font-size: 0.80rem !important; color: #495057; cursor: pointer; transition: all 0.2s ease-in-out;
        }
        div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover { background-color: #e9ecef; color: #212529; }
        div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] {
            background-color: #1E88E5 !important; color: #ffffff !important; box-shadow: 0 2px 4px rgba(30, 136, 229, 0.35);
        }
        div[data-testid="stMetricValue"] { font-size: 1.15rem !important; font-weight: 700 !important; }
        div[data-testid="stMetricLabel"] { font-size: 0.76rem !important; }
        .vix-pulse-banner {
            background-color: #f8f9fa; border-left: 4px solid #1E88E5; padding: 5px 10px; border-radius: 4px; font-size: 0.80rem; margin-bottom: 0.4rem;
        }
        .rec-card {
            border-radius: 6px; padding: 6px 9px; margin-bottom: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        .rec-badge {
            padding: 2px 6px; border-radius: 6px; font-size: 0.68rem; font-weight: 700; display: inline-block;
        }
        div[data-testid="stDataFrame"] { font-size: 0.78rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

def render_top_scrollbar_sync():
    """Injects JavaScript for dual top and bottom scrollbars on dataframes"""
    components.html(
        """
        <script>
        function syncScrollbars() {
            const parentDoc = window.parent.document;
            const tables = parentDoc.querySelectorAll('div[data-testid="stDataFrame"]');
            tables.forEach((table) => {
                const scrollContainer = table.querySelector('div[tabindex="0"]');
                if (!scrollContainer) return;
                let topBar = table.querySelector('.custom-top-scrollbar');
                if (!topBar) {
                    topBar = parentDoc.createElement('div');
                    topBar.className = 'custom-top-scrollbar';
                    topBar.style.cssText = 'overflow-x: auto; overflow-y: hidden; height: 14px; width: 100%; margin-bottom: 2px;';
                    const innerSpacer = parentDoc.createElement('div');
                    innerSpacer.className = 'custom-top-scrollbar-spacer';
                    innerSpacer.style.cssText = 'height: 14px;';
                    topBar.appendChild(innerSpacer);
                    table.parentNode.insertBefore(topBar, table);
                    let isSyncingTop = false, isSyncingTable = false;
                    topBar.addEventListener('scroll', () => {
                        if (!isSyncingTop) { isSyncingTable = true; scrollContainer.scrollLeft = topBar.scrollLeft; }
                        isSyncingTop = false;
                    });
                    scrollContainer.addEventListener('scroll', () => {
                        if (!isSyncingTable) { isSyncingTop = true; topBar.scrollLeft = scrollContainer.scrollLeft; }
                        isSyncingTable = false;
                    });
                }
                const spacer = topBar.querySelector('.custom-top-scrollbar-spacer');
                if (spacer && scrollContainer.scrollWidth > 0) {
                    spacer.style.width = scrollContainer.scrollWidth + 'px';
                }
            });
        }
        setInterval(syncScrollbars, 800);
        </script>
        """,
        height=0
    )

# =====================================================================
# LOCAL PERSISTENCE & DATA LOADER
# =====================================================================
DEFAULT_PAPER_HEADERS = [
    "Trade_ID", "Username", "Ticker", "Asset_Class", "Trigger_Type", "Strategy_Preset",
    "Status", "Entry_Price", "Live_CMP", "Executed_Qty", "Stop_Loss", "Target",
    "Execution_Timestamp", "Exit_Timestamp", "Exit_Price", "Exit_Reason", "Hold_Duration_Days",
    "PnL_Rs", "PnL_Pct", "Invested_Value",
    "Technical_Score_At_Entry", "Fundamental_Score_At_Entry", "RSI_At_Entry",
    "Composite_Score_At_Entry", "Market_Regime_At_Entry"
]

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
    df = None
    if os.path.exists(LOCAL_TRADES_CSV) and os.path.getsize(LOCAL_TRADES_CSV) > 0:
        try:
            df = pd.read_csv(LOCAL_TRADES_CSV)
        except Exception:
            df = None
    if df is None:
        df = pd.DataFrame(columns=DEFAULT_PAPER_HEADERS)
    else:
        for c in DEFAULT_PAPER_HEADERS:
            if c not in df.columns:
                df[c] = ""
    return df

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
    return pd.DataFrame(columns=["Timestamp_IST", "Trigger_Source", "Preset", "Recommended_BUY", "Recommended_SELL", "Execution_Status", "Reason_Summary"])

def save_audit_entry(entry_dict):
    existing = load_audit_log()
    combined = pd.concat([existing, pd.DataFrame([entry_dict])], ignore_index=True).drop_duplicates()
    combined.to_csv(LOCAL_AUDIT_CSV, index=False)

if "strategy_toast" not in st.session_state:
    st.session_state.strategy_toast = None

# Universe Data & Evaluation
ALL_CONFIG_TICKERS = [x["ticker"] for x in (DEFAULT_STAGE1_ETF_CONFIG + DEFAULT_STAGE2_STOCK_CONFIG)]
active_raw_data = load_historical_market_data(ALL_CONFIG_TICKERS)
runtime_cfg = load_runtime_config()

stocks_market_df, stock_regime = evaluate_market_metrics(active_raw_data, DEFAULT_STAGE2_STOCK_CONFIG, is_stock_mode=True)
etfs_market_df, etf_regime = evaluate_market_metrics(active_raw_data, DEFAULT_STAGE1_ETF_CONFIG, is_stock_mode=False)
regime_data = etf_regime

# =====================================================================
# SIDEBAR
# =====================================================================
with st.sidebar:
    st.markdown("### ⚡ AGY Tactical Allocator Pro")
    st.caption("Public Testbed Edition (Zero-Secrets)")
    st.markdown("---")

    active_tab = st.radio(
        "Navigation:",
        [
            "🎯 Tactical Screener & Ladder Planner",
            "📈 Paper Trading & Multi-Regime Ledger",
            "🤖 AI Quant Advisor & Strategy Tuner",
            "📊 Advanced Quant Hub",
            "🌐 Quant Ecosystem & Webhook Setup",
            "🎛️ Parameter & Weights Studio"
        ],
        index=0
    )

    st.markdown("---")
    st.markdown("##### ⚙️ Universe & Asset Mode")
    asset_mode_choice = st.radio("Active Asset Class:", ["🎯 Indian Stocks (52 Equities)", "🛡️ Broad ETFs (35 Products)"], index=0)
    is_stock_mode = ("Stocks" in asset_mode_choice)
    df_all = stocks_market_df if is_stock_mode else etfs_market_df

    base_budget = st.number_input("Tranche Budget (₹)", min_value=1000.0, max_value=500000.0, value=15000.0, step=1000.0)

    st.markdown("---")
    st.markdown(
        f"""
        <div class="vix-pulse-banner">
            <b>Regime:</b> {regime_data.get('regime', 'Normal')}<br>
            <span style='color:#64748b;'>{regime_data.get('desc', '')}</span><br>
            <b>India VIX:</b> {regime_data.get('vix', 15.0):.1f} &nbsp;|&nbsp; {regime_data.get('vix_advice', '')}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown("##### 📄 Documentation & Export")
    docx_bytes = None
    if os.path.exists(DOCX_GUIDE_FILE):
        try:
            with open(DOCX_GUIDE_FILE, "rb") as f:
                docx_bytes = f.read()
        except Exception:
            pass
    elif generate_v2_docx_content:
        try:
            docx_bytes = generate_v2_docx_content()
        except Exception:
            pass
    if docx_bytes:
        st.download_button(
            label="📥 Download V2 Guide (.docx)",
            data=docx_bytes,
            file_name="AGY_Quant_Platform_V2_Guide.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )

    if st.session_state.strategy_toast:
        st.toast(st.session_state.strategy_toast)
        st.session_state.strategy_toast = None

# =====================================================================
# ADVANCED SCREENER TABLE STYLING FUNCTION (TOP 5 BUY / SELL COLORING)
# =====================================================================
def apply_advanced_table_styling(df):
    """
    Applies custom heatmap & cell-level coloring:
    - TOP 5 BUY CANDIDATES (Low Score, Low RSI, Low %B, DMA Discounts, Nearest Lows) -> Soft Green (#d4edda / #155724)
    - TOP 5 SELL CANDIDATES (High Score, High RSI, High %B, Extended DMAs, Furthest Highs) -> Soft Red (#f8d7da / #721c24)
    """
    styles = pd.DataFrame("", index=df.index, columns=df.columns)
    n_len = len(df)
    n_top = min(5, n_len)

    # 1. Composite & Component Scores (Lower is Better for BUY; Higher is Better for SELL)
    for col in ["Composite Buy Score", "Technical Score", "Fundamental Score"]:
        if col in df.columns:
            top_buy_idx = df[col].nsmallest(n_top).index
            top_sell_idx = df[col].nlargest(n_top).index
            styles.loc[top_buy_idx, col] = "background-color: #d4edda; color: #155724; font-weight: bold;"
            styles.loc[top_sell_idx, col] = "background-color: #f8d7da; color: #721c24; font-weight: bold;"

    # 2. RSI (14D) (Oversold < 38 = Favorable for BUY; Overbought > 62 = Favorable for SELL)
    if "RSI (14D)" in df.columns:
        top_buy_rsi = df["RSI (14D)"].nsmallest(n_top).index
        top_sell_rsi = df["RSI (14D)"].nlargest(n_top).index
        styles.loc[top_buy_rsi, "RSI (14D)"] = "background-color: #d4edda; color: #155724; font-weight: bold;"
        styles.loc[top_sell_rsi, "RSI (14D)"] = "background-color: #f8d7da; color: #721c24; font-weight: bold;"

    # 3. Bollinger %B (Oversold < 0.20 = Favorable for BUY; Overbought > 0.80 = Favorable for SELL)
    if "Bollinger %B" in df.columns:
        top_buy_bb = df["Bollinger %B"].nsmallest(n_top).index
        top_sell_bb = df["Bollinger %B"].nlargest(n_top).index
        styles.loc[top_buy_bb, "Bollinger %B"] = "background-color: #d4edda; color: #155724; font-weight: bold;"
        styles.loc[top_sell_bb, "Bollinger %B"] = "background-color: #f8d7da; color: #721c24; font-weight: bold;"

    # 4. Moving Average Distances & VWAP (Deep Negative Discount = Favorable for BUY; Extreme Extension = Favorable for SELL)
    for dma_col in ["Dist VWAP %", "Dist 20DMA %", "Dist 50DMA %", "Dist 100DMA %", "Dist 200DMA %"]:
        if dma_col in df.columns:
            top_buy_dma = df[dma_col].nsmallest(n_top).index
            top_sell_dma = df[dma_col].nlargest(n_top).index
            styles.loc[top_buy_dma, dma_col] = "background-color: #d4edda; color: #155724; font-weight: bold;"
            styles.loc[top_sell_dma, dma_col] = "background-color: #f8d7da; color: #721c24; font-weight: bold;"

    # 5. Distance from 52W Low % (Near Base < 6% = Favorable for BUY; Extended > 40% = Favorable for SELL)
    if "Dist 52W Low %" in df.columns:
        top_buy_52w = df["Dist 52W Low %"].nsmallest(n_top).index
        top_sell_52w = df["Dist 52W Low %"].nlargest(n_top).index
        styles.loc[top_buy_52w, "Dist 52W Low %"] = "background-color: #d4edda; color: #155724; font-weight: bold;"
        styles.loc[top_sell_52w, "Dist 52W Low %"] = "background-color: #f8d7da; color: #721c24; font-weight: bold;"

    # 6. Volume Surge Ratio (Surge > 1.5x = Green)
    if "Volume Surge Ratio" in df.columns:
        top_vol = df["Volume Surge Ratio"].nlargest(n_top).index
        styles.loc[top_vol, "Volume Surge Ratio"] = "background-color: #e0f2fe; color: #0369a1; font-weight: bold;"

    # 7. Relative Strength Spread 21D (Outperformance = Green)
    if "RS Spread 21D %" in df.columns:
        top_rs = df["RS Spread 21D %"].nlargest(n_top).index
        styles.loc[top_rs, "RS Spread 21D %"] = "background-color: #dcfce7; color: #15803d; font-weight: bold;"

    # 8. Dividend Yield % (Higher is Better for Long-Term Income & Value = Green)
    if "Dividend Yield %" in df.columns:
        top_div = df["Dividend Yield %"].nlargest(n_top).index
        styles.loc[top_div, "Dividend Yield %"] = "background-color: #dcfce7; color: #166534; font-weight: bold;"

    # 9. Guards Status Columns
    if "Falling Knife Guard" in df.columns:
        styles["Falling Knife Guard"] = df["Falling Knife Guard"].apply(
            lambda v: "background-color: #d4edda; color: #155724; font-weight: bold;" if "Safe" in str(v) else ("background-color: #f8d7da; color: #721c24; font-weight: bold;" if "Wait" in str(v) else "")
        )
    if "Structural Guard / iNAV" in df.columns:
        styles["Structural Guard / iNAV"] = df["Structural Guard / iNAV"].apply(
            lambda v: "background-color: #d4edda; color: #155724; font-weight: bold;" if "Healthy" in str(v) or "Clean" in str(v) else ("background-color: #f8d7da; color: #721c24; font-weight: bold;" if "Broken" in str(v) or "High Premium" in str(v) else "")
        )

    return styles

# =====================================================================
# TAB 1: TACTICAL SCREENER (TOP 3 BUY/SELL MATRIX + ENRICHED SCREENER)
# =====================================================================
if active_tab == "🎯 Tactical Screener & Ladder Planner":
    st.markdown("### 🎯 Tactical Screener & High-Conviction Matrix (V2)")

    m_col1, m_col2 = st.columns([3, 1])
    with m_col1:
        st.markdown(
            "##### 🌟 Dynamic High-Conviction Matrix &nbsp;<span style='font-size:0.80rem; font-weight:normal; color:#64748b;'>"
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
                f"<div style='font-size:0.82rem; font-weight:700; color:#1E88E5; border-bottom: 2px solid #1E88E5; padding-bottom: 2px; margin-bottom: 6px;'>"
                f"{cat_icon} {cat_name}</div>",
                unsafe_allow_html=True
            )

            # TOP 3 BUY
            st.markdown("<div style='font-size:0.74rem; font-weight:700; color:#155724; margin-bottom:3px;'>🟢 TOP 3 BUY (Dip Value)</div>", unsafe_allow_html=True)
            top_buy_df = category_picks[cat_name]["buy"]
            if top_buy_df is not None and not top_buy_df.empty:
                for rank_i, (_, t_row) in enumerate(top_buy_df.iterrows()):
                    sym = t_row["Ticker"]
                    freq = ticker_match_count.get(sym, 1)
                    if freq >= 3:
                        card_bg, card_border, match_tag = "#fff9e6", "#f59e0b", "<span style='font-size:0.65rem; color:#b45309; font-weight:700;'>★ Multi-Preset Leader</span>"
                    elif freq == 2:
                        card_bg, card_border, match_tag = "#f0f9ff", "#0284c7", "<span style='font-size:0.65rem; color:#0369a1; font-weight:700;'>◆ Dual Match</span>"
                    else:
                        card_bg, card_border, match_tag = "#ffffff", "#22c55e", ""

                    badge_info = f"Conf: {t_row.get('AI_Confidence_Score', '')}" if "AI" in cat_name else f"Score: {t_row.get('Composite Score', 0):.1f}"

                    st.markdown(
                        f"""
                        <div class="rec-card" style="background-color: {card_bg}; border: 1.2px solid {card_border};">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-weight:700; font-size:0.78rem;">#{rank_i+1} {sym}</span>
                                <span class="rec-badge" style="background-color: #d4edda; color: #155724;">BUY | {badge_info}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color:#475569; margin-top:2px;">
                                <span>₹{t_row['CMP (₹)']:.2f}</span>
                                <span>RSI: {t_row['RSI (14D)']:.1f}</span>
                                <span>Tgt: ₹{t_row['Target']:.1f}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.68rem; color:#64748b; margin-top:1px;">
                                <span>SL: ₹{t_row['Stop_Loss']:.1f}</span>
                                {match_tag}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.caption("No qualified setups.")

            # TOP 3 SELL
            st.markdown("<div style='font-size:0.74rem; font-weight:700; color:#721c24; margin-top:6px; margin-bottom:3px;'>🔴 TOP 3 SELL (Distribution)</div>", unsafe_allow_html=True)
            top_sell_df = category_picks[cat_name]["sell"]
            if top_sell_df is not None and not top_sell_df.empty:
                for rank_i, (_, t_row) in enumerate(top_sell_df.iterrows()):
                    sym = t_row["Ticker"]
                    freq = ticker_match_count.get(sym, 1)
                    if freq >= 3:
                        card_bg, card_border, match_tag = "#fff9e6", "#f59e0b", "<span style='font-size:0.65rem; color:#b45309; font-weight:700;'>★ Multi-Preset Leader</span>"
                    elif freq == 2:
                        card_bg, card_border, match_tag = "#f0f9ff", "#0284c7", "<span style='font-size:0.65rem; color:#0369a1; font-weight:700;'>◆ Dual Match</span>"
                    else:
                        card_bg, card_border, match_tag = "#ffffff", "#ef4444", ""

                    badge_info = f"Conf: {t_row.get('AI_Confidence_Score', '')}" if "AI" in cat_name else f"Score: {t_row.get('Composite Score', 0):.1f}"

                    st.markdown(
                        f"""
                        <div class="rec-card" style="background-color: {card_bg}; border: 1.2px solid {card_border};">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-weight:700; font-size:0.78rem;">#{rank_i+1} {sym}</span>
                                <span class="rec-badge" style="background-color: #f8d7da; color: #721c24;">SELL | {badge_info}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color:#475569; margin-top:2px;">
                                <span>₹{t_row['CMP (₹)']:.2f}</span>
                                <span>RSI: {t_row['RSI (14D)']:.1f}</span>
                                <span>Cover: ₹{t_row['Target']:.1f}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.68rem; color:#64748b; margin-top:1px;">
                                <span>Stop: ₹{t_row['Stop_Loss']:.1f}</span>
                                {match_tag}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.caption("No qualified setups.")

    st.markdown("---")

    # Interactive Screener Table with Depth and Category Filters
    v_col1, v_col2 = st.columns([1, 1])
    with v_col1:
        view_depth = st.radio("Screening Depth:", ["🎯 Top 10 High-Conviction (Default)", "⚡ Top 15 Ranked", f"🌐 Full Universe ({len(df_all)})"], horizontal=True)
    with v_col2:
        cat_filt = st.selectbox("Category Filter:", ["All"] + sorted(list(df_all["Category"].unique())) if not df_all.empty else ["All"])

    view_df = df_all.copy() if cat_filt == "All" else df_all[df_all["Category"] == cat_filt].copy()
    sorted_universe = view_df.sort_values(by="Composite Buy Score", ascending=True)
    display_slice = sorted_universe.head(10 if "Top 10" in view_depth else (15 if "Top 15" in view_depth else len(sorted_universe)))

    # Comprehensive Columns
    cols_show = [
        "Ticker", "Name", "Category", "CMP (₹)", "Dividend Yield %", "Dividend Status", "Composite Buy Score", "Technical Score", "Fundamental Score",
        "RSI (14D)", "RSI Delta", "Bollinger %B", "Dist VWAP %", "Dist 20DMA %", "Dist 50DMA %", "Dist 100DMA %", "Dist 200DMA %",
        "Dist 52W Low %", "Dist 52W High %", "Volume Surge Ratio", "RS Spread 21D %", "14D ATR (₹)", "ATR % of CMP",
        "Volatility Stop / Target", "Falling Knife Guard", "Structural Guard / iNAV"
    ]
    present_cols = [c for c in cols_show if c in display_slice.columns]

    # Explicit Tooltips explaining What Value is Better for BUY vs SELL
    screener_column_config = {
        "Ticker": st.column_config.TextColumn("Ticker", help="Instrument NSE ticker symbol.", pinned=True),
        "Name": st.column_config.TextColumn("Name", help="Instrument descriptive company or ETF fund name.", pinned=True),
        "Category": st.column_config.TextColumn("Category", help="Sectoral or asset class categorization.", pinned=True),
        "CMP (₹)": st.column_config.NumberColumn("CMP (₹)", format="₹%.2f", help="Current Market Price on National Stock Exchange.", pinned=True),
        "Dividend Yield %": st.column_config.NumberColumn(
            "Dividend Yield %", format="%.2f%%",
            help="💰 DIVIDEND YIELD %:\n• HIGHER IS BETTER FOR BUY (Income support, defensive value, and long-term compounding)\n• GREEN = Top 5 Highest Yielders"
        ),
        "Dividend Status": st.column_config.TextColumn(
            "Dividend Status",
            help="💰 DIVIDEND TIER:\n• High Yield (>= 3.0%)\n• Moderate (1.0 - 3.0%)\n• Growth / Low (< 1.0%)"
        ),
        "Composite Buy Score": st.column_config.NumberColumn(
            "Composite Buy Score", format="%.1f",
            help="🌟 COMPOSITE CONVICTION SCORE (0 - 100):\n• LOWER IS BETTER FOR BUY (Deep value, oversold confluence, high discount)\n• HIGHER IS BETTER FOR SELL (Overbought exhaustion, extreme extension)\n• TOP 5 BUY highlighted in GREEN | TOP 5 SELL highlighted in RED"
        ),
        "Technical Score": st.column_config.NumberColumn(
            "Technical Score", format="%.1f",
            help="📐 TECHNICAL RANK (0 - 100):\n• LOWER IS BETTER FOR BUY (Deep multi-timeframe oversold pullback)\n• HIGHER IS BETTER FOR SELL (Extended overbought momentum)"
        ),
        "Fundamental Score": st.column_config.NumberColumn(
            "Fundamental Score", format="%.1f",
            help="🏛️ FUNDAMENTAL / LIQUIDITY RANK (0 - 100):\n• LOWER IS BETTER FOR BUY (Superior turnover, lower expense ratio, minimal tracking error)\n• HIGHER IS BETTER FOR SELL (Illiquid or high friction)"
        ),
        "RSI (14D)": st.column_config.NumberColumn(
            "RSI (14D)", format="%.1f",
            help="📊 14-DAY RELATIVE STRENGTH INDEX:\n• LOWER IS BETTER FOR BUY (< 35 indicates deeply oversold capitulation)\n• HIGHER IS BETTER FOR SELL (> 65 indicates overbought distribution)\n• GREEN = Top 5 Lowest | RED = Top 5 Highest"
        ),
        "RSI Delta": st.column_config.NumberColumn(
            "RSI Delta", format="%+.2f",
            help="📈 1-Day change in RSI (Positive indicates bullish turning hook)."
        ),
        "Bollinger %B": st.column_config.NumberColumn(
            "Bollinger %B", format="%.2f",
            help="📉 BOLLINGER BAND POSITION:\n• LOWER IS BETTER FOR BUY (< 0.15 = Trading near or below lower 2-sigma band)\n• HIGHER IS BETTER FOR SELL (> 0.85 = Trading near or above upper 2-sigma band)"
        ),
        "Dist VWAP %": st.column_config.NumberColumn(
            "Dist VWAP %", format="%+.2f%%",
            help="📉 VOLUME WEIGHTED AVERAGE PRICE SPREAD:\n• LOWER / NEGATIVE IS BETTER FOR BUY (Discount below cumulative volume average)\n• HIGHER / POSITIVE IS BETTER FOR SELL (Premium above cumulative volume average)"
        ),
        "Dist 20DMA %": st.column_config.NumberColumn("Dist 20DMA %", format="%+.2f%%", help="Distance from 20-Day Moving Average. Negative = Dip; Positive = Extended."),
        "Dist 50DMA %": st.column_config.NumberColumn("Dist 50DMA %", format="%+.2f%%", help="Distance from 50-Day Moving Average. Negative = Deep pullback; Positive = Extended."),
        "Dist 100DMA %": st.column_config.NumberColumn("Dist 100DMA %", format="%+.2f%%", help="Distance from 100-Day Moving Average."),
        "Dist 200DMA %": st.column_config.NumberColumn(
            "Dist 200DMA %", format="%+.2f%%",
            help="🏛️ 200-DAY MOVING AVERAGE DISTANCE:\n• NEGATIVE = Structural discount test (High-probability institutional dip)\n• POSITIVE > +15% = Extended rally (Prone to mean-reversion)"
        ),
        "Dist 52W Low %": st.column_config.NumberColumn(
            "Dist 52W Low %", format="+%.2f%%",
            help="🛡️ DISTANCE FROM 52-WEEK LOW:\n• LOWER IS BETTER FOR BUY (< 6% indicates major structural base with tight risk)\n• HIGHER IS BETTER FOR SELL (> 40% indicates mature extended cycle)"
        ),
        "Dist 52W High %": st.column_config.NumberColumn(
            "Dist 52W High %", format="%+.2f%%",
            help="🚀 DISTANCE FROM 52-WEEK HIGH:\n• Closer to 0% = Strong momentum breakout candidates\n• Deeper negative = Value recovery potential"
        ),
        "Volume Surge Ratio": st.column_config.NumberColumn(
            "Volume Surge Ratio", format="%.2fx",
            help="🔥 TODAY'S VOLUME / 20D AVERAGE:\n• HIGHER IS BETTER FOR BUY CONFIRMATION (> 1.5x indicates institutional accumulation)"
        ),
        "RS Spread 21D %": st.column_config.NumberColumn(
            "RS Spread 21D %", format="%+.2f%%",
            help="⚡ RELATIVE STRENGTH SPREAD VS NIFTY 50 (21D):\n• HIGHER IS BETTER FOR BUY (Positive spread indicates alpha leadership outperforming index)"
        ),
        "14D ATR (₹)": st.column_config.NumberColumn("14D ATR (₹)", format="₹%.2f", help="14-Day Average True Range (Daily rupee volatility)."),
        "ATR % of CMP": st.column_config.NumberColumn("ATR % of CMP", format="%.2f%%", help="Volatility percentage of price."),
        "Falling Knife Guard": st.column_config.TextColumn("Falling Knife Guard", help="🟢 Reversal Hook (Safe to enter) vs ⚠️ Falling Knife (Wait for support)."),
        "Structural Guard / iNAV": st.column_config.TextColumn("Structural Guard / iNAV", help="Confirms whether stock is above 200DMA or ETF is trading clean of premium.")
    }

    render_top_scrollbar_sync()

    st.dataframe(
        display_slice[present_cols].style.apply(apply_advanced_table_styling, axis=None).format({
            "CMP (₹)": "₹{:.2f}",
            "Dividend Yield %": "{:.2f}%",
            "Composite Buy Score": "{:.1f}",
            "Technical Score": "{:.1f}",
            "Fundamental Score": "{:.1f}",
            "RSI (14D)": "{:.1f}",
            "RSI Delta": "{:+.2f}",
            "Bollinger %B": "{:.2f}",
            "Dist VWAP %": "{:+.2f}%",
            "Dist 20DMA %": "{:+.2f}%",
            "Dist 50DMA %": "{:+.2f}%",
            "Dist 100DMA %": "{:+.2f}%",
            "Dist 200DMA %": "{:+.2f}%",
            "Dist 52W Low %": "+{:.2f}%",
            "Dist 52W High %": "{:+.2f}%",
            "Volume Surge Ratio": "{:.2f}x",
            "RS Spread 21D %": "{:+.2f}%",
            "14D ATR (₹)": "₹{:.2f}",
            "ATR % of CMP": "{:.2f}%"
        }),
        column_config=screener_column_config,
        use_container_width=True,
        height=450
    )

# =====================================================================
# TAB 2: PAPER TRADING & MULTI-REGIME PERFORMANCE KPI LEDGER
# =====================================================================
elif active_tab == "📈 Paper Trading & Multi-Regime Ledger":
    raw_trades = load_paper_trades()
    trades_df = raw_trades.copy()

    st.markdown("### 📈 V2 Paper Trading Ledger & Multi-Regime Performance Hub")

    # Manual Trigger Test Expander
    with st.expander("⚡ Run Manual Strategy Routine Test", expanded=False):
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
            regime_name = regime_data.get("regime", "Normal")
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
                    created.append({
                        "Trade_ID": f"V2_INT_{int(datetime.datetime.now(IST).timestamp())}_{sym}", "Username": "Public_User", "Ticker": sym,
                        "Asset_Class": "Stock", "Trigger_Type": "MANUAL_INTRADAY", "Strategy_Preset": "Intraday",
                        "Status": "ACTIVE", "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                        "Stop_Loss": r["Stop_Loss"], "Target": r["Target"],
                        "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                        "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                        "Invested_Value": round(cmp_v * q, 2),
                        "Technical_Score_At_Entry": round(float(r.get("Technical Score", 50.0)), 1),
                        "Fundamental_Score_At_Entry": round(float(r.get("Fundamental Score", 50.0)), 1),
                        "RSI_At_Entry": round(float(r.get("RSI (14D)", 50.0)), 1),
                        "Composite_Score_At_Entry": round(float(r.get("Composite Score", r.get("Composite Buy Score", 50.0))), 1),
                        "Market_Regime_At_Entry": regime_name
                    })
                    active_syms.add(sym)

                etf_b, _ = get_top_conviction_candidates(etfs_market_df, preset_name="Intraday", is_stock_mode=False, limit=3)
                for _, r in etf_b.iterrows():
                    sym = str(r["Ticker"]).replace(".NS", "")
                    cmp_v = float(r["CMP (₹)"])
                    if sym in active_syms or cmp_v <= 0: continue
                    q = max(1, int(15000 // cmp_v))
                    created.append({
                        "Trade_ID": f"V2_INT_{int(datetime.datetime.now(IST).timestamp())}_{sym}", "Username": "Public_User", "Ticker": sym,
                        "Asset_Class": "ETF", "Trigger_Type": "MANUAL_INTRADAY", "Strategy_Preset": "Intraday",
                        "Status": "ACTIVE", "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                        "Stop_Loss": r["Stop_Loss"], "Target": r["Target"],
                        "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                        "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                        "Invested_Value": round(cmp_v * q, 2),
                        "Technical_Score_At_Entry": round(float(r.get("Technical Score", 50.0)), 1),
                        "Fundamental_Score_At_Entry": round(float(r.get("Fundamental Score", 50.0)), 1),
                        "RSI_At_Entry": round(float(r.get("RSI (14D)", 50.0)), 1),
                        "Composite_Score_At_Entry": round(float(r.get("Composite Score", r.get("Composite Buy Score", 50.0))), 1),
                        "Market_Regime_At_Entry": regime_name
                    })
                    active_syms.add(sym)

            elif "03:00" in exec_mode:
                ai_b, _ = get_ai_rag_conviction_candidates(stocks_market_df, is_stock_mode=True, limit=3)
                for _, r in ai_b.iterrows():
                    sym = str(r["Ticker"]).replace(".NS", "")
                    cmp_v = float(r["CMP (₹)"])
                    if sym in active_syms or cmp_v <= 0: continue
                    q = max(1, int(15000 // cmp_v))
                    created.append({
                        "Trade_ID": f"V2_AI_{int(datetime.datetime.now(IST).timestamp())}_{sym}", "Username": "Public_User", "Ticker": sym,
                        "Asset_Class": "Stock", "Trigger_Type": "AI_CONFLUENCE", "Strategy_Preset": "AI / RAG",
                        "Status": "ACTIVE", "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                        "Stop_Loss": r["Stop_Loss"], "Target": r["Target"],
                        "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                        "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                        "Invested_Value": round(cmp_v * q, 2),
                        "Technical_Score_At_Entry": round(float(r.get("Technical Score", 50.0)), 1),
                        "Fundamental_Score_At_Entry": round(float(r.get("Fundamental Score", 50.0)), 1),
                        "RSI_At_Entry": round(float(r.get("RSI (14D)", 50.0)), 1),
                        "Composite_Score_At_Entry": round(float(r.get("Composite Score", 50.0)), 1),
                        "Market_Regime_At_Entry": regime_name
                    })
                    active_syms.add(sym)

                for p in ["Default", "Long-Term", "Swing / Positional"]:
                    etf_b, _ = get_top_conviction_candidates(etfs_market_df, preset_name=p, is_stock_mode=False, limit=3)
                    for _, r in etf_b.iterrows():
                        sym = str(r["Ticker"]).replace(".NS", "")
                        cmp_v = float(r["CMP (₹)"])
                        if sym in active_syms or cmp_v <= 0: continue
                        q = max(1, int(15000 // cmp_v))
                        created.append({
                            "Trade_ID": f"V2_TR_{int(datetime.datetime.now(IST).timestamp())}_{sym}", "Username": "Public_User", "Ticker": sym,
                            "Asset_Class": "ETF", "Trigger_Type": "MANUAL_3PM", "Strategy_Preset": p,
                            "Status": "ACTIVE", "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                            "Stop_Loss": r["Stop_Loss"], "Target": r["Target"],
                            "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                            "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                            "Invested_Value": round(cmp_v * q, 2),
                            "Technical_Score_At_Entry": round(float(r.get("Technical Score", 50.0)), 1),
                            "Fundamental_Score_At_Entry": round(float(r.get("Fundamental Score", 50.0)), 1),
                            "RSI_At_Entry": round(float(r.get("RSI (14D)", 50.0)), 1),
                            "Composite_Score_At_Entry": round(float(r.get("Composite Score", 50.0)), 1),
                            "Market_Regime_At_Entry": regime_name
                        })
                        active_syms.add(sym)

                    stk_b, _ = get_top_conviction_candidates(stocks_market_df, preset_name=p, is_stock_mode=True, limit=3)
                    for _, r in stk_b.iterrows():
                        sym = str(r["Ticker"]).replace(".NS", "")
                        cmp_v = float(r["CMP (₹)"])
                        if sym in active_syms or cmp_v <= 0: continue
                        q = max(1, int(15000 // cmp_v))
                        created.append({
                            "Trade_ID": f"V2_TR_{int(datetime.datetime.now(IST).timestamp())}_{sym}", "Username": "Public_User", "Ticker": sym,
                            "Asset_Class": "Stock", "Trigger_Type": "MANUAL_3PM", "Strategy_Preset": p,
                            "Status": "ACTIVE", "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                            "Stop_Loss": r["Stop_Loss"], "Target": r["Target"],
                            "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                            "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                            "Invested_Value": round(cmp_v * q, 2),
                            "Technical_Score_At_Entry": round(float(r.get("Technical Score", 50.0)), 1),
                            "Fundamental_Score_At_Entry": round(float(r.get("Fundamental Score", 50.0)), 1),
                            "RSI_At_Entry": round(float(r.get("RSI (14D)", 50.0)), 1),
                            "Composite_Score_At_Entry": round(float(r.get("Composite Score", 50.0)), 1),
                            "Market_Regime_At_Entry": regime_name
                        })
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

    # Process and Render Exits & Active Positions
    if not trades_df.empty and "Status" in trades_df.columns:
        trades_df = evaluate_trade_exits(trades_df, active_raw_data)
        open_trades = trades_df[trades_df["Status"] == "ACTIVE"].copy()
        closed_trades = trades_df[trades_df["Status"] != "ACTIVE"].copy()

        cap_deployed = float(pd.to_numeric(open_trades["Invested_Value"], errors="coerce").sum()) if not open_trades.empty else 0.0
        tot_unrealized = float(pd.to_numeric(open_trades["PnL_Rs"], errors="coerce").sum()) if not open_trades.empty else 0.0
        closed_pnl = float(pd.to_numeric(closed_trades["PnL_Rs"], errors="coerce").sum()) if not closed_trades.empty else 0.0
        win_count = (pd.to_numeric(closed_trades["PnL_Rs"], errors="coerce") > 0).sum() if not closed_trades.empty else 0
        tot_closed = len(closed_trades)
        win_rate = (win_count / tot_closed * 100.0) if tot_closed > 0 else 0.0

        # Top Metric Cards
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Live Unrealized PnL", f"₹{tot_unrealized:+,.2f}", f"{len(open_trades)} Active Positions")
        m2.metric("Active Capital Deployed", f"₹{cap_deployed:,.2f}")
        m3.metric("Closed Realized PnL", f"₹{closed_pnl:+,.2f}", f"{tot_closed} Closed Trades")
        m4.metric("Strategy Win Rate", f"{win_rate:.1f}%" if tot_closed > 0 else "N/A", f"{win_count} Wins / {tot_closed - win_count} Losses")

        # =============================================================
        # MULTI-REGIME & MULTI-CATEGORY PERFORMANCE KPI MATRIX
        # =============================================================
        st.markdown("##### 📊 Multi-Regime & Category KPI Matrix")
        
        all_eval_trades = trades_df.copy()
        for req_col, default_v in [
            ("PnL_Rs", 0.0),
            ("Strategy_Preset", "Default"),
            ("Market_Regime_At_Entry", "Normal"),
            ("Status", "ACTIVE"),
            ("Hold_Duration_Days", 0)
        ]:
            if req_col not in all_eval_trades.columns:
                all_eval_trades[req_col] = default_v

        all_eval_trades["Clean_PnL"] = pd.to_numeric(all_eval_trades["PnL_Rs"], errors="coerce").fillna(0.0)
        all_eval_trades["Strategy_Preset"] = all_eval_trades["Strategy_Preset"].replace("", "Default").fillna("Default").astype(str)
        all_eval_trades["Market_Regime_At_Entry"] = all_eval_trades["Market_Regime_At_Entry"].replace("", "Normal").fillna("Normal").astype(str)
        all_eval_trades["Hold_Duration_Days"] = pd.to_numeric(all_eval_trades["Hold_Duration_Days"], errors="coerce").fillna(0)

        kpi_rows = []
        for (preset_name, regime_entry), grp in all_eval_trades.groupby(["Strategy_Preset", "Market_Regime_At_Entry"]):
            n_trades = len(grp)
            n_closed = len(grp[grp["Status"] != "ACTIVE"])
            c_grp = grp[grp["Status"] != "ACTIVE"]
            wins = (c_grp["Clean_PnL"] > 0).sum()
            losses = (c_grp["Clean_PnL"] < 0).sum()
            w_rate = (wins / n_closed * 100.0) if n_closed > 0 else 0.0
            gross_profit = c_grp[c_grp["Clean_PnL"] > 0]["Clean_PnL"].sum()
            gross_loss = abs(c_grp[c_grp["Clean_PnL"] < 0]["Clean_PnL"].sum())
            p_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (9.99 if gross_profit > 0 else 0.0)
            net_realized = c_grp["Clean_PnL"].sum()
            unrealized = grp[grp["Status"] == "ACTIVE"]["Clean_PnL"].sum()
            avg_hold = grp["Hold_Duration_Days"].mean()

            kpi_rows.append({
                "Strategy Preset": preset_name,
                "Market Regime": regime_entry,
                "Total Trades": n_trades,
                "Closed Trades": n_closed,
                "Win Rate %": f"{w_rate:.1f}%" if n_closed > 0 else "Pending",
                "Profit Factor": f"{p_factor:.2f}" if n_closed > 0 else "N/A",
                "Realized PnL (₹)": net_realized,
                "Unrealized PnL (₹)": unrealized,
                "Avg Hold (Days)": f"{avg_hold:.1f}"
            })

        if kpi_rows:
            kpi_df = pd.DataFrame(kpi_rows)
            st.dataframe(
                kpi_df.style.format({
                    "Realized PnL (₹)": "₹{:+,.2f}",
                    "Unrealized PnL (₹)": "₹{:+,.2f}"
                }),
                use_container_width=True
            )

        # Active Positions Table
        st.markdown("##### 📋 Open Active Positions (Live MTM)")
        if not open_trades.empty:
            open_cols = [
                "Trade_ID", "Ticker", "Asset_Class", "Strategy_Preset", "Entry_Price", "Live_CMP",
                "Executed_Qty", "Stop_Loss", "Target", "PnL_Rs", "PnL_Pct", "Hold_Duration_Days",
                "RSI_At_Entry", "Composite_Score_At_Entry", "Market_Regime_At_Entry"
            ]
            valid_open_cols = [c for c in open_cols if c in open_trades.columns]
            
            # Coerce numeric display columns safely
            open_display = open_trades[valid_open_cols].copy()
            for n_col in ["Entry_Price", "Live_CMP", "Stop_Loss", "Target", "PnL_Rs", "RSI_At_Entry", "Composite_Score_At_Entry"]:
                if n_col in open_display.columns:
                    open_display[n_col] = pd.to_numeric(open_display[n_col], errors="coerce").fillna(0.0)

            st.dataframe(
                open_display.style.format({
                    "Entry_Price": "₹{:.2f}",
                    "Live_CMP": "₹{:.2f}",
                    "Stop_Loss": "₹{:.2f}",
                    "Target": "₹{:.2f}",
                    "PnL_Rs": "₹{:+.2f}",
                    "RSI_At_Entry": "{:.1f}",
                    "Composite_Score_At_Entry": "{:.1f}"
                }),
                use_container_width=True
            )
        else:
            st.info("No active open positions in ledger.")

        # Closed Positions Table
        st.markdown("##### 📜 Closed Positions & Historical Exit Journal")
        if not closed_trades.empty:
            closed_cols = [
                "Trade_ID", "Ticker", "Asset_Class", "Strategy_Preset", "Status", "Exit_Reason",
                "Entry_Price", "Exit_Price", "Executed_Qty", "Hold_Duration_Days", "PnL_Rs", "PnL_Pct",
                "Execution_Timestamp", "Exit_Timestamp", "RSI_At_Entry", "Composite_Score_At_Entry", "Market_Regime_At_Entry"
            ]
            valid_closed_cols = [c for c in closed_cols if c in closed_trades.columns]

            closed_display = closed_trades[valid_closed_cols].copy()
            for n_col in ["Entry_Price", "Exit_Price", "PnL_Rs", "RSI_At_Entry", "Composite_Score_At_Entry"]:
                if n_col in closed_display.columns:
                    closed_display[n_col] = pd.to_numeric(closed_display[n_col], errors="coerce").fillna(0.0)

            st.dataframe(
                closed_display.style.format({
                    "Entry_Price": "₹{:.2f}",
                    "Exit_Price": "₹{:.2f}",
                    "PnL_Rs": "₹{:+.2f}",
                    "RSI_At_Entry": "{:.1f}",
                    "Composite_Score_At_Entry": "{:.1f}"
                }),
                use_container_width=True,
                height=220
            )
    else:
        st.info("No paper trades found. Run a manual strategy test above or let the scheduled cron populate orders.")

    # Execution Audit Log
    st.markdown("---")
    st.markdown("##### 📋 Execution Audit Log")
    aud_df = load_audit_log()
    if not aud_df.empty:
        st.dataframe(aud_df.sort_values(by="Timestamp_IST", ascending=False), use_container_width=True, height=160)

# =====================================================================
# TAB 3: AI QUANT ADVISOR (TRADE REVIEW & ONE-CLICK STRATEGY TUNER)
# =====================================================================
elif active_tab == "🤖 AI Quant Advisor & Strategy Tuner":
    st.markdown("### 🤖 V2 AI Quant Advisor & Strategy Optimization")
    st.caption("Empirically evaluates open/closed trades, computes historical win rates, and tunes runtime risk parameters.")

    sug_df = evaluate_strategy_performance_and_suggest_tweaks()

    ac1, ac2, ac3 = st.columns([2, 1, 1])
    with ac1:
        st.markdown(f"**Optimization Status:** `{runtime_cfg.get('optimization_status', 'Active')}`")
    with ac2:
        if st.button("🔄 Refresh Empirical Analysis", use_container_width=True):
            sug_df = evaluate_strategy_performance_and_suggest_tweaks()
            st.session_state.strategy_toast = "Refreshed recommendations."
            st.rerun()
    with ac3:
        if st.button("⚡ Apply Suggested Changes", use_container_width=True, type="primary"):
            res = apply_suggested_optimizations()
            st.success(f"Applied {len(res['changes'])} optimizations live!")
            st.cache_data.clear()
            st.rerun()

    st.markdown("##### 📊 Empirical Recommendations")
    st.dataframe(sug_df, use_container_width=True)

    with st.expander("🔬 View Active runtime_config.json", expanded=False):
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
# TAB 5: QUANT ECOSYSTEM & CRON-JOB.ORG SETUP GUIDE
# =====================================================================
elif active_tab == "🌐 Quant Ecosystem & Webhook Setup":
    st.markdown("### 🌐 External Cron & Webhook Integration (cron-job.org)")

    st.markdown(
        """
        #### ⏰ How to set up https://cron-job.org/en/ for Automated 3 PM & Intraday Trading

        You can use **cron-job.org** (100% free external cron service) to trigger this platform automatically on schedule.

        ---

        ##### Method 1: Direct Streamlit App Query Ping (No Webhook Server Needed!)
        If you host this app publicly on Streamlit Community Cloud (e.g. `https://your-app.streamlit.app`):
        1. Log in to [cron-job.org](https://cron-job.org/en/) and click **Create Cronjob**.
        2. Set **Title**: `AGY 3PM Accumulation`
        3. Set **URL**:
           ```text
           https://your-app.streamlit.app/?cron_trigger=1&mode=PAPER_TRADE_3PM&token=agy_quant_secure_token_2026
           ```
        4. Set **Schedule**:
           - **Days:** Monday, Tuesday, Wednesday, Thursday, Friday
           - **Time:** `15:00` (Timezone: `Asia/Kolkata`)
        5. Set **Request Method**: `GET`
        6. Click **Save**!

        Repeat for the other market routines:
        - **09:45 AM IST:** `https://your-app.streamlit.app/?cron_trigger=1&mode=INTRADAY_ENTRY&token=agy_quant_secure_token_2026`
        - **03:10 PM IST:** `https://your-app.streamlit.app/?cron_trigger=1&mode=INTRADAY_SQUAREOFF&token=agy_quant_secure_token_2026`

        ---

        ##### Method 2: HTTP POST via `cron_webhook.py` (For Render / VPS Hosting)
        If you run `cron_webhook.py` on Render, Railway, or your VPS:
        1. In [cron-job.org](https://cron-job.org/en/), set **Request Method** to `POST`.
        2. Set **URL**: `https://your-webhook-service.onrender.com/trigger`
        3. Under **Headers**, add:
           - Header: `Content-Type` &nbsp;|&nbsp; Value: `application/json`
        4. Under **Request Body**, enter:
           ```json
           {
             "mode": "PAPER_TRADE_3PM",
             "token": "agy_quant_secure_token_2026"
           }
           ```
        """
    )

    st.markdown("---")
    st.markdown("#### 📥 Official Platform Documentation (.docx)")
    st.write("Download the comprehensive architecture manual, quantitative scoring formulas, preset weights, exit logic, and cron-job setup instructions formatted for Microsoft Word:")

    tab5_docx_bytes = None
    if os.path.exists(DOCX_GUIDE_FILE):
        try:
            with open(DOCX_GUIDE_FILE, "rb") as f:
                tab5_docx_bytes = f.read()
        except Exception:
            pass
    elif generate_v2_docx_content:
        try:
            tab5_docx_bytes = generate_v2_docx_content()
        except Exception:
            pass

    if tab5_docx_bytes:
        st.download_button(
            label="📄 Download AGY Quant Platform Guide (Microsoft Word .docx)",
            data=tab5_docx_bytes,
            file_name="AGY_Quant_Platform_V2_Guide.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary",
            use_container_width=True
        )

# =====================================================================
# TAB 6: PARAMETER & WEIGHTS STUDIO (PUBLIC TESTBED)
# =====================================================================
elif active_tab == "🎛️ Parameter & Weights Studio":
    st.markdown("### 🎛️ Parameter & Weights Calibration Studio")
    st.caption("Centralized quant control studio: fine-tune strategy weights, ATR risk multipliers, execution schedules, review AI/RAG empirical calibrations, and audit monthly evolution.")

    # Refresh active config
    active_cfg = load_runtime_config()
    weights_dict = active_cfg.get("weights", {})
    risk_dict = active_cfg.get("risk_parameters", {})
    sched_dict = active_cfg.get("execution_schedule", {})
    is_weekdays_only = sched_dict.get("weekdays_only", True)

    # Status KPI Cards
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    with col_kpi1:
        st.metric("Strategy Version", active_cfg.get("parameter_version", "v2.2-Adaptive"))
    with col_kpi2:
        sched_badge = "🟢 Weekdays Only (Mon-Fri)" if is_weekdays_only else "🟡 All 7 Days Active"
        st.metric("Schedule Guard", sched_badge)
    with col_kpi3:
        st.metric("Last Optimization", active_cfg.get("last_optimized_timestamp", "Baseline"))
    with col_kpi4:
        st.metric("Testbed Mode", "🧪 Interactive Calibration Mode")

    st.markdown("---")

    # -------------------------------------------------------------
    # 1. AI/RAG STRATEGY PERFORMANCE REVIEW & AUTO-TUNER
    # -------------------------------------------------------------
    st.markdown("#### 🤖 AI/RAG Strategy Logic Review & Side-by-Side Recommendations")
    st.write(
        "The AI/RAG diagnostic engine analyzes empirical paper trades, identifies exit bottlenecks (whipsaw stop-outs, missed runner legs, low-momentum fills), "
        "and formulates optimized parameter suggestions side-by-side with your active settings."
    )

    ai_sug_df = generate_ai_rag_parameter_adjustments()

    # Action Toolbar
    act_col1, act_col2, act_col3 = st.columns([2, 1, 1])
    with act_col1:
        if st.button("⚡ One-Click Apply All AI/RAG Recommendations", type="primary", use_container_width=True):
            res = apply_all_ai_rag_recommendations(user="Testbed_User")
            st.session_state.strategy_toast = f"🟢 Applied {res['applied_count']} AI/RAG parameter adjustments!"
            st.cache_data.clear()
            st.rerun()

    with act_col2:
        if st.button("🔄 Re-Run Empirical Review", use_container_width=True):
            st.cache_data.clear()
            st.session_state.strategy_toast = "Empirical review refreshed."
            st.rerun()

    with act_col3:
        if st.button("🔄 Reset to Factory Baseline", use_container_width=True):
            reset_runtime_config_to_defaults(user="Testbed_User")
            st.session_state.strategy_toast = "Strategy reset to factory default baseline."
            st.cache_data.clear()
            st.rerun()

    # Display AI Comparison Table
    if not ai_sug_df.empty:
        st.dataframe(
            ai_sug_df[[
                "Parameter_Name", "Category", "Current_Value", "AI_Suggested_Value",
                "Delta", "Empirical_Rationale", "Intended_Impact"
            ]],
            use_container_width=True,
            height=280
        )
    else:
        st.info("No parameter adjustments suggested at this time. Current strategy logic is running at optimal calibration.")

    st.markdown("---")

    # -------------------------------------------------------------
    # 2. INTERACTIVE SLIDERS FOR MANUAL ADJUSTMENT
    # -------------------------------------------------------------
    st.markdown("#### 🎚️ Interactive Parameter Calibration Studio")
    st.caption("Adjust sliders directly in the GUI. All changes immediately take effect across the Screener, Paper Trader, and Daemon without modifying source code.")

    with st.form("manual_parameters_studio_form_v2"):
        # Section A: Strategy Preset Weights
        with st.expander("🎯 Strategy Preset Indicator Weights (0% - 100%)", expanded=True):
            st.caption("Relative weight assigned to each technical & fundamental factor when computing composite scores.")

            tab_p1, tab_p2, tab_p3, tab_p4, tab_p5 = st.tabs([
                "Default Preset", "Long-Term Preset", "Swing / Positional", "Intraday Preset", "AI / RAG Preset"
            ])

            new_weights = json.loads(json.dumps(weights_dict))

            with tab_p1:
                st.markdown("##### 📌 Default Baseline Preset")
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    w_dma_def = st.slider("200 DMA Distance (%)", 0, 100, int(weights_dict.get("Default", {}).get("w_dma", 35)), key="v2_s_def_dma")
                with c2:
                    w_rsi_def = st.slider("14D RSI Weight (%)", 0, 100, int(weights_dict.get("Default", {}).get("w_rsi", 30)), key="v2_s_def_rsi")
                with c3:
                    w_low_def = st.slider("52W Low Proximity (%)", 0, 100, int(weights_dict.get("Default", {}).get("w_low", 20)), key="v2_s_def_low")
                with c4:
                    w_exp_def = st.slider("Expense/Spread (%)", 0, 100, int(weights_dict.get("Default", {}).get("w_exp", 15)), key="v2_s_def_exp")
                new_weights["Default"] = {"w_dma": w_dma_def, "w_rsi": w_rsi_def, "w_low": w_low_def, "w_exp": w_exp_def}

            with tab_p2:
                st.markdown("##### 🏛️ Long-Term Secular Accumulation Preset")
                c1, c2, c3, c4, c5 = st.columns(5)
                with c1:
                    w_dma_lt = st.slider("200 DMA Trend (%)", 0, 100, int(weights_dict.get("Long-Term", {}).get("w_dma", 40)), key="v2_s_lt_dma")
                with c2:
                    w_div_lt = st.slider("Dividend Yield (%)", 0, 100, int(weights_dict.get("Long-Term", {}).get("w_div", 15)), key="v2_s_lt_div")
                with c3:
                    w_rsi_lt = st.slider("RSI Mean-Rev (%)", 0, 100, int(weights_dict.get("Long-Term", {}).get("w_rsi", 15)), key="v2_s_lt_rsi")
                with c4:
                    w_low_lt = st.slider("52W Low Proximity (%)", 0, 100, int(weights_dict.get("Long-Term", {}).get("w_low", 15)), key="v2_s_lt_low")
                with c5:
                    w_exp_lt = st.slider("Low Friction (%)", 0, 100, int(weights_dict.get("Long-Term", {}).get("w_exp", 15)), key="v2_s_lt_exp")
                new_weights["Long-Term"] = {"w_dma": w_dma_lt, "w_div": w_div_lt, "w_rsi": w_rsi_lt, "w_low": w_low_lt, "w_exp": w_exp_lt}

            with tab_p3:
                st.markdown("##### 🌊 Swing & Positional Reversal Preset")
                c1, c2, c3, c4, c5 = st.columns(5)
                with c1:
                    w_rsi_sw = st.slider("14D RSI Reversal (%)", 0, 100, int(weights_dict.get("Swing / Positional", {}).get("w_rsi", 30)), key="v2_s_sw_rsi")
                with c2:
                    w_dma_sw = st.slider("200 DMA Pullback (%)", 0, 100, int(weights_dict.get("Swing / Positional", {}).get("w_dma", 25)), key="v2_s_sw_dma")
                with c3:
                    w_bb_sw = st.slider("Bollinger %B (%)", 0, 100, int(weights_dict.get("Swing / Positional", {}).get("w_bb", 20)), key="v2_s_sw_bb")
                with c4:
                    w_vwap_sw = st.slider("VWAP Distance (%)", 0, 100, int(weights_dict.get("Swing / Positional", {}).get("w_vwap", 15)), key="v2_s_sw_vwap")
                with c5:
                    w_stoch_sw = st.slider("Stoch %K (%)", 0, 100, int(weights_dict.get("Swing / Positional", {}).get("w_stoch", 10)), key="v2_s_sw_stoch")
                new_weights["Swing / Positional"] = {"w_rsi": w_rsi_sw, "w_dma": w_dma_sw, "w_bb": w_bb_sw, "w_vwap": w_vwap_sw, "w_stoch": w_stoch_sw}

            with tab_p4:
                st.markdown("##### ⚡ Intraday Momentum & Scalping Preset")
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    w_vol_in = st.slider("Volume Surge Ratio (%)", 0, 100, int(weights_dict.get("Intraday", {}).get("w_vol", 35)), key="v2_s_in_vol")
                with c2:
                    w_rsi_in = st.slider("RSI Exhaustion (%)", 0, 100, int(weights_dict.get("Intraday", {}).get("w_rsi", 30)), key="v2_s_in_rsi")
                with c3:
                    w_bb_in = st.slider("Bollinger %B (%)", 0, 100, int(weights_dict.get("Intraday", {}).get("w_bb", 20)), key="v2_s_in_bb")
                with c4:
                    w_vwap_in = st.slider("VWAP Discount (%)", 0, 100, int(weights_dict.get("Intraday", {}).get("w_vwap", 15)), key="v2_s_in_vwap")
                new_weights["Intraday"] = {"w_vol": w_vol_in, "w_rsi": w_rsi_in, "w_bb": w_bb_in, "w_vwap": w_vwap_in}

            with tab_p5:
                st.markdown("##### 🤖 AI / RAG Multi-Factor Catalyst Preset")
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    w_rsi_ai = st.slider("Catalyst RSI (%)", 0, 100, int(weights_dict.get("AI / RAG", {}).get("w_rsi", 35)), key="v2_s_ai_rsi")
                with c2:
                    w_bb_ai = st.slider("Mean-Reversion %B (%)", 0, 100, int(weights_dict.get("AI / RAG", {}).get("w_bb", 25)), key="v2_s_ai_bb")
                with c3:
                    w_vol_ai = st.slider("Confluence Volume (%)", 0, 100, int(weights_dict.get("AI / RAG", {}).get("w_vol", 25)), key="v2_s_ai_vol")
                with c4:
                    w_macd_ai = st.slider("MACD Histogram (%)", 0, 100, int(weights_dict.get("AI / RAG", {}).get("w_macd", 15)), key="v2_s_ai_macd")
                new_weights["AI / RAG"] = {"w_rsi": w_rsi_ai, "w_bb": w_bb_ai, "w_vol": w_vol_ai, "w_macd": w_macd_ai}

        # Section B: Risk Parameters & Exit Rules
        with st.expander("🛡️ Risk Multipliers, Dynamic Trailing Stops & Exit Thresholds", expanded=True):
            st.caption("Volatility-based Stop-Loss (SL) and Profit Target ATR multipliers dynamically scaled to asset ATR.")

            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                st.markdown("##### ⚡ Intraday Trade Risk")
                in_sl = st.slider("Intraday SL (x ATR)", 0.5, 3.0, float(risk_dict.get("intraday_sl_multiplier", 1.0)), step=0.1, key="v2_in_sl")
                in_tgt = st.slider("Intraday Target (x ATR)", 1.0, 5.0, float(risk_dict.get("intraday_target_multiplier", 1.8)), step=0.1, key="v2_in_tgt")

            with rc2:
                st.markdown("##### 🌊 Swing Trade Risk")
                sw_sl = st.slider("Swing SL (x ATR)", 0.5, 4.0, float(risk_dict.get("swing_sl_multiplier", 1.5)), step=0.1, key="v2_sw_sl")
                sw_tgt = st.slider("Swing Target (x ATR)", 1.0, 8.0, float(risk_dict.get("swing_target_multiplier", 3.0)), step=0.1, key="v2_sw_tgt")

            with rc3:
                st.markdown("##### 🏛️ Long-Term Trade Risk")
                lt_sl = st.slider("Long-Term SL (x ATR)", 1.0, 5.0, float(risk_dict.get("longterm_sl_multiplier", 2.5)), step=0.1, key="v2_lt_sl")
                lt_tgt = st.slider("Long-Term Target (x ATR)", 2.0, 12.0, float(risk_dict.get("longterm_target_multiplier", 5.0)), step=0.1, key="v2_lt_tgt")

            st.markdown("##### 🔒 Dynamic Profit Lock & Exhaustion Exits")
            tc1, tc2, tc3, tc4 = st.columns(4)
            with tc1:
                trail_act = st.slider("Trailing Stop Trigger Gain (%)", 1.0, 8.0, float(risk_dict.get("trailing_stop_activation_pct", 3.0)), step=0.25, key="v2_tr_act")
            with tc2:
                trail_lock = st.slider("Guaranteed Profit Floor (%)", 0.1, 3.0, float(risk_dict.get("trailing_stop_lock_pct", 0.5)), step=0.1, key="v2_tr_lock")
            with tc3:
                ob_rsi = st.slider("Overbought RSI Exit Threshold", 65.0, 90.0, float(risk_dict.get("overbought_rsi_exit_threshold", 76.0)), step=0.5, key="v2_ob_rsi")
            with tc4:
                os_rsi = st.slider("Oversold Screener RSI Floor", 25.0, 50.0, float(risk_dict.get("oversold_rsi_buy_threshold", 38.0)), step=0.5, key="v2_os_rsi")

            new_risk = {
                "intraday_sl_multiplier": in_sl,
                "intraday_target_multiplier": in_tgt,
                "swing_sl_multiplier": sw_sl,
                "swing_target_multiplier": sw_tgt,
                "longterm_sl_multiplier": lt_sl,
                "longterm_target_multiplier": lt_tgt,
                "trailing_stop_activation_pct": trail_act,
                "trailing_stop_lock_pct": trail_lock,
                "overbought_rsi_exit_threshold": ob_rsi,
                "oversold_rsi_buy_threshold": os_rsi
            }

        # Section C: Automated Execution Schedule Controls
        with st.expander("⏱️ Automated Execution Schedule & Weekday Safeguards", expanded=True):
            st.caption("Controls automated background cron-job triggers and safeguards against holiday/weekend market execution.")

            sc1, sc2 = st.columns(2)
            with sc1:
                weekdays_toggle = st.checkbox(
                    "📅 Running Only on Weekdays (Mon - Fri)",
                    value=bool(sched_dict.get("weekdays_only", True)),
                    key="v2_wkdays_only",
                    help="When enabled, automated cron triggers on Saturday and Sunday are safely skipped and logged to prevent weekend drift."
                )
                enable_3pm = st.checkbox(
                    "🔔 Enable 3:00 PM Multi-Asset Accumulation Routine",
                    value=bool(sched_dict.get("enable_3pm_accumulation", True)),
                    key="v2_en_3pm",
                    help="Executes Top 3 BUY orders for both Stocks and ETFs during the closing liquidity window."
                )
            with sc2:
                enable_intra_entry = st.checkbox(
                    "🌅 Enable 9:45 AM High-Volume Morning Intraday Routine",
                    value=bool(sched_dict.get("enable_morning_intraday", True)),
                    key="v2_en_intra",
                    help="Scans for opening 45-minute volume breakouts."
                )
                enable_intra_sq = st.checkbox(
                    "🏁 Enable 3:10 PM Mandatory Intraday Auto-Squareoff",
                    value=bool(sched_dict.get("enable_afternoon_squareoff", True)),
                    key="v2_en_sq",
                    help="Guarantees all intraday positions are closed flat before exchange closing."
                )

            new_sched = {
                "weekdays_only": weekdays_toggle,
                "enable_3pm_accumulation": enable_3pm,
                "enable_morning_intraday": enable_intra_entry,
                "enable_afternoon_squareoff": enable_intra_sq
            }

        # Form Submit Button
        save_btn = st.form_submit_button("💾 Save Manual Parameter Adjustments", type="primary", use_container_width=True)

    if save_btn:
        save_res = save_manual_parameter_adjustments(new_weights, new_risk, new_sched, user="Testbed_User")
        st.session_state.strategy_toast = f"🟢 Saved manual adjustments ({save_res['updated_count']} parameters updated)!"
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")

    # -------------------------------------------------------------
    # 3. ALL PARAMETERS & DIRECTIONALITY SPECIFICATION MATRIX
    # -------------------------------------------------------------
    st.markdown("#### 📐 All Strategy Parameters & Edge Directionality Matrix")
    st.write(
        "Complete technical and quantitative reference explaining whether **higher or lower values** indicate a stronger BUY edge vs SELL edge, "
        "their default baselines, and intended market impact."
    )

    param_matrix_df = get_parameter_reference_matrix()

    # Filter by category
    all_cats = ["All Categories"] + list(param_matrix_df["Category"].unique())
    selected_cat = st.selectbox("Filter Parameters by Category:", all_cats, key="v2_cat_filter")

    if selected_cat != "All Categories":
        filtered_matrix = param_matrix_df[param_matrix_df["Category"] == selected_cat].reset_index(drop=True)
    else:
        filtered_matrix = param_matrix_df.reset_index(drop=True)

    st.dataframe(
        filtered_matrix[[
            "Category", "Parameter", "Current_Value", "Default_Value",
            "BUY_Edge_Direction", "SELL_Edge_Direction", "Intended_Market_Impact"
        ]],
        use_container_width=True,
        height=320
    )

    st.markdown("---")

    # -------------------------------------------------------------
    # 4. MONTH-OVER-MONTH PERFORMANCE & PARAMETER EVOLUTION
    # -------------------------------------------------------------
    st.markdown("#### 📅 Month-over-Month Performance & Parameter Tuning Comparison")
    st.write(
        "Tracks month-by-month historical trading performance against strategy parameter revisions. "
        "Review how algorithmic calibrations directly impacted Win Rate, Profit Factor, and Net Realized PnL."
    )

    monthly_perf_df = get_monthly_performance_comparison()

    if not monthly_perf_df.empty:
        st.dataframe(monthly_perf_df, use_container_width=True)
    else:
        st.info("ℹ️ Trade history is accumulating. As closed trades span multiple months, monthly performance comparison and evolution tracking will display here automatically.")

    st.markdown("---")

    # -------------------------------------------------------------
    # 5. PARAMETER CHANGE AUDIT LOG
    # -------------------------------------------------------------
    st.markdown("#### 📝 Strategy Parameter Change Audit Trail")
    st.caption("Immutable chronological record of every manual adjustment, AI auto-tune, and baseline reset.")

    param_change_log_df = load_parameter_change_log()
    if not param_change_log_df.empty:
        st.dataframe(
            param_change_log_df.sort_values(by="Timestamp_IST", ascending=False).reset_index(drop=True),
            use_container_width=True,
            height=240
        )
    else:
        st.info("No parameter adjustments logged yet. Initial adjustments will appear here.")

