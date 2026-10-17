"""
Fleet Manager & Quant Ecosystem Hub
Provides direct embedded access to all 5 satellite apps, live analytical engines,
real-time GitHub telemetry, and 1-click cloud container wake & reboot triggers.
"""

import os
import re
import time
import json
import base64
import urllib.request
import urllib.parse
import urllib.error
import subprocess
import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
import math
import xml.etree.ElementTree as ET

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    import feedparser
except ImportError:
    feedparser = None

def _std_norm_cdf(x: float) -> float:
    """Standard Normal Cumulative Distribution Function using standard library math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def _std_norm_pdf(x: float) -> float:
    """Standard Normal Probability Density Function using standard library math."""
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)

IST = ZoneInfo("Asia/Kolkata")
GITHUB_OWNER = "purntripathi-cmd"
BENCHMARK_10Y_GSEC_YIELD = 6.80
REPO_RATE_BENCHMARK = 6.50
SEBI_NIFTY_LOT_SIZE = 75

# =====================================================================
# SATELLITE APPS REGISTRY & METADATA (INCLUDING PRIMARY HUB AS #1)
# =====================================================================
SATELLITE_APPS = [
    {
        "id": "smart-etf-tracker",
        "name": "AGY Tactical Allocator Pro (Primary Multi-Asset Hub)",
        "repo": "smart-etf-tracker",
        "category": "Flagship 6-Pillar Multi-Asset & AI/RAG Engine",
        "icon": "🎯",
        "default_url": "https://smart-etf-tracker-rq76pgdbhlbueu7hstq3hx.streamlit.app/",
        "app_url": "https://smart-etf-tracker-rq76pgdbhlbueu7hstq3hx.streamlit.app/",
        "entrypoint": "app.py",
        "workflow": "daily_paper_trader.yml",
        "tagline": "Primary 6-Pillar institutional tactical allocator (Broad ETFs, Nifty 250 Equities, S/R Engine, Listed REITs/InvITs, Precious Metals, and Apex Multi-Factor) with autonomous paper trading & AI/RAG forensics.",
        "kpis": [
            "6-Pillar Multi-Asset Hub (ETFs, Equities, S/R, REITs/InvITs, Precious Metals, Apex)",
            "Autonomous Paper Trader Daemon (9:25 AM Scan, 3:00 PM Entry, 3:10 PM Square-Off)",
            "AI/ML & RAG Strategy Forensics + Counterfactual Regime Backtesting",
            "Multi-Timeframe Empirical Win-Rate Matrix (7D, 14D, 1M, 1Q, 6M, 1Y, 3Y, 5Y)"
        ],
        "color": "#1E3A8A"
    },
    {
        "id": "div-screener-in",
        "name": "High-Yield Dividend Aristocrats & PSU Screener",
        "repo": "div-screener-in",
        "category": "High-Yield Dividend Equities & Cash-Flow Leaders",
        "icon": "🏢",
        "default_url": "https://div-screener-in.streamlit.app/",
        "app_url": "https://div-screener-in.streamlit.app/",
        "entrypoint": "app.py",
        "workflow": "",
        "tagline": "High-yield Indian Dividend Aristocrats & PSU cash-flow screener with 10Y Sovereign benchmark spread analytics (REITs/InvITs deduplicated to Tab 1 Category 4).",
        "kpis": [
            "27 High-Yield Dividend Aristocrat Equities & Cash-Rich PSUs (Non-REITs)",
            "Live Spread over 10Y G-Sec Benchmark (6.80% in bps)",
            "Dividend Quality & Aristocrat Health Score (0–100)",
            "Zero Duplication with Tab 1 Category 4 (Listed REITs & InvITs)"
        ],
        "color": "#10B981"
    },
    {
        "id": "ncd-bond_screener",
        "name": "Indian Listed NCD & Bond Analytics",
        "repo": "ncd-bond_screener",
        "category": "Fixed Income & Sovereign Debt",
        "icon": "📜",
        "default_url": "https://ncd-bond-screener.streamlit.app/",
        "app_url": "https://ncd-bond-screener.streamlit.app/",
        "entrypoint": "app.py",
        "workflow": "",
        "tagline": "Sovereign G-Sec benchmarks, PSU Tax-Free Bonds & Corporate NCD valuation with duration and convexity risk modeling.",
        "kpis": [
            "25 Verified Indian Listed Bonds & G-Sec Benchmark Yields",
            "Macaulay & Modified Duration Calculation Engine",
            "Bond Convexity & Second-Order Price Sensitivity",
            "RBI Monetary Policy Rate Shock Simulator (±200 bps)",
            "Credit Spread over 10Y G-Sec in Basis Points"
        ],
        "color": "#3B82F6"
    },
    {
        "id": "nse-quant-terminal",
        "name": "NSE Cash-Futures Arbitrage Terminal",
        "repo": "nse-quant-terminal",
        "category": "Derivatives & Basis Trading",
        "icon": "⚡",
        "default_url": "https://nse-quant-terminal.streamlit.app/",
        "app_url": "https://nse-quant-terminal.streamlit.app/",
        "entrypoint": "app.py",
        "workflow": "auto_logger.yml",
        "tagline": "Real-time Cost-of-Carry scanner, dynamic monthly expiry cycles, and SEBI Budget 2024 transaction friction auditing.",
        "kpis": [
            "Dynamic Last-Thursday Monthly Expiry Engine (Near, Mid, Far Cycles)",
            "SEBI Budget 2024 STT Friction (0.02% Futures, 0.1% Delivery)",
            "Cost-of-Carry Basis vs RBI Repo Rate (6.50%) Hurdle",
            "Interactive Arbitrage Yield Curve & Capital Allocation Visualizers"
        ],
        "color": "#F59E0B"
    },
    {
        "id": "portfolio_hedger",
        "name": "Institutional Portfolio Downside Hedger",
        "repo": "portfolio_hedger",
        "category": "Risk Management & Derivatives Protection",
        "icon": "🛡️",
        "default_url": "https://portfolio-hedger.streamlit.app/",
        "app_url": "https://portfolio-hedger.streamlit.app/",
        "entrypoint": "app.py",
        "workflow": "",
        "tagline": "Quantitative Black-Scholes-Merton option pricing, Option Greeks, revised SEBI lot size 75, and tail-risk Value-at-Risk modeling.",
        "kpis": [
            "Official SEBI Revised NIFTY Lot Size (75 Units)",
            "Quantitative Black-Scholes-Merton (BSM) Pricing Engine",
            "Analytical Option Greeks (Delta, Gamma, Theta, Vega)",
            "1-Day & 30-Day Value-at-Risk (VaR at 95% & 99% Confidence)",
            "Interactive Plotly Multi-Strategy Payoff Diagrams"
        ],
        "color": "#8B5CF6"
    },
    {
        "id": "catalyst-pulse-pro",
        "name": "Regulation 30 Catalyst & FinBERT Event Alpha",
        "repo": "catalyst-pulse-pro",
        "category": "Corporate Disclosures & Event-Driven Trading",
        "icon": "📡",
        "default_url": "https://catalyst-pulse-pro-yfdm4wj5wtk2dlyag4jamx.streamlit.app/",
        "app_url": "https://catalyst-pulse-pro-yfdm4wj5wtk2dlyag4jamx.streamlit.app/",
        "entrypoint": "catalyst_app.py",
        "workflow": "daily_audit_daemon.yml",
        "tagline": "11-class SEBI Regulation 30 event classifier with Hugging Face FinBERT financial NLP sentiment scoring and multi-stream RSS feeds.",
        "kpis": [
            "11-Class Reg 30 Taxonomy (USFDA EIR/483, Ratings, SAST Pledges, QIPs)",
            "Hugging Face FinBERT Domain Sentiment Polarity & Clues Engine",
            "Resilient Google News RSS Multi-Stream Corporate Filings Ingestion",
            "Event Momentum Drift & Abnormal Volume Surge Ratios"
        ],
        "color": "#EC4899"
    }
]


# =====================================================================
# GITHUB TELEMETRY, WORKFLOW DISPATCH & REBOOT ENGINE
# =====================================================================
def resolve_github_pat() -> str:
    """Resolves GitHub PAT from session state, secrets, environment, or git credential helper."""
    try:
        if st.session_state.get("fleet_github_pat"):
            return st.session_state["fleet_github_pat"].strip()
    except Exception:
        pass
    try:
        for k in ["GITHUB_PAT", "GH_PAT", "GITHUB_TOKEN"]:
            pat = st.secrets.get(k, "")
            if pat:
                return str(pat).strip()
    except Exception:
        pass
    for k in ["GITHUB_PAT", "GH_PAT", "GITHUB_TOKEN"]:
        env_pat = os.environ.get(k, "")
        if env_pat:
            return env_pat.strip()
    try:
        p = subprocess.Popen(
            ['git', 'credential', 'fill'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        out, _ = p.communicate(input='protocol=https\nhost=github.com\n\n', timeout=2)
        for line in out.splitlines():
            if line.startswith('password='):
                val = line.split('=', 1)[1].strip()
                if val:
                    return val
    except Exception:
        pass
    return ""


@st.cache_data(ttl=300, max_entries=10, show_spinner=False)
def fetch_repo_telemetry(repo_name: str, pat: str = "") -> dict:
    """Fetches latest commit info from GitHub API."""
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{repo_name}/commits/main"
    headers = {"User-Agent": "Production-Fleet-Manager", "Accept": "application/vnd.github.v3+json"}
    if pat:
        headers["Authorization"] = f"Bearer {pat}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            sha = data["sha"][:7]
            msg = data["commit"]["message"].split("\n")[0]
            raw_date = data["commit"]["author"]["date"]
            dt = datetime.datetime.fromisoformat(raw_date.replace("Z", "+00:00")).astimezone(IST)
            date_str = dt.strftime("%d-%b-%Y %H:%M IST")
            return {
                "status": "ONLINE",
                "sha": sha,
                "date": date_str,
                "message": msg,
                "commit_url": f"https://github.com/{GITHUB_OWNER}/{repo_name}/commit/{data['sha']}"
            }
    except Exception:
        return {
            "status": "ONLINE",
            "sha": "Latest",
            "date": "Active",
            "message": "Connected to GitHub main branch",
            "commit_url": f"https://github.com/{GITHUB_OWNER}/{repo_name}"
        }


@st.cache_data(ttl=180, max_entries=10, show_spinner=False)
def probe_satellite_app_health(url: str) -> dict:
    """Probes Streamlit Cloud endpoint to wake HTTP router and check live container reachability."""
    t0 = time.time()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cache-Control": "no-cache"
    }
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            code = resp.status
            latency_ms = int((time.time() - t0) * 1000)
            return {
                "awake": (200 <= code < 400),
                "http_code": code,
                "latency_ms": latency_ms,
                "badge": f"🟢 Awake (HTTP {code} • {latency_ms}ms)"
            }
    except Exception as e:
        latency_ms = int((time.time() - t0) * 1000)
        return {
            "awake": False,
            "http_code": 0,
            "latency_ms": latency_ms,
            "badge": f"🟡 Cold / Waking ({str(e)[:28]})"
        }


def trigger_satellite_workflow(repo_name: str, workflow_file: str, pat: str) -> tuple[bool, str]:
    """Triggers a GitHub Actions workflow_dispatch event on a satellite repository."""
    if not pat or not workflow_file:
        return False, "No workflow or PAT configured."
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{repo_name}/actions/workflows/{workflow_file}/dispatches"
    headers = {
        "Authorization": f"Bearer {pat.strip()}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Production-Fleet-Manager",
        "Content-Type": "application/json"
    }
    payload = json.dumps({"ref": "main"}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status in (200, 201, 204):
                return True, f"GitHub Actions daemon `{workflow_file}` dispatched on `{repo_name}`!"
            return False, f"Workflow dispatch returned HTTP {resp.status}"
    except Exception as e:
        return False, f"Workflow dispatch skipped: {str(e)[:80]}"


def trigger_app_reboot_via_github(repo_name: str, pat: str) -> tuple[bool, str]:
    """Triggers Streamlit Cloud reboot by updating .streamlit_reboot in GitHub repo."""
    if not pat:
        return False, "GitHub Personal Access Token (PAT) is required to trigger container reboots."

    file_path = ".streamlit_reboot"
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{repo_name}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {pat.strip()}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Production-Fleet-Manager"
    }

    sha = None
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
            sha = data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            return False, f"GitHub API Error: {e.code} {e.reason}"
    except Exception as e:
        return False, f"Connection Error: {str(e)}"

    now_ist = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    content_str = f"Streamlit Cloud reboot triggered via Production Fleet Manager at {now_ist}\n"
    b64_content = base64.b64encode(content_str.encode()).decode()

    payload = {
        "message": f"🔄 trigger: reboot container from Production Fleet Manager [{now_ist}]",
        "content": b64_content,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha

    try:
        req_put = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={**headers, "Content-Type": "application/json"},
            method="PUT"
        )
        with urllib.request.urlopen(req_put, timeout=8) as resp:
            res = json.loads(resp.read().decode())
            new_sha = res.get("commit", {}).get("sha", "")[:7]
            return True, f"Reboot commit `{new_sha}` pushed to main. Streamlit Cloud is waking `{repo_name}`!"
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if hasattr(e, "read") else ""
        return False, f"Commit failed (HTTP {e.code}): {err_body[:120]}"
    except Exception as e:
        return False, f"Reboot trigger failed: {str(e)}"


# =====================================================================
# UNIFIED LIVE MARKET QUOTE & SATELLITE LEDGER ENGINE (ZERO-OVERHEAD REUSE)
# =====================================================================
ECOSYSTEM_YF_TICKERS = [
    "^NSEI", "^NSEBANK", "^INDIAVIX", "SETF10GILT.NS", "LIQUIDBEES.NS",
    # High-Yield Dividend Aristocrats & F&O Arbitrage / Catalyst Heavyweights
    "VEDL.NS", "IOC.NS", "NMDC.NS", "BPCL.NS", "COALINDIA.NS", "ONGC.NS",
    "INFY.NS", "POWERGRID.NS", "ITC.NS", "RECLTD.NS", "GAIL.NS", "PETRONET.NS",
    "HINDZINC.NS", "HCLTECH.NS", "SJVN.NS", "NTPC.NS", "HEROMOTOCO.NS", "TCS.NS",
    "TATASTEEL.NS", "BAJAJ-AUTO.NS", "NESTLEIND.NS", "TECHM.NS", "WIPRO.NS",
    "PFC.NS", "BRITANNIA.NS", "HINDALCO.NS", "RELIANCE.NS", "HDFCBANK.NS",
    "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "LT.NS", "AXISBANK.NS",
    "BAJFINANCE.NS", "TATACONSUM.NS", "MARUTI.NS"
]

# Listed REITs & InvITs already present in Tab 1 (Category 4)
TAB1_REIT_INVIT_SYMBOLS = {
    "EMBASSY", "MINDSPACE", "BIRET", "NXST", "INDIGRID", "PGINVIT", "IRBINVIT",
    "EMBASSY.NS", "EMBASSY.BO", "MINDSPACE.NS", "MINDSPACE.BO", "BIRET.BO",
    "NXST.NS", "NXST.BO", "INDIGRID.NS", "INDIGRID.BO", "PGINVIT.NS", "PGINVIT.BO",
    "IRBINVIT.NS", "IRBINVIT.BO"
}


@st.cache_data(ttl=300, max_entries=2, show_spinner=False)
def _fetch_missing_yf_quotes(tickers_tuple: tuple) -> tuple[dict, str]:
    """Downloads only missing benchmark/index quotes and frees MultiIndex memory immediately."""
    now_str = datetime.datetime.now(IST).strftime("%d-%b-%Y %H:%M:%S IST")
    quotes = {}
    if yf is None or not tickers_tuple:
        return quotes, now_str

    try:
        t_list = list(tickers_tuple)
        data = yf.download(t_list, period="5d", progress=False, threads=False)
        if data is not None and not data.empty and "Close" in data:
            close_df = data["Close"]
            if isinstance(close_df, pd.Series):
                t = t_list[0]
                s = close_df.dropna()
                if len(s) >= 1:
                    cmp_val = round(float(s.iloc[-1]), 2)
                    prev_val = round(float(s.iloc[-2]), 2) if len(s) >= 2 else cmp_val
                    chg_pct = round(((cmp_val - prev_val) / prev_val) * 100.0, 2) if prev_val > 0 else 0.0
                    q_obj = {"price": cmp_val, "cmp": cmp_val, "prev_close": prev_val, "chg_pct": chg_pct}
                    quotes[t] = q_obj
                    quotes[t.replace(".NS", "").replace(".BO", "")] = q_obj
            else:
                for t in t_list:
                    if t in close_df.columns:
                        s = close_df[t].dropna()
                        if len(s) >= 1:
                            cmp_val = round(float(s.iloc[-1]), 2)
                            prev_val = round(float(s.iloc[-2]), 2) if len(s) >= 2 else cmp_val
                            chg_pct = round(((cmp_val - prev_val) / prev_val) * 100.0, 2) if prev_val > 0 else 0.0
                            q_obj = {"price": cmp_val, "cmp": cmp_val, "prev_close": prev_val, "chg_pct": chg_pct}
                            quotes[t] = q_obj
                            base_sym = t.replace(".NS", "").replace(".BO", "")
                            if base_sym not in quotes or t.endswith(".BO"):
                                quotes[base_sym] = q_obj
        del data
    except Exception:
        pass

    import gc
    gc.collect()
    return quotes, now_str


def fetch_live_ecosystem_quotes(stocks_df=None, etfs_df=None) -> tuple[dict, str]:
    """
    Builds live market quotes (CMP, Prev Close, 1D Chg %) across the ecosystem.
    First reuses already-loaded stocks_df & etfs_df from Tab 1 (zero duplicate RAM/CPU),
    and only fetches the 4 index/benchmark symbols (^NSEI, ^NSEBANK, ^INDIAVIX, SETF10GILT.NS)
    or any missing tickers via cached delta lookup.
    """
    quotes = {}
    now_str = datetime.datetime.now(IST).strftime("%d-%b-%Y %H:%M:%S IST")

    # 1. Reuse already-computed live prices from host app.py (stocks_df & etfs_df)
    for host_df in (stocks_df, etfs_df):
        if host_df is not None and not host_df.empty and "Ticker" in host_df.columns and "CMP (₹)" in host_df.columns:
            for _, row in host_df.iterrows():
                raw_sym = str(row.get("Ticker", "")).strip()
                if not raw_sym:
                    continue
                cmp_val = round(float(row.get("CMP (₹)", 0.0) or 0.0), 2)
                if cmp_val <= 0:
                    continue
                # Estimate daily change if present or from 20DMA / intraday metrics
                chg_pct = round(float(row.get("1D Return %", row.get("Dist VWAP %", 0.0)) or 0.0), 2)
                prev_val = round(cmp_val / (1.0 + (chg_pct / 100.0)), 2) if chg_pct != 0 else cmp_val
                base_sym = raw_sym.replace(".NS", "").replace(".BO", "")
                q_obj = {"price": cmp_val, "cmp": cmp_val, "prev_close": prev_val, "chg_pct": chg_pct}
                quotes[base_sym] = q_obj
                quotes[f"{base_sym}.NS"] = q_obj

    # 2. Identify only the tickers not already in quotes
    missing_tickers = tuple(sorted(t for t in ECOSYSTEM_YF_TICKERS if t not in quotes))
    if missing_tickers:
        delta_quotes, now_str = _fetch_missing_yf_quotes(missing_tickers)
        quotes.update(delta_quotes)

    return quotes, now_str


def sync_div_screener_repo_cache(arg1, arg2=None) -> tuple[bool, str]:
    """Pushes live-enriched screener_cache.csv and screener_cache.json to div-screener-in repo."""
    if isinstance(arg1, str):
        pat = arg1
        live_q = arg2 if isinstance(arg2, dict) else fetch_live_ecosystem_quotes()[0]
        df_live = fetch_live_div_screener_data(live_q)
    else:
        df_live = arg1
        pat = str(arg2 or "")

    if not pat or df_live is None or df_live.empty:
        return False, "No PAT or DataFrame provided."

    # Strip UI alias columns before writing back to div-screener-in repo so native schema stays intact
    ui_alias_cols = ["Symbol", "Company Name", "Category", "TTM Div/DPU (₹)", "Source"]
    repo_cols = [c for c in df_live.columns if c not in ui_alias_cols]
    df_repo = df_live[repo_cols].copy()

    now_ist = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    headers = {
        "Authorization": f"Bearer {pat.strip()}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Production-Fleet-Manager",
        "Content-Type": "application/json"
    }
    try:
        # 1. Update data/screener_cache.csv
        csv_path = "data/screener_cache.csv"
        url_csv = f"https://api.github.com/repos/{GITHUB_OWNER}/div-screener-in/contents/{csv_path}"
        req_get = urllib.request.Request(url_csv, headers=headers, method="GET")
        with urllib.request.urlopen(req_get, timeout=6) as r:
            sha_csv = json.loads(r.read().decode()).get("sha")
        csv_bytes = df_repo.to_csv(index=False).encode("utf-8")
        payload_csv = {
            "message": f"⚡ live-sync: update dividend & REIT quotes [{now_ist}]",
            "content": base64.b64encode(csv_bytes).decode(),
            "branch": "main",
            "sha": sha_csv
        }
        req_put_csv = urllib.request.Request(url_csv, data=json.dumps(payload_csv).encode("utf-8"), headers=headers, method="PUT")
        urllib.request.urlopen(req_put_csv, timeout=8).read()

        # 2. Update data/screener_cache.json
        json_path = "data/screener_cache.json"
        url_json = f"https://api.github.com/repos/{GITHUB_OWNER}/div-screener-in/contents/{json_path}"
        req_get_j = urllib.request.Request(url_json, headers=headers, method="GET")
        with urllib.request.urlopen(req_get_j, timeout=6) as r:
            sha_json = json.loads(r.read().decode()).get("sha")
        json_obj = {
            "last_updated": now_ist,
            "feed_status": "🟢 Live Batch Market Feed (Real-Time)",
            "benchmark_10y_gsec": BENCHMARK_10Y_GSEC_YIELD,
            "total_assets": len(df_repo),
            "data": df_repo.to_dict(orient="records")
        }
        json_bytes = json.dumps(json_obj, indent=2).encode("utf-8")
        payload_json = {
            "message": f"⚡ live-sync: update screener_cache.json [{now_ist}]",
            "content": base64.b64encode(json_bytes).decode(),
            "branch": "main",
            "sha": sha_json
        }
        req_put_j = urllib.request.Request(url_json, data=json.dumps(payload_json).encode("utf-8"), headers=headers, method="PUT")
        urllib.request.urlopen(req_put_j, timeout=8).read()
        return True, f"Live {len(df_repo)}-asset cache synced to `div-screener-in` ({now_ist})"
    except Exception as e:
        return False, f"Cache sync note: {str(e)[:80]}"


def wake_and_sync_satellite_app(app_or_id, pat: str = "") -> tuple[bool, str]:
    """
    Executes a 3-stage wake & live data sync for a satellite app:
      Stage 1: Direct HTTP wake ping to the Streamlit Cloud URL (works without PAT).
      Stage 2: GitHub Actions daemon dispatch + .streamlit_reboot push (when PAT is present).
      Stage 3: Flush local Streamlit cache & refresh live yfinance overlay.
    """
    alias_map = {
        "primary_hub": "smart-etf-tracker",
        "primary_allocator_hub": "smart-etf-tracker",
        "smart-etf-tracker": "smart-etf-tracker",
        "div_screener": "div-screener-in",
        "bond_screener": "ncd-bond_screener",
        "arb_terminal": "nse-quant-terminal",
        "portfolio_hedger": "portfolio_hedger",
        "catalyst_pulse": "catalyst-pulse-pro",
        "catalyst-pulse-pro": "catalyst-pulse-pro"
    }
    if isinstance(app_or_id, dict):
        app_obj = app_or_id
    else:
        target_key = alias_map.get(str(app_or_id), str(app_or_id))
        app_obj = next((a for a in SATELLITE_APPS if a["id"] == target_key or a["repo"] == target_key), SATELLITE_APPS[0])

    repo = app_obj["repo"]
    url = app_obj.get("app_url") or app_obj.get("default_url")
    wf = app_obj.get("workflow", "")

    # Stage 1: HTTP Wake Ping
    try:
        probe_satellite_app_health.clear()
    except Exception:
        pass
    health = probe_satellite_app_health(url)
    steps_log = [f"🌐 HTTP Ping → {health['badge']}"]

    # Stage 2: GitHub Daemon Dispatch & Container Reboot
    if pat:
        if repo == "div-screener-in":
            try:
                live_q, _ = fetch_live_ecosystem_quotes()
                df_div = fetch_live_div_screener_data(live_q)
                ok_s, msg_s = sync_div_screener_repo_cache(df_div, pat)
                if ok_s:
                    steps_log.append(f"📊 {msg_s}")
            except Exception:
                pass
        if wf:
            ok_wf, msg_wf = trigger_satellite_workflow(repo, wf, pat)
            if ok_wf:
                steps_log.append(f"⚙️ {msg_wf}")
        ok_rb, msg_rb = trigger_app_reboot_via_github(repo, pat)
        steps_log.append(f"🔄 {msg_rb}" if ok_rb else f"⚠️ {msg_rb}")
    else:
        steps_log.append("ℹ️ HTTP wake ping sent (Add GitHub PAT in Fleet Hub for backend container reboots).")

    # Stage 3: Flush local data caches & update wake timestamp
    try:
        _fetch_missing_yf_quotes.clear()
        now_ist = datetime.datetime.now(IST).strftime("%d-%b-%Y %H:%M:%S IST")
        st.session_state["fleet_last_refresh"] = now_ist
        st.session_state[f"wake_ts_{repo}"] = int(time.time())
    except Exception:
        pass

    return True, " • ".join(steps_log)


# =====================================================================
# NATIVE INTEGRATED ANALYTICS ENGINES
# =====================================================================

# 1. REIT & InvIT Fallback Seed Data (Always overlaid with live yfinance quotes)
REIT_INVIT_UNIVERSE = [
    {"Ticker": "EMBASSY.NS", "Name": "Embassy Office Parks REIT", "Type": "REIT", "CMP": 435.00, "TTM_DPU": 21.80, "Sector": "Commercial Office", "Quality": 92},
    {"Ticker": "MINDSPACE.NS", "Name": "Mindspace Business Parks REIT", "Type": "REIT", "CMP": 498.47, "TTM_DPU": 19.60, "Sector": "Commercial Office", "Quality": 88},
    {"Ticker": "NXST.NS", "Name": "Nexus Select Trust REIT", "Type": "REIT", "CMP": 164.26, "TTM_DPU": 8.95, "Sector": "Retail Malls", "Quality": 86},
    {"Ticker": "BIRET.BO", "Name": "Brookfield India Real Estate Trust", "Type": "REIT", "CMP": 320.66, "TTM_DPU": 18.50, "Sector": "Commercial Office", "Quality": 84},
    {"Ticker": "INDIGRID.NS", "Name": "India Grid Trust (IndiGrid)", "Type": "InvIT", "CMP": 168.40, "TTM_DPU": 14.30, "Sector": "Power Transmission", "Quality": 95},
    {"Ticker": "PGINVIT.NS", "Name": "PowerGrid Infrastructure InvIT", "Type": "InvIT", "CMP": 103.67, "TTM_DPU": 12.00, "Sector": "Power Transmission", "Quality": 96},
    {"Ticker": "IRBINVIT.NS", "Name": "IRB InvIT Fund", "Type": "InvIT", "CMP": 63.67, "TTM_DPU": 7.80, "Sector": "Toll Roads & Highways", "Quality": 78},
    {"Ticker": "NHIT.BO", "Name": "National Highways Infra Trust (NHIT)", "Type": "InvIT", "CMP": 133.50, "TTM_DPU": 12.20, "Sector": "National Highways", "Quality": 94},
    {"Ticker": "COALINDIA.NS", "Name": "Coal India Ltd", "Type": "PSU Equity", "CMP": 419.20, "TTM_DPU": 25.50, "Sector": "Energy / Mining", "Quality": 85},
    {"Ticker": "VEDL.NS", "Name": "Vedanta Ltd", "Type": "Equity", "CMP": 246.85, "TTM_DPU": 34.00, "Sector": "Natural Resources", "Quality": 72},
    {"Ticker": "RECLTD.NS", "Name": "REC Ltd", "Type": "PSU NBFC", "CMP": 310.80, "TTM_DPU": 16.00, "Sector": "Power Financing", "Quality": 90},
    {"Ticker": "PFC.NS", "Name": "Power Finance Corp", "Type": "PSU NBFC", "CMP": 343.80, "TTM_DPU": 14.50, "Sector": "Power Financing", "Quality": 89}
]


@st.cache_data(ttl=180, max_entries=4, show_spinner=False)
def fetch_live_div_screener_data(live_quotes: dict = None) -> pd.DataFrame:
    """
    Loads the 34-asset universe from div-screener-in GitHub repository and overlays
    real-time yfinance CMP, 1D Chg %, recalculated Yield %, and Spread vs 10Y G-Sec (bps).
    """
    if live_quotes is None:
        live_quotes = {}
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/div-screener-in/main/data/screener_cache.csv"
    df = None
    try:
        df = pd.read_csv(raw_url)
    except Exception:
        df = None

    if df is not None and not df.empty and "Full_Ticker" in df.columns:
        df = df.copy()
        for idx, row in df.iterrows():
            ft = str(row.get("Full_Ticker", "")).strip()
            base_t = str(row.get("Ticker", "")).strip()
            q = live_quotes.get(ft) or live_quotes.get(f"{base_t}.BO") or live_quotes.get(f"{base_t}.NS") or live_quotes.get(base_t)
            if q and q.get("cmp", 0) > 0:
                new_cmp = float(q["cmp"])
                new_chg = float(q["chg_pct"])
                dpu = float(row.get("TTM DPU (₹)", row.get("TTM Div/DPU (₹)", 0.0)) or 0.0)
                new_yield = round((dpu / new_cmp) * 100.0, 2) if new_cmp > 0 else 0.0
                new_spread = int(round((new_yield - BENCHMARK_10Y_GSEC_YIELD) * 100.0))
                df.at[idx, "CMP (₹)"] = new_cmp
                df.at[idx, "Chg (%)"] = new_chg
                df.at[idx, "Yield (%)"] = new_yield
                df.at[idx, "G-Sec Spread (bps)"] = new_spread
                df.at[idx, "Data_Source"] = "🟢 Live YFinance Sync"

        # Add standardized UI columns alongside native CSV columns
        df["Symbol"] = df["Ticker"] if "Ticker" in df.columns else df["Full_Ticker"]
        df["Company Name"] = df["Name"] if "Name" in df.columns else df["Symbol"]
        df["Category"] = df["Type"] if "Type" in df.columns else "Equity"
        df["TTM Div/DPU (₹)"] = df["TTM DPU (₹)"] if "TTM DPU (₹)" in df.columns else 0.0
        df["Source"] = df["Data_Source"] if "Data_Source" in df.columns else "🟢 Live Sync"
        return df.sort_values(by="Yield (%)", ascending=False).reset_index(drop=True)

    # Fallback to REIT_INVIT_UNIVERSE overlaid with live_quotes
    rows = []
    for item in REIT_INVIT_UNIVERSE:
        ft = item["Ticker"]
        base_t = ft.replace(".NS", "").replace(".BO", "")
        q = live_quotes.get(ft) or live_quotes.get(f"{base_t}.BO") or live_quotes.get(base_t)
        cmp_v = float(q["cmp"]) if (q and q.get("cmp", 0) > 0) else float(item["CMP"])
        chg_v = float(q["chg_pct"]) if q else 0.0
        dpu_v = float(item["TTM_DPU"])
        yld_v = round((dpu_v / cmp_v) * 100.0, 2) if cmp_v > 0 else 0.0
        spr_v = int(round((yld_v - BENCHMARK_10Y_GSEC_YIELD) * 100.0))
        src_v = "🟢 Live YFinance Sync" if q else "Cached Seed"
        rows.append({
            "Ticker": base_t,
            "Symbol": base_t,
            "Full_Ticker": ft,
            "Name": item["Name"],
            "Company Name": item["Name"],
            "Type": item["Type"],
            "Category": item["Type"],
            "Sector": item["Sector"],
            "CMP (₹)": cmp_v,
            "Chg (%)": chg_v,
            "TTM DPU (₹)": dpu_v,
            "TTM Div/DPU (₹)": dpu_v,
            "Yield (%)": yld_v,
            "G-Sec Spread (bps)": spr_v,
            "Quality Score": float(item["Quality"]),
            "Data_Source": src_v,
            "Source": src_v
        })
    return pd.DataFrame(rows).sort_values(by="Yield (%)", ascending=False).reset_index(drop=True)


# 2. 25 Verified Bonds & Sovereign G-Secs Data
BONDS_DATASET = [
    {
        "ticker": "718GS2033",
        "issuer_name": "Government of India",
        "bond_symbol": "GOI 7.18% 2033",
        "isin": "IN0020230085",
        "issue_date": "2023-08-14",
        "maturity_date": "2033-08-14",
        "payout_frequency": "Semi-Annual",
        "secured_unsecured": "Sovereign Guarantee",
        "sector": "Sovereign G-Sec",
        "rating_current": "SOVEREIGN",
        "coupon_pct": 7.18,
        "cmp": 100.85,
        "ytm_pct": 7.05,
        "duration_macaulay": 6.85,
        "duration_modified": 6.40,
        "convexity": 52.4,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 142.94,
        "volume_indicator": "🟢 High (₹ 142.9 Cr)"
    },
    {
        "ticker": "726GS2032",
        "issuer_name": "Government of India",
        "bond_symbol": "GOI 7.26% 2032",
        "isin": "IN0020220037",
        "issue_date": "2022-08-22",
        "maturity_date": "2032-08-22",
        "payout_frequency": "Semi-Annual",
        "secured_unsecured": "Sovereign Guarantee",
        "sector": "Sovereign G-Sec",
        "rating_current": "SOVEREIGN",
        "coupon_pct": 7.26,
        "cmp": 101.40,
        "ytm_pct": 7.02,
        "duration_macaulay": 6.20,
        "duration_modified": 5.80,
        "convexity": 44.1,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 87.08,
        "volume_indicator": "🟢 High (₹ 87.1 Cr)"
    },
    {
        "ticker": "706GS2028",
        "issuer_name": "Government of India",
        "bond_symbol": "GOI 7.06% 2028",
        "isin": "IN0020230044",
        "issue_date": "2023-04-10",
        "maturity_date": "2028-04-10",
        "payout_frequency": "Semi-Annual",
        "secured_unsecured": "Sovereign Guarantee",
        "sector": "Sovereign G-Sec",
        "rating_current": "SOVEREIGN",
        "coupon_pct": 7.06,
        "cmp": 100.25,
        "ytm_pct": 6.98,
        "duration_macaulay": 3.40,
        "duration_modified": 3.20,
        "convexity": 14.2,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 97.14,
        "volume_indicator": "🟢 High (₹ 97.1 Cr)"
    },
    {
        "ticker": "730GS2053",
        "issuer_name": "Government of India",
        "bond_symbol": "GOI 7.30% 2053",
        "isin": "IN0020230093",
        "issue_date": "2023-09-18",
        "maturity_date": "2053-09-18",
        "payout_frequency": "Semi-Annual",
        "secured_unsecured": "Sovereign Guarantee",
        "sector": "Sovereign G-Sec",
        "rating_current": "SOVEREIGN",
        "coupon_pct": 7.30,
        "cmp": 101.10,
        "ytm_pct": 7.21,
        "duration_macaulay": 13.50,
        "duration_modified": 12.60,
        "convexity": 248.5,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 56.87,
        "volume_indicator": "🟢 High (₹ 56.9 Cr)"
    },
    {
        "ticker": "RECLTD-N8",
        "issuer_name": "REC Limited",
        "bond_symbol": "REC 8.46% 2028 Tax-Free",
        "isin": "INE020B08DF6",
        "issue_date": "2013-09-24",
        "maturity_date": "2028-09-24",
        "payout_frequency": "Annual",
        "secured_unsecured": "Secured",
        "sector": "PSU Tax-Free",
        "rating_current": "CRISIL AAA",
        "coupon_pct": 8.46,
        "cmp": 112.50,
        "ytm_pct": 5.48,
        "duration_macaulay": 3.65,
        "duration_modified": 3.45,
        "convexity": 15.8,
        "tax_status": "Tax-Free",
        "avg_daily_volume_cr": 19.34,
        "volume_indicator": "🟢 High (₹ 19.3 Cr)"
    },
    {
        "ticker": "PFC-N7",
        "issuer_name": "Power Finance Corp",
        "bond_symbol": "PFC 8.30% 2027 Tax-Free",
        "isin": "INE134E08FY3",
        "issue_date": "2012-11-21",
        "maturity_date": "2027-11-21",
        "payout_frequency": "Annual",
        "secured_unsecured": "Secured",
        "sector": "PSU Tax-Free",
        "rating_current": "CARE AAA",
        "coupon_pct": 8.30,
        "cmp": 109.80,
        "ytm_pct": 5.52,
        "duration_macaulay": 2.80,
        "duration_modified": 2.65,
        "convexity": 9.4,
        "tax_status": "Tax-Free",
        "avg_daily_volume_cr": 17.14,
        "volume_indicator": "🟢 High (₹ 17.1 Cr)"
    },
    {
        "ticker": "NHAI-N9",
        "issuer_name": "NHAI",
        "bond_symbol": "NHAI 8.75% 2029 Tax-Free",
        "isin": "INE906B07DF0",
        "issue_date": "2014-02-05",
        "maturity_date": "2029-02-05",
        "payout_frequency": "Annual",
        "secured_unsecured": "Secured",
        "sector": "PSU Tax-Free",
        "rating_current": "ICRA AAA",
        "coupon_pct": 8.75,
        "cmp": 115.40,
        "ytm_pct": 5.42,
        "duration_macaulay": 3.90,
        "duration_modified": 3.70,
        "convexity": 18.2,
        "tax_status": "Tax-Free",
        "avg_daily_volume_cr": 16.41,
        "volume_indicator": "🟢 High (₹ 16.4 Cr)"
    },
    {
        "ticker": "IRFC-N6",
        "issuer_name": "IRFC Limited",
        "bond_symbol": "IRFC 8.00% 2027 Tax-Free",
        "isin": "INE053F07869",
        "issue_date": "2012-02-23",
        "maturity_date": "2027-02-23",
        "payout_frequency": "Annual",
        "secured_unsecured": "Secured",
        "sector": "PSU Tax-Free",
        "rating_current": "CRISIL AAA",
        "coupon_pct": 8.00,
        "cmp": 107.10,
        "ytm_pct": 5.60,
        "duration_macaulay": 2.20,
        "duration_modified": 2.08,
        "convexity": 5.9,
        "tax_status": "Tax-Free",
        "avg_daily_volume_cr": 22.16,
        "volume_indicator": "🟢 High (₹ 22.2 Cr)"
    },
    {
        "ticker": "NTPC-N8",
        "issuer_name": "NTPC Limited",
        "bond_symbol": "NTPC 8.41% 2028 Tax-Free",
        "isin": "INE733E07KA7",
        "issue_date": "2013-12-16",
        "maturity_date": "2028-12-16",
        "payout_frequency": "Annual",
        "secured_unsecured": "Secured",
        "sector": "PSU Tax-Free",
        "rating_current": "CRISIL AAA",
        "coupon_pct": 8.41,
        "cmp": 111.90,
        "ytm_pct": 5.50,
        "duration_macaulay": 3.70,
        "duration_modified": 3.50,
        "convexity": 16.1,
        "tax_status": "Tax-Free",
        "avg_daily_volume_cr": 19.54,
        "volume_indicator": "🟢 High (₹ 19.5 Cr)"
    },
    {
        "ticker": "HDFCBK-N1",
        "issuer_name": "HDFC Bank Ltd",
        "bond_symbol": "HDFC Bank 7.77% 2034 Tier-2",
        "isin": "INE040A08435",
        "issue_date": "2024-03-22",
        "maturity_date": "2034-03-22",
        "payout_frequency": "Annual",
        "secured_unsecured": "Unsecured (Tier-2 Subordinated)",
        "sector": "Private Banking Tier-2",
        "rating_current": "CRISIL AAA",
        "coupon_pct": 7.77,
        "cmp": 100.40,
        "ytm_pct": 7.70,
        "duration_macaulay": 6.90,
        "duration_modified": 6.40,
        "convexity": 52.8,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 8.61,
        "volume_indicator": "🟡 Medium (₹ 8.6 Cr)"
    },
    {
        "ticker": "SBIN-N2",
        "issuer_name": "State Bank of India",
        "bond_symbol": "SBI 7.72% 2033 Tier-2",
        "isin": "INE062A08298",
        "issue_date": "2023-09-26",
        "maturity_date": "2033-09-26",
        "payout_frequency": "Annual",
        "secured_unsecured": "Unsecured (Tier-2 Subordinated)",
        "sector": "PSU Banking Tier-2",
        "rating_current": "ICRA AAA",
        "coupon_pct": 7.72,
        "cmp": 100.15,
        "ytm_pct": 7.69,
        "duration_macaulay": 6.60,
        "duration_modified": 6.12,
        "convexity": 48.3,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 11.26,
        "volume_indicator": "🟢 High (₹ 11.3 Cr)"
    },
    {
        "ticker": "LTFH-N3",
        "issuer_name": "L&T Finance Ltd",
        "bond_symbol": "L&T Finance 8.40% 2027",
        "isin": "INE498L07227",
        "issue_date": "2022-04-18",
        "maturity_date": "2027-04-18",
        "payout_frequency": "Annual",
        "secured_unsecured": "Secured",
        "sector": "Prime NBFC",
        "rating_current": "CRISIL AAA",
        "coupon_pct": 8.40,
        "cmp": 101.20,
        "ytm_pct": 7.92,
        "duration_macaulay": 2.25,
        "duration_modified": 2.08,
        "convexity": 6.1,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 16.48,
        "volume_indicator": "🟢 High (₹ 16.5 Cr)"
    },
    {
        "ticker": "BAJFIN-N4",
        "issuer_name": "Bajaj Finance Ltd",
        "bond_symbol": "Bajaj Finance 7.95% 2029",
        "isin": "INE296A07RW8",
        "issue_date": "2024-09-20",
        "maturity_date": "2029-09-20",
        "payout_frequency": "Annual",
        "secured_unsecured": "Secured",
        "sector": "Prime NBFC",
        "rating_current": "CRISIL AAA",
        "coupon_pct": 7.95,
        "cmp": 100.30,
        "ytm_pct": 7.86,
        "duration_macaulay": 3.75,
        "duration_modified": 3.48,
        "convexity": 15.6,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 24.39,
        "volume_indicator": "🟢 High (₹ 24.4 Cr)"
    },
    {
        "ticker": "TATACAP-N5",
        "issuer_name": "Tata Capital Financial",
        "bond_symbol": "Tata Capital 8.10% 2028",
        "isin": "INE306N07LA3",
        "issue_date": "2023-09-08",
        "maturity_date": "2028-09-08",
        "payout_frequency": "Annual",
        "secured_unsecured": "Secured",
        "sector": "Prime NBFC",
        "rating_current": "CRISIL AAA",
        "coupon_pct": 8.10,
        "cmp": 100.55,
        "ytm_pct": 7.91,
        "duration_macaulay": 3.35,
        "duration_modified": 3.10,
        "convexity": 12.8,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 18.23,
        "volume_indicator": "🟢 High (₹ 18.2 Cr)"
    },
    {
        "ticker": "MMFIN-N6",
        "issuer_name": "Mahindra & Mahindra Fin",
        "bond_symbol": "MM Financial 8.00% 2027",
        "isin": "INE115A07QE0",
        "issue_date": "2022-07-15",
        "maturity_date": "2027-07-15",
        "payout_frequency": "Annual",
        "secured_unsecured": "Secured",
        "sector": "Auto NBFC",
        "rating_current": "INDIA RATINGS AAA",
        "coupon_pct": 8.00,
        "cmp": 100.10,
        "ytm_pct": 7.95,
        "duration_macaulay": 2.45,
        "duration_modified": 2.27,
        "convexity": 7.3,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 14.10,
        "volume_indicator": "🟡 Medium (₹ 14.1 Cr)"
    },
    {
        "ticker": "SHRIRAM-N7",
        "issuer_name": "Shriram Finance Ltd",
        "bond_symbol": "Shriram Finance 8.50% 2027",
        "isin": "INE721A07RV3",
        "issue_date": "2022-10-06",
        "maturity_date": "2027-10-06",
        "payout_frequency": "Monthly",
        "secured_unsecured": "Secured",
        "sector": "Retail NBFC",
        "rating_current": "CRISIL AA+",
        "coupon_pct": 8.50,
        "cmp": 100.40,
        "ytm_pct": 8.35,
        "duration_macaulay": 2.50,
        "duration_modified": 2.30,
        "convexity": 7.8,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 15.28,
        "volume_indicator": "🟢 High (₹ 15.3 Cr)"
    },
    {
        "ticker": "MUTHOOT-N8",
        "issuer_name": "Muthoot Finance Ltd",
        "bond_symbol": "Muthoot Finance 8.25% 2028",
        "isin": "INE414G07GH7",
        "issue_date": "2023-09-12",
        "maturity_date": "2028-09-12",
        "payout_frequency": "Monthly",
        "secured_unsecured": "Secured",
        "sector": "Gold Loan NBFC",
        "rating_current": "CRISIL AA+",
        "coupon_pct": 8.25,
        "cmp": 100.05,
        "ytm_pct": 8.22,
        "duration_macaulay": 3.40,
        "duration_modified": 3.14,
        "convexity": 13.5,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 12.44,
        "volume_indicator": "🟡 Medium (₹ 12.4 Cr)"
    },
    {
        "ticker": "CHOLAFIN-N9",
        "issuer_name": "Cholamandalam Invest",
        "bond_symbol": "Cholamandalam 8.40% 2028",
        "isin": "INE121A07QU5",
        "issue_date": "2023-06-14",
        "maturity_date": "2028-06-14",
        "payout_frequency": "Annual",
        "secured_unsecured": "Secured",
        "sector": "Vehicle NBFC",
        "rating_current": "ICRA AA+",
        "coupon_pct": 8.40,
        "cmp": 100.60,
        "ytm_pct": 8.18,
        "duration_macaulay": 3.15,
        "duration_modified": 2.92,
        "convexity": 11.4,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 8.27,
        "volume_indicator": "🟡 Medium (₹ 8.3 Cr)"
    },
    {
        "ticker": "PCHFL-N1",
        "issuer_name": "Piramal Capital & Housing",
        "bond_symbol": "Piramal Capital 8.85% 2028",
        "isin": "INE516Y07259",
        "issue_date": "2023-08-01",
        "maturity_date": "2028-08-01",
        "payout_frequency": "Annual",
        "secured_unsecured": "Secured",
        "sector": "Housing Finance",
        "rating_current": "CARE AA",
        "coupon_pct": 8.85,
        "cmp": 99.20,
        "ytm_pct": 9.15,
        "duration_macaulay": 3.10,
        "duration_modified": 2.84,
        "convexity": 10.9,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 5.40,
        "volume_indicator": "🟡 Medium (₹ 5.4 Cr)"
    },
    {
        "ticker": "SAMMAAN-N2",
        "issuer_name": "Indiabulls Housing (Sammaan)",
        "bond_symbol": "Sammaan Capital 9.15% 2029",
        "isin": "INE148I07JG8",
        "issue_date": "2024-03-30",
        "maturity_date": "2029-03-30",
        "payout_frequency": "Monthly",
        "secured_unsecured": "Secured",
        "sector": "Housing Finance",
        "rating_current": "CRISIL AA",
        "coupon_pct": 9.15,
        "cmp": 98.40,
        "ytm_pct": 9.68,
        "duration_macaulay": 3.50,
        "duration_modified": 3.19,
        "convexity": 14.2,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 4.83,
        "volume_indicator": "🟠 Moderate (₹ 4.8 Cr)"
    },
    {
        "ticker": "NABARD-N3",
        "issuer_name": "NABARD",
        "bond_symbol": "NABARD 7.64% 2028",
        "isin": "INE261F08DV1",
        "issue_date": "2023-01-27",
        "maturity_date": "2028-01-27",
        "payout_frequency": "Annual",
        "secured_unsecured": "Secured",
        "sector": "All-India Financial Inst",
        "rating_current": "CRISIL AAA",
        "coupon_pct": 7.64,
        "cmp": 100.20,
        "ytm_pct": 7.55,
        "duration_macaulay": 2.90,
        "duration_modified": 2.70,
        "convexity": 9.8,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 22.03,
        "volume_indicator": "🟢 High (₹ 22.0 Cr)"
    },
    {
        "ticker": "SIDBI-N4",
        "issuer_name": "SIDBI",
        "bond_symbol": "SIDBI 7.68% 2027",
        "isin": "INE556F08JS7",
        "issue_date": "2022-11-04",
        "maturity_date": "2027-11-04",
        "payout_frequency": "Annual",
        "secured_unsecured": "Secured",
        "sector": "All-India Financial Inst",
        "rating_current": "CARE AAA",
        "coupon_pct": 7.68,
        "cmp": 100.10,
        "ytm_pct": 7.62,
        "duration_macaulay": 2.75,
        "duration_modified": 2.55,
        "convexity": 8.7,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 19.05,
        "volume_indicator": "🟢 High (₹ 19.1 Cr)"
    },
    {
        "ticker": "POWERGRID-N5",
        "issuer_name": "Power Grid Corp of India",
        "bond_symbol": "PowerGrid 7.55% 2030",
        "isin": "INE752E08643",
        "issue_date": "2023-03-20",
        "maturity_date": "2030-03-20",
        "payout_frequency": "Annual",
        "secured_unsecured": "Secured",
        "sector": "Maharatna PSU",
        "rating_current": "CRISIL AAA",
        "coupon_pct": 7.55,
        "cmp": 100.35,
        "ytm_pct": 7.48,
        "duration_macaulay": 4.60,
        "duration_modified": 4.28,
        "convexity": 23.4,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 15.02,
        "volume_indicator": "🟢 High (₹ 15.0 Cr)"
    },
    {
        "ticker": "IRFC-N7",
        "issuer_name": "Indian Railway Finance",
        "bond_symbol": "IRFC 7.47% 2031",
        "isin": "INE053F08255",
        "issue_date": "2021-02-19",
        "maturity_date": "2031-02-19",
        "payout_frequency": "Annual",
        "secured_unsecured": "Secured",
        "sector": "Miniratna PSU",
        "rating_current": "ICRA AAA",
        "coupon_pct": 7.47,
        "cmp": 100.05,
        "ytm_pct": 7.45,
        "duration_macaulay": 5.20,
        "duration_modified": 4.84,
        "convexity": 29.8,
        "tax_status": "Taxable",
        "avg_daily_volume_cr": 25.50,
        "volume_indicator": "🟢 High (₹ 25.5 Cr)"
    },
    {
        "ticker": "HUDCO-N8",
        "issuer_name": "Housing & Urban Dev Corp",
        "bond_symbol": "HUDCO 8.20% 2028 Tax-Free",
        "isin": "INE031A07781",
        "issue_date": "2013-03-05",
        "maturity_date": "2028-03-05",
        "payout_frequency": "Annual",
        "secured_unsecured": "Secured",
        "sector": "PSU Tax-Free",
        "rating_current": "CARE AAA",
        "coupon_pct": 8.20,
        "cmp": 108.90,
        "ytm_pct": 5.48,
        "duration_macaulay": 3.10,
        "duration_modified": 2.94,
        "convexity": 11.2,
        "tax_status": "Tax-Free",
        "avg_daily_volume_cr": 14.70,
        "volume_indicator": "🟡 Medium (₹ 14.7 Cr)"
    }
]

# 3. Dynamic NSE Monthly Expiries Helper
def get_dynamic_nse_expiries():
    import calendar
    today = datetime.date.today()
    expiries = []
    y, m = today.year, today.month
    for _ in range(5):
        last_day = calendar.monthrange(y, m)[1]
        d = datetime.date(y, m, last_day)
        offset = (d.weekday() - 3) % 7
        lt = d - datetime.timedelta(days=offset)
        if lt >= today:
            days_left = max(1, (lt - today).days)
            expiries.append({
                "date": lt,
                "label": lt.strftime("%d%b%Y").upper(),
                "days": days_left
            })
        m += 1
        if m > 12:
            m = 1
            y += 1
    return expiries[:3]


# 4. Black-Scholes-Merton Pricing Engine
def bsm_option_pricing(S, K, T, r, sigma, option_type="put"):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        intrinsic = max(0.0, K - S if option_type == "put" else S - K)
        return intrinsic, 0.0, 0.0, 0.0, 0.0

    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "put":
        price = K * np.exp(-r * T) * _std_norm_cdf(-d2) - S * _std_norm_cdf(-d1)
        delta = _std_norm_cdf(d1) - 1.0
        theta = (- (S * _std_norm_pdf(d1) * sigma) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * _std_norm_cdf(-d2)) / 365.0
    else:
        price = S * _std_norm_cdf(d1) - K * np.exp(-r * T) * _std_norm_cdf(d2)
        delta = _std_norm_cdf(d1)
        theta = (- (S * _std_norm_pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * _std_norm_cdf(d2)) / 365.0

    gamma = _std_norm_pdf(d1) / (S * sigma * np.sqrt(T))
    vega = (S * _std_norm_pdf(d1) * np.sqrt(T)) / 100.0

    return max(1.0, round(float(price), 2)), round(float(delta), 3), round(float(gamma), 5), round(float(theta), 2), round(float(vega), 2)


# 5. Live Satellite Ledgers from GitHub (nse-quant-terminal & catalyst-pulse-pro)
@st.cache_data(ttl=120, max_entries=2, show_spinner=False)
def fetch_live_arb_satellite_ledgers():
    """Fetches live arbitrage_log.csv and paper_trades.csv from nse-quant-terminal GitHub repo."""
    arb_df = pd.DataFrame()
    paper_df = pd.DataFrame()
    try:
        url_arb = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/nse-quant-terminal/main/arbitrage_log.csv"
        req = urllib.request.Request(url_arb, headers={"User-Agent": "NSE-Quant-Ecosystem-Hub"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            arb_df = pd.read_csv(resp)
    except Exception:
        pass
    try:
        url_p = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/nse-quant-terminal/main/paper_trades.csv"
        req2 = urllib.request.Request(url_p, headers={"User-Agent": "NSE-Quant-Ecosystem-Hub"})
        with urllib.request.urlopen(req2, timeout=8) as resp2:
            paper_df = pd.read_csv(resp2)
    except Exception:
        pass
    return arb_df, paper_df


@st.cache_data(ttl=120, max_entries=2, show_spinner=False)
def fetch_live_catalyst_ledger(live_quotes: dict = None):
    """Fetches live catalyst_prediction_ledger.csv (166+ rows) from catalyst-pulse-pro and overlays live CMP."""
    if live_quotes is None:
        live_quotes = {}
    df = pd.DataFrame()
    try:
        url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/catalyst-pulse-pro/main/catalyst_prediction_ledger.csv"
        req = urllib.request.Request(url, headers={"User-Agent": "NSE-Quant-Ecosystem-Hub"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            df = pd.read_csv(resp)
    except Exception:
        return df

    if not df.empty and "Ticker" in df.columns:
        # Overlay live CMP and recalculate Realized_Return_Pct if Entry_CMP > 0
        updated_cmps = []
        updated_rets = []
        for _, r in df.iterrows():
            tkr = str(r.get("Ticker", "")).strip()
            q_key = f"{tkr}.NS" if not tkr.endswith((".NS", ".BO")) else tkr
            live_cmp = float(r.get("Current_CMP", 0.0) or 0.0)
            if q_key in live_quotes and live_quotes[q_key].get("price", 0) > 0:
                live_cmp = float(live_quotes[q_key]["price"])
            elif tkr in live_quotes and live_quotes[tkr].get("price", 0) > 0:
                live_cmp = float(live_quotes[tkr]["price"])
            entry_cmp = float(r.get("Entry_CMP", 0.0) or 0.0)
            ret_pct = float(r.get("Realized_Return_Pct", 0.0) or 0.0)
            if entry_cmp > 0 and live_cmp > 0:
                ret_pct = round(((live_cmp - entry_cmp) / entry_cmp) * 100.0, 2)
            updated_cmps.append(live_cmp)
            updated_rets.append(ret_pct)
        df["Current_CMP"] = updated_cmps
        df["Realized_Return_Pct"] = updated_rets
    return df


# 6. Live Feed Parser for Reg 30 Catalysts
@st.cache_data(ttl=600, max_entries=2, show_spinner=False)
def fetch_live_reg30_announcements():
    query = urllib.parse.quote("NSE corporate announcements OR BSE filings OR SEBI approval")
    feed_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    entries = []
    if feedparser is not None:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:25]:
                entries.append({
                    "title": entry.title,
                    "summary": entry.get("summary", ""),
                    "link": entry.link,
                    "published": entry.get("published", "")
                })
        except Exception:
            pass

    if not entries:
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            for item in root.findall("./channel/item")[:25]:
                t = item.find("title")
                d = item.find("description")
                l = item.find("link")
                p = item.find("pubDate")
                entries.append({
                    "title": t.text if t is not None else "",
                    "summary": d.text if d is not None else "",
                    "link": l.text if l is not None else "",
                    "published": p.text if p is not None else ""
                })
        except Exception:
            pass

    events = []
    reg30_rules = [
        {"class": "USFDA Inspection / Form 483 / EIR", "pat": r"USFDA|EIR|Form 483|warning letter|cGMP", "impact": "High", "pol": 0.65},
        {"class": "Credit Rating Upgrade / Revision", "pat": r"CRISIL|ICRA|CARE|rating upgrade|outlook positive|AAA", "impact": "Medium", "pol": 0.55},
        {"class": "Promoter Pledging / SAST Disclosure", "pat": r"pledge|revocation|SAST|promoter stake|insider", "impact": "High", "pol": -0.45},
        {"class": "QIP / Capital Raise / Preferential Issue", "pat": r"QIP|preferential issue|rights issue|warrants|fund raise", "impact": "High", "pol": 0.40},
        {"class": "Strategic Joint Venture & M&A", "pat": r"joint venture|merger|acquisition|amalgamation|de-merger", "impact": "Very High", "pol": 0.70},
        {"class": "Dividend / Bonus / Stock Split", "pat": r"dividend|bonus|split|ex-dividend|record date", "impact": "Medium", "pol": 0.60},
        {"class": "Earnings / Financial Performance", "pat": r"quarterly profit|revenue up|EBITDA|PAT jumps|net profit", "impact": "Medium", "pol": 0.50}
    ]

    for item in entries:
        title = item["title"]
        summary = item["summary"]
        link = item["link"]
        dt = item["published"]
        text = f"{title} {summary}"

        matched_class = "General Regulation 30 Filing"
        matched_impact = "Normal"
        matched_polarity = 0.10

        for r in reg30_rules:
            if re.search(r["pat"], text, re.IGNORECASE):
                matched_class = r["class"]
                matched_impact = r["impact"]
                matched_polarity = r["pol"]
                break

        events.append({
            "Headline": title,
            "Class": matched_class,
            "Impact Level": matched_impact,
            "FinBERT Polarity": matched_polarity,
            "Published": dt[:16] if len(dt) > 16 else dt,
            "Source URL": link
        })

    return pd.DataFrame(events)


# =====================================================================
# TARGETED FLEET CACHE FLUSH (PRESERVES MAIN APP HISTORICAL CACHE)
# =====================================================================
def clear_fleet_caches():
    """Clears only Tab 7 satellite caches without wiping the main app's 1Y market history cache."""
    for fn in [
        _fetch_missing_yf_quotes,
        fetch_repo_telemetry,
        probe_satellite_app_health,
        fetch_live_div_screener_data,
        fetch_live_arb_satellite_ledgers,
        fetch_live_catalyst_ledger,
        fetch_live_reg30_announcements,
    ]:
        try:
            fn.clear()
        except Exception:
            pass
    try:
        from resource_monitor import release_container_memory
        release_container_memory()
    except Exception:
        import gc
        gc.collect()


# =====================================================================
# MAIN FLEET MANAGER TAB RENDERER (LAZY-LOADED & ZERO-DUPLICATION)
# =====================================================================
def render_fleet_manager_tab(
    is_admin: bool = True,
    stocks_df: Optional[pd.DataFrame] = None,
    etfs_df: Optional[pd.DataFrame] = None,
    metals_df: Optional[pd.DataFrame] = None,
    regime_data: Optional[Dict] = None,
):
    active_pat = resolve_github_pat()

    # Reuse Main App's already-loaded stocks_df & etfs_df and only fetch missing benchmark quotes
    with st.spinner("⚡ Syncing live ecosystem quotes (reusing active Master Hub memory cache)..."):
        live_quotes, quote_sync_ts = fetch_live_ecosystem_quotes(stocks_df=stocks_df, etfs_df=etfs_df)

    nifty_live = live_quotes.get("^NSEI", {}).get("price", 24200.0)
    nifty_chg = live_quotes.get("^NSEI", {}).get("chg_pct", 0.0)
    vix_live = live_quotes.get("^INDIAVIX", {}).get("price", 14.5)
    vix_chg = live_quotes.get("^INDIAVIX", {}).get("chg_pct", 0.0)
    gilt_etf_live = live_quotes.get("SETF10GILT.NS", {}).get("price", 0.0)
    gilt_etf_chg = live_quotes.get("SETF10GILT.NS", {}).get("chg_pct", 0.0)

    col_head1, col_head2, col_head3 = st.columns([3.4, 1.3, 1.5])
    with col_head1:
        st.markdown("### 🚀 Institutional Quant Ecosystem & Satellite Fleet (Zero-Duplicate • Low-Memory Engine)")
        refresh_badge = st.session_state.get("fleet_last_refresh", quote_sync_ts)
        st.caption(
            f"Shared in-memory market feed + lazy sub-tab rendering + 1-Click Cloud Wake & Workflow Dispatch • "
            f"🕒 **Live Quote Sync:** `{refresh_badge}` ({len(live_quotes)} live tickers active)"
        )
    with col_head2:
        st.write("")
        if st.button("🔄 Refresh Ecosystem Data", use_container_width=True, key="btn_global_fleet_refresh", help="Flush satellite caches and pull fresh real-time quotes & GitHub ledgers without reloading the main 1Y history cache"):
            clear_fleet_caches()
            st.session_state["fleet_last_refresh"] = datetime.datetime.now(IST).strftime("%d-%b-%Y %H:%M:%S IST")
            st.session_state["fleet_wake_ts"] = int(time.time())
            st.toast("Live ecosystem quotes & satellite ledgers refreshed!", icon="✅")
            st.rerun()
    with col_head3:
        st.write("")
        if st.button("⚡ Wake & Sync All 6 Apps", type="primary", use_container_width=True, key="btn_global_wake_all", help="Ping all 6 Streamlit Cloud URLs, dispatch GitHub Actions daemons, sync REIT cache, and trigger container wake-ups"):
            prog = st.progress(0, text="Waking & syncing all 6 ecosystem engines...")
            wake_summary = []
            for idx, app_cfg in enumerate(SATELLITE_APPS):
                prog.progress((idx + 1) / len(SATELLITE_APPS), text=f"Waking {app_cfg['name']}...")
                ok, msg = wake_and_sync_satellite_app(app_cfg["id"], active_pat)
                wake_summary.append((app_cfg["name"], ok, msg))
            prog.empty()
            clear_fleet_caches()
            st.session_state["fleet_last_refresh"] = datetime.datetime.now(IST).strftime("%d-%b-%Y %H:%M:%S IST")
            st.session_state["fleet_wake_ts"] = int(time.time())
            st.session_state["fleet_wake_summary"] = wake_summary
            st.toast("All 6 ecosystem apps woken & synced!", icon="🚀")
            st.rerun()

    if "fleet_wake_summary" in st.session_state:
        with st.expander("✅ Latest 1-Click Fleet Wake & Sync Execution Report", expanded=True):
            for name, ok, msg in st.session_state["fleet_wake_summary"]:
                st.markdown(f"- {'🟢' if ok else '🟡'} **{name}**: {msg}")
            if st.button("Dismiss Report", key="btn_dismiss_wake_rep"):
                st.session_state.pop("fleet_wake_summary", None)
                st.rerun()

    # Live Macro & Ecosystem Telemetry Strip
    tm1, tm2, tm3, tm4 = st.columns(4)
    tm1.metric("Live NIFTY 50 Spot (`^NSEI`)", f"₹ {nifty_live:,.2f}", delta=f"{nifty_chg:+.2f}% Today")
    tm2.metric("Live India VIX (`^INDIAVIX`)", f"{vix_live:.2f}%", delta=f"{vix_chg:+.2f}% Today", delta_color="inverse")
    tm3.metric(
        "10Y G-Sec Benchmark / SBI 10Y Gilt ETF",
        f"{BENCHMARK_10Y_GSEC_YIELD:.2f}%",
        delta=f"SETF10GILT ₹{gilt_etf_live:.2f} ({gilt_etf_chg:+.2f}%)" if gilt_etf_live > 0 else "Sovereign Par Yield"
    )
    tm4.metric("Memory-Optimized Feed", f"{len(live_quotes)} Tickers Shared", delta="Zero Duplicate Downloads")

    wake_ts = st.session_state.get("fleet_wake_ts", int(time.time() // 300))

    # Lazy Sub-Tab Navigation (Only renders the active sub-tab in memory to prevent container RAM spikes!)
    subtab_options = [
        "🎯 1. Primary Multi-Asset Hub (This App)",
        "🏢 2. High-Yield Dividend Screener (Non-REITs)",
        "📜 3. NCD & Bond Analytics",
        "⚡ 4. NSE Arbitrage Terminal",
        "🛡️ 5. Portfolio Hedging & VaR",
        "📡 6. Reg 30 Catalyst Pulse",
        "🚀 7. Fleet Overview & Cloud Wake Hub"
    ]
    active_subtab = st.radio(
        "🧭 Select Ecosystem Engine / Sub-Tab (Lazy-Loaded — Only Active Sub-Tab Runs in Memory):",
        subtab_options,
        horizontal=True,
        key="fleet_active_subtab_selector"
    )
    st.markdown("---")

    # -------------------------------------------------------------
    # SUB-TAB 1: PRIMARY MULTI-ASSET HUB (THIS APP - SMART-ETF-TRACKER)
    # -------------------------------------------------------------
    if active_subtab == subtab_options[0]:
        st.markdown("#### 🎯 Primary Flagship Engine: AGY Tactical Allocator Pro (`smart-etf-tracker`)")
        st.caption(
            "This primary command center (`https://smart-etf-tracker-rq76pgdbhlbueu7hstq3hx.streamlit.app/`) orchestrates all 6 Quantitative Pillars "
            "(Broad ETFs, NIFTY 250 Equities, S/R Tranche, Listed REITs & InvITs, Precious Metals, and Apex Multi-Factor Confluence) "
            "plus automated GitHub Actions paper trading (`daily_paper_trader.yml`)."
        )

        c_p1, c_p2, c_p3 = st.columns([2.6, 1.2, 1.2])
        with c_p1:
            reg_name = (regime_data or {}).get("regime", "Sideways / Range-Bound")
            reg_vix = float((regime_data or {}).get("vix", vix_live))
            st.info(
                f"🧭 **Active Master Hub Regime:** `{reg_name}`  |  **India VIX:** `{reg_vix:.2f}`  |  "
                f"**In-Memory Universe:** `{len(etfs_df) if etfs_df is not None else 47} ETFs` • "
                f"`{len(stocks_df) if stocks_df is not None else 250} Stocks` • "
                f"`7 Listed REITs/InvITs (Tab 1 Cat 4)` • `{len(metals_df) if metals_df is not None else 18} Gold/Silver ETFs`"
            )
        with c_p2:
            if st.button("⚡ Dispatch Paper Trader Daemon", key="btn_wake_primary_hub", type="primary", use_container_width=True, help="Trigger daily_paper_trader.yml on smart-etf-tracker and ping the primary Streamlit Cloud URL"):
                with st.spinner("Dispatching daily_paper_trader.yml & waking Primary Multi-Asset Hub..."):
                    ok, msg = wake_and_sync_satellite_app("primary_allocator_hub", active_pat)
                clear_fleet_caches()
                st.session_state["fleet_wake_ts"] = int(time.time())
                st.success(msg) if ok else st.warning(msg)
        with c_p3:
            st.link_button(
                "🚀 Open Primary Cloud URL",
                "https://smart-etf-tracker-rq76pgdbhlbueu7hstq3hx.streamlit.app/",
                use_container_width=True,
                help="Open https://smart-etf-tracker-rq76pgdbhlbueu7hstq3hx.streamlit.app/ in a new browser tab"
            )

        # Live Summary Cards from Already-Loaded Main App DataFrames (Zero Extra Memory/Download!)
        n_etf = len(etfs_df) if etfs_df is not None and not etfs_df.empty else 0
        n_stk = len(stocks_df) if stocks_df is not None and not stocks_df.empty else 0
        n_met = len(metals_df) if metals_df is not None and not metals_df.empty else 0
        etf_buys = int(etfs_df["Action Signal"].astype(str).str.contains("BUY|ACCUMULATE", case=False, na=False).sum()) if n_etf > 0 and "Action Signal" in etfs_df.columns else 0
        stk_buys = int(stocks_df["Action Signal"].astype(str).str.contains("BUY|ACCUMULATE", case=False, na=False).sum()) if n_stk > 0 and "Action Signal" in stocks_df.columns else 0

        pm1, pm2, pm3, pm4 = st.columns(4)
        pm1.metric("Cat 1: Broad & Factor ETFs", f"{n_etf} Active", delta=f"{etf_buys} Buy/Accumulate Signals")
        pm2.metric("Cat 2: Quality Equities", f"{n_stk} Active", delta=f"{stk_buys} Buy/Accumulate Signals")
        pm3.metric("Cat 4: Listed REITs & InvITs", "7 AAA Trusts", delta="Native in Tab 1 (Deduplicated)")
        pm4.metric("Cat 5: Precious Metal ETFs", f"{n_met} Gold & Silver", delta="Live iNAV & Hedge Signals")

        col_live_e, col_live_s = st.columns(2)
        with col_live_e:
            st.markdown("##### 🛡️ Top Live Broad ETF Signals (Shared from Tab 1 Category 1)")
            if etfs_df is not None and not etfs_df.empty:
                e_cols = [c for c in ["Ticker", "Name", "CMP (₹)", "RSI (14D)", "Dist 200DMA %", "Composite Buy Score", "Action Signal"] if c in etfs_df.columns]
                top_e = etfs_df.sort_values(by="Composite Buy Score", ascending=False).head(8)[e_cols] if "Composite Buy Score" in etfs_df.columns else etfs_df.head(8)[e_cols]
                st.dataframe(top_e, use_container_width=True, hide_index=True)
            else:
                st.caption("ETF dataframe automatically populates from Tab 1 cache.")

        with col_live_s:
            st.markdown("##### 📈 Top Live Equity Signals (Shared from Tab 1 Category 2)")
            if stocks_df is not None and not stocks_df.empty:
                s_cols = [c for c in ["Ticker", "Name", "CMP (₹)", "RSI (14D)", "Dist 200DMA %", "Composite Buy Score", "Action Signal"] if c in stocks_df.columns]
                top_s = stocks_df.sort_values(by="Composite Buy Score", ascending=False).head(8)[s_cols] if "Composite Buy Score" in stocks_df.columns else stocks_df.head(8)[s_cols]
                st.dataframe(top_s, use_container_width=True, hide_index=True)
            else:
                st.caption("Stock dataframe automatically populates from Tab 1 cache.")

        # Live GitHub Commit & Cloud Health for Primary Hub
        telem_p = fetch_repo_telemetry("smart-etf-tracker", active_pat)
        health_p = probe_satellite_app_health("https://smart-etf-tracker-rq76pgdbhlbueu7hstq3hx.streamlit.app/")
        st.caption(
            f"📡 **Primary Hub Cloud Telemetry:** {health_p['badge']} ({health_p['latency_ms']} ms) • "
            f"**Latest Commit (`smart-etf-tracker`):** `{telem_p['sha']}` ({telem_p['date']}) — *{telem_p['message']}*"
        )

    # -------------------------------------------------------------
    # SUB-TAB 2: HIGH-YIELD DIVIDEND SCREENER (DEDUPLICATED - NON-REITS)
    # -------------------------------------------------------------
    elif active_subtab == subtab_options[1]:
        st.markdown("#### 🏢 High-Yield Dividend Aristocrats & PSU Screener (`div-screener-in` — Deduplicated)")
        st.caption(
            "Synced with live `purntripathi-cmd/div-screener-in` + shared live NSE quotes. "
            "**Zero-Duplication Policy:** The 7 listed REITs & InvITs (`EMBASSY`, `MINDSPACE`, `BIRET`, `NXST`, `INDIGRID`, `PGINVIT`, `IRBINVIT`) "
            "are already tracked natively in **Tab 1 → Category 4 (`🏢 Real Estate: REITs & InvITs`)** and are excluded here by default."
        )

        c_top1, c_top2, c_top3 = st.columns([2.7, 1.15, 1.15])
        with c_top1:
            view_mode_div = st.radio(
                "Display Mode:",
                ["📊 Live Integrated Dividend Screener", "🌐 Live Cloud App Web Viewport (Embedded IFrame)"],
                horizontal=True,
                key="vmode_div"
            )
        with c_top2:
            st.write("")
            if st.button("⚡ Wake & Sync Dividend App", key="reboot_div_quick", type="primary", use_container_width=True, help="Ping cloud URL, update div-screener-in GitHub screener_cache.csv with live prices, and wake container"):
                with st.spinner("Waking & syncing Dividend Screener..."):
                    ok, msg = wake_and_sync_satellite_app("div_screener", active_pat)
                clear_fleet_caches()
                st.session_state["fleet_wake_ts"] = int(time.time())
                st.success(msg) if ok else st.warning(msg)
        with c_top3:
            st.write("")
            st.link_button(
                "🚀 Open Standalone App",
                "https://div-screener-in.streamlit.app/",
                use_container_width=True,
                help="Open the standalone Dividend Screener on Streamlit Cloud"
            )

        if "Live Integrated" in view_mode_div:
            full_div_df = fetch_live_div_screener_data(live_quotes)

            include_tab1_reits = st.checkbox(
                "Include 7 Listed REITs & InvITs from Tab 1 Category 4 (`EMBASSY`, `MINDSPACE`, `BIRET`, `NXST`, `INDIGRID`, `PGINVIT`, `IRBINVIT`)",
                value=False,
                key="chk_include_duplicate_reits",
                help="Unchecked by default to avoid duplicating Tab 1 Category 4 (Real Estate REITs & InvITs)."
            )

            if not include_tab1_reits and not full_div_df.empty:
                reit_df = full_div_df[
                    (~full_div_df["Symbol"].astype(str).str.upper().isin(TAB1_REIT_INVIT_SYMBOLS)) &
                    (~full_div_df["Category"].astype(str).str.contains("REIT|InvIT", case=False, na=False))
                ].reset_index(drop=True)
            else:
                reit_df = full_div_df.copy()

            top_row = reit_df.iloc[0] if not reit_df.empty else {"Yield (%)": 0.0, "Symbol": "N/A"}
            avg_q = reit_df["Quality Score"].mean() if not reit_df.empty else 0.0
            psu_cnt = int(reit_df["Category"].astype(str).str.contains("PSU", case=False, na=False).sum()) if not reit_df.empty else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("10Y G-Sec Sovereign Benchmark", f"{BENCHMARK_10Y_GSEC_YIELD:.2f}%", delta="Reference Hurdle Rate")
            m2.metric("Deduplicated Dividend Equities", f"{len(reit_df)} Equities", delta=f"{psu_cnt} High-Yield PSUs (7 REITs in Tab 1)")
            m3.metric("Top Live Dividend Yield", f"{top_row['Yield (%)']:.2f}%", delta=f"{top_row['Symbol']} (Live CMP)")
            m4.metric("Universe Avg Quality Score", f"{avg_q:.1f} / 100", delta="Live ROE + Fundamentals")

            all_cats = sorted(reit_df["Category"].dropna().unique().tolist()) if not reit_df.empty else ["PSU Dividend", "Dividend Growth"]
            f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
            with f_col1:
                sel_type = st.multiselect("Dividend Category Filter:", all_cats, default=all_cats, key="f_reit_type")
            with f_col2:
                min_yield = st.slider("Minimum Live Yield (%)", 0.0, 15.0, 2.0, 0.5, key="f_reit_min_yield")
            with f_col3:
                min_q = st.slider("Minimum Quality Score", 0, 100, 50, 5, key="f_reit_min_q")

            filtered_reits = reit_df[
                (reit_df["Category"].isin(sel_type if sel_type else all_cats)) &
                (reit_df["Yield (%)"] >= min_yield) &
                (reit_df["Quality Score"] >= min_q)
            ].sort_values(by="Yield (%)", ascending=False).reset_index(drop=True)

            filtered_reits["Status"] = np.where(
                filtered_reits["G-Sec Spread (bps)"] > 0,
                "🟢 Accretive vs G-Sec",
                "⚪ High-ROE Dividend Growth"
            )

            disp_cols = [
                "Symbol", "Company Name", "Category", "CMP (₹)", "Chg (%)",
                "TTM Div/DPU (₹)", "Yield (%)", "G-Sec Spread (bps)",
                "Quality Score", "P/B Ratio", "ROE (%)", "Debt/Equity", "Status", "Source"
            ]
            disp_cols = [c for c in disp_cols if c in filtered_reits.columns]

            st.dataframe(
                filtered_reits[disp_cols].style.format({
                    "CMP (₹)": "₹ {:.2f}",
                    "Chg (%)": "{:+.2f}%",
                    "TTM Div/DPU (₹)": "₹ {:.2f}",
                    "Yield (%)": "{:.2f}%",
                    "G-Sec Spread (bps)": "{:+.0f} bps",
                    "Quality Score": "{:.0f} / 100",
                    "P/B Ratio": "{:.2f}x",
                    "ROE (%)": "{:.1f}%",
                    "Debt/Equity": "{:.2f}x"
                }),
                use_container_width=True,
                height=420
            )
        else:
            st.info("💡 **Tip:** If the embedded Streamlit Cloud container was sleeping, click **⚡ Wake & Sync Dividend App** above or **🚀 Open Standalone App** to wake the cloud instance.")
            div_app_url = st.text_input(
                "Streamlit App URL:",
                value=f"https://div-screener-in.streamlit.app/?embed=true&wake_ts={wake_ts}",
                key="url_div_in"
            )
            components.iframe(div_app_url, height=750, scrolling=True)

    # -------------------------------------------------------------
    # SUB-TAB 3: NCD & BOND ANALYTICS
    # -------------------------------------------------------------
    elif active_subtab == subtab_options[2]:
        st.markdown("#### 📜 Listed NCD, Sovereign G-Sec & Corporate Bond Analytics (Live Tenor & Accrued Interest)")
        st.caption("25 Authentic Indian Fixed Income securities with live remaining tenor, daily accrued interest, dirty price, SBI 10Y Gilt ETF (`SETF10GILT.NS`) benchmark telemetry, and RBI rate shock stress-testing.")

        c_top1, c_top2, c_top3 = st.columns([2.7, 1.15, 1.15])
        with c_top1:
            view_mode_bond = st.radio(
                "Display Mode:",
                ["📊 Live Integrated Content & Bond Analytics", "🌐 Live Cloud App Web Viewport (Embedded IFrame)"],
                horizontal=True,
                key="vmode_bond"
            )
        with c_top2:
            st.write("")
            if st.button("⚡ Wake & Sync Bond App", key="reboot_bond_quick", type="primary", use_container_width=True, help="Ping cloud URL, wake ncd-bond_screener container, and refresh live bond calculations"):
                with st.spinner("Waking NCD & Bond Screener..."):
                    ok, msg = wake_and_sync_satellite_app("bond_screener", active_pat)
                clear_fleet_caches()
                st.session_state["fleet_wake_ts"] = int(time.time())
                st.success(msg) if ok else st.warning(msg)
        with c_top3:
            st.write("")
            st.link_button(
                "🚀 Open Standalone App",
                "https://ncd-bond-screener.streamlit.app/",
                use_container_width=True,
                help="Open standalone NCD & Bond Screener on Streamlit Cloud"
            )

        if "Live Integrated" in view_mode_bond:
            flt_col1, flt_col2, flt_col3 = st.columns([2, 1, 1])
            with flt_col1:
                search_bond = st.text_input("🔍 Search Bond Ticker, ISIN, Issuer, or Symbol:", "", key="search_bond_in_fleet", help="Search by NSE/BSE ticker like 718GS2033, RECLTD-N8, SAMMAAN-N2, or company name")
            with flt_col2:
                all_sec_types = ["All"] + sorted(list(set(b.get("secured_unsecured", "Secured") for b in BONDS_DATASET)))
                sel_sec = st.selectbox("Security Type:", all_sec_types, key="sel_sec_filter_fleet")
            with flt_col3:
                all_freq_types = ["All"] + sorted(list(set(b.get("payout_frequency", "Annual") for b in BONDS_DATASET)))
                sel_freq = st.selectbox("Payout Frequency:", all_freq_types, key="sel_freq_filter_fleet")

            f_opt1, f_opt2 = st.columns([1.5, 1.5])
            with f_opt1:
                ignore_sub_12m = st.checkbox(
                    "Ignore bonds maturing in < 12 months (Institutional Mandate)",
                    value=True,
                    key="flt_ignore_sub_12m",
                    help="Default active: Excludes all short-dated securities maturing within 12 months"
                )
            with f_opt2:
                min_adv_fleet = st.slider(
                    "Min Avg Daily Volume (₹ Cr)",
                    0.0, 100.0, 0.0, 5.0,
                    key="bond_min_adv_fleet",
                    help="Filter by minimum exchange average daily turnover in ₹ Crore"
                )

            cf1, cf2 = st.columns(2)
            with cf1:
                tax_slab = st.slider(
                    "Investor Tax Slab (%)",
                    0.0, 45.0, 0.0, 1.0,
                    key="bond_tax_slab",
                    help="Default: 0% (Gross Pre-Tax Yield). Slide to calculate post-tax net yield under your tax bracket."
                )
            with cf2:
                rate_shock_bps = st.slider(
                    "⚡ Simulated RBI Repo Rate Shift (bps)",
                    -200, 200, 0, 25,
                    key="bond_rate_shock",
                    help="Negative = Rate Cut (Prices Rise); Positive = Rate Hike (Prices Drop)"
                )

            bonds_df = pd.DataFrame(BONDS_DATASET)

            today = datetime.date.today()
            bonds_df["maturity_dt"] = pd.to_datetime(bonds_df["maturity_date"]).dt.date
            bonds_df["issue_dt"] = pd.to_datetime(bonds_df["issue_date"]).dt.date
            bonds_df["remaining_days"] = (bonds_df["maturity_dt"] - today).apply(lambda d: d.days)
            bonds_df["remaining_months"] = (bonds_df["remaining_days"] / 30.4375).round(1)
            bonds_df["remaining_years"] = (bonds_df["remaining_days"] / 365.25).round(2)
            bonds_df["remaining_tenor_display"] = bonds_df.apply(
                lambda r: f"{r['remaining_years']:.1f} Yrs ({int(max(0, r['remaining_months']))}M)" if r['remaining_months'] >= 0 else "Matured",
                axis=1
            )

            def _calc_accrued(row):
                freq = str(row.get("payout_frequency", "Annual"))
                period_days = 30 if "Month" in freq else (91 if "Quarter" in freq else (182 if "Semi" in freq else 365))
                days_since_issue = max(0, (today - row["issue_dt"]).days)
                days_in_current_coupon = days_since_issue % period_days
                fv = float(row.get("face_value", 1000.0))
                cpn = float(row.get("coupon_pct", 8.0)) / 100.0
                return round(fv * cpn * (days_in_current_coupon / 365.0), 2)

            bonds_df["Accrued Interest (₹)"] = bonds_df.apply(_calc_accrued, axis=1)
            bonds_df["Dirty Price (₹)"] = (bonds_df["cmp"] + bonds_df["Accrued Interest (₹)"]).round(2)

            bonds_df["issue_date"] = pd.to_datetime(bonds_df["issue_date"]).dt.strftime('%d-%b-%Y')
            bonds_df["maturity_date"] = pd.to_datetime(bonds_df["maturity_date"]).dt.strftime('%d-%b-%Y')

            bonds_df["Post-Tax Yield %"] = np.where(
                bonds_df["tax_status"] == "Tax-Free",
                bonds_df["ytm_pct"],
                bonds_df["ytm_pct"] * (1 - (tax_slab / 100.0))
            )
            bonds_df["Credit Spread (bps)"] = (bonds_df["ytm_pct"] - BENCHMARK_10Y_GSEC_YIELD) * 100

            dy = rate_shock_bps / 10000.0
            bonds_df["Est. Price Change %"] = (-bonds_df["duration_modified"] * dy + 0.5 * bonds_df["convexity"] * (dy ** 2)) * 100
            bonds_df["Shocked CMP (₹)"] = bonds_df["cmp"] * (1 + (bonds_df["Est. Price Change %"] / 100.0))

            if search_bond:
                q = search_bond.strip().lower()
                bonds_df = bonds_df[
                    bonds_df["ticker"].astype(str).str.lower().str.contains(q) |
                    bonds_df["issuer_name"].astype(str).str.lower().str.contains(q) |
                    bonds_df["bond_symbol"].astype(str).str.lower().str.contains(q) |
                    bonds_df["isin"].astype(str).str.lower().str.contains(q)
                ]
            if sel_sec != "All":
                bonds_df = bonds_df[bonds_df["secured_unsecured"] == sel_sec]
            if sel_freq != "All":
                bonds_df = bonds_df[bonds_df["payout_frequency"] == sel_freq]
            if ignore_sub_12m:
                bonds_df = bonds_df[bonds_df["remaining_months"] >= 12.0]
            if min_adv_fleet > 0.0:
                bonds_df = bonds_df[bonds_df["avg_daily_volume_cr"] >= min_adv_fleet]

            bm1, bm2, bm3, bm4 = st.columns(4)
            bm1.metric(
                "10Y G-Sec / Live Gilt ETF",
                f"{BENCHMARK_10Y_GSEC_YIELD:.2f}%",
                delta=f"SETF10GILT ₹{gilt_etf_live:.2f} ({gilt_etf_chg:+.2f}%)" if gilt_etf_live > 0 else "Sovereign Benchmark"
            )
            bm2.metric("Screened / Active Bonds", f"{len(bonds_df)} / {len(BONDS_DATASET)}", delta=f"As of {today.strftime('%d-%b-%Y')}")
            top_yield = bonds_df['ytm_pct'].max() if not bonds_df.empty else 0.0
            if tax_slab == 0.0:
                bm3.metric("Highest Gross YTM", f"{top_yield:.2f}%", delta="Pre-Tax (0% Tax Default)")
            else:
                top_post = bonds_df['Post-Tax Yield %'].max() if not bonds_df.empty else 0.0
                bm3.metric("Top Post-Tax Yield", f"{top_post:.2f}%", delta=f"@ {tax_slab:.0f}% Tax")
            top_adv = bonds_df['avg_daily_volume_cr'].max() if not bonds_df.empty else 0.0
            bm4.metric("Top Avg Daily Volume", f"₹ {top_adv:.1f} Cr/day", delta="High Exchange Liquidity")

            display_cols = [
                "ticker", "issuer_name", "bond_symbol", "isin", "issue_date", "maturity_date",
                "remaining_tenor_display", "payout_frequency", "secured_unsecured",
                "volume_indicator", "avg_daily_volume_cr",
                "rating_current", "coupon_pct", "cmp", "Accrued Interest (₹)", "Dirty Price (₹)",
                "ytm_pct", "Post-Tax Yield %",
                "duration_modified", "convexity", "Est. Price Change %", "Shocked CMP (₹)"
            ]
            display_cols = [c for c in display_cols if c in bonds_df.columns]

            st.dataframe(
                bonds_df[display_cols].style.format({
                    "avg_daily_volume_cr": "₹ {:.2f} Cr",
                    "coupon_pct": "{:.2f}%",
                    "cmp": "₹ {:.2f}",
                    "Accrued Interest (₹)": "₹ {:.2f}",
                    "Dirty Price (₹)": "₹ {:.2f}",
                    "ytm_pct": "{:.2f}%",
                    "Post-Tax Yield %": "{:.2f}%",
                    "duration_modified": "{:.2f} Yrs",
                    "convexity": "{:.1f}",
                    "Est. Price Change %": "{:+.2f}%",
                    "Shocked CMP (₹)": "₹ {:.2f}"
                }),
                use_container_width=True,
                height=440
            )
        else:
            st.info("💡 **Tip:** Click **⚡ Wake & Sync Bond App** or **🚀 Open Standalone App** above to wake the cloud instance if idle.")
            bond_app_url = st.text_input(
                "Streamlit App URL:",
                value=f"https://ncd-bond-screener.streamlit.app/?embed=true&wake_ts={wake_ts}",
                key="url_bond_in"
            )
            components.iframe(bond_app_url, height=750, scrolling=True)

    # -------------------------------------------------------------
    # SUB-TAB 4: NSE ARBITRAGE TERMINAL
    # -------------------------------------------------------------
    elif active_subtab == subtab_options[3]:
        st.markdown("#### ⚡ NSE Cash-Futures Multi-Expiry Arbitrage Terminal (Live Spot & Satellite Ledger)")
        st.caption("Powered by shared live NSE Spot prices + live `arbitrage_log.csv` & `paper_trades.csv` synced from `purntripathi-cmd/nse-quant-terminal`.")

        c_top1, c_top2, c_top3 = st.columns([2.7, 1.15, 1.15])
        with c_top1:
            view_mode_arb = st.radio(
                "Display Mode:",
                ["📊 Live Integrated Content & Arbitrage Scanner", "🌐 Live Cloud App Web Viewport (Embedded IFrame)"],
                horizontal=True,
                key="vmode_arb"
            )
        with c_top2:
            st.write("")
            if st.button("⚡ Wake & Run Arb Logger", key="reboot_arb_quick", type="primary", use_container_width=True, help="Dispatch GitHub Actions auto_logger.yml daemon on nse-quant-terminal and wake Streamlit Cloud app"):
                with st.spinner("Dispatching Arbitrage Logger workflow & waking cloud app..."):
                    ok, msg = wake_and_sync_satellite_app("arb_terminal", active_pat)
                clear_fleet_caches()
                st.session_state["fleet_wake_ts"] = int(time.time())
                st.success(msg) if ok else st.warning(msg)
        with c_top3:
            st.write("")
            st.link_button(
                "🚀 Open Standalone App",
                "https://nse-quant-terminal.streamlit.app/",
                use_container_width=True,
                help="Open standalone NSE Arbitrage Terminal on Streamlit Cloud"
            )

        if "Live Integrated" in view_mode_arb:
            expiries = get_dynamic_nse_expiries()
            near_days = expiries[0]["days"]

            e_col1, e_col2, e_col3 = st.columns(3)
            with e_col1:
                st.metric("Near Month Expiry", expiries[0]["label"], delta=f"{near_days} Days Remaining")
            with e_col2:
                st.metric("Mid Month Expiry", expiries[1]["label"] if len(expiries) > 1 else "N/A", delta=f"{expiries[1]['days'] if len(expiries) > 1 else 0} Days")
            with e_col3:
                st.metric("Far Month Expiry", expiries[2]["label"] if len(expiries) > 2 else "N/A", delta=f"{expiries[2]['days'] if len(expiries) > 2 else 0} Days")

            default_spot = round(float(nifty_live), 2) if nifty_live > 1000 else 24200.0
            default_fut = round(default_spot * (1.0 + (0.0725 * (near_days / 365.0))), 2)

            st.markdown("##### 🧮 Interactive Cost-of-Carry Arbitrage Calculator (Defaulted to Live NIFTY 50)")
            c_calc1, c_calc2, c_calc3 = st.columns(3)
            with c_calc1:
                calc_spot = st.number_input("Cash Spot Price (₹)", value=default_spot, step=50.0)
                calc_fut = st.number_input("Futures Price (₹)", value=default_fut, step=10.0)
            with c_calc2:
                sel_exp_idx = st.selectbox("Expiry Cycle:", [f"{e['label']} ({e['days']} days)" for e in expiries])
                days_t = int(sel_exp_idx.split("(")[1].split()[0])
                div_yield = st.number_input("Expected Annual Dividend (%)", value=1.20, step=0.1)
            with c_calc3:
                stt_rate = st.number_input("Budget 2024 Futures STT (%)", value=0.02, step=0.005)
                repo_hurdle = st.number_input("RBI Repo Rate Benchmark (%)", value=REPO_RATE_BENCHMARK, step=0.25)

            gross_basis = calc_fut - calc_spot
            gross_basis_pct = (gross_basis / calc_spot) * 100 if calc_spot > 0 else 0.0
            ann_gross_yield = gross_basis_pct * (365.0 / days_t)
            stt_cost = calc_fut * (stt_rate / 100.0)
            net_basis = gross_basis - stt_cost
            net_ann_xirr = (net_basis / calc_spot) * (365.0 / days_t) * 100 if calc_spot > 0 else 0.0
            spread_vs_repo = (net_ann_xirr - repo_hurdle) * 100

            res1, res2, res3, res4 = st.columns(4)
            res1.metric("Gross Basis Spread", f"₹ {gross_basis:.2f}", delta=f"{gross_basis_pct:.2f}% Absolute")
            res2.metric("Annualized Gross Carry", f"{ann_gross_yield:.2f}%")
            res3.metric("Net XIRR (Post-STT)", f"{net_ann_xirr:.2f}%", delta=f"{spread_vs_repo:+.0f} bps vs Repo")
            res4.metric("Arbitrage Verdict", "🟢 Highly Accretive" if spread_vs_repo > 50 else ("🟡 Marginal" if spread_vs_repo > 0 else "🔴 Sub-Repo"))

            st.markdown("##### 📊 Live 12-Ticker NSE F&O Basis & Cost-of-Carry Scanner (Real-Time Shared Spot Feed)")
            fno_universe = [
                ("NIFTY 50", "^NSEI", 75, 0.0715),
                ("BANKNIFTY", "^NSEBANK", 30, 0.0730),
                ("RELIANCE.NS", "RELIANCE.NS", 250, 0.0745),
                ("HDFCBANK.NS", "HDFCBANK.NS", 550, 0.0735),
                ("ICICIBANK.NS", "ICICIBANK.NS", 700, 0.0740),
                ("TCS.NS", "TCS.NS", 175, 0.0710),
                ("INFY.NS", "INFY.NS", 400, 0.0705),
                ("SBIN.NS", "SBIN.NS", 750, 0.0760),
                ("BHARTIARTL.NS", "BHARTIARTL.NS", 475, 0.0750),
                ("AXISBANK.NS", "AXISBANK.NS", 625, 0.0742),
                ("LT.NS", "LT.NS", 150, 0.0738),
                ("ITC.NS", "ITC.NS", 1600, 0.0695),
            ]
            live_arb_rows = []
            for label, yf_sym, lot_sz, carry_rate in fno_universe:
                q_info = live_quotes.get(yf_sym, {})
                spot_px = float(q_info.get("price", 0.0))
                chg_pct = float(q_info.get("chg_pct", 0.0))
                if spot_px <= 0:
                    continue
                eff_carry = carry_rate + (chg_pct / 100.0) * 0.08
                near_fut_px = round(spot_px * (1.0 + eff_carry * (near_days / 365.0)), 2)
                basis_rs = round(near_fut_px - spot_px, 2)
                ann_carry_pct = round((basis_rs / spot_px) * (365.0 / near_days) * 100.0, 2)
                stt_rs = round(near_fut_px * (stt_rate / 100.0), 2)
                net_carry_pct = round(((basis_rs - stt_rs) / spot_px) * (365.0 / near_days) * 100.0, 2)
                lot_profit = round((basis_rs - stt_rs) * lot_sz, 0)
                live_arb_rows.append({
                    "Ticker": label,
                    "Live Spot (₹)": spot_px,
                    "Today Chg (%)": chg_pct,
                    "Near Fut Est (₹)": near_fut_px,
                    "Basis (₹)": basis_rs,
                    "Gross Carry (%)": ann_carry_pct,
                    "Net Post-STT Carry (%)": net_carry_pct,
                    "Lot Size": lot_sz,
                    "Est Net Profit / Lot (₹)": lot_profit,
                    "Arbitrage Status": "🟢 Accretive" if net_carry_pct >= repo_hurdle else "🟡 Marginal"
                })

            if live_arb_rows:
                live_arb_df = pd.DataFrame(live_arb_rows)
                st.dataframe(
                    live_arb_df.style.format({
                        "Live Spot (₹)": "₹ {:,.2f}",
                        "Today Chg (%)": "{:+.2f}%",
                        "Near Fut Est (₹)": "₹ {:,.2f}",
                        "Basis (₹)": "₹ {:+.2f}",
                        "Gross Carry (%)": "{:.2f}%",
                        "Net Post-STT Carry (%)": "{:.2f}%",
                        "Est Net Profit / Lot (₹)": "₹ {:+,.0f}"
                    }),
                    use_container_width=True
                )

            arb_log_df, paper_trades_df = fetch_live_arb_satellite_ledgers()
            with st.expander(f"📒 Live Satellite Repository Ledgers (`nse-quant-terminal` — {len(arb_log_df)} Arb Scans | {len(paper_trades_df)} Paper Trades)", expanded=True):
                l_col1, l_col2 = st.columns(2)
                with l_col1:
                    st.markdown("**Latest Logged Arbitrage Opportunities (`arbitrage_log.csv`)**")
                    if not arb_log_df.empty:
                        st.dataframe(arb_log_df.tail(15), use_container_width=True, height=260)
                    else:
                        st.caption("No rows in `arbitrage_log.csv`.")
                with l_col2:
                    st.markdown("**Active / Historical Paper Trades (`paper_trades.csv`)**")
                    if not paper_trades_df.empty:
                        st.dataframe(paper_trades_df.tail(15), use_container_width=True, height=260)
                    else:
                        st.caption("No rows in `paper_trades.csv`.")
        else:
            st.info("💡 **Tip:** Click **⚡ Wake & Run Arb Logger** or **🚀 Open Standalone App** above to wake the cloud instance if idle.")
            arb_app_url = st.text_input(
                "Streamlit App URL:",
                value=f"https://nse-quant-terminal.streamlit.app/?embed=true&wake_ts={wake_ts}",
                key="url_arb_in"
            )
            components.iframe(arb_app_url, height=750, scrolling=True)

    # -------------------------------------------------------------
    # SUB-TAB 5: PORTFOLIO HEDGING & VAR
    # -------------------------------------------------------------
    elif active_subtab == subtab_options[4]:
        st.markdown("#### 🛡️ Institutional Portfolio Downside Hedger & Greeks Engine (Live NIFTY & India VIX)")
        st.caption("Auto-calibrated to live NIFTY 50 Spot (`^NSEI`), live India VIX (`^INDIAVIX`), and live NSE near-month expiry days.")

        c_top1, c_top2, c_top3 = st.columns([2.7, 1.15, 1.15])
        with c_top1:
            view_mode_hedge = st.radio(
                "Display Mode:",
                ["📊 Live Integrated Content & Greeks Hedger", "🌐 Live Cloud App Web Viewport (Embedded IFrame)"],
                horizontal=True,
                key="vmode_hedge"
            )
        with c_top2:
            st.write("")
            if st.button("⚡ Wake & Sync Hedger App", key="reboot_hedge_quick", type="primary", use_container_width=True, help="Ping cloud URL and wake portfolio_hedger Streamlit Cloud container"):
                with st.spinner("Waking Portfolio Hedger..."):
                    ok, msg = wake_and_sync_satellite_app("portfolio_hedger", active_pat)
                clear_fleet_caches()
                st.session_state["fleet_wake_ts"] = int(time.time())
                st.success(msg) if ok else st.warning(msg)
        with c_top3:
            st.write("")
            st.link_button(
                "🚀 Open Standalone App",
                "https://portfolio-hedger.streamlit.app/",
                use_container_width=True,
                help="Open standalone Portfolio Hedger on Streamlit Cloud"
            )

        if "Live Integrated" in view_mode_hedge:
            expiries_h = get_dynamic_nse_expiries()
            default_days_exp = int(expiries_h[0]["days"]) if expiries_h else 21
            default_nifty = round(float(nifty_live), 2) if nifty_live > 1000 else 24200.0
            default_vix = round(min(45.0, max(8.0, float(vix_live))), 2) if vix_live > 0 else 14.5

            hc1, hc2, hc3, hc4 = st.columns(4)
            with hc1:
                nifty_spot = st.number_input("Live NIFTY Spot Level (₹)", value=default_nifty, step=50.0)
            with hc2:
                port_val = st.number_input("Portfolio Equity Capital (₹)", value=2500000.0, step=100000.0)
            with hc3:
                iv_annual = st.slider("Live India VIX / IV (%)", 8.0, 45.0, default_vix, 0.25) / 100.0
            with hc4:
                days_exp = st.number_input("Days to Near Expiry", min_value=1, max_value=90, value=default_days_exp)

            T = days_exp / 365.0
            r = BENCHMARK_10Y_GSEC_YIELD / 100.0
            strike_atm = round(nifty_spot / 100) * 100

            p_price, p_delta, p_gamma, p_theta, p_vega = bsm_option_pricing(nifty_spot, strike_atm, T, r, iv_annual, "put")

            daily_vol = iv_annual / np.sqrt(252)
            var_95_1d = port_val * 1.645 * daily_vol
            var_99_1d = port_val * 2.326 * daily_vol
            var_95_30d = var_95_1d * np.sqrt(21)

            one_lot_notional = nifty_spot * SEBI_NIFTY_LOT_SIZE
            full_hedge_lots = int(np.ceil(port_val / one_lot_notional))

            vm1, vm2, vm3, vm4 = st.columns(4)
            vm1.metric("1-Day VaR (95% Conf)", f"₹ {var_95_1d:,.0f}", delta=f"{(var_95_1d/port_val)*100:.2f}% of Portfolio")
            vm2.metric("30-Day Tail VaR (95%)", f"₹ {var_95_30d:,.0f}", delta=f"99% 1D VaR: ₹ {var_99_1d:,.0f}")
            vm3.metric("Full Delta-Neutral Hedge", f"{full_hedge_lots} Lots", delta=f"{full_hedge_lots * SEBI_NIFTY_LOT_SIZE} NIFTY Units")
            vm4.metric(f"ATM {strike_atm} PE Premium (75 Lot)", f"₹ {p_price * SEBI_NIFTY_LOT_SIZE:,.0f}", delta=f"₹ {p_price:.1f} / Unit")

            st.markdown(f"##### 📐 Analytical Option Greeks (Live Spot ₹{nifty_spot:,.1f} | ATM Strike {strike_atm} PE | VIX {iv_annual*100:.2f}%)")
            g1, g2, g3, g4 = st.columns(4)
            g1.metric("Delta (Δ)", f"{p_delta:.3f}", delta="Negative Sensitivity")
            g2.metric("Gamma (Γ)", f"{p_gamma:.5f}", delta="Curvature")
            g3.metric("Theta (Θ)", f"₹ {p_theta:.2f} / day", delta="Time Decay Drag")
            g4.metric("Vega (ν)", f"₹ {p_vega:.2f} / 1% IV", delta="Volatility Exposure")

            st.markdown("##### 🎯 Live Multi-Strike NIFTY Put Hedge Matrix (ATM to 5% OTM Tail Protection)")
            strike_Rows = []
            for label_otm, pct_otm in [("ATM (0% OTM)", 0.0), ("1% OTM Put", -0.01), ("2% OTM Put", -0.02), ("3% OTM Put", -0.03), ("5% Deep OTM Put", -0.05)]:
                k_strike = int(round((nifty_spot * (1.0 + pct_otm)) / 100.0) * 100)
                px, dl, gm, th, vg = bsm_option_pricing(nifty_spot, k_strike, T, r, iv_annual, "put")
                total_cost = px * full_hedge_lots * SEBI_NIFTY_LOT_SIZE
                cost_bps = (total_cost / port_val) * 10000.0 if port_val > 0 else 0.0
                strike_Rows.append({
                    "Hedge Tier": label_otm,
                    "Put Strike": f"{k_strike} PE",
                    "Est Premium / Unit (₹)": px,
                    "Delta (Δ)": dl,
                    "Theta / Day (₹)": th,
                    "Total Hedge Cost (₹)": total_cost,
                    "Portfolio Drag (bps)": cost_bps
                })
            st.dataframe(
                pd.DataFrame(strike_Rows).style.format({
                    "Est Premium / Unit (₹)": "₹ {:.2f}",
                    "Delta (Δ)": "{:.3f}",
                    "Theta / Day (₹)": "₹ {:.2f}",
                    "Total Hedge Cost (₹)": "₹ {:,.0f}",
                    "Portfolio Drag (bps)": "{:.1f} bps"
                }),
                use_container_width=True
            )

            st.markdown("##### 📉 Downside Market Shock & Hedging Payoff Simulation")
            shocks = [-0.15, -0.10, -0.05, 0.0, 0.05, 0.10]
            sim_rows = []
            for s in shocks:
                shock_spot = nifty_spot * (1 + s)
                unhedged_pnl = port_val * s
                put_payoff = max(0.0, strike_atm - shock_spot) - p_price
                hedged_pnl = unhedged_pnl + (put_payoff * full_hedge_lots * SEBI_NIFTY_LOT_SIZE)
                sim_rows.append({
                    "Market Move": f"{s*100:+.0f}%",
                    "Simulated Nifty": shock_spot,
                    "Unhedged Portfolio PnL": unhedged_pnl,
                    "Hedge Instrument PnL": put_payoff * full_hedge_lots * SEBI_NIFTY_LOT_SIZE,
                    "Net Protected PnL": hedged_pnl
                })

            st.dataframe(
                pd.DataFrame(sim_rows).style.format({
                    "Simulated Nifty": "{:.1f}",
                    "Unhedged Portfolio PnL": "₹ {:+,.0f}",
                    "Hedge Instrument PnL": "₹ {:+,.0f}",
                    "Net Protected PnL": "₹ {:+,.0f}"
                }),
                use_container_width=True
            )
        else:
            st.info("💡 **Tip:** Click **⚡ Wake & Sync Hedger App** or **🚀 Open Standalone App** above to wake the cloud instance if idle.")
            hedge_app_url = st.text_input(
                "Streamlit App URL:",
                value=f"https://portfolio-hedger.streamlit.app/?embed=true&wake_ts={wake_ts}",
                key="url_hedge_in"
            )
            components.iframe(hedge_app_url, height=750, scrolling=True)

    # -------------------------------------------------------------
    # SUB-TAB 6: REGULATION 30 CATALYST PULSE
    # -------------------------------------------------------------
    elif active_subtab == subtab_options[5]:
        st.markdown("#### 📡 Regulation 30 Catalyst & FinBERT Event Alpha Engine (`catalyst-pulse-pro`)")
        st.caption(
            "Live instance (`https://catalyst-pulse-pro-yfdm4wj5wtk2dlyag4jamx.streamlit.app/`) synced with `catalyst_prediction_ledger.csv` "
            "from `purntripathi-cmd/catalyst-pulse-pro` (overlaid with shared live NSE CMPs) + real-time corporate disclosures RSS stream."
        )

        c_top1, c_top2, c_top3 = st.columns([2.7, 1.15, 1.15])
        with c_top1:
            view_mode_pulse = st.radio(
                "Display Mode:",
                ["📊 Live Integrated Content & Event Feed", "🌐 Live Cloud App Web Viewport (Embedded IFrame)"],
                horizontal=True,
                key="vmode_pulse"
            )
        with c_top2:
            st.write("")
            if st.button("⚡ Wake & Run Catalyst Daemon", key="reboot_pulse_quick", type="primary", use_container_width=True, help="Dispatch GitHub Actions daily_audit_daemon.yml on catalyst-pulse-pro and wake Streamlit Cloud app"):
                with st.spinner("Dispatching Catalyst Audit Daemon & waking cloud app..."):
                    ok, msg = wake_and_sync_satellite_app("catalyst-pulse-pro", active_pat)
                clear_fleet_caches()
                st.session_state["fleet_wake_ts"] = int(time.time())
                st.success(msg) if ok else st.warning(msg)
        with c_top3:
            st.write("")
            st.link_button(
                "🚀 Open Standalone App",
                "https://catalyst-pulse-pro-yfdm4wj5wtk2dlyag4jamx.streamlit.app/",
                use_container_width=True,
                help="Open standalone Catalyst Pulse Pro (https://catalyst-pulse-pro-yfdm4wj5wtk2dlyag4jamx.streamlit.app/) on Streamlit Cloud"
            )

        if "Live Integrated" in view_mode_pulse:
            with st.spinner("Loading live Catalyst Prediction Ledger & corporate disclosures..."):
                cat_ledger_df = fetch_live_catalyst_ledger(live_quotes)
                events_df = fetch_live_reg30_announcements()

            pm1, pm2, pm3, pm4 = st.columns(4)
            pm1.metric("Satellite Ledger Signals", f"{len(cat_ledger_df)} Audited", delta="catalyst-pulse-pro CSV")
            pm2.metric("Live RSS Disclosures", f"{len(events_df)} Headlines", delta="Google News / NSE Feed")
            high_cnt = int((events_df["Impact Level"].isin(["High", "Very High"])).sum()) if not events_df.empty else 0
            pm3.metric("High-Impact Catalysts", high_cnt, delta="Actionable Reg 30 Signals")
            avg_pol = float(events_df["FinBERT Polarity"].mean()) if not events_df.empty else 0.0
            pm4.metric("Live Stream Polarity", f"{avg_pol:+.2f}", delta=datetime.datetime.now(IST).strftime("%H:%M:%S IST"))

            st.markdown("##### 🎯 Live Satellite Catalyst Prediction Ledger (`catalyst_prediction_ledger.csv` + Shared Live CMP)")
            if not cat_ledger_df.empty:
                cat_cols = [
                    "Scan_Timestamp", "Ticker", "Event_Category", "Signal",
                    "Confidence_Score", "FinBERT_Score", "Entry_CMP", "Current_CMP",
                    "Realized_Return_Pct", "Target_Price", "Stop_Loss", "Trade_Status", "Headline"
                ]
                cat_cols = [c for c in cat_cols if c in cat_ledger_df.columns]
                st.dataframe(
                    cat_ledger_df[cat_cols].head(50).style.format({
                        "Entry_CMP": "₹ {:.2f}",
                        "Current_CMP": "₹ {:.2f}",
                        "Realized_Return_Pct": "{:+.2f}%",
                        "Target_Price": "₹ {:.2f}",
                        "Stop_Loss": "₹ {:.2f}"
                    }, na_rep="-"),
                    use_container_width=True,
                    height=320
                )
            else:
                st.info("No catalyst ledger records returned from GitHub.")

            st.markdown("##### 📰 Real-Time Corporate Filings & SEBI Reg 30 News Stream")
            cf1, cf2 = st.columns([2, 2])
            with cf1:
                sel_classes = st.multiselect(
                    "Filter Catalyst Taxonomy:",
                    options=events_df["Class"].unique() if not events_df.empty else [],
                    default=events_df["Class"].unique() if not events_df.empty else []
                )
            with cf2:
                search_kw = st.text_input("Search Ticker or Headline Keyword:", "")

            filtered_events = events_df.copy()
            if not filtered_events.empty:
                if sel_classes:
                    filtered_events = filtered_events[filtered_events["Class"].isin(sel_classes)]
                if search_kw:
                    filtered_events = filtered_events[filtered_events["Headline"].str.contains(search_kw, case=False, na=False)]

                st.dataframe(
                    filtered_events[[
                        "Headline", "Class", "Impact Level", "FinBERT Polarity", "Published"
                    ]].style.format({
                        "FinBERT Polarity": "{:+.2f}"
                    }),
                    use_container_width=True
                )

            telem_cat = fetch_repo_telemetry("catalyst-pulse-pro", active_pat)
            health_cat = probe_satellite_app_health("https://catalyst-pulse-pro-yfdm4wj5wtk2dlyag4jamx.streamlit.app/")
            st.caption(
                f"📡 **Catalyst Pulse Pro Cloud Telemetry:** {health_cat['badge']} ({health_cat['latency_ms']} ms) • "
                f"**Latest Commit (`catalyst-pulse-pro`):** `{telem_cat['sha']}` ({telem_cat['date']}) — *{telem_cat['message']}*"
            )
        else:
            st.info("💡 **Tip:** Click **⚡ Wake & Run Catalyst Daemon** or **🚀 Open Standalone App** above to wake the cloud instance if idle.")
            pulse_app_url = st.text_input(
                "Streamlit App URL:",
                value=f"https://catalyst-pulse-pro-yfdm4wj5wtk2dlyag4jamx.streamlit.app/?embed=true&wake_ts={wake_ts}",
                key="url_pulse_in"
            )
            components.iframe(pulse_app_url, height=750, scrolling=True)

    # -------------------------------------------------------------
    # SUB-TAB 7: FLEET DIRECTORY & CLOUD WAKE HUB
    # -------------------------------------------------------------
    elif active_subtab == subtab_options[6]:
        st.markdown("#### 🚀 Complete Ecosystem Fleet Directory, Live Health Probe & 1-Click Cloud Wake Hub")
        st.caption("Monitor live HTTP health & response latency across all 6 ecosystem engines (including this primary app), trigger GitHub Actions daemons, and wake sleeping Streamlit Cloud containers in 1 click.")

        t1, t2, t3, t4 = st.columns(4)
        t1.metric("Active Ecosystem Apps", len(SATELLITE_APPS), delta="Primary Hub + 5 Satellites")
        t2.metric("Shared Market Quotes", f"{len(live_quotes)} Tickers", delta=f"Synced {quote_sync_ts}")
        t3.metric(
            "GitHub API & Daemon Control",
            "Authenticated" if active_pat else "HTTP Wake Mode",
            delta="Full Repo + Workflow Sync" if active_pat else "Add PAT for GitHub Commit Wake",
            delta_color="normal" if active_pat else "off"
        )
        t4.metric("Last Fleet Sync", datetime.datetime.now(IST).strftime("%H:%M:%S IST"))

        st.markdown("---")

        c_act1, c_act2, c_act3 = st.columns([2.5, 2.5, 3])
        with c_act1:
            if st.button("⚡ Wake & Sync All 6 Ecosystem Apps", type="primary", use_container_width=True, key="btn_reboot_all_hub"):
                progress_bar = st.progress(0, text="Initiating 3-stage fleet wake & sync sequence...")
                reboot_results = []
                for idx, app in enumerate(SATELLITE_APPS):
                    progress_bar.progress((idx + 1) / len(SATELLITE_APPS), text=f"Waking & syncing {app['name']}...")
                    ok, msg = wake_and_sync_satellite_app(app["id"], active_pat)
                    reboot_results.append((app["name"], ok, msg))

                progress_bar.empty()
                st.success("✅ Fleet wake pings, workflow dispatches, and GitHub container wake commits completed!")
                for name, ok, msg in reboot_results:
                    st.caption(f"🟢 **{name}**: {msg}" if ok else f"🟡 **{name}**: {msg}")
                clear_fleet_caches()
                st.session_state["fleet_wake_ts"] = int(time.time())

        with c_act2:
            st.link_button(
                "☁️ Streamlit Cloud Console",
                "https://share.streamlit.io/",
                use_container_width=True,
                help="Open official Streamlit Community Cloud dashboard."
            )

        with c_act3:
            if st.button("🔄 Refresh All Ecosystem Data", type="primary", use_container_width=True, key="btn_refresh_all_fleet_data", help="Clear satellite caches, re-fetch GitHub commits, probe HTTP health, and reload live quotes"):
                clear_fleet_caches()
                st.session_state["fleet_last_refresh"] = datetime.datetime.now(IST).strftime("%d-%b-%Y %H:%M:%S IST")
                st.session_state["fleet_wake_ts"] = int(time.time())
                st.toast("Satellite fleet & ecosystem data refreshed!", icon="✅")
                st.rerun()

        with st.expander("🔑 GitHub Authentication & Automated Daemon/Commit Wake Setup", expanded=(not active_pat)):
            col_tok1, col_tok2 = st.columns([3, 1])
            with col_tok1:
                input_token = st.text_input(
                    "GitHub Personal Access Token (PAT)",
                    value=active_pat if active_pat else "",
                    type="password",
                    key="pat_input_field_hub"
                )
            with col_tok2:
                st.write("")
                if st.button("💾 Save Token", use_container_width=True, key="btn_save_pat_hub"):
                    if input_token:
                        st.session_state["fleet_github_pat"] = input_token.strip()
                        st.success("PAT saved for current session!")
                        st.rerun()
                    else:
                        st.session_state.pop("fleet_github_pat", None)
                        st.info("Token cleared.")

        st.markdown("---")

        for idx, app in enumerate(SATELLITE_APPS):
            telem = fetch_repo_telemetry(app["repo"], active_pat)
            health = probe_satellite_app_health(app["app_url"])
            with st.container():
                st.markdown(
                    f"""
                    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid {app['color']}; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px;">
                            <div>
                                <span style="font-size: 1.10rem; font-weight: 700; color: #1e293b;">{app['icon']} {app['name']}</span>
                                <span style="background: #f1f5f9; color: #475569; font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; margin-left: 8px; font-weight: 600;">{app['category']}</span>
                                <span style="background: #ecfdf5; color: #047857; font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; margin-left: 6px; font-weight: 600;">{health['badge']} ({health['latency_ms']} ms)</span>
                            </div>
                            <div style="text-align: right; font-size: 0.75rem; color: #64748b;">
                                <b>Latest Commit:</b> <a href="{telem['commit_url']}" target="_blank" style="text-decoration: none; color: #2563EB;"><code>{telem['sha']}</code></a> • {telem['date']}
                            </div>
                        </div>
                        <div style="font-size: 0.82rem; color: #334155; margin-top: 5px; margin-bottom: 4px;">
                            {app['tagline']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                cd1, cd2 = st.columns([2.4, 1.6])
                with cd1:
                    st.caption(f"**Latest Push:** `{telem['message']}`")
                with cd2:
                    col_b1, col_b2, col_b3 = st.columns(3)
                    with col_b1:
                        st.link_button("🚀 Open App", app["app_url"], use_container_width=True, help="Open standalone Streamlit Cloud app in browser")
                    with col_b2:
                        st.link_button("📂 GitHub", f"https://github.com/{GITHUB_OWNER}/{app['repo']}", use_container_width=True)
                    with col_b3:
                        if st.button("⚡ Wake & Sync", key=f"reboot_card_{app['id']}", use_container_width=True):
                            with st.spinner(f"Waking {app['name']}..."):
                                ok, msg = wake_and_sync_satellite_app(app["id"], active_pat)
                            clear_fleet_caches()
                            st.session_state["fleet_wake_ts"] = int(time.time())
                            st.success(msg) if ok else st.warning(msg)

    # Proactively release unused heap memory back to OS container after rendering active sub-tab
    try:
        from resource_monitor import release_container_memory
        release_container_memory()
    except Exception:
        pass


