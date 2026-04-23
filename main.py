import os
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


def _save(predictions: pd.DataFrame):
    conn = sqlite3.connect(DB_PATH)
    predictions["timestamp"] = datetime.now().strftime("%Y-%m-%d")
    predictions.to_sql("predictions", conn, if_exists="append", index=False)
    conn.close()


def _models_exist() -> bool:
    return os.path.exists("models/model_3M.pkl")


def _should_retrain() -> bool:
    if not _models_exist():
        return True
    return datetime.now().weekday() == 0  # retrain every Monday


def _print_results(predictions: pd.DataFrame):
    top = predictions.head(TOP_N)
    print(f"\n{'─'*65}")
    print(f"{'RANK':<5} {'NAME':<22} {'TYPE':<14} {'1M':>6} {'3M':>6} {'6M':>6} {'SCORE':>7}")
    print(f"{'─'*65}")
    for rank, (_, row) in enumerate(top.iterrows(), 1):
        ticker = row["ticker"]
        name = TICKER_NAMES.get(ticker, ticker)[:20]
        asset_type = row.get("type", "")
        p1 = f"{row.get('prob_1M', 0):.1f}%"
        p3 = f"{row.get('prob_3M', 0):.1f}%"
        p6 = f"{row.get('prob_6M', 0):.1f}%"
        score = f"{row.get('score', 0):.1f}"
        print(f"{rank:<5} {name:<22} {asset_type:<14} {p1:>6} {p3:>6} {p6:>6} {score:>7}")
    print(f"{'─'*65}")
    print("Probabilities = P(price up ≥5%/10%/15% in 1M/3M/6M)")


def run():
    print(f"\n{'='*65}")
    print(f"  Stock Analyzer — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*65}")

    print("\n[1/4] Fetching market data...")
    data = fetch_all()
    if not data:
        print("No data fetched. Aborting.")
        return

    print("\n[2/4] Computing features...")
    features, prices = _build_features(data)
    print(f"  Features ready for {len(features)} assets.")

    if _should_retrain():
        print("\n[3/4] Training ML models (this takes a few minutes on first run)...")
        models = train_models(features, prices)
    else:
        print("\n[3/4] Loading existing ML models...")
        models = load_models()

    if not models:
        print("No models available. Aborting.")
        return

    print("\n[4/4] Generating predictions...")
    predictions = predict(models, features)
    predictions["type"] = predictions["ticker"].apply(_asset_type)
    predictions["name"] = predictions["ticker"].map(TICKER_NAMES).fillna(predictions["ticker"])

    _save(predictions)
    _print_results(predictions)
    send_daily_digest(predictions)
    print("\nDone. Next run scheduled for tomorrow at", DAILY_RUN_TIME)


if __name__ == "__main__":
    import sys
    once = "--once" in sys.argv
    run()
    if not once:
        schedule.every().day.at(DAILY_RUN_TIME).do(run)
        while True:
            schedule.run_pending()
            time.sleep(30)
