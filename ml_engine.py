import os
import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from pathlib import Path
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score

from config import HORIZONS, GAIN_THRESHOLDS, MODEL_DIR
from feature_engine import FEATURE_COLS

Path(MODEL_DIR).mkdir(exist_ok=True)

_LGB_PARAMS = dict(
    n_estimators=400,
    learning_rate=0.04,
    num_leaves=40,
    min_child_samples=40,
    subsample=0.8,
    colsample_bytree=0.8,
    class_weight="balanced",
    random_state=42,
    verbose=-1,
)


def _make_labels(close: pd.Series, horizon_days: int, threshold: float) -> pd.Series:
    future_return = close.shift(-horizon_days) / close - 1
    return (future_return >= threshold).astype(int)


def _pool_data(
    features_by_ticker: dict[str, pd.DataFrame],
    price_by_ticker: dict[str, pd.Series],
    horizon_days: int,
    threshold: float,
) -> tuple[pd.DataFrame, pd.Series]:
    rows = []
    for ticker, feat in features_by_ticker.items():
        close = price_by_ticker[ticker]
        labels = _make_labels(close, horizon_days, threshold)
        merged = feat[FEATURE_COLS].copy()
        merged["label"] = labels
        merged["_ticker"] = ticker
        merged.dropna(inplace=True)
        if len(merged) < 100 or merged["label"].sum() < 15:
            continue
        rows.append(merged)

    if not rows:
        return pd.DataFrame(), pd.Series(dtype=int)

    combined = pd.concat(rows).sort_index()
    X = combined[FEATURE_COLS]
    y = combined["label"]
    return X, y


def train_models(
    features_by_ticker: dict[str, pd.DataFrame],
    price_by_ticker: dict[str, pd.Series],
) -> dict:
    models = {}
    for label, horizon_days in HORIZONS.items():
        threshold = GAIN_THRESHOLDS[label]
        print(f"\n[{label}] Building training data (horizon={horizon_days}d, threshold={threshold*100:.0f}%)...")
        X, y = _pool_data(features_by_ticker, price_by_ticker, horizon_days, threshold)

        if X.empty:
            print(f"[{label}] Not enough data — skipping.")
            continue

        pos_rate = y.mean()
        print(f"[{label}] {len(X):,} rows | positive rate: {pos_rate:.1%}")

        # Walk-forward AUC to validate model before saving
        tscv = TimeSeriesSplit(n_splits=5)
        aucs = []
        for train_idx, val_idx in tscv.split(X):
            X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]
            if y_val.nunique() < 2:
                continue
            m = lgb.LGBMClassifier(**_LGB_PARAMS)
            m.fit(X_tr, y_tr)
            aucs.append(roc_auc_score(y_val, m.predict_proba(X_val)[:, 1]))

        mean_auc = np.mean(aucs) if aucs else 0.0
        print(f"[{label}] Walk-forward AUC: {mean_auc:.3f} ± {np.std(aucs):.3f}")

        # Final model: train on full dataset
        model = lgb.LGBMClassifier(**_LGB_PARAMS)
        model.fit(X, y)

        # Print top 5 features for transparency
        importance = pd.Series(model.feature_importances_, index=FEATURE_COLS)
        top5 = importance.nlargest(5).index.tolist()
        print(f"[{label}] Top features: {', '.join(top5)}")

        model_path = os.path.join(MODEL_DIR, f"model_{label}.pkl")
        joblib.dump(model, model_path)
        print(f"[{label}] Saved to {model_path}")
        models[label] = model

    return models


def load_models() -> dict:
    models = {}
    for label in HORIZONS:
        path = os.path.join(MODEL_DIR, f"model_{label}.pkl")
        if os.path.exists(path):
            models[label] = joblib.load(path)
    return models


def predict(
    models: dict,
    features_by_ticker: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    rows = []
    for ticker, feat in features_by_ticker.items():
        latest = feat[FEATURE_COLS].dropna().tail(1)
        if latest.empty:
            continue
        row = {"ticker": ticker}
        for label, model in models.items():
            try:
                prob = model.predict_proba(latest)[0][1]
                row[f"prob_{label}"] = round(prob * 100, 1)
            except Exception:
                row[f"prob_{label}"] = None
        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Composite score: 3M weighted most since user target is "few months"
    p1 = df.get("prob_1M", pd.Series(0, index=df.index)).fillna(0)
    p3 = df.get("prob_3M", pd.Series(0, index=df.index)).fillna(0)
    p6 = df.get("prob_6M", pd.Series(0, index=df.index)).fillna(0)
    df["score"] = (p1 * 0.20 + p3 * 0.50 + p6 * 0.30).round(1)
    df.sort_values("score", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df
