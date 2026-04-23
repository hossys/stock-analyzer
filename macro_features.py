import pickle
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

from config import CACHE_DIR, DATA_PERIOD

Path(CACHE_DIR).mkdir(exist_ok=True)

_MACRO_TICKERS = {"VIX": "^VIX", "TNX": "^TNX", "DXY": "DX-Y.NYB", "SPY": "^GSPC"}


def _cache_path() -> Path:
    return Path(CACHE_DIR) / f"macro_{date.today()}.pkl"


def fetch_macro() -> dict[str, pd.Series]:
    cache = _cache_path()
    if cache.exists():
        return pickle.load(open(cache, "rb"))

    result = {}
    for name, ticker in _MACRO_TICKERS.items():
        try:
            df = yf.download(ticker, period=DATA_PERIOD, interval="1d",
                             auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            result[name] = df["Close"].squeeze()
        except Exception as e:
            print(f"  Macro {name} failed: {e}")

    pickle.dump(result, open(cache, "wb"))
    return result


def build_macro_df(macro: dict[str, pd.Series], dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Align macro series to the given index, return feature DataFrame."""
    f = pd.DataFrame(index=dates)

    vix = macro.get("VIX")
    if vix is not None:
        v = vix.reindex(dates, method="ffill")
        f["vix_level"]   = v
        f["vix_chg_10d"] = v.pct_change(10)
    else:
        f["vix_level"]   = 0.0
        f["vix_chg_10d"] = 0.0

    tnx = macro.get("TNX")
    if tnx is not None:
        t = tnx.reindex(dates, method="ffill")
        f["yield_10y"]     = t
        f["yield_chg_20d"] = t.pct_change(20)
    else:
        f["yield_10y"]     = 0.0
        f["yield_chg_20d"] = 0.0

    dxy = macro.get("DXY")
    if dxy is not None:
        f["dollar_chg_20d"] = dxy.reindex(dates, method="ffill").pct_change(20)
    else:
        f["dollar_chg_20d"] = 0.0

    return f
