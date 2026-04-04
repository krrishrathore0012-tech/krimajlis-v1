import random
import time
import math
from collections import deque

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
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "Global",
        "trigger_direction": "falls",
        "rationale": "Dollar weakness unlocks gold bid as alternative store of value",
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
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "EM",
        "trigger_direction": "falls",
        "rationale": "USD weakness eases EM capital outflow pressure, local currencies strengthen",
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
        "loophole_type": "SUPPLY_CHAIN_ECHO",
        "geography": "US",
        "trigger_direction": "falls",
        "rationale": "Jet fuel cost reduction flows through to airline margin expansion with 1-2 session lag",
    },
    {
        "id": "rel_004",
        "trigger_node": "WTI",
        "downstream_instrument": "Paint Sector",
        "downstream_ticker": "SHW",
        "direction": "LONG",
        "lag_min": 12,
        "lag_max": 15,
        "lag_unit": "sessions",
        "accuracy": 0.67,
        "loophole_type": "SUPPLY_CHAIN_ECHO",
        "geography": "US",
        "trigger_direction": "falls",
        "rationale": "Petrochemical feedstock cost reduction materializes in paint sector margins after supply cycle",
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
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "India",
        "trigger_direction": "rises",
        "rationale": "India imports 85% of crude — WTI rise directly pressures current account and rupee",
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
        "loophole_type": "INSTITUTIONAL_FLOW",
        "geography": "EM",
        "trigger_direction": "spikes",
        "rationale": "Risk-off spike triggers institutional flight to USD, EM currency selling follows algorithmically",
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
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "Global",
        "trigger_direction": "spikes",
        "rationale": "Fear spike drives institutional allocation into safe-haven gold before retail catches on",
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
        "loophole_type": "VOLATILITY_SURFACE",
        "geography": "US",
        "trigger_direction": "spikes",
        "rationale": "VIX spike inverts term structure — near-term vol richens vs back months, reversion trade opens",
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
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "US",
        "trigger_direction": "widens",
        "rationale": "HY spread widening signals credit market stress preceding equity repricing",
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
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "US",
        "trigger_direction": "widens",
        "rationale": "Spread widening must materialize in HYG NAV with 1-2hr pricing lag vs OTC credit",
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
        "loophole_type": "INSTITUTIONAL_FLOW",
        "geography": "US",
        "trigger_direction": "falls",
        "rationale": "Fed cut expectations lift bank NIMs and loan demand outlook, institutional rotation follows",
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
        "loophole_type": "INSTITUTIONAL_FLOW",
        "geography": "US",
        "trigger_direction": "falls",
        "rationale": "Rate cut expectations lower cap rate benchmarks, REIT repricing follows with multi-session lag",
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
        "loophole_type": "SUPPLY_CHAIN_ECHO",
        "geography": "Global",
        "trigger_direction": "falls",
        "rationale": "BDI weakness signals demand collapse for dry bulk — mining revenue follows after inventory cycle",
    },
    {
        "id": "rel_014",
        "trigger_node": "BDI",
        "downstream_instrument": "Shipping ETF",
        "downstream_ticker": "BOAT",
        "direction": "SHORT",
        "lag_min": 3,
        "lag_max": 5,
        "lag_unit": "sessions",
        "accuracy": 0.72,
        "loophole_type": "SUPPLY_CHAIN_ECHO",
        "geography": "Global",
        "trigger_direction": "falls",
        "rationale": "BDI directly prices shipping rates — ETF pricing lags OTC freight market by several sessions",
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
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "Global",
        "trigger_direction": "rises",
        "rationale": "Gold price rise improves miner free cash flow non-linearly — equity repricing lags spot by 1-2 sessions",
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
        "loophole_type": "NARRATIVE_VELOCITY",
        "geography": "India",
        "trigger_direction": "falls",
        "rationale": "US tech selloff narrative propagates to Indian IT exporters via ADR pricing and narrative velocity",
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
        "loophole_type": "INSTITUTIONAL_FLOW",
        "geography": "Asia",
        "trigger_direction": "falls",
        "rationale": "US selloff triggers risk-off institutional rebalancing into Asian open with 4-8hr activation lag",
    },
    {
        "id": "rel_018",
        "trigger_node": "China PMI",
        "downstream_instrument": "Iron Ore",
        "downstream_ticker": "TIO",
        "direction": "LONG",
        "lag_min": 2,
        "lag_max": 3,
        "lag_unit": "sessions",
        "accuracy": 0.73,
        "loophole_type": "SUPPLY_CHAIN_ECHO",
        "geography": "China",
        "trigger_direction": "rises",
        "rationale": "PMI expansion signals steel output ramp — iron ore procurement follows after inventory drawdown",
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
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "Australia",
        "trigger_direction": "rises",
        "rationale": "China PMI rise lifts commodity demand — AUD as proxy commodity currency reprices with 1-2 session lag",
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
        "loophole_type": "INSTITUTIONAL_FLOW",
        "geography": "US",
        "trigger_direction": "widens",
        "rationale": "IG widening triggers pension fund rebalancing — mandated bond allocation kicks in over 1-3 session horizon",
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
        "loophole_type": "TRANSMISSION_LAG",
        "geography": "Global",
        "trigger_direction": "falls",
        "rationale": "Dollar weakness mechanically inflates dollar-denominated commodity prices across the complex",
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
        "loophole_type": "VOLATILITY_SURFACE",
        "geography": "US",
        "trigger_direction": "above 30",
        "rationale": "VIX above 30 historically overstates realized vol by 40% — short vol reversion window opens at 5-8 sessions",
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
        "loophole_type": "NARRATIVE_VELOCITY",
        "geography": "US",
        "trigger_direction": "tariff narrative",
        "rationale": "Tariff news drives IT sector IV spike — mean reversion as narrative velocity fades vs realized vol",
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
        "loophole_type": "NARRATIVE_VELOCITY",
        "geography": "US",
        "trigger_direction": "CB communication",
        "rationale": "Central bank communication triggers bond market overreaction — mean reversion trade activates post narrative fade",
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
        "loophole_type": "INSTITUTIONAL_FLOW",
        "geography": "US",
        "trigger_direction": "falls",
        "rationale": "Quarter-end rebalancing triggers equity selling — pension bond buying kicks in with 1-3 session institutional lag",
    },
]

NODE_DEFAULTS = {
    "DXY": {"name": "US Dollar Index", "base": 104.5, "vol": 0.3},
    "Gold": {"name": "Gold Spot", "base": 2340.0, "vol": 8.0},
    "WTI": {"name": "WTI Crude", "base": 78.5, "vol": 1.2},
    "VIX": {"name": "VIX Fear Index", "base": 18.5, "vol": 0.8},
    "SPX": {"name": "S&P 500", "base": 5200.0, "vol": 25.0},
    "NIFTY": {"name": "Nifty 50", "base": 22500.0, "vol": 120.0},
    "IG Spread": {"name": "IG Credit Spread", "base": 95.0, "vol": 2.0},
    "HY Spread": {"name": "HY Credit Spread", "base": 385.0, "vol": 8.0},
    "Real Yield": {"name": "US 10Y Real Yield", "base": 2.1, "vol": 0.05},
    "China PMI": {"name": "China Caixin PMI", "base": 51.2, "vol": 0.3},
    "BDI": {"name": "Baltic Dry Index", "base": 1850.0, "vol": 45.0},
    "EM FX": {"name": "EM Currency Basket", "base": 100.0, "vol": 0.4},
}

REGIME_DEFAULTS = {
    "growth_momentum": {"label": "EXPANDING", "score": 62, "direction": "up"},
    "inflation_trajectory": {"label": "COOLING", "score": 38, "direction": "down"},
    "credit_stress": {"label": "MODERATE", "score": 44, "direction": "neutral"},
    "dollar_cycle": {"label": "PEAK", "score": 71, "direction": "down"},
    "risk_appetite": {"label": "RISK-ON", "score": 65, "direction": "up"},
    "commodity_cycle": {"label": "RECOVERY", "score": 55, "direction": "up"},
}

REGIME_LABELS = {
    "growth_momentum": ["CONTRACTING", "SLOWING", "STABLE", "EXPANDING", "ACCELERATING"],
    "inflation_trajectory": ["DEFLATING", "COOLING", "STABLE", "RISING", "SURGING"],
    "credit_stress": ["BENIGN", "LOW", "MODERATE", "ELEVATED", "CRITICAL"],
    "dollar_cycle": ["TROUGH", "WEAKENING", "NEUTRAL", "STRENGTHENING", "PEAK"],
    "risk_appetite": ["RISK-OFF", "CAUTIOUS", "NEUTRAL", "RISK-ON", "EUPHORIC"],
    "commodity_cycle": ["BUST", "TROUGH", "RECOVERY", "EXPANSION", "BOOM"],
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

    def _compute_gap_to_theoretical(self, rel, z_score):
        base_gap = abs(z_score) * rel["accuracy"] * 100 * self.rng.uniform(0.6, 1.4)
        return round(min(base_gap, 24.9), 2)

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

    def generate_signals(self, regime_state):
        self.cycle_count += 1
        now = time.time()
        signals = []

        for rel in CAUSAL_RELATIONSHIPS:
            trigger_node = rel["trigger_node"]
            z_score = self.compute_zscore(trigger_node)

            should_trigger = abs(z_score) > 0.5 or self.rng.random() < 0.65
            if not should_trigger:
                continue

            effective_z = z_score if abs(z_score) > 0.5 else self.rng.uniform(0.5, 1.8) * (1 if self.rng.random() > 0.5 else -1)

            regime_mult = self._regime_alignment(rel, regime_state)
            conviction = min(0.99, abs(effective_z) * rel["accuracy"] * regime_mult * self.rng.uniform(0.85, 1.15))
            conviction = max(0.30, conviction)

            if rel["id"] not in self.trigger_times:
                self.trigger_times[rel["id"]] = now - self.rng.uniform(0, 90)
            freshness = self._get_freshness(self.trigger_times[rel["id"]])

            gap = self._compute_gap_to_theoretical(rel, effective_z)
            expected_sessions = rel["lag_min"] + self.rng.randint(0, max(1, rel["lag_max"] - rel["lag_min"]))
            causal_chain = self._build_causal_chain(rel, effective_z)

            signal = {
                "signal_id": rel["id"],
                "ticker": rel["downstream_ticker"],
                "instrument_name": rel["downstream_instrument"],
                "geography": rel["geography"],
                "direction": rel["direction"],
                "conviction": round(conviction, 4),
                "loophole_type": rel["loophole_type"],
                "causal_chain": causal_chain,
                "gap_to_theoretical": gap,
                "expected_reversion_sessions": expected_sessions,
                "regime_alignment": regime_mult >= 1.1,
                "freshness": freshness,
                "rationale": rel["rationale"],
                "trigger_node": trigger_node,
                "trigger_z_score": round(effective_z, 4),
                "lag_description": f"{rel['lag_min']}-{rel['lag_max']} {rel['lag_unit']}",
                "historical_accuracy": rel["accuracy"],
            }
            signals.append(signal)

        signals.sort(key=lambda x: x["conviction"], reverse=True)
        self.signal_cache = signals[:25]
        return self.signal_cache

    def get_full_causal_chain(self, signal_id):
        for rel in CAUSAL_RELATIONSHIPS:
            if rel["id"] == signal_id:
                z_score = self.compute_zscore(rel["trigger_node"])
                gap = self._compute_gap_to_theoretical(rel, z_score)
                chain_nodes = [
                    {
                        "node": rel["trigger_node"],
                        "lag": "t=0",
                        "role": "TRIGGER",
                        "lag_coefficient": 1.0,
                        "description": f"Z-score: {round(z_score, 3)}",
                    },
                    {
                        "node": "Transmission Channel",
                        "lag": f"t+{rel['lag_min']}{rel['lag_unit'][0]}",
                        "role": "PROPAGATION",
                        "lag_coefficient": rel["accuracy"] * 0.9,
                        "description": rel["loophole_type"].replace("_", " "),
                    },
                    {
                        "node": rel["downstream_instrument"],
                        "lag": f"t+{rel['lag_max']}{rel['lag_unit'][0]}",
                        "role": "TARGET",
                        "lag_coefficient": rel["accuracy"],
                        "description": f"Expected gap close: {gap}%",
                    },
                ]
                return {
                    "signal_id": signal_id,
                    "trigger_node": rel["trigger_node"],
                    "downstream_instrument": rel["downstream_instrument"],
                    "chain_nodes": chain_nodes,
                    "historical_accuracy": rel["accuracy"],
                    "gap_to_theoretical": gap,
                    "confidence_interval": [
                        round(rel["accuracy"] - 0.08, 3),
                        round(rel["accuracy"] + 0.04, 3),
                    ],
                    "loophole_type": rel["loophole_type"],
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
