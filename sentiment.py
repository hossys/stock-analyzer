import re
import time
from datetime import datetime, timedelta

import feedparser

POSITIVE = {
    "beat", "beats", "record", "growth", "profit", "rise", "rises", "surge",
    "surges", "upgrade", "buy", "strong", "gain", "gains", "exceed", "exceeds",
    "above", "positive", "bullish", "outperform", "expand", "accelerate",
    "breakthrough", "launch", "partnership", "dividend", "buyback", "rally",
    "soar", "soars", "jump", "jumps", "upside", "recovery", "boom", "robust",
}

NEGATIVE = {
    "miss", "misses", "loss", "losses", "decline", "declines", "fall", "falls",
    "cut", "cuts", "downgrade", "sell", "weak", "below", "lawsuit", "investigation",
    "recall", "layoff", "layoffs", "bearish", "underperform", "warning", "fraud",
    "scandal", "crash", "drop", "drops", "disappointing", "concern", "risk",
    "plunge", "plunges", "tumble", "tumbles", "slump", "slumps", "bankruptcy",
}


def _score_headline(text: str) -> float:
    words = set(re.findall(r"\b\w+\b", text.lower()))
    return float(len(words & POSITIVE) - len(words & NEGATIVE))


def get_sentiment(ticker: str, days_back: int = 7) -> dict:
    total, count = 0.0, 0
    cutoff = datetime.now() - timedelta(days=days_back)

    # Use ticker as-is for US/crypto; strip .DE suffix for German stocks
    query_ticker = ticker.replace(".DE", "").replace(".F", "")
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={query_ticker}&region=US&lang=en-US"

    try:
        feed = feedparser.parse(url)
        for entry in feed.get("entries", []):
            try:
                pub = datetime(*entry.published_parsed[:6])
                if pub >= cutoff:
                    total += _score_headline(entry.get("title", ""))
                    count += 1
            except Exception:
                continue
    except Exception:
        pass

    if count == 0:
        return {"sentiment_boost": 0.0, "sentiment_label": "Neutral 😐", "articles": 0}

    avg = total / count
    if avg >= 0.5:
        label = "Positive 🟢"
        boost = 8.0
    elif avg >= 0.2:
        label = "Slightly Positive 🟡"
        boost = 4.0
    elif avg <= -0.5:
        label = "Negative 🔴"
        boost = -10.0
    elif avg <= -0.2:
        label = "Slightly Negative 🟠"
        boost = -5.0
    else:
        label = "Neutral 😐"
        boost = 0.0

    return {"sentiment_boost": boost, "sentiment_label": label, "articles": count}


def get_all_sentiments(tickers: list[str]) -> dict[str, dict]:
    result = {}
    for i, ticker in enumerate(tickers, 1):
        print(f"  Sentiment {ticker} ({i}/{len(tickers)})", end="\r")
        result[ticker] = get_sentiment(ticker)
        time.sleep(0.1)
    print()
    return result
