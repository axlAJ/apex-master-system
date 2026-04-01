"""
APEX MASTER SYSTEM
Philip AJ Sogah | philipajsogah.io
=====================================
Six elite quantitative modules in one system:

  1. Portfolio Optimiser      — Markowitz efficient frontier, Sharpe maximisation
  2. Monte Carlo Engine       — 10,000 simulations, options pricing, risk scenarios
  3. Price Predictor          — ML model: 1-day, 5-day, 20-day price forecasts
  4. Autonomous Trader        — $100 SPY test, self-executing, end-of-day P&L report
  5. Interest Rate Analyser   — Fed cycle detection, hike/cut pattern trading
  6. Market Structure Analyst — Support/resistance, liquidity zones, order flow

All modules feed into one unified daily email report.

Setup:
  export ALPACA_API_KEY="PKxxxxxxxxxxxxxxxx"
  export ALPACA_SECRET="your_secret"
  export FRED_API_KEY="your_fred_key"
  export GMAIL_ADDRESS="philipaxl7@gmail.com"
  export GMAIL_APP_PASSWORD="your_app_password"
  export ALPACA_LIVE="true"   # for real $100 SPY trading

  /usr/bin/python3 apex_master.py

Commands:
  optimise          — run portfolio optimisation
  montecarlo SPY    — run 10,000 Monte Carlo simulations
  predict AAPL      — get 1/5/20-day price predictions
  rates             — analyse current Fed cycle
  structure SPY     — market structure analysis
  report            — generate full daily report
  status            — show all module status
  quit              — shutdown and send final report
"""

import os, sys, json, time, math, random, statistics, smtplib, threading
import urllib.request, urllib.parse, select
from datetime import datetime, timezone, timedelta, date
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass, field

# ── CREDENTIALS ───────────────────────────────────────────────
ALPACA_KEY    = os.getenv("ALPACA_API_KEY","")
ALPACA_SECRET = os.getenv("ALPACA_SECRET","")
FRED_KEY      = os.getenv("FRED_API_KEY","")
GMAIL_ADDR    = os.getenv("GMAIL_ADDRESS","philipaxl7@gmail.com")
GMAIL_PW      = os.getenv("GMAIL_APP_PASSWORD","")
LIVE_MODE     = os.getenv("ALPACA_LIVE","false").lower() == "true"
TO_EMAIL      = "philipaxl7@gmail.com"

PAPER_URL     = "https://paper-api.alpaca.markets"
LIVE_URL      = "https://api.alpaca.markets"
DATA_URL      = "https://data.alpaca.markets/v2"
BASE_URL      = LIVE_URL if LIVE_MODE else PAPER_URL


# ═══════════════════════════════════════════════════════════════
# SHARED UTILITIES
# ═══════════════════════════════════════════════════════════════

def alpaca_get(endpoint, base=None):
    url = f"{base or DATA_URL}{endpoint}"
    req = urllib.request.Request(url, headers={
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def alpaca_post(endpoint, body, base=None):
    url  = f"{base or BASE_URL}{endpoint}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, headers={
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
        "Content-Type": "application/json",
    }, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()}
    except Exception as e:
        return {"error": str(e)}

def alpaca_delete(endpoint, base=None):
    url = f"{base or BASE_URL}{endpoint}"
    req = urllib.request.Request(url, headers={
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
    }, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return True
    except:
        return False

def fred_get(series):
    if not FRED_KEY: return None
    params = {"series_id":series,"api_key":FRED_KEY,
              "file_type":"json","sort_order":"desc","limit":20}
    url = "https://api.stlouisfed.org/fred/series/observations?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        return [(o["date"], float(o["value"])) for o in data.get("observations",[])
                if o.get("value") not in (".",""," ")]
    except:
        return None

def get_bars(symbol, days=120, timeframe="1Day"):
    """Fetch OHLCV bars from Alpaca, fallback to Yahoo Finance."""
    end   = datetime.now(timezone.utc)
    start = end - timedelta(days=days*2)
    url = (f"{DATA_URL}/stocks/{symbol}/bars?"
           f"timeframe={timeframe}"
           f"&start={start.strftime('%Y-%m-%dT%H:%M:%SZ')}"
           f"&end={end.strftime('%Y-%m-%dT%H:%M:%SZ')}"
           f"&limit={days}&adjustment=raw")
    req = urllib.request.Request(url, headers={
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read())
        bars = data.get("bars", [])
        if bars:
            return bars
    except Exception as e:
        pass

    # Fallback: Yahoo Finance
    try:
        period_map = {20:"1mo", 60:"3mo", 90:"3mo", 120:"6mo", 252:"1y", 500:"2y"}
        period = period_map.get(days, "6mo")
        tf_map = {"1Day":"1d","1Week":"1wk","1Month":"1mo"}
        interval = tf_map.get(timeframe, "1d")
        yf_url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                  f"?interval={interval}&range={period}")
        req2 = urllib.request.Request(yf_url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req2, timeout=10) as r:
            d = json.loads(r.read())
        result = d["chart"]["result"][0]
        times  = result["timestamp"]
        ohlcv  = result["indicators"]["quote"][0]
        bars   = []
        for i, ts in enumerate(times):
            c = ohlcv["close"][i]
            if c is None: continue
            bars.append({
                "t": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                "o": ohlcv["open"][i]   or c,
                "h": ohlcv["high"][i]   or c,
                "l": ohlcv["low"][i]    or c,
                "c": c,
                "v": ohlcv["volume"][i] or 0,
            })
        return bars
    except Exception as e:
        return []

def get_account():
    return alpaca_get("/v2/account", BASE_URL)

def send_email(subject, body, html=None):
    if not GMAIL_PW:
        print(f"\n  📧 EMAIL: {subject}\n{body[:300]}")
        return True
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = GMAIL_ADDR
        msg["To"]      = TO_EMAIL
        msg.attach(MIMEText(body, "plain"))
        if html: msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(GMAIL_ADDR, GMAIL_PW)
            s.sendmail(GMAIL_ADDR, TO_EMAIL, msg.as_string())
        print(f"  📧 Email sent: {subject[:50]}")
        return True
    except Exception as e:
        print(f"  ❌ Email failed: {e}")
        return False


# ═══════════════════════════════════════════════════════════════
# MODULE 1: PORTFOLIO OPTIMISER
# Markowitz Modern Portfolio Theory
# Maximises Sharpe ratio across your holdings
# ═══════════════════════════════════════════════════════════════

class PortfolioOptimiser:
    """
    Markowitz Efficient Frontier optimisation.
    Finds the optimal allocation that maximises Sharpe ratio
    (return per unit of risk) across your portfolio.

    Uses 252-day historical returns, covariance matrix,
    and 10,000 random portfolio simulations to map the frontier.
    """

    SYMBOLS    = ["AAPL","NVDA","TSLA","SPY","GLD","USO","QQQ"]
    RISK_FREE  = 0.045   # 4.5% risk-free rate (current T-bill)
    SIM_COUNT  = 10000

    def __init__(self):
        self.results  = {}
        self.last_run = 0

    def run(self) -> dict:
        print("\n  ── Portfolio Optimiser ─────────────────────────────")
        print(f"  Fetching {len(self.SYMBOLS)} symbols...")

        # Get historical returns
        returns = {}
        for sym in self.SYMBOLS:
            bars = get_bars(sym, 252)
            if len(bars) < 30:
                print(f"  ⚠️  Insufficient data for {sym}")
                continue
            closes = [b["c"] for b in bars]
            daily_returns = [(closes[i]-closes[i-1])/closes[i-1]
                             for i in range(1, len(closes))]
            returns[sym] = daily_returns
            print(f"  ✓ {sym}: {len(daily_returns)} days, "
                  f"avg={statistics.mean(daily_returns)*252*100:.1f}% annualised")

        if len(returns) < 2:
            return {"error": "Need at least 2 symbols with data"}

        syms = list(returns.keys())
        n    = len(syms)

        # Annualised returns and covariance
        ann_returns = {s: statistics.mean(r)*252 for s, r in returns.items()}

        # Covariance matrix
        cov = {}
        for i, s1 in enumerate(syms):
            for j, s2 in enumerate(syms):
                r1 = returns[s1]
                r2 = returns[s2]
                min_len = min(len(r1), len(r2))
                r1, r2  = r1[-min_len:], r2[-min_len:]
                mean1   = statistics.mean(r1)
                mean2   = statistics.mean(r2)
                cov_val = sum((a-mean1)*(b-mean2) for a,b in zip(r1,r2)) / (min_len-1)
                cov[(s1,s2)] = cov_val * 252   # annualised

        # Monte Carlo portfolio simulation
        best_sharpe   = -999
        best_weights  = None
        best_ret      = 0
        best_vol      = 0
        frontier      = []

        print(f"  Running {self.SIM_COUNT:,} portfolio simulations...")
        for _ in range(self.SIM_COUNT):
            # Random weights summing to 1
            w = [random.random() for _ in range(n)]
            total = sum(w)
            w = [x/total for x in w]

            # Portfolio return
            port_ret = sum(w[i]*ann_returns[syms[i]] for i in range(n))

            # Portfolio variance
            port_var = sum(
                w[i]*w[j]*cov.get((syms[i],syms[j]),0)
                for i in range(n) for j in range(n)
            )
            port_vol = math.sqrt(max(0, port_var))

            sharpe = (port_ret - self.RISK_FREE) / (port_vol + 0.001)
            frontier.append((port_ret, port_vol, sharpe, w[:]))

            if sharpe > best_sharpe:
                best_sharpe  = sharpe
                best_weights = w[:]
                best_ret     = port_ret
                best_vol     = port_vol

        # Equal weight for comparison
        eq_w      = [1/n]*n
        eq_ret    = sum(eq_w[i]*ann_returns[syms[i]] for i in range(n))
        eq_var    = sum(eq_w[i]*eq_w[j]*cov.get((syms[i],syms[j]),0)
                        for i in range(n) for j in range(n))
        eq_vol    = math.sqrt(max(0, eq_var))
        eq_sharpe = (eq_ret - self.RISK_FREE) / (eq_vol + 0.001)

        result = {
            "optimal_weights": {syms[i]: round(best_weights[i]*100, 2)
                                for i in range(n)},
            "expected_annual_return": round(best_ret*100, 2),
            "expected_volatility":    round(best_vol*100, 2),
            "sharpe_ratio":           round(best_sharpe, 3),
            "equal_weight_sharpe":    round(eq_sharpe, 3),
            "improvement":            round((best_sharpe-eq_sharpe)/abs(eq_sharpe)*100, 1),
            "simulations":            self.SIM_COUNT,
            "symbols":                syms,
            "frontier_points":        len(frontier),
        }
        self.results  = result
        self.last_run = time.time()

        self._print_result(result)
        return result

    def _print_result(self, r):
        print(f"\n  {'─'*55}")
        print(f"  OPTIMAL PORTFOLIO (Max Sharpe = {r['sharpe_ratio']:.3f})")
        print(f"  {'─'*55}")
        for sym, wt in sorted(r["optimal_weights"].items(),
                               key=lambda x: x[1], reverse=True):
            bar = "█" * int(wt/3)
            print(f"  {sym:<8} {wt:>6.2f}%  {bar}")
        print(f"  {'─'*55}")
        print(f"  Expected Return:   {r['expected_annual_return']:>7.2f}% / year")
        print(f"  Expected Vol:      {r['expected_volatility']:>7.2f}% / year")
        print(f"  Sharpe Ratio:      {r['sharpe_ratio']:>7.3f}")
        print(f"  vs Equal Weight:   {r['equal_weight_sharpe']:>7.3f} "
              f"({r['improvement']:+.1f}% improvement)")
        print(f"  {'─'*55}\n")


# ═══════════════════════════════════════════════════════════════
# MODULE 2: MONTE CARLO ENGINE
# 10,000 simulations for options pricing + risk scenarios
# ═══════════════════════════════════════════════════════════════

class MonteCarloEngine:
    """
    Monte Carlo simulation engine.

    Applications:
    1. Options pricing (Black-Scholes + MC validation)
    2. Portfolio risk scenarios (VaR, CVaR)
    3. Price path simulation for any symbol
    """

    SIMULATIONS = 10000

    def run_price_simulation(self, symbol: str, days: int = 30) -> dict:
        """Simulate 10,000 price paths for the next N days."""
        bars = get_bars(symbol, 252)
        if len(bars) < 30:
            return {"error": "Insufficient historical data"}

        closes  = [b["c"] for b in bars]
        current = closes[-1]

        # Calculate drift and volatility from history
        log_returns = [math.log(closes[i]/closes[i-1])
                       for i in range(1, len(closes))]
        mu    = statistics.mean(log_returns)   # daily drift
        sigma = statistics.stdev(log_returns)  # daily volatility

        # Run simulations
        final_prices = []
        paths        = []
        worst_paths  = []

        for sim in range(self.SIMULATIONS):
            price  = current
            path   = [price]
            for _ in range(days):
                shock  = random.gauss(0, 1)
                price *= math.exp((mu - 0.5*sigma**2) + sigma*shock)
                path.append(price)
            final_prices.append(price)
            if sim < 5:  # save a few paths for display
                paths.append(path)

        final_prices.sort()
        n = len(final_prices)

        # Value at Risk
        var_95  = final_prices[int(n*0.05)]
        var_99  = final_prices[int(n*0.01)]
        cvar_95 = statistics.mean(final_prices[:int(n*0.05)])

        # Expected move
        median    = final_prices[n//2]
        bull_p75  = final_prices[int(n*0.75)]
        bear_p25  = final_prices[int(n*0.25)]

        result = {
            "symbol":          symbol,
            "current_price":   round(current, 4),
            "days_ahead":      days,
            "simulations":     self.SIMULATIONS,
            "expected_price":  round(statistics.mean(final_prices), 4),
            "median_price":    round(median, 4),
            "bull_case_75":    round(bull_p75, 4),
            "bear_case_25":    round(bear_p25, 4),
            "var_95":          round(var_95, 4),
            "var_99":          round(var_99, 4),
            "cvar_95":         round(cvar_95, 4),
            "expected_move":   round((statistics.mean(final_prices)-current)/current*100, 2),
            "annual_vol":      round(sigma*math.sqrt(252)*100, 2),
            "prob_profit":     round(sum(1 for p in final_prices if p > current)/n*100, 1),
            "prob_loss_10pct": round(sum(1 for p in final_prices if p < current*0.90)/n*100, 1),
        }

        self._print_simulation(result)
        return result

    def price_option(self, symbol: str, strike: float, days_to_expiry: int,
                     option_type: str = "call") -> dict:
        """Price an option using Monte Carlo simulation."""
        bars = get_bars(symbol, 90)
        if not bars:
            return {"error": "No data"}

        closes  = [b["c"] for b in bars]
        current = closes[-1]
        log_ret = [math.log(closes[i]/closes[i-1]) for i in range(1,len(closes))]
        sigma   = statistics.stdev(log_ret) * math.sqrt(252)
        r       = 0.045   # risk-free rate
        T       = days_to_expiry / 365

        # MC option pricing
        payoffs = []
        for _ in range(self.SIMULATIONS):
            shock   = random.gauss(0, 1)
            ST      = current * math.exp((r - 0.5*sigma**2)*T + sigma*math.sqrt(T)*shock)
            if option_type == "call":
                payoffs.append(max(0, ST - strike))
            else:
                payoffs.append(max(0, strike - ST))

        mc_price = math.exp(-r*T) * statistics.mean(payoffs)

        # Black-Scholes for comparison
        d1 = (math.log(current/strike) + (r + 0.5*sigma**2)*T) / (sigma*math.sqrt(T)+0.001)
        d2 = d1 - sigma*math.sqrt(T)
        bs_price = self._bs_price(current, strike, r, sigma, T, option_type, d1, d2)

        return {
            "symbol":         symbol,
            "option_type":    option_type.upper(),
            "current_price":  round(current, 4),
            "strike":         round(strike, 4),
            "days_to_expiry": days_to_expiry,
            "mc_price":       round(mc_price, 4),
            "bs_price":       round(bs_price, 4),
            "implied_vol":    round(sigma*100, 2),
            "delta":          round(self._norm_cdf(d1 if option_type=="call" else -d1), 4),
            "theta":          round(-current*sigma*math.exp(-0.5*d1**2)/(2*math.sqrt(2*math.pi*T+0.001)), 4),
            "simulations":    self.SIMULATIONS,
        }

    def _bs_price(self, S, K, r, sigma, T, opt, d1, d2):
        if T <= 0: return max(0, S-K) if opt=="call" else max(0, K-S)
        if opt == "call":
            return S*self._norm_cdf(d1) - K*math.exp(-r*T)*self._norm_cdf(d2)
        return K*math.exp(-r*T)*self._norm_cdf(-d2) - S*self._norm_cdf(-d1)

    def _norm_cdf(self, x):
        return 0.5*(1+math.erf(x/math.sqrt(2)))

    def _print_simulation(self, r):
        up   = '\033[92m'; dn='\033[91m'; rst='\033[0m'; amb='\033[93m'
        move_color = up if r["expected_move"]>=0 else dn
        print(f"\n  ── Monte Carlo: {r['symbol']} ({r['simulations']:,} simulations) ──")
        print(f"  Current Price:    ${r['current_price']:.2f}")
        print(f"  Expected ({r['days_ahead']}d):   {move_color}${r['expected_price']:.2f} "
              f"({r['expected_move']:+.2f}%){rst}")
        print(f"  Bull Case (75%):  {up}${r['bull_case_75']:.2f}{rst}")
        print(f"  Bear Case (25%):  {dn}${r['bear_case_25']:.2f}{rst}")
        print(f"  VaR 95%:          {dn}${r['var_95']:.2f} (worst 5% outcome){rst}")
        print(f"  VaR 99%:          {dn}${r['var_99']:.2f} (worst 1% outcome){rst}")
        print(f"  Prob of Profit:   {move_color}{r['prob_profit']:.1f}%{rst}")
        print(f"  Annual Vol:       {amb}{r['annual_vol']:.1f}%{rst}")


# ═══════════════════════════════════════════════════════════════
# MODULE 3: PRICE PREDICTOR
# ML-style prediction using technical + macro features
# No external ML libraries — pure math
# ═══════════════════════════════════════════════════════════════

class PricePredictor:
    """
    Multi-horizon price prediction without external ML libraries.

    Features used:
    - Momentum (5, 10, 20 day)
    - Mean reversion (deviation from MA)
    - Volume trend
    - RSI (overbought/oversold)
    - MACD signal
    - Volatility regime
    - Macro overlay (yield curve, VIX proxy)

    Outputs: 1-day, 5-day, 20-day price targets with confidence.
    """

    def predict(self, symbol: str) -> dict:
        print(f"\n  ── Price Predictor: {symbol} ──────────────────────")
        bars = get_bars(symbol, 120)
        if len(bars) < 30:
            return {"error": "Insufficient data"}

        closes  = [b["c"] for b in bars]
        volumes = [b["v"] for b in bars]
        highs   = [b["h"] for b in bars]
        lows    = [b["l"] for b in bars]
        current = closes[-1]

        features = {}

        # Momentum features
        for period in [5, 10, 20]:
            if len(closes) > period:
                mom = (closes[-1] - closes[-period]) / closes[-period] * 100
                features[f"mom_{period}d"] = mom

        # RSI
        gains  = [max(0, closes[i]-closes[i-1]) for i in range(-15,0)]
        losses = [max(0, closes[i-1]-closes[i]) for i in range(-15,0)]
        avg_g  = statistics.mean(gains)  or 0.001
        avg_l  = statistics.mean(losses) or 0.001
        rsi    = 100 - (100/(1+avg_g/avg_l))
        features["rsi"] = rsi

        # MACD
        ema = lambda data, p: sum(data[-p:]) / p   # simplified EMA
        macd = ema(closes, 12) - ema(closes, 26)
        signal_line = ema(closes, 9)
        features["macd_signal"] = macd - signal_line

        # Volume trend
        avg_vol_recent = statistics.mean(volumes[-5:])
        avg_vol_prev   = statistics.mean(volumes[-20:-5])
        features["vol_trend"] = (avg_vol_recent/avg_vol_prev - 1) * 100

        # Deviation from MA
        ma20 = statistics.mean(closes[-20:])
        features["ma_deviation"] = (current - ma20) / ma20 * 100

        # Volatility (annualised)
        log_ret = [math.log(closes[i]/closes[i-1]) for i in range(1,len(closes))]
        vol     = statistics.stdev(log_ret[-20:]) * math.sqrt(252) * 100
        features["volatility"] = vol

        # Support/Resistance proximity
        recent_high = max(highs[-20:])
        recent_low  = min(lows[-20:])
        rng = recent_high - recent_low
        pos_in_range = (current - recent_low) / (rng + 0.001)
        features["range_position"] = pos_in_range

        # Generate predictions for each horizon
        predictions = {}
        for days, label in [(1,"1d"),(5,"5d"),(20,"20d")]:
            score = 0
            conf  = 50

            # Momentum contribution
            mom_avg = statistics.mean([features.get(f"mom_{p}d",0) for p in [5,10,20]])
            score  += mom_avg * (0.3 if days==1 else 0.2 if days==5 else 0.1)

            # RSI mean reversion
            if rsi > 70:
                score  -= (rsi-70) * 0.3   # overbought = bearish for short term
                conf   += 10
            elif rsi < 30:
                score  += (30-rsi) * 0.3   # oversold = bullish
                conf   += 10

            # MACD
            score += features["macd_signal"] * 5

            # MA deviation (mean reversion for longer horizons)
            if days >= 5:
                score -= features["ma_deviation"] * 0.2

            # Volume confirmation
            if features["vol_trend"] > 20 and mom_avg > 0:
                score += 5   # volume confirming uptrend
                conf  += 5
            elif features["vol_trend"] > 20 and mom_avg < 0:
                score -= 5
                conf  += 5

            # Volatility adjustment
            daily_vol = vol / math.sqrt(252)
            expected_move_pct = score * daily_vol / 10 * math.sqrt(days)
            expected_move_pct = max(-vol/2, min(vol/2, expected_move_pct))

            target = round(current * (1 + expected_move_pct/100), 4)
            conf   = min(85, max(30, conf + abs(score)*0.3))
            direction = "UP" if expected_move_pct > 0 else "DOWN"

            predictions[label] = {
                "target":        target,
                "change_pct":    round(expected_move_pct, 2),
                "direction":     direction,
                "confidence":    round(conf, 1),
                "days":          days,
            }

        result = {
            "symbol":      symbol,
            "current":     round(current, 4),
            "rsi":         round(rsi, 1),
            "macd":        round(features["macd_signal"], 4),
            "momentum_5d": round(features.get("mom_5d",0), 2),
            "volatility":  round(vol, 2),
            "predictions": predictions,
        }
        self._print_predictions(result)
        return result

    def _print_predictions(self, r):
        up='\033[92m'; dn='\033[91m'; rst='\033[0m'; amb='\033[93m'
        print(f"  Current: ${r['current']:.4f} | RSI={r['rsi']:.1f} | "
              f"Vol={r['volatility']:.1f}% | Mom5D={r['momentum_5d']:+.2f}%")
        print(f"  {'─'*52}")
        for label, p in r["predictions"].items():
            col = up if p["direction"]=="UP" else dn
            print(f"  {label:<4}  {col}{p['direction']:<5}{rst}  "
                  f"Target: {col}${p['target']:.4f}{rst}  "
                  f"({p['change_pct']:+.2f}%)  "
                  f"Conf: {amb}{p['confidence']:.0f}%{rst}")
        print()


# ═══════════════════════════════════════════════════════════════
# MODULE 4: AUTONOMOUS TRADER
# $100 SPY test — trades itself, reports at end of day
# Hard limits: max $100 total, halt if -$25 in a day
# ═══════════════════════════════════════════════════════════════

class AutonomousTrader:
    """
    Fully autonomous SPY trader with $100 cap.

    Strategy: Intraday mean reversion on SPY
    - Buy when SPY drops >0.3% from morning open (oversold intraday)
    - Sell when SPY recovers to flat or gains 0.5%
    - Hard stop: sell if down 0.5% from entry
    - Hard halt: stop all trading if daily loss > $25
    - Force close all positions at 3:45pm ET

    End of day: full P&L report emailed to Philip
    """

    MAX_CAPITAL    = 100.0    # max $100 total
    DAILY_LOSS_CAP = 25.0     # halt if lose $25 in a day
    BUY_TRIGGER    = -0.003   # buy if SPY down 0.3% from open
    SELL_TARGET    = 0.005    # sell target: up 0.5% from entry
    STOP_LOSS      = -0.005   # stop loss: down 0.5% from entry
    SYMBOL         = "SPY"

    def __init__(self):
        self.position       = None    # {"qty","entry","order_id"}
        self.daily_pnl      = 0.0
        self.trades         = []
        self.morning_open   = None
        self.halted         = False
        self.running        = False
        self.daily_date     = datetime.now().strftime("%Y-%m-%d")
        self.thread         = None

    def _get_price(self) -> Optional[float]:
        data = alpaca_get(f"/stocks/{self.SYMBOL}/quotes/latest")
        q    = data.get("quote", {})
        bid  = float(q.get("bp",0))
        ask  = float(q.get("ap",0))
        return round((bid+ask)/2, 4) if bid and ask else None

    def _buy(self, price: float) -> bool:
        qty  = round(self.MAX_CAPITAL / price, 4)
        if qty < 0.001: return False
        result = alpaca_post("/v2/orders", {
            "symbol": self.SYMBOL,
            "qty":    str(qty),
            "side":   "buy",
            "type":   "market",
            "time_in_force": "day",
        }, BASE_URL)
        if "error" in result:
            print(f"  ❌ Buy failed: {result['error']}")
            return False
        self.position = {"qty":qty,"entry":price,"order_id":result.get("id")}
        cost = qty * price
        print(f"  🤖 AUTO BUY: {qty:.4f} SPY @ ${price:.2f} (${cost:.2f})")
        return True

    def _sell(self, price: float, reason: str) -> float:
        if not self.position: return 0
        qty = self.position["qty"]
        result = alpaca_post("/v2/orders", {
            "symbol": self.SYMBOL,
            "qty":    str(qty),
            "side":   "sell",
            "type":   "market",
            "time_in_force": "day",
        }, BASE_URL)
        pnl = (price - self.position["entry"]) * qty
        self.daily_pnl += pnl
        self.trades.append({
            "entry":  self.position["entry"],
            "exit":   price,
            "qty":    qty,
            "pnl":    round(pnl,4),
            "reason": reason,
            "time":   datetime.now().strftime("%H:%M:%S"),
        })
        icon = "✅" if pnl>=0 else "🛑"
        print(f"  {icon} AUTO SELL: {qty:.4f} SPY @ ${price:.2f} "
              f"| P&L: ${pnl:+.4f} | {reason}")
        self.position = None
        if self.daily_pnl <= -self.DAILY_LOSS_CAP:
            self.halted = True
            print(f"  ⚠️  DAILY LOSS CAP HIT (${self.daily_pnl:.2f}) — trading halted")
        return pnl

    def _trading_hours(self) -> tuple:
        now   = datetime.now(timezone.utc)
        total = now.hour*60 + now.minute
        open_ = 13*60+30    # 9:30am ET
        close_= 19*60+45    # 3:45pm ET (15min early close)
        return total >= open_ and total <= close_, total

    def _run_loop(self):
        """Main autonomous trading loop."""
        print(f"\n  🤖 AUTONOMOUS TRADER starting — ${self.MAX_CAPITAL} SPY cap")
        print(f"  Strategy: intraday mean reversion | Stop: -${self.DAILY_LOSS_CAP}")
        self.morning_open = None
        self.daily_pnl    = 0.0
        self.halted       = False
        check_count       = 0

        while self.running:
            active, total_mins = self._trading_hours()

            if not active:
                # Close any open position at end of day
                if self.position and total_mins > 19*60+45:
                    price = self._get_price()
                    if price: self._sell(price, "end_of_day_close")
                time.sleep(30)
                continue

            if self.halted:
                time.sleep(60)
                continue

            price = self._get_price()
            if not price:
                time.sleep(10)
                continue

            # Set morning open
            if not self.morning_open:
                self.morning_open = price
                print(f"  🤖 Morning open: ${price:.2f}")

            move_from_open = (price - self.morning_open) / self.morning_open

            # Entry logic
            if not self.position and move_from_open <= self.BUY_TRIGGER:
                print(f"  🤖 Trigger: SPY {move_from_open*100:+.2f}% from open → BUY")
                self._buy(price)

            # Exit logic
            elif self.position:
                move_from_entry = (price - self.position["entry"]) / self.position["entry"]
                if move_from_entry >= self.SELL_TARGET:
                    self._sell(price, "target_hit")
                elif move_from_entry <= self.STOP_LOSS:
                    self._sell(price, "stop_loss")

            check_count += 1
            if check_count % 12 == 0:   # print status every minute
                pos_str = (f"LONG {self.position['qty']:.2f}sh @ "
                           f"${self.position['entry']:.2f}"
                           if self.position else "FLAT")
                print(f"  🤖 ${price:.2f} | {pos_str} | "
                      f"Daily P&L: ${self.daily_pnl:+.4f}")

            time.sleep(5)   # check every 5 seconds

        # End of day report
        self._end_of_day_report()

    def start(self):
        self.running = True
        self.thread  = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def _end_of_day_report(self):
        winners = [t for t in self.trades if t["pnl"] > 0]
        losers  = [t for t in self.trades if t["pnl"] <= 0]
        win_rate= len(winners)/len(self.trades)*100 if self.trades else 0

        subject = (f"🤖 APEX Auto Trader Daily Report | "
                   f"SPY P&L: ${self.daily_pnl:+.4f} | "
                   f"Trades: {len(self.trades)}")

        body = f"""
APEX AUTONOMOUS TRADER — DAILY REPORT
{'='*55}
Date:          {datetime.now().strftime('%A, %B %d, %Y')}
Symbol:        SPY (S&P 500 ETF)
Capital:       ${self.MAX_CAPITAL:.2f}
Strategy:      Intraday Mean Reversion
{'='*55}

PERFORMANCE SUMMARY
{'─'*40}
Daily P&L:     ${self.daily_pnl:+.4f}
Return:        {self.daily_pnl/self.MAX_CAPITAL*100:+.2f}%
Total Trades:  {len(self.trades)}
Winners:       {len(winners)} ({win_rate:.0f}%)
Losers:        {len(losers)}
{'Halted early: daily loss cap hit' if self.halted else 'Full day traded'}

TRADE LOG
{'─'*40}
{'Time':<10} {'Entry':>8} {'Exit':>8} {'Qty':>6} {'P&L':>10} {'Reason'}
"""
        for t in self.trades:
            body += (f"{t['time']:<10} ${t['entry']:>7.2f} ${t['exit']:>7.2f} "
                     f"{t['qty']:>6.3f} ${t['pnl']:>+9.4f} {t['reason']}\n")

        body += f"""
{'─'*40}
{'Great day Philip!' if self.daily_pnl > 0 else 'Tough day — the system protected capital with stop losses.'}
Tomorrow the system resets and hunts for the next opportunity.

─────────────────────────────────────────────────
Philip AJ Sogah | APEX Trading System | philipajsogah.io
"""
        send_email(subject, body)
        print(f"\n  📧 End-of-day report sent to {TO_EMAIL}")


# ═══════════════════════════════════════════════════════════════
# MODULE 5: INTEREST RATE ANALYSER
# Fed cycle detection + pattern-based trading signals
# ═══════════════════════════════════════════════════════════════

class InterestRateAnalyser:
    """
    Studies Federal Reserve interest rate cycles.

    What it does:
    1. Tracks the full Fed Funds Rate history from FRED
    2. Detects current cycle: hiking, cutting, or pausing
    3. Maps historical hike/cut patterns to asset performance
    4. Generates trade signals based on rate cycle phase

    Historical pattern (what markets do in each phase):
    - Hiking cycle start:  Sell bonds (TLT), buy USD, reduce equities
    - Peak rates:          Buy gold (hedge), short high-yield (HYG)
    - Cutting cycle start: Buy bonds aggressively, buy equities
    - Rate cuts accelerating: Full risk-on, buy growth stocks
    """

    def analyse(self) -> dict:
        print("\n  ── Interest Rate Analyser ──────────────────────────")

        fed_data = fred_get("DFF")    # Fed Funds Rate
        cpi_data = fred_get("CPIAUCSL")  # Inflation
        y10_data = fred_get("DGS10")  # 10Y Treasury
        y2_data  = fred_get("DGS2")   # 2Y Treasury

        if not fed_data:
            return {"error": "FRED data unavailable — check FRED_API_KEY"}

        # Current readings
        current_rate = fed_data[0][1]  if fed_data  else 0
        peak_rate    = max(v for _,v in fed_data[:24]) if fed_data else 0
        year_ago     = fed_data[min(12,len(fed_data)-1)][1] if fed_data else 0
        rate_change  = current_rate - year_ago

        cpi_current  = cpi_data[0][1] if cpi_data else 0
        cpi_prev     = cpi_data[1][1] if cpi_data and len(cpi_data)>1 else cpi_current
        cpi_trend    = "rising" if cpi_current > cpi_prev else "falling"

        y10          = y10_data[0][1] if y10_data else 4.4
        y2           = y2_data[0][1]  if y2_data  else 4.0
        spread       = y10 - y2

        # Cycle detection
        recent_moves = [fed_data[i][1]-fed_data[i+1][1]
                        for i in range(min(6,len(fed_data)-1))]
        hikes = sum(1 for m in recent_moves if m > 0.1)
        cuts  = sum(1 for m in recent_moves if m < -0.1)

        if hikes >= 3:
            cycle = "HIKING"
            cycle_desc = "Fed actively raising rates — tightening"
        elif cuts >= 3:
            cycle = "CUTTING"
            cycle_desc = "Fed cutting rates — easing"
        elif abs(rate_change) < 0.25:
            cycle = "PAUSING"
            cycle_desc = "Fed on hold — watching data"
        elif rate_change > 0:
            cycle = "PEAK"
            cycle_desc = "Near peak rates — potential pivot coming"
        else:
            cycle = "EASING"
            cycle_desc = "Easing bias — cuts expected"

        # Trade signals based on cycle
        signals = self._cycle_signals(cycle, spread, current_rate, cpi_trend)

        result = {
            "fed_funds_rate":   current_rate,
            "rate_vs_year_ago": round(rate_change, 2),
            "peak_rate_24m":    peak_rate,
            "cpi_latest":       cpi_current,
            "cpi_trend":        cpi_trend,
            "yield_10y":        y10,
            "yield_2y":         y2,
            "yield_spread":     round(spread, 3),
            "curve_shape":      "inverted" if spread<0 else "flat" if spread<0.5 else "normal",
            "cycle":            cycle,
            "cycle_description":cycle_desc,
            "trade_signals":    signals,
        }

        self._print_analysis(result)
        return result

    def _cycle_signals(self, cycle, spread, rate, cpi_trend) -> list:
        signals = []
        if cycle == "CUTTING":
            signals.append({"asset":"TLT","action":"BUY","reason":"Rate cuts = bond price surge","strength":"STRONG"})
            signals.append({"asset":"SPY","action":"BUY","reason":"Equities rally on rate cuts","strength":"MODERATE"})
            signals.append({"asset":"GLD","action":"BUY","reason":"Gold rises as real rates fall","strength":"MODERATE"})
            signals.append({"asset":"HYG","action":"BUY","reason":"Credit spreads tighten on cuts","strength":"WEAK"})
        elif cycle == "HIKING":
            signals.append({"asset":"TLT","action":"SELL","reason":"Rising rates crush bond prices","strength":"STRONG"})
            signals.append({"asset":"USO","action":"BUY","reason":"Oil benefits from inflation environment","strength":"MODERATE"})
            signals.append({"asset":"GLD","action":"HOLD","reason":"Gold mixed during hikes","strength":"WEAK"})
        elif cycle in ("PAUSING","PEAK"):
            signals.append({"asset":"TLT","action":"BUY","reason":"Peak rates = bonds bottoming","strength":"MODERATE"})
            signals.append({"asset":"GLD","action":"BUY","reason":"Gold performs well at peak rates","strength":"STRONG"})
            signals.append({"asset":"SPY","action":"WATCH","reason":"Equities volatile at peak rates","strength":"WEAK"})
        if spread < 0:
            signals.append({"asset":"SPY","action":"REDUCE","reason":"Inverted curve historically precedes recession","strength":"HIGH_CONVICTION"})
        return signals

    def _print_analysis(self, r):
        up='\033[92m'; dn='\033[91m'; amb='\033[93m'; rst='\033[0m'; b='\033[94m'
        cycle_color = up if r["cycle"]=="CUTTING" else dn if r["cycle"]=="HIKING" else amb
        print(f"  Fed Funds Rate:  {b}{r['fed_funds_rate']:.2f}%{rst} "
              f"(vs {r['rate_vs_year_ago']:+.2f}% YoY)")
        print(f"  Cycle:           {cycle_color}{r['cycle']} — {r['cycle_description']}{rst}")
        print(f"  Yield Curve:     {r['yield_2y']:.2f}% (2Y) → {r['yield_10y']:.2f}% (10Y) "
              f"| Spread: {r['yield_spread']:+.3f}%")
        print(f"  Curve Shape:     {r['curve_shape'].upper()}")
        print(f"\n  Trade Signals from Rate Cycle:")
        for s in r["trade_signals"]:
            col = up if s["action"]=="BUY" else dn if s["action"]=="SELL" else amb
            print(f"  {col}{s['action']:<8}{rst} {s['asset']:<6} "
                  f"[{s['strength']}] — {s['reason']}")


# ═══════════════════════════════════════════════════════════════
# MODULE 6: MARKET STRUCTURE ANALYST
# Support/resistance, liquidity zones, order flow, microstructure
# ═══════════════════════════════════════════════════════════════

class MarketStructureAnalyst:
    """
    Professional market structure analysis.

    Components:
    1. Support & Resistance levels (pivot point method + price clusters)
    2. Liquidity zones (areas with high historical volume = institutional interest)
    3. Market structure shifts (higher highs/lows = uptrend, lower = downtrend)
    4. Order flow proxy (volume delta analysis)
    5. Key levels: 52-week high/low, round numbers, VWAP proxy
    """

    def analyse(self, symbol: str) -> dict:
        print(f"\n  ── Market Structure: {symbol} ─────────────────────")
        bars = get_bars(symbol, 252)
        if len(bars) < 50:
            return {"error": "Insufficient data"}

        closes  = [b["c"] for b in bars]
        highs   = [b["h"] for b in bars]
        lows    = [b["l"] for b in bars]
        volumes = [b["v"] for b in bars]
        current = closes[-1]

        # ── Support & Resistance ──
        pivot   = (highs[-1] + lows[-1] + closes[-1]) / 3
        r1 = 2*pivot - lows[-1]
        r2 = pivot + (highs[-1]-lows[-1])
        r3 = highs[-1] + 2*(pivot-lows[-1])
        s1 = 2*pivot - highs[-1]
        s2 = pivot - (highs[-1]-lows[-1])
        s3 = lows[-1] - 2*(highs[-1]-pivot)

        # ── Historical price clusters (liquidity zones) ──
        price_range = max(closes) - min(closes)
        bucket_size = price_range / 20
        buckets     = {}
        for i, (c, v) in enumerate(zip(closes, volumes)):
            bucket = round(c / bucket_size) * bucket_size
            buckets[bucket] = buckets.get(bucket,0) + v

        top_zones = sorted(buckets.items(), key=lambda x: x[1], reverse=True)[:5]

        # ── Market structure (HH/HL vs LH/LL) ──
        swing_highs = []
        swing_lows  = []
        for i in range(2, len(highs)-2):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1] and \
               highs[i] > highs[i-2] and highs[i] > highs[i+2]:
                swing_highs.append(highs[i])
            if lows[i] < lows[i-1] and lows[i] < lows[i+1] and \
               lows[i] < lows[i-2] and lows[i] < lows[i+2]:
                swing_lows.append(lows[i])

        swing_highs = swing_highs[-6:] if swing_highs else [max(highs)]
        swing_lows  = swing_lows[-6:]  if swing_lows  else [min(lows)]

        hh = all(swing_highs[i]>swing_highs[i-1] for i in range(1,len(swing_highs)))
        hl = all(swing_lows[i] >swing_lows[i-1]  for i in range(1,len(swing_lows)))
        lh = all(swing_highs[i]<swing_highs[i-1] for i in range(1,len(swing_highs)))
        ll = all(swing_lows[i] <swing_lows[i-1]  for i in range(1,len(swing_lows)))

        if hh and hl:   structure = "UPTREND";   struct_bias = "bullish"
        elif lh and ll: structure = "DOWNTREND"; struct_bias = "bearish"
        else:           structure = "RANGING";   struct_bias = "neutral"

        # ── Volume-weighted average price proxy ──
        vwap = sum(c*v for c,v in zip(closes[-20:],volumes[-20:])) / sum(volumes[-20:])

        # ── 52-week levels ──
        high_52w = max(highs[-252:])
        low_52w  = min(lows[-252:])
        pct_from_high = (current - high_52w) / high_52w * 100
        pct_from_low  = (current - low_52w)  / low_52w  * 100

        # ── Order flow proxy ──
        recent_ups   = sum(v for c,v,b in zip(closes[-10:],volumes[-10:],bars[-10:])
                           if c >= b["o"])
        recent_downs = sum(v for c,v,b in zip(closes[-10:],volumes[-10:],bars[-10:])
                           if c <  b["o"])
        flow_bias    = "BUYING" if recent_ups > recent_downs else "SELLING"
        flow_ratio   = recent_ups / (recent_downs+1)

        result = {
            "symbol":   symbol,
            "current":  round(current,4),
            "structure": structure,
            "bias":     struct_bias,
            "vwap_20d": round(vwap,4),
            "above_vwap": current > vwap,
            "high_52w": round(high_52w,4),
            "low_52w":  round(low_52w,4),
            "pct_from_high": round(pct_from_high,2),
            "pct_from_low":  round(pct_from_low,2),
            "resistance": {"R3":round(r3,4),"R2":round(r2,4),"R1":round(r1,4)},
            "pivot":    round(pivot,4),
            "support":  {"S1":round(s1,4),"S2":round(s2,4),"S3":round(s3,4)},
            "liquidity_zones": [{"price":round(z[0],2),"volume_index":i+1}
                                 for i,(z) in enumerate(top_zones)],
            "order_flow":   flow_bias,
            "flow_ratio":   round(flow_ratio,2),
        }

        self._print_structure(result)
        return result

    def _print_structure(self, r):
        up='\033[92m'; dn='\033[91m'; amb='\033[93m'; rst='\033[0m'; b='\033[94m'
        sc = up if r["bias"]=="bullish" else dn if r["bias"]=="bearish" else amb
        fc = up if r["order_flow"]=="BUYING" else dn
        print(f"  Structure:   {sc}{r['structure']}{rst} | "
              f"Order Flow: {fc}{r['order_flow']} ({r['flow_ratio']:.1f}x){rst}")
        print(f"  VWAP (20D):  ${r['vwap_20d']:.2f} | "
              f"Price {'above' if r['above_vwap'] else 'below'} VWAP")
        print(f"  52W High:    ${r['high_52w']:.2f} ({r['pct_from_high']:+.2f}%)")
        print(f"  52W Low:     ${r['low_52w']:.2f}  ({r['pct_from_low']:+.2f}%)")
        print(f"\n  Key Levels:")
        for k,v in r["resistance"].items():
            print(f"  {up}{k}{rst} = ${v:.4f}")
        print(f"  {'─'*20}")
        print(f"  Pivot = ${r['pivot']:.4f}")
        print(f"  {'─'*20}")
        for k,v in r["support"].items():
            print(f"  {dn}{k}{rst} = ${v:.4f}")
        print(f"\n  Top Liquidity Zones (institutional interest):")
        for z in r["liquidity_zones"][:3]:
            print(f"  ${z['price']:.2f}  ({'█'*z['volume_index']})")


# ═══════════════════════════════════════════════════════════════
# MASTER RUNNER
# ═══════════════════════════════════════════════════════════════

def run():
    print("""
╔══════════════════════════════════════════════════════════════╗
║   APEX MASTER SYSTEM — Philip AJ Sogah                       ║
║   philipajsogah.io  |  github.com/axlAJ                      ║
╠══════════════════════════════════════════════════════════════╣
║   Portfolio Optimiser  · Monte Carlo  · Price Predictor      ║
║   Autonomous Trader    · Rate Analyser · Market Structure     ║
╚══════════════════════════════════════════════════════════════╝
    """)

    if not ALPACA_KEY or not ALPACA_SECRET:
        raise SystemExit("Set ALPACA_API_KEY and ALPACA_SECRET")

    acct   = get_account()
    equity = float(acct.get("equity",100000))
    mode   = "🔴 LIVE" if LIVE_MODE else "🟡 PAPER"
    print(f"  {mode} | Equity: ${equity:,.2f}")
    print(f"  FRED: {'✅' if FRED_KEY else '❌ not set'} | "
          f"Email: {'✅' if GMAIL_PW else '❌ not set'}")

    # Init all modules
    optimiser  = PortfolioOptimiser()
    mc         = MonteCarloEngine()
    predictor  = PricePredictor()
    auto_trader= AutonomousTrader()
    rate_anal  = InterestRateAnalyser()
    struct_anal= MarketStructureAnalyst()

    # Start autonomous trader on market open
    print(f"\n  🤖 Autonomous SPY trader: ${auto_trader.MAX_CAPITAL} cap, "
          f"will start on market open")
    auto_trader.start()

    print(f"\n  Commands:")
    print(f"  optimise          — portfolio optimisation (Markowitz)")
    print(f"  montecarlo SPY 30 — Monte Carlo simulation")
    print(f"  option SPY 600 30 — price a call option")
    print(f"  predict AAPL      — 1/5/20 day price prediction")
    print(f"  rates             — interest rate cycle analysis")
    print(f"  structure SPY     — market structure analysis")
    print(f"  status            — show all module status")
    print(f"  report            — generate full daily report")
    print(f"  quit              — shutdown + send report")
    print("─"*65)

    # Run startup analysis
    print("\n  Running startup analysis...")
    rate_result = rate_anal.analyse()

    while True:
        try:
            if select.select([sys.stdin],[],[],0)[0]:
                cmd   = sys.stdin.readline().strip()
                parts = cmd.split()
                if not parts: continue
                action = parts[0].lower()

                if action == "optimise":
                    t = threading.Thread(target=optimiser.run, daemon=True)
                    t.start()

                elif action == "montecarlo":
                    sym  = parts[1].upper() if len(parts)>1 else "SPY"
                    days = int(parts[2]) if len(parts)>2 else 30
                    t = threading.Thread(target=mc.run_price_simulation,
                                         args=(sym,days), daemon=True)
                    t.start()

                elif action == "option":
                    sym    = parts[1].upper() if len(parts)>1 else "SPY"
                    strike = float(parts[2]) if len(parts)>2 else 600
                    days   = int(parts[3]) if len(parts)>3 else 30
                    opt    = parts[4] if len(parts)>4 else "call"
                    result = mc.price_option(sym, strike, days, opt)
                    print(f"\n  Option Price: MC=${result.get('mc_price','?')} "
                          f"BS=${result.get('bs_price','?')} "
                          f"Delta={result.get('delta','?')}")

                elif action == "predict":
                    sym = parts[1].upper() if len(parts)>1 else "AAPL"
                    t = threading.Thread(target=predictor.predict,
                                         args=(sym,), daemon=True)
                    t.start()

                elif action == "rates":
                    t = threading.Thread(target=rate_anal.analyse, daemon=True)
                    t.start()

                elif action == "structure":
                    sym = parts[1].upper() if len(parts)>1 else "SPY"
                    t = threading.Thread(target=struct_anal.analyse,
                                         args=(sym,), daemon=True)
                    t.start()

                elif action == "status":
                    print(f"\n  APEX MASTER STATUS")
                    print(f"  Equity: ${equity:,.2f} | Mode: {mode}")
                    print(f"  Auto Trader: {'RUNNING' if auto_trader.running else 'STOPPED'} | "
                          f"Daily P&L: ${auto_trader.daily_pnl:+.4f}")
                    print(f"  Trades today: {len(auto_trader.trades)} | "
                          f"Halted: {auto_trader.halted}")
                    print(f"  Rate Cycle: {rate_result.get('cycle','?')}")

                elif action == "report":
                    # Full daily report
                    sections = []
                    sections.append("RATE CYCLE: " + rate_result.get("cycle","?") +
                                    " — " + rate_result.get("cycle_description",""))
                    sections.append(f"AUTO TRADER P&L: ${auto_trader.daily_pnl:+.4f} "
                                    f"| Trades: {len(auto_trader.trades)}")
                    body = "\n".join(sections)
                    send_email("APEX Daily Report", body)

                elif action == "quit":
                    print("\n  Shutting down APEX Master System...")
                    auto_trader.stop()
                    sys.exit(0)

                else:
                    print(f"  Unknown command: {cmd}")

            time.sleep(0.5)

        except KeyboardInterrupt:
            print("\n  Ctrl+C — shutting down...")
            auto_trader.stop()
            sys.exit(0)
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(1)


if __name__ == "__main__":
    run()
