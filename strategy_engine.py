# =====================================================================
# V2 STRATEGY ENGINE: PUBLIC TESTBED (NO EXTERNAL SECRETS REQUIRED)
# =====================================================================
import datetime
import os
import json
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger("StrategyEngine_V2")

def get_active_runtime_config():
    """Loads active runtime_config.json or returns factory defaults."""
    cfg_paths = [
        os.path.join(os.path.dirname(__file__), "runtime_config.json"),
        "runtime_config.json",
        os.path.join(os.path.dirname(__file__), "..", "runtime_config.json")
    ]
    for p in cfg_paths:
        if os.path.exists(p) and os.path.getsize(p) > 0:
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {
        "weights": {
            "Default": {"w_dma": 35, "w_rsi": 30, "w_low": 20, "w_exp": 15},
            "Long-Term": {"w_dma": 40, "w_div": 15, "w_rsi": 15, "w_low": 15, "w_exp": 15},
            "Swing / Positional": {"w_rsi": 30, "w_dma": 25, "w_bb": 20, "w_vwap": 15, "w_stoch": 10},
            "Intraday": {"w_vol": 35, "w_rsi": 30, "w_bb": 20, "w_vwap": 15},
            "AI / RAG": {"w_rsi": 35, "w_bb": 25, "w_vol": 25, "w_macd": 15}
        },
        "risk_parameters": {
            "intraday_sl_multiplier": 1.0,
            "intraday_target_multiplier": 1.8,
            "swing_sl_multiplier": 1.5,
            "swing_target_multiplier": 3.0,
            "longterm_sl_multiplier": 2.5,
            "longterm_target_multiplier": 5.0,
            "trailing_stop_activation_pct": 3.0,
            "trailing_stop_lock_pct": 0.5,
            "overbought_rsi_exit_threshold": 76.0,
            "oversold_rsi_buy_threshold": 38.0
        },
        "execution_schedule": {
            "weekdays_only": False,
            "enable_3pm_accumulation": True,
            "enable_morning_intraday": True,
            "enable_afternoon_squareoff": True
        }
    }

# Default Presets & Conviction Weights
DEFAULT_PRESETS = {
    "Default": {"w_dma": 35, "w_rsi": 30, "w_low": 20, "w_exp": 15},
    "Long-Term": {"w_dma": 40, "w_div": 15, "w_rsi": 15, "w_low": 15, "w_exp": 15},
    "Swing / Positional": {"w_rsi": 30, "w_dma": 25, "w_bb": 20, "w_vwap": 15, "w_stoch": 10},
    "Intraday": {"w_vol": 35, "w_rsi": 30, "w_bb": 20, "w_vwap": 15},
    "AI / RAG": {"w_rsi": 35, "w_bb": 25, "w_vol": 25, "w_macd": 15},
}
PRESETS = DEFAULT_PRESETS.copy()

# =====================================================================
# UNIVERSE SPECIFICATIONS: 35 ETFs + 52 STOCKS
# =====================================================================
DEFAULT_STAGE1_ETF_CONFIG = [
    {"ticker": "NIFTYBEES.NS", "name": "Nippon Nifty 50 BeES", "category": "Large Cap", "expense": 0.04},
    {"ticker": "SETFNIF50.NS", "name": "SBI Nifty 50 ETF", "category": "Large Cap", "expense": 0.04},
    {"ticker": "ICICINIFTY.NS", "name": "ICICI Nifty 50 ETF", "category": "Large Cap", "expense": 0.03},
    {"ticker": "HDFCNIFTY.NS", "name": "HDFC Nifty 50 ETF", "category": "Large Cap", "expense": 0.05},
    {"ticker": "NEXT50IETF.NS", "name": "ICICI Nifty Next 50", "category": "Next 50", "expense": 0.30},
    {"ticker": "JUNIORBEES.NS", "name": "Nippon Junior BeES", "category": "Next 50", "expense": 0.12},
    {"ticker": "MIDCAPIETF.NS", "name": "Mirae Nifty Midcap 150", "category": "Midcap", "expense": 0.21},
    {"ticker": "MID150BEES.NS", "name": "Nippon Midcap 150 BeES", "category": "Midcap", "expense": 0.20},
    {"ticker": "HDFCMID150.NS", "name": "HDFC Nifty Midcap 150", "category": "Midcap", "expense": 0.20},
    {"ticker": "HDFCSML250.NS", "name": "HDFC Smallcap 250", "category": "Smallcap", "expense": 0.20},
    {"ticker": "SMALLCAP.NS", "name": "Mirae Smallcap 250", "category": "Smallcap", "expense": 0.26},
    {"ticker": "NV20IETF.NS", "name": "ICICI Nifty50 Value 20", "category": "Value", "expense": 0.27},
    {"ticker": "MOVALUE.NS", "name": "Motilal Enhanced Value", "category": "Value", "expense": 0.35},
    {"ticker": "ICICIB22.NS", "name": "ICICI BHARAT 22 ETF", "category": "CPSE / PSU", "expense": 0.05},
    {"ticker": "CPSEETF.NS", "name": "CPSE ETF (Nippon)", "category": "CPSE / PSU", "expense": 0.05},
    {"ticker": "DIVOPPBEES.NS", "name": "Nippon Dividend Opp 50", "category": "Dividend", "expense": 0.37},
    {"ticker": "NIFTYQLITY.NS", "name": "SBI Nifty 200 Quality 30", "category": "Smart Beta", "expense": 0.30},
    {"ticker": "QUAL30IETF.NS", "name": "ICICI Nifty 200 Quality 30", "category": "Smart Beta", "expense": 0.30},
    {"ticker": "ALPHAETF.NS", "name": "Mirae Nifty 200 Alpha 30", "category": "Smart Beta", "expense": 0.41},
    {"ticker": "ALPL30IETF.NS", "name": "ICICI Alpha Low Vol 30", "category": "Smart Beta", "expense": 0.35},
    {"ticker": "KOTAKALPHA.NS", "name": "Kotak Nifty 200 Alpha 30", "category": "Smart Beta", "expense": 0.36},
    {"ticker": "MOM30IETF.NS", "name": "ICICI Nifty200 Momentum 30", "category": "Smart Beta", "expense": 0.38},
    {"ticker": "MOMENTUM50.NS", "name": "Nippon Nifty 500 Momentum 50", "category": "Smart Beta", "expense": 0.39},
    {"ticker": "HDFCMOM30.NS", "name": "HDFC Nifty200 Momentum 30", "category": "Smart Beta", "expense": 0.40},
    {"ticker": "MOM500.NS", "name": "Motilal Nifty 500 ETF", "category": "Broad Market", "expense": 0.35},
    {"ticker": "GOLDBEES.NS", "name": "Nippon Gold BeES", "category": "Commodity", "expense": 0.79},
    {"ticker": "SETFGOLD.NS", "name": "SBI Gold ETF", "category": "Commodity", "expense": 0.50},
    {"ticker": "SILVERBEES.NS", "name": "Nippon Silver BeES", "category": "Commodity", "expense": 0.50},
    {"ticker": "SILVERIETF.NS", "name": "ICICI Silver ETF", "category": "Commodity", "expense": 0.45},
    {"ticker": "MON100.NS", "name": "Motilal Nasdaq 100", "category": "International", "expense": 0.58},
    {"ticker": "MONQ50.NS", "name": "Motilal Nasdaq Q 50", "category": "International", "expense": 0.60},
    {"ticker": "MASPTOP50.NS", "name": "Mirae S&P 500 Top 50", "category": "International", "expense": 0.70},
    {"ticker": "MAFANG.NS", "name": "Mirae NYSE FANG+ ETF", "category": "International", "expense": 0.65},
    {"ticker": "HNGSNGBEES.NS", "name": "Nippon Hang Seng BeES", "category": "International", "expense": 0.78},
    {"ticker": "MAHKTECH.NS", "name": "Mirae Hang Seng TECH ETF", "category": "International", "expense": 0.70},
]

DEFAULT_STAGE2_STOCK_CONFIG = [
    {"ticker": "RELIANCE.NS", "name": "Reliance Industries", "category": "Energy & Retail", "expense": np.nan},
    {"ticker": "TCS.NS", "name": "Tata Consultancy Services", "category": "IT Services", "expense": np.nan},
    {"ticker": "HDFCBANK.NS", "name": "HDFC Bank", "category": "Banking", "expense": np.nan},
    {"ticker": "ICICIBANK.NS", "name": "ICICI Bank", "category": "Banking", "expense": np.nan},
    {"ticker": "INFY.NS", "name": "Infosys Ltd", "category": "IT Services", "expense": np.nan},
    {"ticker": "BHARTIARTL.NS", "name": "Bharti Airtel", "category": "Telecom", "expense": np.nan},
    {"ticker": "ITC.NS", "name": "ITC Ltd", "category": "FMCG", "expense": np.nan},
    {"ticker": "SBIN.NS", "name": "State Bank of India", "category": "PSU Banking", "expense": np.nan},
    {"ticker": "LT.NS", "name": "Larsen & Toubro", "category": "Infrastructure", "expense": np.nan},
    {"ticker": "HINDUNILVR.NS", "name": "Hindustan Unilever", "category": "FMCG", "expense": np.nan},
    {"ticker": "AXISBANK.NS", "name": "Axis Bank", "category": "Banking", "expense": np.nan},
    {"ticker": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank", "category": "Banking", "expense": np.nan},
    {"ticker": "M&M.NS", "name": "Mahindra & Mahindra", "category": "Automobile", "expense": np.nan},
    {"ticker": "MARUTI.NS", "name": "Maruti Suzuki", "category": "Automobile", "expense": np.nan},
    {"ticker": "TATAMOTORS.NS", "name": "Tata Motors", "category": "Automobile", "expense": np.nan},
    {"ticker": "SUNPHARMA.NS", "name": "Sun Pharma", "category": "Pharma", "expense": np.nan},
    {"ticker": "TITAN.NS", "name": "Titan Company", "category": "Consumer Discretionary", "expense": np.nan},
    {"ticker": "BAJFINANCE.NS", "name": "Bajaj Finance", "category": "NBFC", "expense": np.nan},
    {"ticker": "BAJAJFINSV.NS", "name": "Bajaj Finserv", "category": "Financial Services", "expense": np.nan},
    {"ticker": "NTPC.NS", "name": "NTPC Ltd", "category": "Power / PSU", "expense": np.nan},
    {"ticker": "POWERGRID.NS", "name": "Power Grid Corp", "category": "Power / PSU", "expense": np.nan},
    {"ticker": "ONGC.NS", "name": "ONGC", "category": "Oil & Gas / PSU", "expense": np.nan},
    {"ticker": "COALINDIA.NS", "name": "Coal India", "category": "Mining / PSU", "expense": np.nan},
    {"ticker": "TATASTEEL.NS", "name": "Tata Steel", "category": "Metals", "expense": np.nan},
    {"ticker": "JSWSTEEL.NS", "name": "JSW Steel", "category": "Metals", "expense": np.nan},
    {"ticker": "HINDALCO.NS", "name": "Hindalco Industries", "category": "Metals", "expense": np.nan},
    {"ticker": "ADANIENT.NS", "name": "Adani Enterprises", "category": "Conglomerate", "expense": np.nan},
    {"ticker": "ADANIPORTS.NS", "name": "Adani Ports & SEZ", "category": "Infrastructure", "expense": np.nan},
    {"ticker": "ULTRACEMCO.NS", "name": "UltraTech Cement", "category": "Cement", "expense": np.nan},
    {"ticker": "GRASIM.NS", "name": "Grasim Industries", "category": "Materials", "expense": np.nan},
    {"ticker": "WIPRO.NS", "name": "Wipro", "category": "IT Services", "expense": np.nan},
    {"ticker": "HCLTECH.NS", "name": "HCL Technologies", "category": "IT Services", "expense": np.nan},
    {"ticker": "TECHM.NS", "name": "Tech Mahindra", "category": "IT Services", "expense": np.nan},
    {"ticker": "DRREDDY.NS", "name": "Dr. Reddy's Labs", "category": "Pharma", "expense": np.nan},
    {"ticker": "CIPLA.NS", "name": "Cipla Ltd", "category": "Pharma", "expense": np.nan},
    {"ticker": "APOLLOHOSP.NS", "name": "Apollo Hospitals", "category": "Healthcare", "expense": np.nan},
    {"ticker": "ASIANPAINT.NS", "name": "Asian Paints", "category": "Paints / Consumer", "expense": np.nan},
    {"ticker": "NESTLEIND.NS", "name": "Nestle India", "category": "FMCG", "expense": np.nan},
    {"ticker": "BRITANNIA.NS", "name": "Britannia Industries", "category": "FMCG", "expense": np.nan},
    {"ticker": "TATACONSUM.NS", "name": "Tata Consumer Products", "category": "FMCG", "expense": np.nan},
    {"ticker": "EICHERMOT.NS", "name": "Eicher Motors", "category": "Automobile", "expense": np.nan},
    {"ticker": "HEROMOTOCO.NS", "name": "Hero MotoCorp", "category": "Automobile", "expense": np.nan},
    {"ticker": "BPCL.NS", "name": "BPCL", "category": "Oil & Gas / PSU", "expense": np.nan},
    {"ticker": "BEL.NS", "name": "Bharat Electronics", "category": "Defense / PSU", "expense": np.nan},
    {"ticker": "HAL.NS", "name": "Hindustan Aeronautics", "category": "Defense / PSU", "expense": np.nan},
    {"ticker": "TRENT.NS", "name": "Trent Ltd", "category": "Retail", "expense": np.nan},
    {"ticker": "VBL.NS", "name": "Varun Beverages", "category": "Beverages", "expense": np.nan},
    {"ticker": "CHOLAFIN.NS", "name": "Cholamandalam Inv", "category": "NBFC", "expense": np.nan},
    {"ticker": "CUMMINSIND.NS", "name": "Cummins India", "category": "Capital Goods", "expense": np.nan},
    {"ticker": "POLYCAB.NS", "name": "Polycab India", "category": "Cables & Electricals", "expense": np.nan},
    {"ticker": "PERSISTENT.NS", "name": "Persistent Systems", "category": "IT Midcap", "expense": np.nan},
    {"ticker": "DIXON.NS", "name": "Dixon Technologies", "category": "EMS / Electronics", "expense": np.nan},
]

# =====================================================================
# DIVIDEND YIELD REFERENCE MAPPING (ESTABLISHED CASH-FLOW YIELDS %)
# =====================================================================
DIVIDEND_YIELD_MAP = {
    # High Yield PSU & High Cash-Flow Value
    "COALINDIA.NS": 8.25, "BPCL.NS": 6.10, "ONGC.NS": 5.40, "POWERGRID.NS": 3.75,
    "NTPC.NS": 3.40, "ITC.NS": 3.65, "HCLTECH.NS": 3.20, "TECHM.NS": 2.95,
    "TCS.NS": 2.65, "INFY.NS": 2.50, "TATASTEEL.NS": 2.80, "HEROMOTOCO.NS": 2.85,
    "VEDL.NS": 9.50, "IOC.NS": 6.80, "HINDPETRO.NS": 5.80, "PFC.NS": 4.80, "RECLTD.NS": 4.50,
    "NMDC.NS": 4.30, "GAIL.NS": 4.20, "NHPC.NS": 3.80, "PETRONET.NS": 3.60, "SJVN.NS": 3.50,
    "HUDCO.NS": 3.40, "CANBK.NS": 3.20, "SAIL.NS": 3.10, "BANKBARODA.NS": 3.00, "PNB.NS": 2.80,
    "RVNL.NS": 2.10, "IRFC.NS": 2.20, "NATIONALUM.NS": 4.10, "OIL.NS": 4.60,
    # High Dividend ETFs
    "DIVOPPBEES.NS": 4.20, "CPSEETF.NS": 4.60, "ICICIB22.NS": 3.85, "NV20IETF.NS": 1.95, "MOVALUE.NS": 1.70,
    # Core Large Cap Stocks & ETFs
    "NIFTYBEES.NS": 1.25, "SETFNIF50.NS": 1.25, "ICICINIFTY.NS": 1.25, "HDFCNIFTY.NS": 1.25,
    "HINDUNILVR.NS": 1.65, "SBIN.NS": 1.75, "BRITANNIA.NS": 1.55, "NESTLEIND.NS": 1.35,
    "HDFCBANK.NS": 1.25, "ICICIBANK.NS": 0.85, "KOTAKBANK.NS": 0.15, "AXISBANK.NS": 0.15,
    "M&M.NS": 0.90, "MARUTI.NS": 1.15, "TATAMOTORS.NS": 0.65, "LT.NS": 0.95,
    "BHARTIARTL.NS": 0.70, "RELIANCE.NS": 0.35, "SUNPHARMA.NS": 0.85, "CIPLA.NS": 0.80,
    "DRREDDY.NS": 0.70, "TITAN.NS": 0.40, "BAJFINANCE.NS": 0.45, "BAJAJFINSV.NS": 0.15,
    "EICHERMOT.NS": 1.10, "BEL.NS": 0.75, "HAL.NS": 0.80, "TRENT.NS": 0.10,
    "VBL.NS": 0.25, "CHOLAFIN.NS": 0.30, "CUMMINSIND.NS": 1.10, "POLYCAB.NS": 0.45,
    "PERSISTENT.NS": 0.80, "DIXON.NS": 0.10, "ULTRACEMCO.NS": 0.35, "GRASIM.NS": 0.40,
    "WIPRO.NS": 0.20, "APOLLOHOSP.NS": 0.25, "ASIANPAINT.NS": 1.10, "TATACONSUM.NS": 0.85,
    "JSWSTEEL.NS": 0.75, "HINDALCO.NS": 0.70, "ADANIENT.NS": 0.10, "ADANIPORTS.NS": 0.45,
    # Broad & Sector ETFs
    "JUNIORBEES.NS": 0.90, "NEXT50IETF.NS": 0.90, "MID150BEES.NS": 0.75, "MIDCAPIETF.NS": 0.75,
    "HDFCMID150.NS": 0.75, "SMALLCAP.NS": 0.50, "HDFCSML250.NS": 0.50, "NIFTYQLITY.NS": 1.30,
    "QUAL30IETF.NS": 1.30, "ALPHAETF.NS": 0.65, "ALPL30IETF.NS": 1.10, "KOTAKALPHA.NS": 0.65,
    "MOM30IETF.NS": 0.50, "MOMENTUM50.NS": 0.50, "HDFCMOM30.NS": 0.50, "MOM500.NS": 0.80,
    # Non-Dividend Assets
    "GOLDBEES.NS": 0.0, "SETFGOLD.NS": 0.0, "SILVERBEES.NS": 0.0, "SILVERIETF.NS": 0.0,
    "MON100.NS": 0.15, "MONQ50.NS": 0.15, "MASPTOP50.NS": 0.45, "MAFANG.NS": 0.0,
    "HNGSNGBEES.NS": 1.80, "MAHKTECH.NS": 0.20,
}

# =====================================================================
# TECHNICAL INDICATOR MATHEMATICS
# =====================================================================
def calculate_rsi_series(series, period=14):
    if series is None or len(series) < period:
        return pd.Series(50.0, index=series.index if series is not None else [0])
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)

def calculate_atr(df, period=14):
    h, l, c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()

def calculate_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def calculate_stochastic(df, k_period=14, d_period=3):
    h, l, c = df["High"], df["Low"], df["Close"]
    low_min = l.rolling(k_period, min_periods=1).min()
    high_max = h.rolling(k_period, min_periods=1).max()
    denom = (high_max - low_min).replace(0, np.nan)
    k = ((c - low_min) / denom) * 100.0
    d = k.rolling(d_period, min_periods=1).mean()
    return k.fillna(50.0), d.fillna(50.0)

def extract_ticker_df(raw, ticker):
    if raw is None or raw.empty:
        return pd.DataFrame()

    clean_t = ticker.replace(".NS", "")
    candidates = [ticker, clean_t, f"{clean_t}.NS"]

    if hasattr(raw.columns, "levels") and len(raw.columns.levels) > 1:
        for c in candidates:
            if c in raw.columns.levels[0]:
                sub = raw[c].copy()
                if not sub.empty and "Close" in sub.columns:
                    return sub.dropna(subset=["Close"])
        for c in candidates:
            if c in raw.columns.levels[1]:
                sub = raw.xs(c, level=1, axis=1).copy()
                if not sub.empty and "Close" in sub.columns:
                    return sub.dropna(subset=["Close"])
    else:
        if "Close" in raw.columns:
            return raw.dropna(subset=["Close"])
        for c in candidates:
            matching = [col for col in raw.columns if c in str(col)]
            if matching:
                sub = raw[matching].copy()
                return sub.dropna()

    return pd.DataFrame()

# =====================================================================
# MARKET REGIME & METRICS EVALUATION ENGINE
# =====================================================================
def evaluate_market_metrics(raw, universe_config, is_stock_mode=False, dynamic_weights=None):
    if raw is None or raw.empty:
        return pd.DataFrame(), {
            "regime": "⚠️ Service Offline", "desc": "Market history unavailable.",
            "n500_cmp": 0.0, "n500_d50": 0.0, "n500_d200": 0.0,
            "vix": 15.0, "vix_badge": "🟡 Normal Market (VIX: 15.0)",
            "vix_factor": 1.0, "vix_advice": "Standard position sizing."
        }

    # Benchmark Regime Assessment (^CRSLDX Nifty 500 or ^NSEI Nifty 50)
    bench_df = extract_ticker_df(raw, "^CRSLDX")
    if bench_df.empty:
        bench_df = extract_ticker_df(raw, "^NSEI")

    if not bench_df.empty and "Close" in bench_df.columns:
        n500_close = bench_df["Close"].dropna()
        n500_curr = float(n500_close.iloc[-1])
        n500_d50 = float(n500_close.rolling(50, min_periods=1).mean().iloc[-1])
        n500_d200 = float(n500_close.rolling(200, min_periods=1).mean().iloc[-1])

        if n500_curr > n500_d50 > n500_d200:
            regime = "🟢 Strong Bull Market"
            regime_desc = "Index firmly above 50 & 200 DMA. Quality dips offer high-probability bounces."
        elif n500_curr < n500_d50 < n500_d200:
            regime = "🔴 Bear Market / Correction"
            regime_desc = "Index below 50 & 200 DMA. Prioritize capital preservation & Gold / defensive safe-havens."
        else:
            regime = "🟡 Sideways / Rangebound Consolidation"
            regime_desc = "Oscillating market structure. Mean-reversion swing targets apply."
    else:
        regime = "🟡 Normal Regime"
        regime_desc = "Standard quantitative scanning mode."
        n500_curr, n500_d50, n500_d200 = 0.0, 0.0, 0.0

    # Benchmark 21D Momentum ROC for Relative Strength
    bench_roc_21d = 0.0
    if not bench_df.empty and "Close" in bench_df.columns:
        b_c = bench_df["Close"].dropna()
        if len(b_c) > 21:
            bench_roc_21d = round(((float(b_c.iloc[-1]) - float(b_c.iloc[-21])) / float(b_c.iloc[-21])) * 100.0, 2)

    # India VIX Volatility Filter
    vix_df = extract_ticker_df(raw, "^INDIAVIX")
    current_vix = 15.0
    if not vix_df.empty and "Close" in vix_df.columns:
        vix_series = vix_df["Close"].dropna()
        if not vix_series.empty:
            current_vix = float(vix_series.iloc[-1])

    if current_vix > 22.0:
        vix_factor = 0.50
        vix_badge = f"⚠️ Wild Swings (VIX: {current_vix:.1f}) | Stagger buys"
        vix_advice = "High volatility detected. Reduce tranche sizes & tighten stop-losses."
    elif current_vix < 13.0:
        vix_factor = 1.00
        vix_badge = f"🟢 Calm Market (VIX: {current_vix:.1f}) | Regular size"
        vix_advice = "Calm market structure. Normal position sizing applies."
    else:
        vix_factor = 1.00
        vix_badge = f"🟡 Normal Market (VIX: {current_vix:.1f}) | Steady pace"
        vix_advice = "Standard position sizing."

    records = []
    for item in universe_config:
        t = item["ticker"]
        clean_sym = t.replace(".NS", "")
        df = extract_ticker_df(raw, t)
        
        if df.empty or len(df) < 10:
            continue

        c = df["Close"].dropna()
        if c.empty:
            continue

        h = df["High"] if "High" in df.columns else c
        l = df["Low"] if "Low" in df.columns else c
        v = df["Volume"].fillna(0) if "Volume" in df.columns else pd.Series(0, index=df.index)
        curr = float(c.iloc[-1])

        # Moving Averages
        d20 = float(c.rolling(20, min_periods=1).mean().iloc[-1])
        d50 = float(c.rolling(50, min_periods=1).mean().iloc[-1])
        d100 = float(c.rolling(100, min_periods=1).mean().iloc[-1])
        d200 = float(c.rolling(200, min_periods=1).mean().iloc[-1])
        ema9 = float(c.ewm(span=9, adjust=False).mean().iloc[-1])
        ema21 = float(c.ewm(span=21, adjust=False).mean().iloc[-1])

        # Price Extrema
        today_low = float(l.iloc[-1])
        today_high = float(h.iloc[-1])
        weekly_low = float(l.iloc[-min(5, len(l)):].min())
        weekly_high = float(h.iloc[-min(5, len(h)):].max())
        low52 = float(l.iloc[-min(252, len(l)):].min())
        high52 = float(h.iloc[-min(252, len(h)):].max())

        # RSI (14D) & Delta
        rsi_series = calculate_rsi_series(c, period=14)
        rsi_latest = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50.0
        rsi_prev = float(rsi_series.iloc[-2]) if len(rsi_series) > 1 else rsi_latest
        rsi_delta = round(rsi_latest - rsi_prev, 2)

        # Bollinger Bands & %B
        ma20 = c.rolling(20, min_periods=1).mean()
        std20 = c.rolling(20, min_periods=1).std().fillna(0.001)
        bb_upper = float((ma20 + 2 * std20).iloc[-1])
        bb_lower = float((ma20 - 2 * std20).iloc[-1])
        std_val = float(std20.iloc[-1])
        percent_b = float(((curr - bb_lower) / (4 * std_val))) if std_val > 0 else 0.50

        # MACD (12, 26, 9)
        macd_line, sig_line, macd_hist = calculate_macd(c)
        macd_val = float(macd_line.iloc[-1]) if not macd_line.empty else 0.0
        macd_sig_val = float(sig_line.iloc[-1]) if not sig_line.empty else 0.0
        macd_hist_val = float(macd_hist.iloc[-1]) if not macd_hist.empty else 0.0
        macd_status = "🟢 Bullish Cross" if macd_val > macd_sig_val else "🔴 Bearish Cross"

        # Stochastic Oscillator (%K, %D)
        stoch_k, stoch_d = calculate_stochastic(df, 14, 3)
        stoch_k_val = float(stoch_k.iloc[-1])
        stoch_d_val = float(stoch_d.iloc[-1])

        # Rate of Change / Momentum (21D & 63D)
        roc_21d = round(((curr - float(c.iloc[-min(21, len(c))])) / float(c.iloc[-min(21, len(c))])) * 100.0, 2)
        roc_63d = round(((curr - float(c.iloc[-min(63, len(c))])) / float(c.iloc[-min(63, len(c))])) * 100.0, 2)

        # Historical Volatility (20D Annualized)
        log_ret = np.log(c / c.shift(1))
        hist_vol = round(float(log_ret.rolling(20, min_periods=5).std().iloc[-1] * np.sqrt(252) * 100.0), 1) if len(log_ret) > 5 else 20.0

        # Cumulative VWAP
        typical_p = (h + l + c) / 3.0
        v_cum = v.cumsum()
        cum_vwap = float(((typical_p * v).cumsum() / v_cum.replace(0, np.nan)).fillna(curr).iloc[-1])
        vwap_dist_pct = round(((curr - cum_vwap) / cum_vwap) * 100.0, 2) if cum_vwap > 0 else 0.0

        # Dynamic ATR & Stops/Targets
        atr_series = calculate_atr(df, 14)
        atr_val = float(atr_series.iloc[-1]) if not np.isnan(atr_series.iloc[-1]) else curr * 0.02
        sl_price = round(max(0.01, curr - (1.5 * atr_val)), 2)
        tgt_price = round(curr + (3.0 * atr_val), 2)

        # Reversal Guard
        prev_high = float(h.iloc[-2]) if len(df) > 1 else curr
        has_hook = (rsi_latest > rsi_prev) or (curr > prev_high)
        reversal_status = "🟢 Reversal Hook (Safe)" if has_hook else "⚠️ Falling Knife (Wait)"

        # Volume Metrics
        vol_latest = int(v.iloc[-1])
        vol_5d = int(v.iloc[-min(5, len(v)):].mean())
        vol_20d = int(v.rolling(20, min_periods=1).mean().iloc[-1])
        vol_surge_ratio = round(vol_latest / vol_20d, 2) if vol_20d > 0 else 1.0

        raw_expense = item.get("expense", np.nan)
        exp_ratio = float(raw_expense) if pd.notna(raw_expense) else np.nan

        if not is_stock_mode:
            inav_val = round(float(c.iloc[-min(5, len(c)):].median()), 2)
            inav_dislocation_pct = round(((curr - inav_val) / inav_val) * 100.0, 2) if inav_val > 0 else 0.0
            pricing_status = "✅ Clean (<+0.35%)" if inav_dislocation_pct <= 0.35 else f"🚫 High Premium (+{inav_dislocation_pct:.2f}%)"
            fund_friction_val, fund_spread_val = (exp_ratio if not np.isnan(exp_ratio) else 0.20), max(0.0, inav_dislocation_pct)
        else:
            inav_val = np.nan
            inav_dislocation_pct = np.nan
            pricing_status = "✅ Trend Healthy (>200 DMA)" if curr > d200 else "⛔ Trend Broken (<200 DMA)"
            fund_friction_val, fund_spread_val = 0.0, 0.0

        div_yield = float(DIVIDEND_YIELD_MAP.get(t, DIVIDEND_YIELD_MAP.get(clean_sym + ".NS", 0.0)))
        if div_yield >= 3.0:
            div_status = f"💰 High ({div_yield:.1f}%)"
        elif div_yield >= 1.0:
            div_status = f"💵 Moderate ({div_yield:.1f}%)"
        elif div_yield > 0.0:
            div_status = f"🌱 Growth ({div_yield:.1f}%)"
        else:
            div_status = "⚪ Zero"

        records.append({
            "Ticker": clean_sym, "symbol": clean_sym, "Full_Ticker": t, "Name": item["name"], "Category": item["category"],
            "CMP (₹)": round(curr, 2), "iNAV (₹)": inav_val, "iNAV Dislocation %": inav_dislocation_pct,
            "Today Low (₹)": round(today_low, 2), "Today High (₹)": round(today_high, 2),
            "5D Low (₹)": round(weekly_low, 2), "5D High (₹)": round(weekly_high, 2),
            "% from 5D Low": round(((curr - weekly_low) / weekly_low) * 100.0, 2) if weekly_low > 0 else 0.0,
            "14D ATR (₹)": round(atr_val, 2), "Dynamic Vol SL (₹)": sl_price, "Dynamic Vol Target (₹)": tgt_price,
            "Volatility Stop / Target": f"SL: ₹{sl_price:.2f} | Tgt: ₹{tgt_price:.2f}",
            "Falling Knife Guard": reversal_status, "Structural Guard / iNAV": pricing_status,
            "Expense %": exp_ratio, "Dividend Yield %": div_yield, "Dividend Status": div_status,
            "20 DMA": round(d20, 2), "Dist 20DMA %": round(((curr - d20) / d20) * 100.0, 2),
            "50 DMA": round(d50, 2), "Dist 50DMA %": round(((curr - d50) / d50) * 100.0, 2),
            "100 DMA": round(d100, 2), "Dist 100DMA %": round(((curr - d100) / d100) * 100.0, 2),
            "200 DMA": round(d200, 2), "Dist 200DMA %": round(((curr - d200) / d200) * 100.0, 2),
            "9 EMA": round(ema9, 2), "21 EMA": round(ema21, 2), "EMA Trend": "Bullish" if ema9 > ema21 else "Bearish",
            "52W Low (₹)": round(low52, 2), "Dist 52W Low %": round(((curr - low52) / low52) * 100.0, 2) if low52 > 0 else 0.0,
            "52W High (₹)": round(high52, 2), "Dist 52W High %": round(((curr - high52) / high52) * 100.0, 2) if high52 > 0 else 0.0,
            "ATR % of CMP": round((atr_val / curr) * 100.0, 2) if curr > 0 else 0.0,
            "RS Spread 21D %": round(roc_21d - bench_roc_21d, 2),
            "RSI (14D)": round(rsi_latest, 1), "RSI Delta": rsi_delta,
            "Bollinger %B": round(percent_b, 2), "BB Upper": round(bb_upper, 2), "BB Lower": round(bb_lower, 2),
            "Dist VWAP %": vwap_dist_pct, "Volume Surge Ratio": vol_surge_ratio,
            "MACD Line": round(macd_val, 2), "MACD Signal": round(macd_sig_val, 2), "MACD Hist": round(macd_hist_val, 2), "MACD Cross": macd_status,
            "Stoch %K": round(stoch_k_val, 1), "Stoch %D": round(stoch_d_val, 1),
            "Momentum 1M %": roc_21d, "Momentum 3M %": roc_63d, "Historical Volatility %": hist_vol,
            "Fund_Friction": fund_friction_val, "Fund_Spread": fund_spread_val,
            "Volume": vol_latest, "5D Avg Vol": vol_5d, "20D Avg Vol": vol_20d,
            "Is_Safe_Haven": item.get("category") == "Commodity",
            "Data_Status": "🟢 Healthy", "Last_CMP": round(curr, 2), "Last_Updated": datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        })

    df_out = pd.DataFrame(records)
    if not df_out.empty:
        df_out["Rank_RSI_Buy"] = df_out["RSI (14D)"].rank(ascending=True, pct=True) * 100.0
        df_out["Rank_200DMA_Buy"] = df_out["Dist 200DMA %"].rank(ascending=True, pct=True) * 100.0
        df_out["Rank_BB_Buy"] = df_out["Bollinger %B"].rank(ascending=True, pct=True) * 100.0
        df_out["Rank_VWAP_Buy"] = df_out["Dist VWAP %"].rank(ascending=True, pct=True) * 100.0
        df_out["Rank_Vol_Buy"] = df_out["Volume Surge Ratio"].rank(ascending=False, pct=True) * 100.0
        df_out["Rank_Stoch_Buy"] = df_out["Stoch %K"].rank(ascending=True, pct=True) * 100.0
        df_out["Rank_Div_Buy"] = df_out["Dividend Yield %"].rank(ascending=False, pct=True) * 100.0

        df_out["Rank_RSI_Sell"] = df_out["RSI (14D)"].rank(ascending=False, pct=True) * 100.0
        df_out["Rank_200DMA_Sell"] = df_out["Dist 200DMA %"].rank(ascending=False, pct=True) * 100.0
        df_out["Rank_BB_Sell"] = df_out["Bollinger %B"].rank(ascending=False, pct=True) * 100.0
        df_out["Rank_VWAP_Sell"] = df_out["Dist VWAP %"].rank(ascending=False, pct=True) * 100.0
        df_out["Rank_Stoch_Sell"] = df_out["Stoch %K"].rank(ascending=False, pct=True) * 100.0

        if not is_stock_mode:
            df_out["Rank_Exp"] = df_out["Expense %"].fillna(0.25).rank(ascending=True, pct=True) * 100.0
            df_out["Rank_Spread"] = df_out["Fund_Spread"].rank(ascending=True, pct=True) * 100.0
            df_out["Fundamental Score"] = round((0.60 * df_out["Rank_Exp"]) + (0.40 * df_out["Rank_Spread"]), 1)
        else:
            df_out["Rank_Liq"] = df_out["20D Avg Vol"].rank(ascending=False, pct=True) * 100.0
            trend_bonus = np.where(df_out["CMP (₹)"] > df_out["200 DMA"], 15.0, 75.0)
            df_out["Fundamental Score"] = round((0.70 * df_out["Rank_Liq"]) + (0.30 * trend_bonus), 1)

        cfg = get_active_runtime_config()
        weights_cfg = cfg.get("weights", {})
        
        # Intraday dynamic weights
        intra_w = weights_cfg.get("Intraday", {})
        w_ivol = float(intra_w.get("w_vol", 35))
        w_irsi = float(intra_w.get("w_rsi", 30))
        w_ibb = float(intra_w.get("w_bb", 20))
        w_ivwap = float(intra_w.get("w_vwap", 15))
        tot_intra = max(0.01, w_ivol + w_irsi + w_ibb + w_ivwap)
        
        # Swing dynamic weights
        swing_w = weights_cfg.get("Swing / Positional", {})
        w_srsi = float(swing_w.get("w_rsi", 30))
        w_sdma = float(swing_w.get("w_dma", 25))
        w_sbb = float(swing_w.get("w_bb", 20))
        w_svwap = float(swing_w.get("w_vwap", 15))
        w_sstoch = float(swing_w.get("w_stoch", 10))
        tot_swing = max(0.01, w_srsi + w_sdma + w_sbb + w_svwap + w_sstoch)

        # Long-Term dynamic weights
        lt_w = weights_cfg.get("Long-Term", {})
        w_ldma = float(lt_w.get("w_dma", 40))
        w_ldiv = float(lt_w.get("w_div", 15))
        w_lrsi = float(lt_w.get("w_rsi", 15))
        w_lbb = float(lt_w.get("w_bb", 15))
        w_lexp = float(lt_w.get("w_exp", 15))
        tot_lt = max(0.01, w_ldma + w_ldiv + w_lrsi + w_lbb + w_lexp)

        df_out["Technical Score Buy Intraday"] = round(
            ((w_irsi/tot_intra) * df_out["Rank_RSI_Buy"]) + 
            ((w_ivol/tot_intra) * df_out["Rank_Vol_Buy"]) + 
            ((w_ibb/tot_intra) * df_out["Rank_BB_Buy"]) + 
            ((w_ivwap/tot_intra) * df_out["Rank_VWAP_Buy"]), 1
        )
        df_out["Technical Score Buy Swing"] = round(
            ((w_srsi/tot_swing) * df_out["Rank_RSI_Buy"]) + 
            ((w_sdma/tot_swing) * df_out["Rank_200DMA_Buy"]) + 
            ((w_sbb/tot_swing) * df_out["Rank_BB_Buy"]) + 
            ((w_svwap/tot_swing) * df_out["Rank_VWAP_Buy"]) + 
            ((w_sstoch/tot_swing) * df_out["Rank_Stoch_Buy"]), 1
        )
        df_out["Technical Score Buy LongTerm"] = round(
            ((w_lrsi/tot_lt) * df_out["Rank_RSI_Buy"]) + 
            ((w_ldma/tot_lt) * df_out["Rank_200DMA_Buy"]) + 
            ((w_ldiv/tot_lt) * df_out["Rank_Div_Buy"]) + 
            ((w_lbb/tot_lt) * df_out["Rank_BB_Buy"]) + 
            ((w_lexp/tot_lt) * df_out["Fundamental Score"]), 1
        )
        df_out["Technical Score Sell"] = round(
            (0.35 * df_out["Rank_RSI_Sell"]) + (0.25 * df_out["Rank_200DMA_Sell"]) + (0.20 * df_out["Rank_BB_Sell"]) + (0.10 * df_out["Rank_VWAP_Sell"]) + (0.10 * df_out["Rank_Stoch_Sell"]), 1
        )
        df_out["Technical Score"] = df_out["Technical Score Buy Swing"]
        
        # Default preset weights
        def_w = weights_cfg.get("Default", {})
        def_t_w = (float(def_w.get("w_dma", 35)) + float(def_w.get("w_rsi", 30)) + float(def_w.get("w_low", 20))) / 100.0
        def_f_w = float(def_w.get("w_exp", 15)) / 100.0
        tot_def = max(0.01, def_t_w + def_f_w)
        df_out["Composite Buy Score"] = round(((def_t_w/tot_def) * df_out["Technical Score"]) + ((def_f_w/tot_def) * df_out["Fundamental Score"]), 1)

        # Institutional Action Signal Classification
        def _classify_action_signal(r):
            rsi = float(r.get("RSI (14D)", 50.0))
            d200 = float(r.get("Dist 200DMA %", 0.0))
            fk = str(r.get("Falling Knife Guard", ""))
            
            # Conflict / High Breakdown Risk
            if "Falling Knife" in fk and rsi < 35.0:
                return "AVOID (Falling Knife Risk)"
            if d200 < -25.0 and rsi < 35.0:
                return "AVOID (Secular Breakdown)"
            
            # Accumulate / Buy Signals
            if rsi < 38.0 and d200 < 5.0:
                return "ACCUMULATE (Oversold Dip)"
            if rsi < 50.0 and d200 < 0.0:
                return "ACCUMULATE (Value Support)"
            if rsi < 54.0 and float(r.get("Bollinger %B", 0.5)) < 0.30:
                return "BUY (Mean Reversion)"
                
            # Sell / Profit Booking Signals
            if rsi >= 70.0 or (rsi >= 65.0 and d200 > 15.0):
                return "SELL (Overbought Exhaustion)"
            if d200 > 22.0:
                return "SELL (Extended Trend)"
            if rsi >= 62.0 and float(r.get("Bollinger %B", 0.5)) > 0.90:
                return "BOOK PROFIT (Upper Channel)"
                
            return "HOLD / NEUTRAL"

        df_out["Action Signal"] = df_out.apply(_classify_action_signal, axis=1)

    regime_payload = {
        "regime": regime, "desc": regime_desc, "n500_cmp": n500_curr,
        "n500_d50": n500_d50, "n500_d200": n500_d200, "vix": current_vix,
        "vix_badge": vix_badge, "vix_factor": vix_factor, "vix_advice": vix_advice
    }
    return df_out, regime_payload

# =====================================================================
# TOP CONVICTION CANDIDATE SELECTION (TOP 3 BUY + TOP 3 SELL)
# =====================================================================
def get_top_conviction_candidates(metrics_df, preset_name="Default", is_stock_mode=False, limit=3):
    if metrics_df is None or metrics_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    cfg = get_active_runtime_config()
    risk_cfg = cfg.get("risk_parameters", {})

    p_clean = preset_name.strip()
    if p_clean in ["Swing / Positional", "Swing"]:
        w_t, w_f = 0.80, 0.20
        tech_buy_col = "Technical Score Buy Swing"
    elif p_clean in ["Intraday"]:
        w_t, w_f = 0.85, 0.15
        tech_buy_col = "Technical Score Buy Intraday"
    elif p_clean in ["Long-Term"]:
        w_t, w_f = 0.40, 0.60
        tech_buy_col = "Technical Score Buy LongTerm"
    elif p_clean in ["AI / RAG", "AI-Confluence"]:
        w_t, w_f = 0.70, 0.30
        tech_buy_col = "Technical Score Buy Swing"
    else:  # Default
        w_t, w_f = 0.60, 0.40
        tech_buy_col = "Technical Score Buy Swing"

    buy_candidates = []
    sell_candidates = []

    for _, row in metrics_df.iterrows():
        sym = row.get("Ticker", row.get("symbol", ""))
        if not sym or str(sym).lower() == "nan":
            continue
            
        curr_p = float(row.get("CMP (₹)", 0.0))
        if curr_p <= 0:
            continue

        rsi = float(row.get("RSI (14D)", 50.0))
        dist_200 = float(row.get("Dist 200DMA %", 0.0))
        dist_low = float(row.get("Dist 52W Low %", 0.0))
        range_pct = float(row.get("52W Range %", 50.0))
        vol_ratio = float(row.get("Volume Surge Ratio", 1.0))
        act_sig = str(row.get("Action Signal", "ACCUMULATE"))
        atr = float(row.get("14D ATR (₹)", curr_p * 0.02))
        f_score = float(row.get("Fundamental Score", 50.0))
        t_buy = float(row.get(tech_buy_col, row.get("Technical Score", 50.0)))
        t_sell = float(row.get("Technical Score Sell", 50.0))

        if p_clean == "Intraday":
            sl_mult = float(risk_cfg.get("intraday_sl_multiplier", 1.0))
            tgt_mult = float(risk_cfg.get("intraday_target_multiplier", 1.8))
        elif p_clean == "Long-Term":
            sl_mult = float(risk_cfg.get("longterm_sl_multiplier", 2.5))
            tgt_mult = float(risk_cfg.get("longterm_target_multiplier", 5.0))
        else:
            sl_mult = float(risk_cfg.get("swing_sl_multiplier", 1.5))
            tgt_mult = float(risk_cfg.get("swing_target_multiplier", 3.0))

        # Determine exact buy score directly aligned with metrics_df for 100% transparent sorting
        if p_clean == "Default" and "Composite Buy Score" in row and pd.notna(row["Composite Buy Score"]):
            buy_composite = float(row["Composite Buy Score"])
        elif p_clean in ["Swing / Positional", "Swing"] and "Technical Score Buy Swing" in row and pd.notna(row["Technical Score Buy Swing"]):
            buy_composite = float(row["Technical Score Buy Swing"])
        elif p_clean == "Long-Term" and "Technical Score Buy LongTerm" in row and pd.notna(row["Technical Score Buy LongTerm"]):
            buy_composite = float(row["Technical Score Buy LongTerm"])
        elif p_clean == "Intraday" and "Technical Score Buy Intraday" in row and pd.notna(row["Technical Score Buy Intraday"]):
            buy_composite = float(row["Technical Score Buy Intraday"])
        else:
            buy_composite = round((w_t * t_buy) + (w_f * f_score), 1)

        # Compute true Overbought Exit Urgency Score (0 to 100)
        # Higher score = more severely overbought / extended (Stronger sell urgency)
        d200_norm = min(100.0, max(0.0, 50.0 + (dist_200 * 2.0)))
        sell_exit_urgency = round((0.45 * rsi) + (0.35 * d200_norm) + (0.20 * range_pct), 1)

        sl_buy = round(max(0.01, curr_p - (sl_mult * atr)), 2)
        tgt_buy = round(curr_p + (tgt_mult * atr), 2)
        sl_sell = round(curr_p + (sl_mult * atr), 2)
        tgt_sell = round(max(0.01, curr_p - (tgt_mult * atr)), 2)

        # Explain criteria met for Buy
        buy_criteria_items = []
        if rsi < 40:
            buy_criteria_items.append(f"RSI {rsi:.1f} ≤ 40 (Oversold Dip)")
        elif rsi < 55:
            buy_criteria_items.append(f"RSI {rsi:.1f} (Favourable Momentum)")
        else:
            buy_criteria_items.append(f"RSI {rsi:.1f}")

        if dist_200 < 0:
            buy_criteria_items.append(f"Dist 200DMA {dist_200:+.1f}% (Value Discount)")
        else:
            buy_criteria_items.append(f"Dist 200DMA {dist_200:+.1f}% (Trend Support)")

        if range_pct <= 35:
            buy_criteria_items.append(f"52W Range {range_pct:.1f}% (Cycle Base)")
        elif dist_low < 15:
            buy_criteria_items.append(f"+{dist_low:.1f}% from 52W Low")

        if vol_ratio >= 1.2:
            buy_criteria_items.append(f"Volume Surge {vol_ratio:.1f}x")

        buy_crit_str = " • ".join(buy_criteria_items) if buy_criteria_items else f"Score {buy_composite:.1f} Rank"

        # Explain criteria met for Sell
        sell_criteria_items = []
        if rsi >= 65:
            sell_criteria_items.append(f"RSI {rsi:.1f} ≥ 65 (Overbought)")
        if dist_200 > 12:
            sell_criteria_items.append(f"Dist 200DMA {dist_200:+.1f}% (Extended)")
        if range_pct >= 80:
            sell_criteria_items.append(f"52W Range {range_pct:.1f}% (Cycle High)")
        if not sell_criteria_items:
            sell_criteria_items.append(f"Overbought Urgency {sell_exit_urgency:.1f}/100")
        sell_crit_str = " • ".join(sell_criteria_items)

        # 1. Buy Qualification: Disallow overbought or conflicted breakdown assets
        if rsi < 60.0 and "AVOID" not in act_sig:
            buy_candidates.append({
                "Ticker": sym, "symbol": sym, "Name": row.get("Name", sym), "Category": row.get("Category", "General"),
                "Signal": "BUY", "CMP (₹)": curr_p, "RSI (14D)": rsi,
                "Composite Score": buy_composite, "Stop_Loss": sl_buy, "Target": tgt_buy,
                "14D ATR (₹)": atr, "Volume Surge": vol_ratio,
                "Dist 200DMA %": dist_200, "Dist 52W Low %": dist_low, "52W Range %": range_pct,
                "Action Signal": act_sig, "Criteria_Met": buy_crit_str,
                "Preset": preset_name, "Asset_Class": "Stock" if is_stock_mode else "ETF"
            })

        # 2. Sell Qualification: Strictly requires overbought / extension triggers (NEVER an oversold asset!)
        is_sell_eligible = (
            rsi >= 58.0 or
            dist_200 >= 8.0 or
            range_pct >= 75.0 or
            "SELL" in act_sig or
            "BOOK PROFIT" in act_sig
        )
        if is_sell_eligible and rsi >= 50.0 and "AVOID" not in act_sig:
            sell_candidates.append({
                "Ticker": sym, "symbol": sym, "Name": row.get("Name", sym), "Category": row.get("Category", "General"),
                "Signal": "SELL", "CMP (₹)": curr_p, "RSI (14D)": rsi,
                "Composite Score": sell_exit_urgency, "Stop_Loss": sl_sell, "Target": tgt_sell,
                "14D ATR (₹)": atr, "Volume Surge": vol_ratio,
                "Dist 200DMA %": dist_200, "Dist 52W Low %": dist_low, "52W Range %": range_pct,
                "Action Signal": act_sig, "Criteria_Met": sell_crit_str,
                "Preset": preset_name, "Asset_Class": "Stock" if is_stock_mode else "ETF"
            })

    buy_df = pd.DataFrame(buy_candidates)
    sell_df = pd.DataFrame(sell_candidates)

    if is_stock_mode and p_clean == "Long-Term" and not buy_df.empty:
        healthy_mask = metrics_df["Dist 200DMA %"] > -10.0
        healthy_tickers = set(metrics_df[healthy_mask]["Ticker"])
        buy_df = buy_df[buy_df["Ticker"].isin(healthy_tickers)]

    standard_cand_cols = [
        "Ticker", "symbol", "Name", "Category", "Signal", "CMP (₹)", "RSI (14D)",
        "Composite Score", "Stop_Loss", "Target", "14D ATR (₹)", "Volume Surge",
        "Dist 200DMA %", "Dist 52W Low %", "52W Range %", "Action Signal", "Criteria_Met",
        "Preset", "Asset_Class"
    ]

    top_buy = buy_df.sort_values(by="Composite Score", ascending=True).head(limit).reset_index(drop=True) if not buy_df.empty else pd.DataFrame(columns=standard_cand_cols)

    # ANTI-CONFLICT FILTER: Strictly remove any ticker already selected in top_buy from sell_df
    if not top_buy.empty and not sell_df.empty:
        top_buy_syms = set(top_buy["Ticker"].astype(str).str.replace(".NS", "").str.upper())
        sell_df = sell_df[~sell_df["Ticker"].astype(str).str.replace(".NS", "").str.upper().isin(top_buy_syms)]

    # Sort genuinely overbought sell candidates by highest exit urgency
    top_sell = sell_df.sort_values(by="Composite Score", ascending=False).head(limit).reset_index(drop=True) if not sell_df.empty else pd.DataFrame(columns=standard_cand_cols)

    return top_buy, top_sell

# =====================================================================
# TRADE EXECUTION VALIDATION
# =====================================================================
def validate_trade_execution(ticker, signal_action, preset_name, qty_planned, existing_positions_df):
    if qty_planned <= 0:
        return False, 0, "Calculated order quantity is 0."

    clean_sym = ticker.replace(".NS", "").strip().upper()
    action = signal_action.strip().upper()

    if action == "SELL":
        if existing_positions_df is None or existing_positions_df.empty:
            return False, 0, f"Cannot SELL {clean_sym}: Ledger has no active positions."

        pos_mask = (
            (existing_positions_df["Ticker"].astype(str).str.replace(".NS", "").str.upper() == clean_sym) &
            (existing_positions_df["Status"].astype(str).str.upper() == "ACTIVE")
        )
        matched = existing_positions_df[pos_mask]
        if matched.empty:
            return False, 0, f"Cannot SELL {clean_sym}: 0 active units held in ledger."

        held_qty = float(pd.to_numeric(matched["Executed_Qty"], errors="coerce").sum())
        if held_qty <= 0:
            return False, 0, f"Cannot SELL {clean_sym}: Net quantity is 0."

        final_qty = int(min(held_qty, qty_planned))
        return True, max(1, final_qty), f"Approved SELL: {final_qty} units available."

    return True, qty_planned, f"Approved BUY entry for {clean_sym} under {preset_name}."

# =====================================================================
# INBUILT COMPREHENSIVE EXIT ENGINE (DYNAMIC SL / TARGET / SQUAREOFF)
# =====================================================================
def evaluate_trade_exits(trades_df, raw_data, force_squareoff_intraday=False):
    if trades_df is None or trades_df.empty:
        return trades_df

    updated = trades_df.copy()
    now_ist = datetime.datetime.now(IST)
    current_time_str = now_ist.strftime("%H:%M")
    is_auto_squareoff_time = (current_time_str >= "15:10") or force_squareoff_intraday

    for idx, row in updated.iterrows():
        status = str(row.get("Status", "ACTIVE")).strip().upper()
        if status != "ACTIVE":
            continue

        sym = str(row.get("Ticker", "")).replace(".NS", "").strip()
        df = extract_ticker_df(raw_data, sym)
        if df.empty or "Close" not in df.columns:
            continue

        c_series = df["Close"].dropna()
        if c_series.empty:
            continue
        current_p = float(c_series.iloc[-1])

        entry_p = float(pd.to_numeric(row.get("Entry_Price", 0), errors="coerce") or 0.0)
        stop_l = float(pd.to_numeric(row.get("Stop_Loss", 0), errors="coerce") or 0.0)
        target_p = float(pd.to_numeric(row.get("Target", 0), errors="coerce") or 0.0)
        qty = float(pd.to_numeric(row.get("Executed_Qty", 1), errors="coerce") or 1.0)
        preset = str(row.get("Strategy_Preset", "")).strip().upper()
        trigger_type = str(row.get("Trigger_Type", "")).strip().upper()

        if entry_p <= 0:
            continue

        pnl_rs = round((current_p - entry_p) * qty, 2)
        pnl_pct = round(((current_p - entry_p) / entry_p) * 100.0, 2)

        # Hold duration calculation
        hold_days = 0
        entry_ts_str = str(row.get("Execution_Timestamp", ""))
        try:
            entry_dt = datetime.datetime.strptime(entry_ts_str, "%Y-%m-%d %H:%M:%S")
            hold_days = max(0, (now_ist.date() - entry_dt.date()).days)
        except Exception:
            pass

        cfg = get_active_runtime_config()
        risk_cfg = cfg.get("risk_parameters", {})
        trail_act_pct = float(risk_cfg.get("trailing_stop_activation_pct", 3.0))
        trail_lock_pct = float(risk_cfg.get("trailing_stop_lock_pct", 0.5))
        overbought_rsi = float(risk_cfg.get("overbought_rsi_exit_threshold", 76.0))

        # Trailing stop: Lock in profit once gain exceeds activation %
        if pnl_pct >= trail_act_pct:
            trailing_floor = round(entry_p * (1.0 + (trail_lock_pct / 100.0)), 2)
            if trailing_floor > stop_l:
                updated.at[idx, "Stop_Loss"] = trailing_floor
                stop_l = trailing_floor

        # Exit 1: Intraday Auto-Squareoff
        if ("INTRADAY" in preset or "INTRADAY" in trigger_type) and is_auto_squareoff_time:
            updated.at[idx, "Status"] = "INTRADAY_SQUAREOFF"
            updated.at[idx, "Exit_Price"] = current_p
            updated.at[idx, "Exit_Timestamp"] = now_ist.strftime("%Y-%m-%d %H:%M:%S")
            updated.at[idx, "Exit_Reason"] = "3:10 PM Intraday Auto-Squareoff"
            updated.at[idx, "Hold_Duration_Days"] = hold_days
            updated.at[idx, "Live_CMP"] = current_p
            updated.at[idx, "PnL_Rs"] = pnl_rs
            updated.at[idx, "PnL_Pct"] = f"{pnl_pct:+.2f}%"
            logger.info(f"[EXIT-INTRADAY] {sym} squared off at ₹{current_p:.2f} (PnL: ₹{pnl_rs:.2f})")
            continue

        # Exit 2: Target Achieved
        if target_p > 0 and current_p >= target_p:
            updated.at[idx, "Status"] = "TARGET_ACHIEVED"
            updated.at[idx, "Exit_Price"] = current_p
            updated.at[idx, "Exit_Timestamp"] = now_ist.strftime("%Y-%m-%d %H:%M:%S")
            updated.at[idx, "Exit_Reason"] = "Target Price Reached"
            updated.at[idx, "Hold_Duration_Days"] = hold_days
            updated.at[idx, "Live_CMP"] = current_p
            updated.at[idx, "PnL_Rs"] = pnl_rs
            updated.at[idx, "PnL_Pct"] = f"{pnl_pct:+.2f}%"
            logger.info(f"[EXIT-TARGET] {sym} hit target ₹{target_p:.2f} at ₹{current_p:.2f} (+{pnl_pct:.2f}%)")
            continue

        # Exit 3: Stop-Loss Hit
        if stop_l > 0 and current_p <= stop_l:
            updated.at[idx, "Status"] = "STOP_LOSS_HIT"
            updated.at[idx, "Exit_Price"] = current_p
            updated.at[idx, "Exit_Timestamp"] = now_ist.strftime("%Y-%m-%d %H:%M:%S")
            updated.at[idx, "Exit_Reason"] = "Stop-Loss Hit" if stop_l <= entry_p else "Trailing Stop Triggered"
            updated.at[idx, "Hold_Duration_Days"] = hold_days
            updated.at[idx, "Live_CMP"] = current_p
            updated.at[idx, "PnL_Rs"] = pnl_rs
            updated.at[idx, "PnL_Pct"] = f"{pnl_pct:+.2f}%"
            logger.info(f"[EXIT-STOP] {sym} hit stop ₹{stop_l:.2f} at ₹{current_p:.2f} ({pnl_pct:.2f}%)")
            continue

        # Exit 4: Overbought Swing Exhaustion (RSI >= overbought_rsi)
        if "SWING" in preset:
            rsi_series = calculate_rsi_series(c_series)
            if not rsi_series.empty and float(rsi_series.iloc[-1]) >= overbought_rsi and pnl_pct > 1.5:
                updated.at[idx, "Status"] = "OVERBOUGHT_EXIT"
                updated.at[idx, "Exit_Price"] = current_p
                updated.at[idx, "Exit_Timestamp"] = now_ist.strftime("%Y-%m-%d %H:%M:%S")
                updated.at[idx, "Exit_Reason"] = f"Overbought Exhaustion (RSI >= {overbought_rsi})"
                updated.at[idx, "Hold_Duration_Days"] = hold_days
                updated.at[idx, "Live_CMP"] = current_p
                updated.at[idx, "PnL_Rs"] = pnl_rs
                updated.at[idx, "PnL_Pct"] = f"{pnl_pct:+.2f}%"
                logger.info(f"[EXIT-SWING-RSI] {sym} exited on overbought RSI >= {overbought_rsi} at ₹{current_p:.2f}")
                continue

        # If trade remains active, update live MTM figures
        updated.at[idx, "Live_CMP"] = current_p
        updated.at[idx, "PnL_Rs"] = pnl_rs
        updated.at[idx, "PnL_Pct"] = f"{pnl_pct:+.2f}%"
        updated.at[idx, "Hold_Duration_Days"] = hold_days

    return updated


def get_ai_rag_conviction_candidates(metrics_df, is_stock_mode=False, limit=3):
    """Bridge/re-export to ml_optimizer.get_ai_rag_conviction_candidates with fallback."""
    try:
        from ml_optimizer import get_ai_rag_conviction_candidates as _ai_func
        return _ai_func(metrics_df, is_stock_mode=is_stock_mode, limit=limit)
    except Exception:
        return get_top_conviction_candidates(metrics_df, preset_name="Default", is_stock_mode=is_stock_mode, limit=limit)
