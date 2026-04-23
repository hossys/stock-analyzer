import time
import pandas as pd
import yfinance as yf
from config import US_STOCKS


def get_earnings_warning(ticker: str) -> dict:
    """Returns warning if earnings are within 14 days. US stocks only."""
    if ticker not in US_STOCKS:
        return {"earnings_warning": False, "earnings_note": ""}
    try:
        cal = yf.Ticker(ticker).calendar
        if cal is None:
            return {"earnings_warning": False, "earnings_note": ""}

        if isinstance(cal, dict):
            raw = cal.get("Earnings Date", [])
            if not raw:
                return {"earnings_warning": False, "earnings_note": ""}
            next_date = pd.Timestamp(raw[0] if isinstance(raw, list) else raw)
        elif isinstance(cal, pd.DataFrame) and not cal.empty:
            col = next((c for c in ["Earnings Date", "Earnings"] if c in cal.columns), None)
            if col is None:
                return {"earnings_warning": False, "earnings_note": ""}
            next_date = pd.Timestamp(cal[col].iloc[0])
        else:
            return {"earnings_warning": False, "earnings_note": ""}

        days = (next_date - pd.Timestamp.now()).days
        if 0 <= days <= 14:
            return {
                "earnings_warning": True,
                "earnings_note": f"⚡ Earnings in {days}d ({next_date.strftime('%b %d')}) — high uncertainty",
            }
    except Exception:
        pass
    return {"earnings_warning": False, "earnings_note": ""}


def get_all_earnings(tickers: list[str]) -> dict[str, dict]:
    result = {}
    us = [t for t in tickers if t in US_STOCKS]
    for i, ticker in enumerate(us, 1):
        print(f"  Earnings calendar {ticker} ({i}/{len(us)})", end="\r")
        result[ticker] = get_earnings_warning(ticker)
        time.sleep(0.05)
    print()
    for ticker in tickers:
        result.setdefault(ticker, {"earnings_warning": False, "earnings_note": ""})
    return result
