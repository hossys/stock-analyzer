import time
import pandas as pd
import yfinance as yf
from config import US_STOCKS


def get_insider_signal(ticker: str) -> dict:
    """Fetch SEC Form 4 insider transactions via yfinance. US stocks only."""
    if ticker not in US_STOCKS:
        return {"insider_boost": 0.0, "insider_label": ""}
    try:
        df = yf.Ticker(ticker).insider_transactions
        if df is None or df.empty:
            return {"insider_boost": 0.0, "insider_label": ""}

        # Find the text column (varies by yfinance version)
        text_col = next((c for c in ["Text", "Transaction", "Description"] if c in df.columns), None)
        val_col  = next((c for c in ["Value", "Total Value"] if c in df.columns), None)
        if text_col is None:
            return {"insider_boost": 0.0, "insider_label": ""}

        text     = df[text_col].astype(str).str.lower()
        is_buy   = text.str.contains("purchase|buy", na=False)
        is_sell  = text.str.contains("sale|sell", na=False)

        if val_col:
            buy_val  = pd.to_numeric(df.loc[is_buy,  val_col], errors="coerce").sum()
            sell_val = pd.to_numeric(df.loc[is_sell, val_col], errors="coerce").sum()
        else:
            buy_val, sell_val = float(is_buy.sum()), float(is_sell.sum())

        if buy_val > sell_val * 2 and buy_val > 50_000:
            return {"insider_boost": 12.0, "insider_label": "🟢 Insiders buying"}
        if sell_val > buy_val * 3 and sell_val > 50_000:
            return {"insider_boost": -8.0,  "insider_label": "🔴 Insiders selling"}
        return {"insider_boost": 0.0, "insider_label": ""}
    except Exception:
        return {"insider_boost": 0.0, "insider_label": ""}


def get_all_insider_signals(tickers: list[str]) -> dict[str, dict]:
    result = {}
    us = [t for t in tickers if t in US_STOCKS]
    for i, ticker in enumerate(us, 1):
        print(f"  Insider data {ticker} ({i}/{len(us)})", end="\r")
        result[ticker] = get_insider_signal(ticker)
        time.sleep(0.1)
    print()
    for ticker in tickers:
        result.setdefault(ticker, {"insider_boost": 0.0, "insider_label": ""})
    return result
