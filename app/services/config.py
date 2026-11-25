"""Shared paths, tunables and locks for the analyzer server."""
import os
import sys
import threading
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
ROOT = APP_DIR.parent
SCRIPTS_DIR = ROOT / "scripts"
WEB_DIST = ROOT / "app" / "web" / "dist"
SIGNAL_HISTORY_PATH = ROOT / "SIGNAL_HISTORY.json"

for _path in (SCRIPTS_DIR, APP_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

HOST = os.environ.get("AUTOTRADER_HOST", "127.0.0.1")
PORT = int(os.environ.get("AUTOTRADER_PORT", "8787"))
CANDLE_LIMIT = 220
VALID_TFS = {"5", "15", "60", "240"}
INTRADAY_PENDING_VALID_CANDLES = 4
ZONE_LATE_ENTRY_CANDLES = 4
ZONE_4H_PROXIMITY_PCT = 0.04
SL_ATR_BUFFER_MULT = 0.50
MOVER_SCAN_TZ_OFFSET_HOURS = int(os.environ.get("AUTOTRADER_TZ_OFFSET_HOURS", "1"))
MOVER_SCAN_TIMES = [t.strip() for t in os.environ.get("AUTOTRADER_MOVER_SCHEDULE", "01:05,08:30,14:15").split(",") if t.strip()]
MOVER_SYNC_CANDIDATES = 10
TV_EXTRA_LIMIT = 3
MAX_BODY_BYTES = 65536
SIGNAL_HISTORY_VIEW = 30

ENGINE_LOCK = threading.Lock()
RISK_LOCK = threading.Lock()
