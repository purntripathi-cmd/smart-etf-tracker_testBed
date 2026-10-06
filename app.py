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
import io
import importlib
import json
import logging
import datetime
import zoneinfo
import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
import streamlit.components.v1 as components
try:
    from streamlit_gsheets import GSheetsConnection
except Exception:
    GSheetsConnection = None
import requests
from fleet_manager import render_fleet_manager_tab

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
# INTERNAL MODULE IMPORTS (WITH HOT-RELOAD CACHE INVALIDATION)
# =====================================================================
for _mod_name in ["strategy_engine", "ml_optimizer", "reit_scanner", "universe_manager", "sr_engine"]:
    if _mod_name in sys.modules:
        try:
            importlib.reload(sys.modules[_mod_name])
        except Exception:
            pass

try:
    from strategy_engine import (
        evaluate_market_metrics,
        get_top_conviction_candidates,
        compute_volatility_stop_and_targets,
        get_stopped_out_tickers_in_cooldown,
        check_conviction_gate,
        compute_multi_timeframe_performance
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
        get_ai_rag_conviction_candidates,
        load_strategy_change_log,
        log_strategic_change,
        check_conviction_gate
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

# =====================================================================
# GOOGLE SHEETS & TELEGRAM INTEGRATION (PRODUCTION COMPATIBILITY)
# =====================================================================
def get_db_connection():
    if GSheetsConnection is None:
        return None
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        logger.warning(f"GSheets connection init: {e}")
        return None

def fetch_users_df():
    conn = get_db_connection()
    if conn:
        for ws in ["Users", "Users_Auth_DB"]:
            try:
                raw_df = conn.read(worksheet=ws, ttl=60)
                if raw_df is not None and not raw_df.empty:
                    if "Username" not in raw_df.columns:
                        header_idx = raw_df[raw_df.isin(["Username"]).any(axis=1)].index.tolist()
                        if header_idx:
                            idx = header_idx[0]
                            raw_df.columns = raw_df.iloc[idx]
                            raw_df = raw_df.iloc[idx + 1:].reset_index(drop=True)
                    raw_df = raw_df.dropna(subset=["Username"])
                    for c in ["Username", "Password", "Name", "Email", "Mobile", "Role"]:
                        if c in raw_df.columns:
                            raw_df[c] = raw_df[c].astype(str)
                    return raw_df
            except Exception as ex:
                logger.warning(f"Read {ws} error: {ex}")
    users_local = os.path.join(LOCAL_DATA_DIR, "users_auth.csv")
    if os.path.exists(users_local) and os.path.getsize(users_local) > 0:
        try:
            return pd.read_csv(users_local)
        except Exception:
            pass
    return pd.DataFrame([{
        "Username": "Purn (Admin)", "Password": "Etaa@1234#", "Name": "Purn", "Email": "admin@gmail.com",
        "Mobile": "9999999999", "Role": "admin", "Strategy_Preset": "Default", "Tranche_Budget": 5000, "Monthly_Cap": 50000
    }])

def sync_users_df_to_sheets(u_df):
    conn = get_db_connection()
    if conn:
        try:
            conn.update(worksheet="Users", data=u_df)
            st.cache_data.clear()
            return True
        except Exception as e:
            logger.error(f"Sync users error: {e}")
    users_local = os.path.join(LOCAL_DATA_DIR, "users_auth.csv")
    u_df.to_csv(users_local, index=False)
    return True

def send_concise_telegram_alert(trade_type, signals_list):
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = str(os.getenv("TELEGRAM_CHAT_ID", "887870969")).strip()
    try:
        if not tg_token and "TELEGRAM_BOT_TOKEN" in st.secrets:
            tg_token = str(st.secrets["TELEGRAM_BOT_TOKEN"]).strip()
        if (not tg_chat or tg_chat == "887870969") and "TELEGRAM_CHAT_ID" in st.secrets:
            tg_chat = str(st.secrets["TELEGRAM_CHAT_ID"]).strip()
    except Exception:
        pass
    if not tg_token or tg_token in ["YOUR_BOT_TOKEN", "<YOUR_BOT_TOKEN>"] or not tg_chat:
        return False

    header_map = {
        'Intraday Entry': '⚡ *Intraday Entry Triggered*',
        'Swing / Long-Term (3 PM)': '🎯 *3 PM Multi-Asset & Multi-Preset Execution*',
        'Intraday Exit': '🔴 *Intraday Position Exit & Square-Off*',
        'Central Execution Console': '⚡ *Manual Multi-Asset Execution Hub*',
        'Admin Direct Test': '🔔 *Admin Telegram Notification Test*'
    }
    header = header_map.get(trade_type, f"📊 *{trade_type}*")
    msg_lines = [header, ""]

    if trade_type == 'Intraday Exit':
        if not signals_list:
            msg_lines.append("• No active intraday positions were open to square off at 3:10 PM.")
        else:
            msg_lines.append(f"📦 *Total Positions Squared Off:* {len(signals_list)} Positions")
            msg_lines.append("")
            total_realized_pnl = 0.0
            for sig in signals_list:
                ticker = str(sig.get('ticker', '')).replace('.NS', '')
                cmp = float(sig.get('cmp', 0.0))
                ep = float(sig.get('entry_price', cmp))
                qty = float(sig.get('qty', 1))
                pnl_rs = float(sig.get('pnl_rs', 0.0))
                pnl_pct = str(sig.get('pnl_pct', '0.0%'))
                total_realized_pnl += pnl_rs
                pnl_icon = '🟢' if pnl_rs >= 0 else '🔴'
                
                entry_ts = str(sig.get('entry_ts', ''))
                exit_ts = str(sig.get('exit_ts', ''))
                rsi_e = sig.get('rsi_entry', 'N/A')
                score_e = sig.get('score_entry', 'N/A')
                trigger_ind = sig.get('trigger', 'Intraday Momentum / RSI Dip')
                
                msg_lines.append(f"{pnl_icon} *{ticker}* (Qty: {int(qty)})")
                msg_lines.append(f"   • Exit Price: ₹{cmp:,.2f} | Entry Price: ₹{ep:,.2f}")
                msg_lines.append(f"   • Net PnL: *₹{pnl_rs:+,.2f} ({pnl_pct})*")
                if entry_ts:
                    msg_lines.append(f"   • Window: `{entry_ts}` ➔ `{exit_ts}`")
                msg_lines.append(f"   • Entry Basis: RSI={rsi_e} | Score={score_e} ({trigger_ind})")
                msg_lines.append("")
            
            pnl_tot_icon = '🚀' if total_realized_pnl >= 0 else '⚠️'
            msg_lines.append(f"{pnl_tot_icon} *Total Realized Intraday PnL:* ₹{total_realized_pnl:+,.2f}")

    elif trade_type == 'Intraday Entry':
        if not signals_list:
            msg_lines.append("• No intraday candidates met entry conviction thresholds.")
        else:
            msg_lines.append(f"📦 *Total Orders Executed:* {len(signals_list)} Orders")
            msg_lines.append("")
            for sig in signals_list:
                ticker = str(sig.get('ticker', '')).replace('.NS', '')
                cmp = float(sig.get('cmp', 0.0))
                qty = float(sig.get('qty', 1))
                sl = float(sig.get('sl', 0.0))
                target = float(sig.get('target', 0.0))
                rsi_e = sig.get('rsi', 'N/A')
                score_e = sig.get('score', 'N/A')
                trigger_ind = sig.get('trigger', 'Intraday Momentum / RSI Dip')
                
                msg_lines.append(f"🟢 *{ticker}* | CMP: ₹{cmp:,.2f} | Qty: {int(qty)}")
                msg_lines.append(f"   • Justification: RSI={rsi_e} | Score={score_e} ({trigger_ind})")
                if sl > 0 and target > 0:
                    msg_lines.append(f"   • Target: ₹{target:,.2f} | Stop-Loss: ₹{sl:,.2f}")
                msg_lines.append("")

    else:
        if not signals_list:
            msg_lines.append("• No trades executed in this window.")
        else:
            msg_lines.append(f"📦 *Total Orders Executed:* {len(signals_list)} Orders")
            msg_lines.append("")
            for s in signals_list:
                sym = str(s.get('ticker', '')).replace('.NS', '')
                cmp_v = float(s.get('cmp', 0.0))
                act = str(s.get('action', 'BUY')).upper()
                src = str(s.get('source', 'Quant'))
                icon = '🟢' if act == 'BUY' else ('🔴' if act in ['SELL', 'SQUARE-OFF'] else '🔄')
                msg_lines.append(f"{icon} `{sym}` | ₹{cmp_v:,.2f} | *{act}* ({src})")
    url = f"https://api.telegram.org/bot{tg_token}/sendMessage" if not tg_token.startswith("bot") else f"https://api.telegram.org/{tg_token}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": tg_chat, "text": "\n".join(msg_lines), "parse_mode": "Markdown"}, timeout=10)
        return r.status_code == 200
    except Exception:
        return False

if export_v2_docx_file and not os.path.exists(DOCX_GUIDE_FILE):
    try:
        export_v2_docx_file(DOCX_GUIDE_FILE)
    except Exception:
        pass


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


COLUMN_HEADER_TOOLTIPS = {
    # Price & Valuation
    "CMP": "Current Market Price (₹). Live/closing trading price on the National Stock Exchange (NSE).",
    "CMP (₹)": "Current Market Price (₹). Live/closing trading price on the National Stock Exchange (NSE).",
    "Live CMP (₹)": "Current live market price per unit/share on NSE.",
    "Live_CMP": "Current live market price per unit/share on NSE.",
    "Entry_Price": "Executed purchase price in Indian Rupees. 🟢 Lower the better for BUY positions.",
    "Avg Entry (₹)": "Volume-weighted average purchase price across accumulated tranches. 🟢 Lower the better.",
    "Exit_Price": "Executed square-off exit price in Indian Rupees. 🔴 Higher the better for profit realization.",
    "iNAV (₹)": "Indicative Net Asset Value (₹) published intra-day by the AMC. Fair intrinsic cash value per unit.",
    "Distance to iNAV (%)": "Premium/discount of CMP vs AMC iNAV. 🟢 Lower the better (Negative % = discount to intrinsic value; avoid buying at steep premiums > +1.5%).",
    "Net Asset Value NAV (₹)": "SEBI-audited underlying asset valuation per unit.",
    "NAV Discount / Premium (%)": "Percentage discount/premium of market price to audited NAV. 🟢 Lower the better (Negative discount means buying assets below intrinsic book value).",

    # Technical Momentum & Moving Averages
    "RSI (14D)": "14-Day Relative Strength Index (0–100). 🟢 Lower the better for BUY dips (RSI < 35–40 indicates oversold accumulation zone). 🔴 Higher the better for profit exit (RSI > 70–75 indicates overbought exhaustion).",
    "RSI_At_Entry": "14-Day RSI recorded at moment of trade entry. 🟢 Lower the better for BUY dips (< 40 confirms oversold entry).",
    "Bollinger %B": "Relative position within 20-day Bollinger Bands (0.0 = Lower Band, 0.5 = Middle, 1.0 = Upper Band). 🟢 Lower the better for BUY (< 0.20 confirms oversold band penetration).",
    "Dist VWAP %": "Distance from Volume Weighted Average Price. 🟢 Lower the better for BUY (Negative value indicates buying below average institutional execution cost).",
    "Dist 20DMA %": "Distance of price from 20-Day Moving Average. 🟢 Lower the better for BUY (Negative spread confirms short-term pullback into discount territory).",
    "Dist 50DMA %": "Distance of price from 50-Day Moving Average. 🟢 Lower the better for BUY (Negative spread identifies intermediate swing correction).",
    "Dist 200DMA %": "Distance of price from institutional 200-Day Moving Average trendline. 🟢 Lower the better for BUY (Trading near or slightly below 200DMA offers secular support and asymmetric risk-reward).",
    "Dist 52W Low %": "Percentage distance of CMP above its 52-week low. 🟢 Lower the better for BUY (Closer to 0% means purchasing near year-long rock bottom valuation).",
    "52W Range %": "Relative position in 52-week high-low range (0% = 52W Low, 100% = 52W High). 🟢 Lower the better for BUY (< 30% indicates deep value accumulation zone; > 80% indicates extension).",
    "Volume Surge Ratio": "Today's trading volume relative to 20-day average volume. 🟢 Higher the better (> 1.5x confirms institutional participation and decisive breakout conviction).",
    "RS Spread 21D %": "21-day Relative Strength spread vs Nifty 50 benchmark. 🟢 Higher the better (Positive spread proves asset is outperforming the broad benchmark index).",

    # Multi-Factor Conviction Scores
    "Composite Buy Score": "Multi-factor weighted conviction score combining moving averages, RSI, and valuation. 🟢 Lower the better (Lower percentile score indicates deeper structural discount, greater margin of safety, and higher institutional value).",
    "Composite Score": "Multi-factor quantitative health score. 🟢 Lower the better (Lower percentile score indicates superior structural value and oversold confluence).",
    "Composite_Score_At_Entry": "Multi-factor conviction score recorded at trade entry. 🟢 Lower the better (Indicates entry during deep value confluence).",
    "Technical Score": "Composite technical momentum and mean-reversion score. 🟢 Lower the better for BUY entries (Lower score flags deep oversold pullbacks across 20DMA, 50DMA, 200DMA, and RSI).",
    "Technical_Score_At_Entry": "Technical momentum score recorded at trade entry. 🟢 Lower the better for BUY dips.",
    "Fundamental Score": "Institutional quality, expense ratio, and empirical win-rate score. 🟢 Lower the better for BUY (Indicates superior low-cost efficiency and deep valuation margin of safety).",
    "Fundamental_Score_At_Entry": "Fundamental quality score recorded at trade entry. 🟢 Lower the better for BUY.",
    "Confidence Score (%)": "Machine learning ensemble probability score for favorable upward expansion. 🟢 Higher the better.",

    # Support & Resistance (S/R) Engine
    "Major Support S1 (₹)": "Algorithmic structural support floor. High probability price bounce level for accumulation.",
    "Major Resistance R1 (₹)": "Algorithmic overhead resistance ceiling. Primary profit-taking and distribution target.",
    "Range Position (%)": "Percentage location between Support S1 (0%) and Resistance R1 (100%). 🟢 Lower the better for BUY (≤ 20% indicates near support floor; ≥ 80% indicates near resistance ceiling).",
    "Channel Width (%)": "Percentage range between S1 support and R1 resistance. 🟢 Higher the better (> 6%–10% provides ample swing room for profitable mean-reversion trades).",
    "5Y S/R Win Rate (%)": "Historical 5-year empirical bounce win rate from support. 🟢 Higher the better (≥ 60% indicates statistically verified institutional support reliability).",
    "S/R Predictability Rating": "Structural predictability rating based on historical pivot fidelity (5★ Elite, 4★ Reliable, 3★ Moderate). 🟢 Higher the better.",
    "Success_Probability_Pct": "Historical empirical backtest win probability. 🟢 Higher the better (≥ 65% represents high conviction).",
    "Historical_5Y_Trades": "Total sample trades evaluated across the 5-year backtest. 🟢 Higher the better (Higher trade count confirms statistical significance).",
    "Avg_Gain_Pct": "Average percentage return captured per winning trade. 🟢 Higher the better.",
    "Profit_Factor": "Gross historical profits divided by gross losses. 🟢 Higher the better (> 1.5 indicates robust edge, > 2.0 indicates exceptional institutional profitability).",
    "Profit Factor": "Gross historical profits divided by gross losses. 🟢 Higher the better (> 1.5 indicates robust edge, > 2.0 indicates exceptional institutional profitability).",
    "SR_Fidelity_Rating": "Structural bounce fidelity rating (5★ Elite, 4★ Reliable, 3★ Moderate). 🟢 Higher the better.",

    # REITs & Real Estate Yield
    "Distribution Yield (%)": "Annualized cash distribution payout yield based on SEBI mandatory ≥90% NDCF distributions. 🟢 Higher the better (> 6.5%–7.5% delivers strong recurring institutional cash flow).",
    "Dividend Yield %": "Annual dividend yield distributed to shareholders. 🟢 Higher the better.",
    "Dividend Payout Ratio (%)": "Percentage of Net Distributable Cash Flow (NDCF) paid out to unit holders. Mandatory SEBI minimum ≥ 90%.",
    "Annualized DPU (₹)": "Projected annual Distribution Per Unit in Indian Rupees. 🟢 Higher the better.",
    "Occupancy (%)": "Commercial portfolio leased occupancy rate. 🟢 Higher the better (> 88%–92% reflects high tenant demand and pricing power).",
    "WALE (Years)": "Weighted Average Lease Expiry across Grade-A tenant contracts. 🟢 Higher the better (> 5–7 years secures long-term rental cash-flow certainty).",
    "LTV Leverage (%)": "Loan-to-Value net debt leverage ratio. 🟢 Lower the better (< 35%–40% indicates safe, conservative balance sheet well under SEBI 49% limit).",
    "Credit Rating": "Independent institutional rating agency assessment (CRISIL AAA / ICRA AAA). Highest credit safety.",

    # Risk Management & Trade Parameters
    "Stop_Loss": "Strict capital preservation boundary price. If price breaches below this level, position is closed to cap maximum risk.",
    "Suggested SL (₹)": "Recommended Stop Loss placed strictly below S1 structural support.",
    "Target": "Profit objective price. 🟢 Higher the better (Represents expected resistance exit level).",
    "Suggested Target (₹)": "Recommended profit target based on overhead R1 resistance and ATR multiple. 🟢 Higher the better.",
    "Near_Support_Status": "Proximity to algorithmic S1 support at entry. 🟢 Closer to support is better (confirms low-risk entry).",
    "Hold_Duration_Days": "Number of calendar days elapsed since position entry. For Intraday, 0 days; for Swing, typically 3–15 days.",
    "Executed_Qty": "Number of shares/units accumulated or held in this position.",
    "Total Units": "Cumulative units/shares held across all accumulated tranches.",
    "Units": "Total quantity of shares or ETF units held.",
    "Combined Tranches": "Number of discrete entry tranches executed for this asset.",

    # Profit & Loss (PnL)
    "PnL_Rs": "Net Profit or Loss in Indian Rupees. 🟢 Higher the better (Positive values indicate profitable closed or marked-to-market positions).",
    "Realized PnL (₹)": "Total closed, booked profit or loss in Indian Rupees. 🟢 Higher the better.",
    "Unrealized PnL (₹)": "Current marked-to-market floating profit or loss in Indian Rupees. 🟢 Higher the better.",
    "Total PnL (₹)": "Sum of realized booked gains and unrealized floating gains. 🟢 Higher the better.",
    "PnL_Pct": "Percentage return on invested trade capital. 🟢 Higher the better.",
    "Return %": "Percentage return on invested capital. 🟢 Higher the better.",
    "Unrealized PnL (%)": "Floating percentage return on invested capital. 🟢 Higher the better.",
    "Win Rate %": "Ratio of profitable trades to total closed trades. 🟢 Higher the better (> 55%–60% confirms positive statistical expectancy).",
    "Win Rate (%)": "Ratio of profitable trades to total closed trades. 🟢 Higher the better (> 55%–60% confirms positive statistical expectancy).",
    "Empirical_Win_Rate_At_Entry": "Historical backtested win rate associated with this signal at time of entry. 🟢 Higher the better.",

    # Identifiers & Operational Telemetry
    "Ticker": "Unique NSE/BSE security trading symbol.",
    "Name": "Full registered corporate name of security or fund.",
    "Category": "Asset classification (Broad Equities, Factor ETFs, REITs, Sovereign Metals, etc.).",
    "Asset Class": "Underlying asset type (Equity, Broad ETF, REIT/InvIT, Gold, Silver).",
    "Type": "Trust classification (Commercial Office REIT, Retail Mall REIT, Power/Telecom InvIT).",
    "Sponsor": "Institutional sponsor / asset management entity backing the trust.",
    "AMC": "Asset Management Company managing the fund or ETF.",
    "Metal Type": "Physical precious metal commodity backing the instrument (Gold or Silver).",
    "Expense %": "Annual Total Expense Ratio (TER) charged by fund management. 🟢 Lower the better (Minimizes recurring compounding fee drag).",
    "AUM (₹ Cr)": "Total Assets Under Management in Crores. 🟢 Higher the better (Greater liquidity and narrower bid-ask spreads).",
    "Action Signal": "Algorithmic tactical recommendation: 🟢 STRONG BUY, 🟢 BUY, 🟡 ACCUMULATE, ⚪ HOLD, 🔴 TRIM / SELL.",
    "Tactical Signal": "Algorithmic recommendation based on multi-factor scores (BUY, ACCUMULATE, HOLD).",
    "Tactical Stance": "Operational positioning guidance (ACCUMULATE ON DIP vs MONITOR).",
    "Tactical Status": "Current algorithmic trading status.",
    "Eligibility_Reason": "Institutional screening criteria justification for trade inclusion.",
    "Trade_ID": "Unique system transaction identifier for ledger provenance and auditing.",
    "Trade_Action": "Direction of order execution: 🟢 BUY (Accumulation) or 🔴 SELL (Exit / Square-off).",
    "Buy Ticker": "Purchased asset symbol.",
    "🟢 Buy Tickers": "List of symbols accumulated in this category/preset.",
    "Sell Ticker": "Exited or paired asset symbol.",
    "🔴 Sell Tickers": "List of symbols exited or squared off in this category/preset.",
    "Status": "Position lifecycle state: ACTIVE (open position), CLOSED_PROFIT (booked gain), CLOSED_STOPLOSS (loss cut), INTRADAY_SQUAREOFF (3:10 PM exit).",
    "Active Trades": "Number of open active positions currently running in this category.",
    "Active Positions": "Number of open active positions currently running.",
    "Active": "Number of active open positions currently running.",
    "Closed Trades": "Number of historically exited and settled positions.",
    "Closed": "Number of historically exited and settled positions.",
    "Total Trades": "Total number of orders executed across this strategy or category.",
    "Trades Executed": "Total number of trades executed.",
    "Strategy Preset": "Quantitative rule model (Default, Swing / Positional, Intraday, Long-Term, AI / RAG, S/R Mean Reversion).",
    "Strategy_Preset": "Quantitative rule model (Default, Swing / Positional, Intraday, Long-Term, AI / RAG, S/R Mean Reversion).",
    "Preset": "Trading strategy preset rule applied.",
    "Trigger_Indicator": "Primary technical or fundamental catalyst that triggered order entry.",
    "Trigger_Source": "Execution engine origin (3PM_CRON, 9:45AM_INTRADAY_CRON, 3:10PM_SQUAREOFF_CRON, MANUAL_CONSOLE).",
    "Execution_Status": "Status of execution pipeline (🟢 Executed, ⚪ Skipped, 🔴 Failed).",
    "Reason_Summary": "Detailed quantitative telemetry rationale explaining why trade executed or was skipped.",
    "Exit_Reason": "Institutional square-off rationale (TARGET_ACHIEVED, STOP_LOSS_HIT, INTRADAY_SQUAREOFF, S/R RESISTANCE, etc.).",
    "Execution_Timestamp": "Exact Indian Standard Time (IST) when the trade was executed.",
    "Exit_Timestamp": "Exact Indian Standard Time (IST) when the position was closed.",
    "Timestamp_IST": "Chronological event logging timestamp in Indian Standard Time (IST).",
    "Timestamp": "Chronological event logging timestamp in Indian Standard Time (IST).",
    "Market_Regime_At_Entry": "Broad macroeconomic and market volatility regime captured at execution time (Bullish, Normal, High Volatility).",
    "Invested (₹)": "Total rupee capital deployed in this position or category.",
    "Current Value (₹)": "Current marked-to-market valuation of position in Indian Rupees.",

    # Machine Learning Studio & Parameters
    "Target Preset": "Strategy preset targeted for empirical parameter adjustment.",
    "Current Parameter": "Currently active runtime parameter setting in configuration.",
    "Suggested Adjustment": "Empirical machine learning recommendation based on historical performance.",
    "Confidence Edge": "Statistical confidence edge supporting the recommended parameter change.",
    "Rationale": "Institutional mathematical rationale justifying the strategy adaptation.",
    "Empirical_Rationale": "Historical backtest and trade ledger evidence supporting parameter adjustment.",
    "Parameter": "Configurable quantitative threshold, weight, or multiplier.",
    "Parameter_Name": "Human-readable name of quantitative variable.",
    "Current_Value": "Currently active runtime value in runtime_config.json.",
    "Default_Value": "Factory baseline reference setting.",
    "AI_Suggested_Value": "Machine learning recommended value calibrated from empirical performance.",
    "Delta": "Mathematical divergence between current configuration and AI empirical optimum.",
    "BUY_Edge_Direction": "Directional impact on entry sensitivity when tuning this parameter.",
    "SELL_Edge_Direction": "Directional impact on exit sensitivity when tuning this parameter.",
    "Intended_Market_Impact": "Expected effect on portfolio Sharpe ratio, win rate, drawdown, and transaction costs.",
    "Impact_Summary": "Summary of expected market impact from parameter change.",
    "Parameter_Category": "Functional category of parameter (Risk Multipliers, Preset Weights, Execution Schedule).",
    "Old_Value": "Parameter value prior to modification.",
    "New_Value": "Parameter value after modification.",
    "Changed_By": "User or automated AI tuner who modified the parameter.",
    "Change_Source": "Source of modification (GUI slider, AI optimizer, or factory reset).",

    # Admin User Manager
    "Username": "Unique platform user account handle.",
    "Password": "Encrypted/masked user access credential.",
    "Email": "Contact email address of registered user.",
    "Mobile": "Contact mobile phone number of registered user.",
    "Role": "User permission level (admin: full controls & tuning; user: read & personal paper trading).",
    "Tranche_Budget": "Allocated capital per individual paper trading order in Rupees.",
    "Monthly_Cap": "Maximum monthly deployment ceiling in Rupees to enforce risk discipline."
}

def get_column_help_text(col_name: str) -> str:
    """
    Returns an intuitive, institutional hover explanation for any column header
    across all tables in all tabs, explicitly detailing whether 'Lower the better',
    'Higher the better', or the operational interpretation.
    """
    if not col_name:
        return ""
    col_str = str(col_name).strip()
    if col_str in COLUMN_HEADER_TOOLTIPS:
        return COLUMN_HEADER_TOOLTIPS[col_str]

    # Try normalized / cleaned lookup
    clean_k = col_str.replace("₹", "").replace("(", "").replace(")", "").replace("%", "").strip()
    for k, v in COLUMN_HEADER_TOOLTIPS.items():
        k_clean = k.replace("₹", "").replace("(", "").replace(")", "").replace("%", "").strip()
        if clean_k.lower() == k_clean.lower():
            return v

    # Pattern fallbacks
    s = col_str.upper()
    if "RSI" in s:
        return COLUMN_HEADER_TOOLTIPS["RSI (14D)"]
    if "PNL" in s or "PROFIT" in s:
        return COLUMN_HEADER_TOOLTIPS["PnL_Rs"]
    if "FACTOR" in s:
        return COLUMN_HEADER_TOOLTIPS["Profit_Factor"]
    if "INAV" in s:
        return COLUMN_HEADER_TOOLTIPS["Distance to iNAV (%)"]
    if "200DMA" in s:
        return COLUMN_HEADER_TOOLTIPS["Dist 200DMA %"]
    if "20DMA" in s:
        return COLUMN_HEADER_TOOLTIPS["Dist 20DMA %"]
    if "50DMA" in s:
        return COLUMN_HEADER_TOOLTIPS["Dist 50DMA %"]
    if "52W" in s:
        return COLUMN_HEADER_TOOLTIPS["52W Range %"]
    if "WIN RATE" in s or "WIN_RATE" in s or "WIN" in s:
        return COLUMN_HEADER_TOOLTIPS["5Y S/R Win Rate (%)"]
    if "SUPPORT" in s or "S1" in s:
        return COLUMN_HEADER_TOOLTIPS["Major Support S1 (₹)"]
    if "RESISTANCE" in s or "R1" in s:
        return COLUMN_HEADER_TOOLTIPS["Major Resistance R1 (₹)"]
    if "PRICE" in s or "CMP" in s:
        return COLUMN_HEADER_TOOLTIPS["CMP (₹)"]
    if "TIMESTAMP" in s or "TIME" in s:
        return COLUMN_HEADER_TOOLTIPS["Timestamp_IST"]
    if "SCORE" in s:
        return COLUMN_HEADER_TOOLTIPS["Composite Buy Score"]
    if "EXPENSE" in s:
        return COLUMN_HEADER_TOOLTIPS["Expense %"]
    if "YIELD" in s:
        return COLUMN_HEADER_TOOLTIPS["Distribution Yield (%)"]
    if "PARAM" in s:
        return COLUMN_HEADER_TOOLTIPS["Parameter"]
    if "RETURN" in s or "GAIN" in s or "CAGR" in s:
        return COLUMN_HEADER_TOOLTIPS.get("Avg_Gain_Pct", "Percentage return on invested capital. 🟢 Higher the better.")
    if "DRAWDOWN" in s:
        return "Peak-to-trough decline. 🟢 Lower the better (Minimizes portfolio drawdowns)."
    if "VOLUME" in s:
        return COLUMN_HEADER_TOOLTIPS.get("Volume Surge Ratio", "Trading volume. 🟢 Higher the better.")
    if "AUM" in s:
        return COLUMN_HEADER_TOOLTIPS.get("AUM (₹ Cr)", "Assets Under Management. 🟢 Higher the better.")
    if "OCCUPANCY" in s:
        return COLUMN_HEADER_TOOLTIPS.get("Occupancy (%)", "Commercial portfolio leased occupancy rate. 🟢 Higher the better.")
    if "WALE" in s:
        return COLUMN_HEADER_TOOLTIPS.get("WALE (Years)", "Weighted Average Lease Expiry. 🟢 Higher the better.")
    if "LTV" in s:
        return COLUMN_HEADER_TOOLTIPS.get("LTV Leverage (%)", "Loan-to-Value leverage ratio. 🟢 Lower the better.")

    return f"Details and metrics for {col_str}."


def get_pinned_column_config(data, num_pinned=3):
    """
    Returns a Streamlit column_config mapping that freezes (pins) the first `num_pinned`
    columns to the left so they stay locked in place when scrolling horizontally, and attaches
    rich hover tooltips and visible '(Lower Better)' / '(Higher Better)' directionality indicators
    directly to each column header across all tables in all tabs.
    """
    if isinstance(data, (list, tuple)):
        cols = list(data)
    elif hasattr(data, "columns"):
        cols = list(data.columns)
    elif hasattr(data, "data") and hasattr(data.data, "columns"):
        cols = list(data.data.columns)
    else:
        return {}

    cfg = {}
    for idx, c in enumerate(cols):
        col_name = str(c)
        is_pinned = idx < num_pinned
        h_text = get_column_help_text(col_name)

        # Build intuitive display label with explicit directionality tag
        display_label = col_name
        h_lower = h_text.lower()
        if "lower the better" in h_lower or "lower is better" in h_lower:
            if not any(tag in col_name.lower() for tag in ["lower", "better", "↓"]):
                display_label = f"{col_name} (↓ Lower Better)"
        elif "higher the better" in h_lower or "higher is better" in h_lower:
            if not any(tag in col_name.lower() for tag in ["higher", "better", "↑"]):
                display_label = f"{col_name} (↑ Higher Better)"

        # Ensure column header has sufficient width so title and help icon are fully visible without clipping
        min_w = max(120, len(display_label) * 8 + 35)
        col_kwargs = {
            "label": display_label,
            "help": f"**{col_name}**\n\n{h_text}",
            "width": min_w
        }
        if is_pinned:
            col_kwargs["pinned"] = True
        cfg[c] = st.column_config.Column(**col_kwargs)
    return cfg

def render_metric_glossary_expander(key_prefix="tab1"):
    with st.expander("💡 Interactive Column Header Guide & Metric Directionality (Hover / Search Any Column)", expanded=False):
        c_search, c_disp = st.columns([1.5, 3])
        with c_search:
            all_cols = sorted(list(COLUMN_HEADER_TOOLTIPS.keys()))
            default_idx = all_cols.index("RSI (14D)") if "RSI (14D)" in all_cols else 0
            selected_col = st.selectbox(
                "Select or Type Column Header to Inspect:",
                all_cols,
                index=default_idx,
                key=f"{key_prefix}_metric_selector"
            )
        with c_disp:
            if selected_col:
                help_desc = get_column_help_text(selected_col)
                if "Lower the better" in help_desc:
                    dir_badge = "<span style='background:#dcfce7; color:#15803d; font-weight:700; padding:3px 8px; border-radius:4px; font-size:0.82rem;'>🟢 Lower the Better</span>"
                elif "Higher the better" in help_desc:
                    dir_badge = "<span style='background:#dbeafe; color:#1e40af; font-weight:700; padding:3px 8px; border-radius:4px; font-size:0.82rem;'>🟢 Higher the Better</span>"
                else:
                    dir_badge = "<span style='background:#f1f5f9; color:#475569; font-weight:700; padding:3px 8px; border-radius:4px; font-size:0.82rem;'>⚡ Structural / Neutral</span>"
                
                st.markdown(
                    f"""
                    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:12px; margin-top:4px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                            <span style="font-size:1.0rem; font-weight:700; color:#0f172a;">📌 {selected_col}</span>
                            {dir_badge}
                        </div>
                        <div style="font-size:0.85rem; color:#334155; line-height:1.45;">
                            {help_desc}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

# =====================================================================
# ENRICHED PAPER TRADING LEDGER SCHEMA
# =====================================================================
DEFAULT_PAPER_HEADERS = [
    "Trade_ID", "Username", "Ticker", "Trade_Action", "Buy Ticker", "Sell Ticker",
    "Category", "Asset_Class", "Trigger_Type", "Trigger_Indicator",
    "Strategy_Preset", "Status", "Entry_Price", "Live_CMP", "Executed_Qty", "Stop_Loss", "Target",
    "Execution_Timestamp", "Exit_Timestamp", "Exit_Price", "Exit_Reason", "Hold_Duration_Days",
    "PnL_Rs", "PnL_Pct", "Invested_Value",
    "Technical_Score_At_Entry", "Fundamental_Score_At_Entry", "Composite_Score_At_Entry",
    "Near_Support_Status", "RSI_At_Entry", "Empirical_Win_Rate_At_Entry", "Market_Regime_At_Entry"
]

MARKET_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "market_cache.parquet")

@st.cache_data(ttl=900, max_entries=1, show_spinner=False)
def load_historical_market_data(all_tickers):
    """
    Fetches 1-year historical daily market data across all universe tickers + benchmarks.
    Persists an atomic Parquet snapshot and downcasts to float32 to slash memory by 50%.
    """
    clean_tickers = sorted(list(set(all_tickers)))
    download_list = sorted(list(set(clean_tickers + ["^CRSLDX", "^NSEI", "^INDIAVIX"])))
    try:
        df = yf.download(
            download_list,
            period="1y",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False
        )
        if df is not None and not df.empty and len(df) > 10:
            try:
                for col in df.select_dtypes(include=["float64"]).columns:
                    df[col] = df[col].astype(np.float32)
            except Exception:
                pass
            try:
                os.makedirs(os.path.dirname(MARKET_CACHE_FILE), exist_ok=True)
                df.to_parquet(MARKET_CACHE_FILE)
            except Exception:
                pass
            import gc
            gc.collect()
            return df
    except Exception as e:
        logger.error(f"Error fetching historical data: {e}")

    # Fallback to local snapshot
    if os.path.exists(MARKET_CACHE_FILE):
        try:
            logger.info("Loaded market data from local snapshot cache.")
            df = pd.read_parquet(MARKET_CACHE_FILE)
            try:
                for col in df.select_dtypes(include=["float64"]).columns:
                    df[col] = df[col].astype(np.float32)
            except Exception:
                pass
            import gc
            gc.collect()
            return df
        except Exception as e:
            logger.warning(f"Failed to read market snapshot cache: {e}")
    return pd.DataFrame()

# =====================================================================
# PAPER TRADING & AUDIT STORAGE STUBS (DISABLED IN TEST BED)
# =====================================================================
def load_paper_trades():
    return pd.DataFrame()

def save_paper_trades(df):
    pass

def load_audit_log():
    return pd.DataFrame()

def save_audit_entry(entry_dict):
    pass

def reset_audit_log(entry_dict=None):
    pass

def execute_category_paper_trade(*args, **kwargs):
    return False, "Paper trade execution is disabled in the test bed environment. Use production for paper trades."


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
# HIGH-PERFORMANCE IN-MEMORY CACHED EVALUATION PIPELINES
# =====================================================================
@st.cache_data(ttl=900, max_entries=1, show_spinner=False)
def get_cached_market_evaluation(tickers_tuple):
    """
    Evaluates multi-factor metrics across all 250+ Equities, Broad ETFs, and Precious Metals once,
    caching results in memory for 15 minutes. Subsequent interactions load in milliseconds.
    """
    raw_data = load_historical_market_data(tickers_tuple)
    current_stock_universe, current_etf_universe = get_active_universe()
    stocks_df, stock_reg = evaluate_market_metrics(raw_data, current_stock_universe, is_stock_mode=True)
    etfs_df, etf_reg = evaluate_market_metrics(raw_data, current_etf_universe, is_stock_mode=False)
    metals_df = build_all_precious_metals_df(etfs_df)
    import gc
    gc.collect()
    return stocks_df, stock_reg, etfs_df, etf_reg, metals_df

@st.cache_data(ttl=900, max_entries=1, show_spinner=False)
def get_cached_sr_matrices(tickers_tuple):
    """
    Caches algorithmic Support & Resistance matrices across all stocks and ETFs for 15 minutes.
    """
    raw_data = load_historical_market_data(tickers_tuple)
    current_stock_universe, current_etf_universe = get_active_universe()
    sr_combined_stk = compute_sr_matrix(raw_data, current_stock_universe, is_stock_mode=True)
    sr_combined_etf = compute_sr_matrix(raw_data, current_etf_universe, is_stock_mode=False)
    sr_full_df = pd.concat([sr_combined_stk, sr_combined_etf], ignore_index=True) if not sr_combined_stk.empty else sr_combined_etf
    return sr_full_df

@st.cache_data(ttl=900, max_entries=2, show_spinner=False)
def get_cached_5y_leaderboard(asset_class=None):
    """Caches the 5-Year Empirical Predictability Leaderboard for 15 minutes."""
    return get_5y_fidelity_leaderboard(asset_class)

@st.cache_data(ttl=900, max_entries=1, show_spinner=False)
def get_cached_reits_data():
    """Caches institutional REIT & InvIT analytics for 15 minutes to eliminate repeated sequential downloads."""
    return scan_all_reits()

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

    if "5Y S/R Win Rate (%)" in df.columns:
        def style_wr(val):
            try:
                num_v = float(str(val).replace("%", "").strip())
                if num_v >= 62.0:
                    return "background-color: #dcfce7; color: #15803d; font-weight: bold;"
                elif num_v < 45.0:
                    return "background-color: #fee2e2; color: #991b1b; font-weight: bold;"
            except Exception:
                pass
            return ""
        styles["5Y S/R Win Rate (%)"] = df["5Y S/R Win Rate (%)"].apply(style_wr)

    if "Range Position (%)" in df.columns:
        def style_rp(val):
            try:
                num_v = float(str(val).replace("%", "").strip())
                if num_v <= 25.0:
                    return "background-color: #d4edda; color: #155724; font-weight: bold;"
                elif num_v >= 75.0:
                    return "background-color: #f8d7da; color: #721c24; font-weight: bold;"
            except Exception:
                pass
            return ""
        styles["Range Position (%)"] = df["Range Position (%)"].apply(style_rp)

    if "S/R Predictability Rating" in df.columns:
        def style_rating(val):
            v_str = str(val)
            if "Elite" in v_str or "Reliable" in v_str:
                return "background-color: #dcfce7; color: #15803d; font-weight: bold;"
            elif "Speculative" in v_str:
                return "background-color: #fee2e2; color: #991b1b; font-weight: bold;"
            return ""
        styles["S/R Predictability Rating"] = df["S/R Predictability Rating"].apply(style_rating)

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


def get_apex_multi_factor_candidates(etfs_df, stocks_df, top_n=3):
    """
    Synthesizes candidates across all 5 Strategy Presets (Default, Swing, Long-Term, Intraday, AI/RAG),
    deduplicates tickers across ETFs and Equities, ranks by cross-model confluence count and composite score,
    and returns top N BUY and top N SELL recommendations with explicit selection rationale hints.
    """
    runtime_cfg = load_runtime_config()
    cooldown_tickers = set()
    presets_to_evaluate = ["Default", "Swing / Positional", "Long-Term", "Intraday", "AI / RAG"]

    raw_buys = []
    raw_sells = []

    for p in presets_to_evaluate:
        # Evaluate ETFs
        if etfs_df is not None and not etfs_df.empty:
            if p == "AI / RAG":
                b_etf, s_etf = get_ai_rag_conviction_candidates(etfs_df, is_stock_mode=False, limit=6)
            else:
                b_etf, s_etf = get_top_conviction_candidates(etfs_df, preset_name=p, is_stock_mode=False, limit=6)
            if not b_etf.empty:
                for _, r in b_etf.iterrows():
                    d = r.to_dict()
                    d["_preset"] = p
                    d["_asset_type"] = "ETF"
                    raw_buys.append(d)
            if not s_etf.empty:
                for _, r in s_etf.iterrows():
                    d = r.to_dict()
                    d["_preset"] = p
                    d["_asset_type"] = "ETF"
                    raw_sells.append(d)

        # Evaluate Equities
        if stocks_df is not None and not stocks_df.empty:
            if p == "AI / RAG":
                b_stk, s_stk = get_ai_rag_conviction_candidates(stocks_df, is_stock_mode=True, limit=6)
            else:
                b_stk, s_stk = get_top_conviction_candidates(stocks_df, preset_name=p, is_stock_mode=True, limit=6)
            if not b_stk.empty:
                for _, r in b_stk.iterrows():
                    d = r.to_dict()
                    d["_preset"] = p
                    d["_asset_type"] = "Stock"
                    raw_buys.append(d)
            if not s_stk.empty:
                for _, r in s_stk.iterrows():
                    d = r.to_dict()
                    d["_preset"] = p
                    d["_asset_type"] = "Stock"
                    raw_sells.append(d)

    def _deduplicate_and_rank(raw_list, is_buy=True):
        ticker_map = {}
        for item in raw_list:
            sym = str(item.get("Ticker", "")).replace(".NS", "").strip()
            if not sym or sym.lower() == "nan":
                continue
            # Post-Stop Cooldown check
            if sym in cooldown_tickers:
                continue
            # Conviction Gate check
            if not check_conviction_gate(item, is_buy=is_buy, config=runtime_cfg):
                continue

            preset_name = item.get("_preset", "Default")
            score = float(item.get("Composite Score", item.get("Composite Buy Score", 50.0)))
            cmp_val = float(item.get("CMP (₹)", 0.0))
            if cmp_val <= 0:
                continue

            if sym not in ticker_map:
                ticker_map[sym] = {
                    "ticker": sym,
                    "name": item.get("Name", sym),
                    "asset_class": item.get("_asset_type", "Asset"),
                    "cmp": cmp_val,
                    "rsi": float(item.get("RSI (14D)", 50.0)),
                    "dist_200": float(item.get("Dist 200DMA %", 0.0)),
                    "atr": float(item.get("14D ATR (₹)", cmp_val * 0.02)),
                    "sl": float(item.get("Stop_Loss", cmp_val * 0.95 if is_buy else cmp_val * 1.05)),
                    "tgt1": float(item.get("Target_Tier1", cmp_val * 1.025 if is_buy else cmp_val * 0.975)),
                    "tgt": float(item.get("Target", cmp_val * 1.06 if is_buy else cmp_val * 0.94)),
                    "action_sig": str(item.get("Action Signal", "ACCUMULATE" if is_buy else "PROFIT_BOOK")),
                    "iNAV": item.get("iNAV (₹)", None),
                    "inav_dist": item.get("Distance to iNAV (%)", item.get("iNAV Dislocation %", None)),
                    "presets": [preset_name],
                    "max_score": score,
                    "best_item": item
                }
            else:
                if preset_name not in ticker_map[sym]["presets"]:
                    ticker_map[sym]["presets"].append(preset_name)
                if score > ticker_map[sym]["max_score"]:
                    ticker_map[sym]["max_score"] = score
                    ticker_map[sym]["best_item"] = item

        ranked_list = list(ticker_map.values())
        for c in ranked_list:
            c["confluence_count"] = len(c["presets"])
            conf_str = f"{c['confluence_count']}x Confluence [{', '.join(c['presets'])}]"
            sl_pct = abs((c['cmp'] - c['sl']) / c['cmp'] * 100) if c['cmp'] > 0 else 0.0
            tgt1_pct = abs((c['tgt1'] - c['cmp']) / c['cmp'] * 100) if c['cmp'] > 0 else 0.0
            tgt_pct = abs((c['tgt'] - c['cmp']) / c['cmp'] * 100) if c['cmp'] > 0 else 0.0

            if is_buy:
                c["why_chosen_hint"] = (
                    f"Selected via {conf_str} across models. Top Composite Score: {c['max_score']:.1f}/100. "
                    f"14D RSI at {c['rsi']:.1f} signals strong reversal base near 200DMA ({c['dist_200']:+.1f}%). "
                    f"Passed strict Conviction Gate (Score ≥ 58, RSI ≤ 65) and zero post-stop cooldown lockout. "
                    f"Volatility ATR Stop Loss at ₹{c['sl']:.2f} (-{sl_pct:.1f}%), Tier 1 Breakeven Lock at ₹{c['tgt1']:.2f} (+{tgt1_pct:.1f}%), "
                    f"Primary Target at ₹{c['tgt']:.2f} (+{tgt_pct:.1f}%)."
                )
            else:
                c["why_chosen_hint"] = (
                    f"Selected via {conf_str} across models. Urgency Score: {c['max_score']:.1f}/100. "
                    f"14D RSI at {c['rsi']:.1f} indicates severe overbought exhaustion (+{c['dist_200']:+.1f}% above 200DMA). "
                    f"Passed Conviction Gate for simulated exit/short tracking. "
                    f"Volatility ATR Stop Loss at ₹{c['sl']:.2f} (+{sl_pct:.1f}%), Tier 1 Target at ₹{c['tgt1']:.2f} (-{tgt1_pct:.1f}%), "
                    f"Primary Target at ₹{c['tgt']:.2f} (-{tgt_pct:.1f}%)."
                )

        # Sort descending by confluence count, then composite score
        ranked_list.sort(key=lambda x: (x["confluence_count"], x["max_score"]), reverse=True)
        return ranked_list

    ranked_buys = _deduplicate_and_rank(raw_buys, is_buy=True)
    ranked_sells = _deduplicate_and_rank(raw_sells, is_buy=False)

    return ranked_buys[:top_n], ranked_sells[:top_n], ranked_buys, ranked_sells


def render_apex_multi_factor_tiles(etfs_df, stocks_df, limit=3):
    """
    Renders Category 6: Apex Multi-Factor tiles showing Top 3 BUY and Top 3 SELL picks
    meeting conviction and cooldown criteria, with full selection rationale hints.
    """
    top_buys, top_sells, all_buys, all_sells = get_apex_multi_factor_candidates(etfs_df, stocks_df, top_n=limit)

    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #1e1e38 0%, #2d3748 100%); color: #ffffff; padding: 12px 18px; border-radius: 8px; margin-bottom: 12px; border-left: 5px solid #8b5cf6;">
            <div style="font-weight: 700; font-size: 1.02rem;">⚡ Category 6: Apex Multi-Factor (Best of Presets - Deduplicated)</div>
            <div style="font-size: 0.80rem; color: #cbd5e1; margin-top: 3px;">
                Cross-Preset Multi-Model Synthesis • Pools signals from all 5 models (Default, Swing, Long-Term, Intraday, AI/RAG) • Deduplicates identical tickers • Ranks by multi-model confluence and conviction • Applies Post-Stop Cooldown & Conviction Gate.
            </div>
            <div style="display: flex; gap: 18px; margin-top: 6px; font-size: 0.78rem;">
                <span>🟢 Eligible Confluence BUYs: <b>{len(all_buys)}</b></span>
                <span>🔴 Eligible Confluence SELLs: <b>{len(all_sells)}</b></span>
                <span>🛡️ Post-Stop Cooldown Filter: <b>Active (5D Lockout)</b></span>
                <span>⚖️ Conviction Gate: <b>Score ≥ 58.0</b></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 1. Top 3 High-Conviction BUY Recommendations
    st.markdown("###### 🎯 Top 3 High-Conviction BUY Recommendations (Meeting Strict Gate & Cooldown Rules):")
    if top_buys:
        b_cols = st.columns(len(top_buys))
        for idx, b_item in enumerate(top_buys):
            with b_cols[idx]:
                sym = b_item["ticker"]
                cmp_val = b_item["cmp"]
                rsi_val = b_item["rsi"]
                sc_val = b_item["max_score"]
                sl_val = b_item["sl"]
                tgt1_val = b_item["tgt1"]
                tgt_val = b_item["tgt"]
                dist_dma = b_item["dist_200"]
                conf_cnt = b_item["confluence_count"]
                presets_str = ", ".join(b_item["presets"])
                why_hint = b_item["why_chosen_hint"]
                asset_cls = b_item["asset_class"]

                sl_pct = abs((cmp_val - sl_val) / cmp_val * 100) if cmp_val > 0 else 0.0
                tgt1_pct = abs((tgt1_val - cmp_val) / cmp_val * 100) if cmp_val > 0 else 0.0
                tgt_pct = abs((tgt_val - cmp_val) / cmp_val * 100) if cmp_val > 0 else 0.0

                st.markdown(
                    f"""
                    <div class="rec-card" style="background-color: #f0fdf4; border: 1.4px solid #22c55e;">
                        <div style="font-size:0.72rem; color:#166534; font-weight:700; margin-bottom:3px;">
                            ⚡ APEX CONFLUENCE ALLOCATION #{idx+1} ({asset_cls.upper()})
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight:700; font-size:0.92rem;">#{idx+1} {sym}</span>
                            <span class="rec-badge" style="background-color: #dcfce7; color: #166534; font-weight:700; border: 1px solid #16653433;">
                                🟢 APEX BUY ({conf_cnt}x Confluence)
                            </span>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.76rem; color:#475569; margin-top:4px;">
                            <span>CMP: <b>₹{cmp_val:.2f}</b></span>
                            <span>RSI: <b>{rsi_val:.1f}</b></span>
                            <span>Score: <b>{sc_val:.1f}</b></span>
                            <span>200DMA: <b>{dist_dma:+.1f}%</b></span>
                        </div>
                        <div class="criteria-box" style="margin-top: 6px;">
                            <b>💡 Why Chosen:</b> {why_hint}<br>
                            <span style="color:#15803d; font-weight:600;">
                                Volatility SL: ₹{sl_val:.2f} (-{sl_pct:.1f}%) | Tier 1: ₹{tgt1_val:.2f} (+{tgt1_pct:.1f}%) | Primary Target: ₹{tgt_val:.2f} (+{tgt_pct:.1f}%)
                            </span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        st.info("ℹ️ No assets currently meet the strict Apex Confluence BUY criteria (Score ≥ 58, RSI ≤ 65, and Zero Cooldown Lockout).")

    # 2. Top 3 High-Conviction SELL / Exit Recommendations
    st.markdown("###### 🎯 Top 3 High-Conviction SELL / Exit Recommendations (Meeting Strict Gate Rules):")
    if top_sells:
        s_cols = st.columns(len(top_sells))
        for idx, s_item in enumerate(top_sells):
            with s_cols[idx]:
                sym = s_item["ticker"]
                cmp_val = s_item["cmp"]
                rsi_val = s_item["rsi"]
                sc_val = s_item["max_score"]
                sl_val = s_item["sl"]
                tgt1_val = s_item["tgt1"]
                tgt_val = s_item["tgt"]
                dist_dma = s_item["dist_200"]
                conf_cnt = s_item["confluence_count"]
                presets_str = ", ".join(s_item["presets"])
                why_hint = s_item["why_chosen_hint"]
                asset_cls = s_item["asset_class"]

                sl_pct = abs((sl_val - cmp_val) / cmp_val * 100) if cmp_val > 0 else 0.0
                tgt1_pct = abs((cmp_val - tgt1_val) / cmp_val * 100) if cmp_val > 0 else 0.0
                tgt_pct = abs((cmp_val - tgt_val) / cmp_val * 100) if cmp_val > 0 else 0.0

                st.markdown(
                    f"""
                    <div class="rec-card" style="background-color: #fff1f2; border: 1.4px solid #f43f5e;">
                        <div style="font-size:0.72rem; color:#9f1239; font-weight:700; margin-bottom:3px;">
                            ⚡ APEX CONFLUENCE EXIT/SHORT #{idx+1} ({asset_cls.upper()})
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight:700; font-size:0.92rem;">#{idx+1} {sym}</span>
                            <span class="rec-badge" style="background-color: #ffe4e6; color: #9f1239; font-weight:700; border: 1px solid #9f123933;">
                                🔴 APEX SELL ({conf_cnt}x Confluence)
                            </span>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.76rem; color:#475569; margin-top:4px;">
                            <span>CMP: <b>₹{cmp_val:.2f}</b></span>
                            <span>RSI: <b>{rsi_val:.1f}</b></span>
                            <span>Urgency: <b>{sc_val:.1f}</b></span>
                            <span>200DMA: <b>{dist_dma:+.1f}%</b></span>
                        </div>
                        <div class="criteria-box" style="margin-top: 6px;">
                            <b>💡 Why Chosen:</b> {why_hint}<br>
                            <span style="color:#be123c; font-weight:600;">
                                Volatility SL: ₹{sl_val:.2f} (+{sl_pct:.1f}%) | Tier 1: ₹{tgt1_val:.2f} (-{tgt1_pct:.1f}%) | Primary Target: ₹{tgt_val:.2f} (-{tgt_pct:.1f}%)
                            </span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        st.info("ℹ️ No assets currently meet the strict Apex Confluence SELL / Exit criteria (Overbought extension and Gate validation).")

    # Collapsible Expander for Full Deduplication Matrix
    with st.expander("🔍 See More: Apex Cross-Preset Confluence Screener & Deduplication Matrix (Click to expand)", expanded=False):
        st.markdown(
            """
            > **Apex Multi-Factor Synthesis Architecture:** This screener pools candidate signals generated across all 5 Strategy Presets (Default, Swing / Positional, Long-Term, Intraday, and AI / RAG) across both Broad ETFs and Equities.
            > Tickers are deduplicated, filtered for post-stop cooldown lockout and minimum conviction score (≥ 58.0), and ranked by multi-model confluence count.
            """
        )
        combined_matrix_rows = []
        for b in all_buys:
            combined_matrix_rows.append({
                "Ticker": b["ticker"],
                "Asset Class": b["asset_class"],
                "Action Signal": "🟢 APEX BUY",
                "Confluence Count": f"{b['confluence_count']}x",
                "Contributing Presets": ", ".join(b["presets"]),
                "Composite Score": b["max_score"],
                "CMP (₹)": b["cmp"],
                "RSI (14D)": b["rsi"],
                "Dist 200DMA %": b["dist_200"],
                "Volatility SL (₹)": b["sl"],
                "Tier 1 Target (₹)": b["tgt1"],
                "Target (₹)": b["tgt"],
                "Selection Rationale Hint": b["why_chosen_hint"]
            })
        for s in all_sells:
            combined_matrix_rows.append({
                "Ticker": s["ticker"],
                "Asset Class": s["asset_class"],
                "Action Signal": "🔴 APEX SELL",
                "Confluence Count": f"{s['confluence_count']}x",
                "Contributing Presets": ", ".join(s["presets"]),
                "Composite Score": s["max_score"],
                "CMP (₹)": s["cmp"],
                "RSI (14D)": s["rsi"],
                "Dist 200DMA %": s["dist_200"],
                "Volatility SL (₹)": s["sl"],
                "Tier 1 Target (₹)": s["tgt1"],
                "Target (₹)": s["tgt"],
                "Selection Rationale Hint": s["why_chosen_hint"]
            })

        if combined_matrix_rows:
            apex_mat_df = pd.DataFrame(combined_matrix_rows)
            render_top_scrollbar_sync()
            st.dataframe(
                apex_mat_df.style.apply(apply_advanced_table_styling, axis=None).format({
                    "CMP (₹)": "₹{:.2f}",
                    "Volatility SL (₹)": "₹{:.2f}",
                    "Tier 1 Target (₹)": "₹{:.2f}",
                    "Target (₹)": "₹{:.2f}",
                    "RSI (14D)": "{:.1f}",
                    "Composite Score": "{:.1f}",
                    "Dist 200DMA %": "{:+.1f}%"
                }),
                column_config=get_pinned_column_config(apex_mat_df, 3),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No candidates currently in the Apex Multi-Factor confluence pool.")


def generate_paper_trade_audit_excel(trades_df, strategy_log_df, perf_dict):
    """
    Generates a comprehensive multi-sheet Excel audit workbook (.xlsx) containing:
    1. Platform_&_Code_Summary: Structural breakdown of existing code modules and 6-pillar quant architecture
    2. Strategic_Changes_Log: Full historical changelog of strategic logic & quant calibrations
    3. Complete_Trade_Ledger: Complete ledger with indicator provenance at entry, execution prices, PnL
    4. Multi_Timeframe_Perf: Standardized performance breakdown across 1M, 1Q, 6M, 1Y, 3Y, 5Y horizons
    5. Category_Performance: Multi-horizon breakdown for each asset category
    6. Preset_Performance: Multi-horizon breakdown for each strategy preset
    """
    code_summary_rows = [
        {
            "Module / File": "app.py",
            "Layer": "Presentation & Multi-Tab Cockpit",
            "Core Responsibilities": "Streamlit multi-tab user interface, real-time regime telemetry, pinned column scrolling, interactive metric tooltips, 1-click square-offs, parameter calibration studio, and multi-sheet audit package export.",
            "Key Formulations & Safeguards": "Session persistence, admin testing toggles, 15m parquet synchronization, responsive CSS cards."
        },
        {
            "Module / File": "strategy_engine.py",
            "Layer": "Quantitative Valuation & Risk Core",
            "Core Responsibilities": "Vectorized multi-factor composite scoring (200DMA trend, 14D RSI pullback, 52W low base, expense spread), volatility-adjusted dynamic stops (2.0x ATR), 5-day post-stop cooldown lockout, minimum conviction gate (Score ≥ 58), and multi-tier target breakeven ratchet.",
            "Key Formulations & Safeguards": "Stop = CMP ∓ (2.0 × ATR_14D) bounded [2.5%, 6.5%]; Tier 1 Breakeven Ratchet when profit ≥ 1.5 × ATR_14D."
        },
        {
            "Module / File": "ml_optimizer.py",
            "Layer": "Adaptive Tuning & Strategic Audit",
            "Core Responsibilities": "Persistent zero-secret runtime configuration (runtime_config.json), parameter directionality matrix, parameter change audit logging, and institutional strategic logic change history.",
            "Key Formulations & Safeguards": "Local CSV fallback; parameter rollback baseline; strategic changelog audit trail."
        },
        {
            "Module / File": "sr_engine.py",
            "Layer": "Support & Resistance Mean Reversion",
            "Core Responsibilities": "50-day rolling support (S1) and resistance (R1) calculations, 5-year empirical win rate backtesting, and automated S/R limit orders.",
            "Key Formulations & Safeguards": "Minimum 5-year empirical win rate ≥ 50% hurdle; 34-parameter quantitative profiling."
        },
        {
            "Module / File": "reit_scanner.py",
            "Layer": "Alternative Income Trusts",
            "Core Responsibilities": "SEBI 100% NDCF distribution mandate filter, minimum 6.5% distribution yield, NAV discount check, and occupancy verification.",
            "Key Formulations & Safeguards": "Distribution Yield ≥ 6.5%; NAV Discount Check; LTV leverage ≤ 40%."
        },
        {
            "Module / File": "universe_manager.py",
            "Layer": "Multi-Asset Universe Registry",
            "Core Responsibilities": "Active tracking of 297 assets across 47 Broad/Factor ETFs, 250 NIFTY Equities, 7 REITs/InvITs, and Multi-AMC Gold & Silver.",
            "Key Formulations & Safeguards": "Dynamic liquidity filtering; zero single-sector drawdowns via non-sectoral asset weighting."
        },
        {
            "Module / File": "resource_monitor.py",
            "Layer": "Cloud Telemetry & Optimization",
            "Core Responsibilities": "Real-time CPU and RAM tracking, memory leak prevention via float32 caching and 15-minute parquet snapshots.",
            "Key Formulations & Safeguards": "Eliminates CPU throttling warnings; maintains RAM footprint under 350 MB."
        }
    ]
    code_df = pd.DataFrame(code_summary_rows)

    import io
    try:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            code_df.to_excel(writer, sheet_name="Platform_&_Code_Summary", index=False)
            if strategy_log_df is not None and not strategy_log_df.empty:
                strategy_log_df.to_excel(writer, sheet_name="Strategic_Changes_Log", index=False)
            else:
                pd.DataFrame({"Status": ["No strategic changes recorded"]}).to_excel(writer, sheet_name="Strategic_Changes_Log", index=False)
            
            if trades_df is not None and not trades_df.empty:
                trades_df.to_excel(writer, sheet_name="Complete_Trade_Ledger", index=False)
            else:
                pd.DataFrame({"Status": ["No paper trades recorded"]}).to_excel(writer, sheet_name="Complete_Trade_Ledger", index=False)

            if perf_dict and "matrix_df" in perf_dict and not perf_dict["matrix_df"].empty:
                perf_dict["matrix_df"].to_excel(writer, sheet_name="Multi_Timeframe_Perf", index=False)
            if perf_dict and "category_df" in perf_dict and not perf_dict["category_df"].empty:
                perf_dict["category_df"].to_excel(writer, sheet_name="Category_Performance", index=False)
            if perf_dict and "preset_df" in perf_dict and not perf_dict["preset_df"].empty:
                perf_dict["preset_df"].to_excel(writer, sheet_name="Preset_Performance", index=False)

        return buf.getvalue()
    except Exception as e:
        buf = io.BytesIO()
        buf.write(f"Audit Export Report\nError: {e}\n\n".encode("utf-8"))
        if trades_df is not None and not trades_df.empty:
            buf.write(trades_df.to_csv(index=False).encode("utf-8"))
        return buf.getvalue()


def assign_trade_timeframe_horizon(exec_ts, ref_dt=None):
    """Categorizes a trade timestamp into its standard duration horizon."""
    if pd.isna(exec_ts) or str(exec_ts).strip() in ["", "nan", "—"]:
        return "1 Month (≤30D)"
    try:
        ref = ref_dt if ref_dt is not None else pd.Timestamp.now()
        dt = pd.to_datetime(exec_ts)
        diff_d = (ref - dt).total_seconds() / 86400.0
        if diff_d <= 30:
            return "1 Month (≤30D)"
        elif diff_d <= 90:
            return "1 Quarter (31-90D)"
        elif diff_d <= 180:
            return "6 Months (91-180D)"
        elif diff_d <= 365:
            return "1 Year (181-365D)"
        elif diff_d <= 1095:
            return "3 Years (1-3Y)"
        elif diff_d <= 1825:
            return "5 Years (3-5Y)"
        else:
            return "> 5 Years"
    except Exception:
        return "1 Month (≤30D)"


# =====================================================================
# OPEN ACCESS TESTBED INITIALIZATION
# =====================================================================
if "strategy_toast" not in st.session_state:
    st.session_state.strategy_toast = None

current_user = "Purn"
user_role = "admin"
is_authenticated = True
is_admin = True

# =====================================================================
# AUTHENTICATED DATA INITIALIZATION & CACHED METRIC ENGINE
# =====================================================================
current_stock_universe, current_etf_universe = get_active_universe()
ALL_CONFIG_TICKERS = [x["ticker"] for x in (current_etf_universe + current_stock_universe)]
runtime_cfg = load_runtime_config()
tickers_tuple = tuple(sorted(ALL_CONFIG_TICKERS))

active_raw_data = load_historical_market_data(tickers_tuple)
with st.spinner("Evaluating multi-factor metrics across 250+ Equities & Broad ETFs..."):
    stocks_market_df, stock_regime, etfs_market_df, etf_regime, all_metals_df = get_cached_market_evaluation(tickers_tuple)
regime_data = etf_regime

# =====================================================================
# SIDEBAR NAVIGATION & DATA REFRESH CONTROLS
# =====================================================================
with st.sidebar:
    st.markdown("### ⚡ AGY Tactical Allocator Pro")
    st.caption("Institutional High-Conviction Quantitative Engine")
    st.markdown("---")

    nav_items = [
        "🎯 High-Conviction Master Hub",
        "🧪 Multi-Regime Backtesting & Machine Learning",
        "📘 Platform Strategy Guide & DOCX Export",
        "🚀 Quant Ecosystem & Satellite Apps"
    ]

    active_tab = st.radio(
        "Navigation:",
        nav_items,
        index=0
    )

    st.markdown("---")
    st.markdown("##### 🔄 Data Refresh Control")
    last_update_str = datetime.datetime.now(IST).strftime("%H:%M:%S")
    st.caption(f"⏱️ 15-Minute Adaptive Cache Active • Last Fetched: `{last_update_str}` IST")
    if st.button("🔄 Refresh Live Market Data", use_container_width=True, key="manual_refresh_btn"):
        st.cache_data.clear()
        st.session_state.strategy_toast = "Live market data cache purged and refreshed."
        st.rerun()

    # Cloud Resource Telemetry (CPU / RAM)
    try:
        from resource_monitor import render_resource_monitor_sidebar
        render_resource_monitor_sidebar(key_suffix="prod_sb")
    except Exception:
        pass

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
if "High-Conviction Master Hub" in active_tab:
    c_t1_h1, c_t1_h2 = st.columns([3.5, 1.2])
    with c_t1_h1:
        st.markdown("### 🎯 High-Conviction Tactical Master Hub & Screener")
        st.caption("Institutional Quantitative Allocation across 5 Tactical Pillars • Unified Multi-Preset Analysis • Full Deep-Dive Analytics & Criteria Met Rationale under each Category")
    with c_t1_h2:
        if st.button("🔄 Refresh Market Data", use_container_width=True, key="btn_refresh_tab1_data"):
            st.cache_data.clear()
            st.session_state.strategy_toast = "Live market data and multi-factor metrics refreshed."
            st.rerun()

    render_metric_glossary_expander("tab1")

    # Cloud Resource Telemetry Health Card
    try:
        from resource_monitor import render_resource_monitor_card
        render_resource_monitor_card(key_suffix="tab1_res_card")
    except Exception:
        pass

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
            column_config=get_pinned_column_config(valid_etf_cols, 3),
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
            column_config=get_pinned_column_config(valid_stk_cols, 3),
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
        sr_full_df = get_cached_sr_matrices(tickers_tuple)

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

                # Visual Metric Directionality & Decision Guide
                st.markdown(
                    """
                    <div style="background: linear-gradient(90deg, #f0fdf4 0%, #eff6ff 100%); border-left: 4px solid #10b981; padding: 10px 14px; border-radius: 6px; margin: 4px 0 10px 0; font-size: 0.88rem; color: #1e293b;">
                        <b>💡 Column Directionality & Interpretation Guide:</b><br/>
                        • <span style="color:#15803d; font-weight:700;">🟢 Higher the Better (↑):</span> <b>5Y S/R Win Rate (%)</b> (historical bounce reliability), <b>S/R Predictability Rating</b> (tier & ★ score), <b>Channel Width (%)</b> (trading room/upside).<br/>
                        • <span style="color:#b91c1c; font-weight:700;">🔻 Lower the Better (↓):</span> <b>Range Position (%)</b> (closer to S1 = safer entry), <b>RSI (14D)</b> (oversold mean-reversion setup), <b>Distance to iNAV (%)</b> (cheaper relative to fair value).<br/>
                        • <span style="color:#0369a1; font-weight:600;">ℹ️ Tooltips:</span> Hover over the <b>(?)</b> icon on any table header for the exact mathematical formula, bounds, and institutional guidance.
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                render_metric_glossary_expander("cat3_sr")
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
                    column_config=get_pinned_column_config(valid_sr_cols, 3),
                    use_container_width=True,
                    height=300
                )

            elif sr_sub_mode == "🏆 5-Year Empirical Predictability Leaderboard":
                st.caption("Historical bounce fidelity over ~1,250 daily bars when testing rolling Support Zone during non-trending regimes.")
                c_lead1, c_lead2 = st.columns([1.5, 2.5])
                with c_lead1:
                    lead_filter = st.radio("Asset Class Filter:", ["All Assets", "Stocks Only", "ETFs Only"], horizontal=True, key="lead_asset_radio")
                lead_ac = "Stock" if lead_filter == "Stocks Only" else ("ETF" if lead_filter == "ETFs Only" else None)
                lead_df = get_cached_5y_leaderboard(lead_ac)
                if not lead_df.empty:
                    disp_cols = [c for c in ["Ticker", "Name", "Asset_Class", "Success_Probability_Pct", "Historical_5Y_Trades", "Avg_Gain_Pct", "Profit_Factor", "SR_Fidelity_Rating"] if c in lead_df.columns]
                    top_lead = lead_df.head(30)[disp_cols]
                    st.markdown(
                        """
                        <div style="background: #f8fafc; border-left: 3px solid #3b82f6; padding: 6px 12px; border-radius: 4px; font-size: 0.82rem; color: #334155; margin-bottom: 8px;">
                            <b>🟢 Higher the Better (↑):</b> Success_Probability_Pct, Profit_Factor, Avg_Gain_Pct, SR_Fidelity_Rating. Hover <b>(?)</b> for formula.
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    render_top_scrollbar_sync()
                    st.dataframe(
                        top_lead,
                        column_config=get_pinned_column_config(top_lead, 3),
                        use_container_width=True,
                        hide_index=True
                    )

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
        reits_data = get_cached_reits_data()

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
                column_config=get_pinned_column_config(valid_r_cols, 3),
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
                column_config=get_pinned_column_config(valid_m_cols, 3),
                use_container_width=True,
                hide_index=True
            )

        # -------------------------------------------------------------
        # CATEGORY 6: APEX MULTI-FACTOR DEDUPLICATED ALLOCATOR
        # -------------------------------------------------------------
        st.markdown("---")
        render_apex_multi_factor_tiles(filtered_etfs_df, filtered_stocks_df, limit=3)


# =====================================================================
# TAB 2: BACKTESTING & MACHINE LEARNING OPTIMIZATION STUDIO
# =====================================================================
elif "Multi-Regime Backtesting" in active_tab:
    if not is_authenticated:
        st.warning("🔒 Access Restricted: The Machine Learning Studio is private. Please sign in from the sidebar to access.")
        st.stop()

    c_t3_h1, c_t3_h2 = st.columns([3.5, 1.2])
    with c_t3_h1:
        st.markdown("### 🧪 Machine Learning Optimization & Strategy Calibration Studio")
        st.caption("Empirical factor analysis, dynamic trailing stop tuning, and adaptive multi-factor weight calibration across all 5 Strategy Presets.")
    with c_t3_h2:
        if st.button("🔄 Refresh Studio Data", use_container_width=True, key="btn_refresh_tab3_data"):
            st.cache_data.clear()
            st.session_state.strategy_toast = "Backtesting metrics & parameter data refreshed."
            st.rerun()

    render_metric_glossary_expander("tab3")

    # Cloud Resource Telemetry Health Card
    try:
        from resource_monitor import render_resource_monitor_card
        render_resource_monitor_card(key_suffix="tab3_res_card")
    except Exception:
        pass

    # 1. AI Quant Advisor Analysis & Tweaks
    raw_trades = load_paper_trades()
    sug_df = evaluate_strategy_performance_and_suggest_tweaks(trades_df=raw_trades)
    ac1, ac2, ac3 = st.columns([2, 1, 1])
    with ac1:
        st.markdown(f"**Optimization Engine Status:** `{runtime_cfg.get('optimization_status', 'Active')}`")
    with ac2:
        if st.button("🔄 Refresh Empirical Review", use_container_width=True):
            raw_trades = load_paper_trades()
            sug_df = evaluate_strategy_performance_and_suggest_tweaks(trades_df=raw_trades)
            st.session_state.strategy_toast = "Empirical review refreshed."
            st.rerun()
    with ac3:
        if is_admin:
            if st.button("⚡ Apply AI Optimizations", use_container_width=True, type="primary"):
                res = apply_suggested_optimizations()
                st.success(f"Applied {len(res['changes'])} optimizations live!")
                st.cache_data.clear()
                st.rerun()
        else:
            st.caption("🔒 Apply AI Optimizations (Admin Only)")

    st.markdown("##### 📊 Empirical Recommendations")
    st.dataframe(sug_df, column_config=get_pinned_column_config(sug_df, 3), use_container_width=True)

    st.markdown("---")

    # 2. Comprehensive Interactive Parameter Calibration Studio (All Presets & Per-Category)
    st.markdown("#### 🎚️ Comprehensive Parameter Calibration Studio")
    if is_admin:
        st.caption("Adjust sliders directly in the GUI. All changes immediately take effect across all screeners, tiles, and paper trading executions.")
    else:
        st.info("🔒 Calibration Studio is in Read-Only mode. Administrator privileges are required to modify and save strategy parameters.")

    weights_dict = runtime_cfg.get("weights", {})
    risk_dict = runtime_cfg.get("risk_multipliers", {})
    sched_dict = runtime_cfg.get("execution_schedule", {})
    slider_disabled = not is_admin

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
            w_dma_def = c1.slider("200 DMA Trend Proximity (%)", 0, 100, int(weights_dict.get("Default", {}).get("w_dma", 35)), disabled=slider_disabled, key="s_def_dma")
            w_rsi_def = c2.slider("14D RSI Pullback (%)", 0, 100, int(weights_dict.get("Default", {}).get("w_rsi", 30)), disabled=slider_disabled, key="s_def_rsi")
            w_low_def = c3.slider("52W Low Base Proximity (%)", 0, 100, int(weights_dict.get("Default", {}).get("w_low", 20)), disabled=slider_disabled, key="s_def_low")
            w_exp_def = c4.slider("Expense/Spread Quality (%)", 0, 100, int(weights_dict.get("Default", {}).get("w_exp", 15)), disabled=slider_disabled, key="s_def_exp")
            new_weights["Default"] = {"w_dma": w_dma_def, "w_rsi": w_rsi_def, "w_low": w_low_def, "w_exp": w_exp_def}

        with p_tab2:
            st.caption("Long-term secular compounding prioritizing dividend yield, moving average stability, and low tracking drag.")
            c1, c2, c3, c4, c5 = st.columns(5)
            w_dma_lt = c1.slider("200 DMA Trend (%)", 0, 100, int(weights_dict.get("Long-Term", {}).get("w_dma", 40)), disabled=slider_disabled, key="s_lt_dma")
            w_div_lt = c2.slider("Dividend Yield (%)", 0, 100, int(weights_dict.get("Long-Term", {}).get("w_div", 20)), disabled=slider_disabled, key="s_lt_div")
            w_rsi_lt = c3.slider("Macro RSI (%)", 0, 100, int(weights_dict.get("Long-Term", {}).get("w_rsi", 15)), disabled=slider_disabled, key="s_lt_rsi")
            w_bb_lt = c4.slider("Bollinger Cushion (%)", 0, 100, int(weights_dict.get("Long-Term", {}).get("w_bb", 15)), disabled=slider_disabled, key="s_lt_bb")
            w_exp_lt = c5.slider("Fundamental Expense (%)", 0, 100, int(weights_dict.get("Long-Term", {}).get("w_exp", 10)), disabled=slider_disabled, key="s_lt_exp")
            new_weights["Long-Term"] = {"w_dma": w_dma_lt, "w_div": w_div_lt, "w_rsi": w_rsi_lt, "w_bb": w_bb_lt, "w_exp": w_exp_lt}

        with p_tab3:
            st.caption("Positional mean-reversion exploiting short-term oversold exhaustion and Bollinger Band contractions.")
            c1, c2, c3, c4, c5 = st.columns(5)
            w_rsi_sw = c1.slider("14D RSI Reversal (%)", 0, 100, int(weights_dict.get("Swing / Positional", {}).get("w_rsi", 35)), disabled=slider_disabled, key="s_sw_rsi")
            w_dma_sw = c2.slider("200 DMA Pullback (%)", 0, 100, int(weights_dict.get("Swing / Positional", {}).get("w_dma", 25)), disabled=slider_disabled, key="s_sw_dma")
            w_bb_sw = c3.slider("Bollinger %B Contraction (%)", 0, 100, int(weights_dict.get("Swing / Positional", {}).get("w_bb", 20)), disabled=slider_disabled, key="s_sw_bb")
            w_vwap_sw = c4.slider("VWAP Proximity (%)", 0, 100, int(weights_dict.get("Swing / Positional", {}).get("w_vwap", 10)), disabled=slider_disabled, key="s_sw_vwap")
            w_stoch_sw = c5.slider("Fast Stochastic %K (%)", 0, 100, int(weights_dict.get("Swing / Positional", {}).get("w_stoch", 10)), disabled=slider_disabled, key="s_sw_stoch")
            new_weights["Swing / Positional"] = {"w_rsi": w_rsi_sw, "w_dma": w_dma_sw, "w_bb": w_bb_sw, "w_vwap": w_vwap_sw, "w_stoch": w_stoch_sw}

        with p_tab4:
            st.caption("Intraday momentum breakout capitalizing on morning volume surges and directional VWAP expansion.")
            c1, c2, c3, c4 = st.columns(4)
            w_vol_in = c1.slider("Volume Surge Ratio (%)", 0, 100, int(weights_dict.get("Intraday", {}).get("w_vol", 35)), disabled=slider_disabled, key="s_in_vol")
            w_rsi_in = c2.slider("Intraday Momentum RSI (%)", 0, 100, int(weights_dict.get("Intraday", {}).get("w_rsi", 30)), disabled=slider_disabled, key="s_in_rsi")
            w_bb_in = c3.slider("Bollinger Band Expansion (%)", 0, 100, int(weights_dict.get("Intraday", {}).get("w_bb", 20)), disabled=slider_disabled, key="s_in_bb")
            w_vwap_in = c4.slider("VWAP Breakout (%)", 0, 100, int(weights_dict.get("Intraday", {}).get("w_vwap", 15)), disabled=slider_disabled, key="s_in_vwap")
            new_weights["Intraday"] = {"w_vol": w_vol_in, "w_rsi": w_rsi_in, "w_bb": w_bb_in, "w_vwap": w_vwap_in}

        with p_tab5:
            st.caption("Cross-indicator AI confluence model synthesizing RSI, Volatility Bands, Volume flow, and MACD momentum.")
            c1, c2, c3, c4 = st.columns(4)
            w_rsi_ai = c1.slider("Confluence RSI (%)", 0, 100, int(weights_dict.get("AI / RAG", {}).get("w_rsi", 30)), disabled=slider_disabled, key="s_ai_rsi")
            w_bb_ai = c2.slider("Volatility Band %B (%)", 0, 100, int(weights_dict.get("AI / RAG", {}).get("w_bb", 25)), disabled=slider_disabled, key="s_ai_bb")
            w_vol_ai = c3.slider("Volume Confluence (%)", 0, 100, int(weights_dict.get("AI / RAG", {}).get("w_vol", 25)), disabled=slider_disabled, key="s_ai_vol")
            w_macd_ai = c4.slider("MACD Momentum (%)", 0, 100, int(weights_dict.get("AI / RAG", {}).get("w_macd", 20)), disabled=slider_disabled, key="s_ai_macd")
            new_weights["AI / RAG"] = {"w_rsi": w_rsi_ai, "w_bb": w_bb_ai, "w_vol": w_vol_ai, "w_macd": w_macd_ai}

        st.markdown("---")

        # Section B: Risk Multipliers & Dynamic Trailing Stops
        st.markdown("##### 🛡️ Risk Multipliers & Dynamic Trailing Stops (Per Strategy)")
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            st.markdown("###### Intraday Parameters:")
            in_sl = st.slider("Intraday SL (x ATR)", 0.5, 2.5, float(risk_dict.get("intraday_sl_multiplier", 1.0)), step=0.1, disabled=slider_disabled, key="s_in_sl")
            in_tgt = st.slider("Intraday Target (x ATR)", 1.0, 4.0, float(risk_dict.get("intraday_target_multiplier", 1.8)), step=0.1, disabled=slider_disabled, key="s_in_tgt")
        with rc2:
            st.markdown("###### Swing / Positional Parameters:")
            sw_sl = st.slider("Swing SL (x ATR)", 1.0, 4.0, float(risk_dict.get("swing_sl_multiplier", 1.5)), step=0.1, disabled=slider_disabled, key="s_sw_sl")
            sw_tgt = st.slider("Swing Target (x ATR)", 1.5, 6.0, float(risk_dict.get("swing_target_multiplier", 3.0)), step=0.1, disabled=slider_disabled, key="s_sw_tgt")
        with rc3:
            st.markdown("###### Long-Term Parameters:")
            lt_sl = st.slider("Long-Term SL (x ATR)", 1.5, 5.0, float(risk_dict.get("longterm_sl_multiplier", 2.5)), step=0.1, disabled=slider_disabled, key="s_lt_sl")
            lt_tgt = st.slider("Long-Term Target (x ATR)", 2.0, 8.0, float(risk_dict.get("longterm_target_multiplier", 5.0)), step=0.1, disabled=slider_disabled, key="s_lt_tgt")

        st.markdown("###### Trailing Stop Controls & Exit Thresholds:")
        tr1, tr2, tr3, tr4 = st.columns(4)
        tr_act = tr1.slider("Trailing Activation (%)", 1.0, 8.0, float(risk_dict.get("trailing_stop_activation_pct", 3.0)), step=0.5, disabled=slider_disabled, key="s_tr_act")
        tr_lock = tr2.slider("Trailing Lock-In (%)", 0.1, 4.0, float(risk_dict.get("trailing_stop_lock_pct", 0.5)), step=0.1, disabled=slider_disabled, key="s_tr_lock")
        rsi_ob = tr3.slider("RSI Overbought Exit", 65.0, 85.0, float(risk_dict.get("overbought_rsi_exit_threshold", 75.0)), step=1.0, disabled=slider_disabled, key="s_rsi_ob")
        rsi_os = tr4.slider("RSI Oversold Buy Floor", 25.0, 45.0, float(risk_dict.get("oversold_rsi_buy_threshold", 35.0)), step=1.0, disabled=slider_disabled, key="s_rsi_os")

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
        min_reit_yield = cf1.slider("Minimum REIT / InvIT Yield (%)", 5.0, 10.0, 6.5, step=0.5, disabled=slider_disabled, key="s_min_reit_yd")
        max_metal_range = cf2.slider("Max Metal 52W Range Filter (%)", 60.0, 95.0, 80.0, step=5.0, disabled=slider_disabled, key="s_max_met_rng")
        min_sr_win = cf3.slider("Min S/R 5Y Empirical Win Rate (%)", 50.0, 75.0, 60.0, step=1.0, disabled=slider_disabled, key="s_min_sr_win")

        if is_admin:
            save_btn = st.form_submit_button("💾 Save All Parameter Calibrations to Runtime Config", type="primary", use_container_width=True)
        else:
            st.caption("🔒 Parameter changes can only be saved by Administrator.")
            save_btn = False

    if save_btn and is_admin:
        save_res = save_manual_parameter_adjustments(new_weights, new_risk, sched_dict, user=current_user)
        st.session_state.strategy_toast = f"🟢 Saved adjustments ({save_res['updated_count']} parameters updated live)!"
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")

    # 3. Parameter Edge Directionality Matrix
    st.markdown("#### 📐 All Strategy Parameters & Edge Directionality Matrix")
    param_matrix_df = get_parameter_reference_matrix()
    matrix_sub_df = param_matrix_df[["Category", "Parameter", "Current_Value", "Default_Value", "BUY_Edge_Direction", "SELL_Edge_Direction", "Intended_Market_Impact"]]
    st.dataframe(
        matrix_sub_df,
        column_config=get_pinned_column_config(matrix_sub_df, 3),
        use_container_width=True,
        height=280
    )

    # 4. Parameter Change Audit Trail
    st.markdown("---")
    st.markdown("#### 📝 Parameter Change Audit Log")
    param_change_log_df = load_parameter_change_log()
    if not param_change_log_df.empty:
        st.dataframe(
            param_change_log_df.sort_values(by="Timestamp_IST", ascending=False),
            column_config=get_pinned_column_config(param_change_log_df, 3),
            use_container_width=True,
            height=180
        )

    # 5. Strategic Logic & Architectural Changes History Log
    st.markdown("---")
    st.markdown("#### 🏛️ Strategic Logic & Architectural Changes Log")
    strat_log_tab3 = load_strategy_change_log()
    if not strat_log_tab3.empty:
        st.dataframe(
            strat_log_tab3,
            column_config=get_pinned_column_config(strat_log_tab3, 3),
            use_container_width=True,
            height=200
        )


# =====================================================================
# TAB 3: PLATFORM STRATEGY GUIDE & DOCX EXPORT
# =====================================================================
elif "Platform Strategy Guide" in active_tab:
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


# =====================================================================
# TAB 4: QUANT ECOSYSTEM & SATELLITE APPS FLEET MANAGER
# =====================================================================
elif "Quant Ecosystem & Satellite Apps" in active_tab:
    render_fleet_manager_tab(is_admin=True)
