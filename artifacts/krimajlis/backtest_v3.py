import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import yfinance as yf

POLYGON_KEY = "7aHECCnScfzACOtWgyJl_89ynJWObOpCf"

def fetch_polygon_hourly(ticker, days=500):
    try:
        end = datetime.now()
        start = end - timedelta(days=days)
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/hour/{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"
        params = {
            'adjusted': 'true',
            'sort': 'asc',
            'limit': 50000,
            'apiKey': POLYGON_KEY
        }
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        if data.get('status') == 'ERROR' or not data.get('results'):
            return None
        df = pd.DataFrame(data['results'])
        df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
        df.set_index('timestamp', inplace=True)
        series = df['c']
        if len(series) < 100:
            return None
        return series
    except Exception as e:
        print(f"Polygon fetch failed for {ticker}: {e}")
        return None

def fetch_yfinance_daily(ticker, years=4):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=f'{years*365}d', interval='1d', auto_adjust=True)
        if hist.empty or len(hist) < 100:
            return None
        return hist['Close']
    except Exception:
        return None

def compute_vix_regime_daily(vix_series):
    regimes = {}
    for date, vix in vix_series.items():
        d = date.date() if hasattr(date, 'date') else date
        regimes[d] = 'RISK_OFF' if vix > 20 else 'RISK_ON'
    return regimes

def compute_vix_regime_hourly(vix_hourly):
    regimes = {}
    for ts, vix in vix_hourly.items():
        d = ts.date() if hasattr(ts, 'date') else ts
        if d not in regimes:
            regimes[d] = 'RISK_OFF' if vix > 20 else 'RISK_ON'
    return regimes

def test_intraday_relationship(rel, vix_regimes, lag_bars):
    trigger_data = fetch_polygon_hourly(rel['trigger'], days=500)
    time.sleep(0.5)
    target_data = fetch_polygon_hourly(rel['target'], days=500)
    time.sleep(0.5)

    if trigger_data is None or target_data is None:
        return {'status': 'NO_DATA'}

    trigger_returns = trigger_data.pct_change().dropna()
    target_returns  = target_data.pct_change().dropna()

    common_idx = trigger_returns.index.intersection(target_returns.index)
    trigger_returns = trigger_returns[common_idx]
    target_returns  = target_returns[common_idx]

    if len(trigger_returns) < 50:
        return {'status': 'INSUFFICIENT'}

    threshold  = trigger_returns.std() * 1.0
    dates_list = list(trigger_returns.index)

    res_all      = {'hits': 0, 'total': 0}
    res_risk_off = {'hits': 0, 'total': 0}
    res_risk_on  = {'hits': 0, 'total': 0}

    for i in range(len(dates_list) - lag_bars - 1):
        move = trigger_returns.iloc[i]
        if abs(move) < threshold:
            continue
        fired = (rel['trigger_dir'] == 'down' and move < -threshold) or \
                (rel['trigger_dir'] == 'up'   and move >  threshold)
        if not fired:
            continue
        if i + lag_bars >= len(target_returns):
            continue
        target_move = target_returns.iloc[i + lag_bars]
        correct = (rel['target_dir'] == 'up'   and target_move > 0) or \
                  (rel['target_dir'] == 'down' and target_move < 0)

        ts = dates_list[i]
        d  = ts.date() if hasattr(ts, 'date') else ts
        regime = vix_regimes.get(d, 'UNKNOWN')

        res_all['total'] += 1
        if correct: res_all['hits'] += 1
        if regime == 'RISK_OFF':
            res_risk_off['total'] += 1
            if correct: res_risk_off['hits'] += 1
        elif regime == 'RISK_ON':
            res_risk_on['total'] += 1
            if correct: res_risk_on['hits'] += 1

    if res_all['total'] < 15:
        return {'status': 'INSUFFICIENT', 'total': res_all['total']}

    def acc(r): return round(r['hits'] / r['total'], 3) if r['total'] > 0 else 0

    return {
        'status': 'OK',
        'name': rel['name'],
        'type': rel['type'],
        'stated': rel['stated_accuracy'],
        'all':      {'acc': acc(res_all),      'hits': res_all['hits'],      'total': res_all['total']},
        'risk_off': {'acc': acc(res_risk_off), 'hits': res_risk_off['hits'], 'total': res_risk_off['total']},
        'risk_on':  {'acc': acc(res_risk_on),  'hits': res_risk_on['hits'],  'total': res_risk_on['total']},
        'validated':          acc(res_all)      >= 0.58,
        'validated_risk_off': acc(res_risk_off) >= 0.62 and res_risk_off['total'] >= 10
    }

INTRADAY_RELATIONSHIPS = [
    {'name': 'HYG falls → SPY falls (2h)',  'trigger': 'HYG', 'target': 'SPY', 'trigger_dir': 'down', 'target_dir': 'down', 'lag_bars': 2,  'stated_accuracy': 0.82, 'type': 'TRANSMISSION_LAG'},
    {'name': 'HYG falls → SPY falls (4h)',  'trigger': 'HYG', 'target': 'SPY', 'trigger_dir': 'down', 'target_dir': 'down', 'lag_bars': 4,  'stated_accuracy': 0.82, 'type': 'TRANSMISSION_LAG'},
    {'name': 'SPY falls → EWJ falls (8h)',  'trigger': 'SPY', 'target': 'EWJ', 'trigger_dir': 'down', 'target_dir': 'down', 'lag_bars': 8,  'stated_accuracy': 0.81, 'type': 'INSTITUTIONAL_FLOW'},
    {'name': 'SPY falls → EEM falls (6h)',  'trigger': 'SPY', 'target': 'EEM', 'trigger_dir': 'down', 'target_dir': 'down', 'lag_bars': 6,  'stated_accuracy': 0.77, 'type': 'INSTITUTIONAL_FLOW'},
    {'name': 'HYG falls → TLT rises (4h)', 'trigger': 'HYG', 'target': 'TLT', 'trigger_dir': 'down', 'target_dir': 'up',   'lag_bars': 4,  'stated_accuracy': 0.74, 'type': 'INSTITUTIONAL_FLOW'},
    {'name': 'SPY falls → GLD rises (4h)', 'trigger': 'SPY', 'target': 'GLD', 'trigger_dir': 'down', 'target_dir': 'up',   'lag_bars': 4,  'stated_accuracy': 0.71, 'type': 'TRANSMISSION_LAG'},
    {'name': 'GLD rises → GDX rises (4h)', 'trigger': 'GLD', 'target': 'GDX', 'trigger_dir': 'up',   'target_dir': 'up',   'lag_bars': 4,  'stated_accuracy': 0.79, 'type': 'TRANSMISSION_LAG'},
    {'name': 'GLD rises → GDX rises (2h)', 'trigger': 'GLD', 'target': 'GDX', 'trigger_dir': 'up',   'target_dir': 'up',   'lag_bars': 2,  'stated_accuracy': 0.79, 'type': 'TRANSMISSION_LAG'},
    {'name': 'HYG falls → KBE falls (4h)', 'trigger': 'HYG', 'target': 'KBE', 'trigger_dir': 'down', 'target_dir': 'down', 'lag_bars': 4,  'stated_accuracy': 0.72, 'type': 'TRANSMISSION_LAG'},
    {'name': 'SPY falls → XLK falls (2h)', 'trigger': 'SPY', 'target': 'XLK', 'trigger_dir': 'down', 'target_dir': 'down', 'lag_bars': 2,  'stated_accuracy': 0.83, 'type': 'TRANSMISSION_LAG'},
    {'name': 'SPY falls → JETS falls (6h)','trigger': 'SPY', 'target': 'JETS','trigger_dir': 'down', 'target_dir': 'down', 'lag_bars': 6,  'stated_accuracy': 0.74, 'type': 'SUPPLY_CHAIN_ECHO'},
    {'name': 'GLD rises → SLV rises (2h)', 'trigger': 'GLD', 'target': 'SLV', 'trigger_dir': 'up',   'target_dir': 'up',   'lag_bars': 2,  'stated_accuracy': 0.78, 'type': 'TRANSMISSION_LAG'},
    {'name': 'HYG falls → EEM falls (6h)', 'trigger': 'HYG', 'target': 'EEM', 'trigger_dir': 'down', 'target_dir': 'down', 'lag_bars': 6,  'stated_accuracy': 0.72, 'type': 'INSTITUTIONAL_FLOW'},
    {'name': 'SPY falls → VNQ falls (4h)', 'trigger': 'SPY', 'target': 'VNQ', 'trigger_dir': 'down', 'target_dir': 'down', 'lag_bars': 4,  'stated_accuracy': 0.73, 'type': 'TRANSMISSION_LAG'},
    {'name': 'HYG falls → AGG rises (4h)', 'trigger': 'HYG', 'target': 'AGG', 'trigger_dir': 'down', 'target_dir': 'up',   'lag_bars': 4,  'stated_accuracy': 0.76, 'type': 'INSTITUTIONAL_FLOW'},
    {'name': 'SPY falls → XME falls (8h)', 'trigger': 'SPY', 'target': 'XME', 'trigger_dir': 'down', 'target_dir': 'down', 'lag_bars': 8,  'stated_accuracy': 0.71, 'type': 'SUPPLY_CHAIN_ECHO'},
    {'name': 'GLD rises → AGG rises (6h)', 'trigger': 'GLD', 'target': 'AGG', 'trigger_dir': 'up',   'target_dir': 'up',   'lag_bars': 6,  'stated_accuracy': 0.70, 'type': 'INSTITUTIONAL_FLOW'},
    {'name': 'SPY falls → GLD rises (8h)', 'trigger': 'SPY', 'target': 'GLD', 'trigger_dir': 'down', 'target_dir': 'up',   'lag_bars': 8,  'stated_accuracy': 0.71, 'type': 'TRANSMISSION_LAG'},
    {'name': 'HYG falls → SPY falls (6h)', 'trigger': 'HYG', 'target': 'SPY', 'trigger_dir': 'down', 'target_dir': 'down', 'lag_bars': 6,  'stated_accuracy': 0.82, 'type': 'TRANSMISSION_LAG'},
    {'name': 'SPY falls → EWJ falls (12h)','trigger': 'SPY', 'target': 'EWJ', 'trigger_dir': 'down', 'target_dir': 'down', 'lag_bars': 12, 'stated_accuracy': 0.81, 'type': 'INSTITUTIONAL_FLOW'},
]

print("=" * 75)
print("KRIMAJLIS BACKTEST v3 — Polygon.io Intraday | Regime-Conditioned")
print(f"Data: 500 days hourly | Threshold: 1.0σ | Min obs: 15")
print(f"Run: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 75)

print("\nFetching VIX hourly for regime classification...")
vix_hourly = fetch_polygon_hourly('I:VIX', days=500)
if vix_hourly is None:
    print("VIX hourly unavailable, falling back to yfinance daily...")
    vix_daily = fetch_yfinance_daily('^VIX', years=2)
    vix_regimes = compute_vix_regime_daily(vix_daily) if vix_daily is not None else {}
else:
    vix_regimes = compute_vix_regime_hourly(vix_hourly)

risk_off  = sum(1 for v in vix_regimes.values() if v == 'RISK_OFF')
risk_on   = sum(1 for v in vix_regimes.values() if v == 'RISK_ON')
total_days = risk_off + risk_on
if total_days > 0:
    print(f"Regime: {risk_off} RISK_OFF / {risk_on} RISK_ON days ({risk_off/total_days*100:.1f}% RISK_OFF)")
else:
    print("Regime data unavailable")

print(f"\n{'Relationship':<40} {'All':>7} {'R_OFF':>8} {'R_ON':>7} {'Obs':>6}  Status")
print("-" * 80)

results = []
for rel in INTRADAY_RELATIONSHIPS:
    lag    = rel['lag_bars']
    result = test_intraday_relationship(rel, vix_regimes, lag)

    if result['status'] == 'NO_DATA':
        print(f"{rel['name']:<40} {'NO DATA':>7}")
        continue
    if result['status'] == 'INSUFFICIENT':
        obs = result.get('total', 0)
        print(f"{rel['name']:<40} {'INSUFF':>7} ({obs} obs)")
        continue

    all_a  = f"{result['all']['acc']*100:.1f}%"
    ro_a   = f"{result['risk_off']['acc']*100:.1f}%" if result['risk_off']['total'] >= 5 else "n/a"
    ron_a  = f"{result['risk_on']['acc']*100:.1f}%"  if result['risk_on']['total']  >= 5 else "n/a"
    obs    = result['all']['total']
    status = "✓ VALID" if result['validated'] else ("✓ R_OFF" if result['validated_risk_off'] else "✗ WEAK")

    print(f"{rel['name']:<40} {all_a:>7} {ro_a:>8} {ron_a:>7} {obs:>6}  {status}")
    results.append(result)

print("\n" + "=" * 75)
print("FINAL RESULTS")
print("=" * 75)

ok = [r for r in results if r['status'] == 'OK']
if ok:
    validated    = [r for r in ok if r['validated']]
    validated_ro = [r for r in ok if r['validated_risk_off']]
    avg_all      = sum(r['all']['acc'] for r in ok) / len(ok)
    ro_ok        = [r for r in ok if r['risk_off']['total'] >= 10]
    avg_ro       = sum(r['risk_off']['acc'] for r in ro_ok) / len(ro_ok) if ro_ok else 0

    print(f"Relationships tested:              {len(ok)}/{len(INTRADAY_RELATIONSHIPS)}")
    print(f"Validated overall (>58%):          {len(validated)}/{len(ok)}")
    print(f"Validated RISK_OFF (>62%):         {len(validated_ro)}/{len(ro_ok)}")
    print(f"Overall accuracy:                  {avg_all*100:.1f}%")
    print(f"RISK_OFF accuracy:                 {avg_ro*100:.1f}%")

    print("\nBy type (RISK_OFF):")
    for t in ['TRANSMISSION_LAG', 'INSTITUTIONAL_FLOW', 'SUPPLY_CHAIN_ECHO']:
        tr = [r for r in ro_ok if r['type'] == t]
        if tr:
            ta = sum(r['risk_off']['acc'] for r in tr) / len(tr)
            tv = sum(1 for r in tr if r['validated_risk_off'])
            print(f"  {t:<25}: {ta*100:.1f}%  ({tv}/{len(tr)} validated)")

    print("\nTop relationships (RISK_OFF):")
    top = sorted(ro_ok, key=lambda x: x['risk_off']['acc'], reverse=True)[:7]
    for r in top:
        print(f"  {r['name']:<42}: {r['risk_off']['acc']*100:.1f}%  ({r['risk_off']['hits']}/{r['risk_off']['total']})")

    print(f"\nKRIMAJLIS RISK_OFF ACCURACY:  {avg_ro*100:.1f}%")
    print(f"KRIMAJLIS OVERALL ACCURACY:   {avg_all*100:.1f}%")

    if avg_ro >= 0.70:
        print("\n✓ ACQUISITION GRADE — RISK_OFF accuracy exceeds 70%")
    elif avg_ro >= 0.62:
        print("\n~ NEAR GRADE — strengthen bottom relationships to reach 70%")
    else:
        print("\n✗ BELOW GRADE — intraday data confirms structural weakness")

print(f"\nComplete: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 75)
