from datetime import datetime

import requests
import pandas as pd

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TICKER_NAMES, TOP_N

_TYPE_FLAG = {"US Stock": "🇺🇸", "German Stock": "🇩🇪", "Crypto": "🪙"}


def _signal(adj_score: float, is_bull: bool) -> str:
    if not is_bull and adj_score < 55:
        return "⚠️ CAUTION (bear market)"
    if adj_score >= 65:
        return "🔥 STRONG BUY"
    if adj_score >= 55:
        return "✅ BUY"
    return "👀 WATCH"


def _send(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
        }, timeout=15)
        if not r.ok:
            print(f"Telegram error {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"Telegram error: {e}")


def send_daily_digest(predictions: pd.DataFrame, regime: dict):
    today = datetime.now().strftime("%B %d, %Y")
    is_bull = regime.get("is_bull", True)
    regime_str = regime.get("regime", "UNKNOWN")
    spy_dist = regime.get("spy_vs_200ma", 0)
    spy_line = f"S&P 500 is *{abs(spy_dist):.1f}%* {'above' if spy_dist >= 0 else 'below'} its 200-day average"

    lines = [
        f"📊 *Stock Analyzer — {today}*",
        f"",
        f"🌍 *Market:* {regime_str}",
        f"   {spy_line}",
        f"{'   ⚠️ Bear market: all scores reduced — buy carefully.' if not is_bull else ''}",
        f"",
        f"━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🏆 *TOP PICKS TODAY*",
        f"━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    top = predictions.head(TOP_N)
    for rank, (_, row) in enumerate(top.iterrows(), 1):
        ticker = row["ticker"]
        name = TICKER_NAMES.get(ticker, ticker)
        flag = _TYPE_FLAG.get(row.get("type", ""), "📈")
        adj = row.get("adj_score", row.get("score", 0))
        signal = _signal(adj, is_bull)

        p1 = row.get("prob_1M", "—")
        p3 = row.get("prob_3M", "—")
        p6 = row.get("prob_6M", "—")

        fund_label = row.get("fund_label", "")
        fund_display = row.get("fund_display", "")
        sent_label = row.get("sentiment_label", "")

        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")

        lines += [
            f"",
            f"{medal} {flag} *{name}* (`{ticker}`)",
            f"   Signal: *{signal}*",
            f"   📈 Gain ≥5%  in 1 month:  *{p1}%*",
            f"   📈 Gain ≥10% in 3 months: *{p3}%*",
            f"   📈 Gain ≥15% in 6 months: *{p6}%*",
        ]
        if fund_label:
            lines.append(f"   💼 Fundamentals: {fund_label} — {fund_display}")
        if sent_label:
            lines.append(f"   📰 News sentiment: {sent_label}")

    lines += [
        f"",
        f"━━━━━━━━━━━━━━━━━━━━━━━━",
        f"_Probabilities = ML estimate based on 5 years of historical data._",
        f"_Not financial advice. Always do your own research._",
    ]

    # Telegram has a 4096 char limit — split if needed
    message = "\n".join(lines)
    if len(message) > 4000:
        # Send top 7 only if too long
        send_daily_digest(predictions.head(7), regime)
        return

    _send(message)
