import requests
import pandas as pd
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TICKER_NAMES, TOP_N


def _send(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured — skipping notification.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        }, timeout=10)
        if not r.ok:
            print(f"Telegram error: {r.text}")
    except Exception as e:
        print(f"Telegram error: {e}")


def send_daily_digest(predictions: pd.DataFrame):
    top = predictions.head(TOP_N)
    lines = ["*📊 Daily Stock Picks — Top Buys*\n"]

    type_emoji = {"US Stock": "🇺🇸", "German Stock": "🇩🇪", "Crypto": "🪙"}

    for rank, (_, row) in enumerate(top.iterrows(), 1):
        ticker = row["ticker"]
        name = TICKER_NAMES.get(ticker, ticker)
        emoji = type_emoji.get(row.get("type", ""), "📈")
        p1 = row.get("prob_1M", "—")
        p3 = row.get("prob_3M", "—")
        p6 = row.get("prob_6M", "—")
        score = row.get("score", "—")

        lines.append(
            f"{rank}. {emoji} *{name}* (`{ticker}`)\n"
            f"   Score: *{score}* | 1M: {p1}% | 3M: {p3}% | 6M: {p6}%\n"
        )

    lines.append(
        "\n_Probabilities = chance of gaining 5%/10%/15%+ over 1/3/6 months._\n"
        "_Not financial advice._"
    )

    _send("\n".join(lines))
