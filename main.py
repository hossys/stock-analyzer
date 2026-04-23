import os
import sys
import sqlite3
import schedule
import time
from datetime import datetime

import pandas as pd

from config import (
    US_STOCKS, DE_STOCKS, CRYPTO, SECTOR_MAP,
    TICKER_NAMES, DB_PATH, TOP_N, DAILY_RUN_TIME,
)
from data_fetcher import fetch_all
from feature_engine import compute_features, FEATURE_COLS
from ml_engine import train_models, load_models, predict, feature_count_matches
from macro_features import fetch_macro, build_macro_df
from fundamental import fetch_all_fundamentals, score_fundamentals
from sentiment import get_all_sentiments
from insider import get_all_insider_signals
from earnings import get_all_earnings
from analyst import get_all_analyst_signals
from options_sentiment import get_all_pc_ratios
from market_regime import detect_regime, compute_sector_momentum, sector_boost
from outcome_tracker import save_prediction_prices, update_outcomes
from notifier import send_daily_digest


def _asset_type(ticker: str) -> str:
    if ticker in US_STOCKS:   return "US Stock"
    if ticker in DE_STOCKS:   return "German Stock"
    return "Crypto"


def _benchmark_for(ticker: str, prices: dict) -> pd.Series | None:
    """Return the benchmark price series for computing relative strength."""
    etf = SECTOR_MAP.get(ticker)
    if etf and etf in prices:
        return prices[etf]
    if ticker in DE_STOCKS and "EWG" in prices:
        return prices["EWG"]
    if ticker in CRYPTO and "BTC-USD" in prices and ticker != "BTC-USD":
        return prices["BTC-USD"]
    return None


def _build_features(data: dict, macro_data: dict) -> tuple[dict, dict]:
    features, prices = {}, {}
    all_dates = pd.DatetimeIndex(sorted(set().union(*[df.index for df in data.values()])))
    macro_df = build_macro_df(macro_data, all_dates)

    for ticker, df in data.items():
        try:
            feat = compute_features(df)

            # Inject macro features (aligned by date)
            for col in ["vix_level", "vix_chg_10d", "yield_10y", "yield_chg_20d", "dollar_chg_20d"]:
                if col in macro_df.columns:
                    feat[col] = macro_df[col].reindex(feat.index, method="ffill")

            features[ticker] = feat
            prices[ticker] = df["Close"].squeeze()
        except Exception as e:
            print(f"  [{ticker}] feature error: {e}")

    # Relative strength vs sector (vectorized per ticker)
    for ticker, feat in features.items():
        bench = _benchmark_for(ticker, prices)
        stock = prices.get(ticker)
        if bench is not None and stock is not None:
            bench_aligned = bench.reindex(stock.index, method="ffill")
            rs20 = stock.pct_change(20) - bench_aligned.pct_change(20)
            rs60 = stock.pct_change(60) - bench_aligned.pct_change(60)
            feat["rs_20d"] = rs20.reindex(feat.index, method="ffill")
            feat["rs_60d"] = rs60.reindex(feat.index, method="ffill")

    return features, prices


def _apply_boosts(predictions, fundamentals, sentiments, insiders, earnings_data,
                  analysts, pc_ratios, sector_mom, regime) -> pd.DataFrame:
    predictions = predictions.copy()
    cols = {
        "fund_score": [], "fund_label": [], "fund_display": [],
        "sent_boost": [], "sentiment_label": [],
        "insider_boost": [], "insider_label": [],
        "analyst_boost": [], "analyst_label": [],
        "pc_boost": [], "pc_label": [],
        "sector_boost_val": [],
        "earnings_warning": [], "earnings_note": [],
    }

    for _, row in predictions.iterrows():
        t = row["ticker"]

        fs, fl, fd = score_fundamentals(fundamentals.get(t, {}))
        cols["fund_score"].append(fs)
        cols["fund_label"].append(fl)
        cols["fund_display"].append(fd)

        s = sentiments.get(t, {})
        cols["sent_boost"].append(s.get("sentiment_boost", 0.0))
        cols["sentiment_label"].append(s.get("sentiment_label", "Neutral 😐"))

        ins = insiders.get(t, {})
        cols["insider_boost"].append(ins.get("insider_boost", 0.0))
        cols["insider_label"].append(ins.get("insider_label", ""))

        an = analysts.get(t, {})
        cols["analyst_boost"].append(an.get("analyst_boost", 0.0))
        cols["analyst_label"].append(an.get("analyst_label", ""))

        pc = pc_ratios.get(t, {})
        cols["pc_boost"].append(pc.get("pc_boost", 0.0))
        cols["pc_label"].append(pc.get("pc_label", ""))

        cols["sector_boost_val"].append(sector_boost(t, sector_mom))

        earn = earnings_data.get(t, {})
        cols["earnings_warning"].append(earn.get("earnings_warning", False))
        cols["earnings_note"].append(earn.get("earnings_note", ""))

    for k, v in cols.items():
        predictions[k] = v

    raw = (
        predictions["score"]
        + predictions["fund_score"]
        + predictions["sent_boost"]
        + predictions["insider_boost"]
        + predictions["analyst_boost"]
        + predictions["pc_boost"]
        + predictions["sector_boost_val"]
    )
    earnings_penalty = predictions["earnings_warning"].map({True: 0.70, False: 1.0})
    multiplier = regime.get("score_multiplier", 1.0)
    predictions["adj_score"] = (raw * multiplier * earnings_penalty).round(1)
    predictions.sort_values("adj_score", ascending=False, inplace=True)
    predictions.reset_index(drop=True, inplace=True)
    return predictions


def _should_retrain() -> bool:
    if not feature_count_matches():
        print("  Feature set changed — retraining.")
        return True
    return datetime.now().weekday() == 0   # every Monday


def _save(predictions: pd.DataFrame):
    conn = sqlite3.connect(DB_PATH)
    df = predictions.copy()
    df["timestamp"] = datetime.now().strftime("%Y-%m-%d")
    try:
        df.to_sql("predictions", conn, if_exists="append", index=False)
    except Exception:
        conn.execute("DROP TABLE IF EXISTS predictions")
        df.to_sql("predictions", conn, if_exists="replace", index=False)
    conn.close()


def _print_results(predictions: pd.DataFrame, regime: dict):
    print(f"\n  Market: {regime.get('regime','?')} | "
          f"S&P vs 200MA: {regime.get('spy_vs_200ma', 0):+.1f}%")
    print(f"\n{'─'*78}")
    print(f"{'#':<4} {'Name':<20} {'Type':<14} {'1M':>5} {'3M':>5} {'6M':>5} "
          f"{'Base':>5} {'Adj':>5}  Signal")
    print(f"{'─'*78}")
    for rank, (_, row) in enumerate(predictions.head(TOP_N).iterrows(), 1):
        name = TICKER_NAMES.get(row["ticker"], row["ticker"])[:18]
        p1   = f"{row.get('prob_1M') or 0:.0f}%"
        p3   = f"{row.get('prob_3M') or 0:.0f}%"
        p6   = f"{row.get('prob_6M') or 0:.0f}%"
        base = f"{row.get('score') or 0:.0f}"
        adj  = f"{row.get('adj_score') or 0:.0f}"
        adj_val = row.get("adj_score") or 0
        sig  = "🔥 STRONG BUY" if adj_val >= 65 else ("✅ BUY" if adj_val >= 55 else "👀 WATCH")
        warn = " ⚡earnings" if row.get("earnings_warning") else ""
        ins  = f" {row.get('insider_label','')}" if row.get("insider_label") else ""
        print(f"{rank:<4} {name:<20} {row.get('type',''):<14} "
              f"{p1:>5} {p3:>5} {p6:>5} {base:>5} {adj:>5}  {sig}{warn}{ins}")
    print(f"{'─'*78}")
    print("1M/3M/6M = P(gain ≥5%/10%/15%) | Adj = after macro+fundamentals+sentiment+insider boosts")
    if not regime.get("is_bull", True):
        print("⚠️  Bear market — all scores reduced 30%")


def run():
    print(f"\n{'='*65}")
    print(f"  Stock Analyzer — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*65}")

    print("\n[1/8] Detecting market regime...")
    regime = detect_regime()
    print(f"  {regime['regime']} | S&P vs 200MA: {regime['spy_vs_200ma']:+.1f}%")

    print("\n[2/8] Fetching market + macro data...")
    data = fetch_all()
    macro_data = fetch_macro()
    if not data:
        print("No data fetched. Aborting.")
        return

    print("\n[3/8] Computing features (technical + macro + relative strength)...")
    features, prices = _build_features(data, macro_data)
    print(f"  Features ready for {len(features)} assets ({len(FEATURE_COLS)} features each).")

    if _should_retrain():
        print("\n[4/8] Training LightGBM + XGBoost ensemble...")
        models = train_models(features, prices)
    else:
        print("\n[4/8] Loading existing ML models...")
        models = load_models()

    if not models:
        print("No models available. Aborting.")
        return

    print("\n[5/8] Generating ML predictions...")
    predictions = predict(models, features)
    predictions["type"] = predictions["ticker"].apply(_asset_type)
    predictions["name"] = predictions["ticker"].map(TICKER_NAMES).fillna(predictions["ticker"])

    tickers = predictions["ticker"].tolist()

    print("\n[6/8] Fetching fundamentals, sentiment & sector momentum...")
    fundamentals = fetch_all_fundamentals(tickers)
    sentiments   = get_all_sentiments(tickers)
    sector_mom   = compute_sector_momentum()

    print("\n[7/8] Fetching insider signals, analyst ratings, options & earnings...")
    insiders      = get_all_insider_signals(tickers)
    earnings_data = get_all_earnings(tickers)
    analysts      = get_all_analyst_signals(tickers)
    pc_ratios     = get_all_pc_ratios(tickers)

    predictions = _apply_boosts(
        predictions, fundamentals, sentiments, insiders,
        earnings_data, analysts, pc_ratios, sector_mom, regime,
    )

    print("\n[8/8] Saving results & sending Telegram...")
    current_prices = {t: float(prices[t].iloc[-1]) for t in prices
                      if t in predictions["ticker"].values}
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
