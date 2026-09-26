# =====================================================================
# V2 SUPPORT, RESISTANCE & RANGE-BOUND QUANT ENGINE (SR_ENGINE.PY)
# =====================================================================
"""
Algorithmic Support & Resistance (S/R) Detection, Mean-Reversion Channel
Analysis, 5-Year Empirical Backtesting & Multi-Factor Quant Hub.
"""
import os
import datetime
import numpy as np
import pandas as pd
import yfinance as yf

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
SR_RANKINGS_CSV = os.path.join(LOCAL_DATA_DIR, "sr_5y_fidelity_rankings.csv")


def _safe_series(series, default=0.0):
    if series is None or len(series) == 0:
        return pd.Series([default])
    return series.dropna()


# =====================================================================
# 1. LIVE SUPPORT & RESISTANCE MATRIX CALCULATION
# =====================================================================
def compute_sr_matrix(raw, universe_config, is_stock_mode=False):
    """
    Computes algorithmic Support & Resistance levels, range positioning,
    channel width, and actionable Buy/Sell signals across the universe.
    """
    if raw is None or raw.empty:
        return pd.DataFrame()

    fidelity_df = get_5y_fidelity_leaderboard()
    fidelity_map = {}
    if not fidelity_df.empty:
        for _, r in fidelity_df.iterrows():
            fidelity_map[r["Ticker"]] = {
                "Win_Rate": r.get("Success_Probability_Pct", 50.0),
                "Rating": r.get("SR_Fidelity_Rating", "⭐⭐⭐ Moderate"),
                "Trades": r.get("Historical_5Y_Trades", 0),
                "Profit_Factor": r.get("Profit_Factor", 1.0)
            }

    records = []
    for item in universe_config:
        t = item["ticker"]
        clean_sym = t.replace(".NS", "")
        
        # Extract ticker series
        sub = pd.DataFrame()
        if hasattr(raw.columns, "levels") and len(raw.columns.levels) > 1:
            for cand in [t, clean_sym, f"{clean_sym}.NS"]:
                if cand in raw.columns.levels[0]:
                    sub = raw[cand].dropna(subset=["Close"]).copy()
                    break
        elif "Close" in raw.columns:
            sub = raw.dropna(subset=["Close"]).copy()
            
        if sub.empty or len(sub) < 30:
            continue

        c = sub["Close"].dropna()
        h = sub["High"] if "High" in sub.columns else c
        l = sub["Low"] if "Low" in sub.columns else c
        v = sub["Volume"].fillna(0) if "Volume" in sub.columns else pd.Series(0, index=sub.index)
        cmp_val = float(c.iloc[-1])

        # 1. ATR (14D)
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        atr_series = tr.rolling(14).mean()
        atr_val = float(atr_series.iloc[-1]) if not np.isnan(atr_series.iloc[-1]) else cmp_val * 0.02

        # 2. RSI (14D)
        delta = c.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi_series = 100 - (100 / (1 + rs))
        rsi_val = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50.0

        # 3. Bollinger Bands (20, 2)
        ma20 = c.rolling(20).mean()
        std20 = c.rolling(20).std().fillna(0.01)
        bb_upper = float((ma20 + 2 * std20).iloc[-1])
        bb_lower = float((ma20 - 2 * std20).iloc[-1])

        # 4. Moving Averages
        d50 = float(c.rolling(50, min_periods=1).mean().iloc[-1])
        d200 = float(c.rolling(200, min_periods=1).mean().iloc[-1])

        # 5. Algorithmic S/R Levels
        roll_30_low = float(l.iloc[-min(30, len(l)):].min())
        roll_100_low = float(l.iloc[-min(100, len(l)):].min())
        roll_30_high = float(h.iloc[-min(30, len(h)):].max())
        roll_100_high = float(h.iloc[-min(100, len(h)):].max())

        s1 = round(max(roll_30_low, bb_lower), 2)
        s2 = round(min(roll_100_low, d200 * 0.98 if d200 > 0 else roll_100_low), 2)
        r1 = round(min(roll_30_high, bb_upper), 2)
        r2 = round(max(roll_100_high, d50 * 1.05), 2)

        if s1 >= r1:
            r1 = round(s1 + 2.5 * atr_val, 2)
        midline = round((s1 + r1) / 2.0, 2)

        # 6. Distances & Range Positioning
        dist_s1_pct = round(((cmp_val - s1) / cmp_val) * 100.0, 2)
        dist_r1_pct = round(((r1 - cmp_val) / cmp_val) * 100.0, 2)
        range_span = max(0.01, r1 - s1)
        range_pos_pct = round(max(0.0, min(100.0, ((cmp_val - s1) / range_span) * 100.0)), 1)
        range_width_pct = round((range_span / s1) * 100.0, 2)

        # 7. ADX & Choppiness (Regime Filter)
        plus_dm = h.diff().clip(lower=0)
        minus_dm = (-l.diff()).clip(lower=0)
        tr14 = tr.rolling(14).sum().replace(0, np.nan)
        plus_di = 100 * (plus_dm.rolling(14).sum() / tr14)
        minus_di = 100 * (minus_dm.rolling(14).sum() / tr14)
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
        adx_val = float(dx.rolling(14).mean().iloc[-1]) if not dx.dropna().empty else 20.0

        if adx_val < 22.0:
            regime = "🟢 Range-Bound (Mean-Reverting)"
        elif adx_val < 30.0:
            regime = "🟡 Channeling / Mild Trend"
        else:
            regime = "⚡ Strong Trend (Breakout Mode)"

        # 8. Volume Surge
        vol_latest = float(v.iloc[-1])
        vol_20d = float(v.rolling(20, min_periods=1).mean().iloc[-1])
        vol_surge = round(vol_latest / (vol_20d or 1.0), 2)

        # 9. Actionable Trading Signal Generation
        sl_val = round(max(0.01, s1 - 1.2 * atr_val), 2)
        tgt_val = round(max(midline, cmp_val + 2.0 * atr_val), 2)
        risk_val = max(0.01, cmp_val - sl_val)
        reward_val = max(0.01, tgt_val - cmp_val)
        rr_ratio = round(reward_val / risk_val, 2)

        if dist_s1_pct <= 2.0 and rsi_val <= 44.0 and adx_val < 32.0:
            action = "🟢 BUY AT SUPPORT"
            action_desc = f"Testing Support Zone ₹{s1:.2f}. Oversold bounce setup with {rr_ratio}R reward."
        elif dist_r1_pct <= 2.0 and rsi_val >= 64.0:
            action = "🔴 SELL AT RESISTANCE"
            action_desc = f"At Resistance Ceiling ₹{r1:.2f}. Overbought RSI ({rsi_val:.1f}); take profit / trim."
        elif cmp_val > r1 and vol_surge >= 1.3:
            action = "🚀 BREAKOUT RUNNER"
            action_desc = f"Clean breakout above ₹{r1:.2f} with {vol_surge}x volume surge."
        elif range_pos_pct <= 30.0:
            action = "🌱 ACCUMULATE (LOWER THIRD)"
            action_desc = f"Trading in bottom 30% of range. Accumulation zone."
        elif range_pos_pct >= 70.0:
            action = "⚠️ DISTRIBUTION (UPPER THIRD)"
            action_desc = f"Trading in upper 30% of range. Tighten trailing stops."
        else:
            action = "🟡 MID-RANGE CONSOLIDATION"
            action_desc = f"Equilibrium at ₹{cmp_val:.2f}. Mid-channel between S1 and R1."

        # Fetch 5Y Historical Fidelity
        fid_data = fidelity_map.get(clean_sym, {})
        win_rate_5y = fid_data.get("Win_Rate", 50.0)
        fid_rating = fid_data.get("Rating", "⭐⭐⭐ Moderate")
        hist_trades = fid_data.get("Trades", 0)

        records.append({
            "Ticker": clean_sym,
            "Name": item.get("name", clean_sym),
            "Category": item.get("category", "Core"),
            "CMP (₹)": round(cmp_val, 2),
            "Major Support S1 (₹)": s1,
            "Structural Support S2 (₹)": s2,
            "Major Resistance R1 (₹)": r1,
            "Structural High R2 (₹)": r2,
            "Range Midline (₹)": midline,
            "Dist from Support (%)": dist_s1_pct,
            "Dist from Resistance (%)": dist_r1_pct,
            "Range Position (%)": range_pos_pct,
            "Channel Width (%)": range_width_pct,
            "RSI (14D)": round(rsi_val, 1),
            "ADX (14D)": round(adx_val, 1),
            "Regime": regime,
            "Action Signal": action,
            "Action Description": action_desc,
            "Suggested SL (₹)": sl_val,
            "Suggested Target (₹)": tgt_val,
            "Risk:Reward": rr_ratio,
            "5Y S/R Win Rate (%)": win_rate_5y,
            "5Y Trades": hist_trades,
            "S/R Predictability Rating": fid_rating
        })

    res_df = pd.DataFrame(records)
    if not res_df.empty and "5Y S/R Win Rate (%)" in res_df.columns:
        # Default sort: Best picks on top (descending 5Y empirical success probability, then proximity to support)
        res_df = res_df.sort_values(
            by=["5Y S/R Win Rate (%)", "Range Position (%)"],
            ascending=[False, True]
        ).reset_index(drop=True)

    return res_df


# =====================================================================
# 2. 5-YEAR S/R FIDELITY LEADERBOARD LOADER
# =====================================================================
def get_5y_fidelity_leaderboard(asset_class=None):
    """
    Loads pre-computed 5-year empirical S/R bounce rankings.
    """
    if os.path.exists(SR_RANKINGS_CSV):
        try:
            df = pd.read_csv(SR_RANKINGS_CSV)
            if asset_class:
                df = df[df["Asset_Class"].str.lower() == asset_class.lower()]
            return df
        except Exception:
            pass
    return pd.DataFrame()


# =====================================================================
# 3. LIVE 5-YEAR DEEP TICKER BACKTEST RUNNER
# =====================================================================
def run_live_5y_ticker_backtest(ticker):
    """
    Downloads 5 years of daily data for a single asset and runs an exhaustive
    trade-by-trade backtest of Support bounces and Resistance rejections.
    """
    clean_sym = ticker.replace(".NS", "")
    full_sym = f"{clean_sym}.NS"

    try:
        raw = yf.download(full_sym, period="5y", progress=False)
        if raw.empty:
            return {"status": "error", "message": f"Historical data for {full_sym} not found."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

    if isinstance(raw.columns, pd.MultiIndex):
        df = raw.xs(full_sym, level=0, axis=1) if full_sym in raw.columns.levels[0] else raw.droplevel(1, axis=1)
    else:
        df = raw.copy()

    c = df["Close"].dropna()
    h = df["High"] if "High" in df.columns else c
    l = df["Low"] if "Low" in df.columns else c
    v = df["Volume"] if "Volume" in df.columns else pd.Series(0, index=df.index)

    if len(c) < 120:
        return {"status": "error", "message": "Insufficient data history (<120 days)."}

    # Compute Indicators
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()

    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    s1 = l.rolling(50).min()
    r1 = h.rolling(50).max()
    mid = (s1 + r1) / 2.0

    plus_dm = h.diff().clip(lower=0)
    minus_dm = (-l.diff()).clip(lower=0)
    tr14 = tr.rolling(14).sum()
    plus_di = 100 * (plus_dm.rolling(14).sum() / tr14)
    minus_di = 100 * (minus_dm.rolling(14).sum() / tr14)
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx = dx.rolling(14).mean()

    trades = []
    last_exit_idx = 0

    for i in range(50, len(c) - 20):
        if i < last_exit_idx:
            continue
        cur_c = float(c.iloc[i])
        cur_s1 = float(s1.iloc[i])
        cur_r1 = float(r1.iloc[i])
        cur_atr = float(atr.iloc[i])
        cur_rsi = float(rsi.iloc[i])
        cur_adx = float(adx.iloc[i]) if not pd.isna(adx.iloc[i]) else 20.0
        cur_mid = float(mid.iloc[i])
        cur_date = c.index[i].strftime("%Y-%m-%d")

        range_span = cur_r1 - cur_s1
        if range_span <= 0:
            continue
        pos_in_range = (cur_c - cur_s1) / range_span

        # S/R Bounce Trigger: Lower 20% of range + RSI <= 42 + ADX < 32 (range bound)
        if pos_in_range <= 0.20 and cur_rsi <= 42 and cur_adx < 32:
            entry_p = cur_c
            sl_p = round(entry_p - 1.2 * cur_atr, 2)
            tgt_p = round(max(entry_p + 1.8 * cur_atr, cur_mid), 2)

            fwd_h = h.iloc[i+1 : i+21]
            fwd_l = l.iloc[i+1 : i+21]

            outcome = "EXPIRED"
            exit_p = float(c.iloc[i+20])
            exit_date = c.index[i+20].strftime("%Y-%m-%d")
            bars_held = 20

            for step, (high_val, low_val) in enumerate(zip(fwd_h, fwd_l)):
                if high_val >= tgt_p:
                    outcome = "WIN (Target Hit)"
                    exit_p = tgt_p
                    exit_date = c.index[i+1+step].strftime("%Y-%m-%d")
                    bars_held = step + 1
                    last_exit_idx = i + 1 + step + 2
                    break
                if low_val <= sl_p:
                    outcome = "LOSS (Stop Hit)"
                    exit_p = sl_p
                    exit_date = c.index[i+1+step].strftime("%Y-%m-%d")
                    bars_held = step + 1
                    last_exit_idx = i + 1 + step + 2
                    break

            if outcome == "EXPIRED":
                ret_pct = ((exit_p - entry_p) / entry_p) * 100.0
                outcome = "WIN (Positive Close)" if ret_pct > 0 else "LOSS (Negative Close)"
                last_exit_idx = i + 21

            pnl_pct = round(((exit_p - entry_p) / entry_p) * 100.0, 2)
            trades.append({
                "Entry_Date": cur_date,
                "Exit_Date": exit_date,
                "Entry_Price": round(entry_p, 2),
                "Support_Level": round(cur_s1, 2),
                "Exit_Price": round(exit_p, 2),
                "Stop_Loss": sl_p,
                "Target": tgt_p,
                "PnL_Pct": pnl_pct,
                "Outcome": outcome,
                "Bars_Held": bars_held,
                "RSI_At_Entry": round(cur_rsi, 1),
                "ADX_At_Entry": round(cur_adx, 1)
            })

    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        return {
            "status": "success",
            "ticker": clean_sym,
            "trades_count": 0,
            "win_rate_pct": 50.0,
            "avg_pnl_pct": 0.0,
            "profit_factor": 1.0,
            "trades_df": trades_df
        }

    wins = len(trades_df[trades_df["Outcome"].str.startswith("WIN")])
    total = len(trades_df)
    win_rate = round((wins / total) * 100.0, 1)
    avg_pnl = round(float(trades_df["PnL_Pct"].mean()), 2)
    pos_sum = trades_df[trades_df["PnL_Pct"] > 0]["PnL_Pct"].sum()
    neg_sum = abs(trades_df[trades_df["PnL_Pct"] < 0]["PnL_Pct"].sum())
    profit_factor = round(pos_sum / (neg_sum or 0.01), 2)

    return {
        "status": "success",
        "ticker": clean_sym,
        "trades_count": total,
        "wins_count": wins,
        "losses_count": total - wins,
        "win_rate_pct": win_rate,
        "avg_pnl_pct": avg_pnl,
        "profit_factor": profit_factor,
        "trades_df": trades_df
    }


# =====================================================================
# 4. COMPREHENSIVE MULTI-FACTOR TECHNICAL & FUNDAMENTAL INSPECTOR
# =====================================================================
def get_asset_comprehensive_profile(raw_row):
    """
    Builds a structured dictionary of all 34 technical, quantitative, and
    fundamental parameters for a given row from df_all.
    """
    if raw_row is None:
        return {}
    if hasattr(raw_row, "empty") and raw_row.empty:
        return {}

    r = raw_row.iloc[0] if isinstance(raw_row, pd.DataFrame) else raw_row

    return {
        "Ticker": r.get("Ticker", ""),
        "Name": r.get("Name", ""),
        "Category": r.get("Category", ""),
        "CMP": float(r.get("CMP (₹)", 0.0)),
        "20_DMA": float(r.get("20 DMA (₹)", 0.0)),
        "50_DMA": float(r.get("50 DMA (₹)", 0.0)),
        "100_DMA": float(r.get("100 DMA (₹)", 0.0)),
        "200_DMA": float(r.get("200 DMA (₹)", 0.0)),
        "Dist_200DMA_Pct": float(r.get("Dist 200DMA %", 0.0)),
        "52W_High": float(r.get("52W High (₹)", 0.0)),
        "52W_Low": float(r.get("52W Low (₹)", 0.0)),
        "52W_Range_Pct": float(r.get("52W Range %", 50.0)),
        "RSI_14D": float(r.get("RSI (14D)", 50.0)),
        "RSI_Delta": float(r.get("RSI Delta (1D)", 0.0)),
        "Reversal_Status": r.get("Reversal Status", "Normal"),
        "Bollinger_Upper": float(r.get("Bollinger Upper (₹)", 0.0)),
        "Bollinger_Lower": float(r.get("Bollinger Lower (₹)", 0.0)),
        "Bollinger_B": float(r.get("Bollinger %B", 0.5)),
        "MACD_Line": float(r.get("MACD Line", 0.0)),
        "MACD_Signal": float(r.get("MACD Signal", 0.0)),
        "MACD_Hist": float(r.get("MACD Hist", 0.0)),
        "MACD_Status": r.get("MACD Status", "Neutral"),
        "Stochastic_K": float(r.get("Stoch %K", 50.0)),
        "Stochastic_D": float(r.get("Stoch %D", 50.0)),
        "ROC_21D": float(r.get("21D Momentum ROC %", 0.0)),
        "ROC_63D": float(r.get("63D Momentum ROC %", 0.0)),
        "Hist_Vol": float(r.get("20D Hist Vol %", 20.0)),
        "VWAP": float(r.get("VWAP (₹)", 0.0)),
        "VWAP_Dist_Pct": float(r.get("VWAP Dist %", 0.0)),
        "Volume_Surge_Ratio": float(r.get("Volume Surge Ratio", 1.0)),
        "ATR_14D": float(r.get("14D ATR (₹)", 0.0)),
        "Dividend_Yield_Pct": float(r.get("Dividend Yield %", 0.0)),
        "Dividend_Status": r.get("Dividend Status", "None"),
        "Expense_Ratio": float(r.get("Expense Ratio %", 0.0)) if pd.notna(r.get("Expense Ratio %")) else None,
        "Composite_Buy_Score": float(r.get("Composite Buy Score", 50.0)),
        "Composite_Sell_Score": float(r.get("Composite Sell Score", 50.0)),
        "AI_Buy_Confidence": float(r.get("AI_Buy_Confidence", 50.0)),
        "AI_Sell_Confidence": float(r.get("AI_Sell_Confidence", 50.0))
    }


def get_34_parameter_profile(raw_data, ticker, is_stock_mode=True):
    """Retrieves 34-parameter profile for a specific ticker."""
    try:
        from strategy_engine import evaluate_market_metrics
        from universe_manager import get_active_universe
        stk_u, etf_u = get_active_universe()
        u = stk_u if is_stock_mode else etf_u
        clean_t = str(ticker).replace(".NS", "").strip()
        matched = [item for item in u if item.get("ticker", "").replace(".NS", "").strip() == clean_t]
        if matched and raw_data is not None and not raw_data.empty:
            m_df, _ = evaluate_market_metrics(raw_data, matched, is_stock_mode=is_stock_mode)
            if not m_df.empty:
                return get_asset_comprehensive_profile(m_df.iloc[0])
    except Exception as e:
        logger.error(f"Error building 34-parameter profile for {ticker}: {e}")
    return {}


# =====================================================================
# 5. S/R MATRIX VISUAL STYLER (BUY IN GREEN, SELL/EXIT IN RED)
# =====================================================================
def style_sr_matrix_dataframe(df):
    """
    Applies custom visual styling to S/R Matrix:
    - Favourable / Buy Indicating Values -> Soft Green (#d4edda background, #155724 text, bold)
      * Action Signal: BUY AT SUPPORT, ACCUMULATE (LOWER THIRD)
      * Range Position (%): <= 30% (Near Support)
      * Dist from Support (%): <= 2.5%
      * Suggested Target (₹) / Exit Range (Green profit objective)
      * 5Y S/R Win Rate (%): >= 60% (High fidelity)
    - Exit / Sell Indicating Values -> Soft Red (#f8d7da background, #721c24 text, bold)
      * Action Signal: SELL AT RESISTANCE, DISTRIBUTION (UPPER THIRD)
      * Range Position (%): >= 70% (Near Resistance)
      * Dist from Resistance (%): <= 2.5%
      * Suggested SL (₹): Stop loss risk boundary
      * RSI (14D): >= 65
    - Breakout Runner -> Soft Purple / Blue (#e0e7ff, #3730a3)
    """
    styles = pd.DataFrame("", index=df.index, columns=df.columns)

    for idx, r in df.iterrows():
        # 1. Action Signal
        sig = str(r.get("Action Signal", ""))
        if "BUY" in sig or "ACCUMULATE" in sig:
            styles.loc[idx, "Action Signal"] = "background-color: #d4edda; color: #155724; font-weight: bold;"
        elif "SELL" in sig or "DISTRIBUTION" in sig:
            styles.loc[idx, "Action Signal"] = "background-color: #f8d7da; color: #721c24; font-weight: bold;"
        elif "BREAKOUT" in sig:
            styles.loc[idx, "Action Signal"] = "background-color: #e0e7ff; color: #3730a3; font-weight: bold;"
        elif "MID-RANGE" in sig:
            styles.loc[idx, "Action Signal"] = "background-color: #fef9c3; color: #854d0e; font-weight: 500;"

        # 2. Range Position (%) - Favourable Buy Zone (<=30%) in Green, Exit Zone (>=70%) in Red
        try:
            pos = float(r.get("Range Position (%)", 50.0))
            if pos <= 30.0:
                styles.loc[idx, "Range Position (%)"] = "background-color: #d4edda; color: #155724; font-weight: bold;"
            elif pos >= 70.0:
                styles.loc[idx, "Range Position (%)"] = "background-color: #f8d7da; color: #721c24; font-weight: bold;"
        except Exception:
            pass

        # 3. Distance from Support (%)
        try:
            dist_s = float(r.get("Dist from Support (%)", 50.0))
            if dist_s <= 2.5:
                styles.loc[idx, "Dist from Support (%)"] = "background-color: #d4edda; color: #155724; font-weight: bold;"
        except Exception:
            pass

        # 4. Distance from Resistance (%)
        try:
            dist_r = float(r.get("Dist from Resistance (%)", 50.0))
            if dist_r <= 2.5:
                styles.loc[idx, "Dist from Resistance (%)"] = "background-color: #f8d7da; color: #721c24; font-weight: bold;"
        except Exception:
            pass

        # 5. Suggested Target (Exit Profit Range) -> Green
        if "Suggested Target (₹)" in df.columns:
            styles.loc[idx, "Suggested Target (₹)"] = "background-color: #dcfce7; color: #166534; font-weight: bold;"

        # 6. Suggested SL (Risk Exit Boundary) -> Red
        if "Suggested SL (₹)" in df.columns:
            styles.loc[idx, "Suggested SL (₹)"] = "background-color: #fee2e2; color: #991b1b; font-weight: bold;"

        # 7. 5Y S/R Win Rate (%) -> Highlight High Probability >= 60% in Green
        try:
            wr = float(r.get("5Y S/R Win Rate (%)", 50.0))
            if wr >= 60.0:
                styles.loc[idx, "5Y S/R Win Rate (%)"] = "background-color: #dcfce7; color: #15803d; font-weight: bold;"
        except Exception:
            pass

        # 8. RSI (14D) - Favourable dip (<=38) Green, Stretched (>=65) Red
        try:
            rsi = float(r.get("RSI (14D)", 50.0))
            if rsi <= 38.0:
                styles.loc[idx, "RSI (14D)"] = "background-color: #d4edda; color: #155724; font-weight: bold;"
            elif rsi >= 65.0:
                styles.loc[idx, "RSI (14D)"] = "background-color: #f8d7da; color: #721c24; font-weight: bold;"
        except Exception:
            pass

    return styles


# =====================================================================
# 6. S/R PAPER TRADING EXECUTION CONNECTOR
# =====================================================================
def execute_sr_paper_trade(clean_sym, sr_row, budget=15000.0, username="Public_User", dispatch_telegram=False):
    """
    Executes an S/R Range Mean Reversion trade into the paper trading ledger (paper_trades.csv).
    Optionally dispatches a formatted alert to Telegram.
    Returns (success: bool, message: str)
    """
    trades_path = os.path.join(os.path.dirname(__file__), "data", "paper_trades.csv")
    audit_path = os.path.join(os.path.dirname(__file__), "data", "paper_audit_log.csv")

    existing_df = pd.DataFrame()
    if os.path.exists(trades_path) and os.path.getsize(trades_path) > 0:
        try:
            existing_df = pd.read_csv(trades_path)
        except Exception:
            existing_df = pd.DataFrame()

    # Check duplicate active trade
    if not existing_df.empty and "Status" in existing_df.columns:
        active_dups = existing_df[(existing_df["Ticker"] == clean_sym) & (existing_df["Status"] == "ACTIVE")]
        if not active_dups.empty:
            return False, f"Ticker {clean_sym} already has an active trade in the Paper Trading Ledger."

    cmp_val = float(sr_row.get("CMP (₹)", 0.0))
    if cmp_val <= 0:
        return False, f"Invalid CMP ₹{cmp_val:.2f} for {clean_sym}."

    sl_val = float(sr_row.get("Suggested SL (₹)", round(cmp_val * 0.95, 2)))
    tgt_val = float(sr_row.get("Suggested Target (₹)", round(cmp_val * 1.06, 2)))
    qty = max(1, int(budget // cmp_val))
    now_ist = datetime.datetime.now(IST)
    trade_id = f"V2_SR_{int(now_ist.timestamp())}_{clean_sym}"
    now_str = now_ist.strftime("%Y-%m-%d %H:%M:%S")

    cat = sr_row.get("Category", "Stock")
    s1_level = float(sr_row.get("Immediate Support S1 (₹)", sr_row.get("Major Support S1 (₹)", cmp_val * 0.97)))
    dist_s1 = ((cmp_val - s1_level) / s1_level * 100) if s1_level > 0 else 0.0
    near_supp = f"Yes (+{dist_s1:.1f}% from S1: ₹{s1_level:.1f})" if dist_s1 <= 3.5 else f"Above S1 (+{dist_s1:.1f}%)"
    action_sig = str(sr_row.get("Action Signal", "S1 Support Bounce"))
    win_rt = float(sr_row.get("5Y S/R Win Rate (%)", 50.0))
    rsi_v = float(sr_row.get("RSI (14D)", 50.0))
    tech_sc = float(sr_row.get("Technical Score", rsi_v))
    fund_sc = float(sr_row.get("Fundamental Score", win_rt))
    comp_sc = float(sr_row.get("Composite Buy Score", sr_row.get("Range Position (%)", 50.0)))
    trig_ind = str(sr_row.get("Trigger_Indicator", f"{action_sig} (5Y Win: {win_rt:.1f}%, RSI: {rsi_v:.1f})"))

    rec = {
        "Trade_ID": trade_id,
        "Username": username,
        "Ticker": clean_sym,
        "Category": cat,
        "Asset_Class": cat,
        "Trigger_Type": "SR_SUPPORT_BUY",
        "Trigger_Indicator": trig_ind,
        "Strategy_Preset": sr_row.get("Strategy_Preset", "S/R Range Mean Reversion"),
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
        "Technical_Score_At_Entry": round(tech_sc, 1),
        "Fundamental_Score_At_Entry": round(fund_sc, 1),
        "Composite_Score_At_Entry": round(comp_sc, 1),
        "Near_Support_Status": near_supp,
        "RSI_At_Entry": round(rsi_v, 1),
        "Empirical_Win_Rate_At_Entry": f"{win_rt:.1f}%",
        "Predictability_Rating": str(sr_row.get("S/R Predictability Rating", "Good")),
        "Market_Regime_At_Entry": str(sr_row.get("Regime", "🟢 Range-Bound"))
    }

    combined = pd.concat([existing_df, pd.DataFrame([rec])], ignore_index=True)
    os.makedirs(os.path.dirname(trades_path), exist_ok=True)
    combined.to_csv(trades_path, index=False)

    # Save audit log
    audit_rec = {
        "Timestamp_IST": now_str,
        "Trigger_Source": f"V2_SR_EXEC_{username}",
        "Preset": "S/R Range Mean Reversion",
        "Recommended_BUY": clean_sym,
        "Recommended_SELL": "None",
        "Execution_Status": f"🟢 Logged ({qty} Qty @ ₹{cmp_val:.2f})",
        "Reason_Summary": f"S/R Entry triggered. SL: ₹{sl_val:.2f}, Target: ₹{tgt_val:.2f}, 5Y Win Rate: {sr_row.get('5Y S/R Win Rate (%)', 50)}%."
    }
    audit_df = pd.DataFrame()
    if os.path.exists(audit_path) and os.path.getsize(audit_path) > 0:
        try:
            audit_df = pd.read_csv(audit_path)
        except Exception:
            audit_df = pd.DataFrame()
    combined_audit = pd.concat([audit_df, pd.DataFrame([audit_rec])], ignore_index=True)
    combined_audit.to_csv(audit_path, index=False)

    # Optional Telegram Dispatch
    tg_status_msg = ""
    if dispatch_telegram:
        try:
            from telegram_notifier import send_telegram_message, format_paper_trade_alert, get_telegram_config
            cfg = get_telegram_config()
            if cfg.get("is_configured"):
                tg_text = format_paper_trade_alert(rec, action_type="ENTRY")
                tg_res = send_telegram_message(tg_text)
                if tg_res.get("ok"):
                    tg_status_msg = f" [📲 Telegram Alert Sent (Msg ID: {tg_res.get('message_id', 0)})]"
                else:
                    tg_status_msg = f" [⚠️ Telegram Dispatch Failed: {tg_res.get('error', 'Unknown Error')}]"
            else:
                tg_status_msg = " [ℹ️ Telegram Skipped: Bot Token or Chat ID not configured]"
        except Exception as e:
            logger.warning(f"Telegram dispatch error during S/R trade execution: {e}")
            tg_status_msg = f" [⚠️ Telegram Exception: {e}]"

    return True, f"Successfully executed {clean_sym} ({qty} Qty @ ₹{cmp_val:.2f}) with SL ₹{sl_val:.2f} and Target ₹{tgt_val:.2f}!{tg_status_msg}"


def get_balanced_4asset_sr_picks(sr_stocks_df: pd.DataFrame, sr_etfs_df: pd.DataFrame) -> dict:
    """
    Selects a balanced 4-Asset Execution Tranche:
      - 2 Stocks: Top 2 stocks testing Support / Lower range with highest 5Y Empirical Win Rate.
      - 1 Equity ETF: Broad Indian Equity ETF testing Support / Lower range.
      - 1 Metal / Global ETF: Gold/Silver (Commodity) or International ETF testing Support.
    Evaluates conditional eligibility for Metal/Commodity assets (skip if overbought/high).
    """
    picks = {
        "stocks": [],
        "equity_etf": None,
        "metal_global_etf": None,
        "metal_eligible": True,
        "metal_skip_reason": ""
    }

    # 1. Top 2 Stocks
    if sr_stocks_df is not None and not sr_stocks_df.empty:
        stk_sorted = sr_stocks_df.copy()
        def _rank(sig):
            if "BUY" in str(sig): return 1
            if "ACCUMULATE" in str(sig): return 2
            return 3
        stk_sorted["_r"] = stk_sorted["Action Signal"].apply(_rank)
        stk_sorted = stk_sorted.sort_values(
            by=["_r", "5Y S/R Win Rate (%)", "Range Position (%)"],
            ascending=[True, False, True]
        ).drop(columns=["_r"]).reset_index(drop=True)
        picks["stocks"] = [stk_sorted.iloc[i].to_dict() for i in range(min(2, len(stk_sorted)))]

    # 2. 1 Equity ETF and 1 Metal / Global ETF
    if sr_etfs_df is not None and not sr_etfs_df.empty:
        etf_df = sr_etfs_df.copy()
        metal_global_cats = ["Commodity", "Precious Metals", "Metal", "International"]

        # Equity ETFs (Non-sectoral Broad market, Large, Mid, Small, Factor)
        equity_etfs = etf_df[~etf_df["Category"].isin(metal_global_cats)].copy()
        if not equity_etfs.empty:
            def _rank(sig):
                if "BUY" in str(sig): return 1
                if "ACCUMULATE" in str(sig): return 2
                return 3
            equity_etfs["_r"] = equity_etfs["Action Signal"].apply(_rank)
            equity_etfs = equity_etfs.sort_values(
                by=["_r", "5Y S/R Win Rate (%)", "Range Position (%)"],
                ascending=[True, False, True]
            ).drop(columns=["_r"]).reset_index(drop=True)
            picks["equity_etf"] = equity_etfs.iloc[0].to_dict()

        # Metal / Global ETFs (GOLD, SILVER, NASDAQ, S&P, HANGSENG)
        metal_etfs = etf_df[etf_df["Category"].isin(metal_global_cats)].copy()
        if not metal_etfs.empty:
            def _rank(sig):
                if "BUY" in str(sig): return 1
                if "ACCUMULATE" in str(sig): return 2
                return 3
            metal_etfs["_r"] = metal_etfs["Action Signal"].apply(_rank)
            metal_etfs = metal_etfs.sort_values(
                by=["_r", "5Y S/R Win Rate (%)", "Range Position (%)"],
                ascending=[True, False, True]
            ).drop(columns=["_r"]).reset_index(drop=True)

            top_metal = metal_etfs.iloc[0].to_dict()
            picks["metal_global_etf"] = top_metal

            # Check conditional eligibility (skip if overbought or high)
            rsi = float(top_metal.get("RSI (14D)", 50.0))
            range_pos = float(top_metal.get("Range Position (%)", 50.0))
            if rsi > 62.0:
                picks["metal_eligible"] = False
                picks["metal_skip_reason"] = f"RSI is {rsi:.1f} (> 62.0) - Metal / Global asset is at cyclical high. Buy skipped."
            elif range_pos > 60.0:
                picks["metal_eligible"] = False
                picks["metal_skip_reason"] = f"Range Position is {range_pos:.1f}% (> 60%) - Trading near R1 ceiling. Buy skipped."
            elif "SELL" in str(top_metal.get("Action Signal", "")):
                picks["metal_eligible"] = False
                picks["metal_skip_reason"] = f"Signal is {top_metal.get('Action Signal')}. Buy skipped."
            else:
                picks["metal_eligible"] = True
                picks["metal_skip_reason"] = "Eligible (Favourable dip near Support)."

    return picks

