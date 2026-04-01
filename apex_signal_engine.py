"""
Signal Engine — APEX Trading System
Philip AJ Sogah | philipajsogah.io
======================================
Five proprietary edge strategies fused into a composite signal:

  1. Ghost Pattern Detection    — institutional accumulation/distribution
  2. Multi-Timeframe Confluence — daily + weekly + monthly alignment
  3. Options Flow Analysis      — unusual activity = whale positioning
  4. Sentiment Analysis         — news shock + social momentum
  5. Forensics Edge             — manipulation → mean reversion (YOUR UNIQUE EDGE)

Composite score: -100 (strong sell) to +100 (strong buy)
Time horizon classification: days (1-5), weeks (1-4), months (1-6)
"""

import math
import statistics
import time
import json
import urllib.request
import urllib.parse
import os
from datetime import datetime, timezone, timedelta, date
from dataclasses import dataclass, field
from typing import Optional
from apex_market_feed import Bar, Quote, MacroSnapshot


# ── OUTPUT STRUCTURES ─────────────────────────────────────────

@dataclass
class SignalComponent:
    name:       str
    score:      float      # -100 to +100
    weight:     float
    reason:     str
    confidence: float      # 0-100


@dataclass
class TradeSignal:
    symbol:          str
    action:          str       # BUY | SELL | HOLD | WATCH
    strength:        str       # STRONG | MODERATE | WEAK
    composite_score: float     # -100 to +100
    confidence:      float     # 0-100
    horizon:         str       # days | weeks | months
    horizon_days:    int       # estimated days to target
    entry_price:     float
    target_price:    float
    stop_price:      float
    risk_reward:     float     # risk/reward ratio
    components:      list
    reasoning:       str       # human-readable explanation
    ghost_detected:  bool      # institutional footprint found
    manipulation:    bool      # forensics engine flagged
    asset_class:     str
    timestamp:       str


# ── 1. GHOST PATTERN DETECTION ────────────────────────────────

class GhostPatternDetector:
    """
    Detects institutional accumulation and distribution patterns
    that precede large price moves — the "ghost" footprints left
    by hedge funds and market makers before they execute.

    Ghost accumulation signals:
    - High volume on up days, low volume on down days (accumulation)
    - Price holding above key support despite broad weakness
    - Narrowing range with declining volume (coiling before breakout)
    - Dark pool prints — unusually large transactions at off-exchange prices
    - Volume climax followed by price stabilization (selling exhaustion)

    Ghost distribution signals:
    - High volume on down days, low volume on up days
    - Price failing to make new highs despite broad strength
    - Widening range on down moves
    """

    WEIGHT = 0.25

    def detect(self, bars: list, quote: Quote) -> SignalComponent:
        if len(bars) < 20:
            return SignalComponent("Ghost Pattern", 0, self.WEIGHT,
                                   "Insufficient data", 30)

        closes  = [b.close  for b in bars]
        volumes = [b.volume for b in bars]
        highs   = [b.high   for b in bars]
        lows    = [b.low    for b in bars]

        score   = 0.0
        signals = []

        # ── On-Balance Volume trend ──
        obv = 0
        obv_series = [0]
        for i in range(1, len(bars)):
            if closes[i] > closes[i-1]:
                obv += volumes[i]
            elif closes[i] < closes[i-1]:
                obv -= volumes[i]
            obv_series.append(obv)

        # OBV making new highs while price consolidates = accumulation
        obv_20   = obv_series[-20:]
        price_20 = closes[-20:]
        obv_trend   = (obv_20[-1]   - obv_20[0])   / (abs(obv_20[0])   + 1)
        price_trend = (price_20[-1] - price_20[0]) / price_20[0]

        if obv_trend > 0.1 and price_trend < 0.02:
            score += 35
            signals.append("OBV divergence — volume accumulating while price flat (ghost buying)")
        elif obv_trend < -0.1 and price_trend > -0.02:
            score -= 35
            signals.append("OBV divergence — volume distributing while price holds (ghost selling)")

        # ── Volume pattern analysis ──
        avg_vol = statistics.mean(volumes[-20:])
        up_vol   = statistics.mean(volumes[i] for i in range(len(bars)-10, len(bars))
                                   if closes[i] >= bars[i].open)
        down_vol = statistics.mean(volumes[i] for i in range(len(bars)-10, len(bars))
                                   if closes[i] < bars[i].open) or avg_vol

        if up_vol > down_vol * 1.5:
            score += 20
            signals.append(f"Up-day volume {up_vol/down_vol:.1f}x down-day volume — institutional buying")
        elif down_vol > up_vol * 1.5:
            score -= 20
            signals.append(f"Down-day volume {down_vol/up_vol:.1f}x up-day volume — institutional selling")

        # ── Wyckoff spring/upthrust detection ──
        recent_low  = min(lows[-5:])
        support     = min(lows[-20:-5])
        if recent_low < support * 0.99 and closes[-1] > support:
            score += 30
            signals.append("Wyckoff spring — price briefly broke support then recovered (ghost accumulation)")

        recent_high = max(highs[-5:])
        resistance  = max(highs[-20:-5])
        if recent_high > resistance * 1.01 and closes[-1] < resistance:
            score -= 30
            signals.append("Wyckoff upthrust — price briefly broke resistance then fell (ghost distribution)")

        # ── Coiling pattern (narrowing range = energy building) ──
        ranges_recent = [b.high - b.low for b in bars[-5:]]
        ranges_prev   = [b.high - b.low for b in bars[-20:-5]]
        if ranges_recent and ranges_prev:
            avg_recent = statistics.mean(ranges_recent)
            avg_prev   = statistics.mean(ranges_prev)
            if avg_recent < avg_prev * 0.6:
                # Coiling — determine direction from OBV
                coil_score = 25 if obv_trend > 0 else -25
                score += coil_score
                direction = "bullish" if coil_score > 0 else "bearish"
                signals.append(f"Coiling pattern — narrowing range ({direction} bias from OBV)")

        score = max(-100, min(100, score))
        ghost = abs(score) >= 30
        confidence = min(95, 50 + abs(score) * 0.5)
        reason = " | ".join(signals) if signals else "No ghost patterns detected"

        return SignalComponent("Ghost Pattern", score, self.WEIGHT, reason, confidence)


# ── 2. MULTI-TIMEFRAME CONFLUENCE ─────────────────────────────

class MTFConfluenceAnalyzer:
    """
    The most reliable signals occur when daily, weekly, AND monthly
    charts all agree. This is what separates high-probability setups
    from noise.

    Rules:
    - All 3 timeframes bullish = STRONG BUY (rare and powerful)
    - 2/3 timeframes bullish   = MODERATE signal
    - 1/3 timeframes bullish   = WEAK / conflicted = HOLD
    - All 3 bearish            = STRONG SELL

    Each timeframe scored by: trend direction, momentum, key level position
    """

    WEIGHT = 0.25

    def analyse(self, mtf_bars: dict) -> SignalComponent:
        tf_scores = {}
        reasons   = []

        for tf, bars in mtf_bars.items():
            if len(bars) < 10:
                tf_scores[tf] = 0
                continue

            closes = [b.close for b in bars]
            s = 0

            # Trend: price above/below 20-period MA
            ma20 = statistics.mean(closes[-20:]) if len(closes) >= 20 else closes[0]
            if closes[-1] > ma20 * 1.01:
                s += 30
            elif closes[-1] < ma20 * 0.99:
                s -= 30

            # Momentum: last 5 bars direction
            if len(closes) >= 5:
                mom = (closes[-1] - closes[-5]) / closes[-5] * 100
                s  += max(-25, min(25, mom * 5))

            # RSI-like momentum
            if len(closes) >= 14:
                gains  = [max(0, closes[i]-closes[i-1]) for i in range(1,15)]
                losses = [max(0, closes[i-1]-closes[i]) for i in range(1,15)]
                avg_g  = statistics.mean(gains)  or 0.001
                avg_l  = statistics.mean(losses) or 0.001
                rsi    = 100 - (100 / (1 + avg_g/avg_l))
                if rsi > 70:
                    s -= 15    # overbought
                elif rsi < 30:
                    s += 15    # oversold
                elif rsi > 55:
                    s += 10
                elif rsi < 45:
                    s -= 10

            tf_scores[tf] = max(-100, min(100, s))

        # Confluence scoring
        scores     = list(tf_scores.values())
        positives  = sum(1 for s in scores if s > 10)
        negatives  = sum(1 for s in scores if s < -10)

        if positives == 3:
            composite  = statistics.mean(scores) * 1.3   # boost for full confluence
            reasons.append("FULL BULLISH CONFLUENCE — all 3 timeframes aligned up (rare, high probability)")
        elif negatives == 3:
            composite  = statistics.mean(scores) * 1.3
            reasons.append("FULL BEARISH CONFLUENCE — all 3 timeframes aligned down")
        elif positives == 2:
            composite  = statistics.mean(scores)
            reasons.append(f"2/3 timeframes bullish — moderate confluence")
        elif negatives == 2:
            composite  = statistics.mean(scores)
            reasons.append(f"2/3 timeframes bearish — moderate confluence")
        else:
            composite  = statistics.mean(scores) * 0.5   # reduce conflicted signals
            reasons.append("Mixed timeframes — conflicted signal, reduced confidence")

        for tf, s in tf_scores.items():
            direction = "▲" if s > 0 else "▼" if s < 0 else "→"
            reasons.append(f"{tf}: {direction} {s:+.0f}")

        composite  = max(-100, min(100, composite))
        confidence = (max(positives, negatives) / 3) * 100

        return SignalComponent("MTF Confluence", composite, self.WEIGHT,
                               " | ".join(reasons), confidence)


# ── 3. OPTIONS FLOW ANALYSIS ──────────────────────────────────

class OptionsFlowAnalyzer:
    """
    Unusual options activity = smart money positioning before moves.
    Large call sweeps above ask price = bullish bet.
    Large put sweeps above ask price = bearish bet or hedge.

    Uses Yahoo Finance options data (free, no key needed).
    """

    WEIGHT = 0.15

    def analyse(self, symbol: str, quote: Quote) -> SignalComponent:
        """Analyse options flow for a symbol."""
        # For ETFs and commodities, options flow less relevant
        if quote.asset_class in ("forex", "crypto"):
            return SignalComponent("Options Flow", 0, self.WEIGHT,
                                   "Options flow N/A for this asset class", 30)

        try:
            url  = (f"https://query1.finance.yahoo.com/v7/finance/options/{symbol}"
                    f"?straddle=false")
            req  = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read())

            result   = data.get("optionChain",{}).get("result",[])
            if not result:
                return SignalComponent("Options Flow", 0, self.WEIGHT,
                                       "No options data available", 20)

            calls = result[0].get("options",[{}])[0].get("calls",[])
            puts  = result[0].get("options",[{}])[0].get("puts", [])

            if not calls and not puts:
                return SignalComponent("Options Flow", 0, self.WEIGHT,
                                       "No options contracts found", 20)

            # Volume analysis
            call_vol = sum(c.get("volume",0) or 0 for c in calls)
            put_vol  = sum(p.get("volume",0) or 0 for p in puts)
            total    = call_vol + put_vol

            if total == 0:
                return SignalComponent("Options Flow", 0, self.WEIGHT,
                                       "Zero options volume", 20)

            pc_ratio = put_vol / (call_vol + 1)
            score    = 0
            signals  = []

            # Put/Call ratio interpretation
            if pc_ratio < 0.5:
                score = 40
                signals.append(f"Bullish options flow — P/C ratio {pc_ratio:.2f} (heavy call buying)")
            elif pc_ratio < 0.7:
                score = 20
                signals.append(f"Mild bullish options flow — P/C ratio {pc_ratio:.2f}")
            elif pc_ratio > 1.5:
                score = -40
                signals.append(f"Bearish options flow — P/C ratio {pc_ratio:.2f} (heavy put buying)")
            elif pc_ratio > 1.0:
                score = -20
                signals.append(f"Mild bearish options flow — P/C ratio {pc_ratio:.2f}")
            else:
                signals.append(f"Neutral options flow — P/C ratio {pc_ratio:.2f}")

            # Unusual volume
            avg_call_oi = statistics.mean(c.get("openInterest",0) or 0 for c in calls[:10]) + 1
            for c in calls[:10]:
                vol = c.get("volume",0) or 0
                oi  = c.get("openInterest",0) or 0
                if vol > oi * 2 and vol > 1000:
                    score += 20
                    signals.append(f"Unusual call sweep at ${c.get('strike',0)} — {vol:,} contracts vs {oi:,} OI")
                    break

            for p in puts[:10]:
                vol = p.get("volume",0) or 0
                oi  = p.get("openInterest",0) or 0
                if vol > oi * 2 and vol > 1000:
                    score -= 20
                    signals.append(f"Unusual put sweep at ${p.get('strike',0)} — {vol:,} contracts vs {oi:,} OI")
                    break

            score = max(-100, min(100, score))
            return SignalComponent("Options Flow", score, self.WEIGHT,
                                   " | ".join(signals), 70)

        except Exception as e:
            return SignalComponent("Options Flow", 0, self.WEIGHT,
                                   f"Options data unavailable: {e}", 20)


# ── 4. SENTIMENT ANALYZER ─────────────────────────────────────

class SentimentAnalyzer:
    """
    News and social sentiment — markets move on narrative before price.
    Uses NewsAPI for financial headlines (free tier: 100 req/day).
    Falls back to basic keyword scoring if no API key.
    """

    WEIGHT = 0.15

    BULLISH_WORDS = [
        "surge","rally","soar","jump","beat","record","breakthrough",
        "upgrade","buy","bullish","growth","profit","revenue","strong",
        "outperform","positive","gain","high","rise","increase"
    ]
    BEARISH_WORDS = [
        "crash","plunge","fall","miss","downgrade","sell","bearish",
        "loss","debt","risk","warning","concern","weak","decline",
        "cut","layoff","lawsuit","investigation","fraud","negative"
    ]

    def __init__(self, news_api_key: str = None):
        self.news_key = news_api_key or os.getenv("NEWS_API_KEY","")

    def analyse(self, symbol: str) -> SignalComponent:
        name = symbol.replace("/","").replace("=X","")

        if self.news_key:
            return self._newsapi_sentiment(symbol, name)
        else:
            return self._basic_sentiment(symbol)

    def _newsapi_sentiment(self, symbol: str, name: str) -> SignalComponent:
        try:
            params = {
                "q":        f"{symbol} OR {name} stock",
                "apiKey":   self.news_key,
                "language": "en",
                "pageSize": 10,
                "sortBy":   "publishedAt",
            }
            url = "https://newsapi.org/v2/everything?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read())

            articles = data.get("articles", [])
            if not articles:
                return self._basic_sentiment(symbol)

            scores = []
            for a in articles[:10]:
                text  = ((a.get("title","") or "") + " " +
                         (a.get("description","") or "")).lower()
                bull  = sum(1 for w in self.BULLISH_WORDS if w in text)
                bear  = sum(1 for w in self.BEARISH_WORDS if w in text)
                if bull + bear > 0:
                    scores.append((bull - bear) / (bull + bear) * 100)

            if not scores:
                return SignalComponent("Sentiment", 0, self.WEIGHT,
                                       "No sentiment signals in news", 30)

            avg_score = statistics.mean(scores)
            signal_str = "bullish" if avg_score > 10 else "bearish" if avg_score < -10 else "neutral"
            reason = (f"News sentiment: {signal_str} ({avg_score:+.0f}) "
                      f"from {len(articles)} articles")

            return SignalComponent("Sentiment", max(-100,min(100,avg_score*0.8)),
                                   self.WEIGHT, reason, 65)
        except Exception as e:
            return self._basic_sentiment(symbol)

    def _basic_sentiment(self, symbol: str) -> SignalComponent:
        """Neutral fallback when no API key — doesn't bias signals."""
        return SignalComponent("Sentiment", 0, self.WEIGHT,
                               "Sentiment: neutral (set NEWS_API_KEY for live news scoring)", 30)


# ── 5. FORENSICS EDGE ─────────────────────────────────────────

class ForensicsEdge:
    """
    YOUR UNIQUE EDGE — adapted from the Market Forensics Engine.

    When manipulation is detected (spoofing, layering, wash trading),
    the market is artificially moved. After manipulation ends,
    prices snap back to fair value = predictable mean reversion trade.

    This is alpha that Citadel and Renaissance have but retail doesn't.
    You have it because you built the forensics engine.

    Also monitors for:
    - Unusual spread widening (dark pool activity)
    - Volume spikes at key technical levels
    - Price exhaustion after manipulation
    """

    WEIGHT = 0.20

    def analyse(self, bars: list, quote: Quote) -> SignalComponent:
        if len(bars) < 10 or not quote or quote.price == 0:
            return SignalComponent("Forensics Edge", 0, self.WEIGHT,
                                   "Insufficient data", 20)

        score   = 0.0
        signals = []
        closes  = [b.close  for b in bars]
        volumes = [b.volume for b in bars]
        highs   = [b.high   for b in bars]
        lows    = [b.low    for b in bars]

        # ── Spread analysis (manipulation proxy) ──
        if quote.spread > 0 and quote.price > 0:
            spread_pct = quote.spread / quote.price * 100
            normal_spread = {"equity":0.05,"commodity":0.1,
                             "crypto":0.1,"forex":0.02}.get(quote.asset_class, 0.05)
            if spread_pct > normal_spread * 3:
                signals.append(f"Unusually wide spread {spread_pct:.3f}% — potential manipulation")
                score -= 15   # wide spread = avoid

        # ── Volume spike analysis ──
        avg_vol    = statistics.mean(volumes[:-1]) if len(volumes) > 1 else volumes[-1]
        last_vol   = volumes[-1]
        vol_ratio  = last_vol / (avg_vol + 1)

        # Volume spike with price at extreme = exhaustion signal
        ma20 = statistics.mean(closes[-20:]) if len(closes) >= 20 else closes[0]
        deviation = (quote.price - ma20) / ma20 * 100

        if vol_ratio > 2.5 and deviation > 3:
            score -= 30
            signals.append(f"Volume spike ({vol_ratio:.1f}x) at overbought extreme — exhaustion sell signal")
        elif vol_ratio > 2.5 and deviation < -3:
            score += 30
            signals.append(f"Volume spike ({vol_ratio:.1f}x) at oversold extreme — exhaustion buy signal")

        # ── Shannon entropy proxy (order book depth variability) ──
        # High variability in recent ranges = manipulation-like behavior
        recent_ranges = [(b.high - b.low) / b.close for b in bars[-10:]]
        if recent_ranges:
            range_std = statistics.stdev(recent_ranges) if len(recent_ranges) > 1 else 0
            range_avg = statistics.mean(recent_ranges)
            entropy   = range_std / (range_avg + 0.001)
            if entropy > 0.5:
                signals.append(f"High price entropy {entropy:.2f} — erratic behavior, manipulation possible")
                score *= 0.7   # reduce confidence when entropy high

        # ── Mean reversion after extreme moves ──
        if len(closes) >= 5:
            move_5d = (closes[-1] - closes[-5]) / closes[-5] * 100
            if abs(move_5d) > 8:
                # Extreme 5-day move = mean reversion opportunity
                reversion_score = -move_5d * 2.5
                reversion_score = max(-40, min(40, reversion_score))
                score += reversion_score
                direction = "up" if move_5d > 0 else "down"
                signals.append(f"Extreme {move_5d:+.1f}% 5-day move — mean reversion {('down' if move_5d>0 else 'up')} expected")

        score = max(-100, min(100, score))
        reason = " | ".join(signals) if signals else "No forensics signals detected — clean price action"

        return SignalComponent("Forensics Edge", score, self.WEIGHT, reason,
                               min(90, 40 + abs(score)))


# ── PREDICTOR (TIME HORIZON) ──────────────────────────────────

class HorizonPredictor:
    """
    Classifies trade signals by expected time to target:
    - Days (1-5 days):    momentum + mean reversion
    - Weeks (1-4 weeks):  trend + confluence
    - Months (1-6 months):macro + institutional positioning

    Uses signal strength and timeframe alignment to determine horizon.
    """

    def classify(self, composite: float, mtf_score: float,
                 macro: MacroSnapshot) -> tuple:
        abs_score = abs(composite)

        # Strong short-term signals = days
        if abs_score >= 60 and abs(mtf_score) < 20:
            return "days", 3

        # Strong multi-timeframe = weeks
        elif abs_score >= 40 and abs(mtf_score) >= 30:
            return "weeks", 14

        # Macro-driven = months
        elif macro.curve_shape != "normal" and abs_score >= 30:
            return "months", 45

        # Moderate signals = weeks
        elif abs_score >= 25:
            return "weeks", 10

        else:
            return "days", 5


# ── MASTER SIGNAL ENGINE ──────────────────────────────────────

class SignalEngine:
    """
    Fuses all 5 signals into composite trade recommendations
    with time horizons, price targets, and risk/reward ratios.
    """

    SIGNAL_WEIGHTS = {
        "Ghost Pattern":    0.25,
        "MTF Confluence":   0.25,
        "Options Flow":     0.15,
        "Sentiment":        0.15,
        "Forensics Edge":   0.20,
    }

    def __init__(self, news_api_key: str = None):
        self.ghost      = GhostPatternDetector()
        self.mtf        = MTFConfluenceAnalyzer()
        self.options    = OptionsFlowAnalyzer()
        self.sentiment  = SentimentAnalyzer(news_api_key)
        self.forensics  = ForensicsEdge()
        self.predictor  = HorizonPredictor()

    def analyse(self, symbol: str, quote: Quote,
                mtf_bars: dict,
                macro: MacroSnapshot,
                asset_class: str = "equity") -> TradeSignal:
        """Run full signal analysis for one symbol."""

        daily_bars = mtf_bars.get("1D", [])

        # Run all 5 signals
        ghost_sig   = self.ghost.detect(daily_bars, quote)
        mtf_sig     = self.mtf.analyse(mtf_bars)
        options_sig = self.options.analyse(symbol, quote)
        sent_sig    = self.sentiment.analyse(symbol)
        forensic_sig= self.forensics.analyse(daily_bars, quote)

        components = [ghost_sig, mtf_sig, options_sig, sent_sig, forensic_sig]

        # Weighted composite
        composite = sum(c.score * c.weight for c in components)
        composite = round(max(-100, min(100, composite)), 2)

        # Macro overlay adjustment
        if macro.vix > 30:
            composite *= 0.7      # high fear = reduce all signals
        if macro.curve_shape == "inverted":
            if asset_class == "equity":
                composite -= 8    # inverted curve = equity headwind

        composite = round(max(-100, min(100, composite)), 2)

        # Action classification
        if composite >= 60:   action, strength = "BUY",  "STRONG"
        elif composite >= 35: action, strength = "BUY",  "MODERATE"
        elif composite >= 15: action, strength = "WATCH","WEAK"
        elif composite <= -60:action, strength = "SELL", "STRONG"
        elif composite <= -35:action, strength = "SELL", "MODERATE"
        elif composite <= -15:action, strength = "WATCH","WEAK"
        else:                 action, strength = "HOLD", "NEUTRAL"

        # Price targets
        price = quote.price
        if asset_class in ("forex",):
            target_pct = abs(composite) / 100 * 0.015
            stop_pct   = 0.008
        elif asset_class == "crypto":
            target_pct = abs(composite) / 100 * 0.04
            stop_pct   = 0.02
        elif asset_class == "commodity":
            target_pct = abs(composite) / 100 * 0.025
            stop_pct   = 0.012
        else:
            target_pct = abs(composite) / 100 * 0.025
            stop_pct   = 0.012

        direction    = 1 if composite > 0 else -1
        target_price = round(price * (1 + direction * target_pct), 4)
        stop_price   = round(price * (1 - direction * stop_pct), 4)

        target_dist = abs(target_price - price)
        stop_dist   = abs(stop_price   - price)
        risk_reward = round(target_dist / (stop_dist + 0.001), 2)

        # Time horizon
        horizon, horizon_days = self.predictor.classify(
            composite, mtf_sig.score, macro)

        # Signal agreement → confidence
        positives  = sum(1 for c in components if c.score > 5)
        negatives  = sum(1 for c in components if c.score < -5)
        agreement  = max(positives, negatives)
        confidence = round(min(95, (agreement / len(components)) * 100 +
                              abs(composite) * 0.3), 1)

        # Ghost and manipulation flags
        ghost_detected = abs(ghost_sig.score) >= 30
        manipulation   = abs(forensic_sig.score) >= 25

        # Human-readable reasoning
        top_signals = sorted(components, key=lambda c: abs(c.score), reverse=True)[:3]
        reasoning = (
            f"{strength} {action} signal for {symbol} "
            f"(score {composite:+.0f}, confidence {confidence:.0f}%). "
            f"Expected horizon: {horizon} ({horizon_days} days). "
            f"Top signals: {'; '.join(s.reason[:60] for s in top_signals)}."
        )

        return TradeSignal(
            symbol          = symbol,
            action          = action,
            strength        = strength,
            composite_score = composite,
            confidence      = confidence,
            horizon         = horizon,
            horizon_days    = horizon_days,
            entry_price     = round(price, 4),
            target_price    = target_price,
            stop_price      = stop_price,
            risk_reward     = risk_reward,
            components      = components,
            reasoning       = reasoning,
            ghost_detected  = ghost_detected,
            manipulation    = manipulation,
            asset_class     = asset_class,
            timestamp       = datetime.now(timezone.utc).isoformat(),
        )

    def scan_all(self, quotes: dict, mtf_data: dict,
                 macro: MacroSnapshot) -> list:
        """Scan all symbols and return ranked signals."""
        from apex_market_feed import UNIVERSE
        signals = []
        for symbol, quote in quotes.items():
            info    = UNIVERSE.get(symbol, {})
            mtf     = mtf_data.get(symbol, {"1D":[],"1W":[],"1M":[]})
            signal  = self.analyse(symbol, quote, mtf, macro,
                                   info.get("class","equity"))
            signals.append(signal)

        # Sort by |composite_score| descending
        signals.sort(key=lambda s: abs(s.composite_score), reverse=True)
        return signals
