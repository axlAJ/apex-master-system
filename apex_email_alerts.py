"""
Email Alert System — APEX Trading System
Philip AJ Sogah | philipajsogah.io
==========================================
Sends professional trade alerts to philipaxl7@gmail.com

Alert types:
  - Trade opportunity    — BUY/SELL signal with full analysis
  - Position update      — stop/target hit notification
  - Daily briefing       — 6am market overview
  - Weekly report        — performance summary
  - Risk alert           — circuit breaker, daily loss limit

Setup (Gmail):
  1. Go to myaccount.google.com → Security → App Passwords
  2. Generate app password for "Mail"
  3. export GMAIL_ADDRESS="philipaxl7@gmail.com"
  4. export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
"""

import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from apex_signal_engine import TradeSignal


TO_EMAIL = "philipaxl7@gmail.com"


class ApexAlerter:

    def __init__(self):
        self.gmail   = os.getenv("GMAIL_ADDRESS",       TO_EMAIL)
        self.pw      = os.getenv("GMAIL_APP_PASSWORD",  "")
        self.to      = TO_EMAIL

    def _send(self, subject: str, plain: str, html: str = None) -> bool:
        if not self.pw:
            # Print to terminal if email not configured
            print(f"\n{'='*60}")
            print(f"  📧 EMAIL ALERT (configure GMAIL_APP_PASSWORD to send)")
            print(f"  TO: {self.to}")
            print(f"  SUBJECT: {subject}")
            print(f"  BODY:\n{plain}")
            print(f"{'='*60}\n")
            return True

        try:
            msg            = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = self.gmail
            msg["To"]      = self.to
            msg.attach(MIMEText(plain, "plain"))
            if html:
                msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP("smtp.gmail.com", 587) as s:
                s.starttls()
                s.login(self.gmail, self.pw)
                s.sendmail(self.gmail, self.to, msg.as_string())
            print(f"  📧 Alert sent → {self.to}")
            return True
        except Exception as e:
            print(f"  ❌ Email failed: {e}")
            return False

    # ── TRADE OPPORTUNITY ALERT ────────────────────────────────

    def trade_alert(self, signal: TradeSignal, portfolio_metrics: dict = None) -> bool:
        """Send a trade opportunity alert."""
        icon   = "📈" if signal.action == "BUY" else "📉" if signal.action == "SELL" else "👁️"
        flags  = []
        if signal.ghost_detected: flags.append("👻 GHOST PATTERN")
        if signal.manipulation:   flags.append("🔍 MANIPULATION DETECTED")

        subject = (f"{icon} APEX ALERT: {signal.strength} {signal.action} "
                   f"{signal.symbol} @ ${signal.entry_price:.4f} "
                   f"[{signal.horizon.upper()}]")

        pnl_line = ""
        if portfolio_metrics:
            pnl_line = (f"\nPORTFOLIO STATUS\n"
                        f"{'─'*50}\n"
                        f"Total P&L:     ${portfolio_metrics.get('total_pnl',0):+.2f}\n"
                        f"Win Rate:       {portfolio_metrics.get('win_rate',0):.1f}%\n"
                        f"Open Positions: {portfolio_metrics.get('open_positions',0)}\n")

        plain = f"""
APEX TRADING SYSTEM — TRADE ALERT
{'='*60}
Generated: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p ET')}
{'='*60}

{' | '.join(flags) if flags else ''}

SIGNAL SUMMARY
{'─'*50}
Symbol:         {signal.symbol}
Action:         {signal.strength} {signal.action}
Score:          {signal.composite_score:+.1f} / 100
Confidence:     {signal.confidence:.0f}%
Asset Class:    {signal.asset_class.upper()}
Time Horizon:   {signal.horizon.upper()} (~{signal.horizon_days} days to target)

TRADE LEVELS
{'─'*50}
Entry Price:    ${signal.entry_price:.4f}
Target Price:   ${signal.target_price:.4f}  ({((signal.target_price/signal.entry_price)-1)*100:+.2f}%)
Stop Loss:      ${signal.stop_price:.4f}   ({((signal.stop_price/signal.entry_price)-1)*100:+.2f}%)
Risk/Reward:    {signal.risk_reward:.1f}:1

SIGNAL BREAKDOWN
{'─'*50}
{chr(10).join(f'  [{c.name:<18}] score={c.score:+.0f:>5}  conf={c.confidence:.0f}%  {c.reason[:70]}' for c in signal.components)}

ANALYSIS
{'─'*50}
{signal.reasoning}
{pnl_line}
ACTION REQUIRED
{'─'*50}
{"✅ CONFIRM TRADE — reply YES to execute" if signal.action in ("BUY","SELL") else "👁️  MONITORING — no action needed yet"}

Risk Warning: Never risk more than you can afford to lose.
This system is for informational purposes. Always verify signals.

──────────────────────────────────────────────────────────
Philip AJ Sogah | APEX Trading System | philipajsogah.io
"""

        html = f"""
<html><body style="font-family:monospace;background:#000811;color:#a8d8ff;padding:20px">
<div style="max-width:600px;margin:0 auto">
  <h2 style="color:#00a8ff;letter-spacing:.1em">APEX TRADING SYSTEM</h2>
  <div style="background:#010f1e;border:1px solid #1e3050;padding:15px;margin:10px 0">
    <h3 style="color:{'#00e676' if signal.action=='BUY' else '#ff3b3b' if signal.action=='SELL' else '#ffd700'}">
      {icon} {signal.strength} {signal.action} — {signal.symbol}
    </h3>
    <table style="width:100%;border-collapse:collapse">
      <tr><td style="color:#4a6080;padding:4px">Score</td><td style="color:#fff">{signal.composite_score:+.1f}/100</td></tr>
      <tr><td style="color:#4a6080;padding:4px">Confidence</td><td style="color:#fff">{signal.confidence:.0f}%</td></tr>
      <tr><td style="color:#4a6080;padding:4px">Entry</td><td style="color:#fff">${signal.entry_price:.4f}</td></tr>
      <tr><td style="color:#4a6080;padding:4px">Target</td><td style="color:#00e676">${signal.target_price:.4f} ({((signal.target_price/signal.entry_price)-1)*100:+.2f}%)</td></tr>
      <tr><td style="color:#4a6080;padding:4px">Stop</td><td style="color:#ff3b3b">${signal.stop_price:.4f}</td></tr>
      <tr><td style="color:#4a6080;padding:4px">Horizon</td><td style="color:#fff">{signal.horizon.upper()} (~{signal.horizon_days} days)</td></tr>
      <tr><td style="color:#4a6080;padding:4px">R/R Ratio</td><td style="color:#fff">{signal.risk_reward:.1f}:1</td></tr>
    </table>
  </div>
  {'<div style="background:#1a0a00;border:1px solid #ff6600;padding:8px;color:#ff9944">⚡ ' + ' | '.join(flags) + '</div>' if flags else ''}
  <div style="background:#010f1e;border:1px solid #1e3050;padding:10px;margin:10px 0">
    <p style="color:#4a6080;font-size:11px">{signal.reasoning}</p>
  </div>
  <p style="color:#1e3050;font-size:10px">Philip AJ Sogah | APEX Trading System | philipajsogah.io</p>
</div></body></html>
"""
        return self._send(subject, plain, html)

    # ── POSITION CLOSED ALERT ──────────────────────────────────

    def position_closed(self, symbol: str, side: str, entry: float,
                         exit_price: float, qty: float,
                         pnl: float, pnl_pct: float, reason: str) -> bool:
        icon    = "✅" if pnl >= 0 else "🛑"
        subject = f"{icon} POSITION CLOSED: {symbol} | P&L: {pnl_pct:+.2f}% (${pnl:+.2f})"
        plain   = f"""
APEX TRADING SYSTEM — POSITION CLOSED
{'='*50}
{reason.upper().replace('_',' ')}

Symbol:      {symbol}
Side:        {side.upper()}
Entry:       ${entry:.4f}
Exit:        ${exit_price:.4f}
Quantity:    {qty:.4f}
P&L:         {pnl_pct:+.2f}% (${pnl:+.2f})
Reason:      {reason.replace('_',' ').title()}
Time:        {datetime.now().strftime('%I:%M %p ET')}

{'PROFIT TAKEN ✅ — great trade, Philip!' if pnl >= 0 else 'STOP LOSS HIT 🛑 — loss contained, capital protected.'}

──────────────────────────────────────────────────────────
Philip AJ Sogah | APEX Trading System | philipajsogah.io
"""
        return self._send(subject, plain)

    # ── DAILY BRIEFING ────────────────────────────────────────

    def daily_briefing(self, signals: list,
                        macro, metrics: dict,
                        quotes: dict = None) -> bool:
        now     = datetime.now()
        subject = f"☀️ APEX Daily Briefing — {now.strftime('%A, %B %d')} | {len([s for s in signals if s.action in ('BUY','SELL')])} active signals"

        top_signals = [s for s in signals if s.action in ("BUY","SELL")][:5]
        watch_list  = [s for s in signals if s.action == "WATCH"][:3]

        sig_lines = "\n".join(
            f"  {'📈' if s.action=='BUY' else '📉'} {s.symbol:<12} "
            f"{s.strength:<8} {s.action:<5} "
            f"score={s.composite_score:+.0f} "
            f"target=${s.target_price:.2f} "
            f"({((s.target_price/s.entry_price)-1)*100:+.2f}%) "
            f"[{s.horizon}]"
            for s in top_signals
        ) or "  No strong signals today — markets neutral"

        watch_lines = "\n".join(
            f"  👁️  {s.symbol:<12} score={s.composite_score:+.0f} — monitoring"
            for s in watch_list
        ) or "  No symbols on watch"

        plain = f"""
APEX TRADING SYSTEM — DAILY BRIEFING
{'='*60}
{now.strftime('%A, %B %d, %Y')} | Generated at {now.strftime('%I:%M %p ET')}
{'='*60}

MACRO ENVIRONMENT
{'─'*50}
Yield Curve:    {macro.curve_shape.upper()} (2Y={macro.yield_2y:.2f}% | 10Y={macro.yield_10y:.2f}%)
Spread:         {macro.yield_spread:+.2f}%
Fed Funds:      {macro.fed_funds:.2f}%
VIX:            {macro.vix:.1f} ({'⚠️  HIGH FEAR' if macro.vix > 25 else '✅ NORMAL'})

PORTFOLIO STATUS
{'─'*50}
Total P&L:      ${metrics.get('total_pnl',0):+.2f}
Win Rate:        {metrics.get('win_rate',0):.1f}%
Open Positions:  {metrics.get('open_positions',0)}
Capital at Risk: ${metrics.get('capital_at_risk',0):.2f}
Daily P&L:       ${metrics.get('daily_pnl',0):+.2f}

ACTIVE SIGNALS
{'─'*50}
{sig_lines}

WATCH LIST
{'─'*50}
{watch_lines}

Good {'morning' if now.hour < 12 else 'afternoon'}, Philip.
{'Markets look active today — ' + str(len(top_signals)) + ' signal(s) worth watching.' if top_signals else 'Markets are quiet today — good day to review your strategy.'}

──────────────────────────────────────────────────────────
Philip AJ Sogah | APEX Trading System | philipajsogah.io
"""
        return self._send(subject, plain)

    # ── RISK ALERT ────────────────────────────────────────────

    def risk_alert(self, message: str, severity: str = "HIGH") -> bool:
        subject = f"🚨 APEX RISK ALERT [{severity}]: {message[:60]}"
        plain   = f"""
APEX TRADING SYSTEM — RISK ALERT
{'='*50}
Severity:  {severity}
Time:      {datetime.now().strftime('%I:%M %p ET')}

{message}

ACTION: Review your positions immediately.

──────────────────────────────────────────────────────────
Philip AJ Sogah | APEX Trading System | philipajsogah.io
"""
        return self._send(subject, plain)

    # ── WEEKLY REPORT ─────────────────────────────────────────

    def weekly_report(self, metrics: dict, closed_trades: list) -> bool:
        now     = datetime.now()
        winners = [t for t in closed_trades if t.get("pnl",0) > 0]
        losers  = [t for t in closed_trades if t.get("pnl",0) <= 0]
        subject = (f"📊 APEX Weekly Report | "
                   f"W/L: {len(winners)}/{len(losers)} | "
                   f"P&L: ${metrics.get('weekly_pnl',0):+.2f}")

        trade_lines = "\n".join(
            f"  {'✅' if t.get('pnl',0)>0 else '🛑'} "
            f"{t.get('symbol','?'):<10} "
            f"{t.get('side','?'):<6} "
            f"P&L: {t.get('pnl_pct',0):+.2f}% (${t.get('pnl',0):+.2f})"
            for t in closed_trades[-10:]
        ) or "  No closed trades this week"

        plain = f"""
APEX TRADING SYSTEM — WEEKLY PERFORMANCE REPORT
{'='*60}
Week ending: {now.strftime('%A, %B %d, %Y')}
{'='*60}

PERFORMANCE SUMMARY
{'─'*50}
Weekly P&L:      ${metrics.get('weekly_pnl',0):+.2f}
Total Trades:     {len(closed_trades)}
Winners:          {len(winners)} ({len(winners)/max(len(closed_trades),1)*100:.0f}%)
Losers:           {len(losers)}
Avg Win:          ${statistics.mean([t.get('pnl',0) for t in winners] or [0]):+.2f}
Avg Loss:         ${statistics.mean([t.get('pnl',0) for t in losers] or [0]):+.2f}
Best Trade:       ${max((t.get('pnl',0) for t in closed_trades), default=0):+.2f}
Worst Trade:      ${min((t.get('pnl',0) for t in closed_trades), default=0):+.2f}

TRADE LOG
{'─'*50}
{trade_lines}

Keep pushing, Philip. Consistency beats perfection.

──────────────────────────────────────────────────────────
Philip AJ Sogah | APEX Trading System | philipajsogah.io
"""
        try:
            import statistics
        except:
            pass
        return self._send(subject, plain)


import statistics
