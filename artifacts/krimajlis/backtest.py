import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

RELATIONSHIPS = [
    {'trigger': 'DX-Y.NYB', 'target': 'GLD',     'trigger_dir': 'down', 'target_dir': 'up',   'lag_hours': 4,   'accuracy': 0.78, 'name': 'DXY falls → Gold rises',         'type': 'TRANSMISSION_LAG'},
    {'trigger': 'DX-Y.NYB', 'target': 'EEM',     'trigger_dir': 'down', 'target_dir': 'up',   'lag_hours': 6,   'accuracy': 0.71, 'name': 'DXY falls → EM rises',           'type': 'TRANSMISSION_LAG'},
    {'trigger': 'CL=F',     'target': 'JETS',    'trigger_dir': 'down', 'target_dir': 'up',   'lag_hours': 24,  'accuracy': 0.71, 'name': 'WTI falls → Airlines rise',       'type': 'SUPPLY_CHAIN_ECHO'},
    {'trigger': 'CL=F',     'target': 'USDINR=X','trigger_dir': 'up',   'target_dir': 'up',   'lag_hours': 8,   'accuracy': 0.74, 'name': 'WTI rises → INR weakens',         'type': 'TRANSMISSION_LAG'},
    {'trigger': '^VIX',     'target': 'EEM',     'trigger_dir': 'up',   'target_dir': 'down', 'lag_hours': 6,   'accuracy': 0.69, 'name': 'VIX spikes → EM falls',           'type': 'INSTITUTIONAL_FLOW'},
    {'trigger': '^VIX',     'target': 'GLD',     'trigger_dir': 'up',   'target_dir': 'up',   'lag_hours': 3,   'accuracy': 0.76, 'name': 'VIX spikes → Gold rises',         'type': 'TRANSMISSION_LAG'},
    {'trigger': 'HYG',      'target': 'SPY',     'trigger_dir': 'down', 'target_dir': 'down', 'lag_hours': 2,   'accuracy': 0.82, 'name': 'HYG falls → SPY falls',           'type': 'TRANSMISSION_LAG'},
    {'trigger': '^GSPC',    'target': '^NSEI',   'trigger_dir': 'down', 'target_dir': 'down', 'lag_hours': 12,  'accuracy': 0.77, 'name': 'SPX falls → Nifty falls',         'type': 'NARRATIVE_VELOCITY'},
    {'trigger': '^GSPC',    'target': 'EWJ',     'trigger_dir': 'down', 'target_dir': 'down', 'lag_hours': 8,   'accuracy': 0.81, 'name': 'SPX falls → Japan falls',         'type': 'INSTITUTIONAL_FLOW'},
    {'trigger': 'DX-Y.NYB', 'target': 'GDX',    'trigger_dir': 'down', 'target_dir': 'up',   'lag_hours': 24,  'accuracy': 0.79, 'name': 'DXY falls → Gold miners rise',    'type': 'TRANSMISSION_LAG'},
    {'trigger': '^VIX',     'target': 'TLT',     'trigger_dir': 'up',   'target_dir': 'up',   'lag_hours': 4,   'accuracy': 0.74, 'name': 'VIX spikes → TLT rises',          'type': 'INSTITUTIONAL_FLOW'},
    {'trigger': 'CL=F',     'target': 'SHW',     'trigger_dir': 'down', 'target_dir': 'up',   'lag_hours': 360, 'accuracy': 0.67, 'name': 'WTI falls → Paint rises',         'type': 'SUPPLY_CHAIN_ECHO'},
    {'trigger': 'HYG',      'target': 'KBE',     'trigger_dir': 'down', 'target_dir': 'down', 'lag_hours': 4,   'accuracy': 0.72, 'name': 'HYG falls → Banks fall',          'type': 'TRANSMISSION_LAG'},
    {'trigger': '^GSPC',    'target': 'CEW',     'trigger_dir': 'down', 'target_dir': 'down', 'lag_hours': 6,   'accuracy': 0.69, 'name': 'SPX falls → EM FX falls',         'type': 'INSTITUTIONAL_FLOW'},
    {'trigger': 'DX-Y.NYB', 'target': 'AGG',    'trigger_dir': 'down', 'target_dir': 'up',   'lag_hours': 6,   'accuracy': 0.73, 'name': 'DXY falls → Bonds rise',          'type': 'TRANSMISSION_LAG'},
    {'trigger': '^VIX',     'target': 'CEW',     'trigger_dir': 'up',   'target_dir': 'down', 'lag_hours': 6,   'accuracy': 0.69, 'name': 'VIX spikes → EM FX falls',        'type': 'INSTITUTIONAL_FLOW'},
]

MIN_OBSERVATIONS = 15


def fetch_data(ticker, lag_hours):
    try:
        t = yf.Ticker(ticker)
        if lag_hours < 24:
            hist = t.history(period='60d', interval='1h')
        else:
            hist = t.history(period='90d', interval='1d')
        if hist.empty:
            return None, lag_hours < 24
        return hist['Close'], lag_hours < 24
    except Exception as e:
        print(f"Failed to fetch {ticker}: {e}")
        return None, lag_hours < 24


def test_relationship(rel):
    trigger_data, is_hourly = fetch_data(rel['trigger'], rel['lag_hours'])
    target_data, _ = fetch_data(rel['target'], rel['lag_hours'])

    if trigger_data is None or target_data is None:
        return None

    trigger_returns = trigger_data.pct_change().dropna()
    target_returns = target_data.pct_change().dropna()

    # Align on common timestamps
    common_idx = trigger_returns.index.intersection(target_returns.index)
    trigger_returns = trigger_returns[common_idx]
    target_returns = target_returns[common_idx]

    if len(trigger_returns) < 20:
        return None

    hits = 0
    total = 0

    if is_hourly:
        lag_periods = max(1, rel['lag_hours'])
    else:
        lag_periods = max(1, rel['lag_hours'] // 24)

    threshold = trigger_returns.std() * 1.0  # Fix 1: 1.0 std dev

    for i in range(len(trigger_returns) - lag_periods - 1):
        trigger_move = trigger_returns.iloc[i]

        if abs(trigger_move) < threshold:
            continue

        if i + lag_periods >= len(target_returns):
            continue

        target_move = target_returns.iloc[i + lag_periods]

        trigger_fired_correct = (
            (rel['trigger_dir'] == 'down' and trigger_move < 0) or
            (rel['trigger_dir'] == 'up' and trigger_move > 0)
        )

        if not trigger_fired_correct:
            continue

        target_responded_correct = (
            (rel['target_dir'] == 'up' and target_move > 0) or
            (rel['target_dir'] == 'down' and target_move < 0)
        )

        hits += int(target_responded_correct)
        total += 1

    if total < MIN_OBSERVATIONS:  # Fix 4: min 15 observations
        return {'insufficient': True, 'total': total}

    empirical_accuracy = hits / total
    return {
        'name': rel['name'],
        'type': rel['type'],
        'trigger': rel['trigger'],
        'target': rel['target'],
        'stated_accuracy': rel['accuracy'],
        'empirical_accuracy': round(empirical_accuracy, 3),
        'hits': hits,
        'total': total,
        'validated': empirical_accuracy >= 0.55,
        'hourly': is_hourly,
    }


print("=" * 70)
print("KRIMAJLIS CAUSAL RELATIONSHIP BACKTEST")
print(f"Period: 90d daily / 60d hourly  |  Threshold: 1.0σ  |  Min obs: {MIN_OBSERVATIONS}")
print(f"Run date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
print("=" * 70)

results = []
insufficient = 0

for rel in RELATIONSHIPS:
    label = f"[{'1h' if rel['lag_hours'] < 24 else '1d'}]"
    print(f"Testing {label}: {rel['name']}...", end=' ', flush=True)
    result = test_relationship(rel)
    if result is None:
        print("NO DATA")
    elif result.get('insufficient'):
        print(f"INSUFFICIENT SAMPLE ({result['total']} obs < {MIN_OBSERVATIONS})")
        insufficient += 1
    else:
        status = "✓ VALIDATED" if result['validated'] else "✗ WEAK"
        print(f"{result['empirical_accuracy']*100:.1f}% ({result['hits']}/{result['total']}) {status}")
        results.append(result)

print("\n" + "=" * 70)
print("BACKTEST SUMMARY")
print("=" * 70)

if results:
    validated = [r for r in results if r['validated']]
    overall = sum(r['empirical_accuracy'] for r in results) / len(results)

    print(f"Relationships tested:          {len(RELATIONSHIPS)}")
    print(f"Returned results:              {len(results)}")
    print(f"Insufficient sample (<{MIN_OBSERVATIONS} obs): {insufficient}")
    print(f"Validated (>55% accuracy):     {len(validated)}/{len(results)}")
    print(f"Overall empirical accuracy:    {overall*100:.1f}%")
    print(f"Stated average accuracy:       {sum(r['stated_accuracy'] for r in results)/len(results)*100:.1f}%")

    print("\nBy loophole type:")
    for ltype in ['TRANSMISSION_LAG', 'INSTITUTIONAL_FLOW', 'SUPPLY_CHAIN_ECHO', 'NARRATIVE_VELOCITY', 'VOLATILITY_SURFACE']:
        type_results = [r for r in results if r['type'] == ltype]
        if type_results:
            type_acc = sum(r['empirical_accuracy'] for r in type_results) / len(type_results)
            type_val = sum(1 for r in type_results if r['validated'])
            print(f"  {ltype}: {type_acc*100:.1f}%  ({type_val}/{len(type_results)} validated)")

    print("\nTop performing relationships:")
    sorted_results = sorted(results, key=lambda x: x['empirical_accuracy'], reverse=True)
    for r in sorted_results[:5]:
        tag = '[1h]' if r['hourly'] else '[1d]'
        print(f"  {tag} {r['name']}: {r['empirical_accuracy']*100:.1f}%  ({r['hits']}/{r['total']} obs)")

    print("\nWeakest relationships:")
    for r in sorted_results[-3:]:
        tag = '[1h]' if r['hourly'] else '[1d]'
        print(f"  {tag} {r['name']}: {r['empirical_accuracy']*100:.1f}%  ({r['hits']}/{r['total']} obs)")
else:
    print("No relationships returned sufficient data.")

print("\n" + "=" * 70)
print(f"Backtest complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
print("=" * 70)
