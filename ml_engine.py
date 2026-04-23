import os
import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
import xgboost as xgb
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score

from config import HORIZONS, GAIN_THRESHOLDS, MODEL_DIR
from feature_engine import FEATURE_COLS

Path(MODEL_DIR).mkdir(exist_ok=True)

_LGB_PARAMS = dict(
    n_estimators=300,
    learning_rate=0.05,
    num_leaves=40,
    min_child_samples=40,
    subsample=0.8,
    colsample_bytree=0.8,
    class_weight="balanced",
    random_state=42,
    verbose=-1,
)


def _xgb_params(pos: int, neg: int) -> dict:
    return dict(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=5,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=neg / max(pos, 1),
        random_state=42,
        verbosity=0,
        eval_metric="logloss",
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
        merged.dropna(inplace=True)
        if len(merged) < 100 or merged["label"].sum() < 15:
            continue
        rows.append(merged)

    if not rows:
        return pd.DataFrame(), pd.Series(dtype=int)

    combined = pd.concat(rows).sort_index()
    return combined[FEATURE_COLS], combined["label"]


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

        pos = int(y.sum())
        neg = int(len(y) - pos)
        print(f"[{label}] {len(X):,} rows | positive rate: {y.mean():.1%}")

        # Walk-forward AUC using LightGBM (fast proxy for ensemble quality)
        tscv = TimeSeriesSplit(n_splits=3)
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

        # ── Stacking: generate out-of-fold predictions for meta-learner ──────
        tscv_stack = TimeSeriesSplit(n_splits=3)
        lgb_oof = np.zeros(len(y))
        xgb_oof = np.zeros(len(y))
        for tr_idx, vl_idx in tscv_stack.split(X):
            X_tr, X_vl = X.iloc[tr_idx], X.iloc[vl_idx]
            y_tr = y.iloc[tr_idx]
            pos_tr = int(y_tr.sum()); neg_tr = int(len(y_tr) - pos_tr)
            m_lgb = lgb.LGBMClassifier(**_LGB_PARAMS)
            m_lgb.fit(X_tr, y_tr)
            lgb_oof[vl_idx] = m_lgb.predict_proba(X_vl)[:, 1]
            m_xgb = xgb.XGBClassifier(**_xgb_params(pos_tr, neg_tr))
            m_xgb.fit(X_tr, y_tr)
            xgb_oof[vl_idx] = m_xgb.predict_proba(X_vl)[:, 1]

        meta = LogisticRegression(random_state=42, max_iter=500)
        meta.fit(np.column_stack([lgb_oof, xgb_oof]), y)
        meta_auc = roc_auc_score(y, meta.predict_proba(
            np.column_stack([lgb_oof, xgb_oof]))[:, 1])
        print(f"[{label}] Stacking meta AUC (OOF): {meta_auc:.3f}")

        # ── Final base models trained on all data ─────────────────────────
        lgb_model = lgb.LGBMClassifier(**_LGB_PARAMS)
        lgb_model.fit(X, y)
        xgb_model = xgb.XGBClassifier(**_xgb_params(pos, neg))
        xgb_model.fit(X, y)

        importance = pd.Series(lgb_model.feature_importances_, index=FEATURE_COLS)
        top5 = importance.nlargest(5).index.tolist()
        print(f"[{label}] Top features: {', '.join(top5)}")

        ensemble = {"lgb": lgb_model, "xgb": xgb_model, "meta": meta}
        path = os.path.join(MODEL_DIR, f"model_{label}.pkl")
        joblib.dump(ensemble, path)
        print(f"[{label}] Stacked ensemble saved to {path}")
        models[label] = ensemble

    return models


def load_models() -> dict:
    models = {}
    for label in HORIZONS:
        path = os.path.join(MODEL_DIR, f"model_{label}.pkl")
        if os.path.exists(path):
            models[label] = joblib.load(path)
    return models


def feature_count_matches() -> bool:
    """Check if saved models were trained on the current feature set."""
    path = os.path.join(MODEL_DIR, "model_3M.pkl")
    if not os.path.exists(path):
        return False
    try:
        ensemble = joblib.load(path)
        return ensemble["lgb"].n_features_in_ == len(FEATURE_COLS)
    except Exception:
        return False


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
        for label, ensemble in models.items():
            try:
                lgb_p = ensemble["lgb"].predict_proba(latest)[0][1]
                xgb_p = ensemble["xgb"].predict_proba(latest)[0][1]
                if "meta" in ensemble:
                    import numpy as _np
                    prob = ensemble["meta"].predict_proba(
                        _np.column_stack([[lgb_p], [xgb_p]]))[0][1]
                else:
                    prob = (lgb_p + xgb_p) / 2
                row[f"prob_{label}"] = round(prob * 100, 1)
            except Exception:
                row[f"prob_{label}"] = None
        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    p1 = df.get("prob_1M", pd.Series(0, index=df.index)).fillna(0)
    p3 = df.get("prob_3M", pd.Series(0, index=df.index)).fillna(0)
    p6 = df.get("prob_6M", pd.Series(0, index=df.index)).fillna(0)
    df["score"] = (p1 * 0.20 + p3 * 0.50 + p6 * 0.30).round(1)
    df.sort_values("score", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df
