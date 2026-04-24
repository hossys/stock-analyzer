import pickle
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

from config import US_STOCKS, DE_STOCKS, CRYPTO, ETFS, DATA_PERIOD, CACHE_DIR, MIN_DATA_ROWS

Path(CACHE_DIR).mkdir(exist_ok=True)

_GROUPS = [
    ("US Stocks",      US_STOCKS),
    ("German Stocks",  DE_STOCKS),
    ("Crypto",         CRYPTO),
    ("ETFs",           ETFS),
]


def _cache_path(group_name: str) -> Path:
    return Path(CACHE_DIR) / f"batch_{group_name.replace(' ', '_')}_{date.today()}.pkl"


def _clean_old_cache():
    today = str(date.today())
    for f in Path(CACHE_DIR).glob("batch_*.pkl"):
        if today not in f.name:
            f.unlink(missing_ok=True)


def _download_group(name: str, tickers: list[str]) -> dict[str, pd.DataFrame]:
    cache = _cache_path(name)
    if cache.exists():
        print(f"  {name}: loaded from cache.")
        return pickle.load(open(cache, "rb"))

    print(f"  {name}: downloading {len(tickers)} tickers...", end="\r")
    try:
        raw = yf.download(
            tickers, period=DATA_PERIOD, interval="1d",
            auto_adjust=True, progress=False,
        )
    except Exception as e:
        print(f"  {name}: batch download failed ({e}), skipping.")
        return {}

    result = {}
    fields = ["Open", "High", "Low", "Close", "Volume"]

    for ticker in tickers:
        try:
            if len(tickers) == 1:
                df = raw[fields].dropna(how="all")
            else:
                df = pd.DataFrame(
                    {f: raw[f][ticker] for f in fields if f in raw}
                ).dropna(how="all")

            if len(df) >= MIN_DATA_ROWS:
                result[ticker] = df
        except Exception:
            continue

    print(f"  {name}: {len(result)}/{len(tickers)} assets ready.     ")
    pickle.dump(result, open(cache, "wb"))
    return result


def fetch_all() -> dict[str, pd.DataFrame]:
    _clean_old_cache()
    combined = {}
    for name, tickers in _GROUPS:
        combined.update(_download_group(name, tickers))
    print(f"  Total: {len(combined)} assets loaded.")
    return combined
