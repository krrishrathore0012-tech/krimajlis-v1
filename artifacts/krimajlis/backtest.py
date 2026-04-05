import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

RELATIONSHIPS = [
    {'trigger': 'DX-Y.NYB', 'target': 'GLD', 'trigger_dir': 'down', 'target_dir': 'up', 'lag_hours': 4, 'accuracy': 0.78, 'name': 'DXY falls → Gold rises', 'type': 'TRANSMISSION_LAG'},
    {'trigger': 'DX-Y.NYB', 'target': 'EEM', 'trigger_dir': 'down', 'target_dir': 'up', 'lag_hours': 6, 'accuracy': 0.71, 'name': 'DXY falls → EM rises', 'type': 'TRANSMISSION_LAG'},
    {'trigger': 'CL=F', 'target': 'JETS', 'trigger_dir': 'down', 'target_dir': 'up', 'lag_hours': 24, 'accuracy': 0.71, 'name': 'WTI falls → Airlines rise', 'type': 'SUPPLY_CHAIN_ECHO'},
    {'trigger': 'CL=F', 'target': 'USDINR=X', 'trigger_dir': 'up', 'target_dir': 'up', 'lag_hours': 8, 'accuracy': 0.74, 'name': 'WTI rises → INR weakens', 'type': 'TRANSMISSION_LAG'},
    {'trigger': '^VIX', 'target': 'EEM', 'trigger_dir': 'up', 'target_dir': 'down', 'lag_hours': 6, 'accuracy': 0.69, 'name': 'VIX spikes → EM falls', 'type': 'INSTITUTIONAL_FLOW'},
    {'trigger': '^VIX', 'target': 'GLD', 'trigger_dir': 'up', 'target_dir': 'up', 'lag_hours': 3, 'accuracy': 0.76, 'name': 'VIX spikes → Gold rises', 'type': 'TRANSMISSION_LAG'},
    {'trigger': 'HYG', 'target': 'SPY', 'trigger_dir': 'down', 'target_dir': 'down', 'lag_hours': 2, 'accuracy': 0.82, 'name': 'HYG falls → SPY falls', 'type': 'TRANSMISSION_LAG'},
    {'trigger': '^GSPC', 'target': '^NSEI', 'trigger_dir': 'down', 'target_dir': 'down', 'lag_hours': 12, 'accuracy': 0.77, 'name': 'SPX falls → Nifty falls', 'type': 'NARRATIVE_VELOCITY'},
    {'trigger': '^GSPC', 'target': 'EWJ', 'trigger_dir': 'down', 'target_dir': 'down', 'lag_hours': 8, 'accuracy': 0.81, 'name': 'SPX falls → Japan falls', 'type': 'INSTITUTIONAL_FLOW'},
    {'trigger': 'DX-Y.NYB', 'target': 'GDX', 'trigger_dir': 'down', 'target_dir': 'up', 'lag_hours': 24, 'accuracy': 0.79, 'name': 'DXY falls → Gold miners rise', 'type': 'TRANSMISSION_LAG'},
    {'trigger': '^VIX', 'target': 'TLT', 'trigger_dir': 'up', 'target_dir': 'up', 'lag_hours': 4, 'accuracy': 0.74, 'name': 'VIX spikes → TLT rises', 'type': 'INSTITUTIONAL_FLOW'},
    {'trigger': 'CL=F', 'target': 'SHW', 'trigger_dir': 'down', 'target_dir': 'up', 'lag_hours': 360, 'accuracy': 0.67, 'name': 'WTI falls → Paint rises', 'type': 'SUPPLY_CHAIN_ECHO'},
    {'trigger': 'HYG', 'target': 'KBE', 'trigger_dir': 'down', 'target_dir': 'down', 'lag_hours': 4, 'accuracy': 0.72, 'name': 'HYG falls → Banks fall', 'type': 'TRANSMISSION_LAG'},
    {'trigger': '^GSPC', 'target': 'CEW', 'trigger_dir': 'down', 'target_dir': 'down', 'lag_hours': 6, 'accuracy': 0.69, 'name': 'SPX falls → EM FX falls', 'type': 'INSTITUTIONAL_FLOW'},
    {'trigger': 'DX-Y.NYB', 'target': 'AGG', 'trigger_dir': 'down', 'target_dir': 'up', 'lag_hours': 6, 'accuracy': 0.73, 'name': 'DXY falls → Bonds rise', 'type': 'TRANSMISSION_LAG'},
]

def fetch_data(ticker, days=60):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=f'{days}d', interval='1d')
        if hist.empty:
            return None
        return hist['Close']
    except Exception as e:
        print(f"Failed to fetch {ticker}: {e}")
        return None

def test_relationship(rel, lookback_days=45):
    trigger_data = fetch_data(rel['trigger'], lookback_days + 10)
    target_data = fetch_data(rel['target'], lookback_days + 10)
    
    if trigger_data is None or target_data is None:
        return None
    
    trigger_returns = trigger_data.pct_change().dropna()
    target_returns = target_data.pct_change().dropna()
    
    common_dates = trigger_returns.index.intersection(target_returns.index)
    trigger_returns = trigger_returns[common_dates]
    target_returns = target_returns[common_dates]
    
    if len(trigger_returns) < 20:
        return None
    
    hits = 0
    total = 0
    
    lag_days = max(1, rel['lag_hours'] // 24)
    
    for i in range(len(trigger_returns) - lag_days - 1):
        trigger_move = trigger_returns.iloc[i]
        
        threshold = trigger_returns.std() * 0.5
        if abs(trigger_move) < threshold:
            continue
        
        if i + lag_days >= len(target_returns):
            continue
            
        target_move = target_returns.iloc[i + lag_days]
        
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
    
    if total < 5:
        return None
    
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
        'validated': empirical_accuracy >= 0.55
    }

print("=" * 70)
print("KRIMAJLIS CAUSAL RELATIONSHIP BACKTEST")
print(f"Period: Last 45 trading days ending {datetime.now().strftime('%Y-%m-%d')}")
print("=" * 70)

results = []
for rel in RELATIONSHIPS:
    print(f"Testing: {rel['name']}...", end=' ')
    result = test_relationship(rel)
    if result:
        status = "✓ VALIDATED" if result['validated'] else "✗ WEAK"
        print(f"{result['empirical_accuracy']*100:.1f}% ({result['hits']}/{result['total']}) {status}")
        results.append(result)
    else:
        print("INSUFFICIENT DATA")

print("\n" + "=" * 70)
print("BACKTEST SUMMARY")
print("=" * 70)

if results:
    validated = [r for r in results if r['validated']]
    overall = sum(r['empirical_accuracy'] for r in results) / len(results)
    
    print(f"Relationships tested: {len(results)}")
    print(f"Validated (>55% accuracy): {len(validated)}/{len(results)}")
    print(f"Overall empirical accuracy: {overall*100:.1f}%")
    print(f"Stated average accuracy: {sum(r['stated_accuracy'] for r in results)/len(results)*100:.1f}%")
    
    print("\nBy loophole type:")
    for ltype in ['TRANSMISSION_LAG', 'INSTITUTIONAL_FLOW', 'SUPPLY_CHAIN_ECHO', 'NARRATIVE_VELOCITY']:
        type_results = [r for r in results if r['type'] == ltype]
        if type_results:
            type_acc = sum(r['empirical_accuracy'] for r in type_results) / len(type_results)
            print(f"  {ltype}: {type_acc*100:.1f}% ({len(type_results)} relationships)")
    
    print("\nTop performing relationships:")
    sorted_results = sorted(results, key=lambda x: x['empirical_accuracy'], reverse=True)
    for r in sorted_results[:5]:
        print(f"  {r['name']}: {r['empirical_accuracy']*100:.1f}%")
    
    print("\nWeakest relationships:")
    for r in sorted_results[-3:]:
        print(f"  {r['name']}: {r['empirical_accuracy']*100:.1f}%")

print("\n" + "=" * 70)
print(f"Backtest complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
print("=" * 70)
