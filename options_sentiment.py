import time
import yfinance as yf
from config import US_STOCKS


def get_put_call_ratio(ticker: str) -> dict:
    """Options put/call ratio — US stocks only. High puts = bearish hedge."""
    empty = {"pc_boost": 0.0, "pc_label": ""}
    if ticker not in US_STOCKS:
        return empty
    try:
        t        = yf.Ticker(ticker)
        expiries = t.options
        if not expiries:
            return empty

        call_vol = put_vol = 0
        for exp in expiries[:3]:
            try:
                chain     = t.option_chain(exp)
                call_vol += chain.calls["volume"].fillna(0).sum()
                put_vol  += chain.puts["volume"].fillna(0).sum()
            except Exception:
                continue

        if call_vol == 0:
            return empty

        ratio = put_vol / call_vol

        if ratio > 1.5:
            return {"pc_boost": -10.0,
                    "pc_label": f"🔴 Heavy put buying (P/C {ratio:.1f}) — pros hedging a drop"}
        if ratio > 1.0:
            return {"pc_boost": -4.0,
                    "pc_label": f"🟠 Elevated puts (P/C {ratio:.1f})"}
        if ratio < 0.5:
            return {"pc_boost": 8.0,
                    "pc_label": f"🟢 Heavy call buying (P/C {ratio:.1f}) — bullish options flow"}
        if ratio < 0.7:
            return {"pc_boost": 4.0,
                    "pc_label": f"🟡 Slightly bullish options (P/C {ratio:.1f})"}
        return empty
    except Exception:
        return empty


def get_all_pc_ratios(tickers: list[str]) -> dict[str, dict]:
    result = {}
    us = [t for t in tickers if t in US_STOCKS]
    for i, ticker in enumerate(us, 1):
        print(f"  Options data {ticker} ({i}/{len(us)})", end="\r")
        result[ticker] = get_put_call_ratio(ticker)
        time.sleep(0.1)
    print()
    for ticker in tickers:
        result.setdefault(ticker, {"pc_boost": 0.0, "pc_label": ""})
    return result
