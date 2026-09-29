# =====================================================================
# PAPER TRADER DAEMON: SCHEDULED BACKGROUND EXECUTION & MULTI-ASSET ENGINE
# =====================================================================
import os
import sys
import datetime
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
import pandas as pd
import numpy as np
import requests
import json
import logging
import yfinance as yf

# Ensure local module directory takes precedence
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

LOCAL_DATA_DIR = os.path.join(CURRENT_DIR, "data")
os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
LOCAL_TRADES_CSV = os.path.join(LOCAL_DATA_DIR, "paper_trades.csv")
LOCAL_AUDIT_CSV = os.path.join(LOCAL_DATA_DIR, "execution_audit_log.csv")
LOG_FILE_PATH = os.path.join(LOCAL_DATA_DIR, "daemon_execution.log")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
    ]
)
logger = logging.getLogger("PaperTraderDaemon")

try:
    from holiday_manager import is_trading_day, is_nse_holiday, calculate_trading_days
except ImportError:
    def is_trading_day(dt=None):
        return True, "Active Trading Session"
    def is_nse_holiday(dt=None):
        return False, ""
    def calculate_trading_days(s, e):
        return 0

from strategy_engine import (
    DEFAULT_STAGE1_ETF_CONFIG,
    DEFAULT_STAGE2_STOCK_CONFIG,
    evaluate_market_metrics,
    get_top_conviction_candidates,
    validate_trade_execution,
    evaluate_trade_exits,
    extract_ticker_df,
    get_active_runtime_config
)
from universe_manager import get_active_universe, ALL_PRECIOUS_METALS_CONFIG
from sr_engine import compute_sr_matrix
from reit_scanner import check_reit_investment_eligibility, scan_all_reits, check_metal_investment_eligibility
from ml_optimizer import (
    load_ai_trades,
    save_ai_trades,
    get_ai_rag_conviction_candidates
)
from telegram_notifier import (
    send_telegram_message,
    format_paper_trade_alert,
    get_telegram_config
)

DEFAULT_PAPER_HEADERS = [
    "Trade_ID", "Username", "Ticker", "Trade_Action", "Buy Ticker", "Sell Ticker",
    "Asset_Class", "Category", "Trigger_Type", "Strategy_Preset", "Trigger_Indicator", "Near_Support_Status",
    "Status", "Entry_Price", "Live_CMP", "Executed_Qty", "Stop_Loss", "Target",
    "Execution_Timestamp", "Exit_Timestamp", "Exit_Price", "Exit_Reason", "Hold_Duration_Days",
    "PnL_Rs", "PnL_Pct", "Invested_Value",
    "Technical_Score_At_Entry", "Fundamental_Score_At_Entry", "RSI_At_Entry",
    "Composite_Score_At_Entry", "Empirical_Win_Rate_At_Entry", "Market_Regime_At_Entry"
]

DEFAULT_AUDIT_HEADERS = [
    "Timestamp_IST", "Trigger_Source", "Preset", "Recommended_BUY", "Recommended_SELL", "Execution_Status", "Reason_Summary"
]

DEFAULT_USER_HEADERS = [
    "Username", "Password", "Name", "Email", "Mobile", "Role",
    "Strategy_Preset", "Tranche_Budget", "Monthly_Cap"
]

DEFAULT_CONFIG_HEADERS = [
    "Setting_Key", "Setting_Value", "Updated_At", "Updated_By"
]

# =====================================================================
# PERSISTENCE: DUAL STORAGE (GOOGLE SHEETS + LOCAL CSV)
# =====================================================================
def get_direct_gspread_client():
    # TESTBED MODE: Google Sheets integration is disabled to guarantee zero secrets and 100% offline local CSV operation
    return None

def _safe_update_worksheet(worksheet, values, range_name):
    try:
        worksheet.update(values=values, range_name=range_name)
    except TypeError:
        worksheet.update(range_name, values)

def setup_or_repair_gsheets_schema(wipe_existing_data=False):
    """
    Ensures that Google Sheets contains all 3 required worksheets:
    1. Users
    2. Paper_Trades
    3. Execution_Audit_Log
    
    If wipe_existing_data is True:
        - Clears existing data
        - Recreates clean headers with all current columns
        - Seeds default Admin user in Users
        - Seeds an initialization record in Execution_Audit_Log
        - Also clears local CSV files in data/
    If wipe_existing_data is False:
        - Creates any missing worksheets
        - Appends any missing header columns without deleting existing data
        - Preserves existing rows
    """
    spreadsheet = get_direct_gspread_client()
    status_report = []
    
    if not spreadsheet:
        os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
        users_local = os.path.join(LOCAL_DATA_DIR, "users_auth.csv")
        if wipe_existing_data:
            pd.DataFrame([{
                "Username": "Purn (Admin)", "Password": "Etaa@1234#", "Name": "Purn", "Email": "admin@gmail.com",
                "Mobile": "9999999999", "Role": "admin", "Strategy_Preset": "Default", "Tranche_Budget": 5000, "Monthly_Cap": 50000
            }]).to_csv(users_local, index=False)
            pd.DataFrame(columns=DEFAULT_PAPER_HEADERS).to_csv(LOCAL_TRADES_CSV, index=False)
            pd.DataFrame(columns=DEFAULT_AUDIT_HEADERS).to_csv(LOCAL_AUDIT_CSV, index=False)
            return True, "Testbed zero-secrets mode: Cleaned and recreated local CSV schema files."
        else:
            if not os.path.exists(users_local):
                pd.DataFrame([{
                    "Username": "Purn (Admin)", "Password": "Etaa@1234#", "Name": "Purn", "Email": "admin@gmail.com",
                    "Mobile": "9999999999", "Role": "admin", "Strategy_Preset": "Default", "Tranche_Budget": 5000, "Monthly_Cap": 50000
                }]).to_csv(users_local, index=False)
            if not os.path.exists(LOCAL_TRADES_CSV):
                pd.DataFrame(columns=DEFAULT_PAPER_HEADERS).to_csv(LOCAL_TRADES_CSV, index=False)
            if not os.path.exists(LOCAL_AUDIT_CSV):
                pd.DataFrame(columns=DEFAULT_AUDIT_HEADERS).to_csv(LOCAL_AUDIT_CSV, index=False)
            return True, "Testbed zero-secrets mode: Verified local CSV schema files."
        
    try:
        existing_sheets = {ws.title: ws for ws in spreadsheet.worksheets()}
        
        # 1. USERS WORKSHEET
        if "Users" not in existing_sheets and "Users_Auth_DB" not in existing_sheets:
            ws_users = spreadsheet.add_worksheet(title="Users", rows="1000", cols="15")
            _safe_update_worksheet(ws_users, [DEFAULT_USER_HEADERS], "A1")
            _safe_update_worksheet(ws_users, [["Purn (Admin)", "Etaa@1234#", "Purn", "admin@gmail.com", "9999999999", "admin", "Default", 5000, 50000]], "A2")
            status_report.append("Created 'Users' worksheet with Admin account")
        else:
            ws_users = existing_sheets.get("Users", existing_sheets.get("Users_Auth_DB"))
            if wipe_existing_data:
                ws_users.clear()
                _safe_update_worksheet(ws_users, [DEFAULT_USER_HEADERS], "A1")
                _safe_update_worksheet(ws_users, [["Purn (Admin)", "Etaa@1234#", "Purn", "admin@gmail.com", "9999999999", "admin", "Default", 5000, 50000]], "A2")
                status_report.append("Reset 'Users' worksheet with clean schema & default Admin")
            else:
                try:
                    records = ws_users.get_all_records()
                except Exception:
                    records = []
                if not records:
                    ws_users.clear()
                    _safe_update_worksheet(ws_users, [DEFAULT_USER_HEADERS], "A1")
                    _safe_update_worksheet(ws_users, [["Purn (Admin)", "Etaa@1234#", "Purn", "admin@gmail.com", "9999999999", "admin", "Default", 5000, 50000]], "A2")
                    status_report.append("Populated empty 'Users' worksheet with Admin account")
                else:
                    curr_header = ws_users.row_values(1)
                    missing_user_cols = [c for c in DEFAULT_USER_HEADERS if c not in curr_header]
                    if missing_user_cols:
                        new_headers = curr_header + missing_user_cols
                        _safe_update_worksheet(ws_users, [new_headers], "A1")
                        status_report.append(f"Appended {len(missing_user_cols)} missing columns to 'Users'")
                    else:
                        status_report.append(f"Verified 'Users' worksheet ({len(records)} users)")

        # 2. PAPER_TRADES WORKSHEET
        if "Paper_Trades" not in existing_sheets:
            ws_trades = spreadsheet.add_worksheet(title="Paper_Trades", rows="2000", cols="35")
            _safe_update_worksheet(ws_trades, [DEFAULT_PAPER_HEADERS], "A1")
            status_report.append("Created 'Paper_Trades' worksheet with all quantitative columns")
        else:
            ws_trades = existing_sheets["Paper_Trades"]
            if wipe_existing_data:
                ws_trades.clear()
                _safe_update_worksheet(ws_trades, [DEFAULT_PAPER_HEADERS], "A1")
                status_report.append("Wiped 'Paper_Trades' worksheet and recreated clean schema headers")
            else:
                curr_header = ws_trades.row_values(1)
                missing_cols = [c for c in DEFAULT_PAPER_HEADERS if c not in curr_header]
                if missing_cols:
                    new_headers = curr_header + missing_cols
                    _safe_update_worksheet(ws_trades, [new_headers], "A1")
                    status_report.append(f"Appended {len(missing_cols)} missing columns to 'Paper_Trades'")
                else:
                    status_report.append("Verified 'Paper_Trades' worksheet schema is up-to-date")

        # 3. EXECUTION_AUDIT_LOG WORKSHEET
        if "Execution_Audit_Log" not in existing_sheets:
            ws_audit = spreadsheet.add_worksheet(title="Execution_Audit_Log", rows="2000", cols="15")
            _safe_update_worksheet(ws_audit, [DEFAULT_AUDIT_HEADERS], "A1")
            now_str = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
            init_row = [
                now_str, "SYSTEM_INIT", "ALL", "None", "None", "🟢 Initialized",
                "Google Sheets schema automatically created."
            ]
            _safe_update_worksheet(ws_audit, [init_row], "A2")
            status_report.append("Created 'Execution_Audit_Log' worksheet")
        else:
            ws_audit = existing_sheets["Execution_Audit_Log"]
            if wipe_existing_data:
                ws_audit.clear()
                _safe_update_worksheet(ws_audit, [DEFAULT_AUDIT_HEADERS], "A1")
                now_str = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
                init_row = [
                    now_str, "SCHEMA_RESET", "ALL", "None", "None", "🟢 Recreated",
                    "Google Sheets worksheets cleared and reset with clean schema."
                ]
                _safe_update_worksheet(ws_audit, [init_row], "A2")
                status_report.append("Wiped 'Execution_Audit_Log' and logged reset event")
            else:
                curr_audit_header = ws_audit.row_values(1)
                missing_audit_cols = [c for c in DEFAULT_AUDIT_HEADERS if c not in curr_audit_header]
                if missing_audit_cols:
                    new_audit_headers = curr_audit_header + missing_audit_cols
                    _safe_update_worksheet(ws_audit, [new_audit_headers], "A1")
                    status_report.append(f"Appended {len(missing_audit_cols)} missing columns to 'Execution_Audit_Log'")
                else:
                    status_report.append("Verified 'Execution_Audit_Log' worksheet exists")

        # 4. PLATFORM_CONFIG WORKSHEET
        if "Platform_Config" not in existing_sheets:
            ws_cfg = spreadsheet.add_worksheet(title="Platform_Config", rows="100", cols="5")
            _safe_update_worksheet(ws_cfg, [DEFAULT_CONFIG_HEADERS], "A1")
            now_str = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
            _safe_update_worksheet(ws_cfg, [["allow_weekend_trades", "False", now_str, "System_Init"]], "A2")
            status_report.append("Created 'Platform_Config' worksheet")
        else:
            ws_cfg = existing_sheets["Platform_Config"]
            if wipe_existing_data:
                ws_cfg.clear()
                _safe_update_worksheet(ws_cfg, [DEFAULT_CONFIG_HEADERS], "A1")
                now_str = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
                _safe_update_worksheet(ws_cfg, [["allow_weekend_trades", "False", now_str, "Schema_Reset"]], "A2")
                status_report.append("Reset 'Platform_Config' with default settings")
            else:
                curr_cfg_header = ws_cfg.row_values(1)
                missing_cfg_cols = [c for c in DEFAULT_CONFIG_HEADERS if c not in curr_cfg_header]
                if missing_cfg_cols:
                    new_cfg_headers = curr_cfg_header + missing_cfg_cols
                    _safe_update_worksheet(ws_cfg, [new_cfg_headers], "A1")
                    status_report.append(f"Appended {len(missing_cfg_cols)} missing columns to 'Platform_Config'")
                else:
                    status_report.append("Verified 'Platform_Config' worksheet exists")

        # If wiped, also sync local files
        if wipe_existing_data:
            pd.DataFrame([{
                "Username": "Purn (Admin)", "Password": "Etaa@1234#", "Name": "Purn", "Email": "admin@gmail.com",
                "Mobile": "9999999999", "Role": "admin", "Strategy_Preset": "Default", "Tranche_Budget": 5000, "Monthly_Cap": 50000
            }]).to_csv(os.path.join(LOCAL_DATA_DIR, "users_auth.csv"), index=False)
            pd.DataFrame(columns=DEFAULT_PAPER_HEADERS).to_csv(LOCAL_TRADES_CSV, index=False)
            now_str = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
            pd.DataFrame([{
                "Timestamp_IST": now_str,
                "Trigger_Source": "SCHEMA_RESET", "Preset": "ALL", "Recommended_BUY": "None",
                "Recommended_SELL": "None", "Execution_Status": "🟢 Recreated",
                "Reason_Summary": "Local cache reset in sync with Google Sheets"
            }]).to_csv(LOCAL_AUDIT_CSV, index=False)

        return True, " | ".join(status_report)
    except Exception as ex:
        logger.error(f"Error in setup_or_repair_gsheets_schema: {ex}")
        return False, f"Failed to setup Google Sheets: {ex}"

def load_trades():
    local_df = pd.DataFrame(columns=DEFAULT_PAPER_HEADERS)
    if os.path.exists(LOCAL_TRADES_CSV) and os.path.getsize(LOCAL_TRADES_CSV) > 0:
        try:
            ldf = pd.read_csv(LOCAL_TRADES_CSV)
            if not ldf.empty:
                if "Trade_ID" in ldf.columns:
                    ldf = ldf[ldf["Trade_ID"].astype(str).str.strip().ne("") & ldf["Trade_ID"].notna() & ~ldf["Trade_ID"].astype(str).str.lower().isin(["nan", "none"])]
                elif "Ticker" in ldf.columns:
                    ldf = ldf[ldf["Ticker"].astype(str).str.strip().ne("") & ldf["Ticker"].notna() & ~ldf["Ticker"].astype(str).str.lower().isin(["nan", "none"])]
                local_df = ldf
        except Exception as e:
            logger.warning(f"Error loading local paper trades in daemon: {e}")

    gs_df = pd.DataFrame(columns=DEFAULT_PAPER_HEADERS)
    spreadsheet = get_direct_gspread_client()
    if spreadsheet:
        try:
            worksheet = spreadsheet.worksheet("Paper_Trades")
            data = worksheet.get_all_records()
            if data:
                raw_df = pd.DataFrame(data)
                if not raw_df.empty and "Trade_ID" in raw_df.columns:
                    raw_df = raw_df[raw_df["Trade_ID"].astype(str).str.strip().ne("") & raw_df["Trade_ID"].notna() & ~raw_df["Trade_ID"].astype(str).str.lower().isin(["nan", "none"])]
                    gs_df = raw_df
        except Exception as e:
            logger.warning(f"Could not read 'Paper_Trades' from Google Sheets: {e}")

    if not local_df.empty and not gs_df.empty:
        combined = pd.concat([gs_df, local_df], ignore_index=True)
        if "Trade_ID" in combined.columns:
            combined = combined.drop_duplicates(subset=["Trade_ID"], keep="last")
        res_df = combined
    elif not local_df.empty:
        res_df = local_df
    elif not gs_df.empty:
        res_df = gs_df
    else:
        res_df = pd.DataFrame(columns=DEFAULT_PAPER_HEADERS)

    if spreadsheet and len(res_df) > len(gs_df):
        try:
            try:
                worksheet = spreadsheet.worksheet("Paper_Trades")
            except Exception:
                worksheet = spreadsheet.add_worksheet(title="Paper_Trades", rows="1000", cols="35")
            worksheet.clear()
            header_list = list(res_df.columns)
            rows_list = res_df.fillna("").astype(str).values.tolist()
            _safe_update_worksheet(worksheet, [header_list], "A1")
            if rows_list:
                _safe_update_worksheet(worksheet, rows_list, "A2")
            logger.info("Auto-synced trades from local CSV to Google Sheets 'Paper_Trades'.")
        except Exception as e:
            logger.warning(f"Failed to auto-heal Google Sheets in daemon: {e}")

    if not res_df.empty:
        try:
            res_df.to_csv(LOCAL_TRADES_CSV, index=False)
        except Exception:
            pass

    for col in DEFAULT_PAPER_HEADERS:
        if col not in res_df.columns:
            res_df[col] = ""
    res_df["Status"] = res_df["Status"].fillna("ACTIVE").astype(str)
    if "PnL_Pct" in res_df.columns:
        res_df["PnL_Pct"] = res_df["PnL_Pct"].astype(object)
    float_cols = ["Live_CMP", "Exit_Price", "PnL_Rs", "Entry_Price", "Stop_Loss", "Target", "Executed_Qty", "Invested_Value", "Hold_Duration_Days"]
    for col in float_cols:
        if col in res_df.columns:
            res_df[col] = pd.to_numeric(res_df[col], errors="coerce").fillna(0.0)
    return res_df

def save_trades(df):
    for col in DEFAULT_PAPER_HEADERS:
        if col not in df.columns:
            df[col] = ""
    df["Status"] = df["Status"].fillna("ACTIVE").astype(str)

    # Merge with existing file to prevent overwriting past trades
    existing_df = pd.DataFrame()
    if os.path.exists(LOCAL_TRADES_CSV) and os.path.getsize(LOCAL_TRADES_CSV) > 0:
        try:
            existing_df = pd.read_csv(LOCAL_TRADES_CSV)
        except Exception:
            pass
    if not existing_df.empty and "Trade_ID" in existing_df.columns and "Trade_ID" in df.columns:
        merged_to_save = pd.concat([existing_df, df], ignore_index=True).drop_duplicates(subset=["Trade_ID"], keep="last")
    else:
        merged_to_save = df

    merged_to_save.to_csv(LOCAL_TRADES_CSV, index=False)
    
    spreadsheet = get_direct_gspread_client()
    if spreadsheet:
        try:
            try:
                worksheet = spreadsheet.worksheet("Paper_Trades")
            except Exception:
                worksheet = spreadsheet.add_worksheet(title="Paper_Trades", rows="1000", cols="35")
            
            worksheet.clear()
            header_list = list(merged_to_save.columns)
            rows_list = merged_to_save.fillna("").astype(str).values.tolist()
            _safe_update_worksheet(worksheet, [header_list], "A1")
            if rows_list:
                _safe_update_worksheet(worksheet, rows_list, "A2")
            logger.info("Successfully synced trades to Google Sheets 'Paper_Trades'.")
        except Exception as e:
            logger.error(f"Failed to update Google Sheets worksheet 'Paper_Trades': {e}")

def log_audit(entry):
    existing_csv = pd.DataFrame(columns=DEFAULT_AUDIT_HEADERS)
    if os.path.exists(LOCAL_AUDIT_CSV) and os.path.getsize(LOCAL_AUDIT_CSV) > 0:
        try:
            existing_csv = pd.read_csv(LOCAL_AUDIT_CSV)
        except Exception:
            pass
    combined_csv = pd.concat([existing_csv, pd.DataFrame([entry])], ignore_index=True).drop_duplicates()
    combined_csv.to_csv(LOCAL_AUDIT_CSV, index=False)

    spreadsheet = get_direct_gspread_client()
    if spreadsheet:
        try:
            try:
                worksheet = spreadsheet.worksheet("Execution_Audit_Log")
            except Exception:
                worksheet = spreadsheet.add_worksheet(title="Execution_Audit_Log", rows="1000", cols="10")
            
            data = worksheet.get_all_records()
            audit_history = pd.DataFrame(data) if data else pd.DataFrame(columns=DEFAULT_AUDIT_HEADERS)
            combined = pd.concat([audit_history, pd.DataFrame([entry])], ignore_index=True).drop_duplicates()
            
            worksheet.clear()
            header_list = list(combined.columns)
            rows_list = combined.fillna("").astype(str).values.tolist()
            _safe_update_worksheet(worksheet, [header_list], "A1")
            if rows_list:
                _safe_update_worksheet(worksheet, rows_list, "A2")
        except Exception as e:
            logger.error(f"Failed to update Google Sheets worksheet 'Execution_Audit_Log': {e}")

def load_audit_log():
    local_df = pd.DataFrame(columns=DEFAULT_AUDIT_HEADERS)
    if os.path.exists(LOCAL_AUDIT_CSV) and os.path.getsize(LOCAL_AUDIT_CSV) > 0:
        try:
            ldf = pd.read_csv(LOCAL_AUDIT_CSV)
            if not ldf.empty and "Timestamp_IST" in ldf.columns:
                local_df = ldf[ldf["Timestamp_IST"].astype(str).str.strip().ne("") & ldf["Timestamp_IST"].notna()]
        except Exception:
            pass

    gs_df = pd.DataFrame(columns=DEFAULT_AUDIT_HEADERS)
    spreadsheet = get_direct_gspread_client()
    if spreadsheet:
        try:
            worksheet = spreadsheet.worksheet("Execution_Audit_Log")
            data = worksheet.get_all_records()
            if data:
                raw_df = pd.DataFrame(data)
                if not raw_df.empty and "Timestamp_IST" in raw_df.columns:
                    gs_df = raw_df[raw_df["Timestamp_IST"].astype(str).str.strip().ne("") & raw_df["Timestamp_IST"].notna()]
        except Exception:
            pass

    if not local_df.empty and not gs_df.empty:
        combined = pd.concat([gs_df, local_df], ignore_index=True)
        if "Audit_ID" in combined.columns:
            combined = combined.drop_duplicates(subset=["Audit_ID"], keep="last")
        else:
            combined = combined.drop_duplicates()
        res_df = combined
    elif not local_df.empty:
        res_df = local_df
    elif not gs_df.empty:
        res_df = gs_df
    else:
        res_df = pd.DataFrame(columns=DEFAULT_AUDIT_HEADERS)

    if spreadsheet and len(res_df) > len(gs_df):
        try:
            try:
                worksheet = spreadsheet.worksheet("Execution_Audit_Log")
            except Exception:
                worksheet = spreadsheet.add_worksheet(title="Execution_Audit_Log", rows="1000", cols="10")
            worksheet.clear()
            header_list = list(res_df.columns)
            rows_list = res_df.fillna("").astype(str).values.tolist()
            _safe_update_worksheet(worksheet, [header_list], "A1")
            if rows_list:
                _safe_update_worksheet(worksheet, rows_list, "A2")
        except Exception:
            pass

    if not res_df.empty:
        try:
            res_df.to_csv(LOCAL_AUDIT_CSV, index=False)
        except Exception:
            pass

    for c in DEFAULT_AUDIT_HEADERS:
        if c not in res_df.columns:
            res_df[c] = ""
    return res_df

load_paper_trades = load_trades
save_paper_trades = save_trades

def load_platform_setting(key, default=None):
    """
    Loads a platform setting.
    Checks:
    1. Google Sheets 'Platform_Config' worksheet
    2. Local runtime_config.json
    """
    try:
        spreadsheet = get_direct_gspread_client()
        if spreadsheet:
            try:
                ws = spreadsheet.worksheet("Platform_Config")
                records = ws.get_all_records()
                for r in records:
                    if str(r.get("Setting_Key", "")).strip().lower() == str(key).strip().lower():
                        return str(r.get("Setting_Value", "")).strip()
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"Could not load platform setting '{key}' from Google Sheets: {e}")

    try:
        import streamlit as st
        from streamlit_gsheets import GSheetsConnection
        conn = st.connection("gsheets", type=GSheetsConnection)
        if conn:
            df_cfg = conn.read(worksheet="Platform_Config", ttl=5)
            if df_cfg is not None and not df_cfg.empty and "Setting_Key" in df_cfg.columns:
                match = df_cfg[df_cfg["Setting_Key"].astype(str).str.strip().str.lower() == str(key).strip().lower()]
                if not match.empty:
                    return str(match.iloc[0].get("Setting_Value", "")).strip()
    except Exception:
        pass

    try:
        cfg = get_active_runtime_config()
        if key == "allow_weekend_trades":
            return cfg.get("admin_testing_overrides", {}).get("allow_weekend_trades", default)
    except Exception:
        pass

    return default

def save_platform_setting(key, value, updated_by="Admin"):
    """
    Saves a platform setting to both Google Sheets 'Platform_Config' worksheet
    and local runtime_config.json.
    """
    now_str = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    success = False

    # 1. Update Google Sheets via direct gspread
    try:
        spreadsheet = get_direct_gspread_client()
        if spreadsheet:
            try:
                try:
                    ws = spreadsheet.worksheet("Platform_Config")
                except Exception:
                    ws = spreadsheet.add_worksheet(title="Platform_Config", rows="100", cols="5")
                    _safe_update_worksheet(ws, [DEFAULT_CONFIG_HEADERS], "A1")

                records = ws.get_all_records()
                found_row_idx = None
                for i, r in enumerate(records):
                    if str(r.get("Setting_Key", "")).strip().lower() == str(key).strip().lower():
                        found_row_idx = i + 2
                        break

                row_data = [str(key), str(value), now_str, str(updated_by)]
                if found_row_idx:
                    _safe_update_worksheet(ws, [row_data], f"A{found_row_idx}")
                else:
                    ws.append_row(row_data)
                success = True
            except Exception as ex:
                logger.warning(f"Failed to update Google Sheets Platform_Config: {ex}")
    except Exception as e:
        logger.debug(f"Direct gspread save error: {e}")

    # 2. Also update local runtime_config.json
    try:
        cfg_paths = [
            os.path.join(CURRENT_DIR, "runtime_config.json"),
            "runtime_config.json"
        ]
        for p in cfg_paths:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    cfg_data = json.load(f)
                if key == "allow_weekend_trades":
                    bool_val = str(value).strip().lower() in ["true", "1", "yes"]
                    if "admin_testing_overrides" not in cfg_data:
                        cfg_data["admin_testing_overrides"] = {}
                    cfg_data["admin_testing_overrides"]["allow_weekend_trades"] = bool_val
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(cfg_data, f, indent=4)
    except Exception as ex:
        logger.warning(f"Failed to update local runtime_config.json: {ex}")

    return success

def is_weekend_trading_allowed():
    """
    Returns True only if weekend / off-hours trading is explicitly allowed.
    Strictly defaults to False.
    Priority:
    1. Environment variable ALLOW_WEEKEND_TRADES (if set to 1/true or 0/false)
    2. Google Sheets Platform_Config worksheet
    3. runtime_config.json ('admin_testing_overrides.allow_weekend_trades')
    """
    # 1. Environment variable override check
    env_override = os.getenv("ALLOW_WEEKEND_TRADES")
    if env_override is not None and str(env_override).strip() != "":
        val_env = str(env_override).strip().lower()
        if val_env in ["1", "true", "yes"]:
            return True
        if val_env in ["0", "false", "no"]:
            return False

    # 2. Check Google Sheets Platform_Config
    try:
        val_gsheet = load_platform_setting("allow_weekend_trades", default=None)
        if val_gsheet is not None and str(val_gsheet).strip() != "":
            return str(val_gsheet).strip().lower() in ["1", "true", "yes"]
    except Exception:
        pass

    # 3. Check local runtime_config.json
    try:
        runtime_cfg = get_active_runtime_config()
        return bool(runtime_cfg.get("admin_testing_overrides", {}).get("allow_weekend_trades", False))
    except Exception:
        return False

def run_paper_trader_daemon(mode_override=None):
    if mode_override:
        os.environ["MANUAL_MODE"] = str(mode_override).strip().upper()
    return run_scheduled_daemon_tasks()

# =====================================================================
# MULTI-AMC PRECIOUS METALS BUILDER
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
        m_dict["Tactical Status"] = m_el.get("status", "Support Dip")
        m_dict["Eligibility_Reason"] = m_el.get("reason", "Macro Hedge Allocation")
        m_dict["is_eligible"] = m_el.get("eligible", False)
        m_dict["Stop_Loss"] = float(m_dict.get("Stop_Loss", round(float(m_dict["CMP (₹)"]) * 0.96, 2)))
        m_dict["Target"] = float(m_dict.get("Target", round(float(m_dict["CMP (₹)"]) * 1.06, 2)))
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
# TELEGRAM DISPATCHER
# =====================================================================
def send_concise_telegram_alert(trade_type, signals_list):
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = str(os.getenv("TELEGRAM_CHAT_ID", "887870969")).strip()
    
    try:
        import streamlit as st
        if not tg_token and "TELEGRAM_BOT_TOKEN" in st.secrets:
            tg_token = str(st.secrets["TELEGRAM_BOT_TOKEN"]).strip()
        if (not tg_chat or tg_chat == "887870969") and "TELEGRAM_CHAT_ID" in st.secrets:
            tg_chat = str(st.secrets["TELEGRAM_CHAT_ID"]).strip()
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
    
    header = header_map.get(trade_type, f'📊 *{trade_type}*')
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
            for sig in signals_list:
                ticker = str(sig.get('ticker', '')).replace('.NS', '')
                cmp = float(sig.get('cmp', 0.0))
                action = str(sig.get('action', 'BUY')).upper()
                source = str(sig.get('source', 'Quant'))
                icon = '🟢' if action == 'BUY' else ('🔴' if action in ['SELL', 'SQUARE-OFF'] else '🔄')
                ai_tag = ' 🤖[AI]' if 'AI' in source else ''
                msg_lines.append(f"{icon} `{ticker}` | ₹{cmp:,.2f} | *{action}*{ai_tag} ({source})")

    url = f"https://api.telegram.org/bot{tg_token}/sendMessage" if not tg_token.startswith("bot") else f"https://api.telegram.org/{tg_token}/sendMessage"
    payload = {"chat_id": tg_chat, "text": "\n".join(msg_lines), "parse_mode": "Markdown"}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            logger.error(f"[ERR-TELEGRAM] Send failed with code {response.status_code}: {response.text}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"[ERR-TELEGRAM] Failed to send alert: {e}")
        return False

# =====================================================================
# CORE SCHEDULED DAEMON WORKFLOW
# =====================================================================
def run_scheduled_daemon_tasks(cli_mode=None):
    if cli_mode:
        mode = str(cli_mode).strip().upper()
    elif len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        mode = sys.argv[1].strip().upper()
    else:
        mode = os.getenv("MANUAL_MODE", "PAPER_TRADE_3PM").strip().upper()
    now_ist = datetime.datetime.now(IST)
    now_str = now_ist.strftime("%Y-%m-%d %H:%M:%S")
    is_weekday = (now_ist.weekday() < 5)  # 0=Monday ... 4=Friday, 5=Saturday, 6=Sunday

    is_session_active, session_reason = is_trading_day(now_ist.date())
    logger.info(f"=== Starting Daemon Task: Mode={mode} | Time={now_str} IST (Session Active: {is_session_active} - {session_reason}) ===")

    # 1. Weekday & NSE Trading Holiday Gate Check
    allow_weekend = is_weekend_trading_allowed()

    if not is_session_active and not allow_weekend:
        msg = f"Indian market closed ({session_reason}). Scheduled auto-execution skipped. (Admin testing override is currently disabled)."
        logger.info(f"[SESSION-GATE] {msg}")
        log_audit({
            "Timestamp_IST": now_str,
            "Trigger_Source": f"SCHEDULED_{mode}",
            "Preset": "All Active Presets",
            "Recommended_BUY": "None",
            "Recommended_SELL": "None",
            "Execution_Status": f"⚪ Skipped ({session_reason})",
            "Reason_Summary": msg
        })
        return {
            "status": "skipped",
            "reason": msg,
            "mode": mode,
            "timestamp": now_str
        }

    # 2. Fetch Universe & Market Data
    univ = get_active_universe()
    if isinstance(univ, tuple):
        active_stock_universe, active_etf_universe = univ
    elif isinstance(univ, dict):
        active_stock_universe = univ.get("stocks", DEFAULT_STAGE2_STOCK_CONFIG)
        active_etf_universe = univ.get("etfs", DEFAULT_STAGE1_ETF_CONFIG)
    else:
        active_stock_universe, active_etf_universe = DEFAULT_STAGE2_STOCK_CONFIG, DEFAULT_STAGE1_ETF_CONFIG
    
    all_tickers = list({x["ticker"] for x in (active_stock_universe + active_etf_universe)})
    all_tickers += ["^CRSLDX", "^NSEI", "^INDIAVIX"]
    
    logger.info(f"Downloading market data for {len(all_tickers)} universe assets...")
    try:
        raw_data = yf.download(all_tickers, period="5y", interval="1d", group_by="ticker", auto_adjust=True, threads=True)
    except Exception as e:
        logger.error(f"Failed to download market data: {e}")
        raw_data = pd.DataFrame()

    if raw_data.empty:
        logger.warning("Daemon skipped: Market history unavailable.")
        return

    # 3. Indicator & Regime Computation
    stocks_market_df, stocks_regime = evaluate_market_metrics(raw_data, active_stock_universe, is_stock_mode=True)
    etfs_market_df, etfs_regime = evaluate_market_metrics(raw_data, active_etf_universe, is_stock_mode=False)
    regime_name = stocks_regime.get("regime", "Normal")

    signals_for_alert = []
    trades_df = load_trades()

    # 4. Check & Process Inbuilt Exits First (Dynamic Target, Stop Loss, Trailing Stops)
    # Intraday 3:10 PM Squareoff is explicitly handled in MODE C below with full telemetry, audit logging, and rich Telegram alerts.
    trades_df = evaluate_trade_exits(trades_df, raw_data, force_squareoff_intraday=False, skip_intraday_squareoff=True)
    save_trades(trades_df)

    active_positions = trades_df[trades_df["Status"].fillna("ACTIVE").astype(str).str.strip().str.upper() == "ACTIVE"] if not trades_df.empty else pd.DataFrame()
    active_ticker_set = set(active_positions["Ticker"].astype(str).str.replace(".NS", "").str.upper()) if not active_positions.empty else set()

    TRANCHE_BUDGET = 5000  # Rs 5,000 per tranche

    # =================================================================
    # MODE A: INTRADAY ENTRY (09:45 AM IST)
    # =================================================================
    if mode == "INTRADAY_ENTRY":
        created_records = []
        try:
            stk_buy, _ = get_top_conviction_candidates(stocks_market_df, preset_name="Intraday", is_stock_mode=True, limit=2)
            for _, r in stk_buy.iterrows():
                sym = str(r.get("Ticker", "")).replace(".NS", "").strip()
                cmp_val = float(r.get("CMP (₹)", 0.0) or 0.0)
                if not sym or sym in active_ticker_set or cmp_val <= 0:
                    continue

                qty = max(1, int(TRANCHE_BUDGET // cmp_val))
                can_trade, final_qty, _ = validate_trade_execution(sym, "BUY", "Intraday", qty, active_positions)
                if can_trade:
                    trade_id = f"INTRA_{int(now_ist.timestamp())}_{sym}"
                    rec = {
                        "Trade_ID": trade_id, "Username": "Daemon_Intraday", "Ticker": sym,
                        "Trade_Action": "🟢 BUY", "Buy Ticker": sym, "Sell Ticker": "None",
                        "Asset_Class": "Stock", "Category": "Category 2: Quality Equities",
                        "Trigger_Type": "INTRADAY_BUY", "Strategy_Preset": "Intraday",
                        "Trigger_Indicator": "Intraday Momentum / RSI Dip", "Near_Support_Status": "Dynamic Channel Entry",
                        "Status": "ACTIVE", "Entry_Price": cmp_val, "Live_CMP": cmp_val,
                        "Executed_Qty": final_qty, "Stop_Loss": float(r.get("Stop_Loss", cmp_val * 0.98)), "Target": float(r.get("Target", cmp_val * 1.02)),
                        "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0, "Exit_Reason": "", "Hold_Duration_Days": 0,
                        "PnL_Rs": 0.0, "PnL_Pct": "0.0%", "Invested_Value": round(cmp_val * final_qty, 2),
                        "Technical_Score_At_Entry": float(r.get("Technical Score", 50.0)),
                        "Fundamental_Score_At_Entry": float(r.get("Fundamental Score", 50.0)),
                        "RSI_At_Entry": float(r.get("RSI (14D)", 50.0)),
                        "Composite_Score_At_Entry": float(r.get("Composite Score", 50.0)),
                        "Empirical_Win_Rate_At_Entry": "N/A", "Market_Regime_At_Entry": regime_name
                    }
                    created_records.append(rec)
                    active_ticker_set.add(sym)
                    signals_for_alert.append({
                        'ticker': sym,
                        'cmp': cmp_val,
                        'qty': final_qty,
                        'action': 'BUY',
                        'source': 'Intraday Quant',
                        'rsi': float(r.get("RSI (14D)", 50.0)),
                        'score': float(r.get("Composite Score", 50.0)),
                        'sl': float(r.get("Stop_Loss", cmp_val * 0.98)),
                        'target': float(r.get("Target", cmp_val * 1.02)),
                        'trigger': "Intraday Momentum / RSI Dip"
                    })

            if created_records:
                updated_trades = pd.concat([trades_df, pd.DataFrame(created_records)], ignore_index=True)
                save_trades(updated_trades)
                log_audit({
                    "Timestamp_IST": now_str, "Trigger_Source": "INTRADAY_ENTRY", "Preset": "Intraday",
                    "Recommended_BUY": ", ".join([r["Ticker"] for r in created_records]), "Recommended_SELL": "None",
                    "Execution_Status": f"🟢 Executed ({len(created_records)} Orders)",
                    "Reason_Summary": f"Intraday entry executed at 9:45 AM. Orders: {len(created_records)}."
                })
            else:
                log_audit({
                    "Timestamp_IST": now_str, "Trigger_Source": "INTRADAY_ENTRY", "Preset": "Intraday",
                    "Recommended_BUY": "None", "Recommended_SELL": "None",
                    "Execution_Status": "⚪ Skipped", "Reason_Summary": "Intraday entry skipped: Tickers already active or criteria unmet."
                })
            send_concise_telegram_alert('Intraday Entry', signals_for_alert)
        except Exception as e:
            logger.error(f"Intraday Entry error: {e}")

    # =================================================================
    # MODE B: 3 PM MULTI-PRESET & MULTI-ASSET ACCUMULATION
    # =================================================================
    elif mode == "PAPER_TRADE_3PM":
        created_records = []
        exec_summary_msgs = []
        try:
            # 1. Active symbols set and lookup
            active_syms = set(trades_df[trades_df["Status"].fillna("ACTIVE").astype(str).str.strip().str.upper() == "ACTIVE"]["Ticker"].astype(str).str.replace(".NS", "")) if (not trades_df.empty and "Status" in trades_df.columns) else set()
            
            # 2. Selected Presets for 3 PM Accumulation (Excluding Intraday, aligned with Central Execution Hub)
            selected_presets = ["Default", "Long-Term", "Swing / Positional", "AI / RAG"]
            
            # Loop through the 4 non-intraday presets for Category 1 (ETFs) & Category 2 (Equities)
            for p_name in selected_presets:
                # -------------------------------------------------------------
                # Category 1: Broad Equity ETFs
                # -------------------------------------------------------------
                if p_name == "AI / RAG":
                    etf_b, etf_s = get_ai_rag_conviction_candidates(etfs_market_df, is_stock_mode=False, limit=1)
                else:
                    etf_b, etf_s = get_top_conviction_candidates(etfs_market_df, preset_name=p_name, is_stock_mode=False, limit=1)
                
                # BUY Orders
                for _, r in etf_b.iterrows():
                    sym = str(r.get("Ticker", "")).replace(".NS", "").strip()
                    cmp_v = float(r.get("CMP (₹)", 0.0) or 0.0)
                    if not sym or sym in active_syms or cmp_v <= 0:
                        continue
                    q = max(1, int(TRANCHE_BUDGET // cmp_v))
                    trade_id = f"V2_ETF_{int(now_ist.timestamp())}_{sym}_{p_name[:3].upper()}"
                    rec = {
                        "Trade_ID": trade_id,
                        "Username": "Daemon_AI" if p_name == "AI / RAG" else "Daemon_Cron",
                        "Ticker": sym,
                        "Trade_Action": "🟢 BUY", "Buy Ticker": sym, "Sell Ticker": "—",
                        "Category": "Broad Equity ETF", "Asset_Class": "ETF",
                        "Trigger_Type": f"{p_name.upper()}_ETF_BUY",
                        "Trigger_Indicator": f"{p_name} Preset Buy (RSI: {r.get('RSI (14D)', 50):.1f}, 200DMA: {r.get('Dist 200DMA %', 0):+.1f}%)",
                        "Strategy_Preset": p_name, "Status": "ACTIVE",
                        "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                        "Stop_Loss": float(r.get("Stop_Loss", cmp_v * 0.97)), "Target": float(r.get("Target", cmp_v * 1.04)),
                        "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                        "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                        "Invested_Value": round(cmp_v * q, 2),
                        "Technical_Score_At_Entry": round(float(r.get("Technical Score", 50.0)), 1),
                        "Fundamental_Score_At_Entry": round(float(r.get("Fundamental Score", 50.0)), 1),
                        "Composite_Score_At_Entry": round(float(r.get("Composite Score", r.get("Composite Buy Score", 50.0))), 1),
                        "Near_Support_Status": f"Trend Proximity ({r.get('Dist 200DMA %', 0):+.1f}%)",
                        "RSI_At_Entry": round(float(r.get("RSI (14D)", 50.0)), 1),
                        "Empirical_Win_Rate_At_Entry": "N/A", "Market_Regime_At_Entry": regime_name
                    }
                    created_records.append(rec)
                    active_syms.add(sym)
                    signals_for_alert.append({'ticker': sym, 'cmp': cmp_v, 'action': 'BUY', 'source': f'ETF ({p_name})'})
                    exec_summary_msgs.append(f"🟢 BUY ETF ({p_name}): {sym}")

                # SELL Orders (Square-off if active in trades_df, else record SELL entry)
                for _, r in etf_s.iterrows():
                    sym = str(r.get("Ticker", "")).replace(".NS", "").strip()
                    cmp_v = float(r.get("CMP (₹)", 0.0) or 0.0)
                    if not sym or cmp_v <= 0:
                        continue
                    active_mask = (trades_df["Ticker"].astype(str).str.replace(".NS", "") == sym) & (trades_df["Status"] == "ACTIVE")
                    if active_mask.any():
                        row_idx = trades_df[active_mask].index[0]
                        entry_p = float(trades_df.at[row_idx, "Entry_Price"])
                        eqty = int(trades_df.at[row_idx, "Executed_Qty"])
                        pnl_val = round((cmp_v - entry_p) * eqty, 2)
                        pnl_pct_val = f"{((cmp_v - entry_p) / entry_p * 100):+.2f}%" if entry_p > 0 else "0.0%"
                        trades_df.at[row_idx, "Status"] = "CLOSED_PROFIT" if pnl_val >= 0 else "CLOSED_STOPLOSS"
                        trades_df.at[row_idx, "Trade_Action"] = "🔴 SELL"
                        trades_df.at[row_idx, "Sell Ticker"] = sym
                        trades_df.at[row_idx, "Exit_Price"] = cmp_v
                        trades_df.at[row_idx, "Exit_Timestamp"] = now_str
                        trades_df.at[row_idx, "Exit_Reason"] = f"Overbought Exit Trigger ({p_name} RSI {r.get('RSI (14D)', 50):.1f})"
                        trades_df.at[row_idx, "PnL_Rs"] = pnl_val
                        trades_df.at[row_idx, "PnL_Pct"] = pnl_pct_val
                        active_syms.discard(sym)
                        signals_for_alert.append({'ticker': sym, 'cmp': cmp_v, 'action': 'SQUARE-OFF', 'source': f'ETF ({p_name})'})
                        exec_summary_msgs.append(f"🔴 SQUARE-OFF ETF ({p_name}): {sym} (PnL: ₹{pnl_val:+,.2f})")
                    else:
                        q = max(1, int(TRANCHE_BUDGET // cmp_v))
                        trade_id = f"V2_ETF_EXIT_{int(now_ist.timestamp())}_{sym}_{p_name[:3].upper()}"
                        rec = {
                            "Trade_ID": trade_id,
                            "Username": "Daemon_AI" if p_name == "AI / RAG" else "Daemon_Cron",
                            "Ticker": sym,
                            "Trade_Action": "🔴 SELL", "Buy Ticker": "—", "Sell Ticker": sym,
                            "Category": "Broad Equity ETF", "Asset_Class": "ETF",
                            "Trigger_Type": f"{p_name.upper()}_ETF_SELL",
                            "Trigger_Indicator": f"{p_name} Exit Alert (RSI: {r.get('RSI (14D)', 50):.1f}, Urgency: {r.get('Composite Score', 50):.1f})",
                            "Strategy_Preset": p_name, "Status": "ACTIVE",
                            "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                            "Stop_Loss": float(r.get("Stop_Loss", round(cmp_v * 1.04, 2))),
                            "Target": float(r.get("Target", round(cmp_v * 0.95, 2))),
                            "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                            "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                            "Invested_Value": round(cmp_v * q, 2),
                            "Technical_Score_At_Entry": round(float(r.get("Technical Score", 50.0)), 1),
                            "Fundamental_Score_At_Entry": 50.0,
                            "Composite_Score_At_Entry": round(float(r.get("Composite Score", 50.0)), 1),
                            "Near_Support_Status": "Overbought Resistance Zone",
                            "RSI_At_Entry": round(float(r.get("RSI (14D)", 50.0)), 1),
                            "Empirical_Win_Rate_At_Entry": "N/A", "Market_Regime_At_Entry": regime_name
                        }
                        created_records.append(rec)
                        active_syms.add(sym)
                        signals_for_alert.append({'ticker': sym, 'cmp': cmp_v, 'action': 'SELL', 'source': f'ETF ({p_name})'})
                        exec_summary_msgs.append(f"🔴 SELL Entry ETF ({p_name}): {sym}")

                # -------------------------------------------------------------
                # Category 2: Quality Equities
                # -------------------------------------------------------------
                if p_name == "AI / RAG":
                    stk_b, stk_s = get_ai_rag_conviction_candidates(stocks_market_df, is_stock_mode=True, limit=1)
                else:
                    stk_b, stk_s = get_top_conviction_candidates(stocks_market_df, preset_name=p_name, is_stock_mode=True, limit=1)

                # BUY Orders
                for _, r in stk_b.iterrows():
                    sym = str(r.get("Ticker", "")).replace(".NS", "").strip()
                    cmp_v = float(r.get("CMP (₹)", 0.0) or 0.0)
                    if not sym or sym in active_syms or cmp_v <= 0:
                        continue
                    q = max(1, int(TRANCHE_BUDGET // cmp_v))
                    trade_id = f"V2_STK_{int(now_ist.timestamp())}_{sym}_{p_name[:3].upper()}"
                    rec = {
                        "Trade_ID": trade_id,
                        "Username": "Daemon_AI" if p_name == "AI / RAG" else "Daemon_Cron",
                        "Ticker": sym,
                        "Trade_Action": "🟢 BUY", "Buy Ticker": sym, "Sell Ticker": "—",
                        "Category": "Quality Stock", "Asset_Class": "Stock",
                        "Trigger_Type": f"{p_name.upper()}_STOCK_BUY",
                        "Trigger_Indicator": f"{p_name} Preset Buy (RSI: {r.get('RSI (14D)', 50):.1f}, 200DMA: {r.get('Dist 200DMA %', 0):+.1f}%)",
                        "Strategy_Preset": p_name, "Status": "ACTIVE",
                        "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                        "Stop_Loss": float(r.get("Stop_Loss", cmp_v * 0.95)), "Target": float(r.get("Target", cmp_v * 1.06)),
                        "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                        "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                        "Invested_Value": round(cmp_v * q, 2),
                        "Technical_Score_At_Entry": round(float(r.get("Technical Score", 50.0)), 1),
                        "Fundamental_Score_At_Entry": round(float(r.get("Fundamental Score", 50.0)), 1),
                        "Composite_Score_At_Entry": round(float(r.get("Composite Score", r.get("Composite Buy Score", 50.0))), 1),
                        "Near_Support_Status": f"Trend Proximity ({r.get('Dist 200DMA %', 0):+.1f}%)",
                        "RSI_At_Entry": round(float(r.get("RSI (14D)", 50.0)), 1),
                        "Empirical_Win_Rate_At_Entry": "N/A", "Market_Regime_At_Entry": regime_name
                    }
                    created_records.append(rec)
                    active_syms.add(sym)
                    signals_for_alert.append({'ticker': sym, 'cmp': cmp_v, 'action': 'BUY', 'source': f'Stock ({p_name})'})
                    exec_summary_msgs.append(f"🟢 BUY Stock ({p_name}): {sym}")

                # SELL Orders
                for _, r in stk_s.iterrows():
                    sym = str(r.get("Ticker", "")).replace(".NS", "").strip()
                    cmp_v = float(r.get("CMP (₹)", 0.0) or 0.0)
                    if not sym or cmp_v <= 0:
                        continue
                    active_mask = (trades_df["Ticker"].astype(str).str.replace(".NS", "") == sym) & (trades_df["Status"] == "ACTIVE")
                    if active_mask.any():
                        row_idx = trades_df[active_mask].index[0]
                        entry_p = float(trades_df.at[row_idx, "Entry_Price"])
                        eqty = int(trades_df.at[row_idx, "Executed_Qty"])
                        pnl_val = round((cmp_v - entry_p) * eqty, 2)
                        pnl_pct_val = f"{((cmp_v - entry_p) / entry_p * 100):+.2f}%" if entry_p > 0 else "0.0%"
                        trades_df.at[row_idx, "Status"] = "CLOSED_PROFIT" if pnl_val >= 0 else "CLOSED_STOPLOSS"
                        trades_df.at[row_idx, "Trade_Action"] = "🔴 SELL"
                        trades_df.at[row_idx, "Sell Ticker"] = sym
                        trades_df.at[row_idx, "Exit_Price"] = cmp_v
                        trades_df.at[row_idx, "Exit_Timestamp"] = now_str
                        trades_df.at[row_idx, "Exit_Reason"] = f"Overbought Exit Trigger ({p_name} RSI {r.get('RSI (14D)', 50):.1f})"
                        trades_df.at[row_idx, "PnL_Rs"] = pnl_val
                        trades_df.at[row_idx, "PnL_Pct"] = pnl_pct_val
                        active_syms.discard(sym)
                        signals_for_alert.append({'ticker': sym, 'cmp': cmp_v, 'action': 'SQUARE-OFF', 'source': f'Stock ({p_name})'})
                        exec_summary_msgs.append(f"🔴 SQUARE-OFF Stock ({p_name}): {sym} (PnL: ₹{pnl_val:+,.2f})")
                    else:
                        q = max(1, int(TRANCHE_BUDGET // cmp_v))
                        trade_id = f"V2_STK_EXIT_{int(now_ist.timestamp())}_{sym}_{p_name[:3].upper()}"
                        rec = {
                            "Trade_ID": trade_id,
                            "Username": "Daemon_AI" if p_name == "AI / RAG" else "Daemon_Cron",
                            "Ticker": sym,
                            "Trade_Action": "🔴 SELL", "Buy Ticker": "—", "Sell Ticker": sym,
                            "Category": "Quality Stock", "Asset_Class": "Stock",
                            "Trigger_Type": f"{p_name.upper()}_STOCK_SELL",
                            "Trigger_Indicator": f"{p_name} Exit Alert (RSI: {r.get('RSI (14D)', 50):.1f}, Urgency: {r.get('Composite Score', 50):.1f})",
                            "Strategy_Preset": p_name, "Status": "ACTIVE",
                            "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                            "Stop_Loss": float(r.get("Stop_Loss", round(cmp_v * 1.05, 2))),
                            "Target": float(r.get("Target", round(cmp_v * 0.94, 2))),
                            "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                            "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                            "Invested_Value": round(cmp_v * q, 2),
                            "Technical_Score_At_Entry": round(float(r.get("Technical Score", 50.0)), 1),
                            "Fundamental_Score_At_Entry": 50.0,
                            "Composite_Score_At_Entry": round(float(r.get("Composite Score", 50.0)), 1),
                            "Near_Support_Status": "Overbought Resistance Zone",
                            "RSI_At_Entry": round(float(r.get("RSI (14D)", 50.0)), 1),
                            "Empirical_Win_Rate_At_Entry": "N/A", "Market_Regime_At_Entry": regime_name
                        }
                        created_records.append(rec)
                        active_syms.add(sym)
                        signals_for_alert.append({'ticker': sym, 'cmp': cmp_v, 'action': 'SELL', 'source': f'Stock ({p_name})'})
                        exec_summary_msgs.append(f"🔴 SELL Entry Stock ({p_name}): {sym}")

            # -------------------------------------------------------------
            # Category 3: S/R Mean-Reversion Tranche
            # -------------------------------------------------------------
            try:
                sr_df_stk = compute_sr_matrix(raw_data, active_stock_universe, is_stock_mode=True)
                sr_df_etf = compute_sr_matrix(raw_data, active_etf_universe, is_stock_mode=False)
                sr_all = pd.concat([sr_df_stk, sr_df_etf], ignore_index=True) if (not sr_df_stk.empty or not sr_df_etf.empty) else pd.DataFrame()
                
                if not sr_all.empty:
                    sr_buys = sr_all[sr_all["Action Signal"].str.contains("BUY|ACCUMULATE", na=False)].sort_values(by="5Y S/R Win Rate (%)", ascending=False).head(1)
                    for _, sr_it in sr_buys.iterrows():
                        sym = str(sr_it["Ticker"]).replace(".NS", "").strip()
                        cmp_v = float(sr_it["CMP (₹)"])
                        if not sym or sym in active_syms or cmp_v <= 0:
                            continue
                        q = max(1, int(TRANCHE_BUDGET // cmp_v))
                        s1_v = float(sr_it.get("Major Support S1 (₹)", cmp_v * 0.97))
                        dist_s1 = ((cmp_v - s1_v) / s1_v * 100) if s1_v > 0 else 0.0
                        rec = {
                            "Trade_ID": f"V2_SR_{int(now_ist.timestamp())}_{sym}",
                            "Username": "Daemon_Cron", "Ticker": sym,
                            "Trade_Action": "🟢 BUY", "Buy Ticker": sym, "Sell Ticker": "—",
                            "Category": "S/R Mean Reversion", "Asset_Class": sr_it.get("Category", "Stock"),
                            "Trigger_Type": "SR_SUPPORT_BUY",
                            "Trigger_Indicator": f"S1 Support Bounce ({sr_it.get('5Y S/R Win Rate (%)', 50)}% 5Y Win)",
                            "Strategy_Preset": "S/R Range Mean Reversion", "Status": "ACTIVE",
                            "Entry_Price": cmp_v, "Live_CMP": cmp_v, "Executed_Qty": q,
                            "Stop_Loss": float(sr_it.get("Suggested SL (₹)", cmp_v * 0.95)),
                            "Target": float(sr_it.get("Suggested Target (₹)", cmp_v * 1.05)),
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
                        }
                        created_records.append(rec)
                        active_syms.add(sym)
                        signals_for_alert.append({'ticker': sym, 'cmp': cmp_v, 'action': 'BUY', 'source': 'S/R Support'})
                        exec_summary_msgs.append(f"🟢 BUY S/R Support: {sym}")

                    sr_exits = sr_all[sr_all["Range Position (%)"] >= 80.0].sort_values(by="Range Position (%)", ascending=False).head(1)
                    for _, srx in sr_exits.iterrows():
                        sym = str(srx["Ticker"]).replace(".NS", "").strip()
                        cmp_v = float(srx["CMP (₹)"])
                        if not sym or cmp_v <= 0:
                            continue
                        active_mask = (trades_df["Ticker"].astype(str).str.replace(".NS", "") == sym) & (trades_df["Status"] == "ACTIVE")
                        if active_mask.any():
                            row_idx = trades_df[active_mask].index[0]
                            entry_p = float(trades_df.at[row_idx, "Entry_Price"])
                            eqty = int(trades_df.at[row_idx, "Executed_Qty"])
                            pnl_val = round((cmp_v - entry_p) * eqty, 2)
                            pnl_pct_val = f"{((cmp_v - entry_p) / entry_p * 100):+.2f}%" if entry_p > 0 else "0.0%"
                            trades_df.at[row_idx, "Status"] = "CLOSED_PROFIT" if pnl_val >= 0 else "CLOSED_STOPLOSS"
                            trades_df.at[row_idx, "Trade_Action"] = "🔴 SELL"
                            trades_df.at[row_idx, "Sell Ticker"] = sym
                            trades_df.at[row_idx, "Exit_Price"] = cmp_v
                            trades_df.at[row_idx, "Exit_Timestamp"] = now_str
                            trades_df.at[row_idx, "Exit_Reason"] = f"S/R Resistance Exit (Range Position {srx.get('Range Position (%)', 85):.1f}%)"
                            trades_df.at[row_idx, "PnL_Rs"] = pnl_val
                            trades_df.at[row_idx, "PnL_Pct"] = pnl_pct_val
                            active_syms.discard(sym)
                            signals_for_alert.append({'ticker': sym, 'cmp': cmp_v, 'action': 'SQUARE-OFF', 'source': 'S/R Resistance'})
                            exec_summary_msgs.append(f"🔴 SQUARE-OFF S/R Resistance: {sym} (PnL: ₹{pnl_val:+,.2f})")
            except Exception as sr_err:
                logger.warning(f"S/R Mean Reversion 3 PM error: {sr_err}")

            # -------------------------------------------------------------
            # Category 4: Premier REITs & InvITs (Conditional)
            # -------------------------------------------------------------
            try:
                reit_scan_df = scan_all_reits()
                if not reit_scan_df.empty:
                    for _, r_row in reit_scan_df.iterrows():
                        r_item = r_row.to_dict()
                        r_sym = str(r_item.get("Ticker", "")).replace(".NS", "").strip()
                        if not r_sym or r_sym in active_syms:
                            continue
                        r_el = check_reit_investment_eligibility(r_item)
                        if r_el.get("eligible", False):
                            r_cmp = float(r_item.get("CMP (₹)", 300.0) or 300.0)
                            if r_cmp > 0:
                                r_qty = max(1, int(TRANCHE_BUDGET // r_cmp))
                                rec = {
                                    "Trade_ID": f"V2_REIT_{int(now_ist.timestamp())}_{r_sym}",
                                    "Username": "Daemon_Cron", "Ticker": r_sym,
                                    "Trade_Action": "🟢 BUY", "Buy Ticker": r_sym, "Sell Ticker": "—",
                                    "Category": "REIT/InvIT", "Asset_Class": "Real Estate / Infra",
                                    "Trigger_Type": "HIGH_YIELD_REIT_BUY", "Strategy_Preset": "High-Yield Cash Flow",
                                    "Trigger_Indicator": f"Lucrative Yield {r_item.get('Distribution Yield (%)', 7.5):.1f}% (NAV Disc: {r_item.get('NAV Discount / Premium (%)', 0.0):+.1f}%)",
                                    "Near_Support_Status": "S1 Yield Floor (Lucrative)", "Status": "ACTIVE",
                                    "Entry_Price": r_cmp, "Live_CMP": r_cmp, "Executed_Qty": r_qty,
                                    "Stop_Loss": float(r_item.get("Immediate Support S1 (₹)", r_cmp * 0.95)),
                                    "Target": float(r_item.get("Immediate Resistance R1 (₹)", r_cmp * 1.08)),
                                    "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                                    "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                                    "Invested_Value": round(r_cmp * r_qty, 2),
                                    "Technical_Score_At_Entry": round(float(r_item.get("RSI (14D)", 50.0)), 1),
                                    "Fundamental_Score_At_Entry": round(float(r_item.get("Distribution Yield (%)", 8.0)), 1),
                                    "Composite_Score_At_Entry": round(float(r_item.get("Composite Score (0-100)", 75.0)), 1),
                                    "Near_Support_Status": "S1 Yield Floor (Lucrative)",
                                    "RSI_At_Entry": round(float(r_item.get("RSI (14D)", 50.0)), 1),
                                    "Empirical_Win_Rate_At_Entry": "N/A", "Market_Regime_At_Entry": regime_name
                                }
                                created_records.append(rec)
                                active_syms.add(r_sym)
                                signals_for_alert.append({'ticker': r_sym, 'cmp': r_cmp, 'action': 'BUY', 'source': 'REIT (Lucrative)'})
                                exec_summary_msgs.append(f"🟢 BUY REIT (Lucrative): {r_sym}")
                                break
            except Exception as reit_err:
                logger.warning(f"REIT 3 PM execution error: {reit_err}")

            # -------------------------------------------------------------
            # Category 5: Multi-AMC Precious Metals (Conditional)
            # -------------------------------------------------------------
            try:
                all_metals_df = build_all_precious_metals_df(etfs_market_df)
                for m_metal_type in ["Gold", "Silver"]:
                    metal_cands = all_metals_df[all_metals_df["Metal Type"] == m_metal_type].sort_values(by=["is_eligible", "Expense %", "52W Range %"], ascending=[False, True, True])
                    if not metal_cands.empty:
                        best_m = metal_cands.iloc[0].to_dict()
                        m_sym = str(best_m.get("Ticker", "")).replace(".NS", "").strip()
                        m_cmp = float(best_m.get("CMP (₹)", 0.0) or 0.0)
                        m_el = check_metal_investment_eligibility(best_m)
                        if m_el.get("eligible", False) and m_sym not in active_syms and m_cmp > 0:
                            m_qty = max(1, int(TRANCHE_BUDGET // m_cmp))
                            rec = {
                                "Trade_ID": f"V2_MET_{int(now_ist.timestamp())}_{m_sym}",
                                "Username": "Daemon_Cron", "Ticker": m_sym,
                                "Trade_Action": "🟢 BUY", "Buy Ticker": m_sym, "Sell Ticker": "—",
                                "Category": "Precious Metal", "Asset_Class": "Commodity",
                                "Trigger_Type": "METALS_VALUE_DIP_BUY",
                                "Trigger_Indicator": f"Lucrative Dip (AMC: {best_m.get('AMC')}, RSI: {best_m.get('RSI (14D)', 50):.1f})",
                                "Strategy_Preset": "Commodity Defensive Hedge", "Status": "ACTIVE",
                                "Entry_Price": m_cmp, "Live_CMP": m_cmp, "Executed_Qty": m_qty,
                                "Stop_Loss": round(m_cmp * 0.96, 2), "Target": round(m_cmp * 1.06, 2),
                                "Execution_Timestamp": now_str, "Exit_Timestamp": "", "Exit_Price": 0.0,
                                "Exit_Reason": "", "Hold_Duration_Days": 0, "PnL_Rs": 0.0, "PnL_Pct": "0.0%",
                                "Invested_Value": round(m_cmp * m_qty, 2),
                                "Technical_Score_At_Entry": round(float(best_m.get("RSI (14D)", 50.0)), 1),
                                "Fundamental_Score_At_Entry": 50.0, "Composite_Score_At_Entry": 50.0,
                                "Near_Support_Status": "Value Dip Zone (Lucrative)",
                                "RSI_At_Entry": round(float(best_m.get("RSI (14D)", 50.0)), 1),
                                "Empirical_Win_Rate_At_Entry": "N/A", "Market_Regime_At_Entry": regime_name
                            }
                            created_records.append(rec)
                            active_syms.add(m_sym)
                            signals_for_alert.append({'ticker': m_sym, 'cmp': m_cmp, 'action': 'BUY', 'source': f'Metal ({best_m.get("AMC")} {m_metal_type})'})
                            exec_summary_msgs.append(f"🟢 BUY Metal ({best_m.get('AMC')} {m_metal_type}): {m_sym}")
            except Exception as met_err:
                logger.warning(f"Metals 3 PM execution error: {met_err}")

            # -------------------------------------------------------------
            # Persist Trades & Execution Audit Log
            # -------------------------------------------------------------
            if created_records:
                combined_trades = pd.concat([trades_df, pd.DataFrame(created_records)], ignore_index=True)
            else:
                combined_trades = trades_df

            save_trades(combined_trades)

            total_actions = len(created_records) + len([s for s in signals_for_alert if s.get("action") == "SQUARE-OFF"])
            if total_actions > 0:
                log_audit({
                    "Timestamp_IST": now_str,
                    "Trigger_Source": "SCHEDULED_CRON_0300PM",
                    "Preset": ", ".join(selected_presets),
                    "Recommended_BUY": ", ".join([r["Ticker"] for r in created_records if "BUY" in r.get("Trigger_Type", "")]),
                    "Recommended_SELL": ", ".join([r["Ticker"] for r in created_records if "SELL" in r.get("Trigger_Type", "")]),
                    "Execution_Status": f"🟢 Executed {len(created_records)} Orders across {len(selected_presets)} Presets",
                    "Reason_Summary": f"3 PM Multi-Asset Execution summary: {'; '.join(exec_summary_msgs)}"
                })
            else:
                log_audit({
                    "Timestamp_IST": now_str,
                    "Trigger_Source": "SCHEDULED_CRON_0300PM",
                    "Preset": ", ".join(selected_presets),
                    "Recommended_BUY": "None", "Recommended_SELL": "None",
                    "Execution_Status": "⚪ Skipped",
                    "Reason_Summary": "3 PM daemon completed: All candidates already active or market criteria unmet."
                })

            send_concise_telegram_alert('Swing / Long-Term (3 PM)', signals_for_alert)
        except Exception as ex:
            logger.error(f"3 PM Accumulation daemon error: {ex}")

    # =================================================================
    # MODE C: INTRADAY SQUAREOFF (03:10 PM IST)
    # =================================================================
    elif mode == "INTRADAY_SQUAREOFF":
        try:
            closed_count = 0
            if not trades_df.empty:
                trades_df["Status"] = trades_df["Status"].fillna("ACTIVE").astype(str)
                for idx, row in trades_df.iterrows():
                    st_val = str(row.get("Status", "")).strip().upper()
                    trig_val = str(row.get("Trigger_Type", "") or "").upper()
                    preset_val = str(row.get("Strategy_Preset", "") or "").upper()
                    trade_id_val = str(row.get("Trade_ID", "") or "")

                    if st_val == "ACTIVE" and ("INTRADAY" in trig_val or "INTRADAY" in preset_val or trade_id_val.startswith("INTRA_")):
                        ep = float(pd.to_numeric(row.get("Entry_Price", 0), errors="coerce") or 0.0)
                        qty = float(pd.to_numeric(row.get("Executed_Qty", 1), errors="coerce") or 1.0)
                        sym = str(row.get("Ticker", "")).replace(".NS", "").strip()
                        
                        t_full = f"{sym}.NS"
                        curr_p = ep
                        if t_full in raw_data.columns.levels[0]:
                            sub_d = raw_data[t_full]["Close"].dropna()
                            if not sub_d.empty:
                                curr_p = float(sub_d.iloc[-1])
                        
                        trades_df.at[idx, "Status"] = "INTRADAY_SQUAREOFF"
                        trades_df.at[idx, "Exit_Timestamp"] = now_str
                        trades_df.at[idx, "Exit_Reason"] = "3:10 PM Intraday Auto-Squareoff"
                        trades_df.at[idx, "Exit_Price"] = curr_p
                        trades_df.at[idx, "Live_CMP"] = curr_p
                        trades_df.at[idx, "Hold_Duration_Days"] = 0
                        pnl_rs = round((curr_p - ep) * qty, 2)
                        pnl_pct = round(((curr_p - ep) / ep) * 100.0, 2) if ep > 0 else 0.0
                        trades_df.at[idx, "PnL_Rs"] = pnl_rs
                        if "PnL_Pct" in trades_df.columns and trades_df["PnL_Pct"].dtype != object:
                            trades_df["PnL_Pct"] = trades_df["PnL_Pct"].astype(object)
                        trades_df.at[idx, "PnL_Pct"] = f"{pnl_pct:+.2f}%"

                        closed_count += 1
                        signals_for_alert.append({
                            'ticker': sym,
                            'entry_price': ep,
                            'cmp': curr_p,
                            'action': 'SQUARE-OFF',
                            'source': 'Intraday Exit',
                            'qty': qty,
                            'pnl_rs': pnl_rs,
                            'pnl_pct': f"{pnl_pct:+.2f}%",
                            'entry_ts': str(row.get("Execution_Timestamp", "")),
                            'exit_ts': now_str,
                            'rsi_entry': float(pd.to_numeric(row.get("RSI_At_Entry", 50.0), errors="coerce") or 50.0),
                            'score_entry': float(pd.to_numeric(row.get("Composite_Score_At_Entry", 50.0), errors="coerce") or 50.0),
                            'trigger': str(row.get("Trigger_Indicator", "Intraday Momentum / RSI Dip")),
                            'exit_reason': "3:10 PM Intraday Auto-Squareoff"
                        })

            if closed_count > 0:
                save_trades(trades_df)
                ticker_names = ", ".join([s["ticker"] for s in signals_for_alert])
                detail_summary_list = [
                    f"{s['ticker']} (Exit: ₹{s['cmp']:,.2f}, Entry: ₹{s['entry_price']:,.2f}, PnL: ₹{s['pnl_rs']:+,.2f}, {s['pnl_pct']})"
                    for s in signals_for_alert
                ]
                tot_pnl = sum([s['pnl_rs'] for s in signals_for_alert])
                log_audit({
                    "Timestamp_IST": now_str,
                    "Trigger_Source": "INTRADAY_SQUAREOFF",
                    "Preset": "Intraday",
                    "Recommended_BUY": "None",
                    "Recommended_SELL": ticker_names,
                    "Execution_Status": f"🔴 Closed ({closed_count} Positions): {ticker_names}",
                    "Reason_Summary": f"3:10 PM Intraday positions squared off: {'; '.join(detail_summary_list)}. Total Realized PnL: ₹{tot_pnl:+,.2f}."
                })
            else:
                log_audit({
                    "Timestamp_IST": now_str,
                    "Trigger_Source": "INTRADAY_SQUAREOFF",
                    "Preset": "Intraday",
                    "Recommended_BUY": "None",
                    "Recommended_SELL": "None",
                    "Execution_Status": "⚪ No open positions",
                    "Reason_Summary": "Intraday square-off checked: No active intraday positions found."
                })

            send_concise_telegram_alert('Intraday Exit', signals_for_alert)
        except Exception as e:
            logger.error(f"Intraday Square-off daemon error: {e}")

    logger.info("Daemon scheduled tasks completed successfully.")
    return {
        "status": "success",
        "mode": mode,
        "timestamp": now_str
    }

def run_paper_trader_daemon(mode_override=None):
    """Backwards-compatible wrapper for testbed runners and external cron schedulers."""
    return run_scheduled_daemon_tasks(cli_mode=mode_override)

if __name__ == "__main__":
    if "--init-sheets" in sys.argv:
        ok, msg = setup_or_repair_gsheets_schema(wipe_existing_data=False)
        print(f"[{'SUCCESS' if ok else 'FAILED'}] Init Sheets: {msg}")
    elif "--reset-sheets" in sys.argv:
        ok, msg = setup_or_repair_gsheets_schema(wipe_existing_data=True)
        print(f"[{'SUCCESS' if ok else 'FAILED'}] Reset Sheets: {msg}")
    else:
        run_scheduled_daemon_tasks()
