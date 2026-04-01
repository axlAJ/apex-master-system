# APEX Master System
### Institutional-Grade Quantitative Trading Platform

**Philip AJ Sogah** · [philipajsogah.io](https://philipajsogah.io) · [LinkedIn](https://linkedin.com/in/philip-aj-sogah-a1558633b) · [GitHub](https://github.com/axlAJ)

---

## Overview

APEX is a full-stack quantitative trading system built from scratch in Python — no external ML libraries, no black boxes. Six institutional-grade modules working together to analyse markets, optimise portfolios, simulate risk, predict prices, and execute trades autonomously.

This is the kind of system that quant hedge funds spend millions building. APEX does it in one file.

```
╔══════════════════════════════════════════════════════════════╗
║   APEX MASTER SYSTEM — Philip AJ Sogah                       ║
╠══════════════════════════════════════════════════════════════╣
║   Portfolio Optimiser  · Monte Carlo  · Price Predictor      ║
║   Autonomous Trader    · Rate Analyser · Market Structure     ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Six Core Modules

### 1. Portfolio Optimiser — Markowitz Efficient Frontier
Runs 10,000 random portfolio simulations to find the allocation that maximises the Sharpe ratio across your holdings. Based on Harry Markowitz's Modern Portfolio Theory — the framework that won the Nobel Prize in Economics in 1990.

- Builds the full covariance matrix from 252 days of historical returns
- Simulates 10,000 random weight combinations
- Identifies the efficient frontier — optimal return per unit of risk
- Compares against equal-weight benchmark
- Output: exact allocation percentages with expected annual return, volatility, and Sharpe ratio

**Sample Output:**
```
OPTIMAL PORTFOLIO (Max Sharpe = 2.032)
USO    36.61%  ████████████
GLD    33.84%  ████████████
NVDA   15.61%  █████
TSLA    5.76%  ██
AAPL    3.99%  █
QQQ     2.45%
SPY     1.73%

Expected Return:   49.03% / year
Expected Vol:      21.82% / year
Sharpe Ratio:      2.032
vs Equal Weight:   1.453 (+39.8% improvement)
```

---

### 2. Monte Carlo Engine — 10,000 Simulations
Runs 10,000 stochastic price path simulations using geometric Brownian motion calibrated to historical volatility and drift. Used for options pricing, portfolio risk scenarios, and probability analysis.

- Price path simulation for any symbol and time horizon
- Options pricing via Monte Carlo + Black-Scholes validation
- Greeks calculation: Delta, Theta
- Value at Risk (VaR 95% and 99%)
- Conditional VaR (CVaR) — expected loss in worst scenarios
- Probability of profit calculation

**Sample Output:**
```
Monte Carlo: SPY (10,000 simulations, 30 days)
Current Price:    $654.91
Expected (30d):   $666.40  (+1.75%)
Bull Case (75%):  $694.93
Bear Case (25%):  $636.22
VaR 95%:          $597.42  (worst 5% outcome)
VaR 99%:          $571.45  (worst 1% outcome)
Prob of Profit:   59.1%
Annual Vol:       18.9%
```

---

### 3. Price Predictor — Multi-Horizon Forecasting
Machine learning-style price prediction without external ML libraries. Uses a weighted feature scoring model trained on technical indicators and macro data to forecast 1-day, 5-day, and 20-day price targets.

**Features used:**
- Momentum (5D, 10D, 20D)
- RSI (Relative Strength Index) — overbought/oversold detection
- MACD signal line crossover
- Volume trend confirmation
- Deviation from 20-day moving average (mean reversion input)
- Historical volatility regime
- Support/resistance proximity
- Range position within recent high/low

**Sample Output:**
```
Price Predictor: AAPL
Current: $254.69 | RSI=42.4 | Vol=19.9% | Mom5D=+0.71%
────────────────────────────────────────────────────
1d   DOWN  Target: $229.37  (-9.94%)  Conf: 85%
5d   DOWN  Target: $229.37  (-9.94%)  Conf: 85%
20d  DOWN  Target: $229.37  (-9.94%)  Conf: 85%
```

---

### 4. Autonomous Trader — $100 SPY Live Test
Fully autonomous intraday mean-reversion strategy on SPY (S&P 500 ETF). Executes trades without human approval, manages its own risk, and emails a full P&L report at end of day.

**Strategy: Intraday Mean Reversion**
- Monitors SPY from market open (9:30am ET)
- Buys when SPY drops 0.3% from morning open (oversold intraday)
- Sells when SPY recovers to +0.5% from entry (take profit)
- Hard stop at -0.5% from entry (stop loss)
- Force-closes all positions at 3:45pm ET
- Halts all trading if daily loss exceeds $25

**Hard Risk Limits (non-negotiable):**
```
Max capital:      $100
Max daily loss:   $25 (auto-halt)
Stop loss:        -0.5% per trade
Take profit:      +0.5% per trade
Force close:      3:45pm ET
```

**End-of-day email report includes:**
- Full trade log with entry/exit times and prices
- Win rate, average win, average loss
- Daily P&L and return percentage
- Capital at risk summary

---

### 5. Interest Rate Analyser — Fed Cycle Intelligence
Studies the Federal Reserve interest rate cycle using live FRED (Federal Reserve Economic Data) API data. Detects the current macro phase and generates asset-specific trade signals based on historical patterns.

**Data sources:**
- Fed Funds Rate (DFF) — live from FRED
- CPI inflation (CPIAUCSL)
- 10-Year Treasury Yield (DGS10)
- 2-Year Treasury Yield (DGS2)

**Cycle detection:**
```
HIKING  → Sell bonds, buy oil, avoid growth
PEAK    → Buy gold (strong), buy TLT (moderate), watch equities
PAUSING → Monitor for pivot signals
CUTTING → Buy bonds aggressively, buy equities, buy growth
```

**Sample Output (live):**
```
Fed Funds Rate:  3.64% (vs +0.00% YoY)
Cycle:           PAUSING — Fed on hold, watching data
Yield Curve:     3.82% (2Y) → 4.35% (10Y) | Spread: +0.530%
Curve Shape:     NORMAL

Trade Signals from Rate Cycle:
BUY   TLT  [MODERATE] — Peak rates = bonds bottoming
BUY   GLD  [STRONG]   — Gold performs well at peak rates
WATCH SPY  [WEAK]     — Equities volatile at peak rates
```

---

### 6. Market Structure Analyst — Institutional Price Analysis
Professional-grade market structure analysis using pivot point methodology, volume cluster analysis, swing high/low detection, and order flow proxies.

**Components:**
- Pivot points: R1/R2/R3 resistance, S1/S2/S3 support
- 52-week high/low with percentage distance
- VWAP (Volume-Weighted Average Price) 20-day proxy
- Liquidity zones — price levels with highest historical volume (institutional interest)
- Market structure classification: Uptrend (HH/HL), Downtrend (LH/LL), Ranging
- Order flow bias — volume delta analysis

**Sample Output:**
```
Market Structure: SPY
Structure:   RANGING | Order Flow: SELLING (0.6x)
VWAP (20D):  $659.21 | Price below VWAP
52W High:    $697.84 (-6.16%)
52W Low:     $481.80 (+35.91%)

Key Levels:
R3 = $663.42
R2 = $660.97
R1 = $657.90
──────────────
Pivot = $655.45
──────────────
S1 = $652.38
S2 = $649.93
S3 = $646.86

Top Liquidity Zones (institutional interest):
$686.58  █
$666.68  ██
$676.63  ███
```

---

## Asset Coverage

| Asset Class | Symbols | Data Source |
|---|---|---|
| US Equities | AAPL, NVDA, TSLA, SPY, QQQ | Alpaca Markets |
| Gold | GLD, GDX | Alpaca / Yahoo Finance |
| Oil | USO | Alpaca / Yahoo Finance |
| Crypto | BTC/USD, ETH/USD | Alpaca Crypto |
| Forex | EUR/USD, GBP/USD | Yahoo Finance |
| Macro | Fed Funds, CPI, Yields, VIX | FRED API |

---

## Architecture

```
apex_master.py              ← Master system (all 6 modules)
apex_main.py                ← APEX signal scanner (12 symbols, 5 edges)
apex_signal_engine.py       ← Ghost patterns, MTF, options flow, sentiment, forensics
apex_market_feed.py         ← Unified data feed (Alpaca + Yahoo + FRED)
apex_risk_executor.py       ← Risk manager + Alpaca trade executor
apex_email_alerts.py        ← Email notification system
apex_dashboard_server.py    ← Flask web dashboard server
apex_dashboard.html         ← Live chart dashboard (candlesticks, OBV, MTF, P&L)
```

---

## Signal Engine — 5 Edge Strategies

The signal engine (used in `apex_main.py`) runs five independent strategies and fuses them into a composite score from -100 (strong sell) to +100 (strong buy).

### Ghost Pattern Detection (weight: 25%)
Detects institutional accumulation and distribution before large price moves. Signals:
- OBV divergence (volume accumulating while price flat = ghost buying)
- Wyckoff springs and upthrusts
- Coiling patterns (narrowing range = energy building)
- Volume pattern asymmetry (up-day volume vs down-day volume ratio)

### Multi-Timeframe Confluence (weight: 25%)
Highest probability signals occur when daily, weekly, and monthly charts all agree. Full confluence (3/3 timeframes aligned) gets a 30% score boost.

### Options Flow Analysis (weight: 15%)
Unusual options activity reveals institutional positioning before moves. Analyses put/call ratio and detects unusual sweeps (volume > 2x open interest).

### Sentiment Analysis (weight: 15%)
News headline scoring using bullish/bearish keyword weighting. Integrates with NewsAPI for live financial headlines.

### Forensics Edge (weight: 20%)
Your unique alpha — adapted from the AI Market Forensics Engine. Detects manipulation signatures (OBV divergence, volume spikes at extremes, price entropy) and positions for the inevitable mean reversion.

---

## Live Dashboard

Web-based chart dashboard served at `http://localhost:5001`.

**Charts:**
- Candlestick price chart with ghost pattern markers (👻)
- Moving averages (MA9, MA20)
- Volume bars + OBV overlay (ACCUMULATING/DISTRIBUTING)
- Multi-timeframe view: daily, weekly, monthly side-by-side
- Live P&L chart
- Signal strength bars for all 5 strategies
- Real-time symbol switcher

Also accessible on phone at `http://YOUR_LAPTOP_IP:5001`

---

## Setup

### Requirements
```bash
/usr/bin/python3 -m pip install flask flask-cors
```
No other dependencies — all data fetching uses Python's built-in `urllib`.

### Environment Variables
```bash
export ALPACA_API_KEY=your_alpaca_key
export ALPACA_SECRET=your_alpaca_secret
export FRED_API_KEY=your_fred_key
export GMAIL_ADDRESS=your_email@gmail.com
export GMAIL_APP_PASSWORD=your_app_password
export ALPACA_LIVE=true   # for live trading (default: paper)
```

### Run APEX Master System
```bash
cd apex_trader
/usr/bin/python3 apex_master.py
```

### Run APEX Signal Scanner
```bash
/usr/bin/python3 apex_main.py
```

---

## Commands

### APEX Master System
```
optimise              — Portfolio optimisation (Markowitz, 10,000 simulations)
montecarlo SPY 30     — Monte Carlo simulation (symbol, days ahead)
option SPY 600 30     — Price a call option (symbol, strike, days to expiry)
predict AAPL          — 1/5/20 day price prediction
rates                 — Interest rate cycle analysis (live FRED data)
structure SPY         — Market structure analysis
status                — All module status + autonomous trader P&L
report                — Generate and email full daily report
quit                  — Shutdown + send final report
```

### APEX Signal Scanner
```
yes SYMBOL            — Approve pending trade
no SYMBOL             — Reject pending trade
close SYMBOL          — Manually close open position
status                — Portfolio metrics
signals               — Latest signal table
charts SYMBOL         — ASCII terminal charts
quit                  — Shutdown + weekly report
```

---

## Risk Disclosure

This system is built for educational and research purposes. Trading financial instruments involves substantial risk of loss. The autonomous trader uses real capital — only deploy funds you can afford to lose entirely. Past performance of any algorithm does not guarantee future results.

All hard risk limits in the code are non-negotiable and cannot be overridden at runtime.

---

## Related Projects

| Project | Description | Repo |
|---|---|---|
| AI Market Forensics Engine | Detects market manipulation in real-time | [github.com/axlAJ/ai-market-forensics-engine](https://github.com/axlAJ/ai-market-forensics-engine) |
| Bond Trading Platform | Live yield curve analysis + bond ETF signals | [github.com/axlAJ/bond-trading-platform](https://github.com/axlAJ/bond-trading-platform) |
| Property Management Platform | 25-unit AI property system, 6 AI models | [github.com/axlAJ/property-management-platform](https://github.com/axlAJ/property-management-platform) |

---

## Author

**Philip AJ Sogah**
AI Innovator · FinTech Engineer · Software Engineer
Norwich University, Computer Science — May 2026

[philipajsogah.io](https://philipajsogah.io) · [LinkedIn](https://linkedin.com/in/philip-aj-sogah-a1558633b) · philipaxl7@gmail.com

---

*Built with Python, Alpaca Markets API, FRED API, and zero compromises.*

