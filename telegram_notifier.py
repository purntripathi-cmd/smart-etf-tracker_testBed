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
            return {"ok": False, "chat_id": "", "chat_name": "", "error": data.get("description", f"HTTP {resp.status_code}")}

        results = data.get("result", [])
        if not results:
            return {
                "ok": False,
                "chat_id": "",
                "chat_name": "",
                "error": "No recent updates found. Please open your bot in Telegram, send /start or type 'hello', then try again."
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
