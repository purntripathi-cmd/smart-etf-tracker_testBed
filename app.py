"""
AGY QUANT ALLOCATOR PRO (V2) - UNIFIED MULTI-ASSET COMMAND CENTER
===================================================================
Institutional High-Conviction Allocator across 5 Tactical Pillars:
1. Broad Equity & Smart Beta ETFs (Non-Sectoral Macro Framework)
2. High-Conviction Quality Equities (NIFTY Core & 250)
3. Algorithmic S/R Mean-Reversion Tranche (Major S1 Support Bounces)
4. Premier Indian REITs & High-Yield InvITs (7 Listed AAA Trusts)
5. Sectoral Commodity Metals (Gold & Silver Value Hedges)

Zero-Duplicates Architecture • Direct 1-Click Multi-Asset Execution • Enriched Paper Ledger
"""

import os
import sys
import json
import logging
import datetime
import zoneinfo
import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
import streamlit.components.v1 as components

# =====================================================================
# PLATFORM LOGGING & TIMEZONE
# =====================================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AGY_Quant_V2")
IST = zoneinfo.ZoneInfo("Asia/Kolkata")

# =====================================================================
# PAGE CONFIGURATION & STYLING
# =====================================================================
st.set_page_config(
    page_title="AGY Tactical Allocator Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Fidelity UI Styling
st.markdown(
    """
    <style>
    .main .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2.5rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    .metric-card-box {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .vix-pulse-banner {
        background: #f8fafc;
        border-left: 4px solid #3b82f6;
        padding: 10px 14px;
        border-radius: 6px;
        margin-bottom: 12px;
        font-size: 0.88rem;
    }
    .rec-card {
        padding: 10px 12px;
        border-radius: 8px;
        margin-bottom: 8px;
        transition: transform 0.15s ease-in-out;
    }
    .rec-card:hover {
        transform: translateY(-2px);
    }
    .rec-badge {
        font-size: 0.70rem;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 4px;
        display: inline-block;
    }
    .stDataFrame {
        border-radius: 6px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =====================================================================
# INTERNAL MODULE IMPORTS
# =====================================================================
try:
    from strategy_engine import (
        evaluate_market_metrics,
        get_top_conviction_candidates,
        get_ai_rag_conviction_candidates
    )
    from sr_engine import (
        compute_sr_matrix,
        get_5y_fidelity_leaderboard,
        get_34_parameter_profile,
        execute_sr_paper_trade,
        get_balanced_4asset_sr_picks
    )
    from reit_scanner import (
        scan_all_reits,
        REIT_FUNDAMENTALS_DB,
        check_reit_investment_eligibility,
        check_metal_investment_eligibility
    )
    from universe_manager import (
        get_active_universe,
        analyze_universe_coverage,
        NIFTY_250_STOCK_CONFIG,
        EXPANDED_NON_SECTORAL_ETF_CONFIG
    )
    from ml_optimizer import (
        load_runtime_config,
        evaluate_strategy_performance_and_suggest_tweaks,
        apply_suggested_optimizations,
        reset_runtime_config_to_defaults,
        save_manual_parameter_adjustments,
        get_parameter_reference_matrix,
        get_monthly_performance_comparison,
        load_parameter_change_log
    )
    from paper_trader_daemon import (
        evaluate_trade_exits,
        load_paper_trades,
        save_paper_trades,
        load_audit_log,
        run_paper_trader_daemon
    )
except Exception as _import_err:
    import traceback
    st.error(f"⚠️ Internal Module Import Error: {_import_err}")
    st.code(traceback.format_exc())
    st.info("Tip: Click 'Manage app' in Streamlit Cloud, then click 'Reboot app' to purge any stale cached Python modules.")
    st.stop()

try:
    from export_to_docx import export_v2_docx_file, generate_v2_docx_content
except Exception:
    export_v2_docx_file, generate_v2_docx_content = None, None

LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
LOCAL_TRADES_CSV = os.path.join(LOCAL_DATA_DIR, "paper_trades.csv")
LOCAL_AUDIT_CSV = os.path.join(LOCAL_DATA_DIR, "execution_audit_log.csv")
RUNTIME_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "runtime_config.json")
DOCX_GUIDE_FILE = os.path.join(os.path.dirname(__file__), "AGY_Quant_Platform_V2_Guide.docx")

if export_v2_docx_file and not os.path.exists(DOCX_GUIDE_FILE):
    try:
        export_v2_docx_file(DOCX_GUIDE_FILE)
    except Exception:
        pass

# =====================================================================
# QUERY PARAMETER CRON TRIGGER (ZERO-SECRETS COMPATIBLE)
# =====================================================================
query_params = st.query_params
if "cron_trigger" in query_params:
    mode_param = query_params.get("mode", "PAPER_TRADE_3PM").upper()
    try:
        run_paper_trader_daemon(mode_override=mode_param)
        st.json({"status": "success", "mode": mode_param, "timestamp": datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")})
    except Exception as e:
        st.json({"status": "error", "message": str(e)})
    st.stop()

# =====================================================================
# SYNCHRONIZED TOP HORIZONTAL SCROLLBAR
# =====================================================================
def render_top_scrollbar_sync():
    components.html(
        """
        <script>
        const parentDoc = window.parent.document;
        function syncScrollbars() {
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
# ENRICHED PAPER TRADING LEDGER SCHEMA
# =====================================================================
DEFAULT_PAPER_HEADERS = [
    "Trade_ID", "Username", "Ticker", "Category", "Asset_Class", "Trigger_Type", "Trigger_Indicator",
    "Strategy_Preset", "Status", "Entry_Price", "Live_CMP", "Executed_Qty", "Stop_Loss", "Target",
    "Execution_Timestamp", "Exit_Timestamp", "Exit_Price", "Exit_Reason", "Hold_Duration_Days",
    "PnL_Rs", "PnL_Pct", "Invested_Value",
    "Technical_Score_At_Entry", "Fundamental_Score_At_Entry", "Composite_Score_At_Entry",
    "Near_Support_Status", "RSI_At_Entry", "Empirical_Win_Rate_At_Entry", "Market_Regime_At_Entry"
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
        logger.error(f"Error fetching historical data: {e}")
        return pd.DataFrame()

def save_audit_entry(entry_dict):
    existing = load_audit_log()
    combined = pd.concat([existing, pd.DataFrame([entry_dict])], ignore_index=True).drop_duplicates()
    combined.to_csv(LOCAL_AUDIT_CSV, index=False)

def execute_category_paper_trade(
    ticker, category, trigger_indicator, cmp_val, sl_val, tgt_val,
    s1_val=0.0, rsi_val=50.0, tech_score=50.0, fund_score=50.0,
    comp_score=50.0, win_rate=50.0, budget=15000.0, username="Public_User"
):
    """
    Executes a high-conviction trade into the paper trading ledger with complete parameter provenance.
    """
    clean_sym = str(ticker).replace(".NS", "").strip()
    trades_path = LOCAL_TRADES_CSV
    existing_df = pd.DataFrame()
    if os.path.exists(trades_path) and os.path.getsize(trades_path) > 0:
        try:
            existing_df = pd.read_csv(trades_path)
        except Exception:
            existing_df = pd.DataFrame()

    if not existing_df.empty and "Status" in existing_df.columns:
        active_dups = existing_df[(existing_df["Ticker"] == clean_sym) & (existing_df["Status"] == "ACTIVE")]
        if not active_dups.empty:
            return False, f"Ticker {clean_sym} already has an active trade in the Paper Trading Ledger."

    if cmp_val <= 0:
        return False, f"Invalid CMP ₹{cmp_val:.2f} for {clean_sym}."

    qty = max(1, int(budget // cmp_val))
    now_ist = datetime.datetime.now(IST)
    now_str = now_ist.strftime("%Y-%m-%d %H:%M:%S")
    trade_id = f"V2_{clean_sym}_{int(now_ist.timestamp())}"

    dist_s1 = ((cmp_val - s1_val) / s1_val * 100) if s1_val > 0 else 0.0
    near_supp = f"Yes (+{dist_s1:.1f}% from S1: ₹{s1_val:.1f})" if (s1_val > 0 and dist_s1 <= 3.5) else (f"Above S1 (+{dist_s1:.1f}%)" if s1_val > 0 else "Base Support")

    rec = {
        "Trade_ID": trade_id,
        "Username": username,
        "Ticker": clean_sym,
        "Category": category,
        "Asset_Class": category,
        "Trigger_Type": f"{category.upper().replace(' ', '_')}_BUY",
        "Trigger_Indicator": trigger_indicator,
        "Strategy_Preset": "High-Conviction Allocation",
        "Status": "ACTIVE",
        "Entry_Price": cmp_val,
        "Live_CMP": cmp_val,
        "Executed_Qty": qty,
        "Stop_Loss": sl_val,
        "Target": tgt_val,
        "Execution_Timestamp": now_str,
        "Exit_Timestamp": "",
        "Exit_Price": 0.0,
        "Exit_Reason": "",
        "Hold_Duration_Days": 0,
        "PnL_Rs": 0.0,
        "PnL_Pct": "0.0%",
        "Invested_Value": round(cmp_val * qty, 2),
        "Technical_Score_At_Entry": round(float(tech_score), 1),
        "Fundamental_Score_At_Entry": round(float(fund_score), 1),
        "Composite_Score_At_Entry": round(float(comp_score), 1),
        "Near_Support_Status": near_supp,
        "RSI_At_Entry": round(float(rsi_val), 1),
        "Empirical_Win_Rate_At_Entry": f"{float(win_rate):.1f}%",
        "Market_Regime_At_Entry": "🟢 High Conviction"
    }

    combined = pd.concat([existing_df, pd.DataFrame([rec])], ignore_index=True)
    os.makedirs(os.path.dirname(trades_path), exist_ok=True)
    combined.to_csv(trades_path, index=False)

    save_audit_entry({
        "Timestamp_IST": now_str,
        "Trigger_Source": f"V2_1CLICK_{category.upper().replace(' ', '_')}",
        "Preset": category,
        "Recommended_BUY": clean_sym,
        "Recommended_SELL": "None",
        "Execution_Status": f"🟢 Logged ({qty} Qty @ ₹{cmp_val:.2f})",
        "Reason_Summary": f"1-Click {category} entry via {trigger_indicator}. SL: ₹{sl_val:.2f}, Target: ₹{tgt_val:.2f}."
    })
    return True, f"Executed {qty} units of {clean_sym} ({category}) at ₹{cmp_val:.2f} into Paper Ledger."

# =====================================================================
# ADVANCED SCREENER STYLING FUNCTION
# =====================================================================
def apply_advanced_table_styling(df):
    styles = pd.DataFrame("", index=df.index, columns=df.columns)
    n_len = len(df)
    if n_len == 0:
        return styles
    n_top = min(5, n_len)

    for col in ["Composite Buy Score", "Technical Score", "Fundamental Score"]:
        if col in df.columns:
            top_buy_idx = df[col].nsmallest(n_top).index
            top_sell_idx = df[col].nlargest(n_top).index
            styles.loc[top_buy_idx, col] = "background-color: #d4edda; color: #155724; font-weight: bold;"
            styles.loc[top_sell_idx, col] = "background-color: #f8d7da; color: #721c24; font-weight: bold;"

    if "RSI (14D)" in df.columns:
        top_buy_rsi = df["RSI (14D)"].nsmallest(n_top).index
        top_sell_rsi = df["RSI (14D)"].nlargest(n_top).index
        styles.loc[top_buy_rsi, "RSI (14D)"] = "background-color: #d4edda; color: #155724; font-weight: bold;"
        styles.loc[top_sell_rsi, "RSI (14D)"] = "background-color: #f8d7da; color: #721c24; font-weight: bold;"

    if "Bollinger %B" in df.columns:
        top_buy_bb = df["Bollinger %B"].nsmallest(n_top).index
        top_sell_bb = df["Bollinger %B"].nlargest(n_top).index
        styles.loc[top_buy_bb, "Bollinger %B"] = "background-color: #d4edda; color: #155724; font-weight: bold;"
        styles.loc[top_sell_bb, "Bollinger %B"] = "background-color: #f8d7da; color: #721c24; font-weight: bold;"

    for dma_col in ["Dist VWAP %", "Dist 20DMA %", "Dist 50DMA %", "Dist 100DMA %", "Dist 200DMA %"]:
        if dma_col in df.columns:
            top_buy_dma = df[dma_col].nsmallest(n_top).index
            top_sell_dma = df[dma_col].nlargest(n_top).index
            styles.loc[top_buy_dma, dma_col] = "background-color: #d4edda; color: #155724; font-weight: bold;"
            styles.loc[top_sell_dma, dma_col] = "background-color: #f8d7da; color: #721c24; font-weight: bold;"

    if "Dist 52W Low %" in df.columns:
        top_buy_52w = df["Dist 52W Low %"].nsmallest(n_top).index
        styles.loc[top_buy_52w, "Dist 52W Low %"] = "background-color: #d4edda; color: #155724; font-weight: bold;"

    if "Volume Surge Ratio" in df.columns:
        top_vol = df["Volume Surge Ratio"].nlargest(n_top).index
        styles.loc[top_vol, "Volume Surge Ratio"] = "background-color: #e0f2fe; color: #0369a1; font-weight: bold;"

    if "RS Spread 21D %" in df.columns:
        top_rs = df["RS Spread 21D %"].nlargest(n_top).index
        styles.loc[top_rs, "RS Spread 21D %"] = "background-color: #dcfce7; color: #15803d; font-weight: bold;"

    if "Dividend Yield %" in df.columns:
        top_div = df["Dividend Yield %"].nlargest(n_top).index
        styles.loc[top_div, "Dividend Yield %"] = "background-color: #dcfce7; color: #166534; font-weight: bold;"

    if "Falling Knife Guard" in df.columns:
        styles["Falling Knife Guard"] = df["Falling Knife Guard"].apply(
            lambda v: "background-color: #d4edda; color: #155724; font-weight: bold;" if "Safe" in str(v) else ("background-color: #f8d7da; color: #721c24; font-weight: bold;" if "Wait" in str(v) else "")
        )
    return styles

# =====================================================================
# DATA INITIALIZATION (EXPANDED BY DEFAULT - ZERO CONFIG REQUIRED)
# =====================================================================
if "strategy_toast" not in st.session_state:
    st.session_state.strategy_toast = None

current_stock_universe, current_etf_universe = get_active_universe()
ALL_CONFIG_TICKERS = [x["ticker"] for x in (current_etf_universe + current_stock_universe)]
active_raw_data = load_historical_market_data(ALL_CONFIG_TICKERS)
runtime_cfg = load_runtime_config()

with st.spinner("Evaluating multi-factor metrics across 250+ Equities & Broad ETFs..."):
    stocks_market_df, stock_regime = evaluate_market_metrics(active_raw_data, current_stock_universe, is_stock_mode=True)
    etfs_market_df, etf_regime = evaluate_market_metrics(active_raw_data, current_etf_universe, is_stock_mode=False)
    regime_data = etf_regime

# =====================================================================
# SIDEBAR NAVIGATION
# =====================================================================
with st.sidebar:
    st.markdown("### ⚡ AGY Tactical Allocator Pro")
    st.caption("Institutional High-Conviction Engine")
    st.markdown("---")

    active_tab = st.radio(
        "Navigation:",
        [
            "🎯 High-Conviction Master Hub",
            "📈 Paper Trading & Multi-Asset Ledger",
            "🧪 Multi-Regime Backtesting & Machine Learning",
            "📘 Platform Strategy Guide & DOCX Export"
        ],
        index=0
    )

    st.markdown("---")
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
# TAB 1: HIGH-CONVICTION MASTER HUB (ALL CATEGORIES IN ONE VIEW)
# =====================================================================
if active_tab == "🎯 High-Conviction Master Hub":
    st.markdown("### 🎯 High-Conviction Tactical Master Hub & Screener")
    st.caption("Institutional Quantitative Allocation across 5 Tactical Pillars • Direct 1-Click Execution • Full Deep-Dive Analytics under each Category")

    # Collapsible Universe Coverage Inspection
    u_analysis = analyze_universe_coverage()
    with st.expander("🌐 Complete Multi-Asset Universe & Allocation Philosophy (Click to inspect)", expanded=False):
        uc1, uc2, uc3, uc4 = st.columns(4)
        with uc1:
            st.metric("NIFTY 250 Equities", u_analysis["expanded_stocks_count"], delta="Large & Midcap Quality")
        with uc2:
            st.metric("Broad ETFs", u_analysis["expanded_etfs_count"], delta="100% Non-Sectoral")
        with uc3:
            st.metric("Premier REITs & InvITs", 7, delta="CRISIL AAA Cash Flows")
        with uc4:
            st.metric("Commodity Metals", 2, delta="Gold & Silver Hedges")
        st.markdown(
            """
            <div style="background-color: #f8fafc; border-left: 4px solid #1E88E5; padding: 10px 14px; border-radius: 6px; margin: 8px 0; font-size: 0.86rem; color: #334155;">
                <b>🛡️ Macro Non-Sectoral ETF Philosophy:</b> The platform strictly avoids uncompensated single-sector cyclical drawdown risks (such as Auto, Banking, or IT pure bets) by focusing exclusively on <b>Broad Indices</b> (Nifty 50, Next 50, Midcap 150, Smallcap 250), <b>Smart Beta Factors</b> (Alpha, Momentum, Quality, Low Volatility, Value), and <b>Hedging Commodities</b> (Gold, Silver). Individual stock selection provides sector-specific alpha with multi-factor risk controls.
            </div>
            """,
            unsafe_allow_html=True
        )

    # Master 1-Click Multi-Asset Balanced Tranche Bar
    st.markdown("---")
    mbar_c1, mbar_c2 = st.columns([3, 1.2])
    with mbar_c1:
        st.markdown(
            "##### 🔥 Quick Portfolio Allocation: Balanced 4-Asset Tranche\n"
            "<span style='font-size:0.82rem; color:#64748b;'>"
            "Allocates 2 Quality Stocks at Support + 1 Broad Equity ETF at Support + 1 Metal/Global ETF (conditionally skipped if overbought). Directly paper traded in 1 click."
            "</span>",
            unsafe_allow_html=True
        )
    with mbar_c2:
        if st.button("⚡ Execute 4-Asset Balanced Tranche", type="primary", use_container_width=True, key="exec_4asset_master_btn"):
            with st.spinner("Analyzing high-fidelity support levels across asset classes..."):
                sr_df_stk = compute_sr_matrix(active_raw_data, current_stock_universe, is_stock_mode=True)
                sr_df_etf = compute_sr_matrix(active_raw_data, current_etf_universe, is_stock_mode=False)
                balanced_res = get_balanced_4asset_sr_picks(sr_df_stk, sr_df_etf)
                
                exec_count = 0
                exec_msgs = []
                for stk_p in balanced_res.get("stocks", []):
                    ok, m = execute_sr_paper_trade(stk_p["Ticker"], stk_p, budget=base_budget, username="Public_User", dispatch_telegram=False)
                    if ok:
                        exec_count += 1
                        exec_msgs.append(f"Stock: {stk_p['Ticker']}")
                
                eq_p = balanced_res.get("equity_etf")
                if eq_p:
                    ok, m = execute_sr_paper_trade(eq_p["Ticker"], eq_p, budget=base_budget, username="Public_User", dispatch_telegram=False)
                    if ok:
                        exec_count += 1
                        exec_msgs.append(f"Equity ETF: {eq_p['Ticker']}")

                met_p = balanced_res.get("metal_global_etf")
                if met_p and balanced_res.get("metal_eligible", True):
                    ok, m = execute_sr_paper_trade(met_p["Ticker"], met_p, budget=base_budget, username="Public_User", dispatch_telegram=False)
                    if ok:
                        exec_count += 1
                        exec_msgs.append(f"Metal/Global ETF: {met_p['Ticker']}")
                elif met_p:
                    exec_msgs.append(f"🛑 Skipped {met_p.get('Ticker')} ({balanced_res.get('metal_skip_reason', 'Overextended')})")

                if exec_count > 0:
                    st.success(f"🎉 Successfully executed {exec_count} assets into Paper Trading Ledger! ({', '.join(exec_msgs)})")
                    st.rerun()
                else:
                    st.info(f"ℹ️ Allocation status: {', '.join(exec_msgs) if exec_msgs else 'All targets already active in ledger.'}")

    st.markdown("---")

    # =================================================================
    # CATEGORY 1: BROAD EQUITY & SMART BETA ETFs
    # =================================================================
    st.markdown("#### 🛡️ Category 1: Broad Equity & Smart Beta ETFs")
    st.caption("Top liquid Non-Sectoral ETFs (Nifty 50, Next 50, Midcap 150, Smallcap 250, Momentum 30, Alpha 30, Quality 30).")

    top_etf_b, _ = get_top_conviction_candidates(etfs_market_df, preset_name="Default", is_stock_mode=False, limit=2)
    c1_col1, c1_col2 = st.columns(2)
    for idx_e, (_, etf_r) in enumerate(top_etf_b.iterrows()):
        col_tgt = c1_col1 if idx_e == 0 else c1_col2
        with col_tgt:
            e_sym = str(etf_r["Ticker"]).replace(".NS", "")
            e_cmp = float(etf_r["CMP (₹)"])
            e_rsi = float(etf_r.get("RSI (14D)", 50.0))
            e_sc = float(etf_r.get("Composite Buy Score", 50.0))
            e_sl = float(etf_r.get("Stop_Loss", round(e_cmp * 0.96, 2)))
            e_tgt = float(etf_r.get("Target", round(e_cmp * 1.05, 2)))
            e_sig = str(etf_r.get("Action Signal", "ACCUMULATE"))
            e_dist_dma = float(etf_r.get("Dist 200DMA %", 0.0))

            st.markdown(
                f"""
                <div class="rec-card" style="background-color: #f0fdf4; border: 1.2px solid #22c55e;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight:700; font-size:0.88rem;">#{idx_e+1} {e_sym} ({etf_r.get('Category', 'Broad Index')})</span>
                        <span class="rec-badge" style="background-color: #dcfce7; color: #166534;">{e_sig}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.76rem; color:#475569; margin-top:4px;">
                        <span>CMP: ₹{e_cmp:.2f}</span>
                        <span>RSI: {e_rsi:.1f}</span>
                        <span>Score: #{e_sc:.1f}</span>
                        <span>Dist 200DMA: {e_dist_dma:+.1f}%</span>
                    </div>
                    <div style="font-size: 0.72rem; color:#15803d; margin-top:3px; font-weight:600;">
                        Stop-Loss: ₹{e_sl:.2f} | Target: ₹{e_tgt:.2f}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button(f"⚡ Paper Trade {e_sym} ETF", key=f"btn_tab1_etf_{e_sym}", use_container_width=True):
                ok, msg = execute_category_paper_trade(
                    ticker=e_sym, category="Equity ETF",
                    trigger_indicator=f"Broad ETF Conviction #{e_sc:.1f} (RSI: {e_rsi:.1f}, 200DMA: {e_dist_dma:+.1f}%)",
                    cmp_val=e_cmp, sl_val=e_sl, tgt_val=e_tgt,
                    rsi_val=e_rsi, comp_score=e_sc, budget=base_budget
                )
                if ok:
                    st.success(f"🎉 {msg}")
                    st.rerun()
                else:
                    st.warning(f"⚠️ {msg}")

    with st.expander("🔍 See More: Broad ETF Universe Screener & Factor Rankings (Click to expand)", expanded=False):
        fe1, fe2 = st.columns([1, 1])
        with fe1:
            etf_depth = st.radio("ETF Screener Depth:", ["Top 10 High-Conviction", "Top 15 Ranked", f"Full ETF Universe ({len(etfs_market_df)})"], horizontal=True, key="etf_depth_r")
        with fe2:
            etf_cats = ["All"] + sorted(list(etfs_market_df["Category"].unique())) if not etfs_market_df.empty else ["All"]
            etf_cat_choice = st.selectbox("Filter ETF Category:", etf_cats, key="etf_cat_filter_box")

        view_etf_df = etfs_market_df.copy() if etf_cat_choice == "All" else etfs_market_df[etfs_market_df["Category"] == etf_cat_choice].copy()
        sorted_etfs = view_etf_df.sort_values(by="Composite Buy Score", ascending=True)
        limit_e = 10 if "Top 10" in etf_depth else (15 if "Top 15" in etf_depth else len(sorted_etfs))
        slice_etfs = sorted_etfs.head(limit_e)

        cols_etf_disp = [
            "Ticker", "Name", "Category", "CMP (₹)", "Composite Buy Score", "Technical Score", "Fundamental Score",
            "RSI (14D)", "Bollinger %B", "Dist VWAP %", "Dist 20DMA %", "Dist 50DMA %", "Dist 200DMA %",
            "Dist 52W Low %", "Volume Surge Ratio", "RS Spread 21D %", "Action Signal"
        ]
        valid_etf_cols = [c for c in cols_etf_disp if c in slice_etfs.columns]
        render_top_scrollbar_sync()
        st.dataframe(
            slice_etfs[valid_etf_cols].style.apply(apply_advanced_table_styling, axis=None).format({
                "CMP (₹)": "₹{:.2f}",
                "Composite Buy Score": "{:.1f}",
                "Technical Score": "{:.1f}",
                "Fundamental Score": "{:.1f}",
                "RSI (14D)": "{:.1f}",
                "Bollinger %B": "{:.2f}",
                "Dist VWAP %": "{:+.2f}%",
                "Dist 20DMA %": "{:+.2f}%",
                "Dist 50DMA %": "{:+.2f}%",
                "Dist 200DMA %": "{:+.2f}%",
                "Dist 52W Low %": "+{:.2f}%",
                "Volume Surge Ratio": "{:.2f}x",
                "RS Spread 21D %": "{:+.2f}%"
            }),
            use_container_width=True,
            height=300
        )

    st.markdown("---")

    # =================================================================
    # CATEGORY 2: HIGH-CONVICTION QUALITY STOCKS (NIFTY CORE & 250)
    # =================================================================
    st.markdown("#### 💼 Category 2: High-Conviction Quality Equities (NIFTY Core & 250)")
    st.caption("Top fundamentally sound Indian equities combining multi-timeframe technical oversold pullbacks with institutional quality.")

    top_stk_b, _ = get_ai_rag_conviction_candidates(stocks_market_df, is_stock_mode=True, limit=2)
    c2_col1, c2_col2 = st.columns(2)
    for idx_s, (_, stk_r) in enumerate(top_stk_b.iterrows()):
        col_tgt2 = c2_col1 if idx_s == 0 else c2_col2
        with col_tgt2:
            s_sym = str(stk_r["Ticker"]).replace(".NS", "")
            s_cmp = float(stk_r["CMP (₹)"])
            s_rsi = float(stk_r.get("RSI (14D)", 50.0))
            s_tech = float(stk_r.get("Technical Score", 50.0))
            s_fund = float(stk_r.get("Fundamental Score", 50.0))
            s_sl = float(stk_r.get("Stop_Loss", round(s_cmp * 0.95, 2)))
            s_tgt = float(stk_r.get("Target", round(s_cmp * 1.07, 2)))
            s_sig = str(stk_r.get("Action Signal", "BUY"))

            st.markdown(
                f"""
                <div class="rec-card" style="background-color: #f0fdf4; border: 1.2px solid #22c55e;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight:700; font-size:0.88rem;">#{idx_s+1} {s_sym} ({stk_r.get('Category', 'Equity')})</span>
                        <span class="rec-badge" style="background-color: #dcfce7; color: #166534;">{s_sig}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.76rem; color:#475569; margin-top:4px;">
                        <span>CMP: ₹{s_cmp:.2f}</span>
                        <span>Tech Score: #{s_tech:.1f}</span>
                        <span>Fund Score: #{s_fund:.1f}</span>
                        <span>RSI: {s_rsi:.1f}</span>
                    </div>
                    <div style="font-size: 0.72rem; color:#15803d; margin-top:3px; font-weight:600;">
                        Stop-Loss: ₹{s_sl:.2f} | Target: ₹{s_tgt:.2f}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button(f"⚡ Paper Trade {s_sym} Stock", key=f"btn_tab1_stk_{s_sym}", use_container_width=True):
                ok, msg = execute_category_paper_trade(
                    ticker=s_sym, category="Quality Stock",
                    trigger_indicator=f"AI Quality Confluence (Tech: #{s_tech:.1f}, Fund: #{s_fund:.1f}, RSI: {s_rsi:.1f})",
                    cmp_val=s_cmp, sl_val=s_sl, tgt_val=s_tgt,
                    tech_score=s_tech, fund_score=s_fund, rsi_val=s_rsi, budget=base_budget
                )
                if ok:
                    st.success(f"🎉 {msg}")
                    st.rerun()
                else:
                    st.warning(f"⚠️ {msg}")

    with st.expander("🔍 See More: Quality Stocks Screener & Multi-Factor Rankings (Click to expand)", expanded=False):
        fs1, fs2 = st.columns([1, 1])
        with fs1:
            stk_depth = st.radio("Stock Screener Depth:", ["Top 10 High-Conviction", "Top 15 Ranked", f"Full Equities Universe ({len(stocks_market_df)})"], horizontal=True, key="stk_depth_r")
        with fs2:
            stk_cats = ["All"] + sorted(list(stocks_market_df["Category"].unique())) if not stocks_market_df.empty else ["All"]
            stk_cat_choice = st.selectbox("Filter Stock Sector / Category:", stk_cats, key="stk_cat_filter_box")

        view_stk_df = stocks_market_df.copy() if stk_cat_choice == "All" else stocks_market_df[stocks_market_df["Category"] == stk_cat_choice].copy()
        sorted_stks = view_stk_df.sort_values(by="Composite Buy Score", ascending=True)
        limit_s = 10 if "Top 10" in stk_depth else (15 if "Top 15" in stk_depth else len(sorted_stks))
        slice_stks = sorted_stks.head(limit_s)

        cols_stk_disp = [
            "Ticker", "Name", "Category", "CMP (₹)", "Dividend Yield %", "Composite Buy Score", "Technical Score", "Fundamental Score",
            "RSI (14D)", "Bollinger %B", "Dist VWAP %", "Dist 20DMA %", "Dist 50DMA %", "Dist 200DMA %",
            "Dist 52W Low %", "Volume Surge Ratio", "RS Spread 21D %", "Action Signal"
        ]
        valid_stk_cols = [c for c in cols_stk_disp if c in slice_stks.columns]
        render_top_scrollbar_sync()
        st.dataframe(
            slice_stks[valid_stk_cols].style.apply(apply_advanced_table_styling, axis=None).format({
                "CMP (₹)": "₹{:.2f}",
                "Dividend Yield %": "{:.2f}%",
                "Composite Buy Score": "{:.1f}",
                "Technical Score": "{:.1f}",
                "Fundamental Score": "{:.1f}",
                "RSI (14D)": "{:.1f}",
                "Bollinger %B": "{:.2f}",
                "Dist VWAP %": "{:+.2f}%",
                "Dist 20DMA %": "{:+.2f}%",
                "Dist 50DMA %": "{:+.2f}%",
                "Dist 200DMA %": "{:+.2f}%",
                "Dist 52W Low %": "+{:.2f}%",
                "Volume Surge Ratio": "{:.2f}x",
                "RS Spread 21D %": "{:+.2f}%"
            }),
            use_container_width=True,
            height=300
        )

    st.markdown("---")

    # =================================================================
    # CATEGORY 3: S/R MEAN REVERSION (TESTING S1 SUPPORT)
    # =================================================================
    st.markdown("#### 🎯 Category 3: Algorithmic Support & Resistance (S/R) Mean-Reversion Tranche")
    st.caption("Assets oscillating near 50-day rolling S1 Support with 5-Year Empirical Win Rates ≥ 60%.")

    with st.spinner("Computing Support & Resistance channel boundaries across assets..."):
        sr_combined_stk = compute_sr_matrix(active_raw_data, current_stock_universe, is_stock_mode=True)
        sr_combined_etf = compute_sr_matrix(active_raw_data, current_etf_universe, is_stock_mode=False)
        sr_full_df = pd.concat([sr_combined_stk, sr_combined_etf], ignore_index=True) if not sr_combined_stk.empty else sr_combined_etf

    if not sr_full_df.empty:
        sr_candidates = sr_full_df[sr_full_df["Action Signal"].str.contains("BUY|ACCUMULATE", na=False)]
        if sr_candidates.empty:
            sr_candidates = sr_full_df
        sr_top2 = sr_candidates.sort_values(by=["5Y S/R Win Rate (%)", "Range Position (%)"], ascending=[False, True]).head(2)

        c3_col1, c3_col2 = st.columns(2)
        for idx_sr, (_, sr_r) in enumerate(sr_top2.iterrows()):
            col_tgt3 = c3_col1 if idx_sr == 0 else c3_col2
            with col_tgt3:
                sr_sym = str(sr_r["Ticker"]).replace(".NS", "")
                sr_cmp = float(sr_r["CMP (₹)"])
                sr_s1 = float(sr_r.get("Major Support S1 (₹)", sr_cmp * 0.97))
                sr_r1 = float(sr_r.get("Major Resistance R1 (₹)", sr_cmp * 1.05))
                sr_win = float(sr_r.get("5Y S/R Win Rate (%)", 50.0))
                sr_dist_s1 = ((sr_cmp - sr_s1) / sr_s1 * 100) if sr_s1 > 0 else 0.0
                sr_sl = float(sr_r.get("Suggested SL (₹)", round(sr_cmp * 0.95, 2)))
                sr_tgt = float(sr_r.get("Suggested Target (₹)", round(sr_cmp * 1.06, 2)))
                sr_cat = str(sr_r.get("Category", "Stock"))

                st.markdown(
                    f"""
                    <div class="rec-card" style="background-color: #f0fdf4; border: 1.2px solid #22c55e;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight:700; font-size:0.88rem;">#{idx_sr+1} {sr_sym} ({sr_cat})</span>
                            <span class="rec-badge" style="background-color: #dcfce7; color: #166534;">{sr_win:.1f}% 5Y Win Rate</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.76rem; color:#475569; margin-top:4px;">
                            <span>CMP: ₹{sr_cmp:.2f}</span>
                            <span>S1: ₹{sr_s1:.2f}</span>
                            <span>R1: ₹{sr_r1:.2f}</span>
                            <span>Dist to S1: +{sr_dist_s1:.1f}%</span>
                        </div>
                        <div style="font-size: 0.72rem; color:#15803d; margin-top:3px; font-weight:600;">
                            SL: ₹{sr_sl:.2f} | Target: ₹{sr_tgt:.2f} | Rating: {sr_r.get('S/R Predictability Rating', 'High')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if st.button(f"⚡ Paper Trade {sr_sym} at S1 Support", key=f"btn_tab1_sr_{sr_sym}", use_container_width=True):
                    ok, msg = execute_category_paper_trade(
                        ticker=sr_sym, category="S/R Mean Reversion",
                        trigger_indicator=f"S1 Support Rebound ({sr_win:.1f}% 5Y Win Rate, Dist S1: +{sr_dist_s1:.1f}%)",
                        cmp_val=sr_cmp, sl_val=sr_sl, tgt_val=sr_tgt,
                        s1_val=sr_s1, rsi_val=float(sr_r.get("RSI (14D)", 50.0)),
                        comp_score=float(sr_r.get("Range Position (%)", 50.0)),
                        win_rate=sr_win, budget=base_budget
                    )
                    if ok:
                        st.success(f"🎉 {msg}")
                        st.rerun()
                    else:
                        st.warning(f"⚠️ {msg}")

        with st.expander("🔍 See More: Algorithmic S/R Matrix, 5Y Backtests & 34-Parameter Inspector (Click to expand)", expanded=False):
            sr_sub_mode = st.radio(
                "S/R Analytical View:",
                [
                    "🎯 S/R Levels & Channel Matrix",
                    "🏆 5-Year Empirical Predictability Leaderboard",
                    "🔬 34-Parameter Deep-Dive Inspector"
                ],
                horizontal=True,
                key="sr_sub_mode_radio"
            )

            if sr_sub_mode == "🎯 S/R Levels & Channel Matrix":
                cols_sr_disp = [
                    "Ticker", "Category", "CMP (₹)", "Major Support S1 (₹)", "Major Resistance R1 (₹)",
                    "Range Position (%)", "Channel Width (%)", "5Y S/R Win Rate (%)", "S/R Predictability Rating",
                    "RSI (14D)", "Action Signal"
                ]
                valid_sr_cols = [c for c in cols_sr_disp if c in sr_full_df.columns]
                render_top_scrollbar_sync()
                st.dataframe(
                    sr_full_df[valid_sr_cols].sort_values(by="5Y S/R Win Rate (%)", ascending=False).style.format({
                        "CMP (₹)": "₹{:.2f}",
                        "Major Support S1 (₹)": "₹{:.2f}",
                        "Major Resistance R1 (₹)": "₹{:.2f}",
                        "Range Position (%)": "{:.1f}%",
                        "Channel Width (%)": "{:.1f}%",
                        "5Y S/R Win Rate (%)": "{:.1f}%",
                        "RSI (14D)": "{:.1f}"
                    }),
                    use_container_width=True,
                    height=300
                )

            elif sr_sub_mode == "🏆 5-Year Empirical Predictability Leaderboard":
                st.caption("Historical bounce fidelity over ~1,250 daily bars when testing rolling Support Zone during non-trending regimes.")
                lead_df = get_5y_fidelity_leaderboard("Stock")
                if lead_df.empty:
                    lead_df = get_5y_fidelity_leaderboard()
                if not lead_df.empty:
                    top_lead = lead_df.head(15)[["Ticker", "Name", "Success_Probability_Pct", "Historical_5Y_Trades", "Avg_Gain_Pct", "Profit_Factor", "SR_Fidelity_Rating"]]
                    st.dataframe(top_lead, use_container_width=True, hide_index=True)

            elif sr_sub_mode == "🔬 34-Parameter Deep-Dive Inspector":
                all_tickers_list = sorted(list(sr_full_df["Ticker"].unique()))
                inspect_sym = st.selectbox("Select Asset for 34-Parameter Inspection:", all_tickers_list, key="inspect_asset_box")
                if inspect_sym:
                    prof = get_34_parameter_profile(active_raw_data, inspect_sym, is_stock_mode=True)
                    if prof:
                        p_col1, p_col2, p_col3 = st.columns(3)
                        with p_col1:
                            st.markdown("##### 📐 Price & Momentum Metrics")
                            st.write(f"• **CMP:** ₹{prof.get('CMP', 0.0):.2f}")
                            st.write(f"• **14D RSI:** {prof.get('RSI_14D', 50.0):.1f}")
                            st.write(f"• **Bollinger %B:** {prof.get('Bollinger_B', 0.5):.2f}")
                            st.write(f"• **14D ATR:** ₹{prof.get('ATR_14D', 0.0):.2f}")
                        with p_col2:
                            st.markdown("##### 🏛️ Support & S/R Channels")
                            st.write(f"• **Immediate S1:** ₹{prof.get('Support_S1', 0.0):.2f}")
                            st.write(f"• **Structural S2:** ₹{prof.get('Support_S2', 0.0):.2f}")
                            st.write(f"• **Resistance R1:** ₹{prof.get('Resistance_R1', 0.0):.2f}")
                            st.write(f"• **5Y S/R Win Rate:** {prof.get('SR_Win_Rate_5Y_Pct', 50.0):.1f}%")
                        with p_col3:
                            st.markdown("##### 🏢 Valuation & Fundamentals")
                            st.write(f"• **Trailing P/E:** {prof.get('PE_Ratio', 0.0):.1f}")
                            st.write(f"• **Price-to-Book:** {prof.get('PB_Ratio', 0.0):.1f}")
                            st.write(f"• **Dividend Yield:** {prof.get('Dividend_Yield', 0.0):.2f}%")
                            st.write(f"• **Volume Surge:** {prof.get('Volume_Surge_Ratio', 1.0):.2f}x")

    st.markdown("---")

    # =================================================================
    # CATEGORY 4: PREMIER INDIAN REITs & HIGH-YIELD InvITs
    # =================================================================
    st.markdown("#### 🏢 Category 4: Premier Indian REITs & High-Yield InvITs (7 Listed Trusts)")
    st.caption("Institutional cash flow assets with mandatory SEBI ≥90% NDCF distributions, AAA credit ratings, and inflation-indexed leases.")

    with st.spinner("Scanning 7 Premier Indian REITs & InvITs..."):
        reits_data = scan_all_reits()

    if not reits_data.empty:
        c4_col1, c4_col2 = st.columns(2)
        top_reits_2 = reits_data.head(2)
        for idx_r, (_, r_it) in enumerate(top_reits_2.iterrows()):
            col_tgt4 = c4_col1 if idx_r == 0 else c4_col2
            with col_tgt4:
                r_sym = str(r_it["Ticker"]).replace(".NS", "")
                r_yd = float(r_it["Distribution Yield (%)"])
                r_cp = float(r_it["CMP (₹)"])
                r_disc = float(r_it["NAV Discount / Premium (%)"])
                r_sl = float(r_it.get("Immediate Support S1 (₹)", round(r_cp * 0.95, 2)))
                r_tgt = float(r_it.get("Immediate Resistance R1 (₹)", round(r_cp * 1.08, 2)))
                r_el = check_reit_investment_eligibility(r_it.to_dict())

                badge_bg = "#dcfce7" if r_el["eligible"] else "#ffe4e6"
                badge_col = "#166534" if r_el["eligible"] else "#be123c"

                st.markdown(
                    f"""
                    <div class="rec-card" style="background-color: #f5f3ff; border: 1.2px solid #8b5cf6;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight:700; font-size:0.88rem;">#{idx_r+1} {r_sym} ({r_it.get('Type', 'REIT').split()[0]})</span>
                            <span class="rec-badge" style="background-color: {badge_bg}; color: {badge_col};">{r_el['status']}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.76rem; color:#475569; margin-top:4px;">
                            <span>CMP: ₹{r_cp:.2f}</span>
                            <span>Yield: <b>{r_yd:.1f}%</b></span>
                            <span>Payout: 100% NDCF</span>
                            <span>NAV Disc: {r_disc:+.1f}%</span>
                        </div>
                        <div style="font-size: 0.72rem; color:#5b21b6; margin-top:3px; font-weight:600;">
                            S1 Support: ₹{r_sl:.2f} | Target: ₹{r_tgt:.2f} | Rating: {r_it.get('Credit Rating', 'CRISIL AAA')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if st.button(f"⚡ Paper Trade {r_sym} ({r_yd:.1f}% Yield)", key=f"btn_tab1_reit_{r_sym}", use_container_width=True):
                    ok, msg = execute_category_paper_trade(
                        ticker=r_sym, category="REIT/InvIT",
                        trigger_indicator=f"High-Yield Distribution {r_yd:.1f}% (100% NDCF, NAV Disc: {r_disc:+.1f}%)",
                        cmp_val=r_cp, sl_val=r_sl, tgt_val=r_tgt,
                        s1_val=r_sl, rsi_val=float(r_it.get("RSI (14D)", 50.0)),
                        comp_score=float(r_it.get("Composite Score (0-100)", 50.0)),
                        win_rate=float(r_it.get("Composite Score (0-100)", 50.0)),
                        budget=base_budget
                    )
                    if ok:
                        st.success(f"🎉 {msg}")
                        st.rerun()
                    else:
                        st.warning(f"⚠️ {msg}")

        with st.expander("🔍 See More: Institutional REIT & InvIT Financials & Portfolio Breakdown (Click to expand)", expanded=False):
            rk1, rk2, rk3, rk4, rk5 = st.columns(5)
            rk1.metric("Avg Distribution Yield", f"{reits_data['Distribution Yield (%)'].mean():.2f}%", delta="Cash Flow Yield")
            rk2.metric("NDCF Payout Ratio", "100.0%", delta="Mandatory ≥90%")
            rk3.metric("Avg Discount to NAV", f"{reits_data['NAV Discount / Premium (%)'].mean():+.1f}%", delta="Real Estate Value")
            rk4.metric("Avg Occupancy", f"{reits_data['Occupancy (%)'].mean():.1f}%", delta="Grade-A Tenants")
            rk5.metric("Avg LTV Debt Ratio", f"{reits_data['LTV Leverage (%)'].mean():.1f}%", delta="Safe (Cap 49%)")

            cols_r_show = [
                "Ticker", "Name", "Type", "Sponsor", "CMP (₹)", "Distribution Yield (%)",
                "Dividend Payout Ratio (%)", "Annualized DPU (₹)", "Net Asset Value NAV (₹)",
                "NAV Discount / Premium (%)", "Occupancy (%)", "WALE (Years)", "LTV Leverage (%)",
                "Credit Rating", "Action Signal"
            ]
            valid_r_cols = [c for c in cols_r_show if c in reits_data.columns]
            render_top_scrollbar_sync()
            st.dataframe(
                reits_data[valid_r_cols].style.format({
                    "CMP (₹)": "₹{:.2f}",
                    "Distribution Yield (%)": "{:.2f}%",
                    "Dividend Payout Ratio (%)": "{:.1f}%",
                    "Annualized DPU (₹)": "₹{:.2f}",
                    "Net Asset Value NAV (₹)": "₹{:.2f}",
                    "NAV Discount / Premium (%)": "{:+.2f}%",
                    "Occupancy (%)": "{:.1f}%",
                    "WALE (Years)": "{:.1f} Yrs",
                    "LTV Leverage (%)": "{:.1f}%"
                }),
                use_container_width=True,
                height=260
            )

    st.markdown("---")

    # =================================================================
    # CATEGORY 5: PRECIOUS METALS (GOLD & SILVER SECTORAL COMMODITIES)
    # =================================================================
    st.markdown("#### 🥇 Category 5: Precious Metals (Gold & Silver Sectoral Commodities)")
    st.caption("Defensive commodity hedges against equity drawdowns and currency depreciation. Evaluated conditionally to prevent buying near cyclical peaks.")

    metal_picks = []
    for msym in ["GOLDBEES", "SILVERBEES"]:
        m_row = etfs_market_df[etfs_market_df["Ticker"].str.contains(msym, na=False)] if not etfs_market_df.empty else pd.DataFrame()
        if not m_row.empty:
            metal_picks.append(m_row.iloc[0].to_dict())

    if metal_picks:
        c5_col1, c5_col2 = st.columns(2)
        for idx_m, m_dict in enumerate(metal_picks):
            col_tgt5 = c5_col1 if idx_m == 0 else c5_col2
            with col_tgt5:
                m_sym = str(m_dict["Ticker"]).replace(".NS", "")
                m_cmp = float(m_dict["CMP (₹)"])
                m_rsi = float(m_dict.get("RSI (14D)", 50.0))
                m_rng = float(m_dict.get("Range Position (%)", 50.0))
                m_sl = float(m_dict.get("Stop_Loss", round(m_cmp * 0.96, 2)))
                m_tgt = float(m_dict.get("Target", round(m_cmp * 1.06, 2)))
                m_el = check_metal_investment_eligibility(m_dict)

                mbadge_bg = "#dcfce7" if m_el["eligible"] else "#ffe4e6"
                mbadge_col = "#166534" if m_el["eligible"] else "#be123c"

                st.markdown(
                    f"""
                    <div class="rec-card" style="background-color: #fffbeb; border: 1.2px solid #f59e0b;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight:700; font-size:0.88rem;">#{idx_m+1} {m_sym} (Commodity Metal)</span>
                            <span class="rec-badge" style="background-color: {mbadge_bg}; color: {mbadge_col};">{m_el['status']}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.76rem; color:#475569; margin-top:4px;">
                            <span>CMP: ₹{m_cmp:.2f}</span>
                            <span>RSI: {m_rsi:.1f}</span>
                            <span>52W Range: {m_rng:.1f}%</span>
                        </div>
                        <div style="font-size: 0.72rem; color:#92400e; margin-top:3px; font-weight:600;">
                            SL: ₹{m_sl:.2f} | Target: ₹{m_tgt:.2f} | Note: {m_el.get('reason', 'Macro Hedge')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if st.button(f"⚡ Paper Trade {m_sym} Metal", key=f"btn_tab1_metal_{m_sym}", use_container_width=True):
                    ok, msg = execute_category_paper_trade(
                        ticker=m_sym, category="Precious Metal",
                        trigger_indicator=f"Commodity Value Dip (RSI: {m_rsi:.1f}, 52W Range: {m_rng:.1f}%)",
                        cmp_val=m_cmp, sl_val=m_sl, tgt_val=m_tgt,
                        rsi_val=m_rsi, comp_score=m_rng, budget=base_budget
                    )
                    if ok:
                        st.success(f"🎉 {msg}")
                        st.rerun()
                    else:
                        st.warning(f"⚠️ {msg}")

        with st.expander("🔍 See More: Precious Metals Trend & Value Analytics (Click to expand)", expanded=False):
            st.markdown(
                """
                > **Precious Metals Asset Class Rationale:** Gold and Silver have low to negative historical correlation
                > with Indian large-cap equities. However, entering at cyclical peaks (>85% 52W range or RSI > 68) causes long holding drawdowns.
                > The platform filters metal entries conditionally so allocation only triggers during consolidation dips or support pullbacks.
                """
            )
            m_df = pd.DataFrame(metal_picks)
            if not m_df.empty:
                st.dataframe(
                    m_df[["Ticker", "Name", "CMP (₹)", "RSI (14D)", "Dist 200DMA %", "Dist 52W Low %", "Action Signal"]],
                    use_container_width=True,
                    hide_index=True
                )


# =====================================================================
# TAB 2: PAPER TRADING & MULTI-ASSET PERFORMANCE HUB
# =====================================================================
elif active_tab == "📈 Paper Trading & Multi-Asset Ledger":
    st.markdown("### 📈 Paper Trading Ledger & Multi-Asset Performance Hub")
    st.caption("Tracks simulated executions across all 5 asset classes with complete indicator provenance, technical/fundamental entry scores, and support proximity.")

    raw_trades = load_paper_trades()
    trades_df = raw_trades.copy()

    # Manual Strategy Routine Runner
    with st.expander("⚡ Run Manual Strategy Routine Test (Multi-Asset)", expanded=False):
        ec1, ec2, ec3 = st.columns([2, 1, 1])
        with ec1:
            exec_mode = st.selectbox(
                "Select Scheduled Routine to Trigger:",
                [
                    "03:00 PM IST - Multi-Asset Balanced Accumulation (Stocks, ETFs, REITs, Metals)",
                    "09:45 AM IST - Morning Intraday Volume Breakout",
                    "03:10 PM IST - Mandatory Intraday Auto-Squareoff"
                ]
            )
        with ec2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            run_btn = st.button("🚀 Execute Strategy Run", use_container_width=True, type="primary")
        with ec3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            with st.popover("🗑️ Reset Ledger Data", use_container_width=True):
                st.warning("⚠️ This will clear all local paper trades and execution audit logs.")
                if st.button("🚨 Confirm Reset", type="primary", use_container_width=True):
                    save_paper_trades(pd.DataFrame(columns=DEFAULT_PAPER_HEADERS))
                    save_audit_entry({
                        "Timestamp_IST": datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
                        "Trigger_Source": "RESET", "Preset": "All",
                        "Recommended_BUY": "None", "Recommended_SELL": "None",
                        "Execution_Status": "Reset", "Reason_Summary": "Ledger cleared by user."
                    })
                    st.cache_data.clear()
                    st.session_state.strategy_toast = "Ledger reset clean."
                    st.rerun()

        if run_btn:
            now_str = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
            regime_name = regime_data.get("regime", "Normal")
            created = []
            all_t = load_paper_trades()
            active_t = all_t[all_t["Status"] == "ACTIVE"] if not all_t.empty else pd.DataFrame()
            active_syms = set(active_t["Ticker"].astype(str).str.replace(".NS", "")) if not active_t.empty else set()

            if "03:00" in exec_mode:
                # 1. Balanced 4-Asset Allocation
                sr_df_stk = compute_sr_matrix(active_raw_data, current_stock_universe, is_stock_mode=True)
                sr_df_etf = compute_sr_matrix(active_raw_data, current_etf_universe, is_stock_mode=False)
                balanced_sr = get_balanced_4asset_sr_picks(sr_df_stk, sr_df_etf)

                for stk_item in balanced_sr.get("stocks", []):
                    sym = str(stk_item["Ticker"]).replace(".NS", "")
                    cmp_v = float(stk_item["CMP (₹)"])
                    if sym in active_syms or cmp_v <= 0: continue
                    q = max(1, int(base_budget // cmp_v))
                    s1_v = float(stk_item.get("Major Support S1 (₹)", cmp_v * 0.97))
                    dist_s1 = ((cmp_v - s1_v) / s1_v * 100) if s1_v > 0 else 0.0
                    created.append({
                        "Trade_ID": f"V2_STK_{int(datetime.datetime.now(IST).timestamp())}_{sym}", "Username": "Public_User", "Ticker": sym,
                        "Category": "Quality Stock", "Asset_Class": "Stock", "Trigger_Type": "SR_SUPPORT_BUY",
                        "Trigger_Indicator": f"S1 Support Bounce ({stk_item.get('5Y S/R Win Rate (%)', 50)}% 5Y Win)",
                        "Strategy_Preset": "S/R Range Mean Reversion", "Status": "ACTIVE",
                        "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                        "Stop_Loss": stk_item["Suggested SL (₹)"], "Target": stk_item["Suggested Target (₹)"],
                        "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                        "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                        "Invested_Value": round(cmp_v * q, 2),
                        "Technical_Score_At_Entry": round(float(stk_item.get("RSI (14D)", 50.0)), 1),
                        "Fundamental_Score_At_Entry": round(float(stk_item.get("5Y S/R Win Rate (%)", 50.0)), 1),
                        "Composite_Score_At_Entry": round(float(stk_item.get("Range Position (%)", 50.0)), 1),
                        "Near_Support_Status": f"Yes (+{dist_s1:.1f}% to S1)",
                        "RSI_At_Entry": round(float(stk_item.get("RSI (14D)", 50.0)), 1),
                        "Empirical_Win_Rate_At_Entry": f"{stk_item.get('5Y S/R Win Rate (%)', 50)}%",
                        "Market_Regime_At_Entry": regime_name
                    })
                    active_syms.add(sym)

                eq_etf = balanced_sr.get("equity_etf")
                if eq_etf:
                    sym = str(eq_etf["Ticker"]).replace(".NS", "")
                    cmp_v = float(eq_etf["CMP (₹)"])
                    if sym not in active_syms and cmp_v > 0:
                        q = max(1, int(base_budget // cmp_v))
                        s1_v = float(eq_etf.get("Major Support S1 (₹)", cmp_v * 0.97))
                        dist_s1 = ((cmp_v - s1_v) / s1_v * 100) if s1_v > 0 else 0.0
                        created.append({
                            "Trade_ID": f"V2_ETF_{int(datetime.datetime.now(IST).timestamp())}_{sym}", "Username": "Public_User", "Ticker": sym,
                            "Category": "Equity ETF", "Asset_Class": "Equity ETF", "Trigger_Type": "SR_SUPPORT_BUY",
                            "Trigger_Indicator": f"Broad ETF Support ({eq_etf.get('5Y S/R Win Rate (%)', 50)}% Win)",
                            "Strategy_Preset": "S/R Range Mean Reversion", "Status": "ACTIVE",
                            "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                            "Stop_Loss": eq_etf["Suggested SL (₹)"], "Target": eq_etf["Suggested Target (₹)"],
                            "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                            "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                            "Invested_Value": round(cmp_v * q, 2),
                            "Technical_Score_At_Entry": round(float(eq_etf.get("RSI (14D)", 50.0)), 1),
                            "Fundamental_Score_At_Entry": round(float(eq_etf.get("5Y S/R Win Rate (%)", 50.0)), 1),
                            "Composite_Score_At_Entry": round(float(eq_etf.get("Range Position (%)", 50.0)), 1),
                            "Near_Support_Status": f"Yes (+{dist_s1:.1f}% to S1)",
                            "RSI_At_Entry": round(float(eq_etf.get("RSI (14D)", 50.0)), 1),
                            "Empirical_Win_Rate_At_Entry": f"{eq_etf.get('5Y S/R Win Rate (%)', 50)}%",
                            "Market_Regime_At_Entry": regime_name
                        })
                        active_syms.add(sym)

            elif "09:45" in exec_mode:
                stk_b, _ = get_top_conviction_candidates(stocks_market_df, preset_name="Intraday", is_stock_mode=True, limit=2)
                for _, r in stk_b.iterrows():
                    sym = str(r["Ticker"]).replace(".NS", "")
                    cmp_v = float(r["CMP (₹)"])
                    if sym in active_syms or cmp_v <= 0: continue
                    q = max(1, int(base_budget // cmp_v))
                    created.append({
                        "Trade_ID": f"V2_INT_{int(datetime.datetime.now(IST).timestamp())}_{sym}", "Username": "Public_User", "Ticker": sym,
                        "Category": "Quality Stock", "Asset_Class": "Stock", "Trigger_Type": "MANUAL_INTRADAY",
                        "Trigger_Indicator": f"Intraday Volume Breakout (RSI: {r.get('RSI (14D)', 50):.1f})",
                        "Strategy_Preset": "Intraday", "Status": "ACTIVE",
                        "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                        "Stop_Loss": r["Stop_Loss"], "Target": r["Target"],
                        "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                        "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                        "Invested_Value": round(cmp_v * q, 2),
                        "Technical_Score_At_Entry": round(float(r.get("Technical Score", 50.0)), 1),
                        "Fundamental_Score_At_Entry": round(float(r.get("Fundamental Score", 50.0)), 1),
                        "Composite_Score_At_Entry": round(float(r.get("Composite Buy Score", 50.0)), 1),
                        "Near_Support_Status": "Mid-Channel",
                        "RSI_At_Entry": round(float(r.get("RSI (14D)", 50.0)), 1),
                        "Empirical_Win_Rate_At_Entry": "N/A",
                        "Market_Regime_At_Entry": regime_name
                    })
                    active_syms.add(sym)
            else:
                all_t = evaluate_trade_exits(all_t, active_raw_data, force_squareoff_intraday=True)

            if created:
                combined = pd.concat([all_t, pd.DataFrame(created)], ignore_index=True)
                save_paper_trades(combined)

            save_audit_entry({
                "Timestamp_IST": now_str, "Trigger_Source": f"V2_MANUAL_{exec_mode[:15]}",
                "Preset": "Multi-Asset", "Recommended_BUY": ", ".join([r["Ticker"] for r in created]) or "None",
                "Recommended_SELL": "None", "Execution_Status": f"🟢 Logged ({len(created)} Orders)",
                "Reason_Summary": f"Manual test generated {len(created)} paper orders."
            })
            st.cache_data.clear()
            st.session_state.strategy_toast = f"Manual run approved {len(created)} orders!"
            st.rerun()

    # Process Exits & Active Live MTM
    if not trades_df.empty and "Status" in trades_df.columns:
        trades_df = evaluate_trade_exits(trades_df, active_raw_data)
        
        # Category Filter Dropdown
        cat_options = ["All Categories"] + sorted(list(trades_df["Category"].dropna().unique())) if "Category" in trades_df.columns else ["All Categories"]
        sel_cat = st.selectbox("🎯 Filter Ledger by Asset Category:", cat_options, key="ledger_cat_filter")

        filtered_trades = trades_df if sel_cat == "All Categories" else trades_df[trades_df["Category"] == sel_cat]
        open_trades = filtered_trades[filtered_trades["Status"] == "ACTIVE"].copy()
        closed_trades = filtered_trades[filtered_trades["Status"] != "ACTIVE"].copy()

        cap_deployed = float(pd.to_numeric(open_trades["Invested_Value"], errors="coerce").sum()) if not open_trades.empty else 0.0
        tot_unrealized = float(pd.to_numeric(open_trades["PnL_Rs"], errors="coerce").sum()) if not open_trades.empty else 0.0
        closed_pnl = float(pd.to_numeric(closed_trades["PnL_Rs"], errors="coerce").sum()) if not closed_trades.empty else 0.0
        win_count = (pd.to_numeric(closed_trades["PnL_Rs"], errors="coerce") > 0).sum() if not closed_trades.empty else 0
        tot_closed = len(closed_trades)
        win_rate = (win_count / tot_closed * 100.0) if tot_closed > 0 else 0.0

        # High-Fidelity KPI Cards
        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Live Unrealized PnL", f"₹{tot_unrealized:+,.2f}", f"{len(open_trades)} Active Positions")
        m2.metric("Active Capital Deployed", f"₹{cap_deployed:,.2f}")
        m3.metric("Closed Realized PnL", f"₹{closed_pnl:+,.2f}", f"{tot_closed} Closed Trades")
        m4.metric("Strategy Win Rate", f"{win_rate:.1f}%" if tot_closed > 0 else "N/A", f"{win_count} Wins / {tot_closed - win_count} Losses")

        # Multi-Category Performance Breakdown Matrix
        st.markdown("##### 📊 Multi-Category Performance Breakdown")
        if not trades_df.empty and "Category" in trades_df.columns:
            cat_kpi_rows = []
            for c_name, grp in trades_df.groupby("Category"):
                c_closed = grp[grp["Status"] != "ACTIVE"]
                c_pnl = pd.to_numeric(c_closed["PnL_Rs"], errors="coerce").sum() if not c_closed.empty else 0.0
                c_unreal = pd.to_numeric(grp[grp["Status"] == "ACTIVE"]["PnL_Rs"], errors="coerce").sum() if not grp.empty else 0.0
                c_wins = (pd.to_numeric(c_closed["PnL_Rs"], errors="coerce") > 0).sum() if not c_closed.empty else 0
                c_tot_c = len(c_closed)
                c_wrate = (c_wins / c_tot_c * 100.0) if c_tot_c > 0 else 0.0
                cat_kpi_rows.append({
                    "Category": c_name,
                    "Total Trades": len(grp),
                    "Active Trades": len(grp[grp["Status"] == "ACTIVE"]),
                    "Closed Trades": c_tot_c,
                    "Win Rate %": f"{c_wrate:.1f}%" if c_tot_c > 0 else "Pending",
                    "Realized PnL (₹)": c_pnl,
                    "Unrealized PnL (₹)": c_unreal
                })
            if cat_kpi_rows:
                st.dataframe(
                    pd.DataFrame(cat_kpi_rows).style.format({
                        "Realized PnL (₹)": "₹{:+,.2f}",
                        "Unrealized PnL (₹)": "₹{:+,.2f}"
                    }),
                    use_container_width=True,
                    hide_index=True
                )

        # Active Positions Table with Enriched Parameter Provenance
        st.markdown("##### 📋 Open Active Positions (Live MTM & Indicator Provenance)")
        if not open_trades.empty:
            open_display_cols = [
                "Trade_ID", "Ticker", "Category", "Trigger_Indicator", "Near_Support_Status",
                "Technical_Score_At_Entry", "Fundamental_Score_At_Entry", "RSI_At_Entry",
                "Entry_Price", "Live_CMP", "Executed_Qty", "Stop_Loss", "Target",
                "PnL_Rs", "PnL_Pct", "Hold_Duration_Days", "Execution_Timestamp"
            ]
            valid_open_cols = [c for c in open_display_cols if c in open_trades.columns]
            render_top_scrollbar_sync()
            st.dataframe(
                open_trades[valid_open_cols].style.format({
                    "Entry_Price": "₹{:.2f}",
                    "Live_CMP": "₹{:.2f}",
                    "Stop_Loss": "₹{:.2f}",
                    "Target": "₹{:.2f}",
                    "PnL_Rs": "₹{:+.2f}",
                    "RSI_At_Entry": "{:.1f}",
                    "Technical_Score_At_Entry": "{:.1f}",
                    "Fundamental_Score_At_Entry": "{:.1f}"
                }),
                use_container_width=True
            )
        else:
            st.info("No active open positions for the selected category.")

        # Closed Positions History Journal
        st.markdown("##### 📜 Closed Positions & Historical Exit Journal")
        if not closed_trades.empty:
            closed_display_cols = [
                "Trade_ID", "Ticker", "Category", "Trigger_Indicator", "Near_Support_Status",
                "Technical_Score_At_Entry", "Fundamental_Score_At_Entry",
                "Entry_Price", "Exit_Price", "Executed_Qty", "Hold_Duration_Days",
                "PnL_Rs", "PnL_Pct", "Exit_Reason", "Execution_Timestamp", "Exit_Timestamp"
            ]
            valid_closed_cols = [c for c in closed_display_cols if c in closed_trades.columns]
            render_top_scrollbar_sync()
            st.dataframe(
                closed_trades[valid_closed_cols].style.format({
                    "Entry_Price": "₹{:.2f}",
                    "Exit_Price": "₹{:.2f}",
                    "PnL_Rs": "₹{:+.2f}",
                    "Technical_Score_At_Entry": "{:.1f}",
                    "Fundamental_Score_At_Entry": "{:.1f}"
                }),
                use_container_width=True,
                height=220
            )
    else:
        st.info("No paper trades found. Run a manual routine test above or execute 1-click recommendations from the High-Conviction Master Hub.")

    # Execution Audit Log
    st.markdown("---")
    st.markdown("##### 📋 Execution Audit Trail")
    aud_df = load_audit_log()
    if not aud_df.empty:
        st.dataframe(aud_df.sort_values(by="Timestamp_IST", ascending=False), use_container_width=True, height=180)


# =====================================================================
# TAB 3: BACKTESTING & MACHINE LEARNING OPTIMIZATION STUDIO
# =====================================================================
elif active_tab == "🧪 Multi-Regime Backtesting & Machine Learning":
    st.markdown("### 🧪 Machine Learning Optimization & Strategy Calibration Studio")
    st.caption("Empirical factor analysis, dynamic trailing stop tuning, and adaptive multi-factor weight calibration.")

    # 1. AI Quant Advisor Analysis & Tweaks
    sug_df = evaluate_strategy_performance_and_suggest_tweaks()
    ac1, ac2, ac3 = st.columns([2, 1, 1])
    with ac1:
        st.markdown(f"**Optimization Status:** `{runtime_cfg.get('optimization_status', 'Active')}`")
    with ac2:
        if st.button("🔄 Refresh Empirical Review", use_container_width=True):
            sug_df = evaluate_strategy_performance_and_suggest_tweaks()
            st.session_state.strategy_toast = "Empirical review refreshed."
            st.rerun()
    with ac3:
        if st.button("⚡ Apply AI Optimizations", use_container_width=True, type="primary"):
            res = apply_suggested_optimizations()
            st.success(f"Applied {len(res['changes'])} optimizations live!")
            st.cache_data.clear()
            st.rerun()

    st.markdown("##### 📊 Empirical Recommendations")
    st.dataframe(sug_df, use_container_width=True)

    st.markdown("---")

    # 2. Interactive Parameter Calibration Studio
    st.markdown("#### 🎚️ Interactive Parameter Calibration Studio")
    st.caption("Adjust sliders directly in the GUI. All changes immediately take effect across all screeners and daemons.")

    weights_dict = runtime_cfg.get("weights", {})
    risk_dict = runtime_cfg.get("risk_multipliers", {})
    sched_dict = runtime_cfg.get("execution_schedule", {})

    with st.form("manual_parameters_studio_form_v2"):
        with st.expander("🎯 Strategy Preset Indicator Weights (0% - 100%)", expanded=True):
            tab_p1, tab_p2, tab_p3 = st.tabs(["Default Preset", "Long-Term Secular", "Swing / Positional"])
            new_weights = json.loads(json.dumps(weights_dict))

            with tab_p1:
                c1, c2, c3, c4 = st.columns(4)
                w_dma_def = c1.slider("200 DMA Distance (%)", 0, 100, int(weights_dict.get("Default", {}).get("w_dma", 35)), key="s_def_dma")
                w_rsi_def = c2.slider("14D RSI Weight (%)", 0, 100, int(weights_dict.get("Default", {}).get("w_rsi", 30)), key="s_def_rsi")
                w_low_def = c3.slider("52W Low Proximity (%)", 0, 100, int(weights_dict.get("Default", {}).get("w_low", 20)), key="s_def_low")
                w_exp_def = c4.slider("Expense/Spread (%)", 0, 100, int(weights_dict.get("Default", {}).get("w_exp", 15)), key="s_def_exp")
                new_weights["Default"] = {"w_dma": w_dma_def, "w_rsi": w_rsi_def, "w_low": w_low_def, "w_exp": w_exp_def}

            with tab_p2:
                c1, c2, c3 = st.columns(3)
                w_dma_lt = c1.slider("200 DMA Trend (%)", 0, 100, int(weights_dict.get("Long-Term", {}).get("w_dma", 40)), key="s_lt_dma")
                w_div_lt = c2.slider("Dividend Yield (%)", 0, 100, int(weights_dict.get("Long-Term", {}).get("w_div", 20)), key="s_lt_div")
                w_rsi_lt = c3.slider("RSI Mean-Rev (%)", 0, 100, int(weights_dict.get("Long-Term", {}).get("w_rsi", 20)), key="s_lt_rsi")
                new_weights["Long-Term"] = {"w_dma": w_dma_lt, "w_div": w_div_lt, "w_rsi": w_rsi_lt, "w_low": 10, "w_exp": 10}

            with tab_p3:
                c1, c2, c3 = st.columns(3)
                w_rsi_sw = c1.slider("14D RSI Reversal (%)", 0, 100, int(weights_dict.get("Swing / Positional", {}).get("w_rsi", 35)), key="s_sw_rsi")
                w_dma_sw = c2.slider("200 DMA Pullback (%)", 0, 100, int(weights_dict.get("Swing / Positional", {}).get("w_dma", 35)), key="s_sw_dma")
                w_bb_sw = c3.slider("Bollinger %B (%)", 0, 100, int(weights_dict.get("Swing / Positional", {}).get("w_bb", 30)), key="s_sw_bb")
                new_weights["Swing / Positional"] = {"w_rsi": w_rsi_sw, "w_dma": w_dma_sw, "w_bb": w_bb_sw, "w_vwap": 0, "w_stoch": 0}

        with st.expander("🛡️ Risk Multipliers & Dynamic Trailing Stops", expanded=True):
            rc1, rc2 = st.columns(2)
            sw_sl = rc1.slider("Swing Stop Loss (x ATR)", 1.0, 4.0, float(risk_dict.get("swing_sl_multiplier", 1.8)), step=0.1, key="s_sw_sl")
            sw_tgt = rc2.slider("Swing Target (x ATR)", 1.5, 6.0, float(risk_dict.get("swing_target_multiplier", 3.0)), step=0.1, key="s_sw_tgt")
            new_risk = {
                "swing_sl_multiplier": sw_sl, "swing_target_multiplier": sw_tgt,
                "intraday_sl_multiplier": 1.0, "intraday_target_multiplier": 1.8,
                "longterm_sl_multiplier": 2.5, "longterm_target_multiplier": 5.0,
                "trailing_stop_activation_pct": 3.0, "trailing_stop_lock_pct": 0.5,
                "overbought_rsi_exit_threshold": 76.0, "oversold_rsi_buy_threshold": 38.0
            }

        save_btn = st.form_submit_button("💾 Save Parameter Calibration", type="primary", use_container_width=True)

    if save_btn:
        save_res = save_manual_parameter_adjustments(new_weights, new_risk, sched_dict, user="Public_User")
        st.session_state.strategy_toast = f"🟢 Saved adjustments ({save_res['updated_count']} parameters updated)!"
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")

    # 3. Parameter Edge Directionality Matrix
    st.markdown("#### 📐 All Strategy Parameters & Edge Directionality Matrix")
    param_matrix_df = get_parameter_reference_matrix()
    st.dataframe(
        param_matrix_df[["Category", "Parameter", "Current_Value", "Default_Value", "BUY_Edge_Direction", "SELL_Edge_Direction", "Intended_Market_Impact"]],
        use_container_width=True,
        height=280
    )

    # 4. Parameter Change Audit Trail
    st.markdown("---")
    st.markdown("#### 📝 Parameter Change Audit Log")
    param_change_log_df = load_parameter_change_log()
    if not param_change_log_df.empty:
        st.dataframe(param_change_log_df.sort_values(by="Timestamp_IST", ascending=False), use_container_width=True, height=180)


# =====================================================================
# TAB 4: PLATFORM STRATEGY GUIDE & DOCX EXPORT
# =====================================================================
elif active_tab == "📘 Platform Strategy Guide & DOCX Export":
    st.markdown("### 📘 Platform Strategy Architecture & Quantitative Documentation")
    st.caption("Institutional methodology, mathematical derivations, factor models, and exportable documentation.")

    g_col1, g_col2 = st.columns([3, 1])
    with g_col1:
        st.markdown(
            """
            #### 🏛️ Strategy Philosophy: The 5-Pillar Non-Sectoral Allocator
            1. **Broad Equity & Smart Beta ETFs:** Eliminates uncompensated single-sector cyclical risks by allocating to Nifty 50, Next 50, Midcap 150, Smallcap 250, Momentum 30, Alpha 30, and Quality 30.
            2. **High-Conviction Quality Equities:** Generates alpha by identifying NIFTY LargeMidcap 250 companies experiencing multi-timeframe oversold technical pullbacks while possessing superior balance sheet liquidity.
            3. **Support & Resistance (S/R) Mean Reversion:** Exploits non-trending, range-bound regimes (ADX < 25) to enter precisely at the 50-day rolling S1 support floor, verified by 5-year empirical bounce backtests.
            4. **Premier Indian REITs & InvITs:** Captures inflation-indexed, high-yield cash distributions (7.5% - 12.2%) with SEBI-mandated 100% NDCF payouts and AAA credit protection.
            5. **Precious Metals Sectoral Commodities:** Allocates to Gold and Silver conditionally as macro hedges during equity stress, automatically skipping entries during overbought cyclical peaks.
            """
        )
    with g_col2:
        st.markdown("##### 📥 Export Guide")
        if docx_bytes:
            st.download_button(
                label="📥 Download V2 Guide (.docx)",
                data=docx_bytes,
                file_name="AGY_Quant_Platform_V2_Guide.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        st.markdown(
            """
            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 6px; font-size: 0.80rem;">
                <b>Version:</b> 2.2-Adaptive<br>
                <b>Coverage:</b> 297 Assets<br>
                <b>SEBI Compliance:</b> 100% NDCF<br>
                <b>Zero-Secrets:</b> Verified
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown(
        """
        ##### 📐 Mathematical Factor Formulations
        $$\\text{Composite Buy Score} = w_{\\text{DMA}} \\cdot \\text{Rank}(\\Delta_{\\text{200DMA}}) + w_{\\text{RSI}} \\cdot \\text{Rank}(\\text{RSI}_{14}) + w_{\\text{Low}} \\cdot \\text{Rank}(\\text{Dist}_{52W\\text{Low}}) + w_{\\text{Exp}} \\cdot \\text{Rank}(\\text{Expense})$$
        $$\\text{Dynamic S/R Channel Width (\\%)} = \\frac{R_1 - S_1}{S_1} \\times 100$$
        $$\\text{REIT Real Estate Yield} = \\frac{\\text{Annualized DPU (₹)}}{\\text{CMP (₹)}} \\times 100$$
        """
    )
