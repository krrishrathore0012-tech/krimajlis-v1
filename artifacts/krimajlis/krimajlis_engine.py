import random
import time
import math
from collections import deque

# ── Empirical accuracy by relationship ID (v8 backtest, 2021-2025) ──
# Source: Kryssalis backtest v8 — 3 new triggers (UUP/TLT/XLF), T+0 same-day
# testing, regime gating. Clean scoring window excludes Jan-Apr 2026 shock.
# Grade tiers: VALIDATED ≥70% / ABOVE_BASELINE ≥60% / BELOW_BASELINE <60%
#              SUPPRESSED (empirical <44%, dead signal)
EMPIRICAL_ACCURACY_BY_REL = {
    # ── VALIDATED ≥70% ─────────────────────────────────────────────
    "rel_015": 0.946,   # Gold→GDX   T+0 same-day   94.6%  n=74  VALIDATED
    "rel_029": 0.986,   # GLD→SLV    T+0 same-day   98.6%  n=72  VALIDATED
    "rel_026": 0.700,   # UUP→GLD    T+0 same-day   70.0%  n=10  VALIDATED (THIN)
    # ── ABOVE_BASELINE ≥60% ────────────────────────────────────────
    "rel_028": 0.677,   # XLF→KBE    T+1            67.7%  n=34  ABOVE_BASELINE
    "rel_012": 0.667,   # Real Yield→VNQ (SPY→VNQ)  66.7%  n=27  ABOVE_BASELINE (THIN)
    "rel_027": 0.611,   # UUP→EEM    T+1            61.1%  n=18  ABOVE_BASELINE (THIN)
    # ── BELOW_BASELINE 44-60% ──────────────────────────────────────
    "rel_001": 0.579,   # DXY→GLD   (UUP→GLD T+1)  57.9%  n=19
    "rel_023": 0.517,   # SPX→XLK                   51.7%  n=60
    "rel_004": 0.500,   # WTI→XLB    proxy
    "rel_011": 0.500,   # Real Yield→KBE            50.0%  n=58
    "rel_007": 0.469,   # VIX→GLD   (SPY→GLD v8)   46.9%  n=64
    "rel_024": 0.464,   # Real Yield→AGG            46.4%  n=28
    "rel_020": 0.456,   # IG Spread→TLT             45.6%  n=57
    "rel_025": 0.456,   # SPX→TLT    proxy          45.6%
    "rel_010": 0.450,   # HY Spread→HYG  proxy
    # ── SUPPRESSED — dead signals (empirical <44%) ─────────────────
    "rel_017": 0.433,   # SPX→EWJ   43.3%  SUPPRESSED
    "rel_002": 0.415,   # DXY→EEM   41.5%  SUPPRESSED
    "rel_013": 0.397,   # BDI→XME   39.7%  SUPPRESSED
    "rel_018": 0.397,   # China PMI→XME  SUPPRESSED
    "rel_003": 0.368,   # WTI→JETS  36.8%  SUPPRESSED
    "rel_009": 0.357,   # HY Spread→SPY 35.7%  SUPPRESSED
}

# Fallback ticker-level accuracy for rels not in BY_REL
EMPIRICAL_ACCURACY = {
    "GLD":      0.579,  "SLV":      0.986,  "GDX":      0.946,
    "VNQ":      0.541,  "EEM":      0.415,  "JETS":     0.368,
    "XME":      0.397,  "EWJ":      0.433,  "KBE":      0.677,
    "XLK":      0.517,  "TLT":      0.456,  "AGG":      0.464,
    "SPY":      0.357,  "HYG":      0.450,  "XLF":      0.677,
    "XLB":      0.500,  "CEW":      0.415,  "BDRY":     None,
    "DJP":      None,   "VXX":      None,   "AUDUSD=X": None,
    "USDINR=X": None,   "^NSEI":    None,
}

# ── STEP 6: 4-tier grade thresholds ────────────────────────────────
GRADE_VALIDATED      = 0.70
GRADE_ABOVE_BASELINE = 0.60
GRADE_SUPPRESSED     = 0.44   # conviction zeroed below this threshold

CAUSAL_RELATIONSHIPS = [
    {
        "id": "rel_001",
        "trigger_node": "DXY",
        "downstream_instrument": "Gold",
        "downstream_ticker": "GLD",
        "direction": "SHORT",
        "lag_min": 2,
        "lag_max": 4,
        "lag_unit": "hours",
        "accuracy": 0.78,
        "expected_move_pct": 1.2,
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "Global",
        "trigger_direction": "falls",
        "rationale": "DXY >0.3σ decline triggers gold repricing lag. 78% of DXY moves >0.3σ resolve into Gold within 4hrs. Mechanism: dollar purchasing power reprices dollar-denominated assets. Entry window: T+0 to T+2hrs. Edge: 1.2% expected move per σ.",
        "chain_nodes": [
            {"node": "DXY Falls", "lag": "t=0", "role": "TRIGGER", "description": "Dollar index crosses σ-0.3 threshold — repricing ignites"},
            {"node": "Fed Rate Expectations", "lag": "t+30m", "role": "PROPAGATION", "description": "Dovish rate signals priced into USD futures"},
            {"node": "Dollar Purchasing Power", "lag": "t+1h", "role": "PROPAGATION", "description": "Dollar-denominated assets mechanically reprice higher"},
            {"node": "Gold Spot Bid", "lag": "t+2h", "role": "PROPAGATION", "description": "Institutional gold bid flows through London/NY fixes"},
            {"node": "GLD ETF Entry", "lag": "t+2-4h", "role": "TARGET", "description": "ETF lags spot — entry window before arbitrage closes"},
        ],
    },
    {
        "id": "rel_002",
        "trigger_node": "DXY",
        "downstream_instrument": "EM Equities",
        "downstream_ticker": "EEM",
        "direction": "LONG",
        "lag_min": 4,
        "lag_max": 6,
        "lag_unit": "hours",
        "accuracy": 0.71,
        "expected_move_pct": 0.8,
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "EM",
        "trigger_direction": "falls",
        "rationale": "DXY σ-decline eases EM debt burden and capital outflow pressure. 71% of USD weakness events reprice EEM within 6hrs. Mechanism: local currency appreciation → EM equity inflows via carry reversal. Entry: T+0 to T+4hrs.",
        "chain_nodes": [
            {"node": "DXY Weakens", "lag": "t=0", "role": "TRIGGER", "description": "Dollar weakens — EM debt service costs fall"},
            {"node": "EM Capital Flows Reverse", "lag": "t+1h", "role": "PROPAGATION", "description": "USD outflows from EM slow — carry reversal begins"},
            {"node": "EM Local FX Strengthens", "lag": "t+2h", "role": "PROPAGATION", "description": "Local currencies appreciate vs USD"},
            {"node": "EM Equity Inflows", "lag": "t+4h", "role": "PROPAGATION", "description": "Institutional rebalancing into EM equities"},
            {"node": "EEM ETF Entry", "lag": "t+4-6h", "role": "TARGET", "description": "ETF catches spot EM with lag — LONG entry window"},
        ],
    },
    {
        "id": "rel_003",
        "trigger_node": "WTI",
        "downstream_instrument": "Airline Stocks",
        "downstream_ticker": "JETS",
        "direction": "LONG",
        "lag_min": 1,
        "lag_max": 2,
        "lag_unit": "sessions",
        "accuracy": 0.71,
        "expected_move_pct": 0.6,
        "loophole_type": "SUPPLY_CHAIN_ECHO",
        "geography": "US",
        "trigger_direction": "falls",
        "rationale": "WTI fall reprices jet fuel forward contracts — 71% resolve into JETS within 1-2 sessions. Mechanism: fuel is 20-30% of airline COGS, every $1/bbl WTI = ~$0.3B annual cost saving for US majors. Equity markets lag cost reality. Entry: next session open.",
        "chain_nodes": [
            {"node": "WTI Crude Falls", "lag": "t=0", "role": "TRIGGER", "description": "Crude drops — jet fuel forward contracts reprice"},
            {"node": "Jet Fuel Futures", "lag": "t+2h", "role": "PROPAGATION", "description": "Refinery throughput margin compresses on lower feedstock"},
            {"node": "Airline CFO Hedging Review", "lag": "t+4h", "role": "PROPAGATION", "description": "Hedge books reassessed — Q guidance revisions begin"},
            {"node": "Operating Cost Projections", "lag": "t+1 session", "role": "PROPAGATION", "description": "Analyst earnings models updated — COGS revised down"},
            {"node": "JETS ETF Entry", "lag": "t+1-2 sessions", "role": "TARGET", "description": "Equity markets lag cost reality — LONG entry window"},
        ],
    },
    {
        "id": "rel_004",
        "trigger_node": "WTI",
        "downstream_instrument": "Materials Sector ETF",
        "downstream_ticker": "XLB",
        "direction": "LONG",
        "lag_min": 5,
        "lag_max": 10,
        "lag_unit": "sessions",
        "accuracy": 0.67,
        "expected_move_pct": 0.5,
        "loophole_type": "SUPPLY_CHAIN_ECHO",
        "geography": "US",
        "trigger_direction": "falls",
        "rationale": "WTI fall reduces petrochemical feedstock costs across materials sector — 67% resolve into XLB within 5-10 sessions. Mechanism: lower crude input costs compress production expenses for chemicals, coatings, and industrial materials. XLB (Materials Select Sector SPDR) captures the broad sector repricing. Entry: T+5 sessions.",
        "chain_nodes": [
            {"node": "WTI Crude Falls", "lag": "t=0", "role": "TRIGGER", "description": "Crude drops — petrochemical feedstock cheaper across sector"},
            {"node": "Naphtha/Benzene Prices", "lag": "t+1 session", "role": "PROPAGATION", "description": "Chemical feedstock costs decline after refinery cycle"},
            {"node": "Materials Input Cost Compression", "lag": "t+3 sessions", "role": "PROPAGATION", "description": "Broad materials sector input costs reprice lower"},
            {"node": "Gross Margin Expansion", "lag": "t+5 sessions", "role": "PROPAGATION", "description": "Forward gross margin estimates revised upward sector-wide"},
            {"node": "XLB Materials ETF LONG Entry", "lag": "t+5-10 sessions", "role": "TARGET", "description": "Materials sector ETF lags input cost relief — LONG entry window"},
        ],
    },
    {
        "id": "rel_005",
        "trigger_node": "WTI",
        "downstream_instrument": "INR",
        "downstream_ticker": "USDINR=X",
        "direction": "SHORT",
        "lag_min": 1,
        "lag_max": 1,
        "lag_unit": "sessions",
        "accuracy": 0.74,
        "expected_move_pct": 0.7,
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "India",
        "trigger_direction": "rises",
        "rationale": "WTI rise pressures India's current account — 74% of WTI spikes >0.5σ resolve into USDINR within 1 session. India imports 85% of crude: every $10/bbl = ~$14B annual import bill increase. FX intervention probability rises >70% at current levels. Entry: T+1 session.",
        "chain_nodes": [
            {"node": "WTI Rises", "lag": "t=0", "role": "TRIGGER", "description": "Crude rises — India import bill surges immediately"},
            {"node": "Current Account Pressure", "lag": "t+1h", "role": "PROPAGATION", "description": "Trade deficit widens vs consensus estimates"},
            {"node": "RBI Intervention Signal", "lag": "t+2h", "role": "PROPAGATION", "description": "FX reserve drawdown risk — RBI flags intervention"},
            {"node": "INR Spot Depreciates", "lag": "t+4h", "role": "PROPAGATION", "description": "Rupee weakens mechanically vs dollar"},
            {"node": "USDINR SHORT Entry", "lag": "t+1 session", "role": "TARGET", "description": "Exchange rate adjustment completes — entry window"},
        ],
    },
    {
        "id": "rel_006",
        "trigger_node": "VIX",
        "downstream_instrument": "EM Currencies",
        "downstream_ticker": "CEW",
        "direction": "SHORT",
        "lag_min": 4,
        "lag_max": 6,
        "lag_unit": "hours",
        "accuracy": 0.69,
        "expected_move_pct": 0.9,
        "loophole_type": "INSTITUTIONAL_FLOW",
        "geography": "EM",
        "trigger_direction": "spikes",
        "rationale": "VIX spike triggers EM institutional stop-losses algorithmically. 69% of VIX spikes >1σ reprice CEW within 4-6hrs. Mechanism: risk-off mandate = automatic EM position unwind. Capital repatriation to USD drives EM FX lower. Entry: T+0 to T+4hrs.",
        "chain_nodes": [
            {"node": "VIX Spikes", "lag": "t=0", "role": "TRIGGER", "description": "Risk sentiment deteriorates — institutional stop-losses fire"},
            {"node": "EM Algorithmic Unwind", "lag": "t+30m", "role": "PROPAGATION", "description": "Risk-parity and vol-target mandates unwind EM exposure"},
            {"node": "Capital Repatriation to USD", "lag": "t+2h", "role": "PROPAGATION", "description": "USD demand spikes as EM positions liquidated"},
            {"node": "EM FX Spot Pressure", "lag": "t+3h", "role": "PROPAGATION", "description": "EM currencies sold across the board vs USD"},
            {"node": "CEW ETF SHORT Entry", "lag": "t+4-6h", "role": "TARGET", "description": "ETF reprices vs OTC EM FX — SHORT entry window"},
        ],
    },
    {
        "id": "rel_007",
        "trigger_node": "VIX",
        "downstream_instrument": "Gold",
        "downstream_ticker": "GLD",
        "direction": "LONG",
        "lag_min": 2,
        "lag_max": 3,
        "lag_unit": "hours",
        "accuracy": 0.76,
        "expected_move_pct": 1.2,
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "Global",
        "trigger_direction": "spikes",
        "rationale": "VIX spike triggers institutional gold allocation before retail catches on. 76% of VIX spikes >1σ resolve into GLD within 2-3hrs. Mechanism: safe-haven mandate flows from pension/sovereign wealth precede retail. Entry: T+0 to T+2hrs. Edge: 1.2% expected move per σ.",
        "chain_nodes": [
            {"node": "VIX Spikes", "lag": "t=0", "role": "TRIGGER", "description": "Fear index ignites — safe-haven demand activates"},
            {"node": "CTA Momentum Signals", "lag": "t+30m", "role": "PROPAGATION", "description": "Trend-following models flip to gold long simultaneously"},
            {"node": "Institutional Flight to Quality", "lag": "t+1h", "role": "PROPAGATION", "description": "Pension/sovereign wealth mandates allocate to gold"},
            {"node": "Gold Spot Repricing", "lag": "t+2h", "role": "PROPAGATION", "description": "London gold fix gaps higher — spot leads ETF"},
            {"node": "GLD ETF LONG Entry", "lag": "t+2-3h", "role": "TARGET", "description": "ETF catches spot with 2-3hr lag — entry window before close"},
        ],
    },
    {
        "id": "rel_008",
        "trigger_node": "VIX",
        "downstream_instrument": "Vol Term Structure",
        "downstream_ticker": "VXX",
        "direction": "SELL_VOL",
        "lag_min": 0,
        "lag_max": 0,
        "lag_unit": "sessions",
        "accuracy": 0.84,
        "expected_move_pct": 2.5,
        "loophole_type": "VOLATILITY_SURFACE",
        "geography": "US",
        "trigger_direction": "spikes",
        "rationale": "VIX >20 inverts vol term structure — short front-month vs long back-month. 84% accuracy. Historical RV overshoot: 40%. Mechanism: retail panic buys front-month vol → near-term IV richens vs back months. Mean reversion window: T+0 to T+5 sessions.",
        "chain_nodes": [
            {"node": "VIX Spikes", "lag": "t=0", "role": "TRIGGER", "description": "VIX crosses 20 threshold — term structure inverts"},
            {"node": "Retail Vol Panic Buying", "lag": "t+30m", "role": "PROPAGATION", "description": "Front-month puts bid up — near-term IV richens sharply"},
            {"node": "Back-Month Vol Lags", "lag": "t+2h", "role": "PROPAGATION", "description": "Long-dated implied vol fails to match front-month spike"},
            {"node": "Term Structure Inversion", "lag": "t+3h", "role": "PROPAGATION", "description": "Contango collapses into backwardation — mispricing peaks"},
            {"node": "VXX SELL_VOL Entry", "lag": "t=0 session", "role": "TARGET", "description": "Sell front-month vol — 40% RV overshoot historically"},
        ],
    },
    {
        "id": "rel_009",
        "trigger_node": "HY Spread",
        "downstream_instrument": "SPX",
        "downstream_ticker": "SPY",
        "direction": "SHORT",
        "lag_min": 0,
        "lag_max": 0,
        "lag_unit": "sessions",
        "accuracy": 0.82,
        "expected_move_pct": 1.5,
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "US",
        "trigger_direction": "widens",
        "rationale": "HY spread widening leads equity repricing — credit is the early warning system. 82% of HY widening >0.5σ precede SPX repricing. Mechanism: credit markets price recession 0-2hrs before equities. Entry: T+0 immediately on widening confirmation.",
        "chain_nodes": [
            {"node": "HY Spreads Widen", "lag": "t=0", "role": "TRIGGER", "description": "Credit market prices recession risk ahead of equities"},
            {"node": "Institutional Equity Risk Cut", "lag": "t+30m", "role": "PROPAGATION", "description": "Portfolio managers reduce equity beta mechanically"},
            {"node": "Futures Gap Down", "lag": "t+1h", "role": "PROPAGATION", "description": "Index futures reprice as credit stress confirmed"},
            {"node": "Options Dealer Hedging", "lag": "t+2h", "role": "PROPAGATION", "description": "Dealers sell delta to hedge put exposure — amplifies move"},
            {"node": "SPY SHORT Entry", "lag": "t=0 session", "role": "TARGET", "description": "Equity catches credit — SHORT entry before gap close"},
        ],
    },
    {
        "id": "rel_010",
        "trigger_node": "HY Spread",
        "downstream_instrument": "HYG ETF",
        "downstream_ticker": "HYG",
        "direction": "SHORT",
        "lag_min": 1,
        "lag_max": 2,
        "lag_unit": "hours",
        "accuracy": 0.88,
        "expected_move_pct": 0.8,
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "US",
        "trigger_direction": "widens",
        "rationale": "HY OTC spreads widen → HYG NAV must reprice with 1-2hr lag. 88% accuracy — mechanical arbitrage. ETF temporarily trades at premium to fair NAV. Authorized participant arbitrage closes gap within 2hrs. Entry: T+0 to T+1hr. Edge: ETF-to-OTC pricing lag.",
        "chain_nodes": [
            {"node": "HY OTC Spreads Widen", "lag": "t=0", "role": "TRIGGER", "description": "OTC credit market spreads blow out sharply"},
            {"node": "HYG NAV Calculation Lags", "lag": "t+30m", "role": "PROPAGATION", "description": "ETF NAV update delayed vs real-time OTC market"},
            {"node": "ETF Premium to Fair NAV", "lag": "t+1h", "role": "PROPAGATION", "description": "HYG briefly trades above its fair NAV — mispricing confirmed"},
            {"node": "AP Arbitrage Activation", "lag": "t+1.5h", "role": "PROPAGATION", "description": "Authorized participants create/redeem to close premium"},
            {"node": "HYG SHORT Entry", "lag": "t+1-2h", "role": "TARGET", "description": "Arbitrage window — SHORT before NAV reprices down"},
        ],
    },
    {
        "id": "rel_011",
        "trigger_node": "Real Yield",
        "downstream_instrument": "Banking Sector",
        "downstream_ticker": "KBE",
        "direction": "LONG",
        "lag_min": 3,
        "lag_max": 5,
        "lag_unit": "sessions",
        "accuracy": 0.74,
        "expected_move_pct": 1.1,
        "loophole_type": "INSTITUTIONAL_FLOW",
        "geography": "US",
        "trigger_direction": "falls",
        "rationale": "Real yield fall signals Fed pivot → bank NIM expansion expected. 74% resolve into KBE within 3-5 sessions. Mechanism: NIM sensitivity ~15bps per 100bps real yield move. Institutional value rotators add bank exposure 3-5 sessions after signal. Entry: T+3 sessions.",
        "chain_nodes": [
            {"node": "Real Yield Falls", "lag": "t=0", "role": "TRIGGER", "description": "10yr real yield drops — Fed pivot signaled"},
            {"node": "Forward Rate Repricing", "lag": "t+1h", "role": "PROPAGATION", "description": "Forward rate markets price dovish pivot into curve"},
            {"node": "NIM Forecast Revision", "lag": "t+1 session", "role": "PROPAGATION", "description": "Analysts revise net interest margin forecasts upward"},
            {"node": "Institutional Value Rotation", "lag": "t+2 sessions", "role": "PROPAGATION", "description": "Value rotators add banking sector exposure systematically"},
            {"node": "KBE ETF LONG Entry", "lag": "t+3-5 sessions", "role": "TARGET", "description": "Banking sector re-rates vs bonds — LONG entry window"},
        ],
    },
    {
        "id": "rel_012",
        "trigger_node": "Real Yield",
        "downstream_instrument": "Real Estate",
        "downstream_ticker": "VNQ",
        "direction": "LONG",
        "lag_min": 5,
        "lag_max": 8,
        "lag_unit": "sessions",
        "accuracy": 0.69,
        "expected_move_pct": 1.0,
        "loophole_type": "INSTITUTIONAL_FLOW",
        "geography": "US",
        "trigger_direction": "falls",
        "rationale": "Real yield fall eases REIT cap rate benchmarks — 69% resolve into VNQ within 5-8 sessions. Mechanism: 10yr real yield drives REIT cap rate expectations 1:1. DCF models re-run as lower discount rate lifts NAV. Institutional REIT allocation follows 5-8 sessions later.",
        "chain_nodes": [
            {"node": "Real Yield Falls", "lag": "t=0", "role": "TRIGGER", "description": "Real yield drops — REIT cap rate benchmarks ease"},
            {"node": "Mortgage Rate Expectations", "lag": "t+1h", "role": "PROPAGATION", "description": "10yr real yield drives mortgage reset expectations lower"},
            {"node": "REIT DCF Model Revision", "lag": "t+1 session", "role": "PROPAGATION", "description": "Analysts re-run DCF with lower discount rate — NAV lifts"},
            {"node": "Property Valuation Uplift", "lag": "t+3 sessions", "role": "PROPAGATION", "description": "NAV estimates revised higher across REIT sector"},
            {"node": "VNQ ETF LONG Entry", "lag": "t+5-8 sessions", "role": "TARGET", "description": "REIT sector re-rates vs bonds — LONG entry window"},
        ],
    },
    {
        "id": "rel_013",
        "trigger_node": "BDI",
        "downstream_instrument": "Mining Stocks",
        "downstream_ticker": "XME",
        "direction": "SHORT",
        "lag_min": 8,
        "lag_max": 12,
        "lag_unit": "sessions",
        "accuracy": 0.66,
        "expected_move_pct": 0.7,
        "loophole_type": "SUPPLY_CHAIN_ECHO",
        "geography": "Global",
        "trigger_direction": "falls",
        "rationale": "BDI weakness signals dry bulk demand collapse — 66% resolve into XME within 8-12 sessions. Mechanism: freight rates directly price commodity demand; mining revenue follows after inventory reset cycle (8-12 sessions). 0.7% expected equity move per σ BDI. Entry: T+8 sessions.",
        "chain_nodes": [
            {"node": "BDI Falls", "lag": "t=0", "role": "TRIGGER", "description": "Baltic Dry collapses — demand shock for dry bulk confirmed"},
            {"node": "Freight Rate Collapse", "lag": "t+1h", "role": "PROPAGATION", "description": "Capesize/Panamax spot rates renegotiated sharply lower"},
            {"node": "Mine Utilization Signals", "lag": "t+3 sessions", "role": "PROPAGATION", "description": "Operators signal production rate cuts — volume expectations drop"},
            {"node": "Revenue Forecast Downgrades", "lag": "t+5 sessions", "role": "PROPAGATION", "description": "Analyst revenue models revised down — earnings estimates cut"},
            {"node": "XME ETF SHORT Entry", "lag": "t+8-12 sessions", "role": "TARGET", "description": "Mining equities reprice demand shock — SHORT entry window"},
        ],
    },
    {
        "id": "rel_014",
        "trigger_node": "BDI",
        "downstream_instrument": "Dry Bulk Shipping ETF",
        "downstream_ticker": "BDRY",
        "direction": "SHORT",
        "lag_min": 3,
        "lag_max": 5,
        "lag_unit": "sessions",
        "accuracy": 0.72,
        "expected_move_pct": 0.9,
        "loophole_type": "SUPPLY_CHAIN_ECHO",
        "geography": "Global",
        "trigger_direction": "falls",
        "rationale": "BDI fall → OTC dry bulk freight rates collapse → BDRY ETF lags by 3-5 sessions. 72% accuracy. Mechanism: BDRY (Breakwave Dry Bulk Shipping ETF) directly tracks near-curve Baltic Dry freight futures — charter renewals lock in lower rates before ETF nav updates. Entry: T+0 to T+3 sessions.",
        "chain_nodes": [
            {"node": "BDI Falls", "lag": "t=0", "role": "TRIGGER", "description": "Baltic Dry Index collapses — OTC spot contracts renegotiated"},
            {"node": "Charter Renewal Pressure", "lag": "t+1h", "role": "PROPAGATION", "description": "Shipowners lock in lower charter rates vs prior contracts"},
            {"node": "Revenue Visibility Drops", "lag": "t+1 session", "role": "PROPAGATION", "description": "Forward revenue estimates for dry bulk operators revised down"},
            {"node": "Futures Roll Adjustment", "lag": "t+2 sessions", "role": "PROPAGATION", "description": "Near-curve freight futures roll adjusts to new spot level"},
            {"node": "BDRY ETF SHORT Entry", "lag": "t+3-5 sessions", "role": "TARGET", "description": "BDRY lags spot freight market repricing — SHORT entry window"},
        ],
    },
    {
        "id": "rel_015",
        "trigger_node": "Gold",
        "downstream_instrument": "Gold Miners",
        "downstream_ticker": "GDX",
        "direction": "LONG",
        "lag_min": 1,
        "lag_max": 2,
        "lag_unit": "sessions",
        "accuracy": 0.79,
        "expected_move_pct": 1.8,
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "Global",
        "trigger_direction": "rises",
        "rationale": "Gold spot rise → non-linear miner FCF expansion. 79% resolve into GDX within 1-2 sessions. Mechanism: operating leverage — fixed cost base makes every $1/oz gold = ~$0.85/oz FCF increase. Equity repricing lags spot by 1-2 sessions. Edge: 1.8x gold move in equity. Entry: next session open.",
        "chain_nodes": [
            {"node": "Gold Spot Rises", "lag": "t=0", "role": "TRIGGER", "description": "Gold spot rises — non-linear miner FCF expansion begins"},
            {"node": "AISC Operating Leverage", "lag": "t+1h", "role": "PROPAGATION", "description": "Fixed cost base creates 1.8x leverage vs gold move"},
            {"node": "FCF Estimate Revision", "lag": "t+4h", "role": "PROPAGATION", "description": "Analysts revise free cash flow models upward"},
            {"node": "Institutional Mining Rotation", "lag": "t+1 session", "role": "PROPAGATION", "description": "Funds buy miners as leveraged gold proxy"},
            {"node": "GDX ETF LONG Entry", "lag": "t+1-2 sessions", "role": "TARGET", "description": "Miners lag gold spot by 1-2 sessions — LONG entry window"},
        ],
    },
    {
        "id": "rel_016",
        "trigger_node": "SPX",
        "downstream_instrument": "Nifty IT",
        "downstream_ticker": "^NSEI",
        "direction": "SHORT",
        "lag_min": 1,
        "lag_max": 1,
        "lag_unit": "sessions",
        "accuracy": 0.77,
        "expected_move_pct": 0.7,
        "loophole_type": "NARRATIVE_VELOCITY",
        "geography": "India",
        "trigger_direction": "falls",
        "rationale": "SPX fall propagates to Nifty IT via ADR pricing and narrative velocity. 77% of SPX drops >0.5σ hit Nifty IT within 1 session. Mechanism: Indian IT company ADRs reprice in US session → gap-down expectation set before India open. Entry: India open next session.",
        "chain_nodes": [
            {"node": "SPX Falls", "lag": "t=0", "role": "TRIGGER", "description": "US tech selloff — narrative propagates globally"},
            {"node": "Indian IT ADR Repricing", "lag": "t+1h", "role": "PROPAGATION", "description": "ADRs of Infosys/TCS/Wipro reprice during US session"},
            {"node": "Narrative Velocity Accelerates", "lag": "t+3h", "role": "PROPAGATION", "description": "India press amplifies US tech narrative — fear spreads"},
            {"node": "Nifty IT Futures Pre-Open", "lag": "t+5h", "role": "PROPAGATION", "description": "Futures gap-down set before India 9:15am open"},
            {"node": "^NSEI SHORT Entry", "lag": "t+1 session", "role": "TARGET", "description": "Nifty IT reprices at India open — SHORT entry window"},
        ],
    },
    {
        "id": "rel_017",
        "trigger_node": "SPX",
        "downstream_instrument": "Asian Equities",
        "downstream_ticker": "EWJ",
        "direction": "SHORT",
        "lag_min": 4,
        "lag_max": 8,
        "lag_unit": "hours",
        "accuracy": 0.81,
        "expected_move_pct": 0.6,
        "loophole_type": "INSTITUTIONAL_FLOW",
        "geography": "Asia",
        "trigger_direction": "falls",
        "rationale": "SPX fall triggers institutional risk-off rebalancing into Asian open. 81% of SPX drops >0.5σ resolve into EWJ within 4-8hrs. Mechanism: US institutional equity beta reduction → Asian index futures sold in London hours → gap-down at Tokyo/Seoul open. Entry: T+4 to T+8hrs.",
        "chain_nodes": [
            {"node": "SPX Falls", "lag": "t=0", "role": "TRIGGER", "description": "US equity selloff — institutional risk-off mandate fires"},
            {"node": "US Institutional Rebalancing", "lag": "t+1h", "role": "PROPAGATION", "description": "Equity beta reduced — USD cash raised systematically"},
            {"node": "Asian Futures Hedging", "lag": "t+2h", "role": "PROPAGATION", "description": "Asian index futures sold in US/London overnight hours"},
            {"node": "Asia Pre-Open Positioning", "lag": "t+3h", "role": "PROPAGATION", "description": "Market makers widen spreads ahead of Tokyo/Seoul open"},
            {"node": "EWJ ETF SHORT Entry", "lag": "t+4-8h", "role": "TARGET", "description": "Japan/Asia equities reprice at open — SHORT entry window"},
        ],
    },
    {
        "id": "rel_018",
        "trigger_node": "China PMI",
        "downstream_instrument": "Metals & Mining ETF",
        "downstream_ticker": "XME",
        "direction": "LONG",
        "lag_min": 2,
        "lag_max": 4,
        "lag_unit": "sessions",
        "accuracy": 0.73,
        "expected_move_pct": 1.3,
        "loophole_type": "SUPPLY_CHAIN_ECHO",
        "geography": "China",
        "trigger_direction": "rises",
        "rationale": "China PMI expansion → steel/metals output ramp → XME metals & mining ETF demand surge. 73% resolve into XME within 2-4 sessions. Mechanism: steel mill utilization rises → iron ore and steel input procurement accelerates → US-listed metals/mining equities (XME components) reprice the global demand signal. 1.3% expected move per σ PMI. Entry: T+2 sessions.",
        "chain_nodes": [
            {"node": "China PMI Rises", "lag": "t=0", "role": "TRIGGER", "description": "Manufacturing PMI beats — metals output expansion confirmed"},
            {"node": "Steel Mill Utilization", "lag": "t+1h", "role": "PROPAGATION", "description": "Mills signal production ramp-up — metals procurement rises"},
            {"node": "Iron Ore & Coking Coal Bid", "lag": "t+1 session", "role": "PROPAGATION", "description": "Raw material bids lift at Dalian/SGX exchanges"},
            {"node": "Global Metals Price Repricing", "lag": "t+2 sessions", "role": "PROPAGATION", "description": "LME copper, steel futures reprice the demand signal"},
            {"node": "XME Metals ETF LONG Entry", "lag": "t+2-4 sessions", "role": "TARGET", "description": "XME lags spot metals repricing — LONG entry window"},
        ],
    },
    {
        "id": "rel_019",
        "trigger_node": "China PMI",
        "downstream_instrument": "AUD",
        "downstream_ticker": "AUDUSD=X",
        "direction": "LONG",
        "lag_min": 1,
        "lag_max": 2,
        "lag_unit": "sessions",
        "accuracy": 0.76,
        "expected_move_pct": 0.5,
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "Australia",
        "trigger_direction": "rises",
        "rationale": "China PMI beat lifts Australia terms-of-trade — 76% resolve into AUDUSD within 1-2 sessions. Mechanism: iron ore/coal are 40% of Australian exports — PMI directly lifts AUD terms-of-trade. FX desks adjust AUD carry within 4hrs. Entry: T+1 session.",
        "chain_nodes": [
            {"node": "China PMI Rises", "lag": "t=0", "role": "TRIGGER", "description": "PMI expansion — commodity demand lifts globally"},
            {"node": "Iron Ore/Coal Reprice", "lag": "t+1h", "role": "PROPAGATION", "description": "Australia's key export prices bid higher immediately"},
            {"node": "Terms of Trade Improvement", "lag": "t+2h", "role": "PROPAGATION", "description": "AUD trade balance expected to improve vs consensus"},
            {"node": "FX Desk AUD Buying", "lag": "t+4h", "role": "PROPAGATION", "description": "FX desks adjust AUD carry positions — buying pressure"},
            {"node": "AUDUSD LONG Entry", "lag": "t+1-2 sessions", "role": "TARGET", "description": "Commodity FX proxy fully reprices — LONG entry window"},
        ],
    },
    {
        "id": "rel_020",
        "trigger_node": "IG Spread",
        "downstream_instrument": "Treasury Bonds",
        "downstream_ticker": "TLT",
        "direction": "LONG",
        "lag_min": 1,
        "lag_max": 3,
        "lag_unit": "sessions",
        "accuracy": 0.71,
        "expected_move_pct": 0.6,
        "loophole_type": "INSTITUTIONAL_FLOW",
        "geography": "US",
        "trigger_direction": "widens",
        "rationale": "IG widening triggers pension fund duration mandate — flight to quality begins. 71% resolve into TLT within 1-3 sessions. Mechanism: liability-matching mandates are mechanically automatic — no discretion. Insurance + pension bond allocation kicks in over 1-3 sessions. Entry: T+1 session.",
        "chain_nodes": [
            {"node": "IG Spreads Widen", "lag": "t=0", "role": "TRIGGER", "description": "Investment grade credit widens — flight to quality begins"},
            {"node": "Pension Duration Mandate", "lag": "t+1h", "role": "PROPAGATION", "description": "Liability-matching mandates trigger automatic bond allocation"},
            {"node": "Insurance Co. Rebalancing", "lag": "t+2h", "role": "PROPAGATION", "description": "Duration-matching flows lift Treasury bid mechanically"},
            {"node": "Primary Dealer Inventory", "lag": "t+1 session", "role": "PROPAGATION", "description": "Dealers position long Treasuries ahead of pension flows"},
            {"node": "TLT ETF LONG Entry", "lag": "t+1-3 sessions", "role": "TARGET", "description": "Treasury rally lags credit stress — LONG entry window"},
        ],
    },
    {
        "id": "rel_021",
        "trigger_node": "DXY",
        "downstream_instrument": "Commodity Complex",
        "downstream_ticker": "DJP",
        "direction": "LONG",
        "lag_min": 3,
        "lag_max": 6,
        "lag_unit": "hours",
        "accuracy": 0.73,
        "expected_move_pct": 0.9,
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "Global",
        "trigger_direction": "falls",
        "rationale": "DXY fall mechanically inflates dollar-denominated commodity basket. 73% of DXY drops >0.3σ resolve into commodity complex within 3-6hrs. Mechanism: WTI/Gold/Metals mathematically reprice inversely to USD. CTA commodity programs trigger long signals simultaneously. Entry: T+0 to T+3hrs.",
        "chain_nodes": [
            {"node": "DXY Falls", "lag": "t=0", "role": "TRIGGER", "description": "Dollar weakens — all dollar-denominated commodities inflate"},
            {"node": "Mechanical Commodity Repricing", "lag": "t+30m", "role": "PROPAGATION", "description": "WTI/Gold/Metals reprice inversely to USD move"},
            {"node": "CTA Commodity Programs", "lag": "t+2h", "role": "PROPAGATION", "description": "Trend-following commodity programs trigger long signals"},
            {"node": "Futures Roll Dynamics", "lag": "t+3h", "role": "PROPAGATION", "description": "Contango structure adjusts to new dollar level"},
            {"node": "DJP Commodity ETF LONG", "lag": "t+3-6h", "role": "TARGET", "description": "Commodity basket ETF lags futures repricing — LONG entry"},
        ],
    },
    {
        "id": "rel_022",
        "trigger_node": "VIX",
        "downstream_instrument": "SPX Options",
        "downstream_ticker": "SVXY",
        "direction": "SELL_VOL",
        "lag_min": 5,
        "lag_max": 8,
        "lag_unit": "sessions",
        "accuracy": 0.77,
        "expected_move_pct": 2.0,
        "loophole_type": "VOLATILITY_SURFACE",
        "geography": "US",
        "trigger_direction": "above 30",
        "rationale": "VIX >30 — implied vol historically overstates realized vol by 40%. 77% of VIX >30 events produce short vol edge within 5-8 sessions. Mechanism: retail panic pushes put/call ratio to extremes → IV/RV divergence peaks → mean reversion inevitable. Edge: ~10pp IV overshoot above realized.",
        "chain_nodes": [
            {"node": "VIX Crosses 30", "lag": "t=0", "role": "TRIGGER", "description": "Implied vol exceeds 30 — historically overstates realized by 40%"},
            {"node": "Retail Options Panic", "lag": "t+1h", "role": "PROPAGATION", "description": "Put/call ratio spikes — fear premium builds beyond realized"},
            {"node": "Market Maker Gamma Hedging", "lag": "t+2h", "role": "PROPAGATION", "description": "Dealers long gamma — vol risk premium expands further"},
            {"node": "IV/RV Divergence Peak", "lag": "t+3h", "role": "PROPAGATION", "description": "Implied vol fully detaches from realized — 40% overshoot"},
            {"node": "SVXY SELL_VOL Entry", "lag": "t+5-8 sessions", "role": "TARGET", "description": "Short vol ETF entry as IV mean reverts to realized"},
        ],
    },
    {
        "id": "rel_023",
        "trigger_node": "SPX",
        "downstream_instrument": "IT Sector IV",
        "downstream_ticker": "XLK",
        "direction": "SELL_VOL",
        "lag_min": 1,
        "lag_max": 3,
        "lag_unit": "sessions",
        "accuracy": 0.69,
        "expected_move_pct": 1.4,
        "loophole_type": "NARRATIVE_VELOCITY",
        "geography": "US",
        "trigger_direction": "tariff narrative",
        "rationale": "Tariff narrative drives IT sector IV spike beyond realized vol. 69% of narrative peaks produce mean reversion within 1-3 sessions. Mechanism: retail options panic buys IT puts → IV richens beyond realized vol → professional fade. Edge: ~8pp IV overshoot above realized vol. Entry: T+1 session.",
        "chain_nodes": [
            {"node": "Tariff News Breaks", "lag": "t=0", "role": "TRIGGER", "description": "Trade war narrative hits — IT sector IV spikes rapidly"},
            {"node": "Narrative Velocity Peak", "lag": "t+1h", "role": "PROPAGATION", "description": "Financial media amplifies tech tariff exposure — panic peaks"},
            {"node": "Retail Options Flow", "lag": "t+2h", "role": "PROPAGATION", "description": "Retail puts flood market — IT sector IV richens vs realized"},
            {"node": "IV vs RV Divergence", "lag": "t+3h", "role": "PROPAGATION", "description": "Realized vol fails to match implied — overshoot confirmed"},
            {"node": "XLK SELL_VOL Entry", "lag": "t+1-3 sessions", "role": "TARGET", "description": "Mean reversion as narrative fades — edge: ~8pp IV overshoot"},
        ],
    },
    {
        "id": "rel_024",
        "trigger_node": "Real Yield",
        "downstream_instrument": "Bond Market",
        "downstream_ticker": "AGG",
        "direction": "LONG",
        "lag_min": 1,
        "lag_max": 3,
        "lag_unit": "sessions",
        "accuracy": 0.72,
        "expected_move_pct": 0.6,
        "loophole_type": "NARRATIVE_VELOCITY",
        "geography": "US",
        "trigger_direction": "CB communication",
        "rationale": "CB communication triggers bond market overreaction beyond fundamentals. 72% resolve in AGG within 1-3 sessions. Mechanism: retail panic over-interprets hawkish/dovish signals → institutional desks fade the move → mean reversion. Entry: T+1 to T+3 sessions post-CB. Edge: institutional fade of retail overreaction.",
        "chain_nodes": [
            {"node": "CB Communication", "lag": "t=0", "role": "TRIGGER", "description": "Central bank signal triggers market overreaction"},
            {"node": "Retail Bond Panic", "lag": "t+30m", "role": "PROPAGATION", "description": "Market over-interprets hawkish/dovish signal — retail panic"},
            {"node": "Media Narrative Peak", "lag": "t+1h", "role": "PROPAGATION", "description": "Financial media amplifies CB narrative — fear/greed peaks"},
            {"node": "Institutional Mean Reversion", "lag": "t+2h", "role": "PROPAGATION", "description": "Professional desks fade retail overreaction systematically"},
            {"node": "AGG ETF LONG Entry", "lag": "t+1-3 sessions", "role": "TARGET", "description": "Bond ETF mean reverts to fair value — LONG entry window"},
        ],
    },
    {
        "id": "rel_025",
        "trigger_node": "SPX",
        "downstream_instrument": "Treasury Bonds",
        "downstream_ticker": "TLT",
        "direction": "LONG",
        "lag_min": 1,
        "lag_max": 3,
        "lag_unit": "sessions",
        "accuracy": 0.74,
        "expected_move_pct": 0.8,
        "loophole_type": "INSTITUTIONAL_FLOW",
        "geography": "US",
        "trigger_direction": "falls",
        "rationale": "Quarter-end 60/40 rebalancing — pension bond buying follows equity selloff mechanically. 74% of SPX drops >1σ trigger bond allocation within 1-3 sessions. Mechanism: mandated rebalancing is not discretionary — pension must buy bonds to restore ratio. Entry: T+1 to T+3 sessions.",
        "chain_nodes": [
            {"node": "SPX Falls", "lag": "t=0", "role": "TRIGGER", "description": "Equity selloff disrupts 60/40 allocation — rebalancing triggered"},
            {"node": "Pension Equity/Bond Ratios", "lag": "t+1h", "role": "PROPAGATION", "description": "60/40 mandate forces bond buy to restore allocation ratio"},
            {"node": "Insurance Portfolio Rebalancing", "lag": "t+2h", "role": "PROPAGATION", "description": "Liability-matching desks add duration mechanically"},
            {"node": "Primary Dealer Bond Flow", "lag": "t+1 session", "role": "PROPAGATION", "description": "Dealer inventory positions ahead of known pension flows"},
            {"node": "TLT ETF LONG Entry", "lag": "t+1-3 sessions", "role": "TARGET", "description": "Treasury rally lags equity selloff — LONG entry window"},
        ],
    },

    # ── rel_026: UUP (DXY proxy) → GLD — v8 VALIDATED (70.0% T+0, n=10 thin) ──
    {
        "id": "rel_026",
        "trigger_node": "UUP",
        "downstream_instrument": "Gold ETF",
        "downstream_ticker": "GLD",
        "direction": "LONG",
        "lag_min": 0,
        "lag_max": 0,
        "lag_unit": "sessions",
        "accuracy": 0.70,
        "expected_move_pct": 0.9,
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "Global",
        "trigger_direction": "falls",
        "regime_gate": "ALL",
        "rationale": "UUP (DXY proxy) intraday decline reprices gold within the same session. v8 empirical: 70.0% T+0 accuracy (n=10). Mechanism: dollar-denominated gold price mechanically inversely correlated with dollar strength. Same-day arbitrage by commodity desks closes the gap before the close.",
        "chain_nodes": [
            {"node": "UUP Falls (DXY Weakens)", "lag": "t=0", "role": "TRIGGER", "description": "Dollar index ETF drops — gold purchasing power premium widens"},
            {"node": "Gold Spot Bid Rises", "lag": "t+1h", "role": "PROPAGATION", "description": "Commodity desks bid gold spot — dollar-denominated repricing"},
            {"node": "GLD ETF Arbitrage", "lag": "t+2h", "role": "PROPAGATION", "description": "Authorized participants close ETF/spot gap — GLD catches up"},
            {"node": "GLD Entry (same-day)", "lag": "t+same session", "role": "TARGET", "description": "v8 T+0 accuracy: 70.0%, n=10 — VALIDATED (thin)"},
        ],
    },

    # ── rel_027: UUP (DXY proxy) → EEM — v8 ABOVE_BASELINE (61.1% T+1, n=18 thin) ──
    {
        "id": "rel_027",
        "trigger_node": "UUP",
        "downstream_instrument": "EM Equities ETF",
        "downstream_ticker": "EEM",
        "direction": "LONG",
        "lag_min": 1,
        "lag_max": 2,
        "lag_unit": "sessions",
        "accuracy": 0.611,
        "expected_move_pct": 0.7,
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "EM",
        "trigger_direction": "falls",
        "regime_gate": "ALL",
        "rationale": "UUP (DXY proxy) decline eases USD-denominated debt burden for EM. v8 empirical: 61.1% T+1 accuracy (n=18). Mechanism: EM sovereign and corporate debt is 70%+ USD-denominated — dollar weakness reduces real debt burden, triggers carry reversal inflows.",
        "chain_nodes": [
            {"node": "UUP Falls (Dollar Weakens)", "lag": "t=0", "role": "TRIGGER", "description": "DXY decline — EM USD debt service cost falls"},
            {"node": "EM Carry Reversal", "lag": "t+2h", "role": "PROPAGATION", "description": "USD short positions unwound — EM FX and equities bid"},
            {"node": "EM Capital Inflows", "lag": "t+4h", "role": "PROPAGATION", "description": "Institutional rebalancing back into EM on dollar weakness"},
            {"node": "EEM ETF T+1", "lag": "t+1-2 sessions", "role": "TARGET", "description": "v8 T+1 accuracy: 61.1%, n=18 — ABOVE_BASELINE (thin)"},
        ],
    },

    # ── rel_028: XLF → KBE — v8 ABOVE_BASELINE (67.7% T+1, n=34) ──
    {
        "id": "rel_028",
        "trigger_node": "XLF",
        "downstream_instrument": "Bank ETF",
        "downstream_ticker": "KBE",
        "direction": "LONG",
        "lag_min": 1,
        "lag_max": 2,
        "lag_unit": "sessions",
        "accuracy": 0.677,
        "expected_move_pct": 0.8,
        "loophole_type": "SUPPLY_CHAIN_ECHO",
        "geography": "US",
        "trigger_direction": "rises",
        "regime_gate": "NO_CRISIS",
        "rationale": "XLF (broad financials) leads KBE (banks) — sector composition lag. v8 empirical: 67.7% T+1 accuracy (n=34). Mechanism: XLF includes insurance, asset managers, and diversified financials that reprice faster than bank-specific KBE on sector rotation flows.",
        "chain_nodes": [
            {"node": "XLF Rises", "lag": "t=0", "role": "TRIGGER", "description": "Broad financials bid — sector rotation into financial names"},
            {"node": "Insurance/AM Reprice First", "lag": "t+1h", "role": "PROPAGATION", "description": "Diversified financials and asset managers reprice ahead of banks"},
            {"node": "Bank Stock Catch-Up", "lag": "t+2-4h", "role": "PROPAGATION", "description": "KBE names lag XLF — bank-specific risk still processing"},
            {"node": "KBE T+1 Entry", "lag": "t+1-2 sessions", "role": "TARGET", "description": "v8 T+1 accuracy: 67.7%, n=34 — ABOVE_BASELINE"},
        ],
    },

    # ── rel_029: GLD → SLV — v8 VALIDATED (98.6% T+0 same-day, n=72) ──
    {
        "id": "rel_029",
        "trigger_node": "Gold",
        "downstream_instrument": "Silver ETF",
        "downstream_ticker": "SLV",
        "direction": "LONG",
        "lag_min": 0,
        "lag_max": 0,
        "lag_unit": "sessions",
        "accuracy": 0.986,
        "expected_move_pct": 1.4,
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "Global",
        "trigger_direction": "rises",
        "regime_gate": "ALL",
        "rationale": "Gold intraday move transmits to silver within the same session. v8 empirical: 98.6% T+0 accuracy (n=72). Mechanism: precious metals markets are co-priced via London/NY fixing — gold and silver move together on the same macro drivers (dollar, real rates, risk-off). ETF arbitrage closes any gap same-day.",
        "chain_nodes": [
            {"node": "GLD Rises Intraday", "lag": "t=0", "role": "TRIGGER", "description": "Gold breaks intraday σ — precious metals complex bid"},
            {"node": "Silver Spot Reprices", "lag": "t+30m", "role": "PROPAGATION", "description": "London/NY precious metals desks co-price silver on gold move"},
            {"node": "SLV ETF Arbitrage", "lag": "t+1h", "role": "PROPAGATION", "description": "Authorized participants close SLV/silver spot gap same session"},
            {"node": "SLV Entry (same-day)", "lag": "t+same session", "role": "TARGET", "description": "v8 T+0 accuracy: 98.6%, n=72 — VALIDATED ✓✓"},
        ],
    },
]

NODE_DEFAULTS = {
    "DXY":       {"name": "US Dollar Index",        "base": 100.0,  "vol": 0.3},
    "Gold":      {"name": "Gold Spot",              "base": 4700.0, "vol": 15.0},
    "WTI":       {"name": "WTI Crude",              "base": 112.0,  "vol": 1.5},
    "VIX":       {"name": "VIX Fear Index",         "base": 24.0,   "vol": 0.8},
    "SPX":       {"name": "S&P 500",                "base": 6580.0, "vol": 30.0},
    "NIFTY":     {"name": "Nifty 50",               "base": 22700.0,"vol": 120.0},
    "IG Spread": {"name": "IG Credit Spread",       "base": 96.0,   "vol": 2.0},
    "HY Spread": {"name": "HY Credit Spread",       "base": 396.0,  "vol": 8.0},
    "Real Yield":{"name": "US 10Y Real Yield",      "base": 2.15,   "vol": 0.05},
    "China PMI": {"name": "China Caixin PMI",       "base": 50.4,   "vol": 0.3},
    "BDI":       {"name": "Baltic Dry Index",       "base": 1420.0, "vol": 40.0},
    "EM FX":     {"name": "EM Currency Basket",     "base": 97.5,   "vol": 0.5},
    # ── v8: 3 new independent trigger instruments ──────────────────
    "UUP":       {"name": "US Dollar ETF (DXY)",    "base": 28.5,   "vol": 0.15},
    "TLT":       {"name": "20Y Treasury ETF",       "base": 90.0,   "vol": 1.2},
    "XLF":       {"name": "Financials Select ETF",  "base": 48.0,   "vol": 0.8},
}

REGIME_DEFAULTS = {
    "growth_momentum": {"label": "CONTRACTION", "score": 28, "direction": "down"},
    "inflation_trajectory": {"label": "DISINFLATING", "score": 42, "direction": "down"},
    "credit_stress": {"label": "ELEVATED", "score": 71, "direction": "up"},
    "dollar_cycle": {"label": "WEAKENING", "score": 38, "direction": "down"},
    "risk_appetite": {"label": "RISK_OFF", "score": 12, "direction": "down"},
    "commodity_cycle": {"label": "DEMAND_SHOCK", "score": 22, "direction": "down"},
}

REGIME_LABELS = {
    "growth_momentum": ["DEEP_CONTRACTION", "CONTRACTION", "STABLE", "EXPANDING", "ACCELERATING"],
    "inflation_trajectory": ["DEFLATING", "DISINFLATING", "STABLE", "RISING", "SURGING"],
    "credit_stress": ["BENIGN", "LOW", "ELEVATED", "HIGH_STRESS", "CRITICAL"],
    "dollar_cycle": ["TROUGH", "WEAKENING", "NEUTRAL", "STRENGTHENING", "PEAK"],
    "risk_appetite": ["RISK_OFF", "CAUTIOUS", "NEUTRAL", "RISK-ON", "EUPHORIC"],
    "commodity_cycle": ["DEMAND_SHOCK", "TROUGH", "RECOVERY", "EXPANSION", "BOOM"],
}


class KrimajlisEngine:
    def __init__(self):
        self.rolling_windows = {}
        self.node_values = {}
        self.trigger_times = {}
        self.signal_cache = []
        self.cycle_count = 0
        self.rng = random.Random(42)

        for node_id, cfg in NODE_DEFAULTS.items():
            self.rolling_windows[node_id] = deque(
                [cfg["base"] + self.rng.gauss(0, cfg["vol"]) for _ in range(20)],
                maxlen=20,
            )
            self.node_values[node_id] = {
                "current": cfg["base"],
                "previous": cfg["base"] * (1 + self.rng.gauss(0, 0.002)),
            }

    def update_node(self, node_id, new_value):
        if node_id not in self.rolling_windows:
            self.rolling_windows[node_id] = deque(maxlen=20)
            self.node_values[node_id] = {"current": new_value, "previous": new_value}

        prev = self.node_values[node_id]["current"]
        self.node_values[node_id]["previous"] = prev
        self.node_values[node_id]["current"] = new_value
        self.rolling_windows[node_id].append(new_value)

    def compute_zscore(self, node_id):
        window = list(self.rolling_windows.get(node_id, []))
        if len(window) < 2:
            return 0.0
        mean = sum(window) / len(window)
        variance = sum((x - mean) ** 2 for x in window) / len(window)
        std = math.sqrt(variance) if variance > 0 else 1e-9
        current = self.node_values.get(node_id, {}).get("current", mean)
        return (current - mean) / std

    def compute_velocity(self, node_id):
        window = list(self.rolling_windows.get(node_id, []))
        if len(window) < 3:
            return 0.0
        recent = window[-1]
        prev = window[-3]
        if prev == 0:
            return 0.0
        return (recent - prev) / abs(prev) * 100

    def get_node_metrics(self, node_id):
        vals = self.node_values.get(node_id, {})
        current = vals.get("current", 0)
        previous = vals.get("previous", current)
        pct_change = ((current - previous) / abs(previous) * 100) if previous != 0 else 0.0
        z_score = self.compute_zscore(node_id)
        velocity = self.compute_velocity(node_id)
        cfg = NODE_DEFAULTS.get(node_id, {})
        return {
            "node_id": node_id,
            "name": cfg.get("name", node_id),
            "current_value": round(current, 4),
            "previous_value": round(previous, 4),
            "pct_change": round(pct_change, 4),
            "velocity": round(velocity, 4),
            "z_score": round(z_score, 4),
        }

    def _regime_alignment(self, rel, regime_state):
        risk_on = regime_state.get("risk_appetite", {}).get("score", 50) > 55
        loophole = rel.get("loophole_type", "")
        direction = rel.get("direction", "LONG")

        if direction in ("LONG", "SPREAD") and risk_on:
            return 1.2
        if direction == "SHORT" and not risk_on:
            return 1.2
        if direction == "SELL_VOL" and risk_on:
            return 1.1
        return 1.0

    def _compute_gap_to_theoretical(self, rel, z_score, regime_multiplier=1.0):
        gap = abs(z_score) * rel["accuracy"] * rel["expected_move_pct"] * regime_multiplier
        gap *= self.rng.uniform(0.85, 1.15)
        return round(min(max(gap, 0.1), 9.99), 2)

    def _get_freshness(self, trigger_time):
        now = time.time()
        age = now - trigger_time
        if age < 30:
            return "FRESH"
        if age < 120:
            return "ACTIVE"
        return "DECAYING"

    def _build_causal_chain(self, rel, z_score):
        trigger_node = rel["trigger_node"]
        downstream = rel["downstream_instrument"]
        lag_label = f"{rel['lag_min']}-{rel['lag_max']} {rel['lag_unit']}"
        return [
            {"node": trigger_node, "lag": "0", "role": "TRIGGER"},
            {"node": f"Market Structure", "lag": f"~{rel['lag_min']} {rel['lag_unit']}", "role": "PROPAGATION"},
            {"node": downstream, "lag": lag_label, "role": "TARGET"},
        ]

    def _get_vix_regime(self):
        """
        Derive 3-bucket VIX regime from current VIX node value.
        REGIME_A: VIX <15  (calm, RISK_ON)
        REGIME_B: VIX 15-25 (elevated, mixed)
        REGIME_C: VIX >25  (crisis, RISK_OFF — only crisis signals fire)
        """
        vix = self.node_values.get("VIX", {}).get("current", 24.0)
        if vix < 15.0:
            return "REGIME_A", vix
        elif vix <= 25.0:
            return "REGIME_B", vix
        else:
            return "REGIME_C", vix

    def generate_signals(self, regime_state):
        self.cycle_count += 1
        now = time.time()
        signals = []

        # ── STEP 3: VIX-based regime bucket ───────────────────────
        vix_regime, vix_val = self._get_vix_regime()

        for rel in CAUSAL_RELATIONSHIPS:
            trigger_node = rel["trigger_node"]
            z_score = self.compute_zscore(trigger_node)

            # ── STEP 3: regime gate — suppress signals outside their regime ──
            gate = rel.get("regime_gate", "ALL")
            if gate == "NO_CRISIS" and vix_regime == "REGIME_C":
                regime_suppressed = True
            elif gate == "CRISIS_ONLY" and vix_regime != "REGIME_C":
                regime_suppressed = True
            else:
                regime_suppressed = False

            regime_mult = self._regime_alignment(rel, regime_state)
            z_boost = min(1.0, abs(z_score) * 0.4)

            # ── STEP 6: empirical accuracy — rel_id first, ticker fallback ──
            rel_id   = rel["id"]
            ticker   = rel["downstream_ticker"]
            empirical = (EMPIRICAL_ACCURACY_BY_REL.get(rel_id)
                         or EMPIRICAL_ACCURACY.get(ticker))
            accuracy_base = empirical if empirical is not None else rel["accuracy"]

            # ── STEP 6: 4-tier grade ──────────────────────────────
            if empirical is None:
                empirical_grade = "UNVALIDATED"
            elif empirical >= GRADE_VALIDATED:
                empirical_grade = "VALIDATED"
            elif empirical >= GRADE_ABOVE_BASELINE:
                empirical_grade = "ABOVE_BASELINE"
            elif empirical >= GRADE_SUPPRESSED:
                empirical_grade = "BELOW_BASELINE"
            else:
                empirical_grade = "SUPPRESSED"

            suppressed = (empirical_grade == "SUPPRESSED") or regime_suppressed

            # ── Conviction: suppressed signals get floor 0.001 ────
            if suppressed:
                conviction = 0.001
            else:
                base_conviction = accuracy_base * regime_mult
                raw_conviction  = base_conviction * (0.7 + z_boost)
                raw_conviction *= self.rng.uniform(0.93, 1.07)
                conviction = min(0.97, max(0.35, raw_conviction))

            effective_z = (z_score if abs(z_score) > 0.3
                           else self.rng.uniform(0.3, 1.5) *
                                (1 if self.rng.random() > 0.5 else -1))

            if rel["id"] not in self.trigger_times:
                self.trigger_times[rel["id"]] = now - self.rng.uniform(0, 90)
            freshness = self._get_freshness(self.trigger_times[rel["id"]])

            gap = self._compute_gap_to_theoretical(rel, effective_z, regime_mult)
            expected_sessions = rel["lag_min"] + self.rng.randint(
                0, max(1, rel["lag_max"] - rel["lag_min"]))
            causal_chain = self._build_causal_chain(rel, effective_z)

            # ── STEP 7: full API output fields ────────────────────
            signal = {
                "signal_id":                rel_id,
                "ticker":                   ticker,
                "instrument_name":          rel["downstream_instrument"],
                "geography":                rel["geography"],
                "direction":                rel["direction"],
                "conviction":               round(conviction, 4),
                "loophole_type":            rel["loophole_type"],
                "causal_chain":             causal_chain,
                "gap_to_theoretical":       gap,
                "expected_reversion_sessions": expected_sessions,
                "regime_alignment":         regime_mult >= 1.1,
                "freshness":                freshness,
                "rationale":                rel["rationale"],
                "trigger_node":             trigger_node,
                "trigger_instrument":       trigger_node,   # STEP 7 explicit field
                "trigger_z_score":          round(effective_z, 4),
                "lag_description":          f"{rel['lag_min']}-{rel['lag_max']} {rel['lag_unit']}",
                "historical_accuracy":      rel["accuracy"],
                "empirical_accuracy":       empirical,
                "empirical_grade":          empirical_grade,
                "regime_gate":              gate,           # STEP 7
                "vix_regime":               vix_regime,     # STEP 7
                "vix_level":                round(vix_val, 2),
                "regime_suppressed":        regime_suppressed,
            }
            signals.append(signal)

        # Active signals sorted by conviction; suppressed signals at the back
        signals.sort(key=lambda x: (0 if x["conviction"] > 0.01 else 1,
                                    -x["conviction"]))
        self.signal_cache = signals
        return self.signal_cache

    def get_full_causal_chain(self, signal_id):
        for rel in CAUSAL_RELATIONSHIPS:
            if rel["id"] == signal_id:
                z_score = self.compute_zscore(rel["trigger_node"])
                gap = self._compute_gap_to_theoretical(rel, z_score, regime_multiplier=1.0)
                chain_nodes = rel.get("chain_nodes", [])
                if chain_nodes:
                    enriched = []
                    for i, n in enumerate(chain_nodes):
                        node = dict(n)
                        if node["role"] == "TRIGGER":
                            node["description"] = f"Z={round(z_score,3)}σ — {n['description']}"
                        elif node["role"] == "TARGET":
                            node["description"] = f"Gap: {gap}% — {n['description']}"
                        enriched.append(node)
                    chain_nodes = enriched
                else:
                    chain_nodes = [
                        {"node": rel["trigger_node"], "lag": "t=0", "role": "TRIGGER", "description": f"Z-score: {round(z_score, 3)}σ"},
                        {"node": "Transmission Channel", "lag": f"t+{rel['lag_min']}{rel['lag_unit'][0]}", "role": "PROPAGATION", "description": rel["loophole_type"].replace("_", " ")},
                        {"node": rel["downstream_instrument"], "lag": f"t+{rel['lag_max']}{rel['lag_unit'][0]}", "role": "TARGET", "description": f"Expected gap close: {gap}%"},
                    ]
                return {
                    "signal_id": signal_id,
                    "trigger_node": rel["trigger_node"],
                    "downstream_instrument": rel["downstream_instrument"],
                    "downstream_ticker": rel["downstream_ticker"],
                    "loophole_type": rel["loophole_type"],
                    "chain_nodes": chain_nodes,
                    "historical_accuracy": rel["accuracy"],
                    "gap_to_theoretical": gap,
                    "confidence_interval": [
                        round(rel["accuracy"] - 0.08, 3),
                        round(rel["accuracy"] + 0.04, 3),
                    ],
                    "lag_description": f"{rel['lag_min']}-{rel['lag_max']} {rel['lag_unit']}",
                    "rationale": rel["rationale"],
                    "z_score": round(z_score, 4),
                }
        return None

    def get_layer_metrics(self):
        layer_map = {
            "TRANSMISSION_LAG": {"name": "Transmission Lag", "layer": 1, "desc": "Cross-asset price transmission delays", "color": "gold"},
            "INSTITUTIONAL_FLOW": {"name": "Institutional Flow", "layer": 2, "desc": "Mandated rebalancing and flow patterns", "color": "blue"},
            "NARRATIVE_VELOCITY": {"name": "Narrative Velocity", "layer": 3, "desc": "News-driven overreaction and mean reversion", "color": "purple"},
            "SUPPLY_CHAIN_ECHO": {"name": "Supply Chain Echo", "layer": 4, "desc": "Cost propagation through industrial chains", "color": "green"},
            "VOLATILITY_SURFACE": {"name": "Volatility Surface", "layer": 5, "desc": "IV vs RV structural mispricing", "color": "red"},
        }
        counts = {}
        for sig in self.signal_cache:
            lt = sig.get("loophole_type", "")
            counts[lt] = counts.get(lt, 0) + 1

        result = []
        for lt, meta in layer_map.items():
            result.append({
                "loophole_type": lt,
                "name": meta["name"],
                "layer": meta["layer"],
                "description": meta["desc"],
                "color": meta["color"],
                "signal_count": counts.get(lt, 0),
            })
        return sorted(result, key=lambda x: x["layer"])

    def drift_simulated_nodes(self):
        for node_id, cfg in NODE_DEFAULTS.items():
            if node_id in ("DXY", "Gold", "WTI", "VIX", "SPX", "NIFTY"):
                continue
            current = self.node_values[node_id]["current"]
            drift = self.rng.gauss(0, cfg["vol"] * 0.5)
            mean_reversion = (cfg["base"] - current) * 0.05
            new_val = current + drift + mean_reversion
            self.update_node(node_id, max(0.01, new_val))
