from datetime import datetime
import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator
from ta.volatility import BollingerBands
import requests
import sqlite3
import os
import matplotlib.pyplot as plt
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_telegram_message(message):
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


def log_to_database(symbol, time, close, rsi, stoch, macd_diff, ema20, ema50, bb_lower, bb_upper, signal):
    conn = sqlite3.connect("results.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            timestamp TEXT,
            close REAL,
            rsi REAL,
            stoch REAL,
            macd_diff REAL,
            ema20 REAL,
            ema50 REAL,
            bb_lower REAL,
            bb_upper REAL,
            signal TEXT
        )
    """)
    c.execute("""
        INSERT INTO analysis (symbol, timestamp, close, rsi, stoch, macd_diff, ema20, ema50, bb_lower, bb_upper, signal)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (symbol, time, close, rsi, stoch, macd_diff, ema20, ema50, bb_lower, bb_upper, signal))
    conn.commit()
    conn.close()


def plot_chart(symbol, close, bb_upper, bb_lower, ema20, ema50):
    if not os.path.exists("charts"):
        os.makedirs("charts")
    plt.figure(figsize=(10, 6))
    plt.plot(close.index, close, label="Close Price", linewidth=2, color='black')
    plt.plot(ema20.index, ema20, label="EMA-20", color="blue")
    plt.plot(ema50.index, ema50, label="EMA-50", color="orange")
    plt.plot(bb_upper.index, bb_upper, '--', label="BB Upper", color="green")
    plt.plot(bb_lower.index, bb_lower, '--', label="BB Lower", color="red")
    plt.title(f"{symbol} - Technical Chart")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    image_path = f"charts/{symbol}.png"   
    plt.savefig(image_path)
    plt.close()
    return image_path


def analyze_stock(symbol):
    print(f"\n📈 {symbol} — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    data = yf.download(symbol, period="10d", interval="1h", progress=False, auto_adjust=False)

    if data.empty or "Close" not in data:
        print(f"[{symbol}] ⚠️ No data found.")
        return None

    close = data["Close"].squeeze()
    high = data["High"].squeeze()
    low = data["Low"].squeeze()

    rsi = RSIIndicator(close=close).rsi()
    stoch = StochasticOscillator(close=close, high=high, low=low).stoch()
    macd_diff = MACD(close=close).macd_diff()
    ema20 = EMAIndicator(close=close, window=20).ema_indicator()
    ema50 = EMAIndicator(close=close, window=50).ema_indicator()
    bb = BollingerBands(close=close)
    bb_upper = bb.bollinger_hband()
    bb_lower = bb.bollinger_lband()

    latest_close = close.iloc[-1]
    latest_rsi = rsi.iloc[-1]
    latest_stoch = stoch.iloc[-1]
    latest_macd_diff = macd_diff.iloc[-1]
    latest_ema20 = ema20.iloc[-1]
    latest_ema50 = ema50.iloc[-1]
    latest_bb_upper = bb_upper.iloc[-1]
    latest_bb_lower = bb_lower.iloc[-1]

    if (
        latest_ema20 > latest_ema50
        and latest_rsi < 30
        and latest_stoch < 20
        and latest_close < latest_bb_lower
    ):
        signal = "🟢 STRONG BUY (Oversold + Trend)"
    elif (
        latest_ema20 < latest_ema50
        and latest_rsi > 70
        and latest_stoch > 80
        and latest_close > latest_bb_upper
    ):
        signal = "🔴 STRONG SELL (Overbought + Trend)"
    else:
        signal = "➡️ HOLD (Neutral/Mixed)"

    print(f"Close: {latest_close:.2f}")
    print(f"RSI: {latest_rsi:.2f} | Stoch: {latest_stoch:.2f} | MACD Δ: {latest_macd_diff:.4f}")
    print(f"EMA-20: {latest_ema20:.2f} | EMA-50: {latest_ema50:.2f}")
    print(f"Bollinger Bands: {latest_bb_lower:.2f} - {latest_bb_upper:.2f}")
    print(f"📊 Signal: {signal}")

    with open("results.txt", "a") as f:
        f.write(f"\n📈 {symbol} — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Close: {latest_close:.2f}\n")
        f.write(f"RSI: {latest_rsi:.2f} | Stoch: {latest_stoch:.2f} | MACD Δ: {latest_macd_diff:.4f}\n")
        f.write(f"EMA-20: {latest_ema20:.2f} | EMA-50: {latest_ema50:.2f}\n")
        f.write(f"Bollinger Bands: {latest_bb_lower:.2f} - {latest_bb_upper:.2f}\n")
        f.write(f"📊 Signal: {signal}\n")

    log_to_database(symbol, datetime.now().strftime('%Y-%m-%d %H:%M'), latest_close, latest_rsi, latest_stoch,
                    latest_macd_diff, latest_ema20, latest_ema50, latest_bb_lower, latest_bb_upper, signal)

    image_path = plot_chart(symbol, close, bb_upper, bb_lower, ema20, ema50)
    send_telegram_message(f"*{symbol}* - {datetime.now().strftime('%Y-%m-%d %H:%M')}\nSignal: {signal}")
    return image_path


if __name__ == "__main__":
    print("=== ADVANCED STOCK ANALYZER (HOURLY) ===")
    symbols = ["AAPL", "GOOGL", "MSFT", "NVDA", "AMZN", "TSLA", "AMD", "COIN", "LCID"]
    image_paths = {}

    for symbol in symbols:
        result = analyze_stock(symbol)
        if result:
            image_paths[symbol] = result

    if image_paths:
        print("\nAvailable plots:")
        for i, symbol in enumerate(image_paths.keys(), 1):
            print(f"{i}. {symbol}")

        choice = input("\nEnter the number of the stock to view its chart: ")
        try:
            index = int(choice) - 1
            selected_symbol = list(image_paths.keys())[index]
            selected_path = image_paths[selected_symbol]
            from PIL import Image
            Image.open(selected_path).show()
        except Exception as e:
            print(f"Invalid selection: {e}")