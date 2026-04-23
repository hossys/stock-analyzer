# Stock Analyzer — Professional ML-Based Buy Predictions

Ranks US stocks, German (DAX) stocks, and crypto by their probability of a meaningful price gain over the next 1, 3, and 6 months. Output is a clean ranked list — no technical jargon, just actionable buy probabilities.

---

## What it does

- Downloads 5 years of daily price data for 80 assets (40 US stocks, 30 DAX stocks, 10 crypto) via yfinance (free)
- Computes 28 scale-invariant features from technical indicators (internally — never shown to you)
- Trains three LightGBM models (one per horizon) using walk-forward time-series validation + probability calibration
- Ranks every asset by its probability of gaining **≥5% in 1 month**, **≥10% in 3 months**, **≥15% in 6 months**
- Sends a Telegram digest every morning at 07:00
- Retrains every Monday automatically

---

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Telegram (optional but recommended)

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 3. Run the analyzer

```bash
python main.py
```

The **first run** downloads ~80 tickers and trains 3 ML models — expect 10–20 minutes.
Every subsequent daily run is fast (uses local cache + pre-trained models).

### 4. Open the dashboard

```bash
streamlit run dashboard.py
```

---

## Project structure

```
stock-analyzer/
├── main.py             # Daily runner + scheduler (entry point)
├── config.py           # Universe (tickers), horizons, thresholds
├── data_fetcher.py     # yfinance download with daily file cache
├── feature_engine.py   # 28 technical features (scale-invariant)
├── ml_engine.py        # LightGBM training, walk-forward CV, calibration, prediction
├── notifier.py         # Telegram daily digest
├── dashboard.py        # Streamlit web dashboard
├── requirements.txt
├── .env.example
│
├── models/             # Saved ML models (auto-created, gitignored)
├── cache/              # Daily price cache (auto-created, gitignored)
├── results.db          # Prediction history in SQLite (auto-created)
│
│   ── Legacy (kept for reference, not used by the new system) ──
├── plot_sender.py      # Telegram bot for chart images
├── train_model.py
└── generate_dataset.py
```

---

## Output example

```
─────────────────────────────────────────────────────────────────
RANK  NAME                   TYPE            1M      3M      6M    SCORE
─────────────────────────────────────────────────────────────────
1     NVIDIA                 US Stock      71.2%   68.4%   64.1%    67.8
2     SAP                    German Stock  65.3%   63.1%   59.8%    63.0
3     Bitcoin                Crypto        69.1%   61.2%   55.4%    61.9
...
─────────────────────────────────────────────────────────────────
Probabilities = P(price up ≥5%/10%/15% in 1M/3M/6M)
```

---

## ML details

| | |
|---|---|
| **Model** | LightGBM (gradient boosting) with sigmoid probability calibration |
| **Training data** | All tickers pooled, ~5 years daily = ~100k rows |
| **Validation** | Walk-forward TimeSeriesSplit (5 folds) — no data leakage |
| **Retraining** | Automatic every Monday |
| **Features** | 28 indicators: RSI, MACD, Bollinger %B, EMA ratios, ATR, ADX, OBV, ROC, 52-week position, volume ratio, seasonality |
| **Targets** | Binary: did price rise ≥5%/10%/15% in 21/63/126 trading days? |
| **Score** | Weighted composite: 20% × 1M + 50% × 3M + 30% × 6M |

---

## Covered assets

**US Stocks (40):** AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, JPM, V, UNH, XOM, LLY, JNJ, MA, HD, AVGO, PG, MRK, COST, ABBV, CVX, WMT, BAC, KO, PEP, NFLX, TMO, AMD, ADBE, CRM, ORCL, CSCO, QCOM, TXN, INTU, AMGN, BKNG, PYPL, UBER, COIN

**German Stocks / DAX (30):** SAP, Siemens, Allianz, BMW, Mercedes-Benz, Deutsche Telekom, BASF, Bayer, Airbus, Linde, Munich Re, Rheinmetall, RWE, Volkswagen, Deutsche Bank, Infineon, Adidas, Henkel, E.ON, Fresenius, DHL, Zalando, Vonovia, Continental, Deutsche Börse, Brenntag, HeidelbergMaterials, Siemens Healthineers, Siemens Energy, Merck KGaA

**Crypto (10):** Bitcoin, Ethereum, BNB, XRP, Solana, Cardano, Dogecoin, Avalanche, Polkadot, Chainlink

---

> **Disclaimer:** This tool is for personal research only. Statistical predictions are not financial advice.
