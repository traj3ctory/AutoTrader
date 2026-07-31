import urllib.request, json, statistics

def fetch(symbol, interval, limit=1000):
    url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval={interval}&limit={limit}"
    with urllib.request.urlopen(url, timeout=20) as r:
        d = json.load(r)
    rows = d['result']['list'][::-1]
    return [{'t':int(x[0]),'o':float(x[1]),'h':float(x[2]),'l':float(x[3]),'c':float(x[4]),'v':float(x[5])} for x in rows]

def ema_series(vals, p):
    if len(vals) < p: return [None]*len(vals)
    k = 2/(p+1); out=[None]*len(vals)
    e = sum(vals[:p])/p; out[p-1]=e
    for i in range(p,len(vals)):
        e = vals[i]*k + e*(1-k); out[i]=e
    return out

def atr_at(c, i, period=14):
    if i < period: return None
    trs=[]
    for j in range(i-period+1, i+1):
        trs.append(max(c[j]['h']-c[j]['l'], abs(c[j]['h']-c[j-1]['c']), abs(c[j]['l']-c[j-1]['c'])))
    return sum(trs)/len(trs)

def dir_eff(c, i, n=8):
    if i < n: return 0
    seg = c[i-n+1:i+1]
    net = abs(seg[-1]['c'] - seg[0]['o'])
    tot = sum(x['h']-x['l'] for x in seg)
    return net/tot if tot>0 else 0

def vwap_at(c, i, n=24):
    if i < n: return None
    seg = c[i-n+1:i+1]
    num = sum(((x['h']+x['l']+x['c'])/3)*x['v'] for x in seg)
    den = sum(x['v'] for x in seg)
    return num/den if den else None

def simulate(c, i, direction, atr, horizon=24, rr=1.5):
    """Enter at close of bar i. SL=1*ATR, TP=rr*ATR. Return R outcome."""
    entry = c[i]['c']
    if direction == 'long':
        sl, tp = entry - atr, entry + rr*atr
    else:
        sl, tp = entry + atr, entry - rr*atr
    for j in range(i+1, min(i+1+horizon, len(c))):
        if direction=='long':
            if c[j]['l'] <= sl: return -1.0
            if c[j]['h'] >= tp: return rr
        else:
            if c[j]['h'] >= sl: return -1.0
            if c[j]['l'] <= tp: return rr
    # unresolved: mark to market
    final = c[min(i+horizon, len(c)-1)]['c']
    return ((final-entry) if direction=='long' else (entry-final))/atr

SYMBOLS = ['HYPEUSDT','XRPUSDT','DOGEUSDT','SOLUSDT','AVAXUSDT','ZECUSDT','JTOUSDT','BNBUSDT']
GATE = 0.4

print(f"{'SYMBOL':10} {'BARS':>6} {'ALL n':>7} {'ALL avgR':>9} {'ALL win%':>9} {'GATED n':>8} {'GATE avgR':>10} {'GATE win%':>10}")
tot_all, tot_gated = [], []
for sym in SYMBOLS:
    c = fetch(sym,'60',1000)
    closes=[x['c'] for x in c]
    e9, e20 = ema_series(closes,9), ema_series(closes,20)
    all_r, gated_r = [], []
    for i in range(40, len(c)-25):
        a = atr_at(c,i)
        if not a: continue
        v = vwap_at(c,i)
        if not v: continue
        eff = dir_eff(c,i)
        price = c[i]['c']
        direction = 'long' if price > v else 'short'
        r = simulate(c,i,direction,a)
        all_r.append(r)
        # gated: efficiency must pass, and EMA slope must agree with direction
        if e9[i] and e9[i-3]:
            slope_up = e9[i] > e9[i-3]
            agrees = (direction=='long' and slope_up) or (direction=='short' and not slope_up)
            if eff >= GATE and agrees:
                gated_r.append(r)
    def stats(rs):
        if not rs: return (0,0,0)
        return (len(rs), sum(rs)/len(rs), 100*sum(1 for x in rs if x>0)/len(rs))
    an,aa,aw = stats(all_r); gn,ga,gw = stats(gated_r)
    tot_all += all_r; tot_gated += gated_r
    print(f"{sym:10} {len(c):>6} {an:>7} {aa:>9.3f} {aw:>8.1f}% {gn:>8} {ga:>10.3f} {gw:>9.1f}%")

def stats(rs):
    if not rs: return (0,0,0)
    return (len(rs), sum(rs)/len(rs), 100*sum(1 for x in rs if x>0)/len(rs))
an,aa,aw = stats(tot_all); gn,ga,gw = stats(tot_gated)
print("-"*95)
print(f"{'TOTAL':10} {'':>6} {an:>7} {aa:>9.3f} {aw:>8.1f}% {gn:>8} {ga:>10.3f} {gw:>9.1f}%")
print()
print(f"Gate selectivity: {100*gn/an:.1f}% of bars pass ({gn} of {an})")
print(f"Edge from gating: {ga-aa:+.3f}R per trade vs ungated baseline")
