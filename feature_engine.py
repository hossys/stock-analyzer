import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator, StochasticOscillator, ROCIndicator
from ta.trend import MACD, EMAIndicator, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator

FEATURE_COLS = [
    # Price momentum
    "ret_1d", "ret_5d", "ret_20d", "ret_60d",
    # Oscillators
    "rsi_9", "rsi_14", "rsi_21",
    "macd_diff", "macd_signal", "macd_line",
    "bb_pct", "bb_width",
    # Trend
    "price_vs_ema20", "price_vs_ema50", "price_vs_ema200",
    "ema20_vs_ema50", "ema50_vs_ema200",
    # Volatility / volume
    "atr_pct", "stoch", "adx",
    "volume_ratio", "obv_slope",
    "roc_10", "roc_20",
    # Range
    "high_52w_ratio", "low_52w_ratio",
    # Seasonality
    "month", "day_of_week",
    # 12M-1M momentum (trend minus short-term reversal)
    "momentum_12m_1m",
    # Macro (filled in main.py from macro_features)
    "vix_level", "vix_chg_10d", "yield_10y", "yield_chg_20d", "dollar_chg_20d",
    # Relative strength vs sector (filled in main.py)
    "rs_20d", "rs_60d",
]


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    close = df["Close"].squeeze()
    high = df["High"].squeeze()
    low = df["Low"].squeeze()
    volume = df["Volume"].squeeze()

    f = pd.DataFrame(index=df.index)

    # Price momentum (returns)
    f["ret_1d"] = close.pct_change(1)
    f["ret_5d"] = close.pct_change(5)
    f["ret_20d"] = close.pct_change(20)
    f["ret_60d"] = close.pct_change(60)

    # RSI at three lookbacks
    f["rsi_9"] = RSIIndicator(close, window=9).rsi()
    f["rsi_14"] = RSIIndicator(close, window=14).rsi()
    f["rsi_21"] = RSIIndicator(close, window=21).rsi()

    # MACD
    macd = MACD(close)
    f["macd_diff"] = macd.macd_diff()
    f["macd_signal"] = macd.macd_signal()
    f["macd_line"] = macd.macd()

    # Bollinger Bands — position and width, not raw levels
    bb = BollingerBands(close)
    f["bb_pct"] = bb.bollinger_pband()
    f["bb_width"] = bb.bollinger_wband()

    # EMA trend (ratios, not raw values, so features are scale-invariant)
    ema20 = EMAIndicator(close, window=20).ema_indicator()
    ema50 = EMAIndicator(close, window=50).ema_indicator()
    ema200 = EMAIndicator(close, window=200).ema_indicator()
    f["price_vs_ema20"] = (close - ema20) / ema20
    f["price_vs_ema50"] = (close - ema50) / ema50
    f["price_vs_ema200"] = (close - ema200) / ema200
    f["ema20_vs_ema50"] = (ema20 - ema50) / ema50
    f["ema50_vs_ema200"] = (ema50 - ema200) / ema200

    # Volatility
    f["atr_pct"] = AverageTrueRange(high, low, close, window=14).average_true_range() / close

    # Stochastic
    f["stoch"] = StochasticOscillator(close, high, low).stoch()

    # Trend strength
    f["adx"] = ADXIndicator(high, low, close).adx()

    # Volume
    vol_avg = volume.rolling(20).mean()
    f["volume_ratio"] = volume / vol_avg.replace(0, np.nan)
    f["obv_slope"] = OnBalanceVolumeIndicator(close, volume).on_balance_volume().pct_change(10)

    # Rate of change
    f["roc_10"] = ROCIndicator(close, window=10).roc()
    f["roc_20"] = ROCIndicator(close, window=20).roc()

    # Position within 52-week range (scale-invariant)
    f["high_52w_ratio"] = close / close.rolling(252).max()
    f["low_52w_ratio"] = close / close.rolling(252).min()

    # Seasonality
    f["month"] = df.index.month.astype(float)
    f["day_of_week"] = df.index.dayofweek.astype(float)

    # 12M minus 1M momentum — one of the strongest known quant signals
    # Captures trend while avoiding short-term mean reversion
    f["momentum_12m_1m"] = close.pct_change(252) - close.pct_change(21)

    # Macro + relative strength — zeroed here, filled in main.py after all data is loaded
    for col in ["vix_level", "vix_chg_10d", "yield_10y", "yield_chg_20d",
                "dollar_chg_20d", "rs_20d", "rs_60d"]:
        f[col] = 0.0

    return f[FEATURE_COLS]
