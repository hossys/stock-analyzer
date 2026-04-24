# Stock Analyzer + Stockeram

Two connected products:
1. **Stock Analyzer** — Python ML backend that analyzes 110+ assets daily and sends Telegram picks
2. **Stockeram** — iOS-style PWA (installable on iPhone) with a TikTok-style swipe feed

---

## Part 1 — Stock Analyzer (Python ML Backend)

### What it does

Every morning at 07:00 UTC, the system:
1. Downloads fresh price data for 110+ assets (US stocks, German stocks, ETFs, crypto) via yfinance (free)
2. Computes 36 features per asset: technical indicators + macro (VIX, yield, dollar) + relative strength
3. Predicts probability of gaining ≥5% / ≥10% / ≥15% in 1 / 3 / 6 months using a stacked ML ensemble
4. Applies 8 additional signal boosts (fundamentals, sentiment, analysts, insiders, options, sector)
5. Ranks all assets and sends a Telegram digest with the top picks

### ML Design — Honest Assessment

| Horizon | Label | Typical AUC | Notes |
|---|---|---|---|
| 1 Day | +0.5% | ~0.51 | **Too noisy — near random, not implemented** |
| 1 Week | +2% | ~0.53 | **Too noisy — near random, not implemented** |
| 1 Month | +5% | ~0.55 | Implemented ✅ |
| 3 Months | +10% | ~0.56 | Implemented ✅ (primary target) |
| 6 Months | +15% | ~0.57 | Implemented ✅ |

Daily price movements are dominated by random noise. Even the best quant funds focus on monthly+ horizons. AUC of 0.55+ with free public data is realistic — going higher requires paid alternative data (satellite, credit card, etc.).

**Retraining schedule:** Every Monday automatically. Each run uses the latest downloaded prices for features (daily freshness). Weekly retraining keeps GitHub Actions usage within the free tier (~300 min/week).

### 8 Signal Boosts

| Signal | Source | Boost Range |
|---|---|---|
| Piotroski F-Score | yfinance `.info` | ±15 |
| Analyst consensus | yfinance recommendations | ±15 |
| Insider trading | yfinance Form 4 | ±12 |
| VADER news sentiment | Yahoo Finance RSS | ±10 |
| Options put/call ratio | yfinance options chain | ±10 |
| Sector momentum | Sector ETFs via yfinance | ±8 |
| Market regime (bull/bear) | S&P 500 200-day MA | ×0.70 or ×1.0 |
| Earnings calendar | yfinance calendar | ×0.70 if within 14 days |

### Asset Universe (110+)

**US Stocks (40+):** AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, JPM, NET, AXP, CAVA, RKLB, OKLO, IONQ, NIO, RGTI, and 25 more

**German / EU Stocks (31):** SAP, Siemens, Allianz, BMW, Deutsche Telekom, Rheinmetall, BASF, Bayer, Airbus, Linde, Munich Re, Commerzbank, AXA, and 18 more

**Crypto (14):** BTC, ETH, BNB, XRP, SOL, ADA, DOGE, AVAX, DOT, LINK, XLM, ATOM, TRX, SHIB

**ETFs (11):** SPY, QQQ, IVV, VTI, VWO, IS3Q.DE, VWCE.DE, IWDA.AS, CSPX.L, GLD, TLT

### Project Files

```
stock-analyzer/
├── main.py              # 8-stage daily pipeline — entry point
├── config.py            # Universe, thresholds, Telegram credentials
├── data_fetcher.py      # Batch yfinance downloads with daily cache
├── feature_engine.py    # 36 features: technical + macro + relative strength
├── ml_engine.py         # LGB + XGB stacking ensemble with walk-forward CV
├── macro_features.py    # VIX, 10Y yield, dollar index features
├── fundamental.py       # Piotroski F-Score (9 financial criteria)
├── sentiment.py         # VADER NLP on Yahoo Finance RSS
├── insider.py           # SEC Form 4 insider buy/sell via yfinance
├── earnings.py          # Upcoming earnings calendar (14-day warning)
├── analyst.py           # Wall Street analyst consensus
├── options_sentiment.py # Put/call ratio from options chain
├── market_regime.py     # S&P 500 bull/bear + sector ETF momentum
├── outcome_tracker.py   # Tracks predictions vs real prices (fills over time)
├── notifier.py          # Telegram daily digest
├── dashboard.py         # Streamlit web dashboard
├── .github/workflows/   # GitHub Actions — runs daily, free tier
└── stockeram/           # PWA mobile app (see Part 2)
```

### Quick Start

```bash
pip install -r requirements.txt
python main.py              # first run trains models (~15-20 min)
streamlit run dashboard.py  # web dashboard
```

### GitHub Actions (No PC Needed)

1. Add secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
2. Runs automatically every day at 07:00 UTC
3. Trigger manually: Actions tab → Daily Stock Analysis → Run workflow

### Telegram Output Example

```
📊 Your Daily Stock Picks — April 24, 2026

🌍 Market: Healthy & Growing 🟢
The S&P 500 is 7.0% above its long-term average.

🥇 🇺🇸 UnitedHealth (UNH)
Signal: 🔥 STRONG BUY

📈 How likely is it to rise?
  • In 1 month  → 71% chance of gaining ≥5%
  • In 3 months → 68% chance of gaining ≥10%
  • In 6 months → 63% chance of gaining ≥15%

💼 Company health: Excellent 💪 (F-Score 8/9)
📰 News mood: Positive 🟢
🏢 Insider activity: 🟢 Insiders buying
🟢 Analysts: Strong Buy — 23/28
```

---

## Part 2 — Stockeram (iOS PWA)

An Instagram/TikTok-style mobile app: swipe through daily AI stock picks.

**Live:** `https://stockeram-app.hsaberiansani.workers.dev`
**Repo:** `https://github.com/hossys/Stockeram_app`

### Features

- Vertical swipe feed (TikTok scroll-snap)
- Filter by: 🌍 All · 📈 Stocks · 🪙 Crypto · 📊 ETFs
- **30 picks** — 10 stocks + 10 crypto + 10 ETFs
- Each pick: AI score, price target, upside %, "if you invest €1,000" simulation
- **Full Analysis** sheet: SVG chart (6M history + 12M prediction), 5 probability horizons (1M/3M/6M — daily/weekly not shown as unreliable)
- **Risk Scenarios**: best / most likely / worst case
- **Save** to watchlist — tap saved item to jump directly to that pick
- Like, Share buttons (fixed above tab bar, Instagram-style)
- **Learn section**: 13 expandable investing lessons — Bullish/Bearish, AI Score, F-Score, P/E ratio, ETF vs Stock, crypto basics, probabilities explained
- Installable on iPhone: Safari → Share → Add to Home Screen

### Install on iPhone

1. Open the URL in Safari
2. Tap **Share** → **Add to Home Screen**
3. Opens like a native app (full screen, no browser chrome)

### Deploy

```
stockeram/
├── index.html        # Full app — vanilla HTML/CSS/JS, no framework
├── manifest.json     # PWA manifest
└── service-worker.js # Offline cache
```

Static files only. Deploy to Cloudflare Pages (free), Railway, or any static host.

---

> **Disclaimer:** Not financial advice. All predictions are AI-generated statistical estimates based on historical patterns. Past performance does not guarantee future results.
