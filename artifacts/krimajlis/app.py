import os
import time
import threading
import random
import math
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from krimajlis_engine import KrimajlisEngine, NODE_DEFAULTS, REGIME_DEFAULTS, REGIME_LABELS

app = Flask(__name__)
CORS(app)

engine = KrimajlisEngine()
rng = random.Random(int(time.time()))

state = {
    "regime": dict(REGIME_DEFAULTS),
    "primary_nodes": {},
    "alpha_feed": [],
    "ticker_tape": {},
    "last_regime_update": 0,
    "last_node_update": 0,
    "last_alpha_update": 0,
}

TICKER_MAP = {
    "SPX": "^GSPC",
    "NDX": "^NDX",
    "DAX": "^GDAXI",
    "NIFTY": "^NSEI",
    "WTI": "CL=F",
    "Gold": "GC=F",
    "DXY": "DX-Y.NYB",
    "VIX": "^VIX",
    "HYG": "HYG",
    "BTC": "BTC-USD",
    "USDINR": "USDINR=X",
}

TICKER_FALLBACKS = {
    "SPX": 5200.0,
    "NDX": 18500.0,
    "DAX": 18200.0,
    "NIFTY": 22500.0,
    "WTI": 78.5,
    "Gold": 2340.0,
    "DXY": 104.5,
    "VIX": 18.5,
    "HYG": 79.2,
    "BTC": 68500.0,
    "USDINR": 83.2,
}

NODE_TICKER_MAP = {
    "DXY": "DX-Y.NYB",
    "Gold": "GC=F",
    "WTI": "CL=F",
    "VIX": "^VIX",
    "SPX": "^GSPC",
    "NIFTY": "^NSEI",
}


def safe_fetch_price(ticker_symbol, fallback):
    if not YFINANCE_AVAILABLE:
        return fallback
    try:
        t = yf.Ticker(ticker_symbol)
        hist = t.history(period="2d", interval="1d")
        if hist is not None and not hist.empty and len(hist) >= 1:
            return float(hist["Close"].iloc[-1])
        return fallback
    except Exception:
        return fallback


def refresh_primary_nodes():
    nodes = {}
    for node_id, yf_ticker in NODE_TICKER_MAP.items():
        fallback = NODE_DEFAULTS[node_id]["base"]
        price = safe_fetch_price(yf_ticker, fallback)
        engine.update_node(node_id, price)
        metrics = engine.get_node_metrics(node_id)
        nodes[node_id] = metrics

    for node_id in NODE_DEFAULTS:
        if node_id not in NODE_TICKER_MAP:
            engine.drift_simulated_nodes()
            metrics = engine.get_node_metrics(node_id)
            nodes[node_id] = metrics

    state["primary_nodes"] = nodes
    state["last_node_update"] = time.time()


def refresh_ticker_tape():
    tape = {}
    for label, yf_ticker in TICKER_MAP.items():
        fallback = TICKER_FALLBACKS.get(label, 100.0)
        price = safe_fetch_price(yf_ticker, fallback)
        prev = state["ticker_tape"].get(label, {}).get("price", price * (1 + rng.gauss(0, 0.003)))
        pct = ((price - prev) / abs(prev) * 100) if prev != 0 else 0.0
        tape[label] = {
            "label": label,
            "price": round(price, 4),
            "pct_change": round(pct, 4),
        }
    state["ticker_tape"] = tape


def drift_regime():
    for dim, current in state["regime"].items():
        score = current["score"]
        drift = rng.gauss(0, 2.5)
        mean_reversion = (50 - score) * 0.03
        new_score = max(5, min(95, score + drift + mean_reversion))

        labels = REGIME_LABELS[dim]
        idx = int((new_score / 100) * (len(labels) - 1))
        idx = max(0, min(len(labels) - 1, idx))

        if new_score > score + 1:
            direction = "up"
        elif new_score < score - 1:
            direction = "down"
        else:
            direction = "neutral"

        state["regime"][dim] = {
            "label": labels[idx],
            "score": round(new_score, 1),
            "direction": direction,
        }
    state["last_regime_update"] = time.time()


def regenerate_alpha_feed():
    signals = engine.generate_signals(state["regime"])
    state["alpha_feed"] = signals
    state["last_alpha_update"] = time.time()


def node_refresh_thread():
    time.sleep(2)
    refresh_primary_nodes()
    try:
        refresh_ticker_tape()
    except Exception:
        pass
    while True:
        time.sleep(30)
        try:
            refresh_primary_nodes()
        except Exception:
            pass
        try:
            refresh_ticker_tape()
        except Exception:
            pass


def alpha_thread():
    time.sleep(3)
    regenerate_alpha_feed()
    while True:
        time.sleep(15)
        try:
            regenerate_alpha_feed()
        except Exception:
            pass


def regime_thread():
    time.sleep(1)
    drift_regime()
    while True:
        time.sleep(60)
        try:
            drift_regime()
        except Exception:
            pass


@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": time.time()})


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/regime")
def get_regime():
    return jsonify(state["regime"])


@app.route("/api/primary-nodes")
def get_primary_nodes():
    nodes_list = list(state["primary_nodes"].values())
    if not nodes_list:
        nodes_list = [engine.get_node_metrics(nid) for nid in NODE_DEFAULTS]
    return jsonify(nodes_list)


@app.route("/api/alpha-feed")
def get_alpha_feed():
    feed = state["alpha_feed"]
    if not feed:
        feed = engine.generate_signals(state["regime"])
    return jsonify(feed)


@app.route("/api/causal-chain/<signal_id>")
def get_causal_chain(signal_id):
    chain = engine.get_full_causal_chain(signal_id)
    if chain is None:
        return jsonify({"error": "Signal not found"}), 404
    return jsonify(chain)


@app.route("/api/layers")
def get_layers():
    layers = engine.get_layer_metrics()
    return jsonify(layers)


@app.route("/api/ticker-tape")
def get_ticker_tape():
    tape = state["ticker_tape"]
    if not tape:
        tape = {
            k: {"label": k, "price": TICKER_FALLBACKS.get(k, 100.0), "pct_change": 0.0}
            for k in TICKER_MAP
        }
    return jsonify(list(tape.values()))


@app.route("/api/bridge/veritas", methods=["POST"])
def bridge_veritas():
    payload = request.get_json(silent=True) or {}
    top_signals = state["alpha_feed"][:3] if state["alpha_feed"] else []
    return jsonify({
        "destination": "VERITAS",
        "port": 5000,
        "status": "UPSTREAM_ALERT_QUEUED",
        "timestamp": time.time(),
        "payload_received": payload,
        "upstream_alert": {
            "source": "KRIMAJLIS",
            "alert_type": "ALPHA_SIGNAL_BATCH",
            "signal_count": len(top_signals),
            "top_signals": [
                {
                    "signal_id": s["signal_id"],
                    "ticker": s["ticker"],
                    "direction": s["direction"],
                    "conviction": s["conviction"],
                }
                for s in top_signals
            ],
            "regime_snapshot": state["regime"],
        },
    })


@app.route("/api/bridge/garuda", methods=["POST"])
def bridge_garuda():
    payload = request.get_json(silent=True) or {}
    top_signals = state["alpha_feed"][:3] if state["alpha_feed"] else []
    return jsonify({
        "destination": "GARUDA",
        "port": 8000,
        "status": "UPSTREAM_ALERT_QUEUED",
        "timestamp": time.time(),
        "payload_received": payload,
        "upstream_alert": {
            "source": "KRIMAJLIS",
            "alert_type": "ALPHA_SIGNAL_BATCH",
            "signal_count": len(top_signals),
            "top_signals": [
                {
                    "signal_id": s["signal_id"],
                    "ticker": s["ticker"],
                    "direction": s["direction"],
                    "conviction": s["conviction"],
                }
                for s in top_signals
            ],
            "regime_snapshot": state["regime"],
        },
    })


if __name__ == "__main__":
    t1 = threading.Thread(target=node_refresh_thread, daemon=True)
    t2 = threading.Thread(target=alpha_thread, daemon=True)
    t3 = threading.Thread(target=regime_thread, daemon=True)
    t1.start()
    t2.start()
    t3.start()

    port = int(os.environ.get("PORT", 9000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
