"""Price precision shared by payloads, copy text and the risk log."""
import math

PRICE_SIG_FIGS = 6
PRICE_MIN_DECIMALS = 4


def price_decimals(value):
    # At least four decimals, more for cheap coins so six significant figures survive.
    if not value:
        return PRICE_MIN_DECIMALS
    return max(PRICE_MIN_DECIMALS, PRICE_SIG_FIGS - 1 - math.floor(math.log10(abs(value))))


def round_price(value):
    return None if value is None else round(float(value), price_decimals(float(value)))


def fmt_price(value):
    return "none" if value is None else f"{float(value):.{price_decimals(float(value))}f}"
