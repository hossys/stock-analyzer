import pandas as pd
import yfinance as yf

from config import SECTOR_ETFS, CRYPTO


def detect_regime() -> dict:
    """Detect S&P 500 bull/bear regime using 50/200 EMA cross."""
    try:
        df = yf.download("^GSPC", period="2y", interval="1d",
                         progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close = df["Close"].squeeze()
        ema50 = close.ewm(span=50).mean()
        ema200 = close.ewm(span=200).mean()
        current = float(close.iloc[-1])
        e50 = float(ema50.iloc[-1])
        e200 = float(ema200.iloc[-1])
        distance_pct = (current - e200) / e200 * 100
        mom_1m = (current / float(close.iloc[-21]) - 1) * 100 if len(close) > 21 else 0
        is_bull = current > e200 and e50 > e200
        return {
            "is_bull": is_bull,
            "regime": "BULL 🟢" if is_bull else "BEAR 🔴",
            "spy_vs_200ma": round(distance_pct, 1),
            "mom_1m": round(mom_1m, 1),
            "score_multiplier": 1.0 if is_bull else 0.70,
        }
    except Exception as e:
        print(f"  Regime detection failed: {e}")
        return {"is_bull": True, "regime": "UNKNOWN", "spy_vs_200ma": 0,
                "mom_1m": 0, "score_multiplier": 1.0}


def compute_sector_momentum() -> dict[str, float]:
    """Return (price - EMA50) / EMA50 for each sector ETF."""
    momentum = {}
    for etf in SECTOR_ETFS:
        try:
            df = yf.download(etf, period="1y", interval="1d",
                             progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            close = df["Close"].squeeze()
            ema50 = close.ewm(span=50).mean()
            mom = (float(close.iloc[-1]) - float(ema50.iloc[-1])) / float(ema50.iloc[-1])
            momentum[etf] = round(mom, 4)
        except Exception:
            momentum[etf] = 0.0
    return momentum


def sector_boost(ticker: str, sector_mom: dict[str, float]) -> float:
    from config import SECTOR_MAP, CRYPTO
    etf = SECTOR_MAP.get(ticker)
    if etf is None:
        # crypto and German stocks: use BTC or EWG as proxy
        if ticker in CRYPTO:
            mom = sector_mom.get("BTC_PROXY", 0.0)
        else:
            mom = sector_mom.get("EWG", 0.0)
    else:
        mom = sector_mom.get(etf, 0.0)

    if mom > 0.06:
        return 8.0
    elif mom > 0.02:
        return 4.0
    elif mom < -0.06:
        return -8.0
    elif mom < -0.02:
        return -4.0
    return 0.0
