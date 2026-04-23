import os
import sys
import sqlite3
import schedule
import time
from datetime import datetime

import pandas as pd

from config import (
    US_STOCKS, DE_STOCKS, CRYPTO,
    TICKER_NAMES, DB_PATH, TOP_N, DAILY_RUN_TIME,
)
from data_fetcher import fetch_all
from feature_engine import compute_features
from ml_engine import train_models, load_models, predict
from fundamental import fetch_all_fundamentals, score_fundamentals
from sentiment import get_all_sentiments
from market_regime import detect_regime, compute_sector_momentum, sector_boost
from outcome_tracker import save_prediction_prices, update_outcomes
from notifier import send_daily_digest


def _asset_type(ticker: str) -> str:
    if ticker in US_STOCKS:
        return "US Stock"
    if ticker in DE_STOCKS:
        return "German Stock"
    return "Crypto"


def _build_features(data: dict) -> tuple[dict, dict]:
    features, prices = {}, {}
    for ticker, df in data.items():
        try:
            features[ticker] = compute_features(df)
            prices[ticker] = df["Close"].squeeze()
        except Exception as e:
            print(f"  [{ticker}] feature error: {e}")
    return features, prices


def _apply_boosts(
    predictions: pd.DataFrame,
    fundamentals: dict,
    sentiments: dict,
    sector_mom: dict,
    regime: dict,
) -> pd.DataFrame:
    fund_scores, fund_labels, fund_displays = [], [], []
    sent_boosts, sent_labels = [], []
    sec_boosts = []

    for _, row in predictions.iterrows():
        ticker = row["ticker"]

        f_score, f_label, f_display = score_fundamentals(fundamentals.get(ticker, {}))
        fund_scores.append(f_score)
        fund_labels.append(f_label)
        fund_displays.append(f_display)

        s = sentiments.get(ticker, {})
        sent_boosts.append(s.get("sentiment_boost", 0.0))
        sent_labels.append(s.get("sentiment_label", "Neutral 😐"))

        sec_boosts.append(sector_boost(ticker, sector_mom))

    predictions = predictions.copy()
    predictions["fund_score"]   = fund_scores
    predictions["fund_label"]   = fund_labels
    predictions["fund_display"] = fund_displays
    predictions["sent_boost"]   = sent_boosts
    predictions["sentiment_label"] = sent_labels
    predictions["sector_boost"] = sec_boosts

    raw = predictions["score"] + predictions["fund_score"] + \
          predictions["sent_boost"] + predictions["sector_boost"]
    multiplier = regime.get("score_multiplier", 1.0)
    predictions["adj_score"] = (raw * multiplier).round(1)
    predictions.sort_values("adj_score", ascending=False, inplace=True)
    predictions.reset_index(drop=True, inplace=True)
    return predictions


def _models_exist() -> bool:
    return os.path.exists(os.path.join("models", "model_3M.pkl"))


def _should_retrain() -> bool:
    if not _models_exist():
        return True
    return datetime.now().weekday() == 0


def _save(predictions: pd.DataFrame):
    conn = sqlite3.connect(DB_PATH)
    df = predictions.copy()
    df["timestamp"] = datetime.now().strftime("%Y-%m-%d")
    df.to_sql("predictions", conn, if_exists="append", index=False)
    conn.close()


def _print_results(predictions: pd.DataFrame, regime: dict):
    is_bull = regime.get("is_bull", True)
    print(f"\n  Market: {regime.get('regime', '?')} | "
          f"S&P vs 200MA: {regime.get('spy_vs_200ma', 0):+.1f}%")
    print(f"\n{'─'*75}")
    print(f"{'#':<4} {'Name':<20} {'Type':<14} {'1M':>6} {'3M':>6} {'6M':>6} "
          f"{'Base':>6} {'Adj':>6} {'Signal':<18}")
    print(f"{'─'*75}")
    for rank, (_, row) in enumerate(predictions.head(TOP_N).iterrows(), 1):
        ticker = row["ticker"]
        name = TICKER_NAMES.get(ticker, ticker)[:18]
        p1 = f"{row.get('prob_1M', 0):.0f}%"
        p3 = f"{row.get('prob_3M', 0):.0f}%"
        p6 = f"{row.get('prob_6M', 0):.0f}%"
        base = f"{row.get('score', 0):.0f}"
        adj = f"{row.get('adj_score', 0):.0f}"
        adj_val = row.get("adj_score", 0)
        if adj_val >= 65:
            sig = "🔥 STRONG BUY"
        elif adj_val >= 55:
            sig = "✅ BUY"
        else:
            sig = "👀 WATCH"
        print(f"{rank:<4} {name:<20} {row.get('type',''):<14} "
              f"{p1:>6} {p3:>6} {p6:>6} {base:>6} {adj:>6} {sig}")
    print(f"{'─'*75}")
    print("1M/3M/6M = probability of gaining ≥5%/10%/15% | Adj = score after all boosts")
    if not is_bull:
        print("⚠️  Bear market detected — scores reduced by 30%")


def run():
    print(f"\n{'='*65}")
    print(f"  Stock Analyzer — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*65}")

    print("\n[1/7] Detecting market regime...")
    regime = detect_regime()
    print(f"  {regime['regime']} | S&P vs 200MA: {regime['spy_vs_200ma']:+.1f}%")

    print("\n[2/7] Fetching market data...")
    data = fetch_all()
    if not data:
        print("No data fetched. Aborting.")
        return

    print("\n[3/7] Computing features...")
    features, prices = _build_features(data)
    print(f"  Features ready for {len(features)} assets.")

    if _should_retrain():
        print("\n[4/7] Training ML ensemble (LightGBM + XGBoost)...")
        models = train_models(features, prices)
    else:
        print("\n[4/7] Loading existing ML models...")
        models = load_models()

    if not models:
        print("No models available. Aborting.")
        return

    print("\n[5/7] Generating ML predictions...")
    predictions = predict(models, features)
    predictions["type"] = predictions["ticker"].apply(_asset_type)
    predictions["name"] = predictions["ticker"].map(TICKER_NAMES).fillna(predictions["ticker"])

    tickers = predictions["ticker"].tolist()

    print("\n[6/7] Fetching fundamentals & news sentiment...")
    fundamentals = fetch_all_fundamentals(tickers)
    sentiments = get_all_sentiments(tickers)
    sector_mom = compute_sector_momentum()

    predictions = _apply_boosts(predictions, fundamentals, sentiments, sector_mom, regime)

    print("\n[7/7] Saving results & sending Telegram...")
    current_prices = {t: float(prices[t].iloc[-1]) for t in prices if t in predictions["ticker"].values}
    save_prediction_prices(predictions, current_prices)
    update_outcomes()
    _save(predictions)
    _print_results(predictions, regime)
    send_daily_digest(predictions, regime)
    print(f"\nDone. Next scheduled run at {DAILY_RUN_TIME}.")


if __name__ == "__main__":
    once = "--once" in sys.argv
    run()
    if not once:
        schedule.every().day.at(DAILY_RUN_TIME).do(run)
        while True:
            schedule.run_pending()
            time.sleep(30)
