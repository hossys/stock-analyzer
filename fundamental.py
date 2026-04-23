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


def _piotroski_score(fund: dict) -> int:
    """Simplified Piotroski F-Score (0-9). Higher = stronger fundamentals."""
    score = 0
    # Profitability
    if (fund.get("roe") or 0) > 0:                          score += 1  # positive ROE
    if (fund.get("profit_margin") or 0) > 0:                score += 1  # positive margin
    if (fund.get("revenue_growth") or 0) > 0:               score += 1  # growing revenue
    if (fund.get("earnings_growth") or 0) > 0:              score += 1  # growing earnings
    # Financial strength
    debt = fund.get("debt_to_equity") or 999
    if debt < 100:                                           score += 1  # low debt
    if (fund.get("current_ratio") or 0) > 1.0:              score += 1  # liquid
    # Valuation / efficiency
    pb = fund.get("price_to_book") or 999
    if 0 < pb < 5:                                           score += 1  # reasonable P/B
    pe = fund.get("pe_ratio") or 999
    if 0 < pe < 30:                                          score += 1  # reasonable P/E
    fpe = fund.get("forward_pe") or 999
    if 0 < fpe < pe:                                         score += 1  # forward P/E improving
    return score


def score_fundamentals(fund: dict) -> tuple[float, str, str]:
    """Returns (boost, quality_label, display_text) using Piotroski-inspired scoring."""
    if not fund:
        return 0.0, "", "N/A"

    piotroski = _piotroski_score(fund)   # 0-9
    # Map 0-9 → -15 to +15 boost
    boost = round((piotroski - 4.5) / 4.5 * 15, 1)
    boost = max(-15.0, min(15.0, boost))

    # Human-readable label
    if piotroski >= 7:
        label = "Excellent 💪"
    elif piotroski >= 5:
        label = "Solid ✅"
    elif piotroski >= 3:
        label = "Mixed ⚠️"
    else:
        label = "Weak ❌"

    # Build short display string from available data
    parts = []
    pe = fund.get("pe_ratio")
    if pe:
        parts.append(f"P/E {pe:.0f}")
    margin = fund.get("profit_margin")
    if margin is not None:
        parts.append(f"Margin {margin*100:.0f}%")
    growth = fund.get("revenue_growth")
    if growth is not None:
        sign = "+" if growth >= 0 else ""
        parts.append(f"Rev {sign}{growth*100:.0f}%")
    display = " | ".join(parts[:3]) if parts else "N/A"
    display += f" (F-Score {piotroski}/9)"
    return boost, label, display


def fetch_all_fundamentals(tickers: list[str]) -> dict[str, dict]:
    result = {}
    for i, ticker in enumerate(tickers, 1):
        print(f"  Fundamentals {ticker} ({i}/{len(tickers)})", end="\r")
        result[ticker] = fetch_fundamentals(ticker)
        time.sleep(0.05)
    print()
    return result
