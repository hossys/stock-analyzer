import time
from datetime import datetime, timedelta

import feedparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


def _score(text: str) -> float:
    """VADER compound score: -1 (very negative) to +1 (very positive)."""
    return _analyzer.polarity_scores(text)["compound"]


def get_sentiment(ticker: str, days_back: int = 7) -> dict:
    query = ticker.replace(".DE", "").replace(".F", "")
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={query}&region=US&lang=en-US"
    cutoff = datetime.now() - timedelta(days=days_back)

    total, count = 0.0, 0
    try:
        feed = feedparser.parse(url)
        for entry in feed.get("entries", []):
            try:
                pub = datetime(*entry.published_parsed[:6])
                if pub >= cutoff:
                    total += _score(entry.get("title", ""))
                    count += 1
            except Exception:
                continue
    except Exception:
        pass

    if count == 0:
        return {"sentiment_boost": 0.0, "sentiment_label": "Neutral 😐", "articles": 0}

    avg = total / count

    if avg >= 0.35:
        label, boost = "Positive 🟢", 8.0
    elif avg >= 0.10:
        label, boost = "Slightly Positive 🟡", 4.0
    elif avg <= -0.35:
        label, boost = "Negative 🔴", -10.0
    elif avg <= -0.10:
        label, boost = "Slightly Negative 🟠", -5.0
    else:
        label, boost = "Neutral 😐", 0.0

    return {"sentiment_boost": boost, "sentiment_label": label, "articles": count}


def get_all_sentiments(tickers: list[str]) -> dict[str, dict]:
    result = {}
    for i, ticker in enumerate(tickers, 1):
        print(f"  Sentiment {ticker} ({i}/{len(tickers)})", end="\r")
        result[ticker] = get_sentiment(ticker)
        time.sleep(0.1)
    print()
    return result
