import os
import pickle
import time
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

from config import US_STOCKS, DE_STOCKS, CRYPTO, DATA_PERIOD, CACHE_DIR, MIN_DATA_ROWS

Path(CACHE_DIR).mkdir(exist_ok=True)


def _cache_path(ticker: str) -> Path:
    return Path(CACHE_DIR) / f"{ticker}_{date.today()}.pkl"


def _clean_old_cache():
    today = str(date.today())
    for f in Path(CACHE_DIR).glob("*.pkl"):
        if today not in f.name:
            f.unlink(missing_ok=True)


def _download(ticker: str) -> pd.DataFrame | None:
    cache = _cache_path(ticker)
    if cache.exists():
        return pickle.load(open(cache, "rb"))

    try:
        df = yf.download(ticker, period=DATA_PERIOD, interval="1d",
                         progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df.empty or len(df) < MIN_DATA_ROWS:
            return None
        df.index = pd.to_datetime(df.index)
        pickle.dump(df, open(cache, "wb"))
        return df
    except Exception as e:
        print(f"  [{ticker}] download failed: {e}")
        return None


def fetch_all() -> dict[str, pd.DataFrame]:
    _clean_old_cache()
    all_tickers = US_STOCKS + DE_STOCKS + CRYPTO
    result = {}
    total = len(all_tickers)
    for i, ticker in enumerate(all_tickers, 1):
        print(f"  Fetching {ticker} ({i}/{total})", end="\r")
        df = _download(ticker)
        if df is not None:
            result[ticker] = df
        time.sleep(0.1)  # avoid rate limiting
    print(f"\n  Loaded {len(result)}/{total} assets.")
    return result
