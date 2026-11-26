"""Checks each builder on the SOL 23 Nov spike and that no builder can see the future."""
import datetime as dt
import zoneVariants as zv
import strategyBacktest as sb
import apiAnalyze as api


def stamp(t):
    return dt.datetime.fromtimestamp(t / 1000, dt.timezone.utc).strftime("%m-%d %H:%M")


frames = api.build_frames(api.load_history("SOLUSDT"))
for name, builder in zv.BUILDERS.items():
    sb.source_zones = builder
    print(f"== {name}")
    for interval in ("15", "60", "240"):
        for z in builder(frames[interval], interval):
            day = stamp(z.t)[:5]
            if (z.kind == "supply" and day == "11-23" and z.high > 74) or (z.kind == "demand" and day == "11-25" and z.low < 67):
                print(f"  {interval:>3} {z.kind} {z.low:.2f}-{z.high:.2f} candle {stamp(z.t)} usable {stamp(z.known_t)}")
    for high_tf, low_tf in (("60", "15"), ("240", "60")):
        for z in sb.refined_zones(frames[high_tf], high_tf, frames[low_tf], low_tf):
            if z.kind == "supply" and stamp(z.t)[:5] == "11-23" and z.high > 74:
                print(f"  {high_tf}->{low_tf} supply {z.low:.2f}-{z.high:.2f} refined={z.refined}")
    for interval in ("15", "60", "240"):
        candles = frames[interval][-3000:]
        full = builder(candles, interval)
        for cut in (len(candles) - 700, len(candles) - 211, len(candles) - 37):
            end = candles[cut - 1].t + sb.INTERVAL_MS[interval]
            key = lambda zs: sorted((z.kind, z.t, z.known_t, z.low, z.high) for z in zs if z.known_t <= end)
            assert key(builder(candles[:cut], interval)) == key(full), f"lookahead {name} {interval} {cut}"
    print("  no-lookahead check passed (15m, 1H, 4H; 3 cut points)")
print(f"== {zv.SPLIT}")
zv.use(zv.SPLIT)
for high_tf, low_tf in (("60", "15"), ("240", "60")):
    for z in sb.refined_zones(frames[high_tf], high_tf, frames[low_tf], low_tf):
        if z.kind == "supply" and stamp(z.t)[:5] in ("11-23", "11-24") and z.high > 71:
            print(f"  {high_tf}->{low_tf} supply {z.low:.2f}-{z.high:.2f} candle {stamp(z.t)} refined={z.refined}")
