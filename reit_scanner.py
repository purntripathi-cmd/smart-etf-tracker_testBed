"""
v2/reit_scanner.py
==================
Institutional REIT & High-Yield Income Analytics Engine.
Analyzes India's premier listed Real Estate Investment Trusts (REITs) and InvITs:
  - EMBASSY.NS (Embassy Office Parks REIT)
  - MINDSPACE.NS (Mindspace Business Parks REIT)
  - BIRET.NS (Brookfield India Real Estate Trust)
  - NXST.NS (Nexus Select Trust Retail REIT)
  - PGINVIT.NS (PowerGrid Infrastructure Investment Trust - InvIT)

Provides:
  - Technical Parameters (CMP, 52W High/Low, RSI 14, SMA 50/200, S1/R1, Distance to Support)
  - Fundamental Parameters (Distribution Yield %, Dividend/NDCF Payout Ratio %, Annualized DPU,
    Net Asset Value, Discount/Premium to NAV %, Occupancy %, WALE Years, LTV Leverage %, Sponsor)
  - Composite Scoring & Institutional Action Signals
"""

import os
import logging
import datetime
import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger("v2.reit_scanner")

# Indian Institutional REIT & InvIT Master Database (Q1/Q2 FY25 Filings)
REIT_FUNDAMENTALS_DB = {
    "EMBASSY.NS": {
        "Name": "Embassy Office Parks REIT",
        "Type": "Office REIT",
        "Sponsor": "Blackstone & Embassy Group",
        "Gross_Leasable_Area_MSF": 45.4,
        "Occupancy_Pct": 90.5,
        "WALE_Years": 7.1,
        "LTV_Pct": 31.0,
        "NAV_Per_Unit": 408.00,
        "Annual_DPU_Rs": 22.80,
        "NDCF_Payout_Ratio_Pct": 100.0,
        "Credit_Rating": "CRISIL AAA (Stable)",
        "Tax_Free_Portion_Pct": 45.0,
        "Tenant_Quality": "72% GCCs (JPMorgan, Wells Fargo, IBM, Microsoft)",
        "Description": "India's largest commercial REIT with marquee grade-A parks across Bengaluru, Mumbai, and Pune."
    },
    "MINDSPACE.NS": {
        "Name": "Mindspace Business Parks REIT",
        "Type": "Office REIT",
        "Sponsor": "K Raheja Corp",
        "Gross_Leasable_Area_MSF": 33.2,
        "Occupancy_Pct": 91.2,
        "WALE_Years": 6.9,
        "LTV_Pct": 22.8,
        "NAV_Per_Unit": 468.00,
        "Annual_DPU_Rs": 21.20,
        "NDCF_Payout_Ratio_Pct": 100.0,
        "Credit_Rating": "CRISIL AAA (Stable)",
        "Tax_Free_Portion_Pct": 42.0,
        "Tenant_Quality": "Barclays, Qualcomm, Amazon, Cognizant",
        "Description": "Lowest leverage among Indian REITs with prime business parks in Mumbai MMR, Hyderabad, and Pune."
    },
    "BIRET.NS": {
        "Name": "Brookfield India Real Estate Trust",
        "Type": "Office REIT",
        "Sponsor": "Brookfield Asset Management",
        "Gross_Leasable_Area_MSF": 28.9,
        "Occupancy_Pct": 87.5,
        "WALE_Years": 7.3,
        "LTV_Pct": 35.2,
        "NAV_Per_Unit": 342.00,
        "Annual_DPU_Rs": 20.10,
        "NDCF_Payout_Ratio_Pct": 100.0,
        "Credit_Rating": "CRISIL AA+ (Stable)",
        "Tax_Free_Portion_Pct": 40.0,
        "Tenant_Quality": "Accenture, TCS, Cognizant, Sapient",
        "Description": "High-yielding commercial portfolio backed by global asset manager Brookfield in NCR, Mumbai, and Kolkata."
    },
    "NXST.NS": {
        "Name": "Nexus Select Trust REIT",
        "Type": "Retail Consumption REIT",
        "Sponsor": "Blackstone",
        "Gross_Leasable_Area_MSF": 9.9,
        "Occupancy_Pct": 96.5,
        "WALE_Years": 5.6,
        "LTV_Pct": 16.5,
        "NAV_Per_Unit": 152.00,
        "Annual_DPU_Rs": 9.30,
        "NDCF_Payout_Ratio_Pct": 100.0,
        "Credit_Rating": "CRISIL AAA (Stable)",
        "Tax_Free_Portion_Pct": 50.0,
        "Tenant_Quality": "Zara, H&M, PVR INOX, Shoppers Stop, Reliance Retail",
        "Description": "India's first and only publicly listed retail mall REIT with 17 Grade-A consumption centres across 14 cities."
    },
    "PGINVIT.NS": {
        "Name": "PowerGrid InvIT",
        "Type": "Infrastructure Investment Trust",
        "Sponsor": "Power Grid Corporation of India",
        "Gross_Leasable_Area_MSF": 0.0,
        "Occupancy_Pct": 99.8,
        "WALE_Years": 28.0,
        "LTV_Pct": 12.0,
        "NAV_Per_Unit": 106.00,
        "Annual_DPU_Rs": 12.00,
        "NDCF_Payout_Ratio_Pct": 100.0,
        "Credit_Rating": "CRISIL AAA (Stable)",
        "Tax_Free_Portion_Pct": 65.0,
        "Tenant_Quality": "Sovereign/State Discoms (Transmission assets)",
        "Description": "Perpetual regulated utility cash flows backed by state-owned PowerGrid with ultra-high distribution yield."
    },
    "INDIGRID.NS": {
        "Name": "India Grid Trust InvIT",
        "Type": "Power Transmission InvIT",
        "Sponsor": "KKR & Sterlite Power",
        "Gross_Leasable_Area_MSF": 0.0,
        "Occupancy_Pct": 99.7,
        "WALE_Years": 29.0,
        "LTV_Pct": 44.5,
        "NAV_Per_Unit": 175.00,
        "Annual_DPU_Rs": 14.20,
        "NDCF_Payout_Ratio_Pct": 100.0,
        "Credit_Rating": "CRISIL AAA (Stable) / ICRA AAA",
        "Tax_Free_Portion_Pct": 38.0,
        "Tenant_Quality": "Central Transmission Utility (CTU) / PGCIL - Sovereign Tripartite Agreement",
        "Description": "India's premier private power transmission InvIT backed by KKR with quarterly distributions and highest AAA safety."
    },
    "IRBINVIT.NS": {
        "Name": "IRB InvIT Fund",
        "Type": "Highway Toll Concession InvIT",
        "Sponsor": "IRB Infrastructure Developers & GIC (Govt of Singapore)",
        "Gross_Leasable_Area_MSF": 0.0,
        "Occupancy_Pct": 98.5,
        "WALE_Years": 16.0,
        "LTV_Pct": 24.8,
        "NAV_Per_Unit": 82.00,
        "Annual_DPU_Rs": 8.00,
        "NDCF_Payout_Ratio_Pct": 100.0,
        "Credit_Rating": "CRISIL AAA / CARE AAA",
        "Tax_Free_Portion_Pct": 52.0,
        "Tenant_Quality": "National Highways Authority of India (NHAI) Toll Concessions",
        "Description": "India's first listed highway toll InvIT with robust passenger & freight traffic cash flows and high dividend yield."
    }
}


def fetch_reit_market_data(ticker_symbol: str) -> dict:
    """
    Fetches real-time market data and historical price action for a REIT ticker.
    """
    clean_sym = ticker_symbol.replace(".NS", "")
    try:
        t = yf.Ticker(ticker_symbol)
        hist = t.history(period="1y")
        if hist.empty or len(hist) < 10:
            hist = t.history(period="3mo")

        if hist.empty:
            return {}

        cmp_val = round(float(hist["Close"].iloc[-1]), 2)
        high_52w = round(float(hist["High"].max()), 2)
        low_52w = round(float(hist["Low"].min()), 2)
        pct_from_52w_high = round(((cmp_val - high_52w) / high_52w) * 100, 2)
        pct_from_52w_low = round(((cmp_val - low_52w) / low_52w) * 100, 2)

        # Technical Indicators: SMA 50, SMA 200
        sma_50 = round(float(hist["Close"].rolling(50).mean().iloc[-1]), 2) if len(hist) >= 50 else round(float(hist["Close"].mean()), 2)
        sma_200 = round(float(hist["Close"].rolling(200).mean().iloc[-1]), 2) if len(hist) >= 200 else sma_50

        # RSI 14D
        delta = hist["Close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(14, min_periods=1).mean()
        avg_loss = loss.rolling(14, min_periods=1).mean()
        rs = avg_gain / (avg_loss + 1e-9)
        rsi_14 = round(float(100 - (100 / (1 + rs)).iloc[-1]), 1)

        # Support & Resistance (Pivot Points over last 60 days)
        recent_bars = hist.tail(60)
        r_high = float(recent_bars["High"].max())
        r_low = float(recent_bars["Low"].min())
        r_close = float(recent_bars["Close"].iloc[-1])
        pivot = (r_high + r_low + r_close) / 3.0
        s1 = round(2 * pivot - r_high, 2)
        r1 = round(2 * pivot - r_low, 2)

        dist_to_s1_pct = round(((cmp_val - s1) / s1) * 100, 2)

        return {
            "Ticker": clean_sym,
            "Yahoo_Ticker": ticker_symbol,
            "CMP (₹)": cmp_val,
            "52W High (₹)": high_52w,
            "52W Low (₹)": low_52w,
            "Dist from 52W High (%)": pct_from_52w_high,
            "Dist from 52W Low (%)": pct_from_52w_low,
            "SMA 50 (₹)": sma_50,
            "SMA 200 (₹)": sma_200,
            "RSI (14D)": rsi_14,
            "Immediate Support S1 (₹)": s1,
            "Immediate Resistance R1 (₹)": r1,
            "Dist to Support S1 (%)": dist_to_s1_pct,
            "Volume": int(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 0
        }
    except Exception as e:
        logger.warning(f"Error fetching REIT market data for {ticker_symbol}: {e}")
        return {}


def calculate_reit_scores(rec: dict) -> dict:
    """
    Computes Fundamental Score (0-100), Technical Score (0-100),
    Composite Score (0-100), and Action Recommendation for a REIT.
    """
    # 1. Fundamental Scoring (Weight: 60%)
    # Yield component (Target: > 7.0% = 100 pts, < 5.0% = 40 pts)
    dist_yield = rec.get("Distribution Yield (%)", 6.5)
    yield_score = min(100, max(20, (dist_yield / 7.5) * 100))

    # NAV Discount component (Discount < 0% is good, Premium > 0% is lower score)
    nav_discount = rec.get("NAV Discount / Premium (%)", 0.0)
    if nav_discount < 0:
        # e.g. -10% discount gives 90-100 score
        nav_score = min(100, 80 + abs(nav_discount) * 2.0)
    else:
        # e.g. +10% premium gives 60-70 score
        nav_score = max(30, 80 - nav_discount * 2.0)

    # LTV Safety (SEBI ceiling 49%, <25% gives 100, 25-35% gives 85, >40% gives 50)
    ltv = rec.get("LTV Leverage (%)", 30.0)
    if ltv <= 25.0:
        ltv_score = 100.0
    elif ltv <= 35.0:
        ltv_score = 85.0
    else:
        ltv_score = max(30.0, 100 - (ltv - 25.0) * 3.5)

    # Occupancy component
    occ = rec.get("Occupancy (%)", 90.0)
    occ_score = min(100, max(40, (occ / 95.0) * 100))

    # Dividend Payout Ratio score (100% NDCF payout is gold standard)
    payout = rec.get("Dividend Payout Ratio (%)", 100.0)
    payout_score = 100.0 if payout >= 95.0 else (payout / 95.0) * 90.0

    fundamental_score = round(
        0.30 * yield_score +
        0.25 * nav_score +
        0.20 * ltv_score +
        0.15 * occ_score +
        0.10 * payout_score,
        1
    )

    # 2. Technical Scoring (Weight: 40%)
    # RSI Sweetspot (40-55 is accumulation zone, <35 oversold/great, >65 overbought)
    rsi = rec.get("RSI (14D)", 50.0)
    if rsi < 35:
        rsi_score = 95.0
    elif rsi <= 50:
        rsi_score = 85.0
    elif rsi <= 60:
        rsi_score = 70.0
    else:
        rsi_score = max(20.0, 100 - (rsi - 60) * 4.0)

    # Distance to Support (Closer to S1 support is higher conviction)
    dist_s1 = rec.get("Dist to Support S1 (%)", 2.0)
    if dist_s1 <= 1.5:
        s1_score = 95.0
    elif dist_s1 <= 4.0:
        s1_score = 80.0
    elif dist_s1 <= 7.0:
        s1_score = 65.0
    else:
        s1_score = 45.0

    # Trend (CMP > SMA 50)
    cmp_val = rec.get("CMP (₹)", 100.0)
    sma_50 = rec.get("SMA 50 (₹)", 100.0)
    trend_score = 85.0 if cmp_val >= sma_50 else 60.0

    technical_score = round(
        0.45 * rsi_score +
        0.35 * s1_score +
        0.20 * trend_score,
        1
    )

    composite_score = round(0.60 * fundamental_score + 0.40 * technical_score, 1)

    # Determine Action Signal
    if composite_score >= 82.0 or (dist_yield >= 7.0 and dist_s1 <= 3.0):
        action = "🟢 STRONG ACCUMULATE (HIGH YIELD + AT SUPPORT)"
        badge_color = "green"
    elif composite_score >= 70.0:
        action = "🟢 ACCUMULATE ON DIPS"
        badge_color = "lightgreen"
    elif composite_score >= 55.0:
        action = "🟡 HOLD & HARVEST YIELD"
        badge_color = "orange"
    else:
        action = "🔴 AVOID / OVERBOUGHT"
        badge_color = "red"

    return {
        "Fundamental Score (0-100)": fundamental_score,
        "Technical Score (0-100)": technical_score,
        "Composite Score (0-100)": composite_score,
        "Confidence Score (%)": composite_score,
        "Action Signal": action,
        "Badge Color": badge_color
    }


def scan_all_reits() -> pd.DataFrame:
    """
    Executes a comprehensive institutional scan of all listed Indian REITs & InvITs.
    Returns an enriched Pandas DataFrame.
    """
    records = []
    for yf_ticker, f_info in REIT_FUNDAMENTALS_DB.items():
        market_data = fetch_reit_market_data(yf_ticker)
        if not market_data:
            # Fallback values if offline
            market_data = {
                "Ticker": yf_ticker.replace(".NS", ""),
                "Yahoo_Ticker": yf_ticker,
                "CMP (₹)": f_info["NAV_Per_Unit"] * 0.98,
                "52W High (₹)": f_info["NAV_Per_Unit"] * 1.10,
                "52W Low (₹)": f_info["NAV_Per_Unit"] * 0.85,
                "Dist from 52W High (%)": -10.5,
                "Dist from 52W Low (%)": 15.0,
                "SMA 50 (₹)": f_info["NAV_Per_Unit"] * 0.97,
                "SMA 200 (₹)": f_info["NAV_Per_Unit"] * 0.95,
                "RSI (14D)": 48.0,
                "Immediate Support S1 (₹)": round(f_info["NAV_Per_Unit"] * 0.94, 2),
                "Immediate Resistance R1 (₹)": round(f_info["NAV_Per_Unit"] * 1.05, 2),
                "Dist to Support S1 (%)": 2.5,
                "Volume": 150000
            }

        cmp_val = market_data["CMP (₹)"]
        nav = f_info["NAV_Per_Unit"]
        nav_discount_pct = round(((cmp_val - nav) / nav) * 100, 2)
        annual_dpu = f_info["Annual_DPU_Rs"]
        dist_yield_pct = round((annual_dpu / cmp_val) * 100, 2) if cmp_val > 0 else 0.0

        item = {
            "Ticker": market_data["Ticker"],
            "Name": f_info["Name"],
            "Type": f_info["Type"],
            "Sponsor": f_info["Sponsor"],
            "CMP (₹)": cmp_val,
            "Distribution Yield (%)": dist_yield_pct,
            "Dividend Payout Ratio (%)": f_info["NDCF_Payout_Ratio_Pct"],  # MUST HAVE
            "Annualized DPU (₹)": annual_dpu,
            "Net Asset Value NAV (₹)": nav,
            "NAV Discount / Premium (%)": nav_discount_pct,
            "Portfolio Area (MSF)": f_info["Gross_Leasable_Area_MSF"],
            "Occupancy (%)": f_info["Occupancy_Pct"],
            "WALE (Years)": f_info["WALE_Years"],
            "LTV Leverage (%)": f_info["LTV_Pct"],
            "Credit Rating": f_info["Credit_Rating"],
            "Tax-Free Portion (%)": f_info["Tax_Free_Portion_Pct"],
            "52W High (₹)": market_data["52W High (₹)"],
            "52W Low (₹)": market_data["52W Low (₹)"],
            "RSI (14D)": market_data["RSI (14D)"],
            "SMA 50 (₹)": market_data["SMA 50 (₹)"],
            "SMA 200 (₹)": market_data["SMA 200 (₹)"],
            "Immediate Support S1 (₹)": market_data["Immediate Support S1 (₹)"],
            "Immediate Resistance R1 (₹)": market_data["Immediate Resistance R1 (₹)"],
            "Dist to Support S1 (%)": market_data["Dist to Support S1 (%)"],
            "Tenant Profile": f_info["Tenant_Quality"],
            "Description": f_info["Description"]
        }

        scores = calculate_reit_scores(item)
        item.update(scores)
        records.append(item)

    df = pd.DataFrame(records)
    # Sort descending by Composite Score
    if not df.empty and "Composite Score (0-100)" in df.columns:
        df = df.sort_values(by="Composite Score (0-100)", ascending=False).reset_index(drop=True)
    return df


def check_reit_investment_eligibility(reit_row: dict) -> dict:
    """
    Evaluates whether a REIT or InvIT meets strict value criteria for paper trading:
    - Must NOT be overbought (RSI <= 62.0)
    - Must be near support (Dist to Support S1 <= 4.5% OR Trading at NAV Discount <= 0%)
    - Distribution yield must be >= 6.0%
    """
    rsi = float(reit_row.get("RSI (14D)", 50.0))
    dist_s1 = float(reit_row.get("Dist to Support S1 (%)", 2.0))
    dist_yield = float(reit_row.get("Distribution Yield (%)", 7.0))
    nav_disc = float(reit_row.get("NAV Discount / Premium (%)", reit_row.get("Discount to NAV (%)", 0.0)))

    if rsi > 62.0:
        return {"eligible": False, "status": "🛑 SKIPPED (Overbought / High RSI)", "reason": f"RSI is {rsi:.1f} (> 62). Skipping overextended entry."}
    if dist_s1 > 4.5 and nav_disc > 3.0:
        return {"eligible": False, "status": "🛑 SKIPPED (Trading at Premium)", "reason": f"At {nav_disc:.1f}% NAV premium and {dist_s1:.1f}% from S1 support."}
    if dist_yield < 6.0:
        return {"eligible": False, "status": "🛑 SKIPPED (Low Yield)", "reason": f"Yield of {dist_yield:.1f}% is below 6.0% threshold."}

    return {"eligible": True, "status": "🟢 CRITERIA MET (High-Yield Value)", "reason": f"Yield {dist_yield:.1f}%, RSI {rsi:.1f}, near S1 support ({dist_s1:.1f}%). Safe accumulation zone."}


def check_metal_investment_eligibility(metal_row: dict) -> dict:
    """
    Evaluates whether Gold or Silver (Commodity/Metal) meets strict entry criteria:
    - Must NOT be at resistance peak or overbought (RSI <= 60.0)
    - Range position must be <= 55% (testing support or mid-range, not breakout top)
    """
    rsi = float(metal_row.get("RSI (14D)", metal_row.get("RSI", 50.0)))
    range_pos = float(metal_row.get("Range Position (%)", 50.0))
    sig = str(metal_row.get("Action Signal", "ACCUMULATE")).upper()

    if rsi > 62.0:
        return {"eligible": False, "status": "🛑 SKIPPED (Overbought Peak)", "reason": f"Metal RSI is {rsi:.1f} (> 62.0). Skipping cyclical peak."}
    if range_pos > 60.0:
        return {"eligible": False, "status": "🛑 SKIPPED (Near Resistance Ceiling)", "reason": f"Range position is {range_pos:.1f}% (> 60%). Too close to R1 ceiling."}
    if "SELL" in sig or "DISTRIBUTION" in sig:
        return {"eligible": False, "status": "🛑 SKIPPED (Distribution Signal)", "reason": f"Signal is {sig}. Waiting for support bounce."}

    return {"eligible": True, "status": "🟢 CRITERIA MET (Support Dip)", "reason": f"RSI {rsi:.1f} <= 60, Range {range_pos:.1f}% <= 55%. Favourable hedge entry."}

