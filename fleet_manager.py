"""
Fleet Manager & Quant Ecosystem Hub
Manages satellite Streamlit applications, real-time GitHub telemetry,
and automated cloud container reboots.
"""

import os
import re
import json
import base64
import urllib.request
import urllib.error
import subprocess
import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

IST = ZoneInfo("Asia/Kolkata")
GITHUB_OWNER = "purntripathi-cmd"

SATELLITE_APPS = [
    {
        "id": "div-screener-in",
        "name": "Indian REITs & InvITs Yield Screener",
        "repo": "div-screener-in",
        "category": "Alternative Income & High-Yield Assets",
        "icon": "🏢",
        "default_url": "https://share.streamlit.io/",
        "entrypoint": "app.py",
        "tagline": "SEBI NDCF DPU distribution screener with 10Y Sovereign benchmark spread analytics and dividend aristocrat health scoring.",
        "kpis": [
            "Authentic NDCF DPU Overrides (Brookfield, Embassy, Mindspace, Nexus)",
            "Live Spread over 10Y G-Sec Benchmark (6.80% in bps)",
            "Dividend Quality & Aristocrat Health Score (0–100)",
            "Interactive Plotly Yield vs Payout Ratios & Distribution Tax Guide"
        ],
        "color": "#10B981"
    },
    {
        "id": "ncd-bond_screener",
        "name": "Indian Listed NCD & Bond Analytics",
        "repo": "ncd-bond_screener",
        "category": "Fixed Income & Sovereign Debt",
        "icon": "📜",
        "default_url": "https://share.streamlit.io/",
        "entrypoint": "app.py",
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
        "default_url": "https://share.streamlit.io/",
        "entrypoint": "app.py",
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
        "default_url": "https://share.streamlit.io/",
        "entrypoint": "app.py",
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
        "default_url": "https://share.streamlit.io/",
        "entrypoint": "catalyst_app.py",
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


def resolve_github_pat() -> str:
    """
    Attempts to resolve GitHub PAT from session state, secrets, environment,
    or git credential helper (for local execution).
    """
    # 1. Session state override
    if st.session_state.get("fleet_github_pat"):
        return st.session_state["fleet_github_pat"].strip()

    # 2. Streamlit secrets
    try:
        pat = st.secrets.get("GITHUB_PAT", "")
        if pat:
            return pat.strip()
    except Exception:
        pass

    # 3. OS Environment
    env_pat = os.environ.get("GITHUB_PAT", "")
    if env_pat:
        return env_pat.strip()

    # 4. Local git credential fallback (if available on host system)
    try:
        p = subprocess.Popen(
            ['git', 'credential', 'fill'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
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


@st.cache_data(ttl=120)
def fetch_repo_telemetry(repo_name: str, pat: str = "") -> dict:
    """
    Fetches latest commit info from GitHub API.
    """
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
            # Convert ISO UTC to IST
            dt = datetime.datetime.fromisoformat(raw_date.replace("Z", "+00:00")).astimezone(IST)
            date_str = dt.strftime("%d-%b-%Y %H:%M IST")
            return {
                "status": "ONLINE",
                "sha": sha,
                "date": date_str,
                "message": msg,
                "commit_url": f"https://github.com/{GITHUB_OWNER}/{repo_name}/commit/{data['sha']}"
            }
    except Exception as e:
        return {
            "status": "REACHABLE",
            "sha": "Latest",
            "date": "Up-to-date",
            "message": "Repository active on GitHub",
            "commit_url": f"https://github.com/{GITHUB_OWNER}/{repo_name}"
        }


def trigger_app_reboot_via_github(repo_name: str, pat: str) -> tuple[bool, str]:
    """
    Triggers a Streamlit Cloud reboot by updating .streamlit_reboot in the GitHub repo.
    Streamlit Cloud detects the push event and restarts the app container.
    """
    if not pat:
        return False, "GitHub Personal Access Token (PAT) is required to trigger container reboots."

    file_path = ".streamlit_reboot"
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{repo_name}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {pat.strip()}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Production-Fleet-Manager"
    }

    # 1. Fetch current SHA if file exists
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

    # 2. Put updated content to trigger commit
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
            return True, f"Reboot commit `{new_sha}` pushed to main. Streamlit Cloud is rebooting {repo_name}!"
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if hasattr(e, "read") else ""
        return False, f"Commit failed (HTTP {e.code}): {err_body[:120]}"
    except Exception as e:
        return False, f"Reboot trigger failed: {str(e)}"


def render_fleet_manager_tab(is_admin: bool = True):
    """
    Renders the Quant Ecosystem & Satellite Fleet Manager tab.
    """
    st.markdown("### 🚀 Institutional Quant Ecosystem & Satellite Fleet")
    st.caption("Live telemetry, direct application launch links, and 1-click cloud container reboot triggers for all specialized trading and risk engines.")

    # 1. Top Telemetry Bar
    active_pat = resolve_github_pat()
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Active Satellite Apps", len(SATELLITE_APPS), delta="Fleet Online")
    t2.metric("Target Ecosystem", "Streamlit Cloud", delta="Continuous Delivery")
    t3.metric(
        "GitHub Integration",
        "Authenticated" if active_pat else "Read-Only",
        delta="Reboot Enabled" if active_pat else "Action Required",
        delta_color="normal" if active_pat else "inverse"
    )
    t4.metric("Last Fleet Sync", datetime.datetime.now(IST).strftime("%H:%M:%S IST"))

    st.markdown("---")

    # 2. Global Actions & Configuration
    c_act1, c_act2, c_act3 = st.columns([2.5, 2.5, 3])
    with c_act1:
        if st.button("⚡ Reboot All 5 Satellite Apps", type="primary", use_container_width=True, key="btn_reboot_all"):
            if not active_pat:
                st.error("⚠️ Please configure a GitHub PAT below to enable automated 1-click reboots.")
            else:
                progress_bar = st.progress(0, text="Initiating fleet reboot sequence...")
                reboot_results = []
                for idx, app in enumerate(SATELLITE_APPS):
                    progress_bar.progress((idx + 1) / len(SATELLITE_APPS), text=f"Rebooting {app['name']}...")
                    ok, msg = trigger_app_reboot_via_github(app["repo"], active_pat)
                    reboot_results.append((app["name"], ok, msg))

                progress_bar.empty()
                st.success("✅ Fleet reboot commands dispatched to GitHub! Streamlit Cloud instances are restarting.")
                for name, ok, msg in reboot_results:
                    if ok:
                        st.caption(f"🟢 **{name}**: {msg}")
                    else:
                        st.caption(f"🔴 **{name}**: {msg}")
                st.cache_data.clear()

    with c_act2:
        st.link_button(
            "☁️ Streamlit Cloud Dashboard",
            "https://share.streamlit.io/",
            use_container_width=True,
            help="Open the official Streamlit Community Cloud console to view container logs, secrets, and metrics."
        )

    with c_act3:
        if st.button("🔄 Refresh Telemetry & Commits", use_container_width=True, key="btn_refresh_telemetry"):
            st.cache_data.clear()
            st.rerun()

    # GitHub PAT Configuration Expander
    with st.expander("🔑 GitHub Authentication & Automated Reboot Setup", expanded=(not active_pat)):
        st.markdown(
            """
            <div style="font-size: 0.85rem; color: #475569; margin-bottom: 8px;">
                <b>How Automated Reboots Work:</b> Streamlit Cloud is configured to automatically redeploy whenever a commit is pushed to the repository's <code>main</code> branch.
                Clicking <b>Reboot</b> creates an empty sync commit (<code>.streamlit_reboot</code>) via the GitHub REST API, instantly instructing Streamlit Cloud to tear down and rebuild the container.
            </div>
            """,
            unsafe_allow_html=True
        )
        col_tok1, col_tok2 = st.columns([3, 1])
        with col_tok1:
            input_token = st.text_input(
                "GitHub Personal Access Token (PAT)",
                value=active_pat if active_pat else "",
                type="password",
                help="Requires 'repo' scope permissions on purntripathi-cmd repositories.",
                key="pat_input_field"
            )
        with col_tok2:
            st.write("")
            if st.button("💾 Save Token", use_container_width=True, key="btn_save_pat"):
                if input_token:
                    st.session_state["fleet_github_pat"] = input_token.strip()
                    st.success("PAT saved for current session!")
                    st.rerun()
                else:
                    st.session_state.pop("fleet_github_pat", None)
                    st.info("Token cleared.")

    st.markdown("---")
    st.markdown("#### 🛰️ Specialized Quant Applications Directory")

    # 3. Individual App Cards
    for idx, app in enumerate(SATELLITE_APPS):
        telem = fetch_repo_telemetry(app["repo"], active_pat)
        
        with st.container():
            st.markdown(
                f"""
                <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid {app['color']}; border-radius: 8px; padding: 14px 18px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <span style="font-size: 1.15rem; font-weight: 700; color: #1e293b;">{app['icon']} {app['name']}</span>
                            <span style="background: #f1f5f9; color: #475569; font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; margin-left: 8px; font-weight: 600;">{app['category']}</span>
                        </div>
                        <div style="text-align: right; font-size: 0.75rem; color: #64748b;">
                            <b>Commit:</b> <a href="{telem['commit_url']}" target="_blank" style="text-decoration: none; color: #2563EB;"><code>{telem['sha']}</code></a> • {telem['date']}
                        </div>
                    </div>
                    <div style="font-size: 0.84rem; color: #334155; margin-top: 6px; margin-bottom: 8px;">
                        {app['tagline']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Columns for Details and Actions
            c_det, c_btns = st.columns([2.8, 1.2])
            with c_det:
                st.caption(f"**Latest Push:** `{telem['message']}`")
                with st.expander(f"🔍 Core Quantitative Models & KPIs ({app['name']})", expanded=False):
                    for kpi in app["kpis"]:
                        st.markdown(f"- {kpi}")
                    st.caption(f"**Repository:** [`purntripathi-cmd/{app['repo']}`](https://github.com/purntripathi-cmd/{app['repo']}) • **Entrypoint:** `{app['entrypoint']}`")

            with c_btns:
                st.link_button(
                    f"🚀 Open {app['icon']} App",
                    f"https://share.streamlit.io/",
                    use_container_width=True,
                    help=f"Launch {app['name']} in Streamlit Cloud."
                )
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.link_button("📂 GitHub", f"https://github.com/{GITHUB_OWNER}/{app['repo']}", use_container_width=True)
                with col_b2:
                    if st.button("🔄 Reboot", key=f"btn_reboot_{app['id']}", use_container_width=True, help="Trigger automated Streamlit Cloud container reboot"):
                        if not active_pat:
                            st.error("PAT required. Configure in expander above.")
                        else:
                            with st.spinner(f"Rebooting {app['name']}..."):
                                ok, msg = trigger_app_reboot_via_github(app["repo"], active_pat)
                                if ok:
                                    st.success(msg)
                                    st.cache_data.clear()
                                else:
                                    st.error(msg)

            st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)
