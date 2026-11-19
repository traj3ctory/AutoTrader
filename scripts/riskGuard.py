#!/usr/bin/env python3
# Enforces the written risk limits from RISK_LOG.json: open-trade cap, daily loss cap and the two-loss stop.
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "RISK_LOG.json"
USER_TZ = dt.timezone(dt.timedelta(hours=1))
RISK_PCT = {"scalp": 0.5, "intraday": 1.0}
MAX_OPEN = 2
MAX_DAILY_LOSS_PCT = 3.0
MAX_CONSECUTIVE_LOSSES = 2


def load_trades():
    try:
        return json.loads(LOG_PATH.read_text()).get("trades", [])
    except (OSError, ValueError):
        return []


def local_day(stamp):
    return dt.datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(USER_TZ).date()


def status(now=None):
    # Returns the lockout state; the day rolls over at midnight UTC+1 and only that day's closed trades count.
    now = now or dt.datetime.now(dt.timezone.utc)
    today = now.astimezone(USER_TZ).date()
    trades = load_trades()
    open_trades = [t for t in trades if not t.get("closed")]
    closed_today = sorted((t for t in trades if t.get("closed") and local_day(t["closed"]) == today),
                          key=lambda t: t["closed"])
    daily_pct = sum(t["r"] * t.get("risk_pct", RISK_PCT.get(t.get("type", "").lower(), 0.5)) for t in closed_today)
    streak = 0
    for t in reversed(closed_today):
        if t["r"] < 0:
            streak += 1
        else:
            break
    reasons = []
    if len(open_trades) >= MAX_OPEN:
        reasons.append(f"{len(open_trades)} trades already open (max {MAX_OPEN})")
    if daily_pct <= -MAX_DAILY_LOSS_PCT:
        reasons.append(f"daily loss {daily_pct:.2f}% reached the {MAX_DAILY_LOSS_PCT:.0f}% cap")
    if streak >= MAX_CONSECUTIVE_LOSSES:
        reasons.append(f"{streak} losses in a row today - stop for the day")
    return {"locked": bool(reasons), "reasons": reasons, "open": [t["coin"] for t in open_trades],
            "daily_pct": round(daily_pct, 2), "streak": streak, "closed_today": len(closed_today)}


def line(state=None):
    s = state or status()
    head = "RISK LOCKED - do not take new trades: " + "; ".join(s["reasons"]) if s["locked"] else "RISK OK"
    return (f"{head} | open {len(s['open'])}/{MAX_OPEN} {s['open']} | today {s['daily_pct']:+.2f}% "
            f"({s['closed_today']} closed, {s['streak']} losing in a row)")


def size_line(coin_type, entry, stop):
    # Position size as a fraction of balance: risk% divided by the stop distance in %.
    risk = RISK_PCT.get(coin_type.lower(), 0.5)
    dist = abs(entry - stop) / entry * 100
    return f"risk {risk}% of balance; notional = balance x {risk / dist:.2f} (stop {dist:.2f}% away)" if dist else ""


def main():
    s = status()
    print(line(s))
    sys.exit(1 if s["locked"] else 0)


if __name__ == "__main__":
    main()
