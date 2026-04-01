from typing import Optional
"""
APEX Trading System — Main Runner
Philip AJ Sogah | philipajsogah.io
=====================================
The most sophisticated retail trading system you can build.

What makes APEX different from quant firms:
  ✅ Ghost pattern detection (institutional footprints)
  ✅ Multi-timeframe confluence (daily + weekly + monthly)
  ✅ Options flow analysis (whale activity detection)
  ✅ News sentiment scoring
  ✅ Forensics edge (manipulation → mean reversion) — YOUR UNIQUE EDGE
  ✅ Covers stocks, gold, oil, crypto, forex
  ✅ Email alerts to philipaxl7@gmail.com on every signal
  ✅ Human approval required before execution
  ✅ Hard risk limits that cannot be overridden

Setup:
  export ALPACA_API_KEY="PKxxxxxxxxxxxxxxxx"
  export ALPACA_SECRET="your_secret"
  export FRED_API_KEY="your_fred_key"
  export GMAIL_ADDRESS="philipaxl7@gmail.com"
  export GMAIL_APP_PASSWORD="your_app_password"
  export NEWS_API_KEY="your_newsapi_key"     # optional but recommended
  export ALPACA_LIVE="true"                  # for real money (default: paper)

  python3 main.py

Commands during runtime:
  yes SYMBOL  — approve pending trade for SYMBOL
  no SYMBOL   — reject pending trade
  close SYMBOL — manually close a position
  status      — show portfolio metrics
  signals     — show latest signals
  quit        — graceful shutdown
"""

import os
import sys
import time
import select
import threading
from datetime import datetime, timezone, timedelta

from apex_market_feed   import MarketFeed, UNIVERSE
from apex_signal_engine import SignalEngine, TradeSignal
from apex_risk_executor import RiskManager, AlpacaExecutor
from apex_email_alerts  import ApexAlerter
from apex_dashboard_server import start_dashboard_server, show_terminal_charts


# ── CONFIG ────────────────────────────────────────────────────
SCAN_INTERVAL     = 300    # 5 minutes between full scans
APPROVAL_TIMEOUT  = 1800   # 30 minutes before pending trade expires
MIN_SCORE         = 35     # minimum |score| to generate alert
DAILY_BRIEFING_HR = 9      # 9am ET morning briefing
WEEKLY_REPORT_DAY = 4      # Friday


# ── PENDING APPROVAL QUEUE ────────────────────────────────────

class ApprovalQueue:
    def __init__(self):
        self._queue: dict[str, dict] = {}

    def add(self, signal: TradeSignal, qty: float, cost: float):
        self._queue[signal.symbol] = {
            "signal": signal, "qty": qty, "cost": cost,
            "added": time.time(),
        }
        print(f"\n  ⏳ {signal.strength} {signal.action} {signal.symbol} "
              f"pending — type 'yes {signal.symbol}' to approve")

    def approve(self, symbol: str) -> Optional[dict]:
        return self._queue.pop(symbol.upper(), None)

    def reject(self, symbol: str):
        self._queue.pop(symbol.upper(), None)
        print(f"  Trade {symbol} rejected")

    def expire(self):
        now = time.time()
        for sym in [s for s, v in self._queue.items()
                    if now - v["added"] > APPROVAL_TIMEOUT]:
            item = self._queue.pop(sym)
            print(f"  ⏰ {sym} trade expired after {APPROVAL_TIMEOUT//60}min")

    def pending(self) -> dict:
        return self._queue

    def list(self):
        if not self._queue:
            print("  No pending approvals")
        for sym, item in self._queue.items():
            s   = item["signal"]
            age = int(time.time() - item["added"])
            print(f"  [{sym}] {s.strength} {s.action} "
                  f"score={s.composite_score:+.0f} "
                  f"${s.entry_price:.2f}→${s.target_price:.2f} "
                  f"[{age//60}m{age%60}s waiting]")


# ── MAIN ──────────────────────────────────────────────────────

def run():
    print("""
╔══════════════════════════════════════════════════════════════╗
║   APEX TRADING SYSTEM — Philip AJ Sogah                      ║
║   philipajsogah.io  |  github.com/axlAJ                      ║
╠══════════════════════════════════════════════════════════════╣
║   Stocks · Gold · Oil · Crypto · Forex                        ║
║   Ghost Patterns · MTF · Options Flow · Sentiment · Forensics ║
╚══════════════════════════════════════════════════════════════╝
    """)

    key    = os.getenv("ALPACA_API_KEY")
    secret = os.getenv("ALPACA_SECRET")
    fred   = os.getenv("FRED_API_KEY")
    news   = os.getenv("NEWS_API_KEY")

    if not key or not secret:
        raise SystemExit("Set ALPACA_API_KEY and ALPACA_SECRET")

    # ── Init ──────────────────────────────────────────────────
    print("  Initialising components...")
    feed     = MarketFeed(key, secret, fred)
    engine   = SignalEngine(news)
    executor = AlpacaExecutor(key, secret)
    equity   = executor.equity()
    risk_mgr = RiskManager(equity)
    alerter  = ApexAlerter()
    queue    = ApprovalQueue()

    # ── Shared data stores for dashboard ──────────────────────
    signal_store    = {}   # latest signals for dashboard
    bar_store       = {}   # cached bars for charts
    portfolio_store = {"equity":100000,"pnl":0,"win_rate":0,"open":0,"trades":0}

    # ── Start web dashboard on port 5001 ──────────────────────
    start_dashboard_server(signal_store, bar_store, portfolio_store, feed, port=5001)
    print(f"  ✅ Chart dashboard → http://localhost:5001")

    print(f"  ✅ Market feed connected ({len(UNIVERSE)} symbols)")
    print(f"  ✅ Signal engine ready (5 edge strategies)")
    print(f"  ✅ Risk manager loaded ({len(risk_mgr.positions)} open positions)")
    print(f"  ✅ Email alerts → philipaxl7@gmail.com")
    print(f"  Account equity: ${equity:,.2f}")
    print(f"\n  Commands: yes SYMBOL | no SYMBOL | close SYMBOL | status | signals | charts SYMBOL | quit")
    print("─" * 65)

    last_scan       = 0
    last_briefing   = 0
    last_week       = 0
    latest_signals  = []

    def process(cmd: str):
        cmd = cmd.strip()
        if not cmd:
            queue.list()
            return

        parts  = cmd.split()
        action = parts[0].lower()
        symbol = parts[1].upper() if len(parts) > 1 else ""

        if action == "yes" and symbol:
            item = queue.approve(symbol)
            if not item:
                print(f"  No pending trade for {symbol}")
                return
            sig  = item["signal"]
            qty  = item["qty"]
            cost = item["cost"]
            print(f"\n  ✅ Approved: {sig.strength} {sig.action} {symbol}")
            result = executor.execute(sig, qty, risk_mgr)
            if result.get("success"):
                alerter.trade_alert(sig, risk_mgr.metrics(equity))
                print(f"  ✅ Executed: order {result.get('order_id')}")
            else:
                print(f"  ❌ Execution failed: {result.get('error')}")

        elif action == "no" and symbol:
            queue.reject(symbol)

        elif action == "close" and symbol:
            if symbol not in risk_mgr.positions:
                print(f"  No open position in {symbol}")
                return
            # Get current price
            quotes = feed.quotes()
            price  = quotes.get(symbol, {})
            price  = price.price if hasattr(price, 'price') else 0
            if price == 0:
                print(f"  Cannot get price for {symbol}")
                return
            pos = risk_mgr.close(symbol, price, "manual")
            if pos:
                alerter.position_closed(symbol, pos.side, pos.entry_price,
                                        price, pos.qty, pos.pnl, pos.pnl_pct, "manual")
                print(f"  Position closed: {symbol} P&L={pos.pnl_pct:+.2f}%")

        elif action == "status":
            m = risk_mgr.metrics(equity)
            print(f"\n  Portfolio Metrics:")
            for k, v in m.items():
                print(f"    {k:<22} {v}")

        elif action == "signals":
            if not latest_signals:
                print("  No signals yet — waiting for next scan")
                return
            sigs_dict = {s.symbol:{"action":s.action,"score":s.composite_score,
                "confidence":s.confidence,"ghost":s.ghost_detected,
                "manipulation":s.manipulation,"horizon":s.horizon,
                "price":s.entry_price} for s in latest_signals}
            show_terminal_charts(sigs_dict, bar_store,
                                 parts[1].upper() if len(parts)>1 else "AAPL")

        elif action == "pending":
            queue.list()

        elif action == "charts":
            sym = parts[1].upper() if len(parts) > 1 else "AAPL"
            sigs_dict = {s.symbol:{"action":s.action,"score":s.composite_score,
                "confidence":s.confidence,"ghost":s.ghost_detected,
                "manipulation":s.manipulation,"horizon":s.horizon,
                "price":s.entry_price} for s in latest_signals}
            show_terminal_charts(sigs_dict, bar_store, sym)

        elif action == "quit":
            print("\n  Shutting down APEX...")
            m = risk_mgr.metrics(equity)
            alerter.weekly_report(m, [vars(p) for p in risk_mgr.closed[-20:]])
            print(f"  Final P&L: ${m['total_pnl']:+.2f} | Win rate: {m['win_rate']:.1f}%")
            sys.exit(0)

        else:
            print(f"  Unknown: {cmd}")

    # ── Main loop ─────────────────────────────────────────────
    while True:
        # Non-blocking input
        if select.select([sys.stdin], [], [], 0)[0]:
            process(sys.stdin.readline())
            continue

        now = time.time()
        queue.expire()

        # Update prices and check stops/targets
        if risk_mgr.positions:
            try:
                quotes = feed.quotes()
                prices = {s: q.price for s, q in quotes.items() if q.price > 0}
                events = risk_mgr.update_prices(prices)
                for sym, reason in events:
                    pos = risk_mgr.closed[-1] if risk_mgr.closed else None
                    if pos and pos.symbol == sym:
                        alerter.position_closed(sym, pos.side, pos.entry_price,
                                                pos.exit_price, pos.qty,
                                                pos.pnl, pos.pnl_pct, reason)
                        icon = "✅" if pos.pnl >= 0 else "🛑"
                        print(f"\n  {icon} {reason.upper()} {sym} "
                              f"P&L={pos.pnl_pct:+.2f}% (${pos.pnl:+.2f})")
            except Exception as e:
                print(f"  Price update error: {e}")

        # Full market scan
        if now - last_scan >= SCAN_INTERVAL:
            last_scan = now
            ts = datetime.now().strftime("%I:%M %p")
            print(f"\n[{ts}] Scanning {len(UNIVERSE)} symbols across all markets...")

            if not risk_mgr.metrics(equity)["daily_limit_ok"]:
                print(f"  ⚠️  Daily loss limit hit — no new trades today")
                time.sleep(30)
                continue

            try:
                # Fetch all data
                quotes  = feed.quotes()
                macro   = feed.macro()
                mtf_data = {}
                for sym in list(UNIVERSE.keys())[:8]:   # limit to avoid rate limits
                    try:
                        mtf_data[sym] = feed.mtf(sym)
                        time.sleep(0.2)
                    except:
                        pass

                # Run signal engine
                latest_signals = engine.scan_all(quotes, mtf_data, macro)

                # Update dashboard stores
                for sig in latest_signals:
                    signal_store[sig.symbol] = sig
                for sym, mtf in mtf_data.items():
                    daily = mtf.get("1D",[])
                    if daily:
                        bar_store[sym] = [{"o":b.open,"h":b.high,"l":b.low,
                                           "c":b.close,"v":b.volume,"t":b.timestamp}
                                          for b in daily]
                m2 = risk_mgr.metrics(equity)
                portfolio_store.update({"equity":equity,"pnl":m2["total_pnl"],
                    "win_rate":m2["win_rate"],"open":m2["open_positions"],
                    "trades":m2["total_trades"]})

                # Print results table
                print(f"\n  {'SYM':<10} {'ACT':<5} {'SCORE':>7} {'CONF':>6} "
                      f"{'HORIZON':<8} {'PRICE':>10} {'R/R':>5}  FLAGS")
                print("  " + "─" * 70)
                for s in latest_signals[:10]:
                    icon    = "📈" if s.action=="BUY" else "📉" if s.action=="SELL" else "⏸️ "
                    flags   = ""
                    if s.ghost_detected: flags += "👻"
                    if s.manipulation:   flags += "🔍"
                    print(f"  {icon} {s.symbol:<8} {s.action:<5} "
                          f"{s.composite_score:>+7.1f} {s.confidence:>5.0f}% "
                          f"{s.horizon:<8} ${s.entry_price:>9.4f} "
                          f"{s.risk_reward:>4.1f}x  {flags}")

                # Generate alerts for actionable signals
                for signal in latest_signals:
                    if signal.action not in ("BUY","SELL"):
                        continue
                    if abs(signal.composite_score) < MIN_SCORE:
                        continue
                    if signal.symbol in risk_mgr.positions:
                        continue
                    if signal.symbol in queue.pending():
                        continue

                    ok, reason, size, qty = risk_mgr.check(signal, equity)
                    if not ok:
                        print(f"  ⚠️  {signal.symbol} blocked: {reason}")
                        continue

                    print(f"\n  🔔 SIGNAL: {signal.strength} {signal.action} "
                          f"{signal.symbol} score={signal.composite_score:+.0f} "
                          f"→ emailing philipaxl7@gmail.com")

                    alerter.trade_alert(signal, risk_mgr.metrics(equity))
                    queue.add(signal, qty, size)

                m = risk_mgr.metrics(equity)
                print(f"\n  Portfolio: ${equity:,.2f} equity | "
                      f"P&L: ${m['total_pnl']:+.2f} | "
                      f"Positions: {m['open_positions']}/{risk_mgr.MAX_POSITIONS} | "
                      f"Win: {m['win_rate']:.1f}%")

            except Exception as e:
                print(f"  Scan error: {e}")
                import traceback; traceback.print_exc()

        # Morning briefing
        hr = datetime.now().hour
        if hr == DAILY_BRIEFING_HR and now - last_briefing > 3600:
            last_briefing = now
            try:
                alerter.daily_briefing(
                    latest_signals,
                    feed.macro(),
                    risk_mgr.metrics(equity),
                )
                print(f"  ☀️  Morning briefing sent to philipaxl7@gmail.com")
            except Exception as e:
                print(f"  Briefing error: {e}")

        # Weekly report (Friday)
        if datetime.now().weekday() == WEEKLY_REPORT_DAY and now - last_week > 86400:
            last_week = now
            risk_mgr.weekly_report if hasattr(risk_mgr,'weekly_report') else None
            try:
                alerter.weekly_report(
                    risk_mgr.metrics(equity),
                    [vars(p) for p in risk_mgr.closed[-20:]],
                )
            except Exception as e:
                print(f"  Weekly report error: {e}")

        # Pending reminder
        if queue.pending():
            count = len(queue.pending())
            syms  = list(queue.pending().keys())
            print(f"  ⏳ {count} pending: {', '.join(syms)} — type 'yes SYMBOL'", end="\r")

        time.sleep(1)


if __name__ == "__main__":
    run()
