"""Mover scan, watchlist ranking, and scheduled refresh service."""
import datetime as dt
import json
import re
import subprocess
import sys
import threading
import time

from services.history_service import load_json

MOVER_LOCK = threading.Lock()
SUBPROCESS_TIMEOUT_SEC = 60


def normalize_symbol(raw):
    sym = raw.strip().upper().replace(".P", "")
    if sym and not sym.endswith("USDT"):
        sym = f"{sym}USDT"
    return sym


def run_node_script(root, scripts_dir, script_name):
    proc = subprocess.run(
        ["node", str(scripts_dir / script_name)],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_TIMEOUT_SEC,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"{script_name} exited {proc.returncode}")
    return proc.stdout.strip()


def parse_movers_md(root, schedule_info):
    path = root / "MOVER_SCAN.md"
    if not path.exists():
        return {"updatedAt": None, "gainers": [], "losers": [], "rangeMovers": [], "raw": "", "schedule": schedule_info}
    raw = path.read_text(encoding="utf-8")
    updated_at = None
    gainers, losers, range_movers = [], [], []
    section = None
    pct_re = re.compile(r"^(\S+)\s+([+-]\d+(?:\.\d+)?)%\s+turnover\s+\$(\d+(?:\.\d+)?)M\s+price\s+(\S+)(.*)$")
    range_re = re.compile(
        r"^(\S+)\s+range\s+(\d+(?:\.\d+)?)%\s+\(H\s+(\S+)\s+/\s+L\s+(\S+)\)\s+net\s+([+-]\d+(?:\.\d+)?)%\s+turnover\s+\$(\d+(?:\.\d+)?)M\s+price\s+(\S+)(.*)$"
    )
    for line in raw.splitlines():
        if line.startswith("# Bybit mover scan"):
            parts = line.split("—", 1)
            updated_at = parts[1].strip() if len(parts) > 1 else None
        elif line.startswith("## Top") and "gainer" in line.lower():
            section = "gainers"
        elif line.startswith("## Top") and "loser" in line.lower():
            section = "losers"
        elif line.startswith("## Intraday range movers"):
            section = "range"
        elif line.startswith("Filters:"):
            section = None
        elif section in ("gainers", "losers"):
            m = pct_re.match(line.strip())
            if m:
                row = {
                    "ticker": m.group(1),
                    "symbol": m.group(1).replace(".P", ""),
                    "pct": float(m.group(2)),
                    "turnoverM": float(m.group(3)),
                    "price": float(m.group(4)),
                    "inLedger": "[already in ledger]" in m.group(5),
                }
                (gainers if section == "gainers" else losers).append(row)
        elif section == "range":
            m = range_re.match(line.strip())
            if m:
                range_movers.append({
                    "ticker": m.group(1),
                    "symbol": m.group(1).replace(".P", ""),
                    "rangePct": float(m.group(2)),
                    "high": float(m.group(3)),
                    "low": float(m.group(4)),
                    "pct": float(m.group(5)),
                    "turnoverM": float(m.group(6)),
                    "price": float(m.group(7)),
                    "inLedger": "[already in ledger]" in m.group(8),
                })
    return {
        "updatedAt": updated_at,
        "gainers": gainers,
        "losers": losers,
        "rangeMovers": range_movers,
        "raw": raw,
        "schedule": schedule_info,
    }


def score_tv_candidate(res):
    score = 0.0
    if res["scalp"]["tradeable"] or res["intraday"]["tradeable"]:
        score += 1000.0
    for side in ("long", "short"):
        intr = res["intraday"][side]
        if any("lacks 15m rejection/engulfing" in b for b in intr["blockedBy"]):
            score += 120.0
        sc = res["scalp"][side]
        if sc["zone"] is not None and sc["rr"] is not None:
            score += 50.0
    if res["structure4h"] == res["structure1d"] and res["structure4h"] in ("bullish", "bearish"):
        score += 80.0
    if res["intraday"]["verdictKind"] == "VALID":
        score += 40.0
    score += max(0.0, min(40.0, float(res["scalp"]["replay"].get("totalR") or 0.0)))
    return score


def refresh_movers_and_sync(root, scripts_dir, analyze_fn, schedule_info, extra_limit=3, sync_candidates=10):
    with MOVER_LOCK:
        run_node_script(root, scripts_dir, "scanMovers.mjs")
        movers = parse_movers_md(root, schedule_info)
        ledger = load_json(root / "SETUP_LEDGER.json", {})
        core_set = {s.replace(".P", "") for s in ledger.get("setups", {})} | {"BTCUSDT", "ETHUSDT"}

        candidates = []
        seen = set(core_set)
        lists = [movers["losers"], movers["gainers"], movers["rangeMovers"]]
        max_len = max((len(lst) for lst in lists), default=0)
        for idx in range(max_len):
            for lst in lists:
                if idx < len(lst):
                    sym = normalize_symbol(lst[idx].get("symbol", ""))
                    if sym and sym not in seen:
                        seen.add(sym)
                        candidates.append(sym)
                        if len(candidates) >= sync_candidates:
                            break
            if len(candidates) >= sync_candidates:
                break

        scored = []
        for sym in candidates:
            try:
                res = analyze_fn(sym, tf="15", include_candles=False)
                scored.append((score_tv_candidate(res), sym))
            except Exception:
                continue

        scored.sort(key=lambda item: item[0], reverse=True)
        top_tv = [f"{sym}.P" for _, sym in scored[:extra_limit]]
        now_iso = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        tv_path = root / "TV_WATCHLIST.json"
        tv_doc = load_json(tv_path, {})
        if top_tv:
            if not isinstance(tv_doc, dict):
                tv_doc = {}
            tv_doc["symbols"] = top_tv
            tv_doc["updated_at"] = now_iso
            tv_doc["last_mover_sync"] = now_iso
            tv_path.write_text(json.dumps(tv_doc, indent=2) + "\n", encoding="utf-8")

        movers["tvWatchlist"] = top_tv or (tv_doc.get("symbols", [])[:extra_limit] if isinstance(tv_doc, dict) else [])
        movers["schedule"] = schedule_info
        return movers


def start_mover_scheduler(tz_offset_hours, scan_times, sync_fn):
    tz = dt.timezone(dt.timedelta(hours=tz_offset_hours))
    ran_slots = set()

    def _loop():
        while True:
            now = dt.datetime.now(tz)
            slot = (now.strftime("%Y-%m-%d"), now.strftime("%H:%M"))
            if slot[1] in scan_times and slot not in ran_slots:
                ran_slots.add(slot)
                try:
                    sync_fn()
                except Exception as exc:
                    print(f"[mover-scheduler] error at {slot[0]} {slot[1]}: {exc}", file=sys.stderr, flush=True)
            time.sleep(30)

    thread = threading.Thread(target=_loop, name="mover-scheduler", daemon=True)
    thread.start()
    return thread
