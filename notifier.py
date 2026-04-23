from datetime import datetime

import requests
import pandas as pd

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TICKER_NAMES, TOP_N

_FLAG  = {"US Stock": "🇺🇸", "German Stock": "🇩🇪", "Crypto": "🪙"}
_MEDAL = {1: "🥇", 2: "🥈", 3: "🥉"}


def _signal_text(adj_score: float, is_bull: bool) -> str:
    if not is_bull and adj_score < 55:
        return "⚠️ RISKY — Bear Market"
    if adj_score >= 65:
        return "🔥 STRONG BUY"
    if adj_score >= 55:
        return "✅ BUY"
    return "👀 WATCH"


def _market_summary(regime: dict) -> str:
    is_bull   = regime.get("is_bull", True)
    spy_dist  = regime.get("spy_vs_200ma", 0)
    direction = "above" if spy_dist >= 0 else "below"

    if is_bull:
        mood = "Healthy & Growing 🟢"
        note = "Good conditions for buying stocks."
    else:
        mood = "Weak / Declining 🔴"
        note = "⚠️ Be careful — the overall market is in a downtrend. Consider smaller positions."

    return (
        f"🌍 *Market Status:* {mood}\n"
        f"The S&P 500 is *{abs(spy_dist):.1f}%* {direction} its long-term average.\n"
        f"_{note}_"
    )


def _stock_block(rank: int, row: pd.Series) -> str:
    ticker    = row["ticker"]
    name      = TICKER_NAMES.get(ticker, ticker)
    flag      = _FLAG.get(row.get("type", ""), "📈")
    medal     = _MEDAL.get(rank, f"{rank}.")
    adj       = row.get("adj_score") or 0
    signal    = _signal_text(adj, True)

    p1 = row.get("prob_1M") or 0
    p3 = row.get("prob_3M") or 0
    p6 = row.get("prob_6M") or 0

    fund_label   = row.get("fund_label", "")
    sent_label   = row.get("sentiment_label", "")
    insider      = row.get("insider_label", "")
    earn_note    = row.get("earnings_note", "")

    lines = [
        f"{medal} {flag} *{name}* (`{ticker}`)",
        f"Signal: *{signal}*",
        f"",
        f"📈 *How likely is it to rise?*",
        f"  • In 1 month  → *{p1:.0f}%* chance of gaining ≥5%",
        f"  • In 3 months → *{p3:.0f}%* chance of gaining ≥10%",
        f"  • In 6 months → *{p6:.0f}%* chance of gaining ≥15%",
    ]

    if fund_label:
        lines += [f"", f"💼 *Company health:* {fund_label}"]

    if sent_label:
        lines.append(f"📰 *News mood:* {sent_label}")

    if insider:
        lines.append(f"🏢 *Insider activity:* {insider}")

    if earn_note:
        lines.append(f"{earn_note}")

    return "\n".join(lines)


def _hints_block() -> str:
    return (
        "💡 *Quick Guide*\n"
        "  🔥 STRONG BUY = All signals align — high confidence\n"
        "  ✅ BUY = Good opportunity\n"
        "  👀 WATCH = Interesting but not ideal timing yet\n"
        "  % = AI's estimated probability of reaching that gain\n"
        "  💼 Company health = Based on profit, growth & debt\n"
        "  📰 News mood = Recent headlines analyzed by AI\n"
        "  🏢 Insider activity = Are company executives buying or selling?\n"
        "  ⚡ Earnings = Company reports results soon → more volatile, higher risk\n"
        "  🇺🇸 = US stock  |  🇩🇪 = German stock  |  🪙 = Crypto"
    )


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
    today   = datetime.now().strftime("%B %d, %Y")
    is_bull = regime.get("is_bull", True)
    top     = predictions.head(TOP_N)

    # ── Header ───────────────────────────────────────────────────────────────
    parts = [
        f"📊 *Your Daily Stock Picks*",
        f"📅 {today}",
        f"",
        f"{'─' * 28}",
        _market_summary(regime),
        f"{'─' * 28}",
        f"",
        f"🏆 *TOP PICKS TODAY*",
        f"",
    ]

    # ── Top 5 full detail ────────────────────────────────────────────────────
    full_detail = top.head(5)
    for rank, (_, row) in enumerate(full_detail.iterrows(), 1):
        parts.append(_stock_block(rank, row))
        parts.append("")

    # ── Ranks 6-15 brief ─────────────────────────────────────────────────────
    rest = top.iloc[5:]
    if not rest.empty:
        parts.append(f"{'─' * 28}")
        parts.append("*Also worth watching:*")
        for rank, (_, row) in enumerate(rest.iterrows(), 6):
            ticker = row["ticker"]
            name   = TICKER_NAMES.get(ticker, ticker)
            flag   = _FLAG.get(row.get("type", ""), "📈")
            p3     = row.get("prob_3M") or 0
            adj    = row.get("adj_score") or 0
            sig    = "🔥" if adj >= 65 else ("✅" if adj >= 55 else "👀")
            parts.append(f"  {rank}. {flag} *{name}* — 3M: {p3:.0f}% {sig}")
        parts.append("")

    # ── Hints + disclaimer ───────────────────────────────────────────────────
    parts += [
        f"{'─' * 28}",
        _hints_block(),
        f"",
        f"{'─' * 28}",
        f"_⚠️ This is AI-generated analysis, not financial advice._",
        f"_Always do your own research before investing._",
    ]

    message = "\n".join(parts)

    # Telegram 4096 char limit — split into two messages if needed
    if len(message) <= 4090:
        _send(message)
    else:
        mid = message.rfind("\n", 0, 4090)
        _send(message[:mid])
        _send(message[mid:])
