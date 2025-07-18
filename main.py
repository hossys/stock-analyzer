from datetime import datetime
import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator
from ta.volatility import BollingerBands
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import requests

def send_telegram_message(message):
    """Send a message via Telegram bot."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram error: {e}")

def analyze_stock(symbol):
    print(f"\n📈 {symbol} — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    data = yf.download(symbol, period="10d", interval="1h", progress=False, auto_adjust=False)

    if data.empty or "Close" not in data:
        print(f"[{symbol}] ⚠️ No data found.")
        return

    # Ensure we have 1D Series
    close = data["Close"].squeeze()
    high = data["High"].squeeze()
    low = data["Low"].squeeze()

    # Indicators
    rsi = RSIIndicator(close=close).rsi()
    stoch = StochasticOscillator(close=close, high=high, low=low).stoch()
    macd_diff = MACD(close=close).macd_diff()
    ema20 = EMAIndicator(close=close, window=20).ema_indicator()
    ema50 = EMAIndicator(close=close, window=50).ema_indicator()
    bb = BollingerBands(close=close)
    bb_upper = bb.bollinger_hband()
    bb_lower = bb.bollinger_lband()

    # Get latest values
    latest_close = close.iloc[-1]
    latest_rsi = rsi.iloc[-1]
    latest_stoch = stoch.iloc[-1]
    latest_macd_diff = macd_diff.iloc[-1]
    latest_ema20 = ema20.iloc[-1]
    latest_ema50 = ema50.iloc[-1]
    latest_bb_upper = bb_upper.iloc[-1]
    latest_bb_lower = bb_lower.iloc[-1]

    # Signal logic
    if (
        latest_ema20 > latest_ema50
        and latest_rsi < 30
        and latest_stoch < 20
        and latest_close < latest_bb_lower
    ):
        signal = "🔼 STRONG SELL (Overbought + Trend)"
    elif (
        latest_ema20 < latest_ema50
        and latest_rsi > 70
        and latest_stoch > 80
        and latest_close > latest_bb_upper
    ):
        signal = "🔴 STRONG SELL (Overbought + Trend)"

    else:
        signal = "➡️ HOLD (Neutral/Mixed)"

    # Print results
    print(f"Close: {latest_close:.2f}")
    print(f"RSI: {latest_rsi:.2f} | Stoch: {latest_stoch:.2f} | MACD Δ: {latest_macd_diff:.4f}")
    print(f"EMA-20: {latest_ema20:.2f} | EMA-50: {latest_ema50:.2f}")
    print(f"Bollinger Bands: {latest_bb_lower:.2f} - {latest_bb_upper:.2f}")
    print(f"📊 Signal: {signal}")

    # Save to file
    with open("results.txt", "a") as f:
        f.write(f"\n📈 {symbol} — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Close: {latest_close:.2f}\n")
        f.write(f"RSI: {latest_rsi:.2f} | Stoch: {latest_stoch:.2f} | MACD Δ: {latest_macd_diff:.4f}\n")
        f.write(f"EMA-20: {latest_ema20:.2f} | EMA-50: {latest_ema50:.2f}\n")
        f.write(f"Bollinger Bands: {latest_bb_lower:.2f} - {latest_bb_upper:.2f}\n")
        f.write(f"📊 Signal: {signal}\n")

    print("=== ADVANCED STOCK ANALYZER (HOURLY) ===")
    symbols = ["AAPL", "GOOGL", "MSFT", "NVDA", "AMZN"]
    for symbol in symbols:
        analyze_stock(symbol)
