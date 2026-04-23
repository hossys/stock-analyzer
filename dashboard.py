import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Stock Analyzer", page_icon="📈", layout="wide",
                   initial_sidebar_state="collapsed")

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stMetric"] { background:#1e2130; border-radius:10px; padding:12px; }
[data-testid="stMetricLabel"] { font-size:13px; color:#aaa; }
.signal-strong { color:#00c853; font-weight:bold; }
.signal-buy    { color:#69f0ae; }
.signal-watch  { color:#ffd740; }
.signal-risk   { color:#ff5252; }
.hint-box { background:#1e2130; border-left:4px solid #7c4dff;
            padding:12px 16px; border-radius:6px; margin:8px 0; font-size:13px; }
</style>
""", unsafe_allow_html=True)


# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=900)
def load_today() -> pd.DataFrame:
    try:
        conn = sqlite3.connect("results.db")
        df = pd.read_sql("SELECT * FROM predictions ORDER BY timestamp DESC", conn)
        conn.close()
        if df.empty:
            return pd.DataFrame()
        return df[df["timestamp"] == df["timestamp"].max()].copy()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=900)
def load_accuracy():
    try:
        conn = sqlite3.connect("results.db")
        row = conn.execute("""
            SELECT
                SUM(CASE WHEN hit_1M IS NOT NULL THEN 1 ELSE 0 END),
                ROUND(AVG(CASE WHEN hit_1M IS NOT NULL THEN hit_1M END)*100,1),
                SUM(CASE WHEN hit_3M IS NOT NULL THEN 1 ELSE 0 END),
                ROUND(AVG(CASE WHEN hit_3M IS NOT NULL THEN hit_3M END)*100,1),
                SUM(CASE WHEN hit_6M IS NOT NULL THEN 1 ELSE 0 END),
                ROUND(AVG(CASE WHEN hit_6M IS NOT NULL THEN hit_6M END)*100,1)
            FROM outcome_tracking
        """).fetchone()
        hist = pd.read_sql("""
            SELECT ticker, prediction_date, prob_3M, return_3M, hit_3M
            FROM outcome_tracking WHERE hit_3M IS NOT NULL
            ORDER BY prediction_date DESC LIMIT 50
        """, conn)
        conn.close()
        return row, hist
    except Exception:
        return None, pd.DataFrame()


def _signal(adj):
    if adj >= 65: return "🔥 STRONG BUY"
    if adj >= 55: return "✅ BUY"
    if adj >= 45: return "👀 WATCH"
    return "⏸️ HOLD"


def _signal_color(adj):
    if adj >= 65: return "signal-strong"
    if adj >= 55: return "signal-buy"
    if adj >= 45: return "signal-watch"
    return "signal-risk"


df = load_today()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 📈 Stock Analyzer")
if df.empty:
    st.warning("No predictions yet. Run `python main.py` first.")
    st.stop()

last_updated = df["timestamp"].iloc[0]
st.caption(f"Last updated: **{last_updated}** · {len(df)} assets analyzed")

# ── Market banner ─────────────────────────────────────────────────────────────
# ── Summary metrics ───────────────────────────────────────────────────────────
adj_col = "adj_score" if "adj_score" in df.columns else "score"
strong_buys = (df[adj_col] >= 65).sum()
buys        = ((df[adj_col] >= 55) & (df[adj_col] < 65)).sum()
top_pick    = df.iloc[0].get("name", df.iloc[0]["ticker"]) if not df.empty else "—"
top_score   = df.iloc[0].get(adj_col, 0) if not df.empty else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Assets Analyzed", f"{len(df)}", "US + German + Crypto")
c2.metric("🔥 Strong Buys", str(strong_buys), f"+ {buys} Buys")
c3.metric("⭐ Top Pick Today", top_pick, f"Score {top_score:.0f}")
c4.metric("📅 Date", last_updated)

st.divider()

# ── How to read this? ─────────────────────────────────────────────────────────
with st.expander("💡 How to read this? (click to expand)", expanded=False):
    st.markdown("""
<div class="hint-box">

**🔥 STRONG BUY** — AI + all signals (fundamentals, news, analysts, insiders) strongly agree. Highest confidence.<br>
**✅ BUY** — Good opportunity. Most signals are positive.<br>
**👀 WATCH** — Interesting but timing is not perfect yet. Keep an eye on it.<br><br>

**Probabilities** — The % is the AI's estimated chance that the stock reaches the target gain:<br>
- *1 Month → needs to gain ≥5%*<br>
- *3 Months → needs to gain ≥10%*<br>
- *6 Months → needs to gain ≥15%*<br><br>

**Adj. Score** — Final score combining: AI prediction + company health + news mood + analyst ratings + insider activity + options market + sector trend.<br><br>

**💼 Company Health (F-Score /9)** — Rates the company on 9 financial criteria (profitability, debt, growth). 7-9 = excellent, 4-6 = solid, 0-3 = weak.<br>
**📰 News Mood** — AI reads recent news headlines and rates them positive/negative.<br>
**🏢 Insider Activity** — Are company executives buying or selling their own stock? Buying is bullish.<br>
**🟢 Analyst Ratings** — What professional Wall Street analysts recommend.<br>
**⚡ Earnings Warning** — The company reports quarterly results soon. This makes short-term predictions less reliable.<br>
**🔴 High Put Buying** — Options traders are buying protection against a drop — a bearish signal from professionals.

</div>
""", unsafe_allow_html=True)

# ── Main tabs ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🏆 Today's Picks", "📊 Charts & Breakdown", "📐 Model Accuracy"])

# ════════════════════════════════════════════════════════════════════
with tab1:
    # Filters
    fc1, fc2, fc3 = st.columns([2, 2, 2])
    with fc1:
        types = ["All"] + sorted(df["type"].dropna().unique().tolist()) if "type" in df.columns else ["All"]
        sel_type = st.selectbox("Asset type", types)
    with fc2:
        sel_horizon = st.selectbox("Primary horizon", ["3M", "1M", "6M", "Score"])
    with fc3:
        min_score = st.slider("Min adjusted score", 0, 100, 30)

    filtered = df.copy()
    if sel_type != "All" and "type" in filtered.columns:
        filtered = filtered[filtered["type"] == sel_type]
    filtered = filtered[filtered.get(adj_col, filtered.get("score", 0)) >= min_score]
    sort_col = adj_col if sel_horizon == "Score" else f"prob_{sel_horizon}"
    if sort_col in filtered.columns:
        filtered = filtered.sort_values(sort_col, ascending=False)

    # ── Top 3 cards ──────────────────────────────────────────────────────────
    if not filtered.empty:
        st.subheader("🏅 Top 3 Picks")
        medals = ["🥇", "🥈", "🥉"]
        flag_map = {"US Stock": "🇺🇸", "German Stock": "🇩🇪", "Crypto": "🪙"}
        top3 = filtered.head(3)

        for (medal, (_, row)) in zip(medals, top3.iterrows()):
            adj     = row.get(adj_col) or 0
            signal  = _signal(adj)
            flag    = flag_map.get(row.get("type", ""), "📈")
            name    = row.get("name", row["ticker"])
            p1      = row.get("prob_1M") or 0
            p3      = row.get("prob_3M") or 0
            p6      = row.get("prob_6M") or 0

            with st.container(border=True):
                left, right = st.columns([3, 1])
                with left:
                    st.markdown(f"### {medal} {flag} {name} `{row['ticker']}`")
                    st.markdown(f"**Signal: {signal}** &nbsp;|&nbsp; Adjusted Score: **{adj:.0f}**")
                    prog_cols = st.columns(3)
                    prog_cols[0].metric("1 Month", f"{p1:.0f}%", "target +5%")
                    prog_cols[1].metric("3 Months", f"{p3:.0f}%", "target +10%")
                    prog_cols[2].metric("6 Months", f"{p6:.0f}%", "target +15%")
                with right:
                    details = []
                    fl = row.get("fund_label", "")
                    fd = row.get("fund_display", "")
                    if fl:  details.append(f"💼 **Company:** {fl}")
                    if fd and fd != "N/A": details.append(f"_{fd}_")
                    sl = row.get("sentiment_label", "")
                    if sl:  details.append(f"📰 **News:** {sl}")
                    al = row.get("analyst_label", "")
                    if al:  details.append(f"🟢 **Analysts:** {al}")
                    il = row.get("insider_label", "")
                    if il:  details.append(f"🏢 **Insiders:** {il}")
                    pl = row.get("pc_label", "")
                    if pl:  details.append(f"📊 **Options:** {pl}")
                    en = row.get("earnings_note", "")
                    if en:  details.append(f"{en}")
                    st.markdown("\n\n".join(details) if details else "_No additional signals_")

        st.divider()

    # ── Full ranked table ─────────────────────────────────────────────────────
    st.subheader(f"📋 Full Rankings ({len(filtered)} assets)")

    display_cols = ["name", "ticker", "type", "prob_1M", "prob_3M", "prob_6M",
                    adj_col, "fund_label", "sentiment_label", "analyst_label"]
    avail = [c for c in display_cols if c in filtered.columns]
    table = filtered[avail].head(50).copy()
    table[adj_col] = table[adj_col].fillna(0)

    rename = {"name": "Name", "ticker": "Ticker", "type": "Type",
              "prob_1M": "1M %", "prob_3M": "3M %", "prob_6M": "6M %",
              adj_col: "Score", "fund_label": "Company Health",
              "sentiment_label": "News", "analyst_label": "Analysts"}
    table.rename(columns=rename, inplace=True)

    col_cfg = {
        "1M %":   st.column_config.ProgressColumn("1M %",   min_value=0, max_value=100, format="%.0f%%"),
        "3M %":   st.column_config.ProgressColumn("3M %",   min_value=0, max_value=100, format="%.0f%%"),
        "6M %":   st.column_config.ProgressColumn("6M %",   min_value=0, max_value=100, format="%.0f%%"),
        "Score":  st.column_config.ProgressColumn("Score",  min_value=0, max_value=100, format="%.0f"),
    }
    st.dataframe(table, use_container_width=True, hide_index=True, column_config=col_cfg)

# ════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📊 Top 15 — Adjusted Score")
    chart_data = filtered.head(15).set_index(
        filtered.head(15).get("name", filtered.head(15)["ticker"])
        if "name" in filtered.columns else filtered.head(15)["ticker"]
    )[[adj_col]].rename(columns={adj_col: "Score"})
    st.bar_chart(chart_data)

    st.subheader("🌐 Signal Distribution by Asset Type")
    if "type" in filtered.columns:
        type_cols = st.columns(3)
        for i, atype in enumerate(["US Stock", "German Stock", "Crypto"]):
            sub = filtered[filtered["type"] == atype].head(8)
            with type_cols[i]:
                st.markdown(f"**{atype}**")
                if sub.empty:
                    st.caption("No results")
                else:
                    for _, r in sub.iterrows():
                        adj = r.get(adj_col) or 0
                        sig = "🔥" if adj >= 65 else ("✅" if adj >= 55 else "👀")
                        p3  = r.get("prob_3M") or 0
                        nm  = r.get("name", r["ticker"])
                        st.markdown(f"{sig} **{nm}** — {p3:.0f}% (3M)")

    st.subheader("📈 Probability Distribution")
    if "prob_3M" in filtered.columns:
        hist_data = filtered["prob_3M"].dropna()
        st.bar_chart(hist_data.value_counts(bins=10).sort_index())

# ════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("📐 Model Accuracy Tracking")
    st.caption("Fills in automatically as each prediction's horizon passes (1 / 3 / 6 months after the prediction date).")

    acc_row, acc_hist = load_accuracy()

    if acc_row and acc_row[0]:
        m1, m2, m3 = st.columns(3)
        m1.metric("1-Month accuracy", f"{acc_row[1] or 0:.1f}%",
                  f"{int(acc_row[0])} predictions resolved",
                  help="% of predictions where the stock actually gained ≥5% in 1 month")
        m2.metric("3-Month accuracy", f"{acc_row[3] or 0:.1f}%",
                  f"{int(acc_row[2])} predictions resolved",
                  help="% of predictions where the stock gained ≥10% in 3 months")
        m3.metric("6-Month accuracy", f"{acc_row[5] or 0:.1f}%",
                  f"{int(acc_row[4])} predictions resolved",
                  help="% of predictions where the stock gained ≥15% in 6 months")

        if not acc_hist.empty:
            st.dataframe(acc_hist, use_container_width=True, hide_index=True)
    else:
        st.info("📅 Accuracy data appears after the first horizon passes (1 month from today). "
                "Come back in a month to see how well the model performed!")

st.divider()
st.caption("⚠️ Not financial advice. Predictions are AI-generated estimates based on historical patterns. Always do your own research.")
