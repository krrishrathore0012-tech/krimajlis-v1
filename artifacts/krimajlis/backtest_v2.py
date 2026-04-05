import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import time
import json

POLYGON_API_KEY = "demo"

RELATIONSHIPS = [
    {
        'id': 'R01',
        'name': 'HYG falls → SPY falls',
        'trigger': 'HYG', 'target': 'SPY',
        'trigger_dir': 'down', 'target_dir': 'down',
        'lag_days': 1, 'data_type': 'daily',
        'stated_accuracy': 0.82, 'type': 'TRANSMISSION_LAG'
    },
    {
        'id': 'R02',
        'name': 'HYG falls → KBE falls',
        'trigger': 'HYG', 'target': 'KBE',
        'trigger_dir': 'down', 'target_dir': 'down',
        'lag_days': 1, 'data_type': 'daily',
        'stated_accuracy': 0.72, 'type': 'TRANSMISSION_LAG'
    },
    {
        'id': 'R03',
        'name': 'SPY falls → EWJ falls',
        'trigger': 'SPY', 'target': 'EWJ',
        'trigger_dir': 'down', 'target_dir': 'down',
        'lag_days': 1, 'data_type': 'daily',
        'stated_accuracy': 0.81, 'type': 'INSTITUTIONAL_FLOW'
    },
    {
        'id': 'R04',
        'name': 'SPY falls → EEM falls',
        'trigger': 'SPY', 'target': 'EEM',
        'trigger_dir': 'down', 'target_dir': 'down',
        'lag_days': 1, 'data_type': 'daily',
        'stated_accuracy': 0.77, 'type': 'INSTITUTIONAL_FLOW'
    },
    {
        'id': 'R05',
        'name': 'HYG falls → TLT rises',
        'trigger': 'HYG', 'target': 'TLT',
        'trigger_dir': 'down', 'target_dir': 'up',
        'lag_days': 1, 'data_type': 'daily',
        'stated_accuracy': 0.74, 'type': 'INSTITUTIONAL_FLOW'
    },
    {
        'id': 'R06',
        'name': 'SPY falls → GLD rises',
        'trigger': 'SPY', 'target': 'GLD',
        'trigger_dir': 'down', 'target_dir': 'up',
        'lag_days': 1, 'data_type': 'daily',
        'stated_accuracy': 0.71, 'type': 'TRANSMISSION_LAG'
    },
    {
        'id': 'R07',
        'name': 'GLD rises → GDX rises',
        'trigger': 'GLD', 'target': 'GDX',
        'trigger_dir': 'up', 'target_dir': 'up',
        'lag_days': 1, 'data_type': 'daily',
        'stated_accuracy': 0.79, 'type': 'TRANSMISSION_LAG'
    },
    {
        'id': 'R08',
        'name': 'SPY falls → VNQ falls',
        'trigger': 'SPY', 'target': 'VNQ',
        'trigger_dir': 'down', 'target_dir': 'down',
        'lag_days': 1, 'data_type': 'daily',
        'stated_accuracy': 0.73, 'type': 'TRANSMISSION_LAG'
    },
    {
        'id': 'R09',
        'name': 'HYG falls → AGG rises',
        'trigger': 'HYG', 'target': 'AGG',
        'trigger_dir': 'down', 'target_dir': 'up',
        'lag_days': 1, 'data_type': 'daily',
        'stated_accuracy': 0.76, 'type': 'INSTITUTIONAL_FLOW'
    },
    {
        'id': 'R10',
        'name': 'SPY falls → JETS falls',
        'trigger': 'SPY', 'target': 'JETS',
        'trigger_dir': 'down', 'target_dir': 'down',
        'lag_days': 1, 'data_type': 'daily',
        'stated_accuracy': 0.74, 'type': 'SUPPLY_CHAIN_ECHO'
    },
    {
        'id': 'R11',
        'name': 'SPY falls → XME falls',
        'trigger': 'SPY', 'target': 'XME',
        'trigger_dir': 'down', 'target_dir': 'down',
        'lag_days': 1, 'data_type': 'daily',
        'stated_accuracy': 0.71, 'type': 'SUPPLY_CHAIN_ECHO'
    },
    {
        'id': 'R12',
        'name': 'GLD rises → SLV rises',
        'trigger': 'GLD', 'target': 'SLV',
        'trigger_dir': 'up', 'target_dir': 'up',
        'lag_days': 1, 'data_type': 'daily',
        'stated_accuracy': 0.78, 'type': 'TRANSMISSION_LAG'
    },
    {
        'id': 'R13',
        'name': 'HYG falls → SPY falls T+2',
        'trigger': 'HYG', 'target': 'SPY',
        'trigger_dir': 'down', 'target_dir': 'down',
        'lag_days': 2, 'data_type': 'daily',
        'stated_accuracy': 0.76, 'type': 'TRANSMISSION_LAG'
    },
    {
        'id': 'R14',
        'name': 'SPY falls → EWJ falls T+2',
        'trigger': 'SPY', 'target': 'EWJ',
        'trigger_dir': 'down', 'target_dir': 'down',
        'lag_days': 2, 'data_type': 'daily',
        'stated_accuracy': 0.74, 'type': 'INSTITUTIONAL_FLOW'
    },
    {
        'id': 'R15',
        'name': 'HYG falls → EEM falls',
        'trigger': 'HYG', 'target': 'EEM',
        'trigger_dir': 'down', 'target_dir': 'down',
        'lag_days': 1, 'data_type': 'daily',
        'stated_accuracy': 0.72, 'type': 'INSTITUTIONAL_FLOW'
    },
    {
        'id': 'R16',
        'name': 'SPY falls → KBE falls',
        'trigger': 'SPY', 'target': 'KBE',
        'trigger_dir': 'down', 'target_dir': 'down',
        'lag_days': 1, 'data_type': 'daily',
        'stated_accuracy': 0.75, 'type': 'TRANSMISSION_LAG'
    },
    {
        'id': 'R17',
        'name': 'GLD rises → AGG rises',
        'trigger': 'GLD', 'target': 'AGG',
        'trigger_dir': 'up', 'target_dir': 'up',
        'lag_days': 1, 'data_type': 'daily',
        'stated_accuracy': 0.70, 'type': 'INSTITUTIONAL_FLOW'
    },
    {
        'id': 'R18',
        'name': 'SPY falls → XLK falls',
        'trigger': 'SPY', 'target': 'XLK',
        'trigger_dir': 'down', 'target_dir': 'down',
        'lag_days': 1, 'data_type': 'daily',
        'stated_accuracy': 0.83, 'type': 'TRANSMISSION_LAG'
    },
    {
        'id': 'R19',
        'name': 'HYG falls → XME falls',
        'trigger': 'HYG', 'target': 'XME',
        'trigger_dir': 'down', 'target_dir': 'down',
        'lag_days': 2, 'data_type': 'daily',
        'stated_accuracy': 0.71, 'type': 'SUPPLY_CHAIN_ECHO'
    },
    {
        'id': 'R20',
        'name': 'SPY falls → VNQ falls T+2',
        'trigger': 'SPY', 'target': 'VNQ',
        'trigger_dir': 'down', 'target_dir': 'down',
        'lag_days': 2, 'data_type': 'daily',
        'stated_accuracy': 0.72, 'type': 'TRANSMISSION_LAG'
    },
]


def fetch_yfinance_daily(ticker, years=4):
    try:
        t = yf.Ticker(ticker)
        end = datetime.now()
        start = end - timedelta(days=years * 365)
        hist = t.history(
            start=start.strftime('%Y-%m-%d'),
            end=end.strftime('%Y-%m-%d'),
            interval='1d',
            auto_adjust=True
        )
        if hist.empty or len(hist) < 100:
            return None
        return hist['Close']
    except Exception:
        return None


def compute_vix_regime(vix_series):
    regimes = {}
    for date, vix in vix_series.items():
        d = date.date() if hasattr(date, 'date') else date
        regimes[d] = 'RISK_OFF' if vix > 20 else 'RISK_ON'
    return regimes


def test_relationship_regime_conditioned(rel, vix_regimes):
    trigger_data = fetch_yfinance_daily(rel['trigger'], years=4)
    target_data = fetch_yfinance_daily(rel['target'], years=4)

    if trigger_data is None or target_data is None:
        return None

    trigger_returns = trigger_data.pct_change().dropna()
    target_returns = target_data.pct_change().dropna()

    common_dates = trigger_returns.index.intersection(target_returns.index)
    trigger_returns = trigger_returns[common_dates]
    target_returns = target_returns[common_dates]

    if len(trigger_returns) < 50:
        return None

    threshold = trigger_returns.std() * 1.0
    lag = rel['lag_days']

    results_all      = {'hits': 0, 'total': 0}
    results_risk_off = {'hits': 0, 'total': 0}
    results_risk_on  = {'hits': 0, 'total': 0}

    dates_list = list(trigger_returns.index)

    for i in range(len(dates_list) - lag - 1):
        trigger_move = trigger_returns.iloc[i]

        if abs(trigger_move) < threshold:
            continue

        trigger_fired = (
            (rel['trigger_dir'] == 'down' and trigger_move < -threshold) or
            (rel['trigger_dir'] == 'up'   and trigger_move > threshold)
        )

        if not trigger_fired:
            continue

        if i + lag >= len(target_returns):
            continue

        target_move = target_returns.iloc[i + lag]

        target_correct = (
            (rel['target_dir'] == 'up'   and target_move > 0) or
            (rel['target_dir'] == 'down' and target_move < 0)
        )

        d = dates_list[i].date() if hasattr(dates_list[i], 'date') else dates_list[i]
        regime = vix_regimes.get(d, 'UNKNOWN')

        results_all['total'] += 1
        if target_correct:
            results_all['hits'] += 1

        if regime == 'RISK_OFF':
            results_risk_off['total'] += 1
            if target_correct:
                results_risk_off['hits'] += 1
        elif regime == 'RISK_ON':
            results_risk_on['total'] += 1
            if target_correct:
                results_risk_on['hits'] += 1

    if results_all['total'] < 15:
        return {'status': 'INSUFFICIENT_SAMPLE', 'total': results_all['total']}

    def acc(r):
        return round(r['hits'] / r['total'], 3) if r['total'] > 0 else 0

    return {
        'name': rel['name'],
        'type': rel['type'],
        'stated_accuracy': rel['stated_accuracy'],
        'all':      {'accuracy': acc(results_all),      'hits': results_all['hits'],      'total': results_all['total']},
        'risk_off': {'accuracy': acc(results_risk_off), 'hits': results_risk_off['hits'], 'total': results_risk_off['total']},
        'risk_on':  {'accuracy': acc(results_risk_on),  'hits': results_risk_on['hits'],  'total': results_risk_on['total']},
        'validated_all':      acc(results_all)      >= 0.55,
        'validated_risk_off': acc(results_risk_off) >= 0.60,
        'status': 'OK'
    }


print("=" * 75)
print("KRIMAJLIS CAUSAL RELATIONSHIP BACKTEST v2")
print("4-year daily data | 1.0σ threshold | Regime-conditioned | Min 15 obs")
print(f"Run date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
print("=" * 75)

print("\nFetching VIX regime data (4 years)...")
vix_data = fetch_yfinance_daily('^VIX', years=4)
if vix_data is None:
    print("ERROR: Could not fetch VIX data. Exiting.")
    exit(1)

vix_regimes = compute_vix_regime(vix_data)
risk_off_days = sum(1 for v in vix_regimes.values() if v == 'RISK_OFF')
risk_on_days  = sum(1 for v in vix_regimes.values() if v == 'RISK_ON')
print(f"VIX regime classification: {risk_off_days} RISK_OFF days, {risk_on_days} RISK_ON days")
print(f"RISK_OFF proportion: {risk_off_days/(risk_off_days+risk_on_days)*100:.1f}%")

print("\nTesting relationships...\n")
print(f"{'Relationship':<35} {'All':>8} {'RISK_OFF':>10} {'RISK_ON':>9} {'Obs':>6}   Status")
print("-" * 80)

results = []
for rel in RELATIONSHIPS:
    result = test_relationship_regime_conditioned(rel, vix_regimes)
    time.sleep(0.3)

    if result is None:
        print(f"{rel['name']:<35} {'NO DATA':>8}")
        continue

    if result.get('status') == 'INSUFFICIENT_SAMPLE':
        print(f"{rel['name']:<35} {'INSUFF':>8} (only {result['total']} obs)")
        continue

    all_acc = f"{result['all']['accuracy']*100:.1f}%"
    ro_acc  = f"{result['risk_off']['accuracy']*100:.1f}%" if result['risk_off']['total'] >= 5 else "n/a"
    ron_acc = f"{result['risk_on']['accuracy']*100:.1f}%"  if result['risk_on']['total']  >= 5 else "n/a"
    obs     = result['all']['total']
    status  = (
        "✓ VALID"     if result['validated_all'] else
        "✓ RISK_OFF"  if result['validated_risk_off'] and result['risk_off']['total'] >= 5 else
        "✗ WEAK"
    )

    print(f"{rel['name']:<35} {all_acc:>8} {ro_acc:>10} {ron_acc:>9} {obs:>6}   {status}")
    results.append(result)

print("\n" + "=" * 75)
print("BACKTEST SUMMARY v2")
print("=" * 75)

valid_results = [r for r in results if r.get('status') == 'OK']

if valid_results:
    validated_all      = [r for r in valid_results if r['validated_all']]
    risk_off_results   = [r for r in valid_results if r['risk_off']['total'] >= 5]
    risk_on_results    = [r for r in valid_results if r['risk_on']['total']  >= 5]
    validated_risk_off = [r for r in risk_off_results if r['validated_risk_off']]

    overall_all      = sum(r['all']['accuracy']      for r in valid_results)      / len(valid_results)
    overall_risk_off = sum(r['risk_off']['accuracy'] for r in risk_off_results)   / len(risk_off_results) if risk_off_results else 0
    overall_risk_on  = sum(r['risk_on']['accuracy']  for r in risk_on_results)    / len(risk_on_results)  if risk_on_results  else 0

    print(f"\nRelationships with sufficient data:     {len(valid_results)}/{len(RELATIONSHIPS)}")
    print(f"Validated overall (>55%):               {len(validated_all)}/{len(valid_results)}")
    print(f"Validated in RISK_OFF regime (>60%):    {len(validated_risk_off)}/{len(risk_off_results)}")
    print(f"\nOverall accuracy (all regimes):         {overall_all*100:.1f}%")
    print(f"RISK_OFF regime accuracy:               {overall_risk_off*100:.1f}%")
    print(f"RISK_ON regime accuracy:                {overall_risk_on*100:.1f}%")

    print("\nBy loophole type (RISK_OFF accuracy):")
    for ltype in ['TRANSMISSION_LAG', 'INSTITUTIONAL_FLOW', 'SUPPLY_CHAIN_ECHO', 'NARRATIVE_VELOCITY']:
        type_results = [r for r in risk_off_results if r['type'] == ltype]
        if type_results:
            type_acc = sum(r['risk_off']['accuracy'] for r in type_results) / len(type_results)
            validated_count = sum(1 for r in type_results if r['validated_risk_off'])
            print(f"  {ltype:<25}: {type_acc*100:.1f}%  ({validated_count}/{len(type_results)} validated)")

    print("\nTop 5 relationships in RISK_OFF regime:")
    sorted_ro = sorted(risk_off_results, key=lambda x: x['risk_off']['accuracy'], reverse=True)
    for r in sorted_ro[:5]:
        print(f"  {r['name']:<35}: {r['risk_off']['accuracy']*100:.1f}%  ({r['risk_off']['hits']}/{r['risk_off']['total']} obs)")

    print("\nRelationships to strengthen or remove:")
    weak = [r for r in valid_results if not r['validated_all'] and not r['validated_risk_off']]
    for r in weak:
        ro_str = f"{r['risk_off']['accuracy']*100:.1f}%" if r['risk_off']['total'] >= 5 else "n/a"
        print(f"  {r['name']:<35}: {r['all']['accuracy']*100:.1f}% overall, {ro_str} RISK_OFF")

    print(f"\nKRIMAJLIS RISK_OFF ACCURACY:   {overall_risk_off*100:.1f}%")
    print(f"KRIMAJLIS ALL-REGIME ACCURACY: {overall_all*100:.1f}%")

    if overall_risk_off >= 0.70:
        print("\n✓ ACQUISITION GRADE: RISK_OFF accuracy exceeds 70% threshold")
    elif overall_risk_off >= 0.60:
        print("\n~ NEAR GRADE: RISK_OFF accuracy exceeds 60% — strengthen weak relationships")
    else:
        print("\n✗ BELOW GRADE: Review and replace weak relationships")

print(f"\nBacktest complete: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
print("=" * 75)
