"""
APEX Dashboard Server — Chart Feature
Philip AJ Sogah | philipajsogah.io
========================================
Adds two things to APEX:

1. Web dashboard at http://localhost:5001
   - Candlestick charts with ghost pattern markers
   - Volume + OBV overlay
   - Multi-timeframe view (daily/weekly/monthly)
   - Live P&L chart
   - Signal strength bars for all 5 strategies

2. Terminal ASCII charts (no browser needed)
   - Price chart with trend line
   - Signal bars
   - Volume histogram

Run alongside apex_main.py:
  python3 apex_dashboard_server.py
  Then open http://localhost:5001
"""

import os
import sys
import json
import time
import math
import threading
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from typing import Optional

# ── TERMINAL CHARTS ───────────────────────────────────────────

def terminal_price_chart(bars: list, symbol: str, width: int = 60, height: int = 16):
    """Draw ASCII candlestick chart in terminal."""
    if not bars:
        print(f"  No data for {symbol}")
        return

    display = bars[-width//2:]
    closes  = [b["c"] for b in display]
    highs   = [b["h"] for b in display]
    lows    = [b["l"] for b in display]

    mn = min(lows) * 0.999
    mx = max(highs) * 1.001

    def sy(v): return int((1 - (v - mn) / (mx - mn)) * (height - 1))

    # Build grid
    grid = [[' '] * len(display) for _ in range(height)]

    for i, b in enumerate(display):
        hi = sy(b["h"])
        lo = sy(b["l"])
        op = sy(b["o"])
        cl = sy(b["c"])
        is_up = b["c"] >= b["o"]

        for y in range(hi, lo + 1):
            if min(op, cl) <= y <= max(op, cl):
                grid[y][i] = '█' if is_up else '░'
            else:
                grid[y][i] = '│'

    # Price labels
    rows = []
    for y, row in enumerate(grid):
        price = mx - (y / (height - 1)) * (mx - mn)
        label = f"${price:>8.2f} │"
        rows.append(label + ''.join(row))

    # Print
    print(f"\n  {'─'*10} {symbol} {'─'*(width-len(symbol)-12)}")
    up_color   = '\033[92m'
    dn_color   = '\033[91m'
    reset      = '\033[0m'
    for row in rows:
        colored = row.replace('█', f'{up_color}█{reset}').replace('░', f'{dn_color}░{reset}')
        print(f"  {colored}")

    # Trend
    trend = (closes[-1] - closes[0]) / closes[0] * 100
    trend_str = f"{'▲' if trend >= 0 else '▼'} {trend:+.2f}%"
    color = up_color if trend >= 0 else dn_color
    print(f"  {'─'*10} Last: ${closes[-1]:.2f} | 30D Trend: {color}{trend_str}{reset}")


def terminal_signal_bars(signals: dict, width: int = 50):
    """Draw signal strength bars in terminal."""
    if not signals:
        print("  No signals available")
        return

    print(f"\n  {'─'*65}")
    print(f"  {'SYMBOL':<10} {'ACTION':<7} {'SCORE':>7} {'CONFIDENCE':>11}  SIGNAL BAR")
    print(f"  {'─'*65}")

    up   = '\033[92m'
    dn   = '\033[91m'
    amb  = '\033[93m'
    rst  = '\033[0m'
    dim  = '\033[90m'

    for sym, sig in sorted(signals.items(),
                           key=lambda x: abs(x[1].get("score", 0)),
                           reverse=True):
        score  = sig.get("score", 0)
        action = sig.get("action", "HOLD")
        conf   = sig.get("confidence", 0)
        price  = sig.get("price", 0)

        bar_len = int(abs(score) / 100 * 30)
        bar_len = min(30, bar_len)

        if action == "BUY":
            color  = up
            icon   = "📈"
            bar    = f"{up}{'█' * bar_len}{'░' * (30 - bar_len)}{rst}"
        elif action == "SELL":
            color  = dn
            icon   = "📉"
            bar    = f"{dn}{'█' * bar_len}{'░' * (30 - bar_len)}{rst}"
        else:
            color  = dim
            icon   = "⏸️ "
            bar    = f"{dim}{'─' * 30}{rst}"

        ghost = " 👻" if sig.get("ghost") else ""
        manip = " 🔍" if sig.get("manipulation") else ""

        print(f"  {icon} {sym:<8} {color}{action:<7}{rst} "
              f"{color}{score:>+7.1f}{rst} "
              f"{conf:>9.0f}%  {bar}{ghost}{manip}")

    print(f"  {'─'*65}")


def terminal_volume_chart(bars: list, symbol: str, width: int = 50):
    """Draw ASCII volume histogram with OBV."""
    if not bars:
        return

    display = bars[-width:]
    volumes = [b["v"] for b in display]
    closes  = [b["c"] for b in display]
    max_vol = max(volumes) or 1
    height  = 8

    # OBV
    obv = 0
    obv_series = [0]
    for i in range(1, len(display)):
        if closes[i] > closes[i-1]:
            obv += volumes[i]
        elif closes[i] < closes[i-1]:
            obv -= volumes[i]
        obv_series.append(obv)

    up  = '\033[92m'
    dn  = '\033[91m'
    rst = '\033[0m'
    obv_trend = up if obv_series[-1] > 0 else dn
    obv_label = "ACCUMULATING" if obv_series[-1] > 0 else "DISTRIBUTING"

    print(f"\n  Volume · OBV ({obv_trend}{obv_label}{rst})")
    for h in range(height, 0, -1):
        row = ""
        for i, (vol, b) in enumerate(zip(volumes, display)):
            bar_h = int(vol / max_vol * height)
            if bar_h >= h:
                color = up if b["c"] >= b["o"] else dn
                row += f"{color}█{rst}"
            else:
                row += " "
        avg_vol = sum(volumes) / len(volumes)
        print(f"  {'':>8} │{row}")
    print(f"  {'':>8} └{'─'*len(display)}")
    print(f"  Avg Vol: {sum(volumes)/len(volumes)/1e6:.1f}M | "
          f"Last: {volumes[-1]/1e6:.1f}M | "
          f"OBV: {obv_series[-1]/1e6:+.1f}M")


def terminal_mtf_summary(bars: list, symbol: str):
    """Print multi-timeframe trend summary."""
    if not bars:
        return

    closes = [b["c"] for b in bars]
    up  = '\033[92m'
    dn  = '\033[91m'
    rst = '\033[0m'

    tfs = [
        ("Daily  (5D)",  closes[-5:]  if len(closes) >= 5  else closes),
        ("Weekly (20D)", closes[-20:] if len(closes) >= 20 else closes),
        ("Monthly(60D)", closes[-60:] if len(closes) >= 60 else closes),
    ]

    print(f"\n  Multi-Timeframe Analysis — {symbol}")
    print(f"  {'─'*40}")
    all_bullish = True
    all_bearish = True

    for label, data in tfs:
        if len(data) < 2:
            continue
        trend = (data[-1] - data[0]) / data[0] * 100
        ma    = sum(data) / len(data)
        above = data[-1] > ma
        color = up if trend >= 0 else dn
        icon  = "▲" if trend >= 0 else "▼"
        pos   = "ABOVE MA" if above else "BELOW MA"
        print(f"  {label}: {color}{icon} {trend:+.2f}%{rst} | {pos}")
        if trend < 0: all_bullish = False
        if trend > 0: all_bearish = False

    if all_bullish:
        print(f"  {up}★ FULL BULLISH CONFLUENCE — all timeframes aligned UP{rst}")
    elif all_bearish:
        print(f"  {dn}★ FULL BEARISH CONFLUENCE — all timeframes aligned DOWN{rst}")
    else:
        print(f"  \033[93m⚡ MIXED — timeframes not fully aligned{rst}")


# ── FLASK DASHBOARD SERVER ────────────────────────────────────

def start_dashboard_server(signal_store: dict, bar_store: dict,
                            portfolio_store: dict, feed,
                            port: int = 5001):
    """
    Start the web dashboard server on port 5001.
    Serves the HTML dashboard + API endpoints for chart data.
    """
    try:
        from flask import Flask, jsonify, request, Response
        from flask_cors import CORS
    except ImportError:
        print("  Dashboard requires flask: pip3 install flask flask-cors")
        return

    app = Flask(__name__)
    CORS(app)

    @app.route("/")
    def index():
        html_path = os.path.join(os.path.dirname(__file__), "apex_dashboard.html")
        if os.path.exists(html_path):
            with open(html_path) as f:
                return Response(f.read(), mimetype="text/html")
        return jsonify({"status": "APEX Dashboard", "note": "Place apex_dashboard.html here"})

    @app.route("/api/apex/signals")
    def get_signals():
        formatted = {}
        for sym, sig in signal_store.items():
            formatted[sym] = {
                "action":     sig.action,
                "score":      sig.composite_score,
                "confidence": sig.confidence,
                "horizon":    sig.horizon,
                "price":      sig.entry_price,
                "target":     sig.target_price,
                "stop":       sig.stop_price,
                "rr":         sig.risk_reward,
                "ghost":      sig.ghost_detected,
                "manipulation": sig.manipulation,
                "components": [
                    {"name": c.name, "score": c.score,
                     "reason": c.reason, "confidence": c.confidence}
                    for c in sig.components
                ],
            }
        return jsonify({"signals": formatted, "next_scan": 300,
                        "timestamp": datetime.now(timezone.utc).isoformat()})

    @app.route("/api/apex/bars/<symbol>")
    def get_bars(symbol):
        sym = urllib.parse.unquote(symbol)
        bars = bar_store.get(sym, [])
        if not bars and feed:
            try:
                raw  = feed.bars(sym, "1D", 60)
                bars = [{"t":b.timestamp,"o":b.open,"h":b.high,
                          "l":b.low,"c":b.close,"v":b.volume} for b in raw]
                bar_store[sym] = bars
            except: pass
        return jsonify({"symbol": sym, "bars": bars})

    @app.route("/api/apex/portfolio")
    def get_portfolio():
        return jsonify(portfolio_store)

    @app.route("/api/apex/command", methods=["POST"])
    def command():
        data = request.json or {}
        cmd  = data.get("command","").strip().lower()
        if cmd.startswith("yes "):
            sym = cmd.split()[1].upper()
            return jsonify({"message": f"✅ Approve {sym} — use terminal to confirm"})
        elif cmd.startswith("no "):
            sym = cmd.split()[1].upper()
            return jsonify({"message": f"❌ {sym} rejected"})
        return jsonify({"message": f"Command received: {cmd}"})

    print(f"\n  📊 Dashboard starting at http://localhost:{port}")
    print(f"  📊 On your phone: http://YOUR_LAPTOP_IP:{port}")

    t = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False),
        daemon=True
    )
    t.start()
    return t


# ── TERMINAL CHART DISPLAY ────────────────────────────────────

def show_terminal_charts(signals: dict, bars_cache: dict, symbol: str = "AAPL"):
    """Display all terminal charts for a symbol."""
    bars = bars_cache.get(symbol, [])
    if bars:
        terminal_price_chart(bars, symbol)
        terminal_volume_chart(bars, symbol)
        terminal_mtf_summary(bars, symbol)

    print()
    terminal_signal_bars(signals)


if __name__ == "__main__":
    # Test with demo data
    import random

    # Generate demo bars
    p = 252.0
    bars = []
    for i in range(60):
        chg = (random.random() - 0.48) * p * 0.02
        o, c = p, p + chg
        h = max(o, c) * (1 + random.random() * 0.008)
        l = min(o, c) * (1 - random.random() * 0.008)
        bars.append({"o":round(o,2),"h":round(h,2),"l":round(l,2),
                     "c":round(c,2),"v":int(1e6+random.random()*5e6),"t":i})
        p = c

    demo_signals = {
        "AAPL": {"action":"BUY",  "score":68.4,"confidence":78,"ghost":True,
                 "manipulation":False,"horizon":"weeks"},
        "NVDA": {"action":"SELL", "score":-45.2,"confidence":62,"ghost":False,
                 "manipulation":True,"horizon":"days"},
        "GLD":  {"action":"BUY",  "score":52.1,"confidence":71,"ghost":True,
                 "manipulation":False,"horizon":"months"},
        "TSLA": {"action":"HOLD", "score":8.3,"confidence":35,"ghost":False,
                 "manipulation":False,"horizon":"days"},
        "SPY":  {"action":"WATCH","score":22.5,"confidence":45,"ghost":False,
                 "manipulation":False,"horizon":"weeks"},
    }

    show_terminal_charts(demo_signals, {"AAPL": bars}, "AAPL")
    print("\n  Dashboard server test — run with apex_main.py for live data")
