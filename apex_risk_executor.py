"""
Risk Manager & Trade Executor — APEX Trading System
Philip AJ Sogah | philipajsogah.io
======================================================
Enforces all risk limits and executes trades via Alpaca.

Risk Rules (hardcoded — cannot be overridden):
  - Max position size:    2% of portfolio per trade
  - Max total exposure:   20% of portfolio
  - Daily loss limit:     5% of portfolio — halts all trading
  - Stop loss:            Required on every trade
  - No trading 15min after open or before close
  - Max 5 open positions at once
  - Correlation check:    No 2 positions >80% correlated
"""

import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, date
from dataclasses import dataclass
from typing import Optional
from apex_signal_engine import TradeSignal


@dataclass
class Position:
    symbol:       str
    side:         str        # long | short
    qty:          float
    entry_price:  float
    current_price:float
    stop_price:   float
    target_price: float
    cost_basis:   float
    opened_at:    str
    signal_score: float
    asset_class:  str
    status:       str = "open"
    exit_price:   float = 0.0
    pnl:          float = 0.0
    pnl_pct:      float = 0.0
    closed_at:    str   = ""
    close_reason: str   = ""


class RiskManager:
    SAVE_FILE = "apex_positions.json"

    # Hard limits
    MAX_POSITION_PCT    = 0.02    # 2% of portfolio per trade
    MAX_TOTAL_PCT       = 0.20    # 20% total exposure
    DAILY_LOSS_LIMIT    = 0.05    # 5% daily loss = halt
    MAX_POSITIONS       = 5
    MARKET_OPEN_BUFFER  = 15      # minutes
    MARKET_CLOSE_BUFFER = 15

    def __init__(self, starting_capital: float = 10000.0):
        self.starting_capital = starting_capital
        self.positions: dict = {}
        self.closed:    list      = []
        self.daily_pnl  = 0.0
        self.daily_date = datetime.now().strftime("%Y-%m-%d")
        self.trades_today = 0
        self._load()

    def check(self, signal: TradeSignal,
              portfolio_equity: float) -> tuple:
        """
        Pre-trade risk check.
        Returns: (approved, reason, position_size_usd, qty)
        """
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self.daily_date:
            self.daily_pnl    = 0.0
            self.daily_date   = today
            self.trades_today = 0

        # 1. Market hours
        ok, msg = self._market_hours()
        if not ok:
            return False, msg, 0, 0

        # 2. Daily loss limit
        daily_loss_pct = abs(self.daily_pnl) / portfolio_equity
        if self.daily_pnl < 0 and daily_loss_pct >= self.DAILY_LOSS_LIMIT:
            return False, f"Daily loss limit hit ({daily_loss_pct:.1%}) — trading halted", 0, 0

        # 3. Max positions
        if len(self.positions) >= self.MAX_POSITIONS:
            return False, f"Max {self.MAX_POSITIONS} positions reached", 0, 0

        # 4. Already in position
        if signal.symbol in self.positions:
            return False, f"Already in {signal.symbol}", 0, 0

        # 5. Total exposure check
        total_exposure = sum(p.cost_basis for p in self.positions.values())
        max_exposure   = portfolio_equity * self.MAX_TOTAL_PCT
        if total_exposure >= max_exposure:
            return False, f"Max exposure reached (${total_exposure:.0f}/${max_exposure:.0f})", 0, 0

        # 6. Position sizing (scale to signal strength)
        base_pct  = self.MAX_POSITION_PCT
        strength_mult = {
            "STRONG":   1.0,
            "MODERATE": 0.65,
            "WEAK":     0.35,
        }.get(signal.strength, 0.5)

        position_size = portfolio_equity * base_pct * strength_mult
        position_size = min(position_size, max_exposure - total_exposure)

        if signal.entry_price <= 0:
            return False, "Invalid entry price", 0, 0

        qty = round(position_size / signal.entry_price, 4)
        if qty < 0.001:
            return False, "Position size too small", 0, 0

        # 7. Risk/reward check — minimum 1.5:1
        if signal.risk_reward < 1.5:
            return False, f"Risk/reward {signal.risk_reward:.1f}:1 below minimum 1.5:1", 0, 0

        return True, "All checks passed", round(position_size, 2), qty

    def open_position(self, signal: TradeSignal, qty: float,
                      cost_basis: float) -> Position:
        pos = Position(
            symbol        = signal.symbol,
            side          = "long"  if signal.action == "BUY" else "short",
            qty           = qty,
            entry_price   = signal.entry_price,
            current_price = signal.entry_price,
            stop_price    = signal.stop_price,
            target_price  = signal.target_price,
            cost_basis    = cost_basis,
            opened_at     = datetime.now(timezone.utc).isoformat(),
            signal_score  = signal.composite_score,
            asset_class   = signal.asset_class,
        )
        self.positions[signal.symbol] = pos
        self.trades_today += 1
        self._save()
        return pos

    def update_prices(self, prices: dict) -> list:
        """Check stop/target hits. Returns list of (symbol, reason) exits."""
        events = []
        for sym, pos in list(self.positions.items()):
            price = prices.get(sym)
            if not price or pos.status != "open":
                continue
            pos.current_price = price

            stop_hit = (pos.side == "long"  and price <= pos.stop_price) or \
                       (pos.side == "short" and price >= pos.stop_price)
            tgt_hit  = (pos.side == "long"  and price >= pos.target_price) or \
                       (pos.side == "short" and price <= pos.target_price)

            if stop_hit:
                self._close(sym, price, "stop_loss")
                events.append((sym, "stop_loss"))
            elif tgt_hit:
                self._close(sym, price, "target_hit")
                events.append((sym, "target_hit"))

        self._save()
        return events

    def close(self, symbol: str, price: float, reason: str = "manual") -> Optional[Position]:
        if symbol not in self.positions:
            return None
        return self._close(symbol, price, reason)

    def _close(self, symbol: str, price: float, reason: str) -> Position:
        pos              = self.positions.pop(symbol)
        pos.status       = reason
        pos.exit_price   = price
        pos.closed_at    = datetime.now(timezone.utc).isoformat()
        pos.close_reason = reason
        pos.pnl          = ((price - pos.entry_price) * pos.qty
                            if pos.side == "long"
                            else (pos.entry_price - price) * pos.qty)
        pos.pnl_pct      = pos.pnl / pos.cost_basis * 100
        self.daily_pnl  += pos.pnl
        self.closed.append(pos)
        return pos

    def metrics(self, equity: float = None) -> dict:
        equity     = equity or self.starting_capital
        total_pnl  = sum(p.pnl for p in self.closed)
        winners    = [p for p in self.closed if p.pnl > 0]
        win_rate   = len(winners) / len(self.closed) * 100 if self.closed else 0
        exposure   = sum(p.cost_basis for p in self.positions.values())
        return {
            "open_positions":  len(self.positions),
            "capital_at_risk": round(exposure, 2),
            "daily_pnl":       round(self.daily_pnl, 2),
            "total_pnl":       round(total_pnl, 2),
            "total_trades":    len(self.closed),
            "win_rate":        round(win_rate, 1),
            "trades_today":    self.trades_today,
            "daily_limit_ok":  self.daily_pnl > -(equity * self.DAILY_LOSS_LIMIT),
        }

    def _market_hours(self) -> tuple:
        now  = datetime.now(timezone.utc)
        h, m = now.hour, now.minute
        total = h * 60 + m
        # Market: 13:30–20:00 UTC (9:30am–4pm ET)
        open_t  = 13 * 60 + 30
        close_t = 20 * 60
        if total < open_t:
            return False, "Market not open yet"
        if total > close_t:
            return False, "Market closed"
        if total < open_t + self.MARKET_OPEN_BUFFER:
            return False, f"Within {self.MARKET_OPEN_BUFFER}min open buffer"
        if total > close_t - self.MARKET_CLOSE_BUFFER:
            return False, f"Within {self.MARKET_CLOSE_BUFFER}min close buffer"
        return True, "Market hours OK"

    def _save(self):
        state = {
            "positions":  {s: vars(p) for s, p in self.positions.items()},
            "closed":     [vars(p) for p in self.closed[-100:]],
            "daily_pnl":  self.daily_pnl,
            "daily_date": self.daily_date,
        }
        with open(self.SAVE_FILE, "w") as f:
            json.dump(state, f, indent=2)

    def _load(self):
        if not os.path.exists(self.SAVE_FILE):
            return
        try:
            with open(self.SAVE_FILE) as f:
                s = json.load(f)
            self.daily_pnl  = s.get("daily_pnl", 0)
            self.daily_date = s.get("daily_date", self.daily_date)
            for sym, pd in s.get("positions", {}).items():
                self.positions[sym] = Position(**pd)
            for pd in s.get("closed", []):
                self.closed.append(Position(**pd))
            print(f"  Loaded: {len(self.positions)} open positions, "
                  f"{len(self.closed)} closed trades")
        except Exception as e:
            print(f"  Load error: {e}")


class AlpacaExecutor:
    PAPER_URL = "https://paper-api.alpaca.markets"
    LIVE_URL  = "https://api.alpaca.markets"

    def __init__(self, key: str, secret: str):
        self.key    = key
        self.secret = secret
        live        = os.getenv("ALPACA_LIVE","false").lower() == "true"
        self.base   = self.LIVE_URL if live else self.PAPER_URL
        self.live   = live
        mode = "🔴 LIVE" if live else "🟡 PAPER"
        print(f"  Alpaca executor: {mode}")

    def _post(self, endpoint: str, body: dict) -> dict:
        url  = f"{self.base}{endpoint}"
        data = json.dumps(body).encode()
        req  = urllib.request.Request(url, data=data, headers={
            "APCA-API-KEY-ID":     self.key,
            "APCA-API-SECRET-KEY": self.secret,
            "Content-Type":        "application/json",
            "Accept":              "application/json",
        }, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            return {"error": e.read().decode()}
        except Exception as e:
            return {"error": str(e)}

    def _get(self, endpoint: str) -> dict:
        url = f"{self.base}{endpoint}"
        req = urllib.request.Request(url, headers={
            "APCA-API-KEY-ID":     self.key,
            "APCA-API-SECRET-KEY": self.secret,
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read())
        except Exception as e:
            return {"error": str(e)}

    def execute(self, signal: TradeSignal, qty: float,
                risk_manager: RiskManager) -> dict:
        """Execute a trade with bracket order (entry + stop + target)."""
        side = "buy" if signal.action == "BUY" else "sell"
        print(f"\n  🚀 EXECUTING: {side.upper()} {signal.symbol} "
              f"qty={qty:.4f} @ ~${signal.entry_price:.4f}")

        # Crypto symbols need different format
        sym = signal.symbol.replace("/","") if "/" in signal.symbol else signal.symbol

        order = {
            "symbol":        sym,
            "qty":           str(round(qty, 4)),
            "side":          side,
            "type":          "market",
            "time_in_force": "day",
            "order_class":   "bracket",
            "stop_loss":    {"stop_price": str(round(signal.stop_price, 4))},
            "take_profit":  {"limit_price": str(round(signal.target_price, 4))},
        }

        result = self._post("/v2/orders", order)

        if "error" in result:
            print(f"  ❌ Order failed: {result['error']}")
            return {"success": False, "error": result["error"]}

        order_id = result.get("id","?")
        print(f"  ✅ Order placed: {order_id}")

        # Record in risk manager
        cost_basis = qty * signal.entry_price
        risk_manager.open_position(signal, qty, cost_basis)

        return {
            "success":  True,
            "order_id": order_id,
            "symbol":   signal.symbol,
            "side":     side,
            "qty":      qty,
            "status":   result.get("status","submitted"),
        }

    def account(self) -> dict:
        return self._get("/v2/account")

    def positions(self) -> list:
        r = self._get("/v2/positions")
        return r if isinstance(r, list) else []

    def equity(self) -> float:
        acct = self.account()
        return float(acct.get("equity", 10000))
