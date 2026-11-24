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


DEFAULT_LOG = {
    "version": 1,
    "principle": "Log every trade actually taken. Leave closed and r null while it is open; fill both when it closes. r is the net result in R (negative for a loss).",
    "trades": [],
}


def load_doc():
    try:
        doc = json.loads(LOG_PATH.read_text())
        if isinstance(doc, dict) and isinstance(doc.get("trades"), list):
            return doc
    except (OSError, ValueError):
        pass
    return dict(DEFAULT_LOG, trades=[])


def save_doc(doc):
    LOG_PATH.write_text(json.dumps(doc, indent=2) + "\n")


def load_trades():
    return load_doc().get("trades", [])


def utc_now_iso():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_coin(raw):
    coin = raw.strip().upper()
    if not coin.endswith(".P"):
        coin = f"{coin}USDT.P" if not coin.endswith("USDT") else f"{coin}.P"
    return coin


def parse_opt(args, flag):
    if flag not in args:
        return None, args
    idx = args.index(flag)
    if idx + 1 >= len(args):
        raise ValueError(f"Missing value after {flag}")
    val = args[idx + 1]
    rest = args[:idx] + args[idx + 2:]
    return val, rest


def cmd_open(args):
    risk_raw, pos = parse_opt(args, "--risk-pct")
    if len(pos) != 4:
        raise ValueError("Usage: riskGuard.py open <COIN> <scalp|intraday> <entry> <stop> [--risk-pct X]")
    coin = normalize_coin(pos[0])
    trade_type = pos[1].strip().lower()
    if trade_type not in RISK_PCT:
        raise ValueError(f"Trade type must be one of {list(RISK_PCT)}, got {pos[1]!r}")
    entry = float(pos[2])
    stop = float(pos[3])
    risk_pct = float(risk_raw) if risk_raw is not None else RISK_PCT[trade_type]
    doc = load_doc()
    doc["trades"].append({
        "coin": coin,
        "type": trade_type,
        "opened": utc_now_iso(),
        "entry": entry,
        "stop": stop,
        "risk_pct": risk_pct,
        "closed": None,
        "r": None,
    })
    save_doc(doc)
    print(f"Logged OPEN: {coin} {trade_type} entry={entry} stop={stop} risk={risk_pct}%")
    sizing = size_line(trade_type, entry, stop)
    if sizing:
        print(sizing)
    s = status()
    print(line(s))
    return 1 if s["locked"] else 0


def cmd_close(args):
    fill_raw, pos = parse_opt(args, "--fill-price")
    if len(pos) != 2:
        raise ValueError("Usage: riskGuard.py close <COIN> <R> [--fill-price X]")
    coin = normalize_coin(pos[0])
    r_val = float(pos[1])
    doc = load_doc()
    match = None
    for t in reversed(doc["trades"]):
        if not t.get("closed") and normalize_coin(t.get("coin", "")) == coin:
            match = t
            break
    if match is None:
        raise ValueError(f"No open trade found for {coin}")
    match["closed"] = utc_now_iso()
    match["r"] = r_val
    if fill_raw is not None:
        match["fill_price"] = float(fill_raw)
    save_doc(doc)
    print(f"Logged CLOSE: {coin} r={r_val:+.2f}R")
    s = status()
    print(line(s))
    return 1 if s["locked"] else 0


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
    args = sys.argv[1:]
    if not args:
        s = status()
        print(line(s))
        sys.exit(1 if s["locked"] else 0)
    cmd = args[0].lower()
    try:
        if cmd == "open":
            sys.exit(cmd_open(args[1:]))
        if cmd == "close":
            sys.exit(cmd_close(args[1:]))
        raise ValueError(f"Unknown command {args[0]!r}. Use: status (no args), open, or close")
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
