"""Ranks a fresh signal: 4H trend tag, 4H zone veto and BTC/ETH confirmation."""
TREND_WITH, TREND_RANGE, TREND_COUNTER = "with", "range", "counter"
TREND_RANK = {TREND_WITH: 0, TREND_RANGE: 1, TREND_COUNTER: 2}
MAJOR_SYMBOLS = ("BTCUSDT", "ETHUSDT")
CONFIRM_ALIGNED, CONFIRM_MIXED, CONFIRM_CONFLICTING = "ALIGNED", "MIXED", "CONFLICTING"


def trend_tag(*, bias4h, direction):
    if bias4h not in ("bullish", "bearish"):
        return TREND_RANGE
    return TREND_WITH if (bias4h == "bullish") == (direction == "long") else TREND_COUNTER


def zone_veto(*, badge, direction):
    # Rule (b): a long into overhead 4H supply, or a short into 4H demand just below, is capped at Watch Only.
    if not badge:
        return None
    blocked_side = "supply" if direction == "long" else "demand"
    if badge.get("side") != blocked_side:
        return None
    return f"{badge['label']} ({badge['distPct']}% away)"


def major_confirmation(*, direction, majors):
    """majors maps BTC/ETH symbol to its 4H structure; the symbol being scored is left out by the caller."""
    if not majors:
        return None
    want, against = ("bullish", "bearish") if direction == "long" else ("bearish", "bullish")
    states = list(majors.values())
    if all(s == want for s in states):
        return CONFIRM_ALIGNED
    if all(s == against for s in states):
        return CONFIRM_CONFLICTING
    return CONFIRM_MIXED


def classify_signal(*, res, mode_data, symbol, majors):
    """Returns the tier fields added to a tradeable scan entry."""
    pos = mode_data.get("position") or mode_data.get("pending") or {}
    direction = pos.get("direction")
    trend = trend_tag(bias4h=res["structure4h"], direction=direction)
    veto = zone_veto(badge=res.get("zone4hBadge"), direction=direction)
    others = {s: v for s, v in majors.items() if s != symbol}
    return {
        "trend": trend,
        "lowerTier": trend == TREND_COUNTER,
        "zoneVeto": veto,
        "btcEth": major_confirmation(direction=direction, majors=others),
    }
