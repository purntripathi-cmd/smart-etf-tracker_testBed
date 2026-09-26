# =====================================================================
# V2 CRON WEBHOOK SERVER FOR CRON-JOB.ORG (HTTP POST / GET HANDLER)
# =====================================================================
# This standalone lightweight HTTP server accepts incoming POST requests
# from https://cron-job.org/en/ to trigger scheduled paper trading routines.
#
# Can be hosted on:
# - Render (Free Web Service)
# - Railway / Koyeb / Fly.io / PythonAnywhere
# - VPS / Cloud Server
# - Local PC exposed via Cloudflare Tunnel or ngrok
# =====================================================================
import os
import sys

# Ensure v2 directory takes precedence for local module imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import json
import logging
import datetime
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
from http.server import HTTPServer, BaseHTTPRequestHandler

from paper_trader_daemon import run_paper_trader_daemon

IST = ZoneInfo("Asia/Kolkata")
PORT = int(os.environ.get("PORT", 8080))
CRON_SECRET_TOKEN = os.environ.get("CRON_SECRET_TOKEN", "agy_quant_secure_token_2026")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WEBHOOK_SERVER] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("CronWebhookServer")

class CronJobRequestHandler(BaseHTTPRequestHandler):

    def _send_response(self, status_code, payload):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Cron-Token")
        self.end_headers()

    def do_GET(self):
        """Health check endpoint and optional GET trigger"""
        now_str = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        self._send_response(200, {
            "status": "online",
            "service": "AGY Quant Platform V2 Cron Webhook",
            "server_time_ist": now_str,
            "instructions": "Send an HTTP POST to /trigger with JSON: {'mode': 'PAPER_TRADE_3PM', 'token': 'YOUR_TOKEN'}"
        })

    def do_POST(self):
        """Receives POST webhook from cron-job.org"""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            body = {}

        # 1. Token Authentication Check (via body or header)
        incoming_token = (
            body.get("token") or 
            body.get("auth_token") or 
            self.headers.get("X-Cron-Token") or 
            self.headers.get("Authorization", "").replace("Bearer ", "").strip()
        )

        if CRON_SECRET_TOKEN and incoming_token != CRON_SECRET_TOKEN:
            logger.warning(f"Unauthorized POST attempt from {self.client_address[0]}")
            self._send_response(401, {
                "status": "unauthorized",
                "message": "Invalid authentication token. Check 'token' or 'auth_token' in JSON body."
            })
            return

        # 2. Determine Action Mode
        mode = body.get("mode", "PAPER_TRADE_3PM").strip().upper()
        if mode not in ["PAPER_TRADE_3PM", "INTRADAY_ENTRY", "INTRADAY_SQUAREOFF"]:
            mode = "PAPER_TRADE_3PM"

        now_str = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Incoming cron-job.org trigger: Mode = {mode} at {now_str} IST")

        # 3. Execute Daemon
        try:
            run_paper_trader_daemon(mode_override=mode)
            self._send_response(200, {
                "status": "success",
                "executed_mode": mode,
                "timestamp_ist": now_str,
                "message": f"Successfully completed execution for mode: {mode}"
            })
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            self._send_response(500, {
                "status": "error",
                "executed_mode": mode,
                "error_detail": str(e),
                "timestamp_ist": now_str
            })

def run_server():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, CronJobRequestHandler)
    logger.info(f"🚀 V2 Webhook Server listening on port {PORT}...")
    logger.info(f"Configured Auth Token: '{CRON_SECRET_TOKEN}'")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping webhook server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
