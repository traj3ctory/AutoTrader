"""Binds the mover service helpers to this app's config and analyzer."""
from services import movers_service
from services.analysis_service import analyze_symbol
from services.config import (
    MOVER_SCAN_TIMES,
    MOVER_SCAN_TZ_OFFSET_HOURS,
    MOVER_SYNC_CANDIDATES,
    ROOT,
    SCRIPTS_DIR,
    TV_EXTRA_LIMIT,
)


def mover_schedule_info():
    return {"times": MOVER_SCAN_TIMES, "tzOffsetHours": MOVER_SCAN_TZ_OFFSET_HOURS}


def parse_movers_md():
    return movers_service.parse_movers_md(ROOT, mover_schedule_info())


def refresh_movers_and_sync():
    return movers_service.refresh_movers_and_sync(ROOT, SCRIPTS_DIR, analyze_symbol, mover_schedule_info(), TV_EXTRA_LIMIT, MOVER_SYNC_CANDIDATES)


def start_mover_scheduler():
    return movers_service.start_mover_scheduler(MOVER_SCAN_TZ_OFFSET_HOURS, MOVER_SCAN_TIMES, refresh_movers_and_sync)


def run_node_script(script_name):
    return movers_service.run_node_script(ROOT, SCRIPTS_DIR, script_name)
