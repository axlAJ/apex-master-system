# APEX Trading System
### The Complete Institutional Quantitative Trading Stack

**Philip AJ Sogah** · [philipajsogah.io](https://philipajsogah.io) · [LinkedIn](https://linkedin.com/in/philip-aj-sogah-a1558633b) · [GitHub](https://github.com/axlAJ)

---

## Overview

APEX is a complete institutional-grade quantitative trading system built entirely in Python — no external ML libraries, no black boxes, no shortcuts. It covers every asset class, runs adaptive algorithms that breed new strategies when old ones fail, and emails live trade alerts to your phone.

This is what quant hedge funds spend hundreds of millions building. APEX does it in pure Python.

```
╔══════════════════════════════════════════════════════════════╗
║   APEX TRADING SYSTEM — Philip AJ Sogah                      ║
╠══════════════════════════════════════════════════════════════╣
║   Stocks · Gold · Oil · Crypto · Forex · Options             ║
║   20+ Modules · Adaptive Algorithms · Live Email Alerts      ║
╚══════════════════════════════════════════════════════════════╝
```

---

## System Architecture

```
apex_launcher.py          ← Master launcher — starts all systems, market countdown
├── apex_master.py        ← Core signal scanner + autonomous SPY trader
│   ├── apex_market_feed.py     — Alpaca + Yahoo Finance + FRED unified feed
│   ├── apex_signal_engine.py   — 5 edge strategies, composite scoring
│   ├── apex_risk_executor.py   — Risk manager + Alpaca trade executor
│   └── apex_email_alerts.py    — Email notifications to philipaxl7@gmail.com
├── apex_forex.py         ← Adaptive forex system (8 pairs, 8 algorithms)
├── apex_quant.py         ← 12 institutional quant modules
├── apex_master.py        ← 6-module master system
├── apex_charts.py        ← Terminal ASCII charts (candlestick, OBV, MTF, RSI)
├── apex_dashboard.html   ← Live web dashboard
└── apex_dashboard_server.py  ← Flask dashboard server
```

---

## Module Index

### Core Signal Engine (apex_main.py)

Five proprietary edge strategies fused into a composite score (-100 to +100):

| Strategy | Weight | What it detects |
|---|---|---|
| Ghost Pattern Detection | 25% | Institutional accumulation before breakouts |
| Multi-Timeframe Confluence | 25% | Daily + weekly + monthly alignment |
| Options Flow Analysis | 15% | Unusual put/call sweeps — whale positioning |
| Sentiment Analysis | 15% | News shock before price reacts |
| Forensics Edge | 20% | Manipulation → mean reversion (your unique edge) |

---

### APEX Master System (apex_master.py) — 6 Modules

**Module 1: Portfolio Optimiser — Markowitz Efficient Frontier**
Runs 10,000 random portfolio simulations to find the allocation that maximises the Sharpe ratio. Built on Harry Markowitz's Nobel Prize-winning Modern Portfolio Theory.
```
OPTIMAL PORTFOLIO (Max Sharpe = 2.032)
USO    36.61%  ████████  Expected Return: 49.03%/year
GLD    33.84%  ████████  Sharpe Ratio:    2.032
NVDA   15.61%  ████      vs Equal Weight: +39.8% improvement
```

**Module 2: Monte Carlo Engine — 10,000 Simulations**
Stochastic price path simulation using geometric Brownian motion. Options pricing with Black-Scholes validation. VaR 95/99, CVaR, probability of profit.

**Module 3: Price Predictor — Multi-Horizon Forecasting**
Pure-math prediction model using RSI, MACD, momentum, volume trend, Bollinger deviation, and volatility regime. Outputs 1-day, 5-day, 20-day forecasts with confidence scores.

**Module 4: Autonomous Trader — $100 SPY Live Test**
Intraday mean-reversion strategy. Buys SPY dips, takes profit at +0.5%, stops at -0.5%. Hard cap $100, daily loss limit $25. Emails full P&L report at market close.

**Module 5: Interest Rate Analyser — Fed Cycle Intelligence**
Live Federal Reserve data from FRED API. Detects hiking/pausing/cutting cycle. Generates asset-specific trade signals based on historical rate patterns.

**Module 6: Market Structure Analyst**
Pivot points (R1/R2/R3, S1/S2/S3), 52-week levels, VWAP, liquidity zones, order flow bias, market structure classification (uptrend/downtrend/ranging).

---

### APEX Forex System (apex_forex.py)

**8 Currency Pairs:** EUR/USD, GBP/USD, USD/JPY, USD/CHF, AUD/USD, USD/CAD, NZD/USD, EUR/GBP

**8 Competing Algorithms — adaptive rotation:**

| Algorithm | Inspired by | What it does |
|---|---|---|
| Rate Differential | George Soros | Trade central bank divergence — the Soros model |
| Currency Strength Breakout | — | Buy strongest vs sell weakest currency |
| Mean Reversion | — | Fade extreme moves, snap-back trades |
| Session Breakout | — | London/NY overlap momentum |
| Macro Shock Reversal | — | Fade news overreactions |
| Correlation Divergence | — | Trade when correlated pairs separate |
| Ghost Pattern Forex | — | Institutional footprints in currency markets |
| Trend Turtle System | Richard Dennis | 20-day breakout — the original turtle strategy |

**Adaptive Rotation:** When any algorithm's win rate drops below 55%, the system automatically rotates to the best-performing algorithm and emails you.

**Additional Features:**
- Currency strength scanner — ranks all 8 currencies by strength score
- Interest rate differential table — live central bank rates from FRED
- Session analysis — Sydney, Tokyo, London, New York session detection
- Correlation matrix — prevents holding correlated pairs simultaneously

---

### APEX Quant Engine (apex_quant.py) — 12 Institutional Modules

| # | Module | Inspired by |
|---|---|---|
| 1 | **Genetic Algorithm Engine** | Renaissance Technologies — breeds new strategies when all 8 fail |
| 2 | **Backtesting Engine** | Walk-forward 2-year historical testing, Sharpe/Sortino/MaxDD |
| 3 | **ML Price Model** | Two Sigma — pure-math neural network, trains on trade history |
| 4 | **Options Greeks Dashboard** | Goldman Sachs — Delta, Gamma, Theta, Vega, Rho live |
| 5 | **Volatility Surface Model** | JP Morgan — implied vol across all strikes and expiries |
| 6 | **Kelly Criterion Sizer** | Ed Thorp — mathematically optimal position sizing |
| 7 | **Fama-French Factor Model** | Nobel Prize — 5-factor return decomposition |
| 8 | **Statistical Arbitrage** | Citadel/DE Shaw — cointegrated pairs spread trading |
| 9 | **Regime Detection** | Winton Group — Hurst exponent + ADX market classification |
| 10 | **Risk Parity Portfolio** | Ray Dalio/Bridgewater — equal risk contribution allocation |
| 11 | **Drawdown Protection** | Every prop firm — auto-scales size on 4-tier drawdown ladder |
| 12 | **P&L Attribution** | Bloomberg PORT — which signals/algos/regimes are profitable |

---

### Genetic Algorithm Engine — The Crown Jewel

When all 8 forex algorithms drop below 55% win rate simultaneously, the genetic engine breeds a new one:

1. Generate 100 random rule combinations (chromosomes)
2. Backtest each on 1 year of historical data
3. Select top 20 by Sharpe ratio — survival of the fittest
4. Cross-breed: combine rules from two parent strategies
5. Mutate: randomly tweak 10% of rules
6. Repeat 50 generations
7. Champion algorithm emailed to Philip automatically

```
Gen  0/50 | Best Sharpe: +0.8821 | Pop avg: +0.2341
Gen 10/50 | Best Sharpe: +1.4432 | Pop avg: +0.8901
Gen 30/50 | Best Sharpe: +2.1089 | Pop avg: +1.3421
Gen 50/50 | Best Sharpe: +2.8834 | Pop avg: +1.9012

CHAMPION ALGORITHM EVOLVED — Fitness: +2.8834
rsi_buy:       32.4
ma_fast:       7
ma_slow:       23
stop_pct:      0.018
target_pct:    0.045
```

---

### Terminal Charts (apex_charts.py)

Full ASCII trading charts rendered in your terminal:
- Candlestick chart with MA9 and MA20
- Volume bars with OBV ACCUMULATING/DISTRIBUTING
- Multi-timeframe analysis (5D, 20D, 60D) with confluence detection
- RSI with overbought/oversold zones
- Support & Resistance (R1/R2/S1/S2)

```bash
python3 apex_charts.py SPY
python3 apex_charts.py EURUSD
python3 apex_charts.py GLD
```

---

### Live Web Dashboard (apex_dashboard.html)

Browser-based chart dashboard at `http://localhost:5001`:
- Live candlestick charts with ghost pattern markers (👻)
- Volume + OBV overlay
- Multi-timeframe side-by-side view
- Real-time P&L chart
- Signal strength bars for all 5 strategies
- Works on phone at `http://YOUR_IP:5001`

---

## Asset Coverage

| Asset Class | Symbols | Data Source |
|---|---|---|
| US Equities | AAPL, NVDA, TSLA, SPY, QQQ | Alpaca Markets |
| Gold & Oil | GLD, GDX, USO | Alpaca / Yahoo Finance |
| Bonds | TLT, IEF, HYG | Alpaca / Yahoo Finance |
| Crypto | BTC/USD, ETH/USD | Alpaca Crypto |
| Forex | EUR/USD, GBP/USD, USD/JPY, USD/CHF, AUD/USD, USD/CAD, NZD/USD, EUR/GBP | Alpaca / Yahoo Finance |
| Macro | Fed Funds, CPI, Yield Curve, VIX | FRED API |

---

## Setup

### Requirements
```bash
/usr/bin/python3 -m pip install flask flask-cors
```
No other external dependencies. All data via built-in `urllib`.

### Environment Variables
```bash
export ALPACA_API_KEY=your_key
export ALPACA_SECRET=your_secret
export FRED_API_KEY=your_fred_key
export GMAIL_ADDRESS=your_email
export GMAIL_APP_PASSWORD=your_app_password
export ALPACA_LIVE=true   # real money (default: paper)
```

### Run Everything — One Command
```bash
cd apex_trader
/usr/bin/python3 apex_launcher.py
```

The launcher starts all systems, shows a live countdown to market open, sends a morning briefing email at 9:30am ET, and shuts down everything cleanly on Ctrl+C.

### Run Individual Systems
```bash
/usr/bin/python3 apex_master.py    # signal scanner + autonomous trader
/usr/bin/python3 apex_forex.py     # forex system
/usr/bin/python3 apex_quant.py     # 12 quant modules
/usr/bin/python3 apex_charts.py SPY  # terminal charts
```

---

## Commands Reference

### apex_launcher.py
Starts everything. No commands needed — just run it.

### apex_master.py
```
optimise              — Portfolio optimisation (Markowitz, 10,000 simulations)
montecarlo SPY 30     — Monte Carlo simulation
predict AAPL          — 1/5/20 day price prediction
rates                 — Interest rate cycle analysis
structure SPY         — Market structure analysis
status                — All module status
quit                  — Shutdown + send final report
```

### apex_forex.py
```
strength              — Currency strength rankings
scan                  — Scan all 8 pairs
rates                 — Central bank rate differentials
session               — Current session analysis
correlation           — Correlation matrix
algo                  — Algorithm performance dashboard
predict GBPUSD        — All 8 algorithms predict GBP/USD
charts EURUSD         — Candlestick chart
```

### apex_quant.py
```
genetic               — Breed new algorithm (50 generations)
backtest SPY          — 2-year walk-forward backtest
ml AAPL               — ML price prediction
greeks SPY 600 30     — Options greeks
surface SPY           — Volatility surface
kelly                 — Kelly criterion position sizes
factors SPY           — Fama-French 5-factor model
arb                   — Statistical arbitrage scanner
regime SPY            — Market regime detection
riskparity            — Risk parity portfolio
drawdown              — Drawdown protection status
attribution           — P&L attribution breakdown
full SPY              — Run all 12 modules
```

---

## Live Results

```
Currency Strength (live):
  1. USD  +0.6550  STRONG  ████
  8. NZD  -1.4166  WEAK    ████ (red)
  Best Trade: BUY USD vs SELL NZD

Rate Differentials:
  BUY  USD/JPY  +4.230%  [STRONG] — carry trade
  BUY  USD/CHF  +2.580%  [MODERATE]
  SELL EUR/GBP  -1.750%  [MODERATE]

Regime Detection — SPY:
  TRENDING (Hurst: 0.972, ADX: 30.7)
  Strategy: momentum, trail stops

Risk Parity Portfolio:
  TLT  35.43%  (lowest vol — bonds)
  SPY  21.44%
  Expected Return: +18.43%/year  Sharpe: 1.181
```

---

## Risk Disclosure

Built for research and educational purposes. Trading involves substantial risk of loss. The autonomous trader uses real capital — only deploy what you can afford to lose entirely. All hard risk limits are non-negotiable and cannot be overridden at runtime.

---

## Related Projects

| Project | Description |
|---|---|
| [AI Market Forensics Engine](https://github.com/axlAJ/ai-market-forensics-engine) | Detects market manipulation — powers the Forensics Edge in APEX |
| [Bond Trading Platform](https://github.com/axlAJ/bond-trading-platform) | Live yield curve analysis — powers the rate module |
| [Property Management Platform](https://github.com/axlAJ/property-management-platform) | 25-unit AI property system, 6 AI models |

---

## Author

**Philip AJ Sogah**
AI Innovator · FinTech Engineer · Quantitative Systems Developer
Norwich University, Computer Science — May 2026

[philipajsogah.io](https://philipajsogah.io) · [LinkedIn](https://linkedin.com/in/philip-aj-sogah-a1558633b) · philipaxl7@gmail.com

---

*Built in pure Python. No shortcuts. No black boxes. No compromises.*


