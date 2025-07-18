import yfinance as yf
import pandas as pd
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands

def generate_dataset(symbol="AAPL", period="90d", interval="1h", future_window=2, threshold=0.01, output_file="dataset.csv"):
    data = yf.download(symbol, period=period, interval=interval, progress=False)

    if data.empty or "Close" not in data:
        print(f"No data for {symbol}")
        return

    data.dropna(inplace=True)

    close = data["Close"]
    high = data["High"]
    low = data["Low"]

    data["rsi"] = RSIIndicator(close).rsi()
    data["stoch"] = StochasticOscillator(close, high, low).stoch()
    data["macd_diff"] = MACD(close).macd_diff()
    data["ema20"] = EMAIndicator(close, window=20).ema_indicator()
    data["ema50"] = EMAIndicator(close, window=50).ema_indicator()
    bb = BollingerBands(close)
    data["bb_upper"] = bb.bollinger_hband()
    data["bb_lower"] = bb.bollinger_lband()

    data.dropna(inplace=True)

    future_returns = (data["Close"].shift(-future_window) - data["Close"]) / data["Close"]
    data["label"] = future_returns.apply(
        lambda x: 1 if x > threshold else (-1 if x < -threshold else 0)
    )

    data = data.dropna()
    selected_columns = [
        "Close", "rsi", "stoch", "macd_diff", "ema20", "ema50", "bb_upper", "bb_lower", "label"
    ]
    dataset = data[selected_columns]
    dataset.to_csv(output_file, index=False)
    print(f"✅ Dataset saved to {output_file} with {len(dataset)} rows.")

if name == "__main__":
    generate_dataset(symbol="AAPL")
