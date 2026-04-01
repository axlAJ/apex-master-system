"""
Market Data Feed — APEX Trading System
Philip AJ Sogah | philipajsogah.io
========================================
Unified data feed for all asset classes:
  - US Stocks:  Alpaca Markets (real-time)
  - Gold/Oil:   GLD, GC=F, USO, CL=F via yfinance
  - Crypto:     yfinance (BTC-USD, ETH-USD)
  - Forex:      yfinance (EURUSD=X, GBPUSD=X)
  - Macro:      FRED (yield curve, inflation, VIX)

All data normalized into a unified Bar/Quote format
for the signal engine to consume.
"""

import os
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta, date
from dataclasses import dataclass, field
from typing import Optional
import logging

log = logging.getLogger(__name__)

# ── UNIVERSE ─────────────────────────────────────────────────

UNIVERSE = {
    # US Stocks
    "AAPL":  {"name":"Apple",          "class":"equity",  "sector":"tech"},
    "NVDA":  {"name":"Nvidia",         "class":"equity",  "sector":"tech"},
    "TSLA":  {"name":"Tesla",          "class":"equity",  "sector":"auto"},
    "SPY":   {"name":"S&P 500 ETF",    "class":"equity",  "sector":"index"},
    "QQQ":   {"name":"Nasdaq ETF",     "class":"equity",  "sector":"index"},
    # Gold & Oil (ETF proxies — tradeable via Alpaca)
    "GLD":   {"name":"Gold ETF",       "class":"commodity","sector":"gold"},
    "USO":   {"name":"Oil ETF",        "class":"commodity","sector":"oil"},
    "GDX":   {"name":"Gold Miners",    "class":"equity",  "sector":"gold"},
    # Crypto (via Alpaca crypto)
    "BTC/USD":{"name":"Bitcoin",       "class":"crypto",  "sector":"crypto"},
    "ETH/USD":{"name":"Ethereum",      "class":"crypto",  "sector":"crypto"},
    # Forex (via Alpaca forex)
    "EUR/USD":{"name":"Euro/Dollar",   "class":"forex",   "sector":"forex"},
    "GBP/USD":{"name":"Pound/Dollar",  "class":"forex",   "sector":"forex"},
}

# ── DATA STRUCTURES ───────────────────────────────────────────

@dataclass
class Bar:
    symbol:    str
    timestamp: str
    open:      float
    high:      float
    low:       float
    close:     float
    volume:    float
    timeframe: str    # 1D, 1W, 1M

@dataclass
class Quote:
    symbol:    str
    price:     float
    bid:       float
    ask:       float
    spread:    float
    volume:    int
    timestamp: str
    asset_class: str

@dataclass
class MacroSnapshot:
    yield_2y:    float
    yield_10y:   float
    yield_spread:float
    fed_funds:   float
    vix:         float
    curve_shape: str   # normal, flat, inverted
    timestamp:   str


# ── ALPACA FEED ───────────────────────────────────────────────

class AlpacaFeed:
    DATA_URL   = "https://data.alpaca.markets/v2"
    CRYPTO_URL = "https://data.alpaca.markets/v1beta3"

    def __init__(self, key: str, secret: str):
        self.key    = key
        self.secret = secret

    def _get(self, url: str, params: dict = None) -> dict:
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={
            "APCA-API-KEY-ID":     self.key,
            "APCA-API-SECRET-KEY": self.secret,
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read())
        except Exception as e:
            log.warning(f"Alpaca fetch error: {e}")
            return {}

    def quote(self, symbol: str) -> Optional[Quote]:
        """Get latest quote for a stock/ETF."""
        data = self._get(f"{self.DATA_URL}/stocks/{symbol}/quotes/latest")
        q = data.get("quote", {})
        if not q:
            return None
        bid = float(q.get("bp", 0))
        ask = float(q.get("ap", 0))
        price = (bid + ask) / 2 if bid and ask else 0
        info = UNIVERSE.get(symbol, {})
        return Quote(
            symbol      = symbol,
            price       = round(price, 4),
            bid         = round(bid, 4),
            ask         = round(ask, 4),
            spread      = round(ask - bid, 4),
            volume      = int(q.get("as", 0)) + int(q.get("bs", 0)),
            timestamp   = q.get("t", datetime.now(timezone.utc).isoformat()),
            asset_class = info.get("class", "equity"),
        )

    def crypto_quote(self, symbol: str) -> Optional[Quote]:
        """Get latest crypto quote."""
        sym = symbol.replace("/", "")
        data = self._get(f"{self.CRYPTO_URL}/crypto/us/latest/quotes",
                         {"symbols": sym})
        q = data.get("quotes", {}).get(sym, {}).get("quote", {})
        if not q:
            return None
        bid = float(q.get("bp", 0))
        ask = float(q.get("ap", 0))
        return Quote(
            symbol      = symbol,
            price       = round((bid+ask)/2, 4),
            bid         = round(bid, 4),
            ask         = round(ask, 4),
            spread      = round(ask-bid, 4),
            volume      = int(q.get("as", 0)),
            timestamp   = q.get("t", datetime.now(timezone.utc).isoformat()),
            asset_class = "crypto",
        )

    def bars(self, symbol: str, timeframe: str = "1Day",
             limit: int = 60) -> list:
        """Get historical OHLCV bars."""
        end   = datetime.now(timezone.utc)
        start = end - timedelta(days=limit * 2)
        params = {
            "timeframe": timeframe,
            "start":     start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end":       end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "limit":     limit,
        }
        if symbol in ("BTC/USD", "ETH/USD"):
            sym  = symbol.replace("/", "")
            data = self._get(f"{self.CRYPTO_URL}/crypto/us/bars",
                             {"symbols": sym, **params})
            raw  = data.get("bars", {}).get(sym, [])
        else:
            data = self._get(f"{self.DATA_URL}/stocks/{symbol}/bars", params)
            raw  = data.get("bars", [])

        tf_map = {"1Day":"1D","1Week":"1W","1Month":"1M"}
        tf     = tf_map.get(timeframe, "1D")
        return [Bar(
            symbol=symbol, timestamp=b["t"],
            open=b["o"], high=b["h"], low=b["l"], close=b["c"],
            volume=b["v"], timeframe=tf,
        ) for b in raw]

    def multi_timeframe_bars(self, symbol: str) -> dict:
        """Get daily, weekly, and monthly bars for MTF analysis."""
        return {
            "1D": self.bars(symbol, "1Day",   60),
            "1W": self.bars(symbol, "1Week",  52),
            "1M": self.bars(symbol, "1Month", 24),
        }

    def all_quotes(self) -> dict:
        """Fetch quotes for all symbols."""
        quotes = {}
        for sym, info in UNIVERSE.items():
            try:
                if info["class"] == "crypto":
                    q = self.crypto_quote(sym)
                elif info["class"] == "forex":
                    q = None   # forex via yfinance fallback
                else:
                    q = self.quote(sym)
                if q and q.price > 0:
                    quotes[sym] = q
                time.sleep(0.1)
            except Exception as e:
                log.warning(f"Quote error {sym}: {e}")
        return quotes


# ── YAHOO FINANCE FALLBACK ────────────────────────────────────

class YFinanceFeed:
    """
    Yahoo Finance for commodities, forex, and fallback data.
    No API key needed. Rate limit: ~2000 req/hour.
    """

    BASE = "https://query1.finance.yahoo.com/v8/finance/chart"

    YAHOO_MAP = {
        "GLD":     "GLD",
        "USO":     "USO",
        "GDX":     "GDX",
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "BTC/USD": "BTC-USD",
        "ETH/USD": "ETH-USD",
        "VIX":     "^VIX",
    }

    def price(self, symbol: str) -> Optional[float]:
        yf_sym = self.YAHOO_MAP.get(symbol, symbol)
        url    = f"{self.BASE}/{yf_sym}?interval=1d&range=2d"
        req    = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0"
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            closes = [c for c in closes if c is not None]
            return round(closes[-1], 4) if closes else None
        except Exception as e:
            log.warning(f"YFinance error {symbol}: {e}")
            return None

    def bars(self, symbol: str, period: str = "3mo",
             interval: str = "1d") -> list:
        yf_sym = self.YAHOO_MAP.get(symbol, symbol)
        url    = f"{self.BASE}/{yf_sym}?interval={interval}&range={period}"
        req    = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            result = data["chart"]["result"][0]
            times  = result["timestamp"]
            ohlcv  = result["indicators"]["quote"][0]
            bars   = []
            for i, ts in enumerate(times):
                c = ohlcv["close"][i]
                if c is None: continue
                bars.append(Bar(
                    symbol    = symbol,
                    timestamp = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                    open      = ohlcv["open"][i]   or c,
                    high      = ohlcv["high"][i]   or c,
                    low       = ohlcv["low"][i]    or c,
                    close     = c,
                    volume    = ohlcv["volume"][i] or 0,
                    timeframe = "1D",
                ))
            return bars
        except Exception as e:
            log.warning(f"YFinance bars error {symbol}: {e}")
            return []

    def vix(self) -> Optional[float]:
        return self.price("VIX")


# ── FRED MACRO FEED ───────────────────────────────────────────

class FREDFeed:
    BASE = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, key: str = None):
        self.key = key or os.getenv("FRED_API_KEY", "")

    def get(self, series: str) -> Optional[float]:
        if not self.key:
            return None
        params = {"series_id": series, "api_key": self.key,
                  "file_type": "json", "sort_order": "desc", "limit": 5}
        url = self.BASE + "?" + urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(url, timeout=8) as r:
                data = json.loads(r.read())
            for o in data.get("observations", []):
                if o.get("value") not in (".", ""):
                    return float(o["value"])
        except Exception as e:
            log.warning(f"FRED error {series}: {e}")
        return None

    def macro_snapshot(self) -> MacroSnapshot:
        y2  = self.get("DGS2")  or 4.0
        y10 = self.get("DGS10") or 4.4
        fed = self.get("DFF")   or 4.3
        spread = y10 - y2
        shape  = "inverted" if spread < -0.1 else "flat" if spread < 0.5 else "normal"
        return MacroSnapshot(
            yield_2y     = y2,
            yield_10y    = y10,
            yield_spread = round(spread, 3),
            fed_funds    = fed,
            vix          = YFinanceFeed().vix() or 15.0,
            curve_shape  = shape,
            timestamp    = datetime.now(timezone.utc).isoformat(),
        )


# ── UNIFIED FEED ──────────────────────────────────────────────

class MarketFeed:
    """
    Single interface to all data sources.
    This is what the signal engine consumes.
    """

    def __init__(self, alpaca_key: str, alpaca_secret: str, fred_key: str = None):
        self.alpaca = AlpacaFeed(alpaca_key, alpaca_secret)
        self.yf     = YFinanceFeed()
        self.fred   = FREDFeed(fred_key)
        self._macro_cache  = None
        self._macro_ts     = 0

    def quotes(self) -> dict:
        """Get all quotes — Alpaca for stocks, YFinance for others."""
        quotes = self.alpaca.all_quotes()

        # Fill in forex/commodity gaps with YFinance
        for sym, info in UNIVERSE.items():
            if sym not in quotes:
                price = self.yf.price(sym)
                if price:
                    quotes[sym] = Quote(
                        symbol=sym, price=price, bid=price*0.9995,
                        ask=price*1.0005, spread=price*0.001,
                        volume=0, timestamp=datetime.now(timezone.utc).isoformat(),
                        asset_class=info["class"],
                    )
        return quotes

    def bars(self, symbol: str, timeframe: str = "1D",
             limit: int = 60) -> list:
        """Get bars — Alpaca first, YFinance fallback."""
        info = UNIVERSE.get(symbol, {})
        if info.get("class") in ("forex",) or symbol in ("GLD","USO","GDX"):
            period_map = {"1D":"3mo","1W":"1y","1M":"2y"}
            interval_map = {"1D":"1d","1W":"1wk","1M":"1mo"}
            return self.yf.bars(symbol,
                                period_map.get(timeframe,"3mo"),
                                interval_map.get(timeframe,"1d"))
        tf_map = {"1D":"1Day","1W":"1Week","1M":"1Month"}
        return self.alpaca.bars(symbol, tf_map.get(timeframe,"1Day"), limit)

    def mtf(self, symbol: str) -> dict:
        """Multi-timeframe bars — daily, weekly, monthly."""
        return {
            "1D": self.bars(symbol, "1D", 60),
            "1W": self.bars(symbol, "1W", 52),
            "1M": self.bars(symbol, "1M", 24),
        }

    def macro(self) -> MacroSnapshot:
        """Macro snapshot — cached 1 hour."""
        now = time.time()
        if now - self._macro_ts > 3600 or not self._macro_cache:
            self._macro_cache = self.fred.macro_snapshot()
            self._macro_ts    = now
        return self._macro_cache


if __name__ == "__main__":
    key    = os.getenv("ALPACA_API_KEY")
    secret = os.getenv("ALPACA_SECRET")
    fred   = os.getenv("FRED_API_KEY")

    if not key or not secret:
        raise SystemExit("Set ALPACA_API_KEY and ALPACA_SECRET")

    feed = MarketFeed(key, secret, fred)
    print("Fetching all quotes...")
    quotes = feed.quotes()
    for sym, q in quotes.items():
        print(f"  {sym:<12} ${q.price:>10.4f}  [{q.asset_class}]")

    print("\nMacro snapshot:")
    m = feed.macro()
    print(f"  2Y={m.yield_2y:.2f}% 10Y={m.yield_10y:.2f}% "
          f"Spread={m.yield_spread:+.2f}% Fed={m.fed_funds:.2f}% "
          f"VIX={m.vix:.1f} Curve={m.curve_shape.upper()}")
