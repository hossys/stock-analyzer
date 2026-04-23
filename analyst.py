import time
import numpy as np
import pandas as pd
import yfinance as yf


def get_analyst_signal(ticker: str) -> dict:
    empty = {"analyst_boost": 0.0, "analyst_label": "", "analyst_summary": "N/A"}
    try:
        t = yf.Ticker(ticker)
        try:
            recs = t.get_recommendations_summary()
        except Exception:
            recs = t.recommendations

        if recs is None or (hasattr(recs, "empty") and recs.empty):
            return empty

        row = recs.iloc[0]

        def _get(names):
            for n in names:
                if n in row.index and pd.notna(row[n]):
                    return int(row[n])
            return 0

        sb = _get(["strongBuy",  "Strong Buy",  "STRONG_BUY"])
        b  = _get(["buy",        "Buy",         "BUY"])
        h  = _get(["hold",       "Hold",        "HOLD"])
        s  = _get(["sell",       "Sell",        "SELL"])
        ss = _get(["strongSell", "Strong Sell", "STRONG_SELL"])

        total = sb + b + h + s + ss
        if total == 0:
            return empty

        score      = (2 * sb + b - s - 2 * ss) / total
        buy_count  = sb + b
        sell_count = s + ss

        if score >= 1.2:
            return {"analyst_boost": 15.0,
                    "analyst_label": f"🟢 Strong Buy — {buy_count}/{total} analysts",
                    "analyst_summary": f"{buy_count}/{total} Buy"}
        elif score >= 0.4:
            return {"analyst_boost": 8.0,
                    "analyst_label": f"🟡 Buy — {buy_count}/{total} analysts",
                    "analyst_summary": f"{buy_count}/{total} Buy"}
        elif score <= -0.8:
            return {"analyst_boost": -12.0,
                    "analyst_label": f"🔴 Sell — {sell_count}/{total} analysts",
                    "analyst_summary": f"{sell_count}/{total} Sell"}
        else:
            return {"analyst_boost": 0.0,
                    "analyst_label": f"⚪ Mixed — {h}/{total} Hold",
                    "analyst_summary": "Mixed"}
    except Exception:
        return empty


def get_all_analyst_signals(tickers: list[str]) -> dict[str, dict]:
    result = {}
    for i, ticker in enumerate(tickers, 1):
        print(f"  Analyst ratings {ticker} ({i}/{len(tickers)})", end="\r")
        result[ticker] = get_analyst_signal(ticker)
        time.sleep(0.1)
    print()
    return result
