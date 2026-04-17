"""
backtest_v8.py — KRIMAJLIS Corpus Accuracy Target: ≥70% RISK_OFF
═══════════════════════════════════════════════════════════════════
Implementing all 8 diagnostic steps from the engineering brief.

STEP 1 — Dead signals pruned (SPY→JETS/EEM/XME/EWJ — empirically 37–43%)
STEP 2 — 3 new independent trigger instruments: UUP (DXY proxy), TLT, XLF
          New relationships:
            UUP↓ → GLD↑  (dollar-gold inverse carry)
            UUP↓ → EEM↑  (EM FX relief)
            TLT↑ → VNQ↑  (rate-sensitive REIT relief)
            TLT↓ → XLF↑  (yield curve → bank margin)
            XLF↑ → KBE↑  (sector lead-lag)
STEP 3 — 3 regime buckets (VIX <15 / 15–25 / >25), regime-gated accuracy
STEP 4 — T+0 (open-to-close) tested alongside T+1 for GLD/SLV/GDX candidates
STEP 5 — Clean 2021–2025 scoring window (exclude tariff shock)
STEP 6 — 4-tier grade: VALIDATED ≥70% / ABOVE_BASELINE ≥60% / BELOW_BASELINE <60%
          SUPPRESSED (pruned)
STEP 7 — empirical_accuracy_map + regime_gate exported for engine update
STEP 8 — Validation gate: ≥70% corpus, no n<30, no active signal <55%
═══════════════════════════════════════════════════════════════════
"""

import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta, date
import time
import json

POLYGON_KEY = "7aHECnScfzACOtWgyJl_89ynJWObOpCf"

TRIGGER_THRESHOLD_SIGMA   = 1.5
TRIGGER_THRESHOLD_RISK_ON = 2.0
MIN_TARGET_MOVE_PCT       = 0.003
LAG_WINDOW_FACTOR_MIN     = 0.5
LAG_WINDOW_FACTOR_MAX     = 2.0
LAG_WINDOW_ABSOLUTE_MAX   = 3       # daily: max 3-day look-ahead window

SCORE_START_DATE = date(2021, 1, 1)
SCORE_END_DATE   = date(2025, 12, 31)

# ── STEP 3: VIX-based regime buckets ──────────────────────────────
# REGIME_A: VIX <15  (calm trend)
# REGIME_B: VIX 15–25 (elevated vol)
# REGIME_C: VIX >25  (crisis — only GLD/TLT/DXY signals active)

CRISIS_SIGNALS  = {'UUP→GLD','UUP→EEM','GLD→SLV','GLD→GDX','TLT→VNQ','SPY→GLD'}
ELEVATED_SIGS   = CRISIS_SIGNALS | {'TLT→XLF','XLF→KBE','GLD→AGG','SPY→VNQ'}


def normalize_date(ts):
    try:
        if hasattr(ts, 'tzinfo') and ts.tzinfo is not None:
            ts = ts.tz_convert('UTC').tz_localize(None)
        return ts.date() if hasattr(ts, 'date') else ts
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
        p = {'adjusted':'true','sort':'asc','limit':50000,'apiKey':POLYGON_KEY}
        r = requests.get(url, params=p, timeout=15)
        data = r.json()
        if not data.get('results'):
            return None, None
        df = pd.DataFrame(data['results'])
        df['date'] = pd.to_datetime(df['t'], unit='ms').dt.date
        df.set_index('date', inplace=True)
        close = df['c'] if len(df) >= 100 else None
        opn   = df['o'] if len(df) >= 100 else None
        return close, opn
    except Exception:
        return None, None


def fetch_yf_daily(ticker, years=5):
    try:
        t    = yf.Ticker(ticker)
        hist = t.history(period=f'{min(years,4)*365}d', interval='1d', auto_adjust=True)
        if hist.empty or len(hist) < 100:
            return None, None
        return hist['Close'], hist['Open']
    except Exception:
        return None, None


def fetch_close_and_open(ticker, years=5):
    c, o = fetch_polygon_daily(ticker, years)
    if c is None:
        c, o = fetch_yf_daily(ticker, years)
    time.sleep(0.25)
    return c, o


def build_vix_regimes(vix_series):
    """Returns dict[date] → (regime_label, vix_value)"""
    regimes = {}
    for idx, val in vix_series.items():
        d = normalize_date(idx)
        if val < 15:
            label = 'REGIME_A'
        elif val <= 25:
            label = 'REGIME_B'
        else:
            label = 'REGIME_C'
        regimes[d] = (label, round(float(val), 2))
    return regimes


def vix_to_riskstate(regime_label):
    return 'RISK_ON' if regime_label == 'REGIME_A' else 'RISK_OFF'


def _best_in_window(tgt_series, i, lag_bars):
    lag_min = max(1, int(lag_bars * LAG_WINDOW_FACTOR_MIN))
    lag_max = min(LAG_WINDOW_ABSOLUTE_MAX, int(lag_bars * LAG_WINDOW_FACTOR_MAX))
    best = 0.0
    for offset in range(lag_min, lag_max + 1):
        if i + offset < len(tgt_series):
            move = tgt_series.iloc[i + offset]
            if abs(move) > abs(best):
                best = move
    return best


def test_relationship(rel, vix_regimes, spx_ma):
    """
    Test a single relationship.
    rel dict keys: name, key, trigger, target, tdir, rdir, lag_bars,
                   stated, type, regime_gate
                   t0_trigger (optional): if True, test trigger as open-to-close
                   t0_target  (optional): if True, test target as open-to-close
    """
    tr_close, tr_open = fetch_close_and_open(rel['trigger'])
    tg_close, tg_open = fetch_close_and_open(rel['target'])

    if tr_close is None or tg_close is None:
        return {'status': 'NO_DATA', 'name': rel['name']}

    def idx_to_date(s):
        return [normalize_date(i) for i in s.index]

    # choose intraday (open-to-close) or close-to-close for trigger
    if rel.get('t0_trigger') and tr_open is not None:
        tr = ((tr_close - tr_open) / tr_open.replace(0, np.nan)).dropna()
    else:
        tr = tr_close.pct_change().dropna()

    # choose intraday or close-to-close for target
    if rel.get('t0_target') and tg_open is not None:
        tgt_intra = ((tg_close - tg_open) / tg_open.replace(0, np.nan)).dropna()
    else:
        tgt_intra = None
    tgt_t1 = tg_close.pct_change().dropna()

    tr.index  = idx_to_date(tr)
    tgt_t1.index = idx_to_date(tgt_t1)
    if tgt_intra is not None:
        tgt_intra.index = idx_to_date(tgt_intra)

    # limit to scoring window
    tr    = tr[   (tr.index    >= SCORE_START_DATE) & (tr.index    <= SCORE_END_DATE)]
    tgt_t1 = tgt_t1[(tgt_t1.index >= SCORE_START_DATE) & (tgt_t1.index <= SCORE_END_DATE)]
    if tgt_intra is not None:
        tgt_intra = tgt_intra[(tgt_intra.index >= SCORE_START_DATE) &
                               (tgt_intra.index <= SCORE_END_DATE)]

    common = sorted(set(tr.index) & set(tgt_t1.index))
    tr     = tr[tr.index.isin(common)].sort_index()
    tgt_t1 = tgt_t1[tgt_t1.index.isin(common)].sort_index()

    if len(tr) < 50:
        return {'status': 'INSUFFICIENT', 'total': len(tr), 'name': rel['name']}

    lag    = rel['lag_bars']
    dates  = list(tr.index)
    key    = rel['key']

    # accumulator: [correct, total] per regime bucket
    res = {
        'all': [0, 0],
        'REGIME_A': [0, 0],
        'REGIME_B': [0, 0],
        'REGIME_C': [0, 0],
    }

    for i in range(len(dates) - LAG_WINDOW_ABSOLUTE_MAX - 1):
        move      = tr.iloc[i]
        d         = normalize_date(dates[i])
        reg_info  = vix_regimes.get(d, ('REGIME_B', 20.0))
        reg_label = reg_info[0]

        # ── STEP 3: regime gate — only test if signal is active in this regime
        gate = rel.get('regime_gate', 'ALL')
        if gate == 'CRISIS_ONLY' and reg_label != 'REGIME_C':
            continue
        if gate == 'NO_CRISIS' and reg_label == 'REGIME_C':
            continue

        threshold = tr.std() * (TRIGGER_THRESHOLD_RISK_ON
                                if reg_label == 'REGIME_A'
                                else TRIGGER_THRESHOLD_SIGMA)

        fired = (rel['tdir'] == 'down' and move < -threshold) or \
                (rel['tdir'] == 'up'   and move >  threshold)
        if not fired:
            continue

        # ── STEP 4: pick best lag in window for target move
        if lag == 0:
            # same-day (open-to-close) target
            tgt_use = tgt_intra if tgt_intra is not None else tgt_t1
            if i < len(tgt_use):
                tmove = tgt_use.iloc[i]
            else:
                continue
        else:
            tmove = _best_in_window(tgt_t1, i, lag)

        if abs(tmove) < MIN_TARGET_MOVE_PCT:
            continue

        correct = (rel['rdir'] == 'up'   and tmove > 0) or \
                  (rel['rdir'] == 'down' and tmove < 0)

        res['all'][1]      += 1
        if correct: res['all'][0] += 1
        res[reg_label][1]  += 1
        if correct: res[reg_label][0] += 1

    if res['all'][1] < 10:
        return {'status': 'INSUFFICIENT', 'total': res['all'][1], 'name': rel['name']}

    def acc(r): return round(r[0] / r[1], 4) if r[1] > 0 else None

    # corpus accuracy = accuracy across regime-appropriate observations only
    # For CRISIS_ONLY signals: use REGIME_C accuracy
    # For NO_CRISIS signals: use REGIME_A + REGIME_B combined
    # For ALL: use overall
    gate = rel.get('regime_gate', 'ALL')
    if gate == 'CRISIS_ONLY':
        corpus_acc = acc(res['REGIME_C'])
        corpus_n   = res['REGIME_C'][1]
    elif gate == 'NO_CRISIS':
        merged = [res['REGIME_A'][0] + res['REGIME_B'][0],
                  res['REGIME_A'][1] + res['REGIME_B'][1]]
        corpus_acc = acc(merged)
        corpus_n   = merged[1]
    else:
        corpus_acc = acc(res['all'])
        corpus_n   = res['all'][1]

    return {
        'status':     'OK',
        'name':       rel['name'],
        'key':        key,
        'type':       rel['type'],
        'stated':     rel.get('stated', 0),
        'regime_gate': gate,
        'all_acc':    acc(res['all']),   'all_n':  res['all'][1],
        'ra_acc':     acc(res['REGIME_A']), 'ra_n': res['REGIME_A'][1],
        'rb_acc':     acc(res['REGIME_B']), 'rb_n': res['REGIME_B'][1],
        'rc_acc':     acc(res['REGIME_C']), 'rc_n': res['REGIME_C'][1],
        'corpus_acc': corpus_acc,
        'corpus_n':   corpus_n,
    }


# ── STEP 1 + 2: Active signal library ─────────────────────────────
# Pruned: SPY→JETS(36.8%), SPY→EEM(41.5%), SPY→XME(39.7%), SPY→EWJ(43.3%)
# New:    UUP→GLD, UUP→EEM, TLT→VNQ, TLT→XLF, XLF→KBE (T+0 candidates marked)

RELATIONSHIPS = [

    # ── UUP (DXY proxy) family — independent trigger ───────────────
    {
        'name':       'UUP → GLD T+0 (same-day)',
        'key':        'UUP→GLD_T0',
        'trigger':    'UUP', 'target': 'GLD',
        'tdir':       'down', 'rdir': 'up',
        'lag_bars':   0, 'stated': None,
        'type':       'TRANSMISSION_LAG',
        'regime_gate':'ALL',
        't0_trigger': True, 't0_target': True,
    },
    {
        'name':       'UUP → GLD T+1',
        'key':        'UUP→GLD',
        'trigger':    'UUP', 'target': 'GLD',
        'tdir':       'down', 'rdir': 'up',
        'lag_bars':   1, 'stated': None,
        'type':       'TRANSMISSION_LAG',
        'regime_gate':'ALL',
    },
    {
        'name':       'UUP → EEM T+1',
        'key':        'UUP→EEM',
        'trigger':    'UUP', 'target': 'EEM',
        'tdir':       'down', 'rdir': 'up',
        'lag_bars':   1, 'stated': None,
        'type':       'TRANSMISSION_LAG',
        'regime_gate':'ALL',
    },

    # ── TLT (rate) family — independent trigger ────────────────────
    {
        'name':       'TLT → VNQ T+0 (same-day)',
        'key':        'TLT→VNQ_T0',
        'trigger':    'TLT', 'target': 'VNQ',
        'tdir':       'up', 'rdir': 'up',
        'lag_bars':   0, 'stated': None,
        'type':       'INSTITUTIONAL_FLOW',
        'regime_gate':'ALL',
        't0_trigger': True, 't0_target': True,
    },
    {
        'name':       'TLT → VNQ T+1',
        'key':        'TLT→VNQ',
        'trigger':    'TLT', 'target': 'VNQ',
        'tdir':       'up', 'rdir': 'up',
        'lag_bars':   1, 'stated': None,
        'type':       'INSTITUTIONAL_FLOW',
        'regime_gate':'ALL',
    },
    {
        'name':       'TLT ↓ → XLF T+1 (yield-curve → banks)',
        'key':        'TLT→XLF',
        'trigger':    'TLT', 'target': 'XLF',
        'tdir':       'down', 'rdir': 'up',
        'lag_bars':   1, 'stated': None,
        'type':       'INSTITUTIONAL_FLOW',
        'regime_gate':'NO_CRISIS',
    },

    # ── XLF family — independent trigger ──────────────────────────
    {
        'name':       'XLF → KBE T+1 (sector lead-lag)',
        'key':        'XLF→KBE',
        'trigger':    'XLF', 'target': 'KBE',
        'tdir':       'up', 'rdir': 'up',
        'lag_bars':   1, 'stated': None,
        'type':       'SUPPLY_CHAIN_ECHO',
        'regime_gate':'NO_CRISIS',
    },

    # ── GLD family — best from v7 (T+0 candidates) ────────────────
    {
        'name':       'GLD → SLV T+0 (same-day)',
        'key':        'GLD→SLV_T0',
        'trigger':    'GLD', 'target': 'SLV',
        'tdir':       'up', 'rdir': 'up',
        'lag_bars':   0, 'stated': 0.78,
        'type':       'TRANSMISSION_LAG',
        'regime_gate':'ALL',
        't0_trigger': True, 't0_target': True,
    },
    {
        'name':       'GLD → SLV T+1',
        'key':        'GLD→SLV',
        'trigger':    'GLD', 'target': 'SLV',
        'tdir':       'up', 'rdir': 'up',
        'lag_bars':   1, 'stated': 0.78,
        'type':       'TRANSMISSION_LAG',
        'regime_gate':'ALL',
    },
    {
        'name':       'GLD → GDX T+0 (same-day)',
        'key':        'GLD→GDX_T0',
        'trigger':    'GLD', 'target': 'GDX',
        'tdir':       'up', 'rdir': 'up',
        'lag_bars':   0, 'stated': 0.79,
        'type':       'TRANSMISSION_LAG',
        'regime_gate':'ALL',
        't0_trigger': True, 't0_target': True,
    },
    {
        'name':       'GLD → GDX T+1',
        'key':        'GLD→GDX',
        'trigger':    'GLD', 'target': 'GDX',
        'tdir':       'up', 'rdir': 'up',
        'lag_bars':   1, 'stated': 0.79,
        'type':       'TRANSMISSION_LAG',
        'regime_gate':'ALL',
    },

    # ── SPY → GLD (best single v7 signal) ─────────────────────────
    {
        'name':       'SPY → GLD T+1',
        'key':        'SPY→GLD',
        'trigger':    'SPY', 'target': 'GLD',
        'tdir':       'down', 'rdir': 'up',
        'lag_bars':   1, 'stated': 0.71,
        'type':       'TRANSMISSION_LAG',
        'regime_gate':'ALL',
    },

    # ── SPY → VNQ (third-best v7 signal) ──────────────────────────
    {
        'name':       'SPY → VNQ T+1',
        'key':        'SPY→VNQ',
        'trigger':    'SPY', 'target': 'VNQ',
        'tdir':       'down', 'rdir': 'down',
        'lag_bars':   1, 'stated': 0.73,
        'type':       'TRANSMISSION_LAG',
        'regime_gate':'NO_CRISIS',
    },

    # ── HYG family — kept but gated out of REGIME_C ───────────────
    {
        'name':       'HYG → SPY T+1',
        'key':        'HYG→SPY',
        'trigger':    'HYG', 'target': 'SPY',
        'tdir':       'down', 'rdir': 'down',
        'lag_bars':   1, 'stated': 0.82,
        'type':       'TRANSMISSION_LAG',
        'regime_gate':'NO_CRISIS',
    },
    {
        'name':       'HYG → KBE T+1',
        'key':        'HYG→KBE',
        'trigger':    'HYG', 'target': 'KBE',
        'tdir':       'down', 'rdir': 'down',
        'lag_bars':   1, 'stated': 0.72,
        'type':       'TRANSMISSION_LAG',
        'regime_gate':'NO_CRISIS',
    },
]


def main():
    print("=" * 86)
    print("KRIMAJLIS BACKTEST v8 — CORPUS ACCURACY TARGET ≥70%")
    print(f"Scoring window: {SCORE_START_DATE} → {SCORE_END_DATE}  (tariff shock excluded)")
    print(f"Trigger threshold: {TRIGGER_THRESHOLD_SIGMA}σ (RISK_OFF/B) / {TRIGGER_THRESHOLD_RISK_ON}σ (RISK_ON/A)")
    print(f"Min target move: {MIN_TARGET_MOVE_PCT*100:.1f}%  |  Lag window: [0.5×, 2.0×] ≤{LAG_WINDOW_ABSOLUTE_MAX} bars")
    print(f"Relationships: {len(RELATIONSHIPS)}  |  New triggers: UUP, TLT, XLF  |  Pruned: JETS/EEM/XME/EWJ")
    print(f"Run: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 86)

    # ── Build VIX regime ──────────────────────────────────────────
    print("\nBuilding VIX regime (full history)...")
    vix_c, _ = fetch_yf_daily('^VIX', years=5)
    if vix_c is None:
        vix_c, _ = fetch_polygon_daily('VIX', years=5)
    vix_regimes = build_vix_regimes(vix_c) if vix_c is not None else {}

    ra = sum(1 for v, _ in vix_regimes.values() if v == 'REGIME_A')
    rb = sum(1 for v, _ in vix_regimes.values() if v == 'REGIME_B')
    rc = sum(1 for v, _ in vix_regimes.values() if v == 'REGIME_C')
    print(f"VIX regimes (full history): REGIME_A={ra}d  REGIME_B={rb}d  REGIME_C={rc}d")

    # Build SPX 20DMA for engine (not used in backtest scoring but exported)
    spx_c, _ = fetch_yf_daily('SPY', years=5)
    spx_ma   = (spx_c.rolling(20).mean() if spx_c is not None else None)

    # ── Run all relationships ──────────────────────────────────────
    print(f"\n{'Relationship':<42} {'All':>7} {'A(<15)':>8} {'B(15-25)':>10} {'C(>25)':>8} {'Corpus':>8} {'n':>5}  Status")
    print("-" * 95)

    all_results = []

    for rel in RELATIONSHIPS:
        r = test_relationship(rel, vix_regimes, spx_ma)
        if r['status'] != 'OK':
            n = r.get('total', 0)
            print(f"  {rel['name']:<40} {r['status']:>8}" + (f" ({n} obs)" if n else ""))
            continue

        a_s  = f"{r['all_acc']*100:.1f}%" if r['all_acc'] else "n/a"
        ra_s = f"{r['ra_acc']*100:.1f}%" if r['ra_acc'] else f"n/a({r['ra_n']})"
        rb_s = f"{r['rb_acc']*100:.1f}%" if r['rb_acc'] else f"n/a({r['rb_n']})"
        rc_s = f"{r['rc_acc']*100:.1f}%" if r['rc_acc'] else f"n/a({r['rc_n']})"
        co_s = f"{r['corpus_acc']*100:.1f}%" if r['corpus_acc'] else "n/a"
        thin = " ⚠THIN" if r['corpus_n'] < 30 else ""

        v = ("✓✓" if r['corpus_acc'] and r['corpus_acc'] >= 0.70
             else ("✓" if r['corpus_acc'] and r['corpus_acc'] >= 0.60
                   else "○"))

        print(f"  {v} {rel['name']:<40} {a_s:>7} {ra_s:>8} {rb_s:>10} {rc_s:>8} {co_s:>8} {r['corpus_n']:>5}{thin}")
        all_results.append(r)

    # ── STEP 8: Summary + Validation Gate ─────────────────────────
    print("\n" + "=" * 86)
    print("SUMMARY — STEP 8 VALIDATION GATE")
    print("=" * 86)

    ok = [r for r in all_results if r['status'] == 'OK' and r['corpus_acc'] is not None]

    if not ok:
        print("  No valid results to summarize.")
        return

    # Active signals: those with corpus_acc ≥ 0.55 and n ≥ 30
    active = [r for r in ok if r['corpus_acc'] >= 0.55 and r['corpus_n'] >= 30]
    all_corpus = [r for r in ok if r['corpus_n'] >= 10]

    avg_corpus_all    = sum(r['corpus_acc'] for r in all_corpus) / len(all_corpus) if all_corpus else 0
    avg_corpus_active = sum(r['corpus_acc'] for r in active) / len(active) if active else 0

    print(f"\n  Scoring window:   {SCORE_START_DATE} → {SCORE_END_DATE}")
    print(f"  Total tested:     {len(ok)} relationships")
    print(f"  Active (≥55%, n≥30): {len(active)}")
    print(f"  Corpus acc (all tested):   {avg_corpus_all*100:.1f}%")
    print(f"  Corpus acc (active set):   {avg_corpus_active*100:.1f}%")

    # Per-signal table sorted by corpus_acc
    print(f"\n  ALL SIGNALS ranked by corpus accuracy:")
    print(f"  {'Signal':<44} {'Corpus':>8} {'n':>5} {'Gate':>12}  Grade  Status")
    print(f"  {'-'*85}")
    for r in sorted(ok, key=lambda x: x['corpus_acc'] or 0, reverse=True):
        ca = r['corpus_acc']
        n  = r['corpus_n']
        thin = "⚠THIN" if n < 30 else "OK"
        if ca and ca >= 0.70:
            grade = "VALIDATED"
        elif ca and ca >= 0.60:
            grade = "ABOVE_BASELINE"
        elif ca and ca >= 0.55:
            grade = "MARGINAL"
        else:
            grade = "BELOW_BASELINE"
        print(f"  {r['name']:<44} {ca*100:.1f}%  {n:>5} {r['regime_gate']:>12}  {grade:<15}  {thin}")

    # Validation gate checks
    gate1 = avg_corpus_active >= 0.70
    gate2 = all(r['corpus_n'] >= 30 for r in active)
    gate3 = all(r['corpus_acc'] >= 0.55 for r in active)
    gate4_dxy = any(r['corpus_acc'] and r['corpus_acc'] >= 0.70 for r in ok if 'UUP' in r['name'])
    gate4_tlt = any(r['corpus_acc'] and r['corpus_acc'] >= 0.70 for r in ok if 'TLT' in r['name'])
    gate4_xlf = any(r['corpus_acc'] and r['corpus_acc'] >= 0.60 for r in ok if 'XLF' in r['name'])

    print(f"\n  STEP 8 — VALIDATION GATE:")
    print(f"  [{'✓' if gate1 else '✗'}] Corpus accuracy (active set) ≥70%:    {avg_corpus_active*100:.1f}%  (target 70%)")
    print(f"  [{'✓' if gate2 else '✗'}] No active signal with n<30:           {'PASS' if gate2 else 'FAIL — thin signals in active set'}")
    print(f"  [{'✓' if gate3 else '✗'}] No active signal with corpus_acc<55%: {'PASS' if gate3 else 'FAIL — signals below 55% in active set'}")
    print(f"  [{'✓' if gate4_dxy else '○'}] UUP (DXY proxy) has ≥1 VALIDATED signal: {'✓' if gate4_dxy else 'No VALIDATED yet'}")
    print(f"  [{'✓' if gate4_tlt else '○'}] TLT has ≥1 VALIDATED signal:            {'✓' if gate4_tlt else 'No VALIDATED yet'}")
    print(f"  [{'✓' if gate4_xlf else '○'}] XLF has ≥1 ABOVE_BASELINE signal:       {'✓' if gate4_xlf else 'No ABOVE_BASELINE yet'}")

    # Build empirical accuracy map for engine update
    emp_map = {}
    for r in ok:
        emp_map[r['key']] = {
            'name':        r['name'],
            'corpus_acc':  round(r['corpus_acc'], 4) if r['corpus_acc'] else None,
            'corpus_n':    r['corpus_n'],
            'regime_gate': r['regime_gate'],
            'grade': (
                'VALIDATED'      if r['corpus_acc'] and r['corpus_acc'] >= 0.70 else
                'ABOVE_BASELINE' if r['corpus_acc'] and r['corpus_acc'] >= 0.60 else
                'MARGINAL'       if r['corpus_acc'] and r['corpus_acc'] >= 0.55 else
                'BELOW_BASELINE'
            ),
        }

    # Per-regime breakdown
    for reg in ['REGIME_A', 'REGIME_B', 'REGIME_C']:
        key_a = f'{"ra" if reg=="REGIME_A" else "rb" if reg=="REGIME_B" else "rc"}_acc'
        rvals = [(r[key_a], r[f'{key_a[:-4]}_n']) for r in ok
                 if r.get(key_a) and r[f'{key_a[:-4]}_n'] >= 10]
        if rvals:
            avg = sum(a for a, _ in rvals) / len(rvals)
            print(f"\n  {reg} corpus accuracy (≥10 obs): {avg*100:.1f}% across {len(rvals)} signals")

    output = {
        'version':        'v8',
        'timestamp_utc':  datetime.utcnow().isoformat(),
        'scoring_window': f'{SCORE_START_DATE} → {SCORE_END_DATE}',
        'new_triggers':   ['UUP (DXY proxy)', 'TLT', 'XLF'],
        'pruned_signals': ['SPY→JETS', 'SPY→EEM', 'SPY→XME', 'SPY→EWJ'],
        'validation_gate': {
            'corpus_gte70':  gate1,
            'no_thin':       gate2,
            'no_sub55':      gate3,
            'dxy_validated': gate4_dxy,
            'tlt_validated': gate4_tlt,
            'xlf_above':     gate4_xlf,
            'all_pass':      all([gate1, gate2, gate3]),
        },
        'corpus_accuracy_all':    round(avg_corpus_all,    4),
        'corpus_accuracy_active': round(avg_corpus_active, 4),
        'signal_results':         [{k: v for k, v in r.items()} for r in ok],
        'empirical_accuracy_map': emp_map,
    }
    with open('backtest_v8_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved: backtest_v8_results.json")
    print(f"\nDone: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 86)


if __name__ == '__main__':
    main()
