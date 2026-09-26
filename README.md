# ⚡ AGY Quant Platform V2: Public Testbed Edition

The **V2 Public Testbed** is a completely self-contained, **zero-secret** edition of the AGY platform designed for public hosting on Streamlit Community Cloud, public GitHub repositories, or test VMs.

---

## 🎯 Key Differences Between V1 and V2

| Feature | V1 (Private Production) | V2 (Public Testbed) |
|---|---|---|
| **Google Sheets Sync** | Yes (Requires Service Account & URL) | ❌ **No Secrets** (Pure local CSV in `data/`) |
| **Telegram Notifications** | Yes (Requires Bot Token & Chat ID) | ❌ **Disabled** (Detailed console & file logs in `daemon_execution.log`) |
| **Public Hosting Safety** | ⚠️ Secrets must be protected | ✅ **100% Public-Safe** (Can be hosted in public GitHub repos) |
| **External Cron Automation** | Requires GitHub Secrets | ✅ **cron-job.org, Webhook, GitHub Actions, or Python scheduler** |
| **Universe & Math Models** | 52 Stocks + 35 ETFs | **Identical (52 Stocks + 35 ETFs)** |
| **Top 3 BUY / SELL Matrix** | All 5 Presets on Tab 1 | **Identical (All 5 Presets on Tab 1)** |
| **AI/ML Strategy Review & One-Click Tuning** | Yes | **Identical (Yes, tunes `runtime_config.json` via button)** |
| **Inbuilt Exit Engine** | Target, Stop, Trailing Stop, Square-off | **Identical (Logs exit reason, exit price & hold duration)** |
| **Multi-Regime KPI Matrix** | Tab 2 | **Yes (Sliced by Category & Entry Market Regime)** |
| **Dual Top/Bottom Scrollbars** | Included | **Yes (`render_top_scrollbar_sync` JavaScript)** |
| **Color-Coded Screener** | Included | **Yes (Top 5 BUY Green / Top 5 SELL Red per column)** |

---

## 📁 V2 File Structure

```text
v2/
├── app.py                      # Public Streamlit dashboard with dual scrollbars & tooltips
├── strategy_engine.py          # Indicators, universe, top 3 matrix, exit rules, RS spread
├── ml_optimizer.py             # Headless AI/RAG synthesis & one-click tuner
├── paper_trader_daemon.py      # Scheduled execution daemon (pure console logging)
├── cron_webhook.py             # Standalone HTTP POST / GET webhook server for cron-job.org
├── external_cron_job.py        # Standalone Python scheduler for external hosting
├── runtime_config.json         # Active tuned strategy parameters
├── requirements.txt            # Lightweight dependencies (no Google auth)
├── README_V2.md                # Documentation & deployment guide
└── .github/
    └── workflows/
        └── paper_trader_v2.yml # GitHub Actions cron without any secrets
```

---

## 🚀 How to Host Publicly on Streamlit Community Cloud (Free)

1. Create a public repository on GitHub (e.g. `your-username/agy-quant-v2`).
2. Copy all files from this `v2/` directory to your repository.
3. Go to [share.streamlit.io](https://share.streamlit.io) and log in with GitHub.
4. Click **New app**:
   - **Repository:** `your-username/agy-quant-v2`
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. Click **Deploy!**
6. That's it! Your testbed terminal is now live on the internet with **no secrets or API credentials to configure**.

---

## ⏰ External Cron Options (cron-job.org & Others)

### Option 1: https://cron-job.org/en/ via Direct App Query (Easiest & Free)
When your app is hosted on Streamlit Cloud (e.g. `https://my-quant-terminal.streamlit.app`):
1. Register free at [cron-job.org](https://cron-job.org/en/) and click **Create Cronjob**.
2. **Title:** `AGY 3PM Accumulation`
3. **URL:**
   ```text
   https://my-quant-terminal.streamlit.app/?cron_trigger=1&mode=PAPER_TRADE_3PM&token=agy_quant_secure_token_2026
   ```
4. **Schedule:** Monday to Friday at `15:00` (Timezone: `Asia/Kolkata`).
5. **Request Method:** `GET`
6. Click **Save**.

Repeat for other routines:
- **09:45 AM IST:** `.../?cron_trigger=1&mode=INTRADAY_ENTRY&token=agy_quant_secure_token_2026`
- **03:10 PM IST:** `.../?cron_trigger=1&mode=INTRADAY_SQUAREOFF&token=agy_quant_secure_token_2026`

---

### Option 2: https://cron-job.org/en/ via HTTP POST (`cron_webhook.py`)
If you host `cron_webhook.py` on Render (Free Web Service), Railway, Koyeb, or a VPS:
1. In [cron-job.org](https://cron-job.org/en/), create a new Cronjob.
2. **Request Method:** `POST`
3. **URL:** `https://your-webhook-service.onrender.com/trigger`
4. **Headers:**
   - `Content-Type`: `application/json`
5. **Request Body:**
   ```json
   {
     "mode": "PAPER_TRADE_3PM",
     "token": "agy_quant_secure_token_2026"
   }
   ```
6. **Schedule:** `15:00` Asia/Kolkata (Mon-Fri).

---

### Option 3: GitHub Actions (Completely Free)
The workflow file [`.github/workflows/paper_trader_v2.yml`](file:///c:/Users/epurntr/Downloads/Gravity/v2/.github/workflows/paper_trader_v2.yml) runs on GitHub's free runners:
- **09:45 AM IST (`15 4 * * 1-5`):** Intraday Entry (Top 3 Stocks + Top 3 ETFs)
- **03:00 PM IST (`30 9 * * 1-5`):** 3 PM Multi-Asset Accumulation & AI/RAG
- **03:10 PM IST (`40 9 * * 1-5`):** Intraday Auto-Squareoff

---

### Option 4: Standalone Python Scheduler (`external_cron_job.py`)
On any server or local computer:
```bash
python external_cron_job.py
```

---

## 🎨 Screener Depth & Indicator Directionality Guide

In Tab 1, each column has a tooltip (`?`) detailing what it measures and whether a high or low value is favorable:

| Indicator Column | Better for BUY (Highlighted Green) | Better for SELL (Highlighted Red) |
|---|---|---|
| **Composite Buy Score** | **LOWER** (Top 5 lowest = deep value / confluence) | **HIGHER** (Top 5 highest = overextension) |
| **Technical Score** | **LOWER** (Top 5 lowest = oversold multi-timeframe) | **HIGHER** (Top 5 highest = overbought) |
| **Fundamental Score** | **LOWER** (Top 5 lowest = highest liquidity, low friction) | **HIGHER** (Top 5 highest = low liquidity / friction) |
| **RSI (14D)** | **LOWER** (< 35 indicates capitulation dip) | **HIGHER** (> 65 indicates overbought exhaustion) |
| **Bollinger %B** | **LOWER** (< 0.15 indicates lower-band discount) | **HIGHER** (> 0.85 indicates upper-band tag) |
| **Dist VWAP %** | **LOWER / NEGATIVE** (Discount below volume weighted average) | **HIGHER / POSITIVE** (Premium above volume weighted average) |
| **Dist 20/50/100/200 DMA %**| **LOWER / NEGATIVE** (Deep institutional pullback) | **HIGHER / POSITIVE** (Extended above average) |
| **Dist 52W Low %** | **LOWER** (< 6% indicates structural base support) | **HIGHER** (> 40% indicates mature advance) |
| **Volume Surge Ratio** | **HIGHER** (> 1.5x confirms institutional accumulation) | N/A |
| **RS Spread 21D %** | **HIGHER** (Positive spread = outperforming Nifty 50) | **LOWER** (Negative spread = lagging benchmark) |
| **Dividend Yield %** | **HIGHER** (Highlighted in green; cash-flow income cushion & defensive value) | N/A |
| **Dividend Status** | **💰 High Yield (≥3.0%)** / **💵 Moderate (1-3%)** | Non-Dividend / Zero |
| **Falling Knife Guard** | **Reversal Hook (Safe)** | **Falling Knife (Wait)** |
| **Structural Guard / iNAV**| **Clean (<+0.35%) / Healthy (>200 DMA)** | **High Premium / Broken (<200 DMA)** |

---

## 📄 Downloadable Platform Guide (.docx)

A complete Microsoft Word (`.docx`) platform specification is bundled with V2:
- **Location:** `v2/AGY_Quant_Platform_V2_Guide.docx`
- **Zero External Dependencies:** Built using standard Python OpenXML packaging (`export_to_docx.py`), requiring no third-party libraries like `python-docx`.
- **In-App Download:** Click the **📥 Download V2 Guide (.docx)** button located directly in the Streamlit Sidebar or in Tab 5.

---

## 🧮 Preset Filter & Mathematical Logic

The platform features 5 specialized quantitative presets with distinct weight configurations:

1. **Intraday Preset:**
   - **Formula:** `30% Rank_RSI + 35% Rank_VolSurge + 20% Rank_BB + 15% Rank_VWAP`
   - **Risk Multipliers:** SL: $1.2 \times \text{ATR}$, Target: $2.0 \times \text{ATR}$.
   - **Exit:** Auto-squareoff at 03:10 PM IST daily.

2. **Swing / Positional Preset:**
   - **Formula:** `30% Rank_RSI + 25% Rank_200DMA + 20% Rank_BB + 15% Rank_VWAP + 10% Rank_Stoch`
   - **Risk Multipliers:** SL: $1.5 \times \text{ATR}$, Target: $3.0 \times \text{ATR}$.
   - **Exit:** Target, Stop, Trailing Stop (+3% profit triggers +0.5% lock), or Overbought RSI > 76.

3. **Long-Term Preset:**
   - **Formula:** `20% Rank_RSI + 35% Rank_200DMA + 15% Rank_DivYield + 15% Rank_BB + 15% Fundamental_Score`
   - **Risk Multipliers:** SL: $2.5 \times \text{ATR}$, Target: $5.0 \times \text{ATR}$.
   - **Exit:** Wide structural stops, multi-quarter accumulation.

4. **Default Preset:**
   - Balanced baseline: `35% Dist_200DMA + 30% RSI + 20% 52W_Low + 15% Expense_Ratio`.

5. **AI / RAG Hybrid Preset:**
   - Confluence synthesizer: blends statistical indicator ranking with multi-agent consensus and dynamic runtime tuning.

---

## 📊 Inbuilt Auto-Exit Engine & Multi-Regime Ledger

### Auto-Exit Criteria:
1. **Target Achieved (`TARGET_ACHIEVED`):** Triggered when CMP >= Volatility Target Price.
2. **Stop-Loss Hit (`STOP_LOSS_HIT`):** Triggered when CMP <= Dynamic ATR Stop-Loss.
3. **Trailing Stop Lock (`TRAILING_STOP_HIT`):** Once a trade achieves `+3.0%` profit, the stop-loss is raised to lock in at least `+0.5%` profit.
4. **Swing Overbought Exhaustion (`OVERBOUGHT_EXIT`):** For swing trades, if RSI(14) >= 76 and profit > +1.5%, profits are taken early before reversal.
5. **Intraday Auto-Squareoff (`INTRADAY_SQUAREOFF`):** Automatically triggered at 03:10 PM IST.

### Enriched Ledger Columns:
- `Trade_ID`, `Ticker`, `Asset_Class`, `Trigger_Type`, `Strategy_Preset`, `Status`
- `Entry_Price`, `Live_CMP`, `Executed_Qty`, `Stop_Loss`, `Target`
- `Execution_Timestamp`, `Exit_Timestamp`, `Exit_Price`, `Exit_Reason`, `Hold_Duration_Days`
- `PnL_Rs`, `PnL_Pct`, `Invested_Value`
- `Technical_Score_At_Entry`, `Fundamental_Score_At_Entry`, `RSI_At_Entry`, `Composite_Score_At_Entry`, `Market_Regime_At_Entry`

### Multi-Regime KPI Matrix:
Tab 2 slices all closed and active positions by **Strategy Preset** and **Market Regime at Entry** (`🟢 Strong Bull Market`, `🔴 Bear Market / Correction`, `🟡 Sideways / Consolidation`), reporting:
- Win Rate %
- Profit Factor
- Net Realized PnL (₹) & Unrealized MTM (₹)
- Average Holding Duration (Days)

---

## 🎛️ Parameter & Weights Studio (GUI Sliders, Auto-Tuning & Monthly Evolution)

Tab 6 provides an interactive testbed studio allowing real-time parameter tuning directly in the GUI:

1. **Interactive Sliders (0% - 100%):**
   - Fine-tune quantitative factor weights across **Default, Long-Term, Swing / Positional, Intraday, and AI / RAG** presets without modifying source code.
2. **Dynamic Risk Multipliers:**
   - Calibrate Intraday, Swing, and Long-Term SL/Target ATR multipliers, trailing stop trigger gains, guaranteed profit locks, and overbought/oversold RSI thresholds.
3. **Execution Schedule & Weekday Guard:**
   - `weekdays_only`: Safely bypasses Saturday and Sunday cron executions to prevent weekend drift.
4. **All Parameters & Directionality Matrix:**
   - 34-parameter reference table indicating whether **higher or lower** values are better for BUY vs SELL, along with intended market impacts.
5. **AI/RAG Empirical Review & One-Click Tuning:**
   - Analyzes paper ledger trade distributions and suggests calibrated parameter adjustments.
   - **"⚡ One-Click Apply All AI/RAG Recommendations"** instantly updates `runtime_config.json`.
6. **Month-over-Month Performance Comparison:**
   - Correlates monthly Win Rate %, Profit Factor, and Net PnL (₹) with parameter tuning frequencies to audit algorithmic evolution over time.

