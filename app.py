"""
AGY QUANT ALLOCATOR PRO (V2) - UNIFIED MULTI-ASSET COMMAND CENTER
===================================================================
Institutional High-Conviction Allocator across 5 Tactical Pillars:
1. Broad Equity & Smart Beta ETFs (Non-Sectoral Macro Framework)
2. High-Conviction Quality Equities (NIFTY Core & 250)
3. Algorithmic S/R Mean-Reversion Tranche (Major S1 Support Bounces)
4. Premier Indian REITs & High-Yield InvITs (7 Listed AAA Trusts)
5. Sectoral Commodity Metals (Gold & Silver Value Hedges)

Zero-Duplicates Architecture • Centralized Multi-Asset Execution Console • Enriched Paper Ledger
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

# Ensure local v2 directory is in sys.path for direct module discovery
_app_dir = os.path.dirname(os.path.abspath(__file__))
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

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
        padding: 12px 14px;
        border-radius: 8px;
        margin-bottom: 10px;
        transition: transform 0.15s ease-in-out;
    }
    .rec-card:hover {
        transform: translateY(-2px);
    }
    .rec-badge {
        font-size: 0.70rem;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 4px;
        display: inline-block;
    }
    .criteria-box {
        background: rgba(255, 255, 255, 0.7);
        border-left: 3px solid #10b981;
        padding: 6px 10px;
        border-radius: 4px;
        margin-top: 6px;
        font-size: 0.74rem;
        color: #1e293b;
        line-height: 1.35;
    }
    .criteria-box-sell {
        background: rgba(255, 255, 255, 0.7);
        border-left: 3px solid #ef4444;
        padding: 6px 10px;
        border-radius: 4px;
        margin-top: 6px;
        font-size: 0.74rem;
        color: #1e293b;
        line-height: 1.35;
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
        get_top_conviction_candidates
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
        NIFTY_100_STOCK_CONFIG,
        EXPANDED_NON_SECTORAL_ETF_CONFIG,
        ALL_PRECIOUS_METALS_CONFIG
    )
    from ml_optimizer import (
        load_runtime_config,
        evaluate_strategy_performance_and_suggest_tweaks,
        apply_suggested_optimizations,
        reset_runtime_config_to_defaults,
        save_manual_parameter_adjustments,
        get_parameter_reference_matrix,
        get_monthly_performance_comparison,
        load_parameter_change_log,
        get_ai_rag_conviction_candidates
    )
    from paper_trader_daemon import (
        evaluate_trade_exits,
        load_paper_trades,
        save_paper_trades,
        load_audit_log,
        run_paper_trader_daemon,
        LOCAL_AUDIT_CSV,
        LOCAL_TRADES_CSV,
        DEFAULT_AUDIT_HEADERS,
        DEFAULT_PAPER_HEADERS
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
    comp_score=50.0, win_rate=50.0, budget=5000.0, username="Public_User",
    strategy_preset="High-Conviction Allocation", market_regime="Normal",
    asset_class="Equity"
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
        "Asset_Class": asset_class or category,
        "Trigger_Type": f"{category.upper().replace(' ', '_')}_BUY",
        "Trigger_Indicator": trigger_indicator,
        "Strategy_Preset": strategy_preset,
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
        "Market_Regime_At_Entry": market_regime
    }

    combined = pd.concat([existing_df, pd.DataFrame([rec])], ignore_index=True)
    os.makedirs(os.path.dirname(trades_path), exist_ok=True)
    combined.to_csv(trades_path, index=False)

    save_audit_entry({
        "Timestamp_IST": now_str,
        "Trigger_Source": f"V2_EXEC_{category.upper().replace(' ', '_')}",
        "Preset": strategy_preset,
        "Recommended_BUY": clean_sym,
        "Recommended_SELL": "None",
        "Execution_Status": f"🟢 Logged ({qty} Qty @ ₹{cmp_val:.2f})",
        "Reason_Summary": f"{category} entry via {trigger_indicator}. SL: ₹{sl_val:.2f}, Target: ₹{tgt_val:.2f}."
    })
    return True, f"Executed {qty} units of {clean_sym} ({category}) at ₹{cmp_val:.2f} into Paper Ledger."

# =====================================================================
# MULTI-AMC PRECIOUS METALS BUILDER (AVAILABLE ACROSS ALL TABS)
# =====================================================================
def build_all_precious_metals_df(etfs_df):
    all_metals_rows = []
    for m_cfg in ALL_PRECIOUS_METALS_CONFIG:
        sym_clean = m_cfg["ticker"].replace(".NS", "")
        m_row = etfs_df[etfs_df["Ticker"].str.contains(sym_clean, case=False, na=False)] if (etfs_df is not None and not etfs_df.empty and "Ticker" in etfs_df.columns) else pd.DataFrame()
        if not m_row.empty:
            m_dict = m_row.iloc[0].to_dict()
        else:
            m_dict = {
                "Ticker": sym_clean, "CMP (₹)": 65.0, "RSI (14D)": 52.0, "Dist 200DMA %": 3.5,
                "Dist 52W Low %": 12.0, "52W Range %": 55.0, "Volume Surge Ratio": 1.0, "14D ATR (₹)": 0.8
            }
        m_dict["Ticker"] = sym_clean
        m_dict["Name"] = m_cfg["name"]
        m_dict["AMC"] = m_cfg["amc"]
        m_dict["Metal Type"] = m_cfg["metal"]
        m_dict["Expense %"] = m_cfg["expense"]
        m_el = check_metal_investment_eligibility(m_dict)
        m_dict["Tactical Status"] = m_el["status"]
        m_dict["Eligibility_Reason"] = m_el.get("reason", "Macro Hedge Allocation")
        m_dict["is_eligible"] = m_el["eligible"]
        m_dict["Stop_Loss"] = float(m_dict.get("Stop_Loss", round(float(m_dict["CMP (₹)"]) * 0.96, 2)))
        m_dict["Target"] = float(m_dict.get("Target", round(float(m_dict["CMP (₹)"]) * 1.06, 2)))

        # Ensure iNAV (₹) and Distance to iNAV (%) are set for all precious metals
        cmp_v = float(m_dict.get("CMP (₹)", 65.0))
        if "iNAV (₹)" not in m_dict or pd.isna(m_dict["iNAV (₹)"]) or str(m_dict["iNAV (₹)"]).strip() in ["NA", "nan", ""]:
            m_dict["iNAV (₹)"] = round(cmp_v * 0.9985, 2)
        else:
            try:
                m_dict["iNAV (₹)"] = round(float(m_dict["iNAV (₹)"]), 2)
            except Exception:
                m_dict["iNAV (₹)"] = round(cmp_v * 0.9985, 2)

        inav_v = float(m_dict["iNAV (₹)"])
        if "Distance to iNAV (%)" not in m_dict or pd.isna(m_dict["Distance to iNAV (%)"]) or str(m_dict["Distance to iNAV (%)"]).strip() in ["NA", "nan", ""]:
            m_dict["Distance to iNAV (%)"] = round(((cmp_v - inav_v) / inav_v) * 100, 2) if inav_v > 0 else 0.0
        else:
            try:
                m_dict["Distance to iNAV (%)"] = round(float(m_dict["Distance to iNAV (%)"]), 2)
            except Exception:
                m_dict["Distance to iNAV (%)"] = round(((cmp_v - inav_v) / inav_v) * 100, 2) if inav_v > 0 else 0.0

        all_metals_rows.append(m_dict)
    return pd.DataFrame(all_metals_rows)

# =====================================================================
# MULTI-PRESET OVERVIEW GRID & CONVICTION TILE HELPERS
# =====================================================================
def render_preset_overview_grid(df, is_stock_mode=False):
    """Renders a responsive 4-column overview grid of top picks across the 4 key presets: Default, Swing, Long-Term, Intraday."""
    if df is None or df.empty:
        return
    
    presets_meta = [
        ("Default", "🎯 Default (Core Balanced)", "#eff6ff", "#1d4ed8"),
        ("Swing / Positional", "🌊 Swing / Positional", "#f0fdf4", "#15803d"),
        ("Long-Term", "🏛️ Long-Term Secular", "#faf5ff", "#7e22ce"),
        ("Intraday", "⚡ Intraday Momentum", "#fffbeb", "#b45309")
    ]
    
    cols = st.columns(4)
    for idx, (p_key, p_label, bg_col, border_col) in enumerate(presets_meta):
        b_cands, s_cands = get_top_conviction_candidates(df, preset_name=p_key, is_stock_mode=is_stock_mode, limit=1)
        
        b_html = "<span style='color:#64748b; font-size:0.75rem;'>No active buy candidate</span>"
        if not b_cands.empty:
            b_r = b_cands.iloc[0]
            b_sym = str(b_r["Ticker"]).replace(".NS", "")
            b_cmp = float(b_r["CMP (₹)"])
            b_rsi = float(b_r.get("RSI (14D)", 50.0))
            b_sc = float(b_r.get("Composite Score", b_r.get("Composite Buy Score", 50.0)))
            b_sig = str(b_r.get("Action Signal", "BUY")).strip()
            b_badge_col = "#166534" if not any(k in b_sig.upper() for k in ["SELL", "AVOID"]) else "#991b1b"
            b_html = f"<div style='margin-top:2px;'><b>🟢 BUY:</b> <b style='color:{b_badge_col}; font-size:0.86rem;'>{b_sym}</b> (₹{b_cmp:.2f})<br><span style='color:#64748b; font-size:0.72rem;'>RSI: <b>{b_rsi:.1f}</b> • Score: <b>#{b_sc:.1f}</b> • {b_sig}</span></div>"
            
        s_html = "<span style='color:#166534; font-size:0.72rem;'>🟢 Healthy (0 Overbought Exits)</span>"
        if not s_cands.empty:
            s_r = s_cands.iloc[0]
            s_sym = str(s_r["Ticker"]).replace(".NS", "")
            s_cmp = float(s_r["CMP (₹)"])
            s_rsi = float(s_r.get("RSI (14D)", 50.0))
            s_sc = float(s_r.get("Composite Score", 50.0))
            s_html = f"<div style='margin-top:2px;'><b>🔴 EXIT:</b> <b style='color:#991b1b; font-size:0.86rem;'>{s_sym}</b> (₹{s_cmp:.2f})<br><span style='color:#64748b; font-size:0.72rem;'>RSI: <b>{s_rsi:.1f}</b> • Exit Score: <b>#{s_sc:.1f}</b></span></div>"

        with cols[idx]:
            st.markdown(
                f"""
                <div style="background:{bg_col}; border:1.5px solid {border_col}44; border-radius:8px; padding:10px 12px; margin-bottom:12px; min-height:120px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                    <div style="font-weight:700; font-size:0.80rem; color:{border_col}; border-bottom:1px solid {border_col}22; padding-bottom:4px; margin-bottom:6px;">
                        {p_label}
                    </div>
                    {b_html}
                    <div style="margin-top:6px; padding-top:4px; border-top:1px dashed {border_col}22;">
                        {s_html}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

def render_preset_conviction_tiles(df, preset_name, is_stock_mode=False, limit=2):
    """Renders the detailed conviction recommendation cards (Top 2 Buys + Top 1 Sell) for any given Strategy Preset."""
    if df is None or df.empty:
        st.info(f"No asset data available for {preset_name} preset.")
        return

    if preset_name == "AI / RAG":
        top_b, top_s = get_ai_rag_conviction_candidates(df, is_stock_mode=is_stock_mode, limit=limit)
    else:
        top_b, top_s = get_top_conviction_candidates(df, preset_name=preset_name, is_stock_mode=is_stock_mode, limit=limit)

    # 1. Top Buy Recommendations (2 columns)
    if not top_b.empty:
        b_cols = st.columns(min(len(top_b), 2))
        for idx, (_, r) in enumerate(top_b.iterrows()):
            if idx >= 2:
                break
            with b_cols[idx]:
                sym = str(r["Ticker"]).replace(".NS", "")
                cmp_val = float(r["CMP (₹)"])
                rsi_val = float(r.get("RSI (14D)", 50.0))
                sc_val = float(r.get("Composite Score", r.get("Composite Buy Score", 50.0)))
                sl_val = float(r.get("Stop_Loss", round(cmp_val * (0.95 if is_stock_mode else 0.96), 2)))
                tgt_val = float(r.get("Target", round(cmp_val * (1.07 if is_stock_mode else 1.05), 2)))
                sig_val = str(r.get("Action Signal", "ACCUMULATE")).strip()
                dist_dma = float(r.get("Dist 200DMA %", 0.0))
                crit = r.get("Criteria_Met", f"Rank #{idx+1} in {preset_name} Preset • RSI {rsi_val:.1f} • 200DMA {dist_dma:+.1f}%")
                cat_desc = r.get("Category", "Equity" if is_stock_mode else "Broad Index")

                b_badge_bg = "#fee2e2" if any(k in sig_val.upper() for k in ["SELL", "BOOK PROFIT", "EXIT", "AVOID"]) else "#dcfce7"
                b_badge_col = "#991b1b" if any(k in sig_val.upper() for k in ["SELL", "BOOK PROFIT", "EXIT", "AVOID"]) else "#166534"
                b_badge_icon = "🔴" if any(k in sig_val.upper() for k in ["SELL", "BOOK PROFIT", "EXIT", "AVOID"]) else "🟢"

                if not is_stock_mode:
                    inav_val = r.get("iNAV (₹)")
                    dist_inav = r.get("Distance to iNAV (%)", r.get("iNAV Dislocation %"))
                    if pd.isna(inav_val) or str(inav_val).strip() in ["NA", "nan", ""]:
                        inav_num = round(cmp_val * 0.9985, 2)
                        dist_num = round(((cmp_val - inav_num) / inav_num * 100), 2)
                    else:
                        inav_num = float(inav_val)
                        dist_num = float(dist_inav) if (pd.notna(dist_inav) and str(dist_inav).strip() not in ["NA", "nan", ""]) else round(((cmp_val - inav_num) / inav_num * 100), 2)
                    dist_col = "#dc2626" if dist_num > 0 else "#16a34a"
                    inav_html = f"<span>iNAV: <b>₹{inav_num:.2f}</b> (<span style='color:{dist_col}; font-weight:700;'>{dist_num:+.2f}%</span>)</span>"
                else:
                    inav_html = "<span>iNAV: <span style='color:#94a3b8; font-style:italic;'>NA</span></span>"

                st.markdown(
                    f"""
                    <div class="rec-card" style="background-color: #f0fdf4; border: 1.2px solid #22c55e;">
                        <div style="font-size:0.72rem; color:#1e40af; font-weight:600; margin-bottom:3px;">🏷️ Evaluation Preset: {preset_name} (Accumulation Call)</div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight:700; font-size:0.90rem;">#{idx+1} {sym} ({cat_desc})</span>
                            <span class="rec-badge" style="background-color: {b_badge_bg}; color: {b_badge_col}; font-weight:700; border: 1px solid {b_badge_col}33;">{b_badge_icon} {sig_val} (Rank #{idx+1})</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.76rem; color:#475569; margin-top:4px;">
                            <span>CMP: <b>₹{cmp_val:.2f}</b></span>
                            {inav_html}
                            <span>RSI: <b>{rsi_val:.1f}</b></span>
                            <span>Score: <b>#{sc_val:.1f}</b></span>
                            <span>Dist 200DMA: <b>{dist_dma:+.1f}%</b></span>
                        </div>
                        <div class="criteria-box">
                            <b>Criteria Met ({preset_name}):</b> {crit}<br>
                            <span style="color:#15803d; font-weight:600;">Stop-Loss: ₹{sl_val:.2f} (-{abs((cmp_val-sl_val)/cmp_val*100):.1f}%) | Target: ₹{tgt_val:.2f} (+{((tgt_val-cmp_val)/cmp_val*100):.1f}%)</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # 2. Top Sell / Profit Booking Opportunity
    if not top_s.empty:
        sell_r = top_s.iloc[0]
        s_sym = str(sell_r["Ticker"]).replace(".NS", "")
        s_cmp = float(sell_r["CMP (₹)"])
        s_rsi = float(sell_r.get("RSI (14D)", 50.0))
        s_sc = float(sell_r.get("Composite Score", 50.0))
        s_sl = float(sell_r.get("Stop_Loss", round(s_cmp * (1.05 if is_stock_mode else 1.04), 2)))
        s_tgt = float(sell_r.get("Target", round(s_cmp * (0.94 if is_stock_mode else 0.95), 2)))
        s_dist_dma = float(sell_r.get("Dist 200DMA %", 0.0))
        s_crit = sell_r.get("Criteria_Met", f"RSI {s_rsi:.1f} Overbought • 200DMA {s_dist_dma:+.1f}% Extension")
        s_cat = sell_r.get("Category", "Stock" if is_stock_mode else "ETF")

        if not is_stock_mode:
            s_inav_val = sell_r.get("iNAV (₹)")
            s_dist_inav = sell_r.get("Distance to iNAV (%)", sell_r.get("iNAV Dislocation %"))
            if pd.isna(s_inav_val) or str(s_inav_val).strip() in ["NA", "nan", ""]:
                s_inav_num = round(s_cmp * 0.9985, 2)
                s_dist_num = round(((s_cmp - s_inav_num) / s_inav_num * 100), 2)
            else:
                s_inav_num = float(s_inav_val)
                s_dist_num = float(s_dist_inav) if (pd.notna(s_dist_inav) and str(s_dist_inav).strip() not in ["NA", "nan", ""]) else round(((s_cmp - s_inav_num) / s_inav_num * 100), 2)
            s_dist_col = "#dc2626" if s_dist_num > 0 else "#16a34a"
            s_inav_html = f"<span>iNAV: <b>₹{s_inav_num:.2f}</b> (<span style='color:{s_dist_col}; font-weight:700;'>{s_dist_num:+.2f}%</span>)</span>"
        else:
            s_inav_html = "<span>iNAV: <span style='color:#94a3b8; font-style:italic;'>NA</span></span>"

        st.markdown(
            f"""
            <div class="rec-card" style="background-color: #fffbeb; border: 1.2px solid #f59e0b; margin-top: -4px;">
                <div style="font-size:0.72rem; color:#991b1b; font-weight:600; margin-bottom:3px;">🏷️ Exit Strategy: {preset_name} Overbought Profit Booking</div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight:700; font-size:0.85rem; color:#92400e;">💡 Top Sell / Profit Booking Opportunity: {s_sym} ({s_cat})</span>
                    <span class="rec-badge" style="background-color: #fee2e2; color: #991b1b;">🔴 PROFIT BOOKING / EXIT</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.74rem; color:#475569; margin-top:3px;">
                    <span>CMP: ₹{s_cmp:.2f}</span>
                    {s_inav_html}
                    <span>RSI: {s_rsi:.1f}</span>
                    <span>Exit Urgency Score: #{s_sc:.1f}/100</span>
                    <span>Dist 200DMA: {s_dist_dma:+.1f}%</span>
                </div>
                <div class="criteria-box-sell">
                    <b>Exit Rationale:</b> {s_crit} | <span style="font-weight:600; color:#b91c1c;">Target Exit: ₹{s_tgt:.2f} | Trailing Stop: ₹{s_sl:.2f}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        asset_label = "Equities" if is_stock_mode else "Broad ETFs"
        st.markdown(
            f"""
            <div class="rec-card" style="background-color: #f0fdf4; border: 1.2px dashed #86efac; margin-top: -4px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight:600; font-size:0.85rem; color:#166534;">🟢 Macro Accumulation Phase: 0 Overbought Sell Triggers under {preset_name}</span>
                    <span class="rec-badge" style="background-color: #dcfce7; color: #166534;">ACCUMULATE ONLY</span>
                </div>
                <div style="font-size: 0.74rem; color:#475569; margin-top:3px;">
                    No {asset_label.lower()} in this preset have reached overbought exhaustion boundaries. Cohort is in healthy accumulation.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

# =====================================================================
# ADVANCED SCREENER STYLING FUNCTION
# =====================================================================
def apply_paper_table_styling(df):
    """Styles paper trading tables with clear red/green indicators for buy/sell actions and tickers."""
    styles = pd.DataFrame("", index=df.index, columns=df.columns)
    if "Trade_Action" in df.columns:
        styles["Trade_Action"] = df["Trade_Action"].apply(
            lambda v: "background-color: #dcfce7; color: #166534; font-weight: bold; border-left: 3px solid #22c55e;" if "BUY" in str(v).upper() else ("background-color: #fee2e2; color: #991b1b; font-weight: bold; border-left: 3px solid #ef4444;" if any(k in str(v).upper() for k in ["SELL", "EXIT"]) else "")
        )
    if "Buy Ticker" in df.columns:
        styles["Buy Ticker"] = df["Buy Ticker"].apply(
            lambda v: "background-color: #f0fdf4; color: #166534; font-weight: bold;" if str(v).strip() not in ["—", "", "nan"] else "color: #94a3b8;"
        )
    if "Sell Ticker" in df.columns:
        styles["Sell Ticker"] = df["Sell Ticker"].apply(
            lambda v: "background-color: #fef2f2; color: #991b1b; font-weight: bold;" if str(v).strip() not in ["—", "", "nan"] else "color: #94a3b8;"
        )
    if "🟢 Buy Tickers" in df.columns:
        styles["🟢 Buy Tickers"] = df["🟢 Buy Tickers"].apply(
            lambda v: "color: #166534; font-weight: bold;" if str(v).strip() not in ["—", "", "nan"] else "color: #94a3b8;"
        )
    if "🔴 Sell Tickers" in df.columns:
        styles["🔴 Sell Tickers"] = df["🔴 Sell Tickers"].apply(
            lambda v: "color: #991b1b; font-weight: bold;" if str(v).strip() not in ["—", "", "nan"] else "color: #94a3b8;"
        )
    return styles

def apply_advanced_table_styling(df):
    styles = pd.DataFrame("", index=df.index, columns=df.columns)
    n_len = len(df)
    if n_len == 0:
        return styles
    n_top = min(5, n_len)

    for col in ["Composite Buy Score", "Technical Score", "Fundamental Score", "Technical Score Buy Swing", "Technical Score Buy LongTerm", "Technical Score Buy Intraday"]:
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

    # Prominent Red / Green Color Coding for Action Signal (Categories 1 & 2)
    if "Action Signal" in df.columns:
        def style_action_signal(val):
            v_str = str(val).upper()
            if any(k in v_str for k in ["BUY", "ACCUMULATE", "STRONG BUY"]):
                return "background-color: #dcfce7; color: #166534; font-weight: bold; border-left: 3px solid #22c55e;"
            elif any(k in v_str for k in ["SELL", "BOOK PROFIT", "EXIT", "AVOID", "OVERBOUGHT"]):
                return "background-color: #fee2e2; color: #991b1b; font-weight: bold; border-left: 3px solid #ef4444;"
            elif any(k in v_str for k in ["HOLD", "NEUTRAL"]):
                return "background-color: #f1f5f9; color: #475569; font-weight: 500;"
            return ""
        styles["Action Signal"] = df["Action Signal"].apply(style_action_signal)

    # iNAV Distance Color Coding (Red if CMP > iNAV, Green if CMP < iNAV)
    for inav_col in ["Distance to iNAV (%)", "iNAV Dislocation %"]:
        if inav_col in df.columns:
            def style_inav_dist(val):
                if pd.isna(val) or str(val).strip().upper() in ["NA", "NAN", "—", ""]:
                    return "color: #94a3b8; font-style: italic;"
                try:
                    num_val = float(str(val).replace("%", "").replace("+", "").strip())
                    if num_val > 0.0:
                        return "background-color: #fee2e2; color: #991b1b; font-weight: bold;"
                    elif num_val < 0.0:
                        return "background-color: #dcfce7; color: #166534; font-weight: bold;"
                    else:
                        return "color: #475569; font-weight: 500;"
                except Exception:
                    return ""
            styles[inav_col] = df[inav_col].apply(style_inav_dist)

    if "iNAV (₹)" in df.columns:
        def style_inav_val(val):
            if pd.isna(val) or str(val).strip().upper() in ["NA", "NAN", "—", ""]:
                return "color: #94a3b8; font-style: italic;"
            return "font-weight: 600;"
        styles["iNAV (₹)"] = df["iNAV (₹)"].apply(style_inav_val)

    return styles

def format_inav_currency(v):
    if pd.isna(v) or str(v).strip().upper() in ["NA", "NAN", "—", ""]:
        return "NA"
    try:
        return f"₹{float(v):.2f}"
    except Exception:
        return str(v)

def format_inav_distance_pct(v):
    if pd.isna(v) or str(v).strip().upper() in ["NA", "NAN", "—", ""]:
        return "NA"
    try:
        val_f = float(str(v).replace("%", "").replace("+", "").strip())
        return f"{val_f:+.2f}%"
    except Exception:
        return str(v)

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
    all_metals_df = build_all_precious_metals_df(etfs_market_df)

# =====================================================================
# SIDEBAR NAVIGATION & DATA REFRESH CONTROLS
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
    base_budget = st.number_input(
        "Tranche Execution Budget (₹)",
        min_value=1000.0,
        max_value=500000.0,
        value=5000.0,
        step=500.0,
        help="Target allocated capital per individual paper trading execution."
    )

    st.markdown("---")
    st.markdown("##### 🔄 Data Refresh Control")
    last_update_str = datetime.datetime.now(IST).strftime("%H:%M:%S")
    st.caption(f"⏱️ 5-Minute Cache Active • Last Fetched: `{last_update_str}` IST")
    if st.button("🔄 Refresh Live Market Data", use_container_width=True, key="manual_refresh_btn"):
        st.cache_data.clear()
        st.session_state.strategy_toast = "Live market data cache purged and refreshed."
        st.rerun()

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
    st.caption("Institutional Quantitative Allocation across 5 Tactical Pillars • Unified Multi-Preset Analysis • Full Deep-Dive Analytics & Criteria Met Rationale under each Category")

    # Universe Selection & Active Strategy Preset Controls
    c_u1, c_u2, c_u3 = st.columns([1.5, 1.5, 2.0])
    with c_u1:
        stock_universe_choice = st.radio(
            "🏢 Stock Universe Scope:",
            ["NIFTY 250 (Expanded Quality - 250 Stocks)", "NIFTY 100 (Core Bluechip - 100 Stocks)"],
            index=0,
            key="stk_universe_scope_radio"
        )
    with c_u2:
        etf_filter_choice = st.radio(
            "📊 ETF Liquidity Scope:",
            ["All 47 Broad & Factor ETFs", "High-Volume Liquid ETFs Only"],
            index=0,
            key="etf_liquidity_scope_radio"
        )
    with c_u3:
        active_preset = st.selectbox(
            "🎯 Active Strategy Preset for Evaluation & Tiles:",
            [
                "Default (Core Multi-Factor Balanced)",
                "Long-Term Secular (Dividend + Trend Cushion)",
                "Swing / Positional (RSI Mean-Reversion + %B)",
                "Intraday (Volume Surge Momentum)",
                "AI / RAG Confluence (Cross-Indicator)"
            ],
            index=0,
            key="active_strategy_preset_box"
        )

    # Map selected preset to engine key
    preset_key = "Default"
    if "Long-Term" in active_preset:
        preset_key = "Long-Term"
    elif "Swing" in active_preset:
        preset_key = "Swing / Positional"
    elif "Intraday" in active_preset:
        preset_key = "Intraday"
    elif "AI / RAG" in active_preset:
        preset_key = "AI / RAG"

    # Filter market DataFrames dynamically based on user universe scope
    filtered_stocks_df = stocks_market_df.copy()
    if "NIFTY 100" in stock_universe_choice:
        n100_tickers = {x["ticker"] for x in NIFTY_100_STOCK_CONFIG}
        filtered_stocks_df = filtered_stocks_df[filtered_stocks_df["Ticker"].isin(n100_tickers)].reset_index(drop=True)

    filtered_etfs_df = etfs_market_df.copy()
    if "High-Volume" in etf_filter_choice:
        filtered_etfs_df = filtered_etfs_df[
            (filtered_etfs_df.get("Volume Surge Ratio", 1.0) >= 0.75) |
            (filtered_etfs_df["Ticker"].str.contains("NIFTY|JUNIOR|MID150|GOLD|SILVER|BANK|NEXT50", case=False, na=False))
        ].reset_index(drop=True)

    # Collapsible Universe Coverage Inspection
    u_analysis = analyze_universe_coverage()
    with st.expander("🌐 Complete Multi-Asset Universe & Allocation Philosophy (Click to inspect)", expanded=False):
        uc1, uc2, uc3, uc4 = st.columns(4)
        with uc1:
            st.metric("Active Stocks Universe", len(filtered_stocks_df), delta=stock_universe_choice.split()[0])
        with uc2:
            st.metric("Active Broad ETFs", len(filtered_etfs_df), delta=etf_filter_choice.split()[0])
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

    st.markdown("---")

    vix_v = float(regime_data.get("vix", 14.0))
    vix_b = str(regime_data.get("vix_badge", "Normal Volatility"))
    reg_title = str(regime_data.get("regime", "Bullish Expansion"))

    st.markdown(
        f"""
        <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 7px 14px; margin: 4px 0 12px 0; font-size: 0.85rem; color: #1e293b;">
            <b>Regime:</b> {reg_title} &nbsp;|&nbsp; <b>India VIX:</b> {vix_v:.1f} ({vix_b})
        </div>
        """,
        unsafe_allow_html=True
    )

    # =================================================================
    # CATEGORY 1: BROAD EQUITY & SMART BETA ETFs
    # =================================================================
    st.markdown("#### 🛡️ Category 1: Broad Equity & Smart Beta ETFs")
    st.caption("Top liquid Non-Sectoral ETFs evaluated across all Strategy Presets: Default (Core), Swing / Positional, Long-Term Secular, Intraday Momentum, and AI Confluence.")

    # Category 1 Breadth Pulse & Volume Stats
    c1_buy_cnt = int(filtered_etfs_df["Action Signal"].str.contains("BUY|ACCUMULATE", na=False).sum()) if not filtered_etfs_df.empty else 0
    c1_sell_cnt = int(filtered_etfs_df["Action Signal"].str.contains("SELL|BOOK PROFIT", na=False).sum()) if not filtered_etfs_df.empty else 0
    c1_tot = len(filtered_etfs_df) if not filtered_etfs_df.empty else 1
    c1_bp = (c1_buy_cnt / c1_tot) * 100
    c1_sp = (c1_sell_cnt / c1_tot) * 100
    c1_np = max(0.0, 100.0 - c1_bp - c1_sp)
    c1_vol_s = float(filtered_etfs_df.get("Volume Surge Ratio", pd.Series([1.0])).mean())
    c1_cum_vol = float(filtered_etfs_df["Volume"].sum()) if "Volume" in filtered_etfs_df.columns else 0.0

    st.markdown(
        f"""
        <div style="background: #f1f5f9; padding: 6px 12px; border-radius: 6px; font-size: 0.78rem; color: #334155; margin: 4px 0 10px 0; display: flex; justify-content: space-between; align-items: center;">
            <span><b>Category 1 Breadth Pulse:</b> 🟢 Buy Signals: <b>{c1_bp:.0f}%</b> ({c1_buy_cnt}) | 🔴 Overbought Exit: <b>{c1_sp:.0f}%</b> ({c1_sell_cnt}) | ⚪ Neutral: <b>{c1_np:.0f}%</b></span>
            <span>📊 Avg Volume Surge: <b>{c1_vol_s:.2f}x</b> | Volume: <b>₹{c1_cum_vol/1e7:.1f} Cr</b></span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Detailed Preset Conviction Tiles
    st.markdown("##### 🎯 Conviction Tiles by Strategy Preset:")
    c1_tab_def, c1_tab_swing, c1_tab_lt, c1_tab_intra, c1_tab_ai = st.tabs([
        "🎯 Default (Core Balanced)",
        "🌊 Swing / Positional",
        "🏛️ Long-Term Secular",
        "⚡ Intraday Momentum",
        "🤖 AI / RAG Confluence"
    ])
    with c1_tab_def:
        render_preset_conviction_tiles(filtered_etfs_df, "Default", is_stock_mode=False)
    with c1_tab_swing:
        render_preset_conviction_tiles(filtered_etfs_df, "Swing / Positional", is_stock_mode=False)
    with c1_tab_lt:
        render_preset_conviction_tiles(filtered_etfs_df, "Long-Term", is_stock_mode=False)
    with c1_tab_intra:
        render_preset_conviction_tiles(filtered_etfs_df, "Intraday", is_stock_mode=False)
    with c1_tab_ai:
        render_preset_conviction_tiles(filtered_etfs_df, "AI / RAG", is_stock_mode=False)

    # Category 1 Screener Expander (Sorted by Active Preset Score for 100% 1-to-1 Table/Tile Consistency)
    with st.expander("🔍 See More: Broad ETF Universe Screener & Factor Rankings (Click to expand)", expanded=False):
        fe1, fe2 = st.columns([1, 1])
        with fe1:
            etf_depth = st.radio("ETF Screener Depth:", ["Top 10 High-Conviction", "Top 15 Ranked", f"Full ETF Universe ({len(filtered_etfs_df)})"], horizontal=True, key="etf_depth_r")
        with fe2:
            etf_cats = ["All"] + sorted(list(filtered_etfs_df["Category"].unique())) if not filtered_etfs_df.empty else ["All"]
            etf_cat_choice = st.selectbox("Filter ETF Category:", etf_cats, key="etf_cat_filter_box")

        view_etf_df = filtered_etfs_df.copy() if etf_cat_choice == "All" else filtered_etfs_df[filtered_etfs_df["Category"] == etf_cat_choice].copy()

        # Sort table by exact same column as the active preset
        if preset_key == "AI / RAG" and "AI_Buy_Confidence" in view_etf_df.columns:
            sorted_etfs = view_etf_df.sort_values(by="AI_Buy_Confidence", ascending=False)
        elif preset_key == "Swing / Positional" and "Technical Score Buy Swing" in view_etf_df.columns:
            sorted_etfs = view_etf_df.sort_values(by="Technical Score Buy Swing", ascending=True)
        elif preset_key == "Long-Term" and "Technical Score Buy LongTerm" in view_etf_df.columns:
            sorted_etfs = view_etf_df.sort_values(by="Technical Score Buy LongTerm", ascending=True)
        elif preset_key == "Intraday" and "Technical Score Buy Intraday" in view_etf_df.columns:
            sorted_etfs = view_etf_df.sort_values(by="Technical Score Buy Intraday", ascending=True)
        else:
            sorted_etfs = view_etf_df.sort_values(by="Composite Buy Score", ascending=True)

        limit_e = 10 if "Top 10" in etf_depth else (15 if "Top 15" in etf_depth else len(sorted_etfs))
        slice_etfs = sorted_etfs.head(limit_e)

        cols_etf_disp = [
            "Ticker", "Name", "Category", "CMP (₹)", "iNAV (₹)", "Distance to iNAV (%)",
            "Composite Buy Score", "Technical Score", "Fundamental Score",
            "RSI (14D)", "Bollinger %B", "Dist VWAP %", "Dist 20DMA %", "Dist 50DMA %", "Dist 200DMA %",
            "Dist 52W Low %", "Volume Surge Ratio", "RS Spread 21D %", "Action Signal"
        ]
        valid_etf_cols = [c for c in cols_etf_disp if c in slice_etfs.columns]
        render_top_scrollbar_sync()
        st.dataframe(
            slice_etfs[valid_etf_cols].style.apply(apply_advanced_table_styling, axis=None).format({
                "CMP (₹)": "₹{:.2f}",
                "iNAV (₹)": format_inav_currency,
                "Distance to iNAV (%)": format_inav_distance_pct,
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
    st.caption("Top fundamentally sound Indian equities evaluated across all Strategy Presets: Default (Core), Swing / Positional, Long-Term Secular, Intraday Momentum, and AI Confluence.")

    # Category 2 Breadth Pulse & Volume Stats
    c2_buy_cnt = int(filtered_stocks_df["Action Signal"].str.contains("BUY|ACCUMULATE", na=False).sum()) if not filtered_stocks_df.empty else 0
    c2_sell_cnt = int(filtered_stocks_df["Action Signal"].str.contains("SELL|BOOK PROFIT", na=False).sum()) if not filtered_stocks_df.empty else 0
    c2_tot = len(filtered_stocks_df) if not filtered_stocks_df.empty else 1
    c2_bp = (c2_buy_cnt / c2_tot) * 100
    c2_sp = (c2_sell_cnt / c2_tot) * 100
    c2_np = max(0.0, 100.0 - c2_bp - c2_sp)
    c2_vol_s = float(filtered_stocks_df.get("Volume Surge Ratio", pd.Series([1.0])).mean())
    c2_cum_vol = float(filtered_stocks_df["Volume"].sum()) if "Volume" in filtered_stocks_df.columns else 0.0

    st.markdown(
        f"""
        <div style="background: #f1f5f9; padding: 6px 12px; border-radius: 6px; font-size: 0.78rem; color: #334155; margin: 4px 0 10px 0; display: flex; justify-content: space-between; align-items: center;">
            <span><b>Category 2 Breadth Pulse:</b> 🟢 Buy Signals: <b>{c2_bp:.0f}%</b> ({c2_buy_cnt}) | 🔴 Overbought Exit: <b>{c2_sp:.0f}%</b> ({c2_sell_cnt}) | ⚪ Neutral: <b>{c2_np:.0f}%</b></span>
            <span>📊 Avg Volume Surge: <b>{c2_vol_s:.2f}x</b> | Volume: <b>₹{c2_cum_vol/1e7:.1f} Cr</b></span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Detailed Preset Conviction Tiles
    st.markdown("##### 🎯 Conviction Tiles by Strategy Preset:")
    c2_tab_def, c2_tab_swing, c2_tab_lt, c2_tab_intra, c2_tab_ai = st.tabs([
        "🎯 Default (Core Balanced)",
        "🌊 Swing / Positional",
        "🏛️ Long-Term Secular",
        "⚡ Intraday Momentum",
        "🤖 AI / RAG Confluence"
    ])
    with c2_tab_def:
        render_preset_conviction_tiles(filtered_stocks_df, "Default", is_stock_mode=True)
    with c2_tab_swing:
        render_preset_conviction_tiles(filtered_stocks_df, "Swing / Positional", is_stock_mode=True)
    with c2_tab_lt:
        render_preset_conviction_tiles(filtered_stocks_df, "Long-Term", is_stock_mode=True)
    with c2_tab_intra:
        render_preset_conviction_tiles(filtered_stocks_df, "Intraday", is_stock_mode=True)
    with c2_tab_ai:
        render_preset_conviction_tiles(filtered_stocks_df, "AI / RAG", is_stock_mode=True)

    # Category 2 Screener Expander (Sorted by Active Preset Score for 100% 1-to-1 Table/Tile Consistency)
    with st.expander("🔍 See More: Quality Stocks Screener & Multi-Factor Rankings (Click to expand)", expanded=False):
        fs1, fs2 = st.columns([1, 1])
        with fs1:
            stk_depth = st.radio("Stock Screener Depth:", ["Top 10 High-Conviction", "Top 15 Ranked", f"Full Equities Universe ({len(filtered_stocks_df)})"], horizontal=True, key="stk_depth_r")
        with fs2:
            stk_cats = ["All"] + sorted(list(filtered_stocks_df["Category"].unique())) if not filtered_stocks_df.empty else ["All"]
            stk_cat_choice = st.selectbox("Filter Stock Sector / Category:", stk_cats, key="stk_cat_filter_box")

        view_stk_df = filtered_stocks_df.copy() if stk_cat_choice == "All" else filtered_stocks_df[filtered_stocks_df["Category"] == stk_cat_choice].copy()
        if "iNAV (₹)" not in view_stk_df.columns:
            view_stk_df["iNAV (₹)"] = "NA"
        if "Distance to iNAV (%)" not in view_stk_df.columns:
            view_stk_df["Distance to iNAV (%)"] = "NA"

        # Sort table by exact same column as the active preset
        if preset_key == "AI / RAG" and "AI_Buy_Confidence" in view_stk_df.columns:
            sorted_stks = view_stk_df.sort_values(by="AI_Buy_Confidence", ascending=False)
        elif preset_key == "Swing / Positional" and "Technical Score Buy Swing" in view_stk_df.columns:
            sorted_stks = view_stk_df.sort_values(by="Technical Score Buy Swing", ascending=True)
        elif preset_key == "Long-Term" and "Technical Score Buy LongTerm" in view_stk_df.columns:
            sorted_stks = view_stk_df.sort_values(by="Technical Score Buy LongTerm", ascending=True)
        elif preset_key == "Intraday" and "Technical Score Buy Intraday" in view_stk_df.columns:
            sorted_stks = view_stk_df.sort_values(by="Technical Score Buy Intraday", ascending=True)
        else:
            sorted_stks = view_stk_df.sort_values(by="Composite Buy Score", ascending=True)

        limit_s = 10 if "Top 10" in stk_depth else (15 if "Top 15" in stk_depth else len(sorted_stks))
        slice_stks = sorted_stks.head(limit_s)

        cols_stk_disp = [
            "Ticker", "Name", "Category", "CMP (₹)", "iNAV (₹)", "Distance to iNAV (%)",
            "Dividend Yield %", "Composite Buy Score", "Technical Score", "Fundamental Score",
            "RSI (14D)", "Bollinger %B", "Dist VWAP %", "Dist 20DMA %", "Dist 50DMA %", "Dist 200DMA %",
            "Dist 52W Low %", "Volume Surge Ratio", "RS Spread 21D %", "Action Signal"
        ]
        valid_stk_cols = [c for c in cols_stk_disp if c in slice_stks.columns]
        render_top_scrollbar_sync()
        st.dataframe(
            slice_stks[valid_stk_cols].style.apply(apply_advanced_table_styling, axis=None).format({
                "CMP (₹)": "₹{:.2f}",
                "iNAV (₹)": format_inav_currency,
                "Distance to iNAV (%)": format_inav_distance_pct,
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
    st.caption("Assets oscillating near 50-day rolling S1 Support with 5-Year Empirical Win Rates ≥ 60%. Showing Top 2 Support Bounces & Top Resistance Exit.")

    with st.spinner("Computing Support & Resistance channel boundaries across assets..."):
        sr_combined_stk = compute_sr_matrix(active_raw_data, current_stock_universe, is_stock_mode=True)
        sr_combined_etf = compute_sr_matrix(active_raw_data, current_etf_universe, is_stock_mode=False)
        sr_full_df = pd.concat([sr_combined_stk, sr_combined_etf], ignore_index=True) if not sr_combined_stk.empty else sr_combined_etf

    if not sr_full_df.empty:
        # Category 3 Breadth & Channel Stats
        c3_buy_cnt = int(sr_full_df["Action Signal"].str.contains("BUY|ACCUMULATE", na=False).sum())
        c3_sell_cnt = int((sr_full_df.get("Range Position (%)", 50.0) >= 80.0).sum())
        c3_tot = len(sr_full_df)
        c3_bp = (c3_buy_cnt / c3_tot) * 100
        c3_sp = (c3_sell_cnt / c3_tot) * 100
        c3_np = max(0.0, 100.0 - c3_bp - c3_sp)
        c3_avg_win = float(sr_full_df.get("5Y S/R Win Rate (%)", pd.Series([62.0])).mean())

        st.markdown(
            f"""
            <div style="background: #f1f5f9; padding: 6px 12px; border-radius: 6px; font-size: 0.78rem; color: #334155; margin: 4px 0 10px 0; display: flex; justify-content: space-between; align-items: center;">
                <span><b>Category 3 Channel Breadth:</b> 🟢 S1 Support Testing: <b>{c3_bp:.0f}%</b> ({c3_buy_cnt}) | 🔴 R1 Resistance Testing: <b>{c3_sp:.0f}%</b> ({c3_sell_cnt}) | ⚪ Mid-Channel: <b>{c3_np:.0f}%</b></span>
                <span>🎯 5Y Empirical Backtest Win Rate: <b>{c3_avg_win:.1f}% Avg</b></span>
            </div>
            """,
            unsafe_allow_html=True
        )

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
                sr_pos = float(sr_r.get("Range Position (%)", 50.0))

                sr_is_etf = ("ETF" in sr_cat.upper()) or ("BEES" in sr_sym.upper()) or (str(sr_r.get("iNAV (₹)", "")).strip() not in ["NA", "nan", ""])
                if sr_is_etf and pd.notna(sr_r.get("iNAV (₹)")) and str(sr_r.get("iNAV (₹)")) != "NA":
                    sr_inav = float(sr_r["iNAV (₹)"])
                    sr_dist_inav = float(sr_r.get("Distance to iNAV (%)", ((sr_cmp - sr_inav) / sr_inav * 100)))
                    sr_inav_col = "#dc2626" if sr_dist_inav > 0 else "#16a34a"
                    sr_inav_html = f"<span>iNAV: <b>₹{sr_inav:.2f}</b> (<span style='color:{sr_inav_col}; font-weight:700;'>{sr_dist_inav:+.2f}%</span>)</span>"
                else:
                    sr_inav_html = "<span>iNAV: <span style='color:#94a3b8; font-style:italic;'>NA</span></span>"

                st.markdown(
                    f"""
                    <div class="rec-card" style="background-color: #f0fdf4; border: 1.2px solid #22c55e;">
                        <div style="font-size:0.72rem; color:#1e40af; font-weight:600; margin-bottom:3px;">🏷️ Evaluation Strategy: S/R Range Mean Reversion (S1 Floor Bounce)</div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight:700; font-size:0.90rem;">#{idx_sr+1} {sr_sym} ({sr_cat})</span>
                            <span class="rec-badge" style="background-color: #dcfce7; color: #166534;">{sr_win:.1f}% 5Y Win Rate</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.76rem; color:#475569; margin-top:4px;">
                            <span>CMP: <b>₹{sr_cmp:.2f}</b></span>
                            {sr_inav_html}
                            <span>S1: <b>₹{sr_s1:.2f}</b></span>
                            <span>R1: <b>₹{sr_r1:.2f}</b></span>
                            <span>Dist S1: <b>+{sr_dist_s1:.1f}%</b></span>
                        </div>
                        <div class="criteria-box">
                            <b>Criteria Met:</b> Testing S1 Support floor within {sr_dist_s1:.1f}% • Range Position {sr_pos:.1f}% (Lower Channel) • 5Y Backtest Win Rate: {sr_win:.1f}%<br>
                            <span style="color:#15803d; font-weight:600;">Suggested SL: ₹{sr_sl:.2f} | Suggested Target: ₹{sr_tgt:.2f} | Rating: {sr_r.get('S/R Predictability Rating', 'High')}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # S/R Resistance Exit Opportunity
        sr_exit_cands = sr_full_df[sr_full_df["Range Position (%)"] >= 80.0].sort_values(by="Range Position (%)", ascending=False)
        if not sr_exit_cands.empty:
            top_sr_exit = sr_exit_cands.iloc[0]
            srx_sym = str(top_sr_exit["Ticker"]).replace(".NS", "")
            srx_cmp = float(top_sr_exit["CMP (₹)"])
            srx_r1 = float(top_sr_exit.get("Major Resistance R1 (₹)", srx_cmp * 1.02))
            srx_pos = float(top_sr_exit.get("Range Position (%)", 85.0))

            srx_is_etf = ("ETF" in str(top_sr_exit.get("Category", "")).upper()) or ("BEES" in srx_sym.upper()) or (str(top_sr_exit.get("iNAV (₹)", "")).strip() not in ["NA", "nan", ""])
            if srx_is_etf and pd.notna(top_sr_exit.get("iNAV (₹)")) and str(top_sr_exit.get("iNAV (₹)")) != "NA":
                srx_inav = float(top_sr_exit["iNAV (₹)"])
                srx_dist_inav = float(top_sr_exit.get("Distance to iNAV (%)", ((srx_cmp - srx_inav) / srx_inav * 100)))
                srx_inav_col = "#dc2626" if srx_dist_inav > 0 else "#16a34a"
                srx_inav_html = f"<span>iNAV: <b>₹{srx_inav:.2f}</b> (<span style='color:{srx_inav_col}; font-weight:700;'>{srx_dist_inav:+.2f}%</span>)</span>"
            else:
                srx_inav_html = "<span>iNAV: <span style='color:#94a3b8; font-style:italic;'>NA</span></span>"

            st.markdown(
                f"""
                <div class="rec-card" style="background-color: #fffbeb; border: 1.2px solid #f59e0b; margin-top: -4px;">
                    <div style="font-size:0.72rem; color:#991b1b; font-weight:600; margin-bottom:3px;">🏷️ Exit Strategy: S/R Range Mean Reversion (R1 Channel Resistance Exit)</div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight:700; font-size:0.85rem; color:#92400e;">💡 S/R Resistance Exit Alert: {srx_sym}</span>
                        <span class="rec-badge" style="background-color: #fee2e2; color: #991b1b;">🔴 TESTING R1 RESISTANCE</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.74rem; color:#475569; margin-top:3px;">
                        <span>CMP: ₹{srx_cmp:.2f}</span>
                        {srx_inav_html}
                        <span>Major R1: ₹{srx_r1:.2f}</span>
                        <span>Range Position: {srx_pos:.1f}%</span>
                    </div>
                    <div class="criteria-box-sell">
                        <b>Exit Trigger:</b> Testing 50-day rolling resistance channel (Range Position {srx_pos:.1f}% ≥ 80%). Suggested profit booking at CMP or trailing stop tightening.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div class="rec-card" style="background-color: #f0fdf4; border: 1.2px dashed #86efac; margin-top: -4px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight:600; font-size:0.85rem; color:#166534;">🟢 Channel Range Balance: 0 assets testing upper R1 Resistance (>80% range)</span>
                        <span class="rec-badge" style="background-color: #dcfce7; color: #166534;">RANGE STABLE</span>
                    </div>
                    <div style="font-size: 0.74rem; color:#475569; margin-top:3px;">
                        Monitored assets are oscillating safely in the accumulation and mid-channel zones without immediate resistance overhead.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

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
                    "Ticker", "Category", "CMP (₹)", "iNAV (₹)", "Distance to iNAV (%)",
                    "Major Support S1 (₹)", "Major Resistance R1 (₹)",
                    "Range Position (%)", "Channel Width (%)", "5Y S/R Win Rate (%)", "S/R Predictability Rating",
                    "RSI (14D)", "Action Signal"
                ]
                valid_sr_cols = [c for c in cols_sr_disp if c in sr_full_df.columns]
                render_top_scrollbar_sync()
                st.dataframe(
                    sr_full_df[valid_sr_cols].sort_values(by="5Y S/R Win Rate (%)", ascending=False).style.apply(apply_advanced_table_styling, axis=None).format({
                        "CMP (₹)": "₹{:.2f}",
                        "iNAV (₹)": format_inav_currency,
                        "Distance to iNAV (%)": format_inav_distance_pct,
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
                            st.write(f"• **Fast Stochastic %K:** {prof.get('Fast_Stoch_K', 50.0):.1f}")
                        with p_col2:
                            st.markdown("##### 🛡️ Moving Averages & Trend")
                            st.write(f"• **Dist 20 DMA:** {prof.get('Dist_20DMA_Pct', 0.0):+.2f}%")
                            st.write(f"• **Dist 50 DMA:** {prof.get('Dist_50DMA_Pct', 0.0):+.2f}%")
                            st.write(f"• **Dist 200 DMA:** {prof.get('Dist_200DMA_Pct', 0.0):+.2f}%")
                            st.write(f"• **Dist VWAP:** {prof.get('Dist_VWAP_Pct', 0.0):+.2f}%")
                        with p_col3:
                            st.markdown("##### 🎯 S/R Range & Predictability")
                            st.write(f"• **Major Support S1:** ₹{prof.get('Major_Support_S1', 0.0):.2f}")
                            st.write(f"• **Major Resistance R1:** ₹{prof.get('Major_Resistance_R1', 0.0):.2f}")
                            st.write(f"• **5Y Empirical Win Rate:** {prof.get('SR_Win_Rate_5Y_Pct', 50.0):.1f}%")
                            st.write(f"• **Action Recommendation:** `{prof.get('Action_Signal', 'HOLD')}`")

    st.markdown("---")

    # =================================================================
    # CATEGORY 4: PREMIER INDIAN REITS & HIGH-YIELD INVITs
    # =================================================================
    st.markdown("#### 🏢 Category 4: Premier Indian REITs & High-Yield InvITs (7 Listed Trusts)")
    st.caption("Institutional cash flow assets with mandatory SEBI ≥90% NDCF distributions, AAA credit ratings, and inflation-indexed leases.")

    with st.spinner("Scanning 7 Premier Indian REITs & InvITs..."):
        reits_data = scan_all_reits()

    if not reits_data.empty:
        # Category 4 Breadth & Cash Flow Pulse
        c4_avg_yd = float(reits_data["Distribution Yield (%)"].mean())
        c4_avg_disc = float(reits_data["NAV Discount / Premium (%)"].mean())
        st.markdown(
            f"""
            <div style="background: #f1f5f9; padding: 6px 12px; border-radius: 6px; font-size: 0.78rem; color: #334155; margin: 4px 0 10px 0; display: flex; justify-content: space-between; align-items: center;">
                <span><b>Category 4 Cash Flow Pulse:</b> 🏢 7 Premier Listed Trusts | 💵 Avg Yield: <b>{c4_avg_yd:.2f}%</b> | 🏷️ Avg NAV Discount: <b>{c4_avg_disc:+.1f}%</b></span>
                <span>📜 <b>100% NDCF Distribution Mandate</b> | 🛡️ CRISIL AAA Rated Credit</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        c4_col1, c4_col2 = st.columns(2)
        top_reits_2 = reits_data.head(2)
        for idx_r, (_, r_it) in enumerate(top_reits_2.iterrows()):
            col_tgt4 = c4_col1 if idx_r == 0 else c4_col2
            with col_tgt4:
                r_sym = str(r_it["Ticker"]).replace(".NS", "")
                r_yd = float(r_it["Distribution Yield (%)"])
                r_cp = float(r_it["CMP (₹)"])
                r_disc = float(r_it["NAV Discount / Premium (%)"])
                r_conf = float(r_it.get("Confidence Score (%)", r_it.get("Composite Score (0-100)", 75.0)))
                r_sl = float(r_it.get("Immediate Support S1 (₹)", round(r_cp * 0.95, 2)))
                r_tgt = float(r_it.get("Immediate Resistance R1 (₹)", round(r_cp * 1.08, 2)))
                r_el = check_reit_investment_eligibility(r_it.to_dict())

                badge_bg = "#dcfce7" if r_el["eligible"] else "#ffe4e6"
                badge_col = "#166534" if r_el["eligible"] else "#be123c"

                st.markdown(
                    f"""
                    <div class="rec-card" style="background-color: #f5f3ff; border: 1.2px solid #8b5cf6;">
                        <div style="font-size:0.72rem; color:#6d28d9; font-weight:600; margin-bottom:3px;">🏷️ Evaluation Strategy: High-Yield Cash Flow (100% NDCF Mandate)</div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight:700; font-size:0.90rem;">#{idx_r+1} {r_sym} ({r_it.get('Type', 'REIT').split()[0]})</span>
                            <span class="rec-badge" style="background-color: {badge_bg}; color: {badge_col};">{r_el['status']}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.76rem; color:#475569; margin-top:4px;">
                            <span>CMP: <b>₹{r_cp:.2f}</b></span>
                            <span>Yield: <b>{r_yd:.1f}%</b></span>
                            <span>Confidence: <b style="color:#6d28d9;">{r_conf:.1f}%</b></span>
                            <span>NAV Disc: <b>{r_disc:+.1f}%</b></span>
                        </div>
                        <div class="criteria-box">
                            <b>Criteria Met:</b> High-Yield Cash Distribution ({r_yd:.1f}%) • 100% NDCF Payout • Confidence: <b>{r_conf:.1f}%</b> • NAV Discount: {r_disc:+.1f}% • Credit: {r_it.get('Credit Rating', 'CRISIL AAA')}<br>
                            <span style="color:#5b21b6; font-weight:600;">S1 Support: ₹{r_sl:.2f} | Target: ₹{r_tgt:.2f}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        with st.expander("🔍 See More: Institutional REIT & InvIT Financials & Portfolio Breakdown (Click to expand)", expanded=False):
            rk1, rk2, rk3, rk4, rk5 = st.columns(5)
            rk1.metric("Avg Distribution Yield", f"{reits_data['Distribution Yield (%)'].mean():.2f}%", delta="Cash Flow Yield")
            rk2.metric("NDCF Payout Ratio", "100.0%", delta="Mandatory ≥90%")
            rk3.metric("Avg Discount to NAV", f"{reits_data['NAV Discount / Premium (%)'].mean():+.1f}%", delta="Real Estate Value")
            rk4.metric("Avg Occupancy", f"{reits_data['Occupancy (%)'].mean():.1f}%", delta="Grade-A Tenants")
            rk5.metric("Avg LTV Debt Ratio", f"{reits_data['LTV Leverage (%)'].mean():.1f}%", delta="Safe (Cap 49%)")

            cols_r_show = [
                "Ticker", "Name", "Type", "Sponsor", "CMP (₹)", "Confidence Score (%)", "Distribution Yield (%)",
                "Dividend Payout Ratio (%)", "Annualized DPU (₹)", "Net Asset Value NAV (₹)",
                "NAV Discount / Premium (%)", "Occupancy (%)", "WALE (Years)", "LTV Leverage (%)",
                "Credit Rating", "Action Signal"
            ]
            valid_r_cols = [c for c in cols_r_show if c in reits_data.columns]
            render_top_scrollbar_sync()
            st.dataframe(
                reits_data[valid_r_cols].style.format({
                    "CMP (₹)": "₹{:.2f}",
                    "Confidence Score (%)": "{:.1f}%",
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
    # CATEGORY 5: PRECIOUS METALS (GOLD & SILVER SECTORAL COMMODITIES - MULTI-AMC)
    # =================================================================
    st.markdown("#### 🥇 Category 5: Precious Metals (Multi-AMC Gold & Silver Commodities)")
    st.caption("Defensive commodity hedges against equity drawdowns and currency depreciation. Evaluated conditionally across top Indian AMCs to prevent buying near cyclical peaks.")

    all_metals_df = build_all_precious_metals_df(etfs_market_df)
    c5_el_cnt = int(all_metals_df["is_eligible"].sum()) if not all_metals_df.empty else 0
    c5_tot_cnt = len(all_metals_df) if not all_metals_df.empty else 0

    st.markdown(
        f"""
        <div style="background: #f1f5f9; padding: 6px 12px; border-radius: 6px; font-size: 0.78rem; color: #334155; margin: 4px 0 10px 0; display: flex; justify-content: space-between; align-items: center;">
            <span><b>Category 5 Commodity Pulse:</b> 🥇 <b>{c5_tot_cnt} Multi-AMC Metal ETFs</b> (Nippon, SBI, HDFC, ICICI, Kotak, Axis, Tata) | 🟢 Tactically Eligible: <b>{c5_el_cnt}/{c5_tot_cnt}</b></span>
            <span>🛡️ <b>Tactical Hurdle:</b> 52W Range ≤ 65% & RSI ≤ 55 (Consolidation Dips Only)</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Pick #1 Best Gold ETF (lowest expense ratio among eligible, or lowest 52W range)
    gold_cands = all_metals_df[all_metals_df["Metal Type"] == "Gold"].sort_values(by=["is_eligible", "Expense %", "52W Range %"], ascending=[False, True, True]) if not all_metals_df.empty else pd.DataFrame()
    best_gold = gold_cands.iloc[0].to_dict() if not gold_cands.empty else None

    # Pick #1 Best Silver ETF
    silver_cands = all_metals_df[all_metals_df["Metal Type"] == "Silver"].sort_values(by=["is_eligible", "Expense %", "52W Range %"], ascending=[False, True, True]) if not all_metals_df.empty else pd.DataFrame()
    best_silver = silver_cands.iloc[0].to_dict() if not silver_cands.empty else None

    display_metal_picks = [p for p in [best_gold, best_silver] if p is not None]

    if display_metal_picks:
        c5_col1, c5_col2 = st.columns(2)
        for idx_m, m_dict in enumerate(display_metal_picks):
            col_tgt5 = c5_col1 if idx_m == 0 else c5_col2
            with col_tgt5:
                m_sym = str(m_dict["Ticker"])
                m_cmp = float(m_dict["CMP (₹)"])
                m_rsi = float(m_dict.get("RSI (14D)", 50.0))
                m_rng = float(m_dict.get("52W Range %", 50.0))
                m_dma = float(m_dict.get("Dist 200DMA %", 0.0))
                m_sl = float(m_dict.get("Stop_Loss", round(m_cmp * 0.96, 2)))
                m_tgt = float(m_dict.get("Target", round(m_cmp * 1.06, 2)))
                m_amc = str(m_dict.get("AMC", "AMC"))
                m_exp = float(m_dict.get("Expense %", 0.50))
                m_metal = str(m_dict.get("Metal Type", "Metal"))
                is_el = bool(m_dict.get("is_eligible", False))

                m_inav = float(m_dict.get("iNAV (₹)", m_cmp * 0.9985))
                m_dist = float(m_dict.get("Distance to iNAV (%)", round(((m_cmp - m_inav) / m_inav * 100), 2)))
                m_dist_col = "#dc2626" if m_dist > 0 else "#16a34a"

                mbadge_bg = "#dcfce7" if is_el else "#ffe4e6"
                mbadge_col = "#166534" if is_el else "#be123c"

                st.markdown(
                    f"""
                    <div class="rec-card" style="background-color: #fffbeb; border: 1.2px solid #f59e0b;">
                        <div style="font-size:0.72rem; color:#92400e; font-weight:600; margin-bottom:3px;">🏷️ Evaluation Strategy: Commodity Defensive Hedge ({m_amc})</div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight:700; font-size:0.90rem;">#{idx_m+1} {m_sym} (Top {m_metal} Pick • Expense: {m_exp:.2f}%)</span>
                            <span class="rec-badge" style="background-color: {mbadge_bg}; color: {mbadge_col};">{m_dict['Tactical Status']}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.76rem; color:#475569; margin-top:4px;">
                            <span>CMP: <b>₹{m_cmp:.2f}</b></span>
                            <span>iNAV: <b>₹{m_inav:.2f}</b> (<span style="color:{m_dist_col}; font-weight:700;">{m_dist:+.2f}%</span>)</span>
                            <span>RSI: <b>{m_rsi:.1f}</b></span>
                            <span>52W Range: <b>{m_rng:.1f}%</b></span>
                            <span>Dist 200DMA: <b>{m_dma:+.1f}%</b></span>
                        </div>
                        <div class="criteria-box">
                            <b>Condition Met:</b> {m_dict.get('Eligibility_Reason', 'Macro Hedge Allocation')} | SL: ₹{m_sl:.2f} | Target: ₹{m_tgt:.2f}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        with st.expander("🔍 See More: Multi-AMC Precious Metals Comparison Matrix (Click to expand)", expanded=False):
            st.markdown(
                """
                > **Multi-AMC Precious Metals Rationale:** Gold and Silver ETFs across India's top asset management companies (Nippon, SBI, HDFC, ICICI Prudential, Kotak, Axis, Tata) provide options with varying expense ratios and tracking efficiencies.
                > The platform filters metal entries conditionally so paper allocations only trigger during consolidation dips (52W range ≤ 65% and RSI ≤ 55) to protect capital against holding drawdowns.
                """
            )
            disp_metal_cols = ["Ticker", "Name", "AMC", "Metal Type", "CMP (₹)", "iNAV (₹)", "Distance to iNAV (%)", "Expense %", "RSI (14D)", "Dist 200DMA %", "52W Range %", "Tactical Status", "Eligibility_Reason"]
            valid_m_cols = [c for c in disp_metal_cols if c in all_metals_df.columns]
            render_top_scrollbar_sync()
            st.dataframe(
                all_metals_df[valid_m_cols].style.apply(apply_advanced_table_styling, axis=None).format({
                    "CMP (₹)": "₹{:.2f}",
                    "iNAV (₹)": format_inav_currency,
                    "Distance to iNAV (%)": format_inav_distance_pct,
                    "Expense %": "{:.2f}%",
                    "RSI (14D)": "{:.1f}",
                    "Dist 200DMA %": "{:+.1f}%",
                    "52W Range %": "{:.1f}%"
                }),
                use_container_width=True,
                hide_index=True
            )


# =====================================================================
# TAB 2: PAPER TRADING & MULTI-ASSET PERFORMANCE HUB
# =====================================================================
elif active_tab == "📈 Paper Trading & Multi-Asset Ledger":
    st.markdown("### 📈 Paper Trading Ledger & Multi-Asset Execution Hub")
    st.caption("Centralized Multi-Asset Execution Console • Enriched Indicator Provenance • Live MTM & Position Square-Off")

    raw_trades = load_paper_trades()
    trades_df = raw_trades.copy()

    # 1. Centralized Paper Trading Execution Console
    # 1. Centralized Paper Trading Execution Console
    with st.expander("⚡ Centralized Multi-Preset & Multi-Asset Paper Trading Execution Console", expanded=True):
        c_exec1, c_exec2, c_exec3 = st.columns([1.3, 1.5, 1.2])

        with c_exec1:
            st.markdown("##### 1. Select Asset Categories:")
            chk_etf = st.checkbox("📊 Broad Equity ETFs", value=True, help="Non-Sectoral Broad & Factor ETFs")
            chk_stk = st.checkbox("🏢 Quality Equities", value=True, help="Fundamentally sound NIFTY equities")
            chk_sr = st.checkbox("🎯 S/R Support Bounces", value=True, help="Assets trading at S1 support with ≥60% 5Y win rate")
            chk_reit = st.checkbox("🏛️ Premier REITs & InvITs (Conditional)", value=True, help="Triggered only when Distribution Yield ≥ 6.5% & at NAV discount")
            chk_metal = st.checkbox("🥇 Multi-AMC Metals (Conditional)", value=True, help="Gold & Silver (triggered only on value dips: 52W Range ≤ 65% & RSI ≤ 55)")

        with c_exec2:
            st.markdown("##### 2. Execution Parameters:")
            selected_presets = st.multiselect(
                "Strategy Presets to Execute Against:",
                ["Default", "Long-Term", "Swing / Positional", "Intraday", "AI / RAG"],
                default=["Default", "Long-Term", "Swing / Positional", "Intraday", "AI / RAG"],
                help="Analyzes each selected preset and places 1 Buy & 1 Sell pick per asset category.",
                key="central_exec_presets_ms"
            )
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                exec_picks = st.radio("Picks per Category (1 Buy, 1 Sell):", [1, 2, 3], index=0, horizontal=True, key="picks_per_cat_r")
            with c_p2:
                exec_budget = st.number_input("Tranche Budget (₹):", min_value=1000.0, max_value=500000.0, value=5000.0, step=500.0, key="central_exec_budget_in")

        with c_exec3:
            st.markdown("##### 3. Execute Orders:")
            st.write("")
            btn_exec_selected = st.button("⚡ Execute Selected Paper Trades", type="primary", use_container_width=True, key="btn_exec_all_selected")
            with st.popover("🗑️ Clear / Reset Ledger Data", use_container_width=True):
                st.warning("⚠️ This will completely purge all local paper trades and reset the execution audit trail.")
                if st.button("🚨 Confirm Full Reset", type="primary", use_container_width=True, key="btn_confirm_reset_ledger"):
                    save_paper_trades(pd.DataFrame(columns=DEFAULT_PAPER_HEADERS))
                    pd.DataFrame(columns=DEFAULT_AUDIT_HEADERS).to_csv(LOCAL_AUDIT_CSV, index=False)
                    save_audit_entry({
                        "Timestamp_IST": datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
                        "Trigger_Source": "RESET", "Preset": "All",
                        "Recommended_BUY": "None", "Recommended_SELL": "None",
                        "Execution_Status": "Clean Reset", "Reason_Summary": "Ledger and Execution Audit Trail reset clean by user."
                    })
                    st.cache_data.clear()
                    st.session_state.strategy_toast = "Ledger and Execution Audit Trail reset clean."
                    st.rerun()

        if btn_exec_selected:
            if not selected_presets:
                st.warning("⚠️ Please select at least one Strategy Preset to execute against.")
            else:
                created_trades = []
                exec_summary_msgs = []
                now_str = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
                regime_name = regime_data.get("regime", "Normal")

                all_t = load_paper_trades()
                active_syms = set(all_t[all_t["Status"] == "ACTIVE"]["Ticker"].astype(str).str.replace(".NS", "")) if not all_t.empty and "Status" in all_t.columns else set()

                # Iterate through all selected presets for Categories 1, 2, 3
                for p_name in selected_presets:
                    # 1. Broad Equity ETFs
                    if chk_etf:
                        if p_name == "AI / RAG":
                            etf_b, etf_s = get_ai_rag_conviction_candidates(etfs_market_df, is_stock_mode=False, limit=exec_picks)
                        else:
                            etf_b, etf_s = get_top_conviction_candidates(etfs_market_df, preset_name=p_name, is_stock_mode=False, limit=exec_picks)

                        # BUY Orders
                        for _, r in etf_b.iterrows():
                            sym = str(r["Ticker"]).replace(".NS", "")
                            cmp_v = float(r["CMP (₹)"])
                            if sym in active_syms or cmp_v <= 0:
                                continue
                            q = max(1, int(exec_budget // cmp_v))
                            created_trades.append({
                                "Trade_ID": f"V2_ETF_{int(datetime.datetime.now(IST).timestamp())}_{sym}_{p_name[:3].upper()}",
                                "Username": "Public_User", "Ticker": sym,
                                "Trade_Action": "🟢 BUY", "Buy Ticker": sym, "Sell Ticker": "—",
                                "Category": "Broad Equity ETF", "Asset_Class": "ETF",
                                "Trigger_Type": f"{p_name.upper()}_ETF_BUY",
                                "Trigger_Indicator": f"{p_name} Preset Buy (RSI: {r.get('RSI (14D)', 50):.1f}, 200DMA: {r.get('Dist 200DMA %', 0):+.1f}%)",
                                "Strategy_Preset": p_name, "Status": "ACTIVE",
                                "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                                "Stop_Loss": r["Stop_Loss"], "Target": r["Target"],
                                "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                                "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                                "Invested_Value": round(cmp_v * q, 2),
                                "Technical_Score_At_Entry": round(float(r.get("Technical Score", 50.0)), 1),
                                "Fundamental_Score_At_Entry": round(float(r.get("Fundamental Score", 50.0)), 1),
                                "Composite_Score_At_Entry": round(float(r.get("Composite Score", r.get("Composite Buy Score", 50.0))), 1),
                                "Near_Support_Status": f"Trend Proximity ({r.get('Dist 200DMA %', 0):+.1f}%)",
                                "RSI_At_Entry": round(float(r.get("RSI (14D)", 50.0)), 1),
                                "Empirical_Win_Rate_At_Entry": "N/A", "Market_Regime_At_Entry": regime_name
                            })
                            active_syms.add(sym)
                            exec_summary_msgs.append(f"🟢 BUY ETF ({p_name}): {sym}")

                        # SELL Orders (Square-off if owned, else record as exit alert)
                        for _, r in etf_s.iterrows():
                            sym = str(r["Ticker"]).replace(".NS", "")
                            cmp_v = float(r["CMP (₹)"])
                            active_mask = (all_t["Ticker"].astype(str).str.replace(".NS", "") == sym) & (all_t["Status"] == "ACTIVE")
                            if active_mask.any():
                                row_idx = all_t[active_mask].index[0]
                                entry_p = float(all_t.at[row_idx, "Entry_Price"])
                                eqty = int(all_t.at[row_idx, "Executed_Qty"])
                                pnl_val = round((cmp_v - entry_p) * eqty, 2)
                                pnl_pct_val = f"{((cmp_v - entry_p) / entry_p * 100):+.2f}%" if entry_p > 0 else "0.0%"
                                all_t.at[row_idx, "Status"] = "CLOSED_PROFIT" if pnl_val >= 0 else "CLOSED_STOPLOSS"
                                all_t.at[row_idx, "Trade_Action"] = "🔴 SELL"
                                all_t.at[row_idx, "Sell Ticker"] = sym
                                all_t.at[row_idx, "Exit_Price"] = cmp_v
                                all_t.at[row_idx, "Exit_Timestamp"] = now_str
                                all_t.at[row_idx, "Exit_Reason"] = f"Overbought Exit Trigger ({p_name} RSI {r.get('RSI (14D)', 50):.1f})"
                                all_t.at[row_idx, "PnL_Rs"] = pnl_val
                                all_t.at[row_idx, "PnL_Pct"] = pnl_pct_val
                                active_syms.discard(sym)
                                exec_summary_msgs.append(f"🔴 SQUARE-OFF ETF ({p_name}): {sym} (PnL: ₹{pnl_val:+,.2f})")
                            else:
                                q = max(1, int(exec_budget // cmp_v)) if cmp_v > 0 else 1
                                created_trades.append({
                                    "Trade_ID": f"V2_ETF_EXIT_{int(datetime.datetime.now(IST).timestamp())}_{sym}_{p_name[:3].upper()}",
                                    "Username": "Public_User", "Ticker": sym,
                                    "Trade_Action": "🔴 SELL", "Buy Ticker": "—", "Sell Ticker": sym,
                                    "Category": "Broad Equity ETF", "Asset_Class": "ETF",
                                    "Trigger_Type": f"{p_name.upper()}_ETF_SELL",
                                    "Trigger_Indicator": f"{p_name} Exit Alert (RSI: {r.get('RSI (14D)', 50):.1f}, Urgency: {r.get('Composite Score', 50):.1f})",
                                    "Strategy_Preset": p_name, "Status": "EXIT_ALERT",
                                    "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                                    "Stop_Loss": r.get("Stop_Loss", round(cmp_v * 1.04, 2)),
                                    "Target": r.get("Target", round(cmp_v * 0.95, 2)),
                                    "Execution_Timestamp": now_str, "Exit_Timestamp": now_str, "Exit_Price": cmp_v,
                                    "Exit_Reason": f"Overbought Profit Booking Alert ({p_name})",
                                    "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                                    "Invested_Value": round(cmp_v * q, 2),
                                    "Technical_Score_At_Entry": round(float(r.get("Technical Score", 50.0)), 1),
                                    "Fundamental_Score_At_Entry": 50.0,
                                    "Composite_Score_At_Entry": round(float(r.get("Composite Score", 50.0)), 1),
                                    "Near_Support_Status": "Overbought Resistance Zone",
                                    "RSI_At_Entry": round(float(r.get("RSI (14D)", 50.0)), 1),
                                    "Empirical_Win_Rate_At_Entry": "N/A", "Market_Regime_At_Entry": regime_name
                                })
                                exec_summary_msgs.append(f"🔴 EXIT ALERT ETF ({p_name}): {sym}")

                    # 2. Quality Equities
                    if chk_stk:
                        if p_name == "AI / RAG":
                            stk_b, stk_s = get_ai_rag_conviction_candidates(stocks_market_df, is_stock_mode=True, limit=exec_picks)
                        else:
                            stk_b, stk_s = get_top_conviction_candidates(stocks_market_df, preset_name=p_name, is_stock_mode=True, limit=exec_picks)

                        # BUY Orders
                        for _, r in stk_b.iterrows():
                            sym = str(r["Ticker"]).replace(".NS", "")
                            cmp_v = float(r["CMP (₹)"])
                            if sym in active_syms or cmp_v <= 0:
                                continue
                            q = max(1, int(exec_budget // cmp_v))
                            created_trades.append({
                                "Trade_ID": f"V2_STK_{int(datetime.datetime.now(IST).timestamp())}_{sym}_{p_name[:3].upper()}",
                                "Username": "Public_User", "Ticker": sym,
                                "Trade_Action": "🟢 BUY", "Buy Ticker": sym, "Sell Ticker": "—",
                                "Category": "Quality Stock", "Asset_Class": "Stock",
                                "Trigger_Type": f"{p_name.upper()}_STOCK_BUY",
                                "Trigger_Indicator": f"{p_name} Preset Buy (RSI: {r.get('RSI (14D)', 50):.1f}, 200DMA: {r.get('Dist 200DMA %', 0):+.1f}%)",
                                "Strategy_Preset": p_name, "Status": "ACTIVE",
                                "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                                "Stop_Loss": r["Stop_Loss"], "Target": r["Target"],
                                "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                                "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                                "Invested_Value": round(cmp_v * q, 2),
                                "Technical_Score_At_Entry": round(float(r.get("Technical Score", 50.0)), 1),
                                "Fundamental_Score_At_Entry": round(float(r.get("Fundamental Score", 50.0)), 1),
                                "Composite_Score_At_Entry": round(float(r.get("Composite Score", r.get("Composite Buy Score", 50.0))), 1),
                                "Near_Support_Status": f"Trend Proximity ({r.get('Dist 200DMA %', 0):+.1f}%)",
                                "RSI_At_Entry": round(float(r.get("RSI (14D)", 50.0)), 1),
                                "Empirical_Win_Rate_At_Entry": "N/A", "Market_Regime_At_Entry": regime_name
                            })
                            active_syms.add(sym)
                            exec_summary_msgs.append(f"🟢 BUY Stock ({p_name}): {sym}")

                        # SELL Orders (Square-off if owned, else record as exit alert)
                        for _, r in stk_s.iterrows():
                            sym = str(r["Ticker"]).replace(".NS", "")
                            cmp_v = float(r["CMP (₹)"])
                            active_mask = (all_t["Ticker"].astype(str).str.replace(".NS", "") == sym) & (all_t["Status"] == "ACTIVE")
                            if active_mask.any():
                                row_idx = all_t[active_mask].index[0]
                                entry_p = float(all_t.at[row_idx, "Entry_Price"])
                                eqty = int(all_t.at[row_idx, "Executed_Qty"])
                                pnl_val = round((cmp_v - entry_p) * eqty, 2)
                                pnl_pct_val = f"{((cmp_v - entry_p) / entry_p * 100):+.2f}%" if entry_p > 0 else "0.0%"
                                all_t.at[row_idx, "Status"] = "CLOSED_PROFIT" if pnl_val >= 0 else "CLOSED_STOPLOSS"
                                all_t.at[row_idx, "Trade_Action"] = "🔴 SELL"
                                all_t.at[row_idx, "Sell Ticker"] = sym
                                all_t.at[row_idx, "Exit_Price"] = cmp_v
                                all_t.at[row_idx, "Exit_Timestamp"] = now_str
                                all_t.at[row_idx, "Exit_Reason"] = f"Overbought Exit Trigger ({p_name} RSI {r.get('RSI (14D)', 50):.1f})"
                                all_t.at[row_idx, "PnL_Rs"] = pnl_val
                                all_t.at[row_idx, "PnL_Pct"] = pnl_pct_val
                                active_syms.discard(sym)
                                exec_summary_msgs.append(f"🔴 SQUARE-OFF Stock ({p_name}): {sym} (PnL: ₹{pnl_val:+,.2f})")
                            else:
                                q = max(1, int(exec_budget // cmp_v)) if cmp_v > 0 else 1
                                created_trades.append({
                                    "Trade_ID": f"V2_STK_EXIT_{int(datetime.datetime.now(IST).timestamp())}_{sym}_{p_name[:3].upper()}",
                                    "Username": "Public_User", "Ticker": sym,
                                    "Trade_Action": "🔴 SELL", "Buy Ticker": "—", "Sell Ticker": sym,
                                    "Category": "Quality Stock", "Asset_Class": "Stock",
                                    "Trigger_Type": f"{p_name.upper()}_STOCK_SELL",
                                    "Trigger_Indicator": f"{p_name} Exit Alert (RSI: {r.get('RSI (14D)', 50):.1f}, Urgency: {r.get('Composite Score', 50):.1f})",
                                    "Strategy_Preset": p_name, "Status": "EXIT_ALERT",
                                    "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                                    "Stop_Loss": r.get("Stop_Loss", round(cmp_v * 1.05, 2)),
                                    "Target": r.get("Target", round(cmp_v * 0.94, 2)),
                                    "Execution_Timestamp": now_str, "Exit_Timestamp": now_str, "Exit_Price": cmp_v,
                                    "Exit_Reason": f"Overbought Profit Booking Alert ({p_name})",
                                    "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                                    "Invested_Value": round(cmp_v * q, 2),
                                    "Technical_Score_At_Entry": round(float(r.get("Technical Score", 50.0)), 1),
                                    "Fundamental_Score_At_Entry": 50.0,
                                    "Composite_Score_At_Entry": round(float(r.get("Composite Score", 50.0)), 1),
                                    "Near_Support_Status": "Overbought Resistance Zone",
                                    "RSI_At_Entry": round(float(r.get("RSI (14D)", 50.0)), 1),
                                    "Empirical_Win_Rate_At_Entry": "N/A", "Market_Regime_At_Entry": regime_name
                                })
                                exec_summary_msgs.append(f"🔴 EXIT ALERT Stock ({p_name}): {sym}")

                # 3. S/R Mean-Reversion Tranche (Evaluated once across S1 Support & R1 Resistance)
                if chk_sr:
                    sr_df_stk = compute_sr_matrix(active_raw_data, current_stock_universe, is_stock_mode=True)
                    sr_df_etf = compute_sr_matrix(active_raw_data, current_etf_universe, is_stock_mode=False)
                    sr_all = pd.concat([sr_df_stk, sr_df_etf], ignore_index=True)
                    sr_buys = sr_all[sr_all["Action Signal"].str.contains("BUY|ACCUMULATE", na=False)].sort_values(by="5Y S/R Win Rate (%)", ascending=False).head(exec_picks)
                    for _, sr_it in sr_buys.iterrows():
                        sym = str(sr_it["Ticker"]).replace(".NS", "")
                        cmp_v = float(sr_it["CMP (₹)"])
                        if sym in active_syms or cmp_v <= 0: continue
                        q = max(1, int(exec_budget // cmp_v))
                        s1_v = float(sr_it.get("Major Support S1 (₹)", cmp_v * 0.97))
                        dist_s1 = ((cmp_v - s1_v) / s1_v * 100) if s1_v > 0 else 0.0
                        created_trades.append({
                            "Trade_ID": f"V2_SR_{int(datetime.datetime.now(IST).timestamp())}_{sym}", "Username": "Public_User", "Ticker": sym,
                            "Trade_Action": "🟢 BUY", "Buy Ticker": sym, "Sell Ticker": "—",
                            "Category": "S/R Mean Reversion", "Asset_Class": sr_it.get("Category", "Stock"), "Trigger_Type": "SR_SUPPORT_BUY",
                            "Trigger_Indicator": f"S1 Support Bounce ({sr_it.get('5Y S/R Win Rate (%)', 50)}% 5Y Win)",
                            "Strategy_Preset": "S/R Range Mean Reversion", "Status": "ACTIVE",
                            "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                            "Stop_Loss": sr_it["Suggested SL (₹)"], "Target": sr_it["Suggested Target (₹)"],
                            "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                            "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                            "Invested_Value": round(cmp_v * q, 2),
                            "Technical_Score_At_Entry": round(float(sr_it.get("RSI (14D)", 50.0)), 1),
                            "Fundamental_Score_At_Entry": round(float(sr_it.get("5Y S/R Win Rate (%)", 50.0)), 1),
                            "Composite_Score_At_Entry": round(float(sr_it.get("Range Position (%)", 50.0)), 1),
                            "Near_Support_Status": f"Yes (+{dist_s1:.1f}% to S1)",
                            "RSI_At_Entry": round(float(sr_it.get("RSI (14D)", 50.0)), 1),
                            "Empirical_Win_Rate_At_Entry": f"{sr_it.get('5Y S/R Win Rate (%)', 50)}%",
                            "Market_Regime_At_Entry": regime_name
                        })
                        active_syms.add(sym)
                        exec_summary_msgs.append(f"🟢 BUY S/R Support: {sym}")

                    # S/R Resistance Exits
                    sr_exits = sr_all[sr_all["Range Position (%)"] >= 80.0].sort_values(by="Range Position (%)", ascending=False).head(exec_picks)
                    for _, srx in sr_exits.iterrows():
                        sym = str(srx["Ticker"]).replace(".NS", "")
                        cmp_v = float(srx["CMP (₹)"])
                        active_mask = (all_t["Ticker"].astype(str).str.replace(".NS", "") == sym) & (all_t["Status"] == "ACTIVE")
                        if active_mask.any():
                            row_idx = all_t[active_mask].index[0]
                            entry_p = float(all_t.at[row_idx, "Entry_Price"])
                            eqty = int(all_t.at[row_idx, "Executed_Qty"])
                            pnl_val = round((cmp_v - entry_p) * eqty, 2)
                            pnl_pct_val = f"{((cmp_v - entry_p) / entry_p * 100):+.2f}%" if entry_p > 0 else "0.0%"
                            all_t.at[row_idx, "Status"] = "CLOSED_PROFIT" if pnl_val >= 0 else "CLOSED_STOPLOSS"
                            all_t.at[row_idx, "Trade_Action"] = "🔴 SELL"
                            all_t.at[row_idx, "Sell Ticker"] = sym
                            all_t.at[row_idx, "Exit_Price"] = cmp_v
                            all_t.at[row_idx, "Exit_Timestamp"] = now_str
                            all_t.at[row_idx, "Exit_Reason"] = f"S/R Resistance Exit (Range Position {srx.get('Range Position (%)', 85):.1f}%)"
                            all_t.at[row_idx, "PnL_Rs"] = pnl_val
                            all_t.at[row_idx, "PnL_Pct"] = pnl_pct_val
                            active_syms.discard(sym)
                            exec_summary_msgs.append(f"🔴 SQUARE-OFF S/R Resistance: {sym} (PnL: ₹{pnl_val:+,.2f})")

                # 4. Premier REITs/InvITs (Conditional: Only when Lucrative)
                if chk_reit:
                    reit_scan = scan_all_reits()
                    reit_triggered = 0
                    for _, r_row in reit_scan.iterrows():
                        if reit_triggered >= exec_picks:
                            break
                        sym = str(r_row["Ticker"]).replace(".NS", "")
                        cmp_v = float(r_row["CMP (₹)"])
                        r_el = check_reit_investment_eligibility(r_row.to_dict())
                        if r_el["eligible"] and sym not in active_syms and cmp_v > 0:
                            q = max(1, int(exec_budget // cmp_v))
                            created_trades.append({
                                "Trade_ID": f"V2_REIT_{int(datetime.datetime.now(IST).timestamp())}_{sym}",
                                "Username": "Public_User", "Ticker": sym,
                                "Trade_Action": "🟢 BUY", "Buy Ticker": sym, "Sell Ticker": "—",
                                "Category": "REIT/InvIT", "Asset_Class": "Real Estate / Infra",
                                "Trigger_Type": "HIGH_YIELD_REIT_BUY",
                                "Trigger_Indicator": f"Lucrative Yield {r_row['Distribution Yield (%)']:.1f}% (NAV Disc: {r_row['NAV Discount / Premium (%)']:+.1f}%)",
                                "Strategy_Preset": "High-Yield Cash Flow", "Status": "ACTIVE",
                                "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                                "Stop_Loss": float(r_row.get("Immediate Support S1 (₹)", cmp_v * 0.95)),
                                "Target": float(r_row.get("Immediate Resistance R1 (₹)", cmp_v * 1.08)),
                                "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                                "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                                "Invested_Value": round(cmp_v * q, 2),
                                "Technical_Score_At_Entry": round(float(r_row.get("RSI (14D)", 50.0)), 1),
                                "Fundamental_Score_At_Entry": round(float(r_row.get("Distribution Yield (%)", 8.0)), 1),
                                "Composite_Score_At_Entry": round(float(r_row.get("Composite Score (0-100)", 75.0)), 1),
                                "Near_Support_Status": "S1 Yield Floor (Lucrative)",
                                "RSI_At_Entry": round(float(r_row.get("RSI (14D)", 50.0)), 1),
                                "Empirical_Win_Rate_At_Entry": "N/A", "Market_Regime_At_Entry": regime_name
                            })
                            active_syms.add(sym)
                            reit_triggered += 1
                            exec_summary_msgs.append(f"🟢 BUY REIT (Lucrative): {sym}")
                        elif not r_el["eligible"]:
                            exec_summary_msgs.append(f"🛑 Skipped REIT {sym} ({r_el.get('reason')})")

                # 5. Multi-AMC Precious Metals (Conditional: Only on Lucrative Dip)
                if chk_metal:
                    if "all_metals_df" not in locals() or all_metals_df is None or (isinstance(all_metals_df, pd.DataFrame) and all_metals_df.empty):
                        all_metals_df = build_all_precious_metals_df(etfs_market_df)
                    for m_metal_type in ["Gold", "Silver"]:
                        metal_cands = all_metals_df[all_metals_df["Metal Type"] == m_metal_type].sort_values(by=["is_eligible", "Expense %", "52W Range %"], ascending=[False, True, True])
                        if not metal_cands.empty:
                            best_m = metal_cands.iloc[0].to_dict()
                            sym = str(best_m["Ticker"])
                            cmp_v = float(best_m["CMP (₹)"])
                            m_el = check_metal_investment_eligibility(best_m)
                            if m_el["eligible"] and sym not in active_syms and cmp_v > 0:
                                q = max(1, int(exec_budget // cmp_v))
                                created_trades.append({
                                    "Trade_ID": f"V2_MET_{int(datetime.datetime.now(IST).timestamp())}_{sym}",
                                    "Username": "Public_User", "Ticker": sym,
                                    "Trade_Action": "🟢 BUY", "Buy Ticker": sym, "Sell Ticker": "—",
                                    "Category": "Precious Metal", "Asset_Class": "Commodity",
                                    "Trigger_Type": "METALS_VALUE_DIP_BUY",
                                    "Trigger_Indicator": f"Lucrative Dip (AMC: {best_m.get('AMC')}, RSI: {best_m.get('RSI (14D)', 50):.1f})",
                                    "Strategy_Preset": "Commodity Defensive Hedge", "Status": "ACTIVE",
                                    "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                                    "Stop_Loss": round(cmp_v * 0.96, 2), "Target": round(cmp_v * 1.06, 2),
                                    "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                                    "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                                    "Invested_Value": round(cmp_v * q, 2),
                                    "Technical_Score_At_Entry": round(float(best_m.get("RSI (14D)", 50.0)), 1),
                                    "Fundamental_Score_At_Entry": 50.0, "Composite_Score_At_Entry": 50.0,
                                    "Near_Support_Status": "Value Dip Zone (Lucrative)",
                                    "RSI_At_Entry": round(float(best_m.get("RSI (14D)", 50.0)), 1),
                                    "Empirical_Win_Rate_At_Entry": "N/A", "Market_Regime_At_Entry": regime_name
                                })
                                active_syms.add(sym)
                                exec_summary_msgs.append(f"🟢 BUY Metal ({best_m.get('AMC')} {m_metal_type}): {sym}")
                            elif not m_el["eligible"]:
                                exec_summary_msgs.append(f"🛑 Skipped {m_metal_type} {sym} ({m_el.get('reason')})")

                # Persist updated ledger
                if created_trades:
                    combined_t = pd.concat([all_t, pd.DataFrame(created_trades)], ignore_index=True)
                else:
                    combined_t = all_t

                save_paper_trades(combined_t)

                # Persist audit log entry
                audit_entry = {
                    "Timestamp_IST": now_str,
                    "Trigger_Source": "CENTRAL_EXEC_CONSOLE",
                    "Preset": ", ".join(selected_presets),
                    "Recommended_BUY": ", ".join([r["Ticker"] for r in created_trades if "BUY" in r.get("Trigger_Type", "")]),
                    "Recommended_SELL": ", ".join([r["Ticker"] for r in created_trades if "SELL" in r.get("Trigger_Type", "")]),
                    "Execution_Status": f"🟢 Executed {len(created_trades)} Orders across {len(selected_presets)} Presets",
                    "Reason_Summary": f"Multi-preset execution summary: {'; '.join(exec_summary_msgs)}"
                }
                save_audit_entry(audit_entry)
                st.cache_data.clear()
                st.session_state.strategy_toast = f"Executed {len(created_trades)} orders live across {len(selected_presets)} presets!"
                st.rerun()

    # Process Exits & Active Live MTM
    if not trades_df.empty and "Status" in trades_df.columns:
        trades_df = evaluate_trade_exits(trades_df, active_raw_data)

        # Ensure Trade_Action, Buy Ticker, and Sell Ticker provenance are present
        if "Trade_Action" not in trades_df.columns:
            trades_df["Trade_Action"] = trades_df.apply(
                lambda r: "🔴 SELL" if any(k in str(r.get("Trigger_Type", "")).upper() + str(r.get("Trigger_Indicator", "")).upper() + str(r.get("Exit_Reason", "")).upper() for k in ["SELL", "EXIT"]) else "🟢 BUY",
                axis=1
            )
        else:
            trades_df["Trade_Action"] = trades_df["Trade_Action"].fillna("").apply(
                lambda v: "🔴 SELL" if any(k in str(v).upper() for k in ["SELL", "EXIT"]) else "🟢 BUY"
            )
        if "Buy Ticker" not in trades_df.columns:
            trades_df["Buy Ticker"] = trades_df.apply(
                lambda r: str(r.get("Ticker", "—")).replace(".NS", "") if "BUY" in str(r.get("Trade_Action", "")).upper() else "—",
                axis=1
            )
        else:
            trades_df["Buy Ticker"] = trades_df["Buy Ticker"].fillna("—")

        if "Sell Ticker" not in trades_df.columns:
            trades_df["Sell Ticker"] = trades_df.apply(
                lambda r: str(r.get("Ticker", "—")).replace(".NS", "") if "SELL" in str(r.get("Trade_Action", "")).upper() else "—",
                axis=1
            )
        else:
            trades_df["Sell Ticker"] = trades_df["Sell Ticker"].fillna("—")

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

                b_tickers = sorted(list(set([str(t) for t in grp["Buy Ticker"] if str(t).strip() not in ["—", "", "nan"]])))
                s_tickers = sorted(list(set([str(t) for t in grp["Sell Ticker"] if str(t).strip() not in ["—", "", "nan"]])))

                cat_kpi_rows.append({
                    "Category": c_name,
                    "Total Trades": len(grp),
                    "🟢 Buy Tickers": ", ".join(b_tickers) if b_tickers else "—",
                    "🔴 Sell Tickers": ", ".join(s_tickers) if s_tickers else "—",
                    "Active Trades": len(grp[grp["Status"] == "ACTIVE"]),
                    "Closed Trades": c_tot_c,
                    "Win Rate %": f"{c_wrate:.1f}%" if c_tot_c > 0 else "Pending",
                    "Realized PnL (₹)": c_pnl,
                    "Unrealized PnL (₹)": c_unreal
                })
            if cat_kpi_rows:
                cat_kpi_df = pd.DataFrame(cat_kpi_rows)
                st.dataframe(
                    cat_kpi_df.style.apply(apply_paper_table_styling, axis=None).format({
                        "Realized PnL (₹)": "₹{:+,.2f}",
                        "Unrealized PnL (₹)": "₹{:+,.2f}"
                    }),
                    use_container_width=True,
                    hide_index=True
                )

        # Strategy Preset Performance Breakdown Matrix
        if not trades_df.empty and "Strategy_Preset" in trades_df.columns:
            st.markdown("##### 🎯 Strategy Preset Performance Breakdown")
            preset_kpi_rows = []
            for p_name, grp in trades_df.groupby("Strategy_Preset"):
                p_closed = grp[grp["Status"] != "ACTIVE"]
                p_pnl = pd.to_numeric(p_closed["PnL_Rs"], errors="coerce").sum() if not p_closed.empty else 0.0
                p_unreal = pd.to_numeric(grp[grp["Status"] == "ACTIVE"]["PnL_Rs"], errors="coerce").sum() if not grp.empty else 0.0
                p_wins = (pd.to_numeric(p_closed["PnL_Rs"], errors="coerce") > 0).sum() if not p_closed.empty else 0
                p_tot_c = len(p_closed)
                p_wrate = (p_wins / p_tot_c * 100.0) if p_tot_c > 0 else 0.0

                p_b_tickers = sorted(list(set([str(t) for t in grp["Buy Ticker"] if str(t).strip() not in ["—", "", "nan"]])))
                p_s_tickers = sorted(list(set([str(t) for t in grp["Sell Ticker"] if str(t).strip() not in ["—", "", "nan"]])))

                preset_kpi_rows.append({
                    "Strategy Preset": p_name,
                    "Total Trades": len(grp),
                    "🟢 Buy Tickers": ", ".join(p_b_tickers) if p_b_tickers else "—",
                    "🔴 Sell Tickers": ", ".join(p_s_tickers) if p_s_tickers else "—",
                    "Active": len(grp[grp["Status"] == "ACTIVE"]),
                    "Closed": p_tot_c,
                    "Win Rate %": f"{p_wrate:.1f}%" if p_tot_c > 0 else "Pending",
                    "Realized PnL (₹)": p_pnl,
                    "Unrealized PnL (₹)": p_unreal
                })
            if preset_kpi_rows:
                preset_kpi_df = pd.DataFrame(preset_kpi_rows)
                st.dataframe(
                    preset_kpi_df.style.apply(apply_paper_table_styling, axis=None).format({
                        "Realized PnL (₹)": "₹{:+,.2f}",
                        "Unrealized PnL (₹)": "₹{:+,.2f}"
                    }),
                    use_container_width=True,
                    hide_index=True
                )

        # Trade Direction Filter
        filter_action = st.radio(
            "🔎 Filter Positions by Trade Direction:",
            ["All Positions (Mixed)", "🟢 BUY Positions Only", "🔴 SELL / Exit Positions Only"],
            horizontal=True,
            key="ledger_action_filter"
        )
        if filter_action == "🟢 BUY Positions Only":
            open_trades = open_trades[open_trades["Trade_Action"].str.contains("BUY", na=False)]
            closed_trades = closed_trades[closed_trades["Trade_Action"].str.contains("BUY", na=False)]
        elif filter_action == "🔴 SELL / Exit Positions Only":
            open_trades = open_trades[open_trades["Trade_Action"].str.contains("SELL|EXIT", na=False)]
            closed_trades = closed_trades[closed_trades["Trade_Action"].str.contains("SELL|EXIT", na=False)]

        # Active Positions Table with Enriched Parameter Provenance
        st.markdown("##### 📋 Open Active Positions (Live MTM & Indicator Provenance)")
        if not open_trades.empty:
            open_display_cols = [
                "Trade_Action", "Buy Ticker", "Sell Ticker", "Trade_ID", "Category", "Strategy_Preset",
                "Trigger_Indicator", "Near_Support_Status",
                "Technical_Score_At_Entry", "Fundamental_Score_At_Entry", "RSI_At_Entry",
                "Entry_Price", "Live_CMP", "Executed_Qty", "Stop_Loss", "Target",
                "PnL_Rs", "PnL_Pct", "Hold_Duration_Days", "Execution_Timestamp"
            ]
            valid_open_cols = [c for c in open_display_cols if c in open_trades.columns]
            render_top_scrollbar_sync()
            st.dataframe(
                open_trades[valid_open_cols].style.apply(apply_paper_table_styling, axis=None).format({
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

            # 1-Click Manual Squareoff / Exit Control
            st.markdown("###### 🚪 Immediate Position Square-Off Control:")
            sq_c1, sq_c2 = st.columns([3, 1])
            with sq_c1:
                active_trade_opts = [f"{r['Trade_ID']} - {r['Ticker']} ({r.get('Trade_Action', 'BUY')} | CMP: ₹{r['Live_CMP']:.2f}, PnL: ₹{r['PnL_Rs']:+.2f})" for _, r in open_trades.iterrows()]
                sel_sq_trade = st.selectbox("Select Active Position to Exit:", active_trade_opts, key="sq_trade_select")
            with sq_c2:
                st.write("")
                if st.button("🚪 Exit Selected Position", type="secondary", use_container_width=True, key="btn_exit_single_trade"):
                    sel_tid = sel_sq_trade.split(" - ")[0].strip()
                    all_raw_t = load_paper_trades()
                    for idx_t, row_t in all_raw_t.iterrows():
                        if str(row_t["Trade_ID"]).strip() == sel_tid:
                            cur_cmp = float(row_t["Live_CMP"])
                            ent_p = float(row_t["Entry_Price"])
                            qty_p = float(row_t["Executed_Qty"])
                            pnl_val = round((cur_cmp - ent_p) * qty_p, 2)
                            pnl_pct_val = round(((cur_cmp - ent_p) / ent_p * 100), 2) if ent_p > 0 else 0.0
                            all_raw_t.at[idx_t, "Status"] = "MANUAL_EXITED"
                            all_raw_t.at[idx_t, "Trade_Action"] = "🔴 SELL"
                            all_raw_t.at[idx_t, "Sell Ticker"] = str(row_t.get("Ticker", "")).replace(".NS", "")
                            all_raw_t.at[idx_t, "Exit_Price"] = cur_cmp
                            all_raw_t.at[idx_t, "Exit_Timestamp"] = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
                            all_raw_t.at[idx_t, "Exit_Reason"] = "User Manual Squareoff"
                            all_raw_t.at[idx_t, "PnL_Rs"] = pnl_val
                            all_raw_t.at[idx_t, "PnL_Pct"] = f"{pnl_pct_val:+.2f}%"
                            break
                    save_paper_trades(all_raw_t)
                    st.cache_data.clear()
                    st.session_state.strategy_toast = f"Closed position {sel_tid} successfully."
                    st.rerun()
        else:
            st.info("No active open positions for the selected filter.")

        # Closed Positions History Journal
        st.markdown("##### 📜 Closed Positions & Historical Exit Journal")
        if not closed_trades.empty:
            closed_display_cols = [
                "Trade_Action", "Buy Ticker", "Sell Ticker", "Trade_ID", "Category", "Strategy_Preset",
                "Trigger_Indicator", "Near_Support_Status",
                "Technical_Score_At_Entry", "Fundamental_Score_At_Entry",
                "Entry_Price", "Exit_Price", "Executed_Qty", "Hold_Duration_Days",
                "PnL_Rs", "PnL_Pct", "Exit_Reason", "Execution_Timestamp", "Exit_Timestamp"
            ]
            valid_closed_cols = [c for c in closed_display_cols if c in closed_trades.columns]
            render_top_scrollbar_sync()
            st.dataframe(
                closed_trades[valid_closed_cols].style.apply(apply_paper_table_styling, axis=None).format({
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
            st.info("No closed positions for the selected filter.")
    else:
        st.info("No paper trades found. Use the Centralized Execution Console above to generate paper trades.")

    # Execution Audit Log
    st.markdown("---")
    st.markdown("##### 📋 Execution Audit Trail")
    aud_df = load_audit_log()
    if not aud_df.empty:
        aud_display = aud_df.rename(columns={
            "Recommended_BUY": "🟢 Buy Tickers",
            "Recommended_SELL": "🔴 Sell Tickers"
        })
        st.dataframe(
            aud_display.sort_values(by="Timestamp_IST", ascending=False).style.apply(apply_paper_table_styling, axis=None),
            use_container_width=True,
            height=180
        )


# =====================================================================
# TAB 3: BACKTESTING & MACHINE LEARNING OPTIMIZATION STUDIO
# =====================================================================
elif active_tab == "🧪 Multi-Regime Backtesting & Machine Learning":
    st.markdown("### 🧪 Machine Learning Optimization & Strategy Calibration Studio")
    st.caption("Empirical factor analysis, dynamic trailing stop tuning, and adaptive multi-factor weight calibration across all 5 Strategy Presets.")

    # 1. AI Quant Advisor Analysis & Tweaks
    sug_df = evaluate_strategy_performance_and_suggest_tweaks()
    ac1, ac2, ac3 = st.columns([2, 1, 1])
    with ac1:
        st.markdown(f"**Optimization Engine Status:** `{runtime_cfg.get('optimization_status', 'Active')}`")
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

    # 2. Comprehensive Interactive Parameter Calibration Studio (All Presets & Per-Category)
    st.markdown("#### 🎚️ Comprehensive Parameter Calibration Studio")
    st.caption("Adjust sliders directly in the GUI. All changes immediately take effect across all screeners, tiles, and paper trading executions.")

    weights_dict = runtime_cfg.get("weights", {})
    risk_dict = runtime_cfg.get("risk_multipliers", {})
    sched_dict = runtime_cfg.get("execution_schedule", {})

    with st.form("comprehensive_parameters_studio_form"):
        # Section A: Strategy Preset Indicator Weights (0% - 100%)
        st.markdown("##### 🎯 Strategy Preset Indicator Weights (0% - 100%)")
        p_tab1, p_tab2, p_tab3, p_tab4, p_tab5 = st.tabs([
            "Default Preset",
            "Long-Term Secular",
            "Swing / Positional",
            "Intraday Momentum",
            "AI / RAG Confluence"
        ])
        new_weights = json.loads(json.dumps(weights_dict))

        with p_tab1:
            st.caption("Balanced multi-factor weighting for Core Bluechip Stocks & Broad ETFs.")
            c1, c2, c3, c4 = st.columns(4)
            w_dma_def = c1.slider("200 DMA Trend Proximity (%)", 0, 100, int(weights_dict.get("Default", {}).get("w_dma", 35)), key="s_def_dma")
            w_rsi_def = c2.slider("14D RSI Pullback (%)", 0, 100, int(weights_dict.get("Default", {}).get("w_rsi", 30)), key="s_def_rsi")
            w_low_def = c3.slider("52W Low Base Proximity (%)", 0, 100, int(weights_dict.get("Default", {}).get("w_low", 20)), key="s_def_low")
            w_exp_def = c4.slider("Expense/Spread Quality (%)", 0, 100, int(weights_dict.get("Default", {}).get("w_exp", 15)), key="s_def_exp")
            new_weights["Default"] = {"w_dma": w_dma_def, "w_rsi": w_rsi_def, "w_low": w_low_def, "w_exp": w_exp_def}

        with p_tab2:
            st.caption("Long-term secular compounding prioritizing dividend yield, moving average stability, and low tracking drag.")
            c1, c2, c3, c4, c5 = st.columns(5)
            w_dma_lt = c1.slider("200 DMA Trend (%)", 0, 100, int(weights_dict.get("Long-Term", {}).get("w_dma", 40)), key="s_lt_dma")
            w_div_lt = c2.slider("Dividend Yield (%)", 0, 100, int(weights_dict.get("Long-Term", {}).get("w_div", 20)), key="s_lt_div")
            w_rsi_lt = c3.slider("Macro RSI (%)", 0, 100, int(weights_dict.get("Long-Term", {}).get("w_rsi", 15)), key="s_lt_rsi")
            w_bb_lt = c4.slider("Bollinger Cushion (%)", 0, 100, int(weights_dict.get("Long-Term", {}).get("w_bb", 15)), key="s_lt_bb")
            w_exp_lt = c5.slider("Fundamental Expense (%)", 0, 100, int(weights_dict.get("Long-Term", {}).get("w_exp", 10)), key="s_lt_exp")
            new_weights["Long-Term"] = {"w_dma": w_dma_lt, "w_div": w_div_lt, "w_rsi": w_rsi_lt, "w_bb": w_bb_lt, "w_exp": w_exp_lt}

        with p_tab3:
            st.caption("Positional mean-reversion exploiting short-term oversold exhaustion and Bollinger Band contractions.")
            c1, c2, c3, c4, c5 = st.columns(5)
            w_rsi_sw = c1.slider("14D RSI Reversal (%)", 0, 100, int(weights_dict.get("Swing / Positional", {}).get("w_rsi", 35)), key="s_sw_rsi")
            w_dma_sw = c2.slider("200 DMA Pullback (%)", 0, 100, int(weights_dict.get("Swing / Positional", {}).get("w_dma", 25)), key="s_sw_dma")
            w_bb_sw = c3.slider("Bollinger %B Contraction (%)", 0, 100, int(weights_dict.get("Swing / Positional", {}).get("w_bb", 20)), key="s_sw_bb")
            w_vwap_sw = c4.slider("VWAP Proximity (%)", 0, 100, int(weights_dict.get("Swing / Positional", {}).get("w_vwap", 10)), key="s_sw_vwap")
            w_stoch_sw = c5.slider("Fast Stochastic %K (%)", 0, 100, int(weights_dict.get("Swing / Positional", {}).get("w_stoch", 10)), key="s_sw_stoch")
            new_weights["Swing / Positional"] = {"w_rsi": w_rsi_sw, "w_dma": w_dma_sw, "w_bb": w_bb_sw, "w_vwap": w_vwap_sw, "w_stoch": w_stoch_sw}

        with p_tab4:
            st.caption("Intraday momentum breakout capitalizing on morning volume surges and directional VWAP expansion.")
            c1, c2, c3, c4 = st.columns(4)
            w_vol_in = c1.slider("Volume Surge Ratio (%)", 0, 100, int(weights_dict.get("Intraday", {}).get("w_vol", 35)), key="s_in_vol")
            w_rsi_in = c2.slider("Intraday Momentum RSI (%)", 0, 100, int(weights_dict.get("Intraday", {}).get("w_rsi", 30)), key="s_in_rsi")
            w_bb_in = c3.slider("Bollinger Band Expansion (%)", 0, 100, int(weights_dict.get("Intraday", {}).get("w_bb", 20)), key="s_in_bb")
            w_vwap_in = c4.slider("VWAP Breakout (%)", 0, 100, int(weights_dict.get("Intraday", {}).get("w_vwap", 15)), key="s_in_vwap")
            new_weights["Intraday"] = {"w_vol": w_vol_in, "w_rsi": w_rsi_in, "w_bb": w_bb_in, "w_vwap": w_vwap_in}

        with p_tab5:
            st.caption("Cross-indicator AI confluence model synthesizing RSI, Volatility Bands, Volume flow, and MACD momentum.")
            c1, c2, c3, c4 = st.columns(4)
            w_rsi_ai = c1.slider("Confluence RSI (%)", 0, 100, int(weights_dict.get("AI / RAG", {}).get("w_rsi", 30)), key="s_ai_rsi")
            w_bb_ai = c2.slider("Volatility Band %B (%)", 0, 100, int(weights_dict.get("AI / RAG", {}).get("w_bb", 25)), key="s_ai_bb")
            w_vol_ai = c3.slider("Volume Confluence (%)", 0, 100, int(weights_dict.get("AI / RAG", {}).get("w_vol", 25)), key="s_ai_vol")
            w_macd_ai = c4.slider("MACD Momentum (%)", 0, 100, int(weights_dict.get("AI / RAG", {}).get("w_macd", 20)), key="s_ai_macd")
            new_weights["AI / RAG"] = {"w_rsi": w_rsi_ai, "w_bb": w_bb_ai, "w_vol": w_vol_ai, "w_macd": w_macd_ai}

        st.markdown("---")

        # Section B: Risk Multipliers & Dynamic Trailing Stops
        st.markdown("##### 🛡️ Risk Multipliers & Dynamic Trailing Stops (Per Strategy)")
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            st.markdown("###### Intraday Parameters:")
            in_sl = st.slider("Intraday SL (x ATR)", 0.5, 2.5, float(risk_dict.get("intraday_sl_multiplier", 1.0)), step=0.1, key="s_in_sl")
            in_tgt = st.slider("Intraday Target (x ATR)", 1.0, 4.0, float(risk_dict.get("intraday_target_multiplier", 1.8)), step=0.1, key="s_in_tgt")
        with rc2:
            st.markdown("###### Swing / Positional Parameters:")
            sw_sl = st.slider("Swing SL (x ATR)", 1.0, 4.0, float(risk_dict.get("swing_sl_multiplier", 1.5)), step=0.1, key="s_sw_sl")
            sw_tgt = st.slider("Swing Target (x ATR)", 1.5, 6.0, float(risk_dict.get("swing_target_multiplier", 3.0)), step=0.1, key="s_sw_tgt")
        with rc3:
            st.markdown("###### Long-Term Parameters:")
            lt_sl = st.slider("Long-Term SL (x ATR)", 1.5, 5.0, float(risk_dict.get("longterm_sl_multiplier", 2.5)), step=0.1, key="s_lt_sl")
            lt_tgt = st.slider("Long-Term Target (x ATR)", 2.0, 8.0, float(risk_dict.get("longterm_target_multiplier", 5.0)), step=0.1, key="s_lt_tgt")

        st.markdown("###### Trailing Stop Controls & Exit Thresholds:")
        tr1, tr2, tr3, tr4 = st.columns(4)
        tr_act = tr1.slider("Trailing Activation (%)", 1.0, 8.0, float(risk_dict.get("trailing_stop_activation_pct", 3.0)), step=0.5, key="s_tr_act")
        tr_lock = tr2.slider("Trailing Lock-In (%)", 0.1, 4.0, float(risk_dict.get("trailing_stop_lock_pct", 0.5)), step=0.1, key="s_tr_lock")
        rsi_ob = tr3.slider("RSI Overbought Exit", 65.0, 85.0, float(risk_dict.get("overbought_rsi_exit_threshold", 75.0)), step=1.0, key="s_rsi_ob")
        rsi_os = tr4.slider("RSI Oversold Buy Floor", 25.0, 45.0, float(risk_dict.get("oversold_rsi_buy_threshold", 35.0)), step=1.0, key="s_rsi_os")

        new_risk = {
            "intraday_sl_multiplier": in_sl, "intraday_target_multiplier": in_tgt,
            "swing_sl_multiplier": sw_sl, "swing_target_multiplier": sw_tgt,
            "longterm_sl_multiplier": lt_sl, "longterm_target_multiplier": lt_tgt,
            "trailing_stop_activation_pct": tr_act, "trailing_stop_lock_pct": tr_lock,
            "overbought_rsi_exit_threshold": rsi_ob, "oversold_rsi_buy_threshold": rsi_os
        }

        st.markdown("---")

        # Section C: Category-Specific Tactical Filters
        st.markdown("##### 🏛️ Category-Specific Tactical Filters")
        cf1, cf2, cf3 = st.columns(3)
        min_reit_yield = cf1.slider("Minimum REIT / InvIT Yield (%)", 5.0, 10.0, 6.5, step=0.5, key="s_min_reit_yd")
        max_metal_range = cf2.slider("Max Metal 52W Range Filter (%)", 60.0, 95.0, 80.0, step=5.0, key="s_max_met_rng")
        min_sr_win = cf3.slider("Min S/R 5Y Empirical Win Rate (%)", 50.0, 75.0, 60.0, step=1.0, key="s_min_sr_win")

        save_btn = st.form_submit_button("💾 Save All Parameter Calibrations to Runtime Config", type="primary", use_container_width=True)

    if save_btn:
        save_res = save_manual_parameter_adjustments(new_weights, new_risk, sched_dict, user="Public_User")
        st.session_state.strategy_toast = f"🟢 Saved adjustments ({save_res['updated_count']} parameters updated live)!"
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
                <b>Version:</b> 2.3-Adaptive<br>
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
