# Stock Analyzer + Stockeram

Two connected products: a Python ML backend that analyzes stocks daily, and an iOS-style PWA that presents the results beautifully.

---

## Part 1 — Stock Analyzer (Python ML backend)

Ranks US stocks, German (DAX) stocks, ETFs, and crypto by probability of meaningful price gain over 1, 3, and 6 months. Sends a Telegram digest every morning at 07:00.

### What it does

- Downloads 5 years of daily price data for **110+ assets** via yfinance (free)
- Computes **36 features**: technical indicators, macro (VIX, yield, dollar), relative strength vs sector
- Trains a **stacked ML ensemble** (LightGBM + XGBoost + meta-learner) using walk-forward time-series validation
- Ranks every asset by probability of gaining ≥5% / ≥10% / ≥15% in 1M / 3M / 6M
- Applies **8 signal boosts**: Piotroski fundamentals, VADER sentiment, insider trading, analyst consensus, options put/call ratio, sector momentum, market regime (bull/bear), earnings calendar
- Retrains every Monday automatically

### Universe

| Category | Assets |
|---|---|
| **US Stocks** | AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, JPM, NET, AXP, CAVA, RKLB, OKLO, IONQ, NIO, RGTI + 25 more |
| **German / EU** | SAP, Siemens, Allianz, BMW, Deutsche Telekom, Rheinmetall, BASF, Bayer, Airbus, Linde, Commerzbank, AXA + 20 more |
| **Crypto** | BTC, ETH, BNB, XRP, SOL, ADA, DOGE, AVAX, DOT, LINK, XLM, ATOM, TRX, SHIB |
| **ETFs** | SPY, QQQ, IVV, VTI, VWO, IS3Q.DE, VWCE.DE, IWDA.AS, CSPX.L, GLD, TLT |

### Quick start

```bash
pip install -r requirements.txt
python main.py          # first run trains models (~15-20 min)
streamlit run dashboard.py  # open web dashboard
```

### Project files

```
stock-analyzer/
├── main.py              # 8-stage daily pipeline (entry point)
├── config.py            # Universe, thresholds, Telegram credentials
├── data_fetcher.py      # Batch yfinance downloads with daily cache
├── feature_engine.py    # 36 technical + macro + RS features
├── ml_engine.py         # LGB + XGB stacking ensemble
├── macro_features.py    # VIX, 10Y yield, dollar index
├── fundamental.py       # Piotroski F-Score (9 criteria)
├── sentiment.py         # VADER NLP on Yahoo Finance RSS
├── insider.py           # SEC Form 4 insider buy/sell signals
├── earnings.py          # Upcoming earnings calendar warning
├── analyst.py           # Wall Street analyst consensus
├── options_sentiment.py # Put/call ratio from options chain
├── market_regime.py     # S&P 500 bull/bear + sector momentum
├── outcome_tracker.py   # Tracks prediction vs actual results
├── notifier.py          # Telegram daily digest
├── dashboard.py         # Streamlit web dashboard
└── .github/workflows/   # GitHub Actions — runs daily at 07:00 UTC
```

### ML details

| | |
|---|---|
| **Models** | LightGBM + XGBoost → LogisticRegression meta-learner (stacking) |
| **Validation** | Walk-forward TimeSeriesSplit — no data leakage |
| **Retraining** | Every Monday (auto-detects feature count changes) |
| **Features** | 36: returns, RSI×3, MACD, BB, EMA ratios, ATR, ADX, OBV, ROC, 52W range, VIX, yield, dollar, sector RS, 12M-1M momentum |
| **Labels** | Binary: price gains ≥5%/10%/15% in 21/63/126 trading days |
| **Boosts** | Fundamentals ±15, Analysts ±15, Insiders ±12, Sentiment ±10, Options ±10, Sector ±8, Earnings ×0.7 |

### Telegram output example

```
📊 Your Daily Stock Picks — April 24, 2026

🌍 Market: Healthy & Growing 🟢
The S&P 500 is 7.0% above its long-term average.

━━━━━━━━━━━━━━━━━━━━━
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

### GitHub Actions (cloud, no PC needed)

Set two repository secrets (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`), then it runs automatically every morning. Trigger manually from the Actions tab.

---

## Part 2 — Stockeram (iOS PWA)

Instagram/TikTok-style mobile app: swipe through daily stock picks with beautiful cards, AI score, price chart, and full analysis.

**Live:** `https://stockeram-app.hsaberiansani.workers.dev`  
**Repo:** `https://github.com/hossys/Stockeram_app`

### Features

- Vertical swipe feed (TikTok-style scroll-snap)
- Filter by: 🌍 All · 📈 Stocks · 🪙 Crypto · 📊 ETFs
- Each pick shows: AI score, price target, upside %, "if you invest €1,000" calculator
- **Full Analysis** sheet: SVG price chart (6M history + 12M prediction cone), AI probabilities, all signals
- **Risk Scenarios** sheet: best / most likely / worst case
- Save to watchlist (localStorage), Like, Share
- Installable on iPhone: Safari → Share → Add to Home Screen

### Deploy

Static files only (HTML + CSS + JS, no framework). Deploy to Cloudflare Pages, Railway, or any static host.

---

> **Disclaimer:** Not financial advice. All predictions are AI-generated statistical estimates based on historical patterns.
