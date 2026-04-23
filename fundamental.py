import pickle
import time
from pathlib import Path
from datetime import date

import yfinance as yf

from config import CACHE_DIR

Path(CACHE_DIR).mkdir(exist_ok=True)

_WEEK = date.today().isocalendar()[1]


def _cache_path(ticker: str) -> Path:
    return Path(CACHE_DIR) / f"fund_{ticker}_w{_WEEK}.pkl"


def fetch_fundamentals(ticker: str) -> dict:
    cache = _cache_path(ticker)
    if cache.exists():
        return pickle.load(open(cache, "rb"))
    try:
        info = yf.Ticker(ticker).info
        data = {
            "pe_ratio":       info.get("trailingPE"),
            "forward_pe":     info.get("forwardPE"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth":info.get("earningsGrowth"),
            "profit_margin":  info.get("profitMargins"),
            "debt_to_equity": info.get("debtToEquity"),
            "roe":            info.get("returnOnEquity"),
            "price_to_book":  info.get("priceToBook"),
            "short_ratio":    info.get("shortRatio"),
        }
        pickle.dump(data, open(cache, "wb"))
        return data
    except Exception:
        return {}


def score_fundamentals(fund: dict) -> tuple[float, str, str]:
    """Returns (boost, quality_label, display_text)."""
    score = 0
    parts = []

    pe = fund.get("pe_ratio")
    if pe is not None:
        if 5 < pe < 25:
            score += 3
            parts.append(f"P/E {pe:.0f}✅")
        elif 25 <= pe <= 40:
            parts.append(f"P/E {pe:.0f}⚠️")
        elif pe > 40:
            score -= 4
            parts.append(f"P/E {pe:.0f}❌")

    margin = fund.get("profit_margin")
    if margin is not None:
        if margin > 0.20:
            score += 5
            parts.append(f"Margin {margin*100:.0f}%✅")
        elif margin > 0.08:
            score += 2
            parts.append(f"Margin {margin*100:.0f}%")
        elif margin < 0:
            score -= 8
            parts.append(f"Margin {margin*100:.0f}%❌")

    growth = fund.get("revenue_growth")
    if growth is not None:
        if growth > 0.15:
            score += 5
            parts.append(f"Rev+{growth*100:.0f}%✅")
        elif growth > 0.05:
            score += 2
            parts.append(f"Rev+{growth*100:.0f}%")
        elif growth < 0:
            score -= 4
            parts.append(f"Rev{growth*100:.0f}%❌")

    debt = fund.get("debt_to_equity")
    if debt is not None:
        if debt < 50:
            score += 2
        elif debt > 200:
            score -= 4
            parts.append(f"Debt/Eq {debt:.0f}❌")

    score = max(-15.0, min(15.0, float(score)))

    if score >= 8:
        label = "Strong 💪"
    elif score >= 2:
        label = "Solid"
    elif score >= -3:
        label = "Mixed"
    elif score >= -8:
        label = "Weak ⚠️"
    else:
        label = "Poor ❌"

    display = " | ".join(parts[:3]) if parts else "N/A"
    return score, label, display


def fetch_all_fundamentals(tickers: list[str]) -> dict[str, dict]:
    result = {}
    for i, ticker in enumerate(tickers, 1):
        print(f"  Fundamentals {ticker} ({i}/{len(tickers)})", end="\r")
        result[ticker] = fetch_fundamentals(ticker)
        time.sleep(0.05)
    print()
    return result
