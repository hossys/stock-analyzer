import os
import sys
import json
import sqlite3
import schedule
import time
from datetime import datetime

import pandas as pd

from config import (
    US_STOCKS, DE_STOCKS, CRYPTO, ETFS, SECTOR_MAP,
    TICKER_NAMES, DB_PATH, TOP_N, DAILY_RUN_TIME,
)
from data_fetcher import fetch_all
from feature_engine import compute_features, FEATURE_COLS
from ml_engine import train_models, load_models, predict, feature_count_matches
from macro_features import fetch_macro, build_macro_df
from fundamental import fetch_all_fundamentals, score_fundamentals
from sentiment import get_all_sentiments
from insider import get_all_insider_signals
from earnings import get_all_earnings
from analyst import get_all_analyst_signals
from options_sentiment import get_all_pc_ratios
from market_regime import detect_regime, compute_sector_momentum, sector_boost
from outcome_tracker import save_prediction_prices, update_outcomes
from notifier import send_daily_digest


def _asset_type(ticker: str) -> str:
    if ticker in ETFS:        return "ETF"
    if ticker in US_STOCKS:   return "US Stock"
    if ticker in DE_STOCKS:   return "German Stock"
    return "Crypto"


def _benchmark_for(ticker: str, prices: dict) -> pd.Series | None:
    """Return the benchmark price series for computing relative strength."""
    etf = SECTOR_MAP.get(ticker)
    if etf and etf in prices:
        return prices[etf]
    if ticker in DE_STOCKS and "EWG" in prices:
        return prices["EWG"]
    if ticker in CRYPTO and "BTC-USD" in prices and ticker != "BTC-USD":
        return prices["BTC-USD"]
    return None


def _build_features(data: dict, macro_data: dict) -> tuple[dict, dict]:
    features, prices = {}, {}
    all_dates = pd.DatetimeIndex(sorted(set().union(*[df.index for df in data.values()])))
    macro_df = build_macro_df(macro_data, all_dates)

    for ticker, df in data.items():
        try:
            feat = compute_features(df)

            # Inject macro features (aligned by date)
            for col in ["vix_level", "vix_chg_10d", "yield_10y", "yield_chg_20d", "dollar_chg_20d"]:
                if col in macro_df.columns:
                    feat[col] = macro_df[col].reindex(feat.index, method="ffill")

            features[ticker] = feat
            prices[ticker] = df["Close"].squeeze()
        except Exception as e:
            print(f"  [{ticker}] feature error: {e}")

    # Relative strength vs sector (vectorized per ticker)
    for ticker, feat in features.items():
        bench = _benchmark_for(ticker, prices)
        stock = prices.get(ticker)
        if bench is not None and stock is not None:
            bench_aligned = bench.reindex(stock.index, method="ffill")
            rs20 = stock.pct_change(20) - bench_aligned.pct_change(20)
            rs60 = stock.pct_change(60) - bench_aligned.pct_change(60)
            feat["rs_20d"] = rs20.reindex(feat.index, method="ffill")
            feat["rs_60d"] = rs60.reindex(feat.index, method="ffill")

    return features, prices


def _apply_boosts(predictions, fundamentals, sentiments, insiders, earnings_data,
                  analysts, pc_ratios, sector_mom, regime) -> pd.DataFrame:
    predictions = predictions.copy()
    cols = {
        "fund_score": [], "fund_label": [], "fund_display": [],
        "sent_boost": [], "sentiment_label": [],
        "insider_boost": [], "insider_label": [],
        "analyst_boost": [], "analyst_label": [],
        "pc_boost": [], "pc_label": [],
        "sector_boost_val": [],
        "earnings_warning": [], "earnings_note": [],
    }

    for _, row in predictions.iterrows():
        t = row["ticker"]

        fs, fl, fd = score_fundamentals(fundamentals.get(t, {}))
        cols["fund_score"].append(fs)
        cols["fund_label"].append(fl)
        cols["fund_display"].append(fd)

        s = sentiments.get(t, {})
        cols["sent_boost"].append(s.get("sentiment_boost", 0.0))
        cols["sentiment_label"].append(s.get("sentiment_label", "Neutral 😐"))

        ins = insiders.get(t, {})
        cols["insider_boost"].append(ins.get("insider_boost", 0.0))
        cols["insider_label"].append(ins.get("insider_label", ""))

        an = analysts.get(t, {})
        cols["analyst_boost"].append(an.get("analyst_boost", 0.0))
        cols["analyst_label"].append(an.get("analyst_label", ""))

        pc = pc_ratios.get(t, {})
        cols["pc_boost"].append(pc.get("pc_boost", 0.0))
        cols["pc_label"].append(pc.get("pc_label", ""))

        cols["sector_boost_val"].append(sector_boost(t, sector_mom))

        earn = earnings_data.get(t, {})
        cols["earnings_warning"].append(earn.get("earnings_warning", False))
        cols["earnings_note"].append(earn.get("earnings_note", ""))

    for k, v in cols.items():
        predictions[k] = v

    raw = (
        predictions["score"]
        + predictions["fund_score"]
        + predictions["sent_boost"]
        + predictions["insider_boost"]
        + predictions["analyst_boost"]
        + predictions["pc_boost"]
        + predictions["sector_boost_val"]
    )
    earnings_penalty = predictions["earnings_warning"].map({True: 0.70, False: 1.0})
    multiplier = regime.get("score_multiplier", 1.0)
    predictions["adj_score"] = (raw * multiplier * earnings_penalty).round(1)
    predictions.sort_values("adj_score", ascending=False, inplace=True)
    predictions.reset_index(drop=True, inplace=True)
    return predictions


def _should_retrain() -> bool:
    if not feature_count_matches():
        print("  Feature set changed — retraining.")
        return True
    return datetime.now().weekday() == 0   # every Monday


def _save(predictions: pd.DataFrame):
    conn = sqlite3.connect(DB_PATH)
    df = predictions.copy()
    df["timestamp"] = datetime.now().strftime("%Y-%m-%d")
    try:
        df.to_sql("predictions", conn, if_exists="append", index=False)
    except Exception:
        conn.execute("DROP TABLE IF EXISTS predictions")
        df.to_sql("predictions", conn, if_exists="replace", index=False)
    conn.close()


def _print_results(predictions: pd.DataFrame, regime: dict):
    print(f"\n  Market: {regime.get('regime','?')} | "
          f"S&P vs 200MA: {regime.get('spy_vs_200ma', 0):+.1f}%")
    print(f"\n{'─'*78}")
    print(f"{'#':<4} {'Name':<20} {'Type':<14} {'1M':>5} {'3M':>5} {'6M':>5} "
          f"{'Base':>5} {'Adj':>5}  Signal")
    print(f"{'─'*78}")
    for rank, (_, row) in enumerate(predictions.head(TOP_N).iterrows(), 1):
        name = TICKER_NAMES.get(row["ticker"], row["ticker"])[:18]
        p1   = f"{row.get('prob_1M') or 0:.0f}%"
        p3   = f"{row.get('prob_3M') or 0:.0f}%"
        p6   = f"{row.get('prob_6M') or 0:.0f}%"
        base = f"{row.get('score') or 0:.0f}"
        adj  = f"{row.get('adj_score') or 0:.0f}"
        adj_val = row.get("adj_score") or 0
        sig  = "🔥 STRONG BUY" if adj_val >= 65 else ("✅ BUY" if adj_val >= 55 else "👀 WATCH")
        warn = " ⚡earnings" if row.get("earnings_warning") else ""
        ins  = f" {row.get('insider_label','')}" if row.get("insider_label") else ""
        print(f"{rank:<4} {name:<20} {row.get('type',''):<14} "
              f"{p1:>5} {p3:>5} {p6:>5} {base:>5} {adj:>5}  {sig}{warn}{ins}")
    print(f"{'─'*78}")
    print("1M/3M/6M = P(gain ≥5%/10%/15%) | Adj = after macro+fundamentals+sentiment+insider boosts")
    if not regime.get("is_bull", True):
        print("⚠️  Bear market — all scores reduced 30%")


_SECTORS = {
    "AAPL":"Consumer Tech","MSFT":"Cloud & AI","NVDA":"Semiconductors","AMZN":"E-Commerce",
    "GOOGL":"Search & AI","META":"Social Media","TSLA":"Electric Vehicles","JPM":"Banking",
    "V":"Payments","UNH":"Healthcare","XOM":"Energy","LLY":"Pharma","JNJ":"Healthcare",
    "MA":"Payments","HD":"Retail","AVGO":"Semiconductors","PG":"Consumer Goods",
    "MRK":"Pharma","COST":"Retail","ABBV":"Biotech","CVX":"Energy","WMT":"Retail",
    "BAC":"Banking","KO":"Beverages","PEP":"Beverages","NFLX":"Streaming","TMO":"Lab Equipment",
    "AMD":"Semiconductors","ADBE":"Software","CRM":"Software","ORCL":"Software","CSCO":"Networking",
    "QCOM":"Semiconductors","TXN":"Semiconductors","INTU":"Software","AMGN":"Biotech",
    "BKNG":"Travel","PYPL":"Payments","UBER":"Mobility","COIN":"Crypto Exchange",
    "NET":"Cybersecurity","AXP":"Financial Services","CAVA":"Restaurants","RKLB":"Aerospace",
    "OKLO":"Nuclear Energy","IONQ":"Quantum Computing","NIO":"Electric Vehicles",
    "RGTI":"Quantum Computing","A":"Lab Equipment","SNEX":"Financial Services",
    "BBIO":"Biotech","RCEL":"Medical Devices","ALHC":"Healthcare",
    "ADS.DE":"Sportswear","AIR.DE":"Aerospace & Defence","ALV.DE":"Insurance","BAS.DE":"Chemicals",
    "BAYN.DE":"Pharma & Chemicals","BMW.DE":"Automotive","CON.DE":"Automotive","DBK.DE":"Banking",
    "DB1.DE":"Financial Services","DHL.DE":"Logistics","DTE.DE":"Telecom","EOAN.DE":"Utilities",
    "FRE.DE":"Healthcare","HEI.DE":"Construction","HEN3.DE":"Consumer","IFX.DE":"Semiconductors",
    "LIN.DE":"Industrial Gases","MBG.DE":"Automotive","MRK.DE":"Pharma & Chemicals",
    "MUV2.DE":"Insurance","RHM.DE":"Defence","RWE.DE":"Utilities","SAP.DE":"Software",
    "SIE.DE":"Industrial","VOW3.DE":"Automotive","VNA.DE":"Real Estate","ZAL.DE":"E-Commerce",
    "BNR.DE":"Chemicals","SHL.DE":"Medical Devices","ENR.DE":"Energy","CBK.DE":"Banking",
    "AXA.PA":"Insurance",
    "SPY":"US Index — 500 cos","QQQ":"US Tech Index","IVV":"US Index","VTI":"Total US Market",
    "VWO":"Emerging Markets","IS3Q.DE":"MSCI World Quality","VWCE.DE":"Global All-World",
    "IWDA.AS":"Developed Markets","CSPX.L":"S&P 500","GLD":"Gold","TLT":"US Bonds",
    "BTC-USD":"Store of Value","ETH-USD":"Smart Contracts","BNB-USD":"Exchange Token",
    "XRP-USD":"Payments","SOL-USD":"Smart Contracts","ADA-USD":"Smart Contracts",
    "DOGE-USD":"Meme / Payments","AVAX-USD":"Smart Contracts","DOT-USD":"Interoperability",
    "LINK-USD":"Oracle Network","XLM-USD":"Payments","ATOM-USD":"Interoperability",
    "TRX-USD":"Smart Contracts","SHIB-USD":"Meme Token",
}

def _flag_for(ticker: str) -> str:
    if ticker in CRYPTO:            return "🪙"
    if ticker in DE_STOCKS or ticker.endswith(".DE"): return "🇩🇪"
    if ticker.endswith(".PA") or ticker.endswith(".AS"): return "🇪🇺"
    if ticker.endswith(".L"):       return "🇬🇧"
    if ticker in ETFS and any(x in ticker for x in ["VWCE","IS3Q","IWDA","CSPX"]): return "🌍"
    return "🇺🇸"

def _currency_for(ticker: str) -> str:
    if ticker in CRYPTO: return "$"
    if ticker.endswith(".DE") or ticker.endswith(".PA") or ticker.endswith(".AS"): return "€"
    return "$"

def _price_targets(price: float, score: float) -> dict:
    ret = 0.22 if score >= 65 else (0.14 if score >= 55 else (0.07 if score >= 45 else 0.03))
    return {
        "target": round(price * (1 + ret), 2),
        "best":   round(price * (1 + ret * 1.6), 2),
        "worst":  round(price * (1 - ret * 0.7), 2),
    }


def _recommendation(score_out: float, signal: str) -> str:
    """
    Compute the buy/hold/watch/sell recommendation.
    Mirrors the frontend getRecommendation() exactly so the daily diff
    matches what users see in the app.
    score_out is the 0-10 scale value exported in picks.json.
    """
    if score_out >= 7.5 and signal == "buy": return "buy-more"
    if score_out >= 6.0 and signal == "buy": return "buy-more"
    if score_out >= 5.5: return "hold"
    if score_out >= 4.5: return "watch"
    return "sell"

def _build_reasons(row: pd.Series) -> list:
    reasons = []
    fund = str(row.get("fund_label") or "")
    analyst = str(row.get("analyst_label") or "")
    insider = str(row.get("insider_label") or "")
    sent = str(row.get("sentiment_label") or "")
    earn = str(row.get("earnings_note") or "")
    if any(x in fund for x in ["💪","Excellent","Solid"]):
        reasons.append({"t":"pos","text":f"Financial health: {fund}"})
    if analyst and "Buy" in analyst and "Mixed" not in analyst:
        reasons.append({"t":"pos","text":analyst})
    if insider and "buying" in insider.lower():
        reasons.append({"t":"pos","text":insider})
    if "Positive" in sent:
        reasons.append({"t":"pos","text":f"News: {sent}"})
    if earn:
        reasons.append({"t":"warn","text":earn})
    if any(x in fund for x in ["Weak","Poor"]):
        reasons.append({"t":"warn","text":f"Financial health: {fund}"})
    if not [r for r in reasons if r["t"]=="pos"]:
        reasons.insert(0,{"t":"pos","text":f"AI Score: {float(row.get('adj_score') or row.get('score') or 0)/10:.1f}/10"})
    return reasons[:3]

def _build_signals(row: pd.Series) -> list:
    out = []
    for label, key in [("Company Health","fund_display"),("Analyst Rating","analyst_label"),
                        ("News Sentiment","sentiment_label"),("Insider Activity","insider_label"),
                        ("Options Market","pc_label"),("Earnings","earnings_note")]:
        val = str(row.get(key) or "")
        if val and val not in ("None","nan",""):
            out.append({"l":label,"val":val})
    return out[:6]

def _export_picks_json(predictions: pd.DataFrame, regime: dict, prices: dict):
    """Export all ML predictions as JSON for the Stockeram mobile app."""
    picks_out = []
    for _, row in predictions.iterrows():
        ticker = str(row["ticker"])
        price_s = prices.get(ticker)
        if price_s is None or len(price_s) == 0:
            continue
        price = float(price_s.iloc[-1])
        score = float(row.get("adj_score") or row.get("score") or 0)
        targets = _price_targets(price, score)
        signal = "buy" if score >= 55 else "watch"
        verdict = ("Strong buy signal" if score >= 65 else
                   "Good buy signal"   if score >= 55 else
                   "Mixed — watch"     if score >= 45 else "Weak signals")
        # App displays score as X/10 — convert from 0-100 internal scale
        score_out = round(score / 10.0, 1)
        picks_out.append({
            "ticker":       ticker,
            "name":         TICKER_NAMES.get(ticker, ticker),
            "type":         {"US Stock":"stock","German Stock":"stock","ETF":"etf","Crypto":"crypto"}.get(str(row.get("type","stock")), "stock"),
            "flag":         _flag_for(ticker),
            "sector":       _SECTORS.get(ticker, "Global Markets"),
            "signal":       signal,
            "score":        score_out,
            "scoreVerdict": verdict,
            "scoreColor":   "green" if score >= 55 else "amber",
            "priceNow":     round(price, 2),
            "priceTarget":  targets["target"],
            "bestCase":     targets["best"],
            "worstCase":    targets["worst"],
            "currency":     _currency_for(ticker),
            "prob1W":       round(float(row.get("prob_1W") or 0), 1),
            "prob1M":       round(float(row.get("prob_1M") or 0), 1),
            "prob3M":       round(float(row.get("prob_3M") or 0), 1),
            "prob6M":       round(float(row.get("prob_6M") or 0), 1),
            "fundLabel":    str(row.get("fund_label") or ""),
            "sentimentLabel": str(row.get("sentiment_label") or ""),
            "analystLabel": str(row.get("analyst_label") or ""),
            "insiderLabel": str(row.get("insider_label") or ""),
            "earningsNote": str(row.get("earnings_note") or ""),
            "reasons":      _build_reasons(row),
            "signals":      _build_signals(row),
            "recommendation": _recommendation(score_out, signal),
        })
    # Read yesterday's picks BEFORE overwriting — for daily diff.
    previous_picks = []
    try:
        with open("picks.json", encoding="utf-8") as f:
            previous_picks = json.load(f).get("picks", [])
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    output = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
        "market": {
            "regime":      regime.get("regime","UNKNOWN"),
            "spy_vs_200ma": regime.get("spy_vs_200ma",0),
            "is_bull":     bool(regime.get("is_bull",True)),
        },
        "picks": picks_out,
    }
    with open("picks.json","w",encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)
    print(f"  Exported {len(picks_out)} picks → picks.json")

    # Diff against yesterday and trigger Web Push to subscribed users.
    _notify_recommendation_changes(picks_out, previous_picks)


def _notify_recommendation_changes(new_picks: list, previous_picks: list) -> None:
    """
    Compare today's recommendations with yesterday's. For every ticker whose
    recommendation flipped, POST the change to the Stockeram Worker which
    sends a Web Push notification to every user holding that ticker.
    """
    if not previous_picks:
        print("  No previous picks data — first run, skipping diff.")
        return

    admin_token = os.environ.get("STOCKERAM_ADMIN_TOKEN")
    if not admin_token:
        print("  STOCKERAM_ADMIN_TOKEN not set — skipping push notification trigger.")
        return

    api_url = os.environ.get("STOCKERAM_API_URL", "https://stockeram-app.hsaberiansani.workers.dev").rstrip("/")

    prev_recs = {p["ticker"]: p.get("recommendation") for p in previous_picks if p.get("ticker")}
    changes = []
    for p in new_picks:
        ticker  = p.get("ticker")
        new_rec = p.get("recommendation")
        old_rec = prev_recs.get(ticker)
        if old_rec and new_rec and old_rec != new_rec:
            changes.append({
                "ticker": ticker,
                "name":   p.get("name") or ticker,
                "oldRec": old_rec,
                "newRec": new_rec,
                "score":  p.get("score"),
            })

    if not changes:
        print("  No recommendation changes — no push notifications needed.")
        return

    summary = ", ".join(f"{c['ticker']} {c['oldRec']}→{c['newRec']}" for c in changes[:10])
    print(f"  {len(changes)} ticker(s) flipped: {summary}{' ...' if len(changes) > 10 else ''}")

    try:
        import urllib.request
        req = urllib.request.Request(
            f"{api_url}/api/admin/notify-changes",
            data=json.dumps({"changes": changes}).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Admin-Token": admin_token},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            try:
                result = json.loads(body)
                print(f"  Worker: sent={result.get('sent', 0)} failed={result.get('failed', 0)}")
            except json.JSONDecodeError:
                print(f"  Worker: {body[:200]}")
    except Exception as e:
        print(f"  Push notify failed: {e}")


def run():
    print(f"\n{'='*65}")
    print(f"  Stock Analyzer — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*65}")

    print("\n[1/8] Detecting market regime...")
    regime = detect_regime()
    print(f"  {regime['regime']} | S&P vs 200MA: {regime['spy_vs_200ma']:+.1f}%")

    print("\n[2/8] Fetching market + macro data...")
    data = fetch_all()
    macro_data = fetch_macro()
    if not data:
        print("No data fetched. Aborting.")
        return

    print("\n[3/8] Computing features (technical + macro + relative strength)...")
    features, prices = _build_features(data, macro_data)
    print(f"  Features ready for {len(features)} assets ({len(FEATURE_COLS)} features each).")

    if _should_retrain():
        print("\n[4/8] Training LightGBM + XGBoost ensemble...")
        models = train_models(features, prices)
    else:
        print("\n[4/8] Loading existing ML models...")
        models = load_models()

    if not models:
        print("No models available. Aborting.")
        return

    print("\n[5/8] Generating ML predictions...")
    predictions = predict(models, features)
    predictions["type"] = predictions["ticker"].apply(_asset_type)
    predictions["name"] = predictions["ticker"].map(TICKER_NAMES).fillna(predictions["ticker"])

    tickers = predictions["ticker"].tolist()

    print("\n[6/8] Fetching fundamentals, sentiment & sector momentum...")
    fundamentals = fetch_all_fundamentals(tickers)
    sentiments   = get_all_sentiments(tickers)
    sector_mom   = compute_sector_momentum()

    print("\n[7/8] Fetching insider signals, analyst ratings, options & earnings...")
    insiders      = get_all_insider_signals(tickers)
    earnings_data = get_all_earnings(tickers)
    analysts      = get_all_analyst_signals(tickers)
    pc_ratios     = get_all_pc_ratios(tickers)

    predictions = _apply_boosts(
        predictions, fundamentals, sentiments, insiders,
        earnings_data, analysts, pc_ratios, sector_mom, regime,
    )

    print("\n[8/8] Saving results & sending Telegram...")
    current_prices = {t: float(prices[t].iloc[-1]) for t in prices
                      if t in predictions["ticker"].values}
    save_prediction_prices(predictions, current_prices)
    update_outcomes()
    _save(predictions)
    _print_results(predictions, regime)
    send_daily_digest(predictions, regime)
    _export_picks_json(predictions, regime, prices)
    print(f"\nDone. Next scheduled run at {DAILY_RUN_TIME}.")


if __name__ == "__main__":
    once = "--once" in sys.argv
    run()
    if not once:
        schedule.every().day.at(DAILY_RUN_TIME).do(run)
        while True:
            schedule.run_pending()
            time.sleep(30)
