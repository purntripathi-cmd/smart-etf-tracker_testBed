"""
AGY QUANT PLATFORM V2: TELEGRAM NOTIFIER & TESTING MODULE
Handles Telegram Bot configuration, API connectivity tests, and signal alert formatting.
Supports:
- S/R Range-Bound Lab alerts (Support Bounces, Range Breakouts)
- Paper Trading execution & exit notifications
- Interactive GUI test triggers and bot verification
"""

import os
import json
import logging
import requests
from datetime import datetime
import zoneinfo

logger = logging.getLogger("v2.telegram_notifier")
IST = zoneinfo.ZoneInfo("Asia/Kolkata")

RUNTIME_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "runtime_config.json")


def get_telegram_config():
    """
    Retrieves Telegram Bot Token and Chat ID from multiple priority sources:
    1. Streamlit Secrets (st.secrets) if running within Streamlit
    2. Environment Variables (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    3. runtime_config.json under 'telegram' section
    """
    token = ""
    chat_id = ""
    enabled = True
    source = "unconfigured"

    # 1. Try Streamlit Secrets (Most Secure for Public Cloud)
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            s_tok = st.secrets.get("TELEGRAM_BOT_TOKEN", "") or st.secrets.get("telegram", {}).get("bot_token", "")
            s_chat = st.secrets.get("TELEGRAM_CHAT_ID", "") or st.secrets.get("telegram", {}).get("chat_id", "")
            if s_tok:
                token = str(s_tok).strip()
                source = "Streamlit Secrets (Encrypted Server-Side Vault)"
            if s_chat:
                chat_id = str(s_chat).strip()
    except Exception:
        pass

    # 2. Try Environment Variables
    if not token and os.getenv("TELEGRAM_BOT_TOKEN"):
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        source = "Environment Variable"
    if not chat_id and os.getenv("TELEGRAM_CHAT_ID"):
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    # 3. Try runtime_config.json
    if os.path.exists(RUNTIME_CONFIG_PATH):
        try:
            with open(RUNTIME_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                tg_cfg = cfg.get("telegram", {})
                if not token and tg_cfg.get("bot_token"):
                    token = str(tg_cfg.get("bot_token", "")).strip()
                    source = "Local Runtime Config"
                if not chat_id and tg_cfg.get("chat_id"):
                    chat_id = str(tg_cfg.get("chat_id", "")).strip()
                enabled = tg_cfg.get("enabled", True)
        except Exception as e:
            logger.warning(f"Error reading runtime_config.json for telegram: {e}")

    # Keep chat_id empty if not configured so user is guided to link it
    if not chat_id:
        chat_id = ""

    masked = ""
    if token and len(token) >= 8:
        masked = token[:4] + "••••••••" + token[-4:]

    return {
        "bot_token": token.strip(),
        "chat_id": chat_id.strip(),
        "enabled": enabled,
        "is_configured": bool(token.strip() and chat_id.strip()),
        "source": source,
        "masked_token": masked
    }


def save_telegram_config(bot_token, chat_id, enabled=True):
    """Saves Telegram configuration to runtime_config.json for GUI persistence."""
    try:
        cfg = {}
        if os.path.exists(RUNTIME_CONFIG_PATH):
            with open(RUNTIME_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)

        if "telegram" not in cfg:
            cfg["telegram"] = {}

        if bot_token and str(bot_token).strip():
            cfg["telegram"]["bot_token"] = str(bot_token).strip()
        if chat_id is not None:
            cfg["telegram"]["chat_id"] = str(chat_id).strip()
        cfg["telegram"]["enabled"] = enabled

        with open(RUNTIME_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Failed to save telegram config: {e}")
        return False


def test_bot_connection(bot_token=None):
    """
    Tests bot token connectivity by calling Telegram's getMe endpoint.
    Returns: {"ok": bool, "bot_name": str, "username": str, "error": str}
    """
    token = bot_token or get_telegram_config()["bot_token"]
    if not token:
        return {"ok": False, "bot_name": "", "username": "", "error": "Bot Token is missing or empty."}

    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if resp.status_code == 200 and data.get("ok"):
            result = data.get("result", {})
            return {
                "ok": True,
                "bot_name": result.get("first_name", "Telegram Bot"),
                "username": result.get("username", ""),
                "id": result.get("id", ""),
                "error": ""
            }
        else:
            return {
                "ok": False,
                "bot_name": "",
                "username": "",
                "error": data.get("description", f"HTTP {resp.status_code}")
            }
    except requests.exceptions.Timeout:
        return {"ok": False, "bot_name": "", "username": "", "error": "Connection timed out (10s). Check internet or firewall."}
    except Exception as e:
        return {"ok": False, "bot_name": "", "username": "", "error": str(e)}


def fetch_latest_chat_id(bot_token=None):
    """
    Queries Telegram getUpdates API to automatically detect the exact Chat ID
    of the most recent user, group, or channel that messaged or interacted with the bot.
    """
    token = bot_token or get_telegram_config().get("bot_token", "")
    if not token:
        return {"ok": False, "chat_id": "", "chat_name": "", "error": "Bot Token is missing or empty."}

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        resp = requests.get(url, params={"limit": 20, "timeout": 5}, timeout=10)
        data = resp.json()
        if not data.get("ok"):
            err_desc = data.get("description", f"HTTP {resp.status_code}")
            # If webhook is active, auto-remove it so getUpdates can function
            if "webhook" in err_desc.lower() and "conflict" in err_desc.lower():
                try:
                    requests.post(f"https://api.telegram.org/bot{token}/deleteWebhook", timeout=6)
                    resp = requests.get(url, params={"limit": 20, "timeout": 5}, timeout=10)
                    data = resp.json()
                except Exception:
                    pass
            if not data.get("ok"):
                return {"ok": False, "chat_id": "", "chat_name": "", "error": f"Telegram API error: {err_desc}"}

        results = data.get("result", [])
        if not results:
            return {
                "ok": False,
                "chat_id": "",
                "chat_name": "",
                "error": "No recent updates found for @TAPscreenerbot. Please open Telegram, search for @TAPscreenerbot, send /start or type 'hello', and click Detect Chat ID again."
            }

        for item in reversed(results):
            msg = item.get("message") or item.get("channel_post") or item.get("my_chat_member")
            if msg and "chat" in msg:
                chat = msg["chat"]
                cid = str(chat.get("id"))
                cname = chat.get("title") or chat.get("first_name", "Telegram User")
                username = f" (@{chat.get('username')})" if chat.get("username") else ""
                ctype = chat.get("type", "private")
                return {
                    "ok": True,
                    "chat_id": cid,
                    "chat_name": f"{cname}{username}",
                    "chat_type": ctype,
                    "error": ""
                }

        return {
            "ok": False,
            "chat_id": "",
            "chat_name": "",
            "error": "No active chat events found in recent bot updates."
        }
    except Exception as e:
        return {"ok": False, "chat_id": "", "chat_name": "", "error": str(e)}


def send_telegram_message(message_text, bot_token=None, chat_id=None):
    """
    Dispatches an HTML-formatted message to the specified Telegram Chat ID.
    Returns: {"ok": bool, "message_id": int, "error": str}
    """
    cfg = get_telegram_config()
    token = (str(bot_token).strip() if bot_token else "") or cfg.get("bot_token", "")
    target_chat = (str(chat_id).strip() if chat_id else "") or cfg.get("chat_id", "")

    if not token or not target_chat:
        return {"ok": False, "message_id": 0, "error": "Bot Token or Chat ID is not configured."}

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": str(target_chat).strip(),
        "text": message_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        resp = requests.post(url, json=payload, timeout=12)
        data = resp.json()
        if resp.status_code == 200 and data.get("ok"):
            msg_id = data.get("result", {}).get("message_id", 0)
            logger.info(f"Telegram message dispatched successfully (ID: {msg_id})")
            return {"ok": True, "message_id": msg_id, "error": ""}
        else:
            err_msg = data.get("description", f"HTTP {resp.status_code}")
            if "chat not found" in err_msg.lower():
                err_msg = f"{err_msg}. (Resolution: Open this bot in Telegram and click START (/start) so the bot has permission to message you, or if posting to a group/channel, add the bot as Administrator)."
            logger.warning(f"Telegram dispatch failed: {err_msg}")
            return {"ok": False, "message_id": 0, "error": err_msg}
    except requests.exceptions.Timeout:
        return {"ok": False, "message_id": 0, "error": "Telegram API timed out (12s)."}
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
        return {"ok": False, "message_id": 0, "error": str(e)}


def format_sr_alert(
    ticker,
    cmp_val,
    s1,
    s2,
    r1,
    r2,
    range_pos,
    win_rate,
    action,
    target,
    sl,
    note=None,
    company_name=None
):
    """
    Formats a high-impact, visual Telegram alert for Support & Resistance Lab signals.
    """
    now_str = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    clean_sym = str(ticker).replace(".NS", "").strip()
    name_str = f" ({company_name})" if company_name else ""

    # Choose header emoji based on action
    if "BUY" in action or "ACCUMULATE" in action:
        header_icon = "🟢"
        action_badge = f"<b>{action}</b> (Support Accumulation)"
    elif "SELL" in action or "DISTRIBUTION" in action:
        header_icon = "🔴"
        action_badge = f"<b>{action}</b> (Resistance Exit)"
    elif "BREAKOUT" in action:
        header_icon = "🚀"
        action_badge = f"<b>{action}</b> (Momentum Expansion)"
    else:
        header_icon = "🟡"
        action_badge = f"<b>{action}</b> (Channel Midline)"

    # Target & SL upside/downside %
    tgt_pct_str = f" (+{((target - cmp_val)/cmp_val*100):.1f}%)" if cmp_val > 0 and target > cmp_val else ""
    sl_pct_str = f" ({((sl - cmp_val)/cmp_val*100):.1f}%)" if cmp_val > 0 and sl < cmp_val else ""

    msg = f"""{header_icon} <b>[AGY QUANT LAB] S/R Signal Alert</b>
━━━━━━━━━━━━━━━━━━━━
🎯 <b>Asset:</b> <code>{clean_sym}</code>{name_str}
💰 <b>Current Price (CMP):</b> ₹{cmp_val:,.2f}
📊 <b>Action Signal:</b> {action_badge}

📉 <b>Immediate Support (S1):</b> ₹{s1:,.2f}
🧱 <b>Structural Floor (S2):</b> ₹{s2:,.2f}
📈 <b>Immediate Resistance (R1):</b> ₹{r1:,.2f}
🏛️ <b>Structural Ceiling (R2):</b> ₹{r2:,.2f}

📍 <b>Channel Range Position:</b> <b>{range_pos:.1f}%</b>
🏆 <b>5-Year S/R Win Rate:</b> <b>{win_rate:.1f}%</b>

🎯 <b>Suggested Target:</b> ₹{target:,.2f}{tgt_pct_str}
🛑 <b>Suggested Stop-Loss:</b> ₹{sl:,.2f}{sl_pct_str}
━━━━━━━━━━━━━━━━━━━━"""

    if note:
        msg += f"\n💡 <i>Note: {note}</i>"

    msg += f"\n⏱️ <i>AGY Tactical Platform • {now_str}</i>"
    return msg


def format_paper_trade_alert(trade_dict, action_type="ENTRY"):
    """
    Formats a clean Telegram alert when a paper trade is executed or exited.
    """
    now_str = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    sym = trade_dict.get("Ticker", "UNKNOWN")
    preset = trade_dict.get("Strategy_Preset", "Standard")
    price = float(trade_dict.get("Entry_Price", trade_dict.get("Live_CMP", 0.0)))
    qty = trade_dict.get("Executed_Qty", 1)
    inv_val = float(trade_dict.get("Invested_Value", price * qty))
    sl = float(trade_dict.get("Stop_Loss", 0.0))
    tgt = float(trade_dict.get("Target", 0.0))

    empirical_win = trade_dict.get("Empirical_Win_Rate_At_Entry", "")
    rating = trade_dict.get("Predictability_Rating", "")
    win_rate_line = f"\n📊 <b>5Y Empirical Win Rate:</b> <b>{empirical_win}</b> ({rating})" if empirical_win else ""

    if action_type == "ENTRY":
        msg = f"""🟢 <b>[PAPER TRADE EXECUTED] New Position</b>
━━━━━━━━━━━━━━━━━━━━
🎯 <b>Ticker:</b> <code>{sym}</code> ({trade_dict.get('Asset_Class', 'Stock')})
⚙️ <b>Strategy:</b> {preset}
💵 <b>Entry Price:</b> ₹{price:,.2f}
📦 <b>Quantity:</b> {qty} units (₹{inv_val:,.2f})
🛑 <b>Stop-Loss:</b> ₹{sl:,.2f}
🎯 <b>Target:</b> ₹{tgt:,.2f}{win_rate_line}
🏷️ <b>Trade ID:</b> <code>{trade_dict.get('Trade_ID', 'N/A')}</code>
━━━━━━━━━━━━━━━━━━━━
⏱️ <i>Executed at {now_str}</i>"""
    else:
        pnl_rs = float(trade_dict.get("PnL_Rs", 0.0) or 0.0)
        raw_pnl_pct = trade_dict.get("PnL_Pct", 0.0)
        try:
            pnl_pct = float(str(raw_pnl_pct).replace("%", "").strip())
        except Exception:
            pnl_pct = 0.0
        pnl_icon = "💰" if pnl_rs >= 0 else "🛑"
        exit_p = float(trade_dict.get("Exit_Price", price))
        reason = trade_dict.get("Exit_Reason", "System Exit")

        msg = f"""{pnl_icon} <b>[PAPER TRADE CLOSED] Position Exit</b>
━━━━━━━━━━━━━━━━━━━━
🎯 <b>Ticker:</b> <code>{sym}</code>
⚙️ <b>Strategy:</b> {preset}
🚪 <b>Exit Price:</b> ₹{exit_p:,.2f} | <b>Reason:</b> {reason}
📈 <b>Realized PnL:</b> ₹{pnl_rs:+,.2f} ({pnl_pct:+.2f}%)
⏱️ <b>Hold Duration:</b> {trade_dict.get('Hold_Duration_Days', 0)} days
🏷️ <b>Trade ID:</b> <code>{trade_dict.get('Trade_ID', 'N/A')}</code>
━━━━━━━━━━━━━━━━━━━━
⏱️ <i>Closed at {now_str}</i>"""

    return msg


def compute_market_situation_summary(raw_data=None, stocks_market_df=None):
    """
    Computes concise indication of Market situation across key benchmarks:
    - Nifty 50 (^NSEI): latest price and 1D percentage change
    - NIFTY 250: average 1D change across stock universe or HDFCSML250.NS
    - Nifty 500 (^CRSLDX): broad market 1D percentage change
    - India VIX (^INDIAVIX): volatility level

    Returns list of markdown-formatted lines for Telegram alerts.
    """
    import pandas as pd
    try:
        from strategy_engine import extract_ticker_df
    except Exception:
        def extract_ticker_df(raw, t):
            if raw is None or (isinstance(raw, pd.DataFrame) and raw.empty):
                return pd.DataFrame()
            if hasattr(raw.columns, "levels") and len(raw.columns.levels) > 1:
                clean_t = t.replace(".NS", "")
                for c in [t, clean_t, f"{clean_t}.NS"]:
                    if c in raw.columns.levels[0]:
                        return raw[c].copy()
            return pd.DataFrame()

    n50_cmp, n50_chg = None, None
    n250_chg = None
    n500_cmp, n500_chg = None, None
    vix_val = None

    if raw_data is not None:
        try:
            sub_50 = extract_ticker_df(raw_data, '^NSEI')
            if not sub_50.empty and 'Close' in sub_50.columns:
                c = sub_50['Close'].dropna()
                if len(c) >= 2:
                    n50_cmp = float(c.iloc[-1])
                    n50_chg = ((c.iloc[-1] - c.iloc[-2]) / c.iloc[-2]) * 100.0

            sub_500 = extract_ticker_df(raw_data, '^CRSLDX')
            if not sub_500.empty and 'Close' in sub_500.columns:
                c = sub_500['Close'].dropna()
                if len(c) >= 2:
                    n500_cmp = float(c.iloc[-1])
                    n500_chg = ((c.iloc[-1] - c.iloc[-2]) / c.iloc[-2]) * 100.0

            sub_vix = extract_ticker_df(raw_data, '^INDIAVIX')
            if not sub_vix.empty and 'Close' in sub_vix.columns:
                c = sub_vix['Close'].dropna()
                if len(c) >= 1:
                    vix_val = float(c.iloc[-1])

            if stocks_market_df is not None and not stocks_market_df.empty and '1D Return %' in stocks_market_df.columns:
                ret_s = pd.to_numeric(stocks_market_df['1D Return %'].astype(str).str.replace('%', '').str.replace('+', ''), errors='coerce').dropna()
                if len(ret_s) >= 5:
                    n250_chg = float(ret_s.mean())

            if n250_chg is None:
                sub_250 = extract_ticker_df(raw_data, 'HDFCSML250.NS')
                if not sub_250.empty and 'Close' in sub_250.columns:
                    c = sub_250['Close'].dropna()
                    if len(c) >= 2:
                        n250_chg = ((c.iloc[-1] - c.iloc[-2]) / c.iloc[-2]) * 100.0
        except Exception as e:
            logger.debug(f"Error extracting market situation from raw_data: {e}")

    if n50_chg is None:
        try:
            import yfinance as yf
            bench_raw = yf.download(['^NSEI', '^CRSLDX', '^INDIAVIX', 'HDFCSML250.NS'], period='5d', interval='1d', progress=False)
            if not bench_raw.empty:
                sub_50 = extract_ticker_df(bench_raw, '^NSEI')
                if not sub_50.empty and 'Close' in sub_50.columns:
                    c = sub_50['Close'].dropna()
                    if len(c) >= 2:
                        n50_cmp = float(c.iloc[-1])
                        n50_chg = ((c.iloc[-1] - c.iloc[-2]) / c.iloc[-2]) * 100.0

                sub_500 = extract_ticker_df(bench_raw, '^CRSLDX')
                if not sub_500.empty and 'Close' in sub_500.columns:
                    c = sub_500['Close'].dropna()
                    if len(c) >= 2:
                        n500_cmp = float(c.iloc[-1])
                        n500_chg = ((c.iloc[-1] - c.iloc[-2]) / c.iloc[-2]) * 100.0

                sub_v = extract_ticker_df(bench_raw, '^INDIAVIX')
                if not sub_v.empty and 'Close' in sub_v.columns:
                    c = sub_v['Close'].dropna()
                    if len(c) >= 1:
                        vix_val = float(c.iloc[-1])

                if n250_chg is None:
                    sub_250 = extract_ticker_df(bench_raw, 'HDFCSML250.NS')
                    if not sub_250.empty and 'Close' in sub_250.columns:
                        c = sub_250['Close'].dropna()
                        if len(c) >= 2:
                            n250_chg = ((c.iloc[-1] - c.iloc[-2]) / c.iloc[-2]) * 100.0
        except Exception as e:
            logger.debug(f"Error fetching benchmark fallback: {e}")

    def _fmt(name, pct, cmp_val=None):
        if pct is None:
            return f"{name} data pending"
        dir_w = "up by" if pct > 0 else ("down by" if pct < 0 else "flat at")
        abs_p = abs(pct)
        cmp_s = f" ({cmp_val:,.0f})" if cmp_val is not None and cmp_val > 0 else ""
        return f"{name} {dir_w} {abs_p:.1f}%{cmp_s}"

    lines = ["🌐 *Market Situation:*"]
    l1 = f"• {_fmt('Nifty 50', n50_chg, n50_cmp)}, {_fmt('NIFTY 250', n250_chg)}"
    lines.append(l1)
    if n500_chg is not None or vix_val is not None:
        v_str = f" | India VIX: {vix_val:.1f}" if vix_val is not None else ""
        l2 = f"• {_fmt('Nifty 500', n500_chg)}{v_str}"
        lines.append(l2)

    return lines


def compute_preset_performance_summary(trades_df=None):
    """
    Computes brief success rate summary across strategy presets for the 3 PM message:
    e.g. Default: 40% success rate, Long term: 60% success rate etc. in brief manner.
    """
    import pandas as pd
    if trades_df is None:
        try:
            trades_path = os.path.join(os.path.dirname(__file__), "data", "paper_trades.csv")
            if not os.path.exists(trades_path):
                trades_path = os.path.join(os.path.dirname(__file__), "data", "paper_trading_ledger.csv")
            if os.path.exists(trades_path):
                trades_df = pd.read_csv(trades_path)
            else:
                trades_df = pd.DataFrame()
        except Exception:
            trades_df = pd.DataFrame()

    if trades_df is None or trades_df.empty:
        return [
            "🎯 *Preset Performance (Success Rates):*",
            "• All Presets: Pending execution"
        ]

    try:
        from strategy_engine import compute_multi_timeframe_performance
        res = compute_multi_timeframe_performance(trades_df)
        preset_df = res.get("preset_df", pd.DataFrame())
    except Exception:
        preset_df = pd.DataFrame()

    if preset_df.empty:
        return [
            "🎯 *Preset Performance (Success Rates):*",
            "• All Presets: Pending execution"
        ]

    def _parse_leading_int(val):
        try:
            s = str(val).split("(")[0].replace(",", "").strip()
            return int(float(s)) if s else 0
        except Exception:
            return 0

    def _parse_float(val):
        try:
            s = str(val).replace("₹", "").replace(",", "").replace("+", "").strip()
            return float(s) if s else 0.0
        except Exception:
            return 0.0

    items = []
    for _, r in preset_df.iterrows():
        p_name = str(r.get("Strategy Preset", "")).strip()
        short_name = p_name
        if "Swing" in p_name:
            short_name = "Swing / Positional"
        elif "Apex" in p_name:
            short_name = "Apex Multi-Factor"
        elif "AI" in p_name:
            short_name = "AI / RAG"
        elif "Long" in p_name:
            short_name = "Long-Term"

        wr = str(r.get("Win Rate %", "Pending")).strip()
        tot_c = _parse_leading_int(r.get("Closed", 0))
        pnl = _parse_float(r.get("Total PnL (₹)", 0.0))

        if not wr.startswith("Pending") and tot_c > 0:
            # Format integer percentage if no fractional part (handles e.g. '47.1% (8/17)')
            try:
                wr_clean = wr.split("(")[0].replace("%", "").strip()
                wr_num = float(wr_clean)
                wr_fmt = f"{int(round(wr_num))}%" if abs(wr_num - round(wr_num)) < 0.05 else f"{wr_num:.1f}%"
            except Exception:
                wr_fmt = wr
            pnl_tag = f" (₹{pnl:+,.0f})" if abs(pnl) >= 1 else ""
            items.append(f"• {short_name}: {wr_fmt} success rate{pnl_tag}")
        else:
            act = _parse_leading_int(r.get("Active", 0))
            if act > 0:
                items.append(f"• {short_name}: Pending ({act} active)")
            else:
                items.append(f"• {short_name}: Pending (0 closed)")

    return ["🎯 *Preset Performance (Success Rates):*"] + items


def compute_today_intraday_pnl_summary(trades_df=None, signals_list=None, now_ist=None):
    """
    Computes final profit or loss details on all intraday trades executed today for the 3:10 PM message:
    e.g. loss of Rs. 150 or profit of Rs. 150 in today's intraday trade.
    """
    import pandas as pd
    if now_ist is None:
        now_ist = datetime.now(IST)
    today_str = now_ist.strftime("%Y-%m-%d")

    if trades_df is None:
        try:
            trades_path = os.path.join(os.path.dirname(__file__), "data", "paper_trades.csv")
            if not os.path.exists(trades_path):
                trades_path = os.path.join(os.path.dirname(__file__), "data", "paper_trading_ledger.csv")
            if os.path.exists(trades_path):
                trades_df = pd.read_csv(trades_path)
            else:
                trades_df = pd.DataFrame()
        except Exception:
            trades_df = pd.DataFrame()

    today_intra = pd.DataFrame()
    if trades_df is not None and not trades_df.empty:
        df = trades_df.copy()
        ts_col = df["Execution_Timestamp"].astype(str)
        trig_col = df["Trigger_Type"].fillna("").astype(str).str.upper()
        preset_col = df["Strategy_Preset"].fillna("").astype(str).str.upper()
        tid_col = df["Trade_ID"].fillna("").astype(str)
        is_intra = trig_col.str.contains("INTRADAY") | preset_col.str.contains("INTRADAY") | tid_col.str.startswith("INTRA_")
        is_today = ts_col.str.contains(today_str)
        today_intra = df[is_intra & is_today]
        if today_intra.empty:
            exit_ts_col = df["Exit_Timestamp"].fillna("").astype(str)
            today_intra = df[is_intra & exit_ts_col.str.contains(today_str)]

    if today_intra.empty and signals_list:
        pnl_sum = sum([float(s.get("pnl_rs", 0.0)) for s in signals_list])
        cnt = len(signals_list)
        pnl_abs = abs(pnl_sum)
        pnl_str = f"{int(round(pnl_abs)):,}" if abs(pnl_abs - round(pnl_abs)) < 0.05 else f"{pnl_abs:,.2f}"
        if pnl_sum > 0:
            return {
                "net_pnl": pnl_sum,
                "trade_count": cnt,
                "summary_line": f"🚀 *Profit of Rs. {pnl_str}* in today's intraday trade (+₹{pnl_sum:,.2f} across {cnt} trades)"
            }
        elif pnl_sum < 0:
            return {
                "net_pnl": pnl_sum,
                "trade_count": cnt,
                "summary_line": f"🛑 *Loss of Rs. {pnl_str}* in today's intraday trade (-₹{pnl_abs:,.2f} across {cnt} trades)"
            }
        else:
            return {
                "net_pnl": 0.0,
                "trade_count": cnt,
                "summary_line": f"⚖️ *Breakeven (Rs. 0)* in today's intraday trade"
            }

    if today_intra.empty:
        return {
            "net_pnl": 0.0,
            "trade_count": 0,
            "summary_line": "• No intraday trades executed today."
        }

    pnl_series = pd.to_numeric(today_intra["PnL_Rs"], errors="coerce").fillna(0.0)
    net_pnl = round(float(pnl_series.sum()), 2)
    tot_trades = len(today_intra)
    pnl_abs = abs(net_pnl)
    pnl_str = f"{int(round(pnl_abs)):,}" if abs(pnl_abs - round(pnl_abs)) < 0.05 else f"{pnl_abs:,.2f}"

    if net_pnl > 0:
        return {
            "net_pnl": net_pnl,
            "trade_count": tot_trades,
            "summary_line": f"🚀 *Profit of Rs. {pnl_str}* in today's intraday trade (+₹{net_pnl:,.2f} across {tot_trades} trades)"
        }
    elif net_pnl < 0:
        return {
            "net_pnl": net_pnl,
            "trade_count": tot_trades,
            "summary_line": f"🛑 *Loss of Rs. {pnl_str}* in today's intraday trade (-₹{pnl_abs:,.2f} across {tot_trades} trades)"
        }
    else:
        return {
            "net_pnl": 0.0,
            "trade_count": tot_trades,
            "summary_line": f"⚖️ *Breakeven (Rs. 0)* in today's intraday trade"
        }


def send_concise_telegram_alert(trade_type, signals_list, raw_data=None, stocks_market_df=None, trades_df=None):
    """
    Sends structured Telegram alerts with:
    1. Header badge
    2. Market Situation indication in ALL messages (Nifty 50, NIFTY 250, Nifty 500, India VIX)
    3. Performance of each preset at 3 PM message
    4. Final profit or loss on all intraday trades at 3:10 PM message
    5. Detailed trade / square-off execution breakdown
    """
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = str(os.getenv("TELEGRAM_CHAT_ID", "887870969")).strip()

    try:
        import streamlit as st
        if not tg_token and hasattr(st, "secrets") and "TELEGRAM_BOT_TOKEN" in st.secrets:
            tg_token = str(st.secrets["TELEGRAM_BOT_TOKEN"]).strip()
        if (not tg_chat or tg_chat == "887870969") and hasattr(st, "secrets") and "TELEGRAM_CHAT_ID" in st.secrets:
            tg_chat = str(st.secrets["TELEGRAM_CHAT_ID"]).strip()
    except Exception:
        pass

    if not tg_token:
        try:
            cfg = get_telegram_config()
            if cfg.get("bot_token"):
                tg_token = cfg["bot_token"]
            if cfg.get("chat_id") and (not tg_chat or tg_chat == "887870969"):
                tg_chat = cfg["chat_id"]
        except Exception:
            pass

    if not tg_token or tg_token in ["YOUR_BOT_TOKEN", "<YOUR_BOT_TOKEN>"] or not tg_chat:
        logger.warning("[WARN-TELEGRAM] Telegram token or chat ID missing. Alert skipped.")
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

    # Market Situation (Included across all messages: 9:45 AM, 3:00 PM, 3:10 PM, etc.)
    try:
        market_lines = compute_market_situation_summary(raw_data=raw_data, stocks_market_df=stocks_market_df)
        if market_lines:
            msg_lines.extend(market_lines)
            msg_lines.append("")
    except Exception as e:
        logger.warning(f"[WARN-TELEGRAM] Market situation summary skipped: {e}")

    # 3 PM Message: Include brief performance indication of each preset
    if trade_type in ['Swing / Long-Term (3 PM)', '3PM', '3 PM']:
        try:
            preset_lines = compute_preset_performance_summary(trades_df=trades_df)
            if preset_lines:
                msg_lines.extend(preset_lines)
                msg_lines.append("")
        except Exception as e:
            logger.warning(f"[WARN-TELEGRAM] Preset performance summary skipped: {e}")

    # 3:10 PM Message: Include final profit or loss details on all intraday trades
    if trade_type in ['Intraday Exit', 'INTRADAY_SQUAREOFF']:
        try:
            intraday_pnl_info = compute_today_intraday_pnl_summary(trades_df=trades_df, signals_list=signals_list)
            if intraday_pnl_info and "summary_line" in intraday_pnl_info:
                msg_lines.append("📊 *Today's Intraday Result:*")
                msg_lines.append(intraday_pnl_info["summary_line"])
                msg_lines.append("")
        except Exception as e:
            logger.warning(f"[WARN-TELEGRAM] Intraday PnL summary skipped: {e}")

    # Positions Breakdown
    if trade_type in ['Intraday Exit', 'INTRADAY_SQUAREOFF']:
        if not signals_list:
            msg_lines.append("• No active intraday positions were open to square off at 3:10 PM.")
        else:
            msg_lines.append(f"📦 *Positions Squared Off (3:10 PM):* {len(signals_list)} Positions")
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
            msg_lines.append(f"{pnl_tot_icon} *Total Realized 3:10 PM Square-off PnL:* ₹{total_realized_pnl:+,.2f}")

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
            for sig in signals_list:
                ticker = str(sig.get('ticker', '')).replace('.NS', '')
                cmp = float(sig.get('cmp', 0.0))
                action = str(sig.get('action', 'BUY')).upper()
                source = str(sig.get('source', 'Quant'))
                preset = str(sig.get('preset', ''))
                icon = '🟢' if action == 'BUY' else ('🔴' if action in ['SELL', 'SQUARE-OFF'] else '🔄')
                ai_tag = ' 🤖[AI]' if 'AI' in source else ''
                preset_tag = f" [{preset}]" if preset else ""
                msg_lines.append(f"{icon} `{ticker}` | ₹{cmp:,.2f} | *{action}*{ai_tag}{preset_tag} ({source})")

    url = f"https://api.telegram.org/bot{tg_token}/sendMessage" if not tg_token.startswith("bot") else f"https://api.telegram.org/{tg_token}/sendMessage"
    payload = {"chat_id": tg_chat, "text": "\n".join(msg_lines), "parse_mode": "Markdown"}

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            logger.warning(f"[WARN-TELEGRAM] Markdown send returned {response.status_code}, retrying without parse_mode: {response.text}")
            fallback_payload = {"chat_id": tg_chat, "text": "\n".join(msg_lines).replace("*", "").replace("`", "")}
            response = requests.post(url, json=fallback_payload, timeout=10)
            if response.status_code != 200:
                logger.error(f"[ERR-TELEGRAM] Send failed with code {response.status_code}: {response.text}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"[ERR-TELEGRAM] Failed to send alert: {e}")
        return False

