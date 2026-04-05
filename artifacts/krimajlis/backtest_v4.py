import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import time

POLYGON_KEY = "7aHECnScfzACOtWgyJl_89ynJWObOpCf"

def fetch_polygon_daily(ticker, years=5):
    try:
        end = datetime.now()
        start = end - timedelta(days=years*365)
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"
        params = {'adjusted': 'true', 'sort': 'asc', 'limit': 50000, 'apiKey': POLYGON_KEY}
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        if not data.get('results'):
            return None
        df = pd.DataFrame(data['results'])
        df['date'] = pd.to_datetime(df['t'], unit='ms').dt.date
        df.set_index('date', inplace=True)
        series = df['c']
        return series if len(series) >= 100 else None
    except Exception:
        return None

def fetch_yfinance_hourly(ticker, days=59):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=f'{days}d', interval='60m', auto_adjust=True)
        if hist.empty or len(hist) < 50:
            return None
        return hist['Close']
    except Exception:
        return None

def fetch_yfinance_daily(ticker, years=5):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=f'{min(years,4)*365}d', interval='1d', auto_adjust=True)
        if hist.empty or len(hist) < 100:
            return None
        return hist['Close']
    except Exception:
        return None

def build_vix_regime(vix_series):
    regimes = {}
    for idx, val in vix_series.items():
        d = idx if isinstance(idx, type(datetime.now().date())) else (idx.date() if hasattr(idx, 'date') else idx)
        regimes[d] = 'RISK_OFF' if val > 20 else 'RISK_ON'
    return regimes

def test_intraday(rel, vix_regimes):
    trigger = fetch_yfinance_hourly(rel['trigger'])
    time.sleep(0.3)
    target = fetch_yfinance_hourly(rel['target'])
    time.sleep(0.3)

    if trigger is None or target is None:
        return {'status': 'NO_DATA'}

    tr  = trigger.pct_change().dropna()
    tgt = target.pct_change().dropna()
    common = tr.index.intersection(tgt.index)
    tr  = tr[common]
    tgt = tgt[common]

    if len(tr) < 30:
        return {'status': 'INSUFFICIENT', 'total': len(tr)}

    threshold = tr.std() * 1.0
    lag   = rel['lag_bars']
    dates = list(tr.index)

    res = {'all': [0, 0], 'off': [0, 0], 'on': [0, 0]}

    for i in range(len(dates) - lag - 1):
        move = tr.iloc[i]
        if abs(move) < threshold:
            continue
        fired = (rel['tdir'] == 'down' and move < -threshold) or \
                (rel['tdir'] == 'up'   and move >  threshold)
        if not fired:
            continue
        if i + lag >= len(tgt):
            continue
        tmove = tgt.iloc[i + lag]
        correct = (rel['rdir'] == 'up'   and tmove > 0) or \
                  (rel['rdir'] == 'down' and tmove < 0)
        ts = dates[i]
        d  = ts.date() if hasattr(ts, 'date') else ts
        regime = vix_regimes.get(d, 'UNK')
        res['all'][1] += 1
        if correct: res['all'][0] += 1
        if regime == 'RISK_OFF':
            res['off'][1] += 1
            if correct: res['off'][0] += 1
        elif regime == 'RISK_ON':
            res['on'][1] += 1
            if correct: res['on'][0] += 1

    if res['all'][1] < 10:
        return {'status': 'INSUFFICIENT', 'total': res['all'][1]}

    def a(r): return round(r[0] / r[1], 3) if r[1] > 0 else 0

    return {
        'status': 'OK', 'name': rel['name'], 'type': rel['type'],
        'stated': rel['stated'],
        'all_acc': a(res['all']), 'all_n': res['all'][1],
        'off_acc': a(res['off']), 'off_n': res['off'][1],
        'on_acc':  a(res['on']),  'on_n':  res['on'][1],
    }

def test_daily(rel, vix_regimes):
    trigger = fetch_polygon_daily(rel['trigger'], years=5)
    if trigger is None:
        trigger = fetch_yfinance_daily(rel['trigger'], years=5)
    time.sleep(0.3)
    target = fetch_polygon_daily(rel['target'], years=5)
    if target is None:
        target = fetch_yfinance_daily(rel['target'], years=5)
    time.sleep(0.3)

    if trigger is None or target is None:
        return {'status': 'NO_DATA'}

    tr  = trigger.pct_change().dropna()
    tgt = target.pct_change().dropna()

    def to_date(idx):
        return [i if isinstance(i, type(datetime.now().date())) else (i.date() if hasattr(i, 'date') else i) for i in idx]

    tr.index  = to_date(tr.index)
    tgt.index = to_date(tgt.index)

    common = set(tr.index).intersection(set(tgt.index))
    tr  = tr[tr.index.isin(common)].sort_index()
    tgt = tgt[tgt.index.isin(common)].sort_index()

    if len(tr) < 50:
        return {'status': 'INSUFFICIENT', 'total': len(tr)}

    threshold = tr.std() * 1.0
    lag   = rel['lag_bars']
    dates = list(tr.index)

    res = {'all': [0, 0], 'off': [0, 0], 'on': [0, 0]}

    for i in range(len(dates) - lag - 1):
        move = tr.iloc[i]
        if abs(move) < threshold:
            continue
        fired = (rel['tdir'] == 'down' and move < -threshold) or \
                (rel['tdir'] == 'up'   and move >  threshold)
        if not fired:
            continue
        if i + lag >= len(tgt):
            continue
        tmove = tgt.iloc[i + lag]
        correct = (rel['rdir'] == 'up'   and tmove > 0) or \
                  (rel['rdir'] == 'down' and tmove < 0)
        d = dates[i]
        regime = vix_regimes.get(d, 'UNK')
        res['all'][1] += 1
        if correct: res['all'][0] += 1
        if regime == 'RISK_OFF':
            res['off'][1] += 1
            if correct: res['off'][0] += 1
        elif regime == 'RISK_ON':
            res['on'][1] += 1
            if correct: res['on'][0] += 1

    if res['all'][1] < 15:
        return {'status': 'INSUFFICIENT', 'total': res['all'][1]}

    def a(r): return round(r[0] / r[1], 3) if r[1] > 0 else 0

    return {
        'status': 'OK', 'name': rel['name'], 'type': rel['type'],
        'stated': rel['stated'],
        'all_acc': a(res['all']), 'all_n': res['all'][1],
        'off_acc': a(res['off']), 'off_n': res['off'][1],
        'on_acc':  a(res['on']),  'on_n':  res['on'][1],
    }


INTRADAY_RELS = [
    {'name': 'HYG → SPY (2h lag)',  'trigger': 'HYG', 'target': 'SPY',  'tdir': 'down', 'rdir': 'down', 'lag_bars': 2,  'stated': 0.82, 'type': 'TRANSMISSION_LAG'},
    {'name': 'HYG → SPY (4h lag)',  'trigger': 'HYG', 'target': 'SPY',  'tdir': 'down', 'rdir': 'down', 'lag_bars': 4,  'stated': 0.82, 'type': 'TRANSMISSION_LAG'},
    {'name': 'HYG → TLT (4h lag)',  'trigger': 'HYG', 'target': 'TLT',  'tdir': 'down', 'rdir': 'up',   'lag_bars': 4,  'stated': 0.74, 'type': 'INSTITUTIONAL_FLOW'},
    {'name': 'HYG → KBE (4h lag)',  'trigger': 'HYG', 'target': 'KBE',  'tdir': 'down', 'rdir': 'down', 'lag_bars': 4,  'stated': 0.72, 'type': 'TRANSMISSION_LAG'},
    {'name': 'HYG → EEM (6h lag)',  'trigger': 'HYG', 'target': 'EEM',  'tdir': 'down', 'rdir': 'down', 'lag_bars': 6,  'stated': 0.72, 'type': 'INSTITUTIONAL_FLOW'},
    {'name': 'HYG → AGG (4h lag)',  'trigger': 'HYG', 'target': 'AGG',  'tdir': 'down', 'rdir': 'up',   'lag_bars': 4,  'stated': 0.76, 'type': 'INSTITUTIONAL_FLOW'},
    {'name': 'SPY → EWJ (8h lag)',  'trigger': 'SPY', 'target': 'EWJ',  'tdir': 'down', 'rdir': 'down', 'lag_bars': 8,  'stated': 0.81, 'type': 'INSTITUTIONAL_FLOW'},
    {'name': 'SPY → EEM (6h lag)',  'trigger': 'SPY', 'target': 'EEM',  'tdir': 'down', 'rdir': 'down', 'lag_bars': 6,  'stated': 0.77, 'type': 'INSTITUTIONAL_FLOW'},
    {'name': 'SPY → GLD (4h lag)',  'trigger': 'SPY', 'target': 'GLD',  'tdir': 'down', 'rdir': 'up',   'lag_bars': 4,  'stated': 0.71, 'type': 'TRANSMISSION_LAG'},
    {'name': 'SPY → GLD (8h lag)',  'trigger': 'SPY', 'target': 'GLD',  'tdir': 'down', 'rdir': 'up',   'lag_bars': 8,  'stated': 0.71, 'type': 'TRANSMISSION_LAG'},
    {'name': 'SPY → XLK (2h lag)',  'trigger': 'SPY', 'target': 'XLK',  'tdir': 'down', 'rdir': 'down', 'lag_bars': 2,  'stated': 0.83, 'type': 'TRANSMISSION_LAG'},
    {'name': 'SPY → JETS (6h lag)', 'trigger': 'SPY', 'target': 'JETS', 'tdir': 'down', 'rdir': 'down', 'lag_bars': 6,  'stated': 0.74, 'type': 'SUPPLY_CHAIN_ECHO'},
    {'name': 'SPY → VNQ (4h lag)',  'trigger': 'SPY', 'target': 'VNQ',  'tdir': 'down', 'rdir': 'down', 'lag_bars': 4,  'stated': 0.73, 'type': 'TRANSMISSION_LAG'},
    {'name': 'SPY → XME (8h lag)',  'trigger': 'SPY', 'target': 'XME',  'tdir': 'down', 'rdir': 'down', 'lag_bars': 8,  'stated': 0.71, 'type': 'SUPPLY_CHAIN_ECHO'},
    {'name': 'GLD → GDX (2h lag)',  'trigger': 'GLD', 'target': 'GDX',  'tdir': 'up',   'rdir': 'up',   'lag_bars': 2,  'stated': 0.79, 'type': 'TRANSMISSION_LAG'},
    {'name': 'GLD → GDX (4h lag)',  'trigger': 'GLD', 'target': 'GDX',  'tdir': 'up',   'rdir': 'up',   'lag_bars': 4,  'stated': 0.79, 'type': 'TRANSMISSION_LAG'},
    {'name': 'GLD → SLV (2h lag)',  'trigger': 'GLD', 'target': 'SLV',  'tdir': 'up',   'rdir': 'up',   'lag_bars': 2,  'stated': 0.78, 'type': 'TRANSMISSION_LAG'},
    {'name': 'GLD → AGG (6h lag)',  'trigger': 'GLD', 'target': 'AGG',  'tdir': 'up',   'rdir': 'up',   'lag_bars': 6,  'stated': 0.70, 'type': 'INSTITUTIONAL_FLOW'},
    {'name': 'SPY → EWJ (12h lag)', 'trigger': 'SPY', 'target': 'EWJ',  'tdir': 'down', 'rdir': 'down', 'lag_bars': 12, 'stated': 0.81, 'type': 'INSTITUTIONAL_FLOW'},
    {'name': 'HYG → SPY (6h lag)',  'trigger': 'HYG', 'target': 'SPY',  'tdir': 'down', 'rdir': 'down', 'lag_bars': 6,  'stated': 0.82, 'type': 'TRANSMISSION_LAG'},
]

DAILY_RELS = [
    {'name': 'SPY → GLD daily T+1', 'trigger': 'SPY', 'target': 'GLD', 'tdir': 'down', 'rdir': 'up',   'lag_bars': 1, 'stated': 0.71, 'type': 'TRANSMISSION_LAG'},
    {'name': 'GLD → GDX daily T+1', 'trigger': 'GLD', 'target': 'GDX', 'tdir': 'up',   'rdir': 'up',   'lag_bars': 1, 'stated': 0.79, 'type': 'TRANSMISSION_LAG'},
    {'name': 'HYG → SPY daily T+1', 'trigger': 'HYG', 'target': 'SPY', 'tdir': 'down', 'rdir': 'down', 'lag_bars': 1, 'stated': 0.82, 'type': 'TRANSMISSION_LAG'},
    {'name': 'SPY → EWJ daily T+1', 'trigger': 'SPY', 'target': 'EWJ', 'tdir': 'down', 'rdir': 'down', 'lag_bars': 1, 'stated': 0.81, 'type': 'INSTITUTIONAL_FLOW'},
    {'name': 'GLD → AGG daily T+1', 'trigger': 'GLD', 'target': 'AGG', 'tdir': 'up',   'rdir': 'up',   'lag_bars': 1, 'stated': 0.70, 'type': 'INSTITUTIONAL_FLOW'},
    {'name': 'SPY → EEM daily T+1', 'trigger': 'SPY', 'target': 'EEM', 'tdir': 'down', 'rdir': 'down', 'lag_bars': 1, 'stated': 0.77, 'type': 'INSTITUTIONAL_FLOW'},
    {'name': 'HYG → TLT daily T+1', 'trigger': 'HYG', 'target': 'TLT', 'tdir': 'down', 'rdir': 'up',   'lag_bars': 1, 'stated': 0.74, 'type': 'INSTITUTIONAL_FLOW'},
    {'name': 'GLD → SLV daily T+1', 'trigger': 'GLD', 'target': 'SLV', 'tdir': 'up',   'rdir': 'up',   'lag_bars': 1, 'stated': 0.78, 'type': 'TRANSMISSION_LAG'},
    {'name': 'SPY → XLK daily T+1', 'trigger': 'SPY', 'target': 'XLK', 'tdir': 'down', 'rdir': 'down', 'lag_bars': 1, 'stated': 0.83, 'type': 'TRANSMISSION_LAG'},
    {'name': 'HYG → EEM daily T+1', 'trigger': 'HYG', 'target': 'EEM', 'tdir': 'down', 'rdir': 'down', 'lag_bars': 1, 'stated': 0.72, 'type': 'INSTITUTIONAL_FLOW'},
]


print("=" * 75)
print("KRIMAJLIS BACKTEST v4")
print("Intraday: yfinance 60m x59d | Daily: Polygon 5yr | Regime: VIX>20")
print(f"Run: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 75)

print("\nBuilding VIX regime from Polygon 5-year daily...")
vix_poly = fetch_polygon_daily('VIX', years=5)
if vix_poly is None:
    print("Polygon VIX unavailable, using yfinance...")
    vix_yf = fetch_yfinance_daily('^VIX', years=4)
    vix_regimes = build_vix_regime(vix_yf) if vix_yf is not None else {}
else:
    vix_regimes = build_vix_regime(vix_poly)

off = sum(1 for v in vix_regimes.values() if v == 'RISK_OFF')
on  = sum(1 for v in vix_regimes.values() if v == 'RISK_ON')
if off + on > 0:
    print(f"Regime: {off} RISK_OFF / {on} RISK_ON ({off/(off+on)*100:.1f}% RISK_OFF)")
else:
    print("No regime data")

print(f"\n{'Relationship':<38} {'All':>7} {'R_OFF':>8} {'R_ON':>7} {'N':>5}  Status")
print("-" * 78)

all_results = []

print("\n-- INTRADAY (60-minute bars, 59 days) --")
for rel in INTRADAY_RELS:
    r = test_intraday(rel, vix_regimes)
    if r['status'] != 'OK':
        n = r.get('total', 0)
        print(f"{rel['name']:<38} {r['status']:>7}" + (f" ({n} obs)" if n else ""))
        continue
    a   = f"{r['all_acc']*100:.1f}%"
    ro  = f"{r['off_acc']*100:.1f}%" if r['off_n'] >= 5 else "n/a"
    ron = f"{r['on_acc']*100:.1f}%"  if r['on_n']  >= 5 else "n/a"
    v   = "✓ VALID" if r['all_acc'] >= 0.58 else ("✓ R_OFF" if r['off_acc'] >= 0.62 and r['off_n'] >= 5 else "✗ WEAK")
    print(f"{rel['name']:<38} {a:>7} {ro:>8} {ron:>7} {r['all_n']:>5}  {v}")
    all_results.append(r)

print("\n-- DAILY (5-year Polygon + yfinance fallback) --")
for rel in DAILY_RELS:
    r = test_daily(rel, vix_regimes)
    if r['status'] != 'OK':
        n = r.get('total', 0)
        print(f"{rel['name']:<38} {r['status']:>7}" + (f" ({n} obs)" if n else ""))
        continue
    a   = f"{r['all_acc']*100:.1f}%"
    ro  = f"{r['off_acc']*100:.1f}%" if r['off_n'] >= 10 else "n/a"
    ron = f"{r['on_acc']*100:.1f}%"  if r['on_n']  >= 10 else "n/a"
    v   = "✓ VALID" if r['all_acc'] >= 0.58 else ("✓ R_OFF" if r['off_acc'] >= 0.62 and r['off_n'] >= 10 else "✗ WEAK")
    print(f"{rel['name']:<38} {a:>7} {ro:>8} {ron:>7} {r['all_n']:>5}  {v}")
    all_results.append(r)

print("\n" + "=" * 75)
print("SUMMARY")
print("=" * 75)

ok = [r for r in all_results if r['status'] == 'OK']
if ok:
    validated    = [r for r in ok if r['all_acc'] >= 0.58]
    avg_all      = sum(r['all_acc'] for r in ok) / len(ok)
    ro_ok        = [r for r in ok if r['off_n'] >= 5]
    avg_ro       = sum(r['off_acc'] for r in ro_ok) / len(ro_ok) if ro_ok else 0
    validated_ro = [r for r in ro_ok if r['off_acc'] >= 0.62]

    print(f"Total tested:                {len(ok)}/30")
    print(f"Validated overall (≥58%):    {len(validated)}/{len(ok)}")
    print(f"Validated RISK_OFF (≥62%):   {len(validated_ro)}/{len(ro_ok)}")
    print(f"Overall accuracy:            {avg_all*100:.1f}%")
    print(f"RISK_OFF accuracy:           {avg_ro*100:.1f}%")

    print("\nBy type — RISK_OFF accuracy:")
    for t in ['TRANSMISSION_LAG', 'INSTITUTIONAL_FLOW', 'SUPPLY_CHAIN_ECHO']:
        tr = [r for r in ro_ok if r['type'] == t]
        if tr:
            ta = sum(r['off_acc'] for r in tr) / len(tr)
            tv = sum(1 for r in tr if r['off_acc'] >= 0.62)
            print(f"  {t:<25}: {ta*100:.1f}%  ({tv}/{len(tr)} validated)")

    print("\nTop 7 RISK_OFF:")
    top = sorted(ro_ok, key=lambda x: x['off_acc'], reverse=True)[:7]
    for r in top:
        print(f"  {r['name']:<40}: {r['off_acc']*100:.1f}%  ({r['off_n']} obs)")

    print(f"\nKRIMAJLIS RISK_OFF ACCURACY:  {avg_ro*100:.1f}%")
    print(f"KRIMAJLIS OVERALL ACCURACY:   {avg_all*100:.1f}%")

    if avg_ro >= 0.70:
        print("\n✓ ACQUISITION GRADE — RISK_OFF accuracy exceeds 70%")
    elif avg_ro >= 0.62:
        print("\n~ NEAR GRADE — RISK_OFF accuracy exceeds 62%")
    else:
        print("\n✗ BELOW GRADE")

print(f"\nDone: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 75)
