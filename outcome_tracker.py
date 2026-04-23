import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from config import DB_PATH

_HORIZONS = {"1M": 30, "3M": 91, "6M": 182}   # calendar days
_THRESHOLDS = {"1M": 0.05, "3M": 0.10, "6M": 0.15}


def _init(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS outcome_tracking (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker          TEXT,
            prediction_date TEXT,
            price_at_pred   REAL,
            prob_1M         REAL,
            prob_3M         REAL,
            prob_6M         REAL,
            price_1M        REAL,
            price_3M        REAL,
            price_6M        REAL,
            return_1M       REAL,
            return_3M       REAL,
            return_6M       REAL,
            hit_1M          INTEGER,
            hit_3M          INTEGER,
            hit_6M          INTEGER
        )
    """)
    conn.commit()


def save_prediction_prices(predictions: pd.DataFrame, current_prices: dict):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    _init(conn)
    # Avoid duplicate entries for the same ticker+date
    existing = pd.read_sql(
        "SELECT ticker FROM outcome_tracking WHERE prediction_date = ?",
        conn, params=(today,)
    )["ticker"].tolist()

    for _, row in predictions.iterrows():
        ticker = row["ticker"]
        if ticker in existing:
            continue
        price = current_prices.get(ticker)
        if price is None:
            continue
        conn.execute("""
            INSERT INTO outcome_tracking
                (ticker, prediction_date, price_at_pred, prob_1M, prob_3M, prob_6M)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            ticker, today, float(price),
            row.get("prob_1M"), row.get("prob_3M"), row.get("prob_6M"),
        ))
    conn.commit()
    conn.close()


def update_outcomes():
    """Fill in actual prices once each horizon has elapsed."""
    conn = sqlite3.connect(DB_PATH)
    _init(conn)
    pending = pd.read_sql("""
        SELECT id, ticker, prediction_date, price_at_pred
        FROM outcome_tracking
        WHERE price_at_pred IS NOT NULL
          AND (hit_1M IS NULL OR hit_3M IS NULL OR hit_6M IS NULL)
    """, conn)
    conn.close()

    if pending.empty:
        return

    today = datetime.now()
    updates = []
    for _, row in pending.iterrows():
        pred_date = datetime.strptime(row["prediction_date"], "%Y-%m-%d")
        for label, cal_days in _HORIZONS.items():
            target = pred_date + timedelta(days=cal_days)
            if today < target:
                continue
            col_price = f"price_{label}"
            col_ret = f"return_{label}"
            col_hit = f"hit_{label}"
            # Check if already filled
            conn2 = sqlite3.connect(DB_PATH)
            val = conn2.execute(
                f"SELECT {col_price} FROM outcome_tracking WHERE id = ?", (row["id"],)
            ).fetchone()
            conn2.close()
            if val and val[0] is not None:
                continue
            try:
                df = yf.download(
                    row["ticker"],
                    start=target.strftime("%Y-%m-%d"),
                    end=(target + timedelta(days=7)).strftime("%Y-%m-%d"),
                    interval="1d", progress=False, auto_adjust=True,
                )
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                if df.empty:
                    continue
                actual = float(df["Close"].iloc[0])
                ret = (actual / row["price_at_pred"] - 1) * 100
                hit = 1 if ret >= _THRESHOLDS[label] * 100 else 0
                conn3 = sqlite3.connect(DB_PATH)
                conn3.execute(
                    f"UPDATE outcome_tracking SET {col_price}=?, {col_ret}=?, {col_hit}=? WHERE id=?",
                    (actual, round(ret, 2), hit, row["id"]),
                )
                conn3.commit()
                conn3.close()
            except Exception as e:
                print(f"  Outcome update failed {row['ticker']} {label}: {e}")


def get_accuracy() -> dict:
    try:
        conn = sqlite3.connect(DB_PATH)
        _init(conn)
        df = pd.read_sql("""
            SELECT
                COUNT(hit_1M) as n_1M, ROUND(AVG(hit_1M)*100,1) as acc_1M,
                COUNT(hit_3M) as n_3M, ROUND(AVG(hit_3M)*100,1) as acc_3M,
                COUNT(hit_6M) as n_6M, ROUND(AVG(hit_6M)*100,1) as acc_6M
            FROM outcome_tracking
            WHERE hit_1M IS NOT NULL OR hit_3M IS NOT NULL OR hit_6M IS NOT NULL
        """, conn)
        conn.close()
        if df.empty:
            return {}
        return df.iloc[0].to_dict()
    except Exception:
        return {}
