import yfinance as yf
from datetime import datetime, timedelta
from db import safe_db_read, safe_db_update, safe_db_write
import json

TICKER_MAP = {
    'SPY': 'SPY', 'HYG': 'HYG', 'TLT': 'TLT', 'GLD': 'GLD',
    'EWJ': 'EWJ', 'XME': 'XME', 'KBE': 'KBE', 'EEM': 'EEM',
    'VXX': 'VXX', 'SVXY': 'SVXY', 'XLK': 'XLK', 'AGG': 'AGG',
    'VNQ': 'VNQ', 'DJP': 'DJP', 'JETS': 'JETS', 'SHW': 'SHW',
    'BOAT': 'BOAT', 'TIO': 'TIO', 'EWA': 'EWA', 'CEW': 'CEW',
    'GDX': 'GDX', 'AUDUSD=X': 'AUDUSD=X', 'USDINR=X': 'USDINR=X',
    '^NSEI': '^NSEI', '^GSPC': '^GSPC', 'DX-Y.NYB': 'DX-Y.NYB'
}


def fetch_current_price(ticker: str) -> float:
    import requests as req

    yf_ticker = TICKER_MAP.get(ticker, ticker)

    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_ticker}"
        params = {
            'interval': '1m',
            'range': '1d',
            'includePrePost': 'true'
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        r = req.get(url, params=params, headers=headers, timeout=10)
        data = r.json()
        result = data.get('chart', {}).get('result', [])
        if result:
            meta = result[0].get('meta', {})
            price = meta.get('regularMarketPrice') or meta.get('previousClose')
            if price and price > 0:
                return float(price)
    except Exception as e:
        print(f"Yahoo direct fetch failed for {ticker}: {e}")

    try:
        t = yf.Ticker(yf_ticker)
        hist = t.history(period='1d', interval='5m')
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except Exception:
        pass

    return None


def validate_pending_signals():
    print(f"[Validator] Running at {datetime.utcnow().isoformat()}")
    try:
        pending = safe_db_read('signals', {'validation_status': 'PENDING'})
        now = datetime.utcnow()
        validated = 0
        for signal in pending:
            try:
                expires_str = signal.get('entry_window_expires_at')
                if not expires_str:
                    continue
                expires = datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
                expires_naive = expires.replace(tzinfo=None)
                if now < expires_naive:
                    continue
                current_price = fetch_current_price(signal['ticker'])
                if current_price is None:
                    continue
                causal_chain = signal.get('causal_chain', [])
                if isinstance(causal_chain, str):
                    causal_chain = json.loads(causal_chain)
                direction = signal.get('direction', 'LONG')
                entry_snapshot = signal.get('primary_node_snapshot', {})
                if isinstance(entry_snapshot, str):
                    entry_snapshot = json.loads(entry_snapshot)
                entry_price = None
                if isinstance(entry_snapshot, list):
                    for node in entry_snapshot:
                        if isinstance(node, dict) and node.get('ticker') == signal['ticker']:
                            entry_price = node.get('current_value')
                            break
                if entry_price is None or entry_price == 0:
                    entry_price = current_price
                move_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price else 0
                if abs(move_pct) < 0.05:
                    print(f"[Validator] Skipping {signal['ticker']} — price unchanged, market likely closed or stale data")
                    continue
                if direction == 'LONG':
                    outcome = 'HIT' if move_pct > 0.1 else 'MISS'
                    realized_direction = 'UP' if move_pct > 0 else 'DOWN'
                elif direction == 'SHORT':
                    outcome = 'HIT' if move_pct < -0.1 else 'MISS'
                    realized_direction = 'DOWN' if move_pct < 0 else 'UP'
                else:
                    outcome = 'HIT' if abs(move_pct) > 0.2 else 'MISS'
                    realized_direction = 'UP' if move_pct > 0 else 'DOWN'
                safe_db_update(
                    'signals',
                    {'signal_id': signal['signal_id']},
                    {
                        'validation_status': 'VALIDATED',
                        'realized_direction': realized_direction,
                        'realized_move_pct': round(move_pct, 4),
                        'outcome': outcome,
                        'validated_at': datetime.utcnow().isoformat()
                    }
                )
                validated += 1
            except Exception as e:
                print(f"[Validator] Error validating signal {signal.get('signal_id')}: {e}")
                continue
        print(f"[Validator] Validated {validated} signals")
        if validated > 0:
            compute_accuracy_summary()
    except Exception as e:
        print(f"[Validator] Fatal error: {e}")


def compute_accuracy_summary():
    try:
        validated = safe_db_read('signals', {'validation_status': 'VALIDATED'}, limit=5000)
        if not validated:
            return
        total = len(validated)
        hits = sum(1 for s in validated if s.get('outcome') == 'HIT')
        misses = total - hits
        overall_accuracy = round(hits / total * 100, 2) if total > 0 else 0
        by_layer = {}
        by_loophole = {}
        by_geo = {}
        for s in validated:
            layer = s.get('alpha_layer', 'unknown')
            loophole = s.get('loophole_type', 'unknown')
            geo = s.get('geography', 'unknown')
            is_hit = s.get('outcome') == 'HIT'
            for d, key in [(by_layer, layer), (by_loophole, loophole), (by_geo, geo)]:
                if key not in d:
                    d[key] = {'hits': 0, 'total': 0}
                d[key]['total'] += 1
                if is_hit:
                    d[key]['hits'] += 1
        for d in [by_layer, by_loophole, by_geo]:
            for key in d:
                d[key]['accuracy'] = round(d[key]['hits'] / d[key]['total'] * 100, 2)
        now = datetime.utcnow()
        cutoff_7d = now - timedelta(days=7)
        cutoff_30d = now - timedelta(days=30)
        recent_7d = [s for s in validated if datetime.fromisoformat(
            s['created_at'].replace('Z', '+00:00')).replace(tzinfo=None) > cutoff_7d]
        recent_30d = [s for s in validated if datetime.fromisoformat(
            s['created_at'].replace('Z', '+00:00')).replace(tzinfo=None) > cutoff_30d]
        r7_hits = sum(1 for s in recent_7d if s.get('outcome') == 'HIT')
        r30_hits = sum(1 for s in recent_30d if s.get('outcome') == 'HIT')
        rolling_7d = round(r7_hits / len(recent_7d) * 100, 2) if recent_7d else 0
        rolling_30d = round(r30_hits / len(recent_30d) * 100, 2) if recent_30d else 0
        safe_db_write('accuracy_summary', {
            'computed_at': now.isoformat(),
            'total_signals': total,
            'validated_signals': total,
            'hit_count': hits,
            'miss_count': misses,
            'overall_accuracy': overall_accuracy,
            'by_layer': by_layer,
            'by_loophole_type': by_loophole,
            'by_geography': by_geo,
            'by_regime': {},
            'rolling_7d_accuracy': rolling_7d,
            'rolling_30d_accuracy': rolling_30d
        })
        print(f"[Validator] Accuracy summary: {overall_accuracy}% ({hits}/{total})")
    except Exception as e:
        print(f"[Validator] Accuracy summary error: {e}")
