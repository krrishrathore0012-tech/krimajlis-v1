"""
backtest_v6.py — Kryssalis Daily-Only Backtest
═══════════════════════════════════════════════════════════════════
Identical to backtest_v5.py with one change:
  - INTRADAY_RELS removed entirely
  - test_intraday() removed entirely
  - fetch_yfinance_hourly() removed entirely
  - Runs ONLY the 15 DAILY_RELS via test_daily()

All four v5 fixes retained:
  FIX 1 — Trigger threshold: 1.5σ (RISK_OFF) / 2.0σ (RISK_ON)
  FIX 2 — Lag window [0.5×, 2.0×] lag_bars, best-bar-in-window
  FIX 3 — Minimum target move 0.3%
  FIX 4 — Regime-specific threshold tightening
═══════════════════════════════════════════════════════════════════
"""

import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import time
import json

POLYGON_KEY = "7aHECnScfzACOtWgyJl_89ynJWObOpCf"

# ── FIX 1+4: Threshold parameters ─────────────────────────────────
TRIGGER_THRESHOLD_SIGMA   = 1.5   # was 1.0 in v4
TRIGGER_THRESHOLD_RISK_ON = 2.0   # stricter in low-stress regimes
MIN_TARGET_MOVE_PCT       = 0.003 # FIX 3: 0.3% minimum target move

# ── FIX 2: Lag window multipliers ─────────────────────────────────
LAG_WINDOW_FACTOR_MIN    = 0.5   # check from lag*0.5
LAG_WINDOW_FACTOR_MAX    = 2.0   # check up to lag*2.0
LAG_WINDOW_ABSOLUTE_MAX  = 16    # cap at 16 bars regardless


def normalize_date(ts):
    try:
        if hasattr(ts, 'tzinfo') and ts.tzinfo is not None:
            ts = ts.tz_convert('UTC').tz_localize(None)
        if hasattr(ts, 'date'):
            return ts.date()
        return ts
    except Exception:
        try:
            return ts.date()
        except Exception:
            return ts


def fetch_polygon_daily(ticker, years=5):
    try:
        end   = datetime.now()
        start = end - timedelta(days=years * 365)
        url   = (f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day"
                 f"/{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}")
        params = {'adjusted':'true','sort':'asc','limit':50000,'apiKey':POLYGON_KEY}
        r    = requests.get(url, params=params, timeout=15)
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


def fetch_yfinance_daily(ticker, years=5):
    try:
        t    = yf.Ticker(ticker)
        hist = t.history(period=f'{min(years,4)*365}d', interval='1d', auto_adjust=True)
        if hist.empty or len(hist) < 100:
            return None
        return hist['Close']
    except Exception:
        return None


def build_vix_regime(vix_series):
    regimes = {}
    for idx, val in vix_series.items():
        d = normalize_date(idx)
        regimes[d] = 'RISK_OFF' if val > 20 else 'RISK_ON'
    return regimes


def _best_in_window(tgt_series, i, lag_bars):
    """
    FIX 2: Return the best-signed move within the lag window.
    Checks from lag_min to lag_max bars after trigger.
    """
    lag_min = max(1, int(lag_bars * LAG_WINDOW_FACTOR_MIN))
    lag_max = min(LAG_WINDOW_ABSOLUTE_MAX, int(lag_bars * LAG_WINDOW_FACTOR_MAX))
    best = 0.0
    for offset in range(lag_min, lag_max + 1):
        if i + offset < len(tgt_series):
            move = tgt_series.iloc[i + offset]
            if abs(move) > abs(best):
                best = move
    return best


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
        return [normalize_date(i) for i in idx]

    tr.index  = to_date(tr.index)
    tgt.index = to_date(tgt.index)

    common = set(tr.index).intersection(set(tgt.index))
    tr  = tr[tr.index.isin(common)].sort_index()
    tgt = tgt[tgt.index.isin(common)].sort_index()

    if len(tr) < 50:
        return {'status': 'INSUFFICIENT', 'total': len(tr)}

    lag   = rel['lag_bars']
    dates = list(tr.index)

    res = {'all': [0,0], 'off': [0,0], 'on': [0,0]}

    for i in range(len(dates) - LAG_WINDOW_ABSOLUTE_MAX - 1):
        move   = tr.iloc[i]
        d      = normalize_date(dates[i])
        regime = vix_regimes.get(d, 'UNK')

        # FIX 4: regime-specific threshold
        threshold = tr.std() * (TRIGGER_THRESHOLD_RISK_ON
                                if regime == 'RISK_ON'
                                else TRIGGER_THRESHOLD_SIGMA)

        if abs(move) < threshold:
            continue

        fired = (rel['tdir'] == 'down' and move < -threshold) or \
                (rel['tdir'] == 'up'   and move >  threshold)
        if not fired:
            continue

        # FIX 2: best move in lag window
        tmove = _best_in_window(tgt, i, lag)

        # FIX 3: minimum target move
        if abs(tmove) < MIN_TARGET_MOVE_PCT:
            continue

        correct = (rel['rdir'] == 'up'   and tmove > 0) or \
                  (rel['rdir'] == 'down' and tmove < 0)

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

    def a(r): return round(r[0]/r[1], 3) if r[1] > 0 else 0

    return {
        'status':  'OK',
        'name':    rel['name'],
        'type':    rel['type'],
        'stated':  rel['stated'],
        'all_acc': a(res['all']), 'all_n':  res['all'][1],
        'off_acc': a(res['off']), 'off_n':  res['off'][1],
        'on_acc':  a(res['on']),  'on_n':   res['on'][1],
    }


# ── Daily relationship library (15 relationships) ─────────────────

DAILY_RELS = [
    {'name':'SPY → GLD daily T+1',  'trigger':'SPY','target':'GLD', 'tdir':'down','rdir':'up',  'lag_bars':1,'stated':0.71,'type':'TRANSMISSION_LAG'},
    {'name':'GLD → GDX daily T+1',  'trigger':'GLD','target':'GDX', 'tdir':'up',  'rdir':'up',  'lag_bars':1,'stated':0.79,'type':'TRANSMISSION_LAG'},
    {'name':'GLD → AGG daily T+1',  'trigger':'GLD','target':'AGG', 'tdir':'up',  'rdir':'up',  'lag_bars':1,'stated':0.70,'type':'INSTITUTIONAL_FLOW'},
    {'name':'HYG → SPY daily T+1',  'trigger':'HYG','target':'SPY', 'tdir':'down','rdir':'down','lag_bars':1,'stated':0.82,'type':'TRANSMISSION_LAG'},
    {'name':'HYG → SPY daily T+2',  'trigger':'HYG','target':'SPY', 'tdir':'down','rdir':'down','lag_bars':2,'stated':0.82,'type':'TRANSMISSION_LAG'},
    {'name':'SPY → EWJ daily T+1',  'trigger':'SPY','target':'EWJ', 'tdir':'down','rdir':'down','lag_bars':1,'stated':0.81,'type':'INSTITUTIONAL_FLOW'},
    {'name':'SPY → EEM daily T+1',  'trigger':'SPY','target':'EEM', 'tdir':'down','rdir':'down','lag_bars':1,'stated':0.77,'type':'INSTITUTIONAL_FLOW'},
    {'name':'HYG → EEM daily T+1',  'trigger':'HYG','target':'EEM', 'tdir':'down','rdir':'down','lag_bars':1,'stated':0.72,'type':'INSTITUTIONAL_FLOW'},
    {'name':'HYG → TLT daily T+1',  'trigger':'HYG','target':'TLT', 'tdir':'down','rdir':'up',  'lag_bars':1,'stated':0.74,'type':'INSTITUTIONAL_FLOW'},
    {'name':'SPY → XLK daily T+1',  'trigger':'SPY','target':'XLK', 'tdir':'down','rdir':'down','lag_bars':1,'stated':0.83,'type':'TRANSMISSION_LAG'},
    {'name':'GLD → SLV daily T+1',  'trigger':'GLD','target':'SLV', 'tdir':'up',  'rdir':'up',  'lag_bars':1,'stated':0.78,'type':'TRANSMISSION_LAG'},
    {'name':'SPY → JETS daily T+2', 'trigger':'SPY','target':'JETS','tdir':'down','rdir':'down','lag_bars':2,'stated':0.74,'type':'SUPPLY_CHAIN_ECHO'},
    {'name':'SPY → XME daily T+2',  'trigger':'SPY','target':'XME', 'tdir':'down','rdir':'down','lag_bars':2,'stated':0.71,'type':'SUPPLY_CHAIN_ECHO'},
    {'name':'HYG → KBE daily T+1',  'trigger':'HYG','target':'KBE', 'tdir':'down','rdir':'down','lag_bars':1,'stated':0.72,'type':'TRANSMISSION_LAG'},
    {'name':'SPY → VNQ daily T+1',  'trigger':'SPY','target':'VNQ', 'tdir':'down','rdir':'down','lag_bars':1,'stated':0.73,'type':'TRANSMISSION_LAG'},
]


# ── Main ───────────────────────────────────────────────────────────

print("=" * 82)
print("KRYSSALIS BACKTEST v6 — DAILY-ONLY (v5 fixes, 15 relationships)")
print(f"Trigger: {TRIGGER_THRESHOLD_SIGMA}σ (RISK_OFF) / {TRIGGER_THRESHOLD_RISK_ON}σ (RISK_ON)")
print(f"Lag: window [{LAG_WINDOW_FACTOR_MIN}×,{LAG_WINDOW_FACTOR_MAX}×] lag_bars")
print(f"Min target move: {MIN_TARGET_MOVE_PCT*100:.1f}%")
print(f"Run: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 82)

print("\nBuilding VIX regime...")
vix_poly = fetch_polygon_daily('VIX', years=5)
if vix_poly is None:
    print("Polygon VIX unavailable — using yfinance ^VIX...")
    vix_yf      = fetch_yfinance_daily('^VIX', years=4)
    vix_regimes = build_vix_regime(vix_yf) if vix_yf is not None else {}
else:
    vix_regimes = build_vix_regime(vix_poly)

off = sum(1 for v in vix_regimes.values() if v == 'RISK_OFF')
on  = sum(1 for v in vix_regimes.values() if v == 'RISK_ON')
if off + on > 0:
    print(f"Regime: {off} RISK_OFF / {on} RISK_ON ({off/(off+on)*100:.1f}% RISK_OFF)")

print(f"\n{'Relationship':<42} {'All':>7} {'R_OFF (n)':>12} {'R_ON':>7} {'N':>5}  Status")
print("-" * 82)

all_results = []

print("\n-- DAILY (5-year Polygon + yfinance fallback, 15 relationships) --")
for rel in DAILY_RELS:
    r = test_daily(rel, vix_regimes)
    if r['status'] != 'OK':
        n = r.get('total', 0)
        print(f"{rel['name']:<42} {r['status']:>7}" + (f" ({n} obs)" if n else ""))
        continue
    a_str   = f"{r['all_acc']*100:.1f}%"
    ro_str  = f"{r['off_acc']*100:.1f}% ({r['off_n']})" if r['off_n'] >= 10 else f"n/a ({r['off_n']})"
    ron_str = f"{r['on_acc']*100:.1f}%" if r['on_n'] >= 10 else f"n/a ({r['on_n']})"
    v = ("✓ VALID" if r['all_acc'] >= 0.58
         else ("✓ R_OFF" if r['off_acc'] >= 0.62 and r['off_n'] >= 10 else "✗ WEAK"))
    print(f"{rel['name']:<42} {a_str:>7} {ro_str:>12} {ron_str:>7} {r['all_n']:>5}  {v}")
    all_results.append(r)

print("\n" + "=" * 82)
print("SUMMARY — v6 DAILY-ONLY")
print("=" * 82)

ok = [r for r in all_results if r['status'] == 'OK']
if ok:
    validated    = [r for r in ok if r['all_acc'] >= 0.58]
    avg_all      = sum(r['all_acc'] for r in ok) / len(ok)
    ro_ok        = [r for r in ok if r['off_n'] >= 10]
    avg_ro       = sum(r['off_acc'] for r in ro_ok) / len(ro_ok) if ro_ok else 0
    validated_ro_62 = [r for r in ro_ok if r['off_acc'] >= 0.62]
    validated_ro_70 = [r for r in ro_ok if r['off_acc'] >= 0.70]

    print(f"\n  Relationships tested:    15")
    print(f"  Returned OK results:     {len(ok)}/15")
    print(f"  Overall accuracy:        {avg_all*100:.1f}%")
    print(f"  RISK_OFF accuracy:       {avg_ro*100:.1f}%")
    print(f"  Validated ≥58% overall:  {len(validated)}/{len(ok)}")
    print(f"  Validated ≥62% R_OFF:    {len(validated_ro_62)}/{len(ro_ok)}")
    print(f"  Validated ≥70% R_OFF:    {len(validated_ro_70)}/{len(ro_ok)}")

    print(f"\n  By type — RISK_OFF accuracy:")
    for t in ['TRANSMISSION_LAG', 'INSTITUTIONAL_FLOW', 'SUPPLY_CHAIN_ECHO']:
        tr = [r for r in ro_ok if r['type'] == t]
        if tr:
            ta  = sum(r['off_acc'] for r in tr) / len(tr)
            tv62 = sum(1 for r in tr if r['off_acc'] >= 0.62)
            tv70 = sum(1 for r in tr if r['off_acc'] >= 0.70)
            print(f"    {t:<25}: {ta*100:.1f}%  (≥62%: {tv62}/{len(tr)}  ≥70%: {tv70}/{len(tr)})")

    print(f"\n  All 15 signals ranked by RISK_OFF accuracy:")
    top = sorted(ro_ok, key=lambda x: x['off_acc'], reverse=True)
    for r in top:
        marker = "✓✓" if r['off_acc'] >= 0.70 else ("✓" if r['off_acc'] >= 0.62 else "○")
        print(f"    {marker} {r['name']:<44}: {r['off_acc']*100:.1f}% R_OFF  "
              f"{r['all_acc']*100:.1f}% all  (stated {r['stated']*100:.0f}%)  n={r['off_n']}")

    print(f"\n  KRYSSALIS v6 RISK_OFF ACCURACY:  {avg_ro*100:.1f}%")
    print(f"  KRYSSALIS v6 OVERALL ACCURACY:   {avg_all*100:.1f}%")

    if avg_ro >= 0.70:
        print(f"\n  ✓✓ ACQUISITION GRADE — RISK_OFF ≥70%")
    elif avg_ro >= 0.62:
        print(f"\n  ~ NEAR GRADE — RISK_OFF ≥62%, below 70% target")
    else:
        print(f"\n  ✗ BELOW GRADE — further calibration required")

    output = {
        'version':       'v6',
        'timestamp_utc': datetime.utcnow().isoformat(),
        'scope':         'daily-only (15 relationships)',
        'fixes_applied': ['1.5σ threshold','lag window','0.3% min move','regime threshold'],
        'result': {
            'overall':          round(avg_all, 4),
            'risk_off':         round(avg_ro, 4),
            'total_tested':     len(ok),
            'validated_58_all': len(validated),
            'validated_62_ro':  len(validated_ro_62),
            'validated_70_ro':  len(validated_ro_70),
        },
        'signal_results': [{k: v for k, v in r.items()} for r in ok],
    }
    with open('backtest_v6_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved: backtest_v6_results.json")

print(f"\nDone: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 82)
