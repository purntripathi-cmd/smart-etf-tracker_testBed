# =====================================================================
# V2 STANDALONE EXTERNAL CRON RUNNER (PYTHON SCHEDULER)
# =====================================================================
# Use this script to run the scheduled paper trader continuously on:
# - A local laptop or desktop (background task)
# - A free Linux cloud VM (AWS EC2 free tier, Render worker, Railway)
# - No GitHub Secrets, Telegram tokens, or GSheets keys required.
# =====================================================================
import os
import sys

# Ensure v2 directory takes precedence for local module imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import time
import datetime
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
import logging

from paper_trader_daemon import run_paper_trader_daemon

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CRON_SCHEDULER] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ExternalCronRunner")

# Target execution times (Monday=0 to Friday=4)
SCHEDULED_TASKS = {
    "09:45": "INTRADAY_ENTRY",       # 09:45 AM IST
    "15:00": "PAPER_TRADE_3PM",      # 03:00 PM IST
    "15:10": "INTRADAY_SQUAREOFF"    # 03:10 PM IST
}

def start_cron_scheduler():
    logger.info("==================================================")
    logger.info("🚀 V2 External Cron Scheduler started.")
    logger.info("Monitoring Indian Market Trading Schedule (Mon-Fri):")
    logger.info("  • 09:45 IST -> INTRADAY_ENTRY (Top 3 Stocks + Top 3 ETFs)")
    logger.info("  • 15:00 IST -> PAPER_TRADE_3PM (Multi-Preset & AI Accumulation)")
    logger.info("  • 15:10 IST -> INTRADAY_SQUAREOFF (Auto-Squareoff Open Intraday)")
    logger.info("==================================================")

    executed_today = set()
    last_date = None

    while True:
        try:
            now_ist = datetime.datetime.now(IST)
            current_date = now_ist.strftime("%Y-%m-%d")
            current_time = now_ist.strftime("%H:%M")
            weekday = now_ist.weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday

            # Reset daily tracker at midnight
            if current_date != last_date:
                executed_today.clear()
                last_date = current_date

            # V2 Testbed: Runs 7 days a week for testing and validation
            if current_time in SCHEDULED_TASKS and current_time not in executed_today:
                task_mode = SCHEDULED_TASKS[current_time]
                logger.info(f"⏰ Triggering scheduled event: {task_mode} at {current_time} IST...")
                try:
                    run_paper_trader_daemon(mode_override=task_mode)
                    executed_today.add(current_time)
                    logger.info(f"✅ Successfully finished {task_mode}.")
                except Exception as e:
                    logger.error(f"❌ Error during {task_mode} execution: {e}")

            # Sleep 25 seconds before next time check
            time.sleep(25)

        except KeyboardInterrupt:
            logger.info("Stopping external cron scheduler upon user interrupt.")
            break
        except Exception as ex:
            logger.error(f"Scheduler loop error: {ex}")
            time.sleep(30)

if __name__ == "__main__":
    start_cron_scheduler()
