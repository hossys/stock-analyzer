import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Stock Analyzer", page_icon="📈", layout="wide")

st.title("📈 Stock Analyzer — Buy Predictions")
st.caption("Probabilities of gaining ≥5% / ≥10% / ≥15% within 1 / 3 / 6 months.")


@st.cache_data(ttl=1800)
def load_predictions() -> pd.DataFrame:
    try:
        conn = sqlite3.connect("results.db")
        df = pd.read_sql("SELECT * FROM predictions ORDER BY timestamp DESC", conn)
        conn.close()
        latest = df["timestamp"].max()
        return df[df["timestamp"] == latest].copy()
    except Exception:
        return pd.DataFrame()


df = load_predictions()

if df.empty:
    st.warning("No predictions yet. Run `python main.py` first to generate predictions.")
    st.stop()

last_updated = df["timestamp"].iloc[0] if "timestamp" in df.columns else "unknown"
st.markdown(f"**Last updated:** {last_updated}")

# ── Filters ────────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    asset_types = ["All"] + sorted(df["type"].dropna().unique().tolist())
    selected_type = st.selectbox("Asset type", asset_types)

with col2:
    sort_horizon = st.selectbox("Sort by horizon", ["Score", "3M", "1M", "6M"])

with col3:
    min_score = st.slider("Min score", 0, 100, 30)

# ── Filter & sort ──────────────────────────────────────────────────────────────
filtered = df.copy()
if selected_type != "All":
    filtered = filtered[filtered["type"] == selected_type]

sort_col = "score" if sort_horizon == "Score" else f"prob_{sort_horizon}"
if sort_col in filtered.columns:
    filtered = filtered.sort_values(sort_col, ascending=False)

filtered = filtered[filtered["score"] >= min_score]

# ── Top picks table ────────────────────────────────────────────────────────────
st.subheader(f"Top picks ({len(filtered)} assets shown)")

display_cols = ["name", "ticker", "type", "prob_1M", "prob_3M", "prob_6M", "score"]
available = [c for c in display_cols if c in filtered.columns]
display = filtered[available].head(50).copy()

rename = {
    "name": "Name", "ticker": "Ticker", "type": "Type",
    "prob_1M": "1M %", "prob_3M": "3M %", "prob_6M": "6M %", "score": "Score",
}
display.rename(columns=rename, inplace=True)

st.dataframe(
    display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "1M %":   st.column_config.ProgressColumn("1M %",   min_value=0, max_value=100, format="%.1f%%"),
        "3M %":   st.column_config.ProgressColumn("3M %",   min_value=0, max_value=100, format="%.1f%%"),
        "6M %":   st.column_config.ProgressColumn("6M %",   min_value=0, max_value=100, format="%.1f%%"),
        "Score":  st.column_config.ProgressColumn("Score",  min_value=0, max_value=100, format="%.1f"),
    },
)

# ── Bar chart: top 15 by selected horizon ──────────────────────────────────────
st.subheader(f"Top 15 — {sort_horizon} probability")

chart_col = "score" if sort_horizon == "Score" else f"prob_{sort_horizon}"
if chart_col in filtered.columns:
    chart_data = filtered.head(15).set_index(
        "name" if "name" in filtered.columns else "ticker"
    )[[chart_col]].rename(columns={chart_col: sort_horizon})
    st.bar_chart(chart_data)

# ── By asset type breakdown ────────────────────────────────────────────────────
if "type" in filtered.columns:
    st.subheader("Breakdown by asset type")
    type_cols = st.columns(3)
    for i, atype in enumerate(["US Stock", "German Stock", "Crypto"]):
        subset = filtered[filtered["type"] == atype].head(5)
        with type_cols[i]:
            st.markdown(f"**{atype}**")
            if subset.empty:
                st.caption("No results.")
            else:
                label_col = "name" if "name" in subset.columns else "ticker"
                for _, row in subset.iterrows():
                    p3 = row.get("prob_3M", 0)
                    st.markdown(f"- **{row[label_col]}** — {p3:.1f}% (3M)")

st.divider()
st.caption("Not financial advice. Predictions are statistical estimates based on historical patterns.")
