#!/usr/bin/env python3
"""Phase 6 NSE better-agents paper test.

Subcommands:
  freeze  Fetch and freeze raw-close yfinance data.
  run     Run the pre-registered train/validation/test A/B/P experiment.
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

try:
    import yfinance as yf
except ImportError:  # pragma: no cover - handled at runtime
    yf = None


PREREGISTRATION_COMMIT = "93c3b6d0f1321dbbf635762e52b82365a8baf087"
RNG_SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_GROSS_SLEEVE = 0.05
TURNOVER_COST_RATE = 0.001
COMMISSION_PER_TRADE = 50.0
START_DATE = "2019-01-01"
END_DATE = "2026-06-20"
DEFAULT_DATA_DIR = Path("evals/experiments/nse_phase6_data_frozen")
DEFAULT_OUTPUT_DIR = Path("evals/experiments/nse_phase6_better_agents_results")

INSTRUMENTS = {
    "NIFTY 50": "^NSEI",
    "BANK NIFTY": "^NSEBANK",
    "RELIANCE": "RELIANCE.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "TCS": "TCS.NS",
    "INFY": "INFY.NS",
    "ICICIBANK": "ICICIBANK.NS",
}

BASE_FEATURES = [
    "ret_1",
    "ret_2",
    "ret_5",
    "ret_10",
    "ret_20",
    "vol_10",
    "vol_20",
    "vol_60",
    "ma20_distance",
    "ma50_distance",
    "ma100_distance",
    "rsi14",
    "volume_z20",
    "trend_up",
    "vol_high",
]


def git_commit_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def freeze_data(output_dir: Path) -> dict[str, Any]:
    if yf is None:
        raise RuntimeError("yfinance is not installed")

    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "source": "yfinance",
        "start_date": START_DATE,
        "end_date": END_DATE,
        "field_used": "raw Close",
        "adjusted_close_used": False,
        "instruments": {},
        "source_limitations": [
            "yfinance may differ from official NSE records.",
            "Raw close is not a total-return series.",
            "Adjusted close is avoided because it can be retroactively rewritten.",
        ],
    }

    for instrument, ticker in INSTRUMENTS.items():
        frame = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False, auto_adjust=False)
        if frame.empty:
            raise RuntimeError(f"No yfinance data returned for {instrument} ({ticker})")
        frame = normalize_yfinance_frame(frame)
        frozen = frame[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
        frozen["Instrument"] = instrument
        frozen["Ticker"] = ticker
        frozen = frozen.dropna(subset=["Date", "Close"]).sort_values("Date").drop_duplicates("Date")
        path = output_dir / f"{safe_name(instrument)}_REAL.csv"
        frozen.to_csv(path, index=False)
        metadata["instruments"][instrument] = {
            "ticker": ticker,
            "rows": len(frozen),
            "first_date": str(pd.to_datetime(frozen["Date"]).min().date()),
            "last_date": str(pd.to_datetime(frozen["Date"]).max().date()),
            "file": str(path),
        }

    metadata_path = output_dir / "METADATA.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))
    return metadata


def normalize_yfinance_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = [column[0] for column in frame.columns]
    frame = frame.reset_index()
    if "Date" not in frame.columns:
        frame = frame.rename(columns={frame.columns[0]: "Date"})
    for column in ["Open", "High", "Low", "Close", "Volume"]:
        if column not in frame.columns:
            raise RuntimeError(f"Missing yfinance column: {column}")
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    return frame


def safe_name(instrument: str) -> str:
    return instrument.replace(" ", "_").lower()


def load_frozen_data(data_dir: Path) -> dict[str, pd.DataFrame]:
    data = {}
    for instrument in INSTRUMENTS:
        path = data_dir / f"{safe_name(instrument)}_REAL.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing frozen data file: {path}")
        frame = pd.read_csv(path)
        frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
        for column in ["Open", "High", "Low", "Close", "Volume"]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame = frame[["Date", "Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Date", "Close"])
        data[instrument] = frame.sort_values("Date").drop_duplicates("Date").reset_index(drop=True)
    return data


def visible_before(frame: pd.DataFrame, prediction_date: pd.Timestamp) -> pd.DataFrame:
    visible = frame[frame["Date"] < prediction_date].copy()
    if len(visible) > 0 and pd.to_datetime(visible["Date"]).max() >= prediction_date:
        raise AssertionError("LOOKAHEAD DETECTED")
    return visible


def build_feature_rows(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for instrument, frame in data.items():
        dates = list(pd.to_datetime(frame["Date"]))
        for i, prediction_date in enumerate(dates[:-1]):
            visible = visible_before(frame, prediction_date)
            if len(visible) < 120:
                continue
            current_close = close_on(frame, prediction_date)
            next_date = dates[i + 1]
            next_close = close_on(frame, next_date)
            if current_close is None or next_close is None:
                continue
            row = feature_row(instrument, visible)
            row.update({
                "instrument": instrument,
                "prediction_date": prediction_date,
                "resolution_date": next_date,
                "label_up": 1 if next_close > current_close else 0,
                "market_return": next_close / current_close - 1.0,
            })
            rows.append(row)
    frame = pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan).dropna()
    return add_instrument_dummies(frame).reset_index(drop=True)


def close_on(frame: pd.DataFrame, date: pd.Timestamp) -> float | None:
    rows = frame[frame["Date"] == date]
    if len(rows) == 0:
        return None
    return float(rows.iloc[0]["Close"])


def feature_row(instrument: str, visible: pd.DataFrame) -> dict[str, float]:
    closes = visible["Close"].astype(float)
    volumes = visible["Volume"].astype(float)
    returns = closes.pct_change()
    log_returns = np.log(closes).diff()
    ma20 = float(closes.tail(20).mean())
    ma50 = float(closes.tail(50).mean())
    ma100 = float(closes.tail(100).mean())
    vol20 = float(log_returns.tail(20).std())
    volume_std = float(volumes.tail(20).std()) or 1.0
    return {
        "ret_1": float(returns.iloc[-1]),
        "ret_2": float(closes.iloc[-1] / closes.iloc[-3] - 1.0),
        "ret_5": float(closes.iloc[-1] / closes.iloc[-6] - 1.0),
        "ret_10": float(closes.iloc[-1] / closes.iloc[-11] - 1.0),
        "ret_20": float(closes.iloc[-1] / closes.iloc[-21] - 1.0),
        "vol_10": float(log_returns.tail(10).std()),
        "vol_20": vol20,
        "vol_60": float(log_returns.tail(60).std()),
        "ma20_distance": float(closes.iloc[-1] / ma20 - 1.0),
        "ma50_distance": float(closes.iloc[-1] / ma50 - 1.0),
        "ma100_distance": float(closes.iloc[-1] / ma100 - 1.0),
        "rsi14": compute_rsi(closes.tail(15).to_numpy()) / 100.0,
        "volume_z20": float((volumes.iloc[-1] - volumes.tail(20).mean()) / volume_std),
        "trend_up": 1.0 if closes.iloc[-1] > ma50 else 0.0,
        "vol_high": 1.0 if vol20 > 0.025 else 0.0,
    }


def compute_rsi(closes: np.ndarray) -> float:
    deltas = np.diff(closes)
    gains = np.clip(deltas, 0, None)
    losses = -np.clip(deltas, None, 0)
    avg_gain = float(np.mean(gains)) if len(gains) else 0.0
    avg_loss = float(np.mean(losses)) if len(losses) else 0.0
    if avg_loss == 0:
        return 50.0 if avg_gain == 0 else 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def add_instrument_dummies(frame: pd.DataFrame) -> pd.DataFrame:
    for instrument in INSTRUMENTS:
        frame[f"instrument_{safe_name(instrument)}"] = (frame["instrument"] == instrument).astype(float)
    return frame


def feature_columns(frame: pd.DataFrame) -> list[str]:
    return BASE_FEATURES + [column for column in frame.columns if column.startswith("instrument_")]


def split_by_instrument(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_parts, validation_parts, test_parts = [], [], []
    for _, group in frame.sort_values("prediction_date").groupby("instrument", sort=False):
        n = len(group)
        train_end = int(n * 0.60)
        validation_end = int(n * 0.80)
        train_parts.append(group.iloc[:train_end])
        validation_parts.append(group.iloc[train_end:validation_end])
        test_parts.append(group.iloc[validation_end:])
    return pd.concat(train_parts), pd.concat(validation_parts), pd.concat(test_parts)


def fit_agents(train: pd.DataFrame, columns: list[str]) -> dict[str, Any]:
    x_train = train[columns]
    y_train = train["label_up"]
    agents: dict[str, Any] = {
        "LogisticCrossSectional": make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1000, random_state=RNG_SEED, class_weight="balanced"),
        ),
        "GradientBoostingCrossSectional": GradientBoostingClassifier(
            random_state=RNG_SEED,
            n_estimators=120,
            learning_rate=0.04,
            max_depth=2,
        ),
        "RandomForestCrossSectional": RandomForestClassifier(
            random_state=RNG_SEED,
            n_estimators=250,
            max_depth=4,
            min_samples_leaf=20,
            class_weight="balanced_subsample",
        ),
    }
    for model in agents.values():
        model.fit(x_train, y_train)

    regime_models = {}
    for trend_value in [0.0, 1.0]:
        subset = train[train["trend_up"] == trend_value]
        if len(subset) >= 100 and subset["label_up"].nunique() == 2:
            model = GradientBoostingClassifier(random_state=RNG_SEED, n_estimators=100, learning_rate=0.04, max_depth=2)
            model.fit(subset[columns], subset["label_up"])
            regime_models[trend_value] = model
    agents["RegimeGradientBoosting"] = regime_models
    return agents


def predict_records(frame: pd.DataFrame, agents: dict[str, Any], columns: list[str], calibrators: dict[str, Any] | None) -> list[dict[str, Any]]:
    records = []
    fallback = agents["GradientBoostingCrossSectional"]
    for _, row in frame.sort_values(["prediction_date", "instrument"]).iterrows():
        x = pd.DataFrame([row[columns].to_dict()])
        for agent, model in agents.items():
            if agent == "RegimeGradientBoosting":
                selected = model.get(float(row["trend_up"]), fallback)
                probability = float(selected.predict_proba(x)[0, 1])
            else:
                probability = float(model.predict_proba(x)[0, 1])
            prediction = "up" if probability >= 0.5 else "down"
            raw_confidence = max(probability, 1.0 - probability)
            confidence = calibrate_confidence(agent, probability, raw_confidence, calibrators)
            hit = (prediction == "up" and row["label_up"] == 1) or (prediction == "down" and row["label_up"] == 0)
            records.append({
                "instrument": row["instrument"],
                "agent": agent,
                "prediction_date": row["prediction_date"],
                "resolution_date": row["resolution_date"],
                "prediction": prediction,
                "probability_up": probability,
                "confidence": confidence,
                "hit": bool(hit),
                "market_return": float(row["market_return"]),
                "post_hoc": False,
            })
    return records


def fit_calibrators(validation_records: list[dict[str, Any]]) -> dict[str, Any]:
    calibrators = {}
    for agent in sorted({record["agent"] for record in validation_records}):
        subset = [record for record in validation_records if record["agent"] == agent]
        fallback = sum(1 for record in subset if record["hit"]) / len(subset)
        buckets = []
        for low, high in [(0.0, 0.4), (0.4, 0.5), (0.5, 0.6), (0.6, 1.01)]:
            bucket = [record for record in subset if low <= record["probability_up"] < high]
            if len(bucket) >= 20:
                buckets.append((low, high, sum(1 for record in bucket if record["hit"]) / len(bucket)))
        calibrators[agent] = {"fallback": fallback, "buckets": buckets}
    return calibrators


def calibrate_confidence(agent: str, probability: float, raw_confidence: float, calibrators: dict[str, Any] | None) -> float:
    if not calibrators or agent not in calibrators:
        return float(max(0.5, min(0.95, raw_confidence)))
    config = calibrators[agent]
    for low, high, empirical_hit_rate in config["buckets"]:
        if low <= probability < high:
            return float(max(0.5, min(0.95, empirical_hit_rate)))
    return float(max(0.5, min(0.95, config["fallback"])))


def trust_score(history: list[dict[str, Any]]) -> float:
    if not history:
        return 0.5
    hit_rate = sum(1 for record in history if record["hit"]) / len(history)
    avg_confidence = statistics.mean(record["confidence"] for record in history)
    if avg_confidence <= hit_rate:
        trust = hit_rate + 0.05 * (hit_rate - avg_confidence)
    else:
        trust = hit_rate - 0.1 * (avg_confidence - hit_rate)
    return max(0.0, min(1.0, trust))


def simulate(validation_records: list[dict[str, Any]], test_records: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    histories = defaultdict(list)
    for record in validation_records:
        histories[record["agent"]].append(record)

    by_date_instrument = defaultdict(list)
    for record in test_records:
        by_date_instrument[(pd.Timestamp(record["prediction_date"]), record["instrument"])].append(record)

    rng = np.random.RandomState(RNG_SEED)
    policies = {
        "A_equal": portfolio_state(),
        "B_trust": portfolio_state(),
        "P_random": portfolio_state(),
        "A_equal_costed": portfolio_state(),
        "B_trust_costed": portfolio_state(),
        "P_random_costed": portfolio_state(),
    }
    daily_rows = []

    dates = sorted({key[0] for key in by_date_instrument})
    for date in dates:
        day_pnl = {policy: 0.0 for policy in policies}
        active_instruments = sorted({instrument for row_date, instrument in by_date_instrument if row_date == date})
        sleeve_capital = INITIAL_CAPITAL / len(active_instruments)
        for instrument in active_instruments:
            records = sorted(by_date_instrument[(date, instrument)], key=lambda record: record["agent"])
            market_return = records[0]["market_return"]
            signals = {
                record["agent"]: record["confidence"] if record["prediction"] == "up" else -record["confidence"]
                for record in records
            }
            weights = {
                "A_equal": {agent: 1.0 for agent in signals},
                "B_trust": {agent: trust_score(histories[agent]) for agent in signals},
                "P_random": {agent: float(rng.uniform(0.0, 1.0)) for agent in signals},
            }
            for base_policy in ["A_equal", "B_trust", "P_random"]:
                signal = weighted_signal(signals, weights[base_policy])
                position = max(
                    -MAX_GROSS_SLEEVE * sleeve_capital,
                    min(MAX_GROSS_SLEEVE * sleeve_capital, signal * MAX_GROSS_SLEEVE * sleeve_capital),
                )
                pnl = position * market_return
                day_pnl[base_policy] += pnl

                costed_policy = f"{base_policy}_costed"
                previous_position = policies[costed_policy]["positions"].get(instrument, 0.0)
                turnover = abs(position - previous_position)
                cost = turnover * TURNOVER_COST_RATE + (COMMISSION_PER_TRADE if turnover > 0 else 0.0)
                day_pnl[costed_policy] += pnl - cost
                policies[costed_policy]["positions"][instrument] = position

        for policy, pnl in day_pnl.items():
            policies[policy]["pnl"].append(pnl)
            policies[policy]["cash"] += pnl
        daily_rows.append({"date": str(date.date()), **{f"{policy}_pnl": round(value, 6) for policy, value in day_pnl.items()}})
        for instrument in active_instruments:
            for record in by_date_instrument[(date, instrument)]:
                histories[record["agent"]].append(record)

    summaries = {policy: summarize_pnl(state["pnl"]) for policy, state in policies.items()}
    summaries["headline"] = {
        "B_minus_P_return_pct": round(summaries["B_trust"]["total_return_pct"] - summaries["P_random"]["total_return_pct"], 4),
        "B_minus_P_sharpe": round(summaries["B_trust"]["sharpe_style_ratio"] - summaries["P_random"]["sharpe_style_ratio"], 4),
        "B_costed_minus_P_costed_return_pct": round(
            summaries["B_trust_costed"]["total_return_pct"] - summaries["P_random_costed"]["total_return_pct"],
            4,
        ),
    }
    return summaries, daily_rows


def portfolio_state() -> dict[str, Any]:
    return {"cash": INITIAL_CAPITAL, "pnl": [], "positions": {}}


def weighted_signal(signals: dict[str, float], weights: dict[str, float]) -> float:
    total_weight = sum(weights.values())
    if total_weight == 0:
        return 0.0
    return sum(signals[agent] * weights[agent] for agent in signals) / total_weight


def summarize_pnl(pnl: list[float]) -> dict[str, Any]:
    returns = [value / INITIAL_CAPITAL for value in pnl]
    std = statistics.stdev(returns) if len(returns) > 1 else 0.0
    sharpe = statistics.mean(returns) / std if std > 0 else 0.0
    return {
        "total_pnl": round(sum(pnl), 4),
        "total_return_pct": round(100.0 * sum(pnl) / INITIAL_CAPITAL, 4),
        "sharpe_style_ratio": round(sharpe, 4),
        "positive_days": sum(1 for value in pnl if value > 0),
        "days": len(pnl),
    }


def calibration_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    output = {}
    for agent in sorted({record["agent"] for record in records}):
        subset = [record for record in records if record["agent"] == agent]
        hit_rate = sum(1 for record in subset if record["hit"]) / len(subset)
        avg_confidence = statistics.mean(record["confidence"] for record in subset)
        output[agent] = {
            "predictions": len(subset),
            "hit_rate": round(hit_rate, 4),
            "avg_confidence": round(avg_confidence, 4),
            "calibration_error": round(avg_confidence - hit_rate, 4),
            "confidence_bins": confidence_bins(subset),
        }
    return output


def confidence_bins(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets = defaultdict(list)
    for record in records:
        confidence = record["confidence"]
        if confidence < 0.55:
            bucket = "0.45-0.55"
        elif confidence < 0.65:
            bucket = "0.55-0.65"
        elif confidence < 0.75:
            bucket = "0.65-0.75"
        else:
            bucket = "0.75-1.00"
        buckets[bucket].append(record)
    rows = []
    for bucket, subset in sorted(buckets.items()):
        hit_rate = sum(1 for record in subset if record["hit"]) / len(subset)
        avg_confidence = statistics.mean(record["confidence"] for record in subset)
        rows.append({
            "bucket": bucket,
            "n": len(subset),
            "hit_rate": round(hit_rate, 4),
            "avg_confidence": round(avg_confidence, 4),
            "calibration_error": round(avg_confidence - hit_rate, 4),
        })
    return rows


def per_instrument_summary(test_records: list[dict[str, Any]]) -> dict[str, Any]:
    output = {}
    for instrument in sorted({record["instrument"] for record in test_records}):
        subset = [record for record in test_records if record["instrument"] == instrument]
        output[instrument] = calibration_summary(subset)
    return output


def run_experiment(data_dir: Path, output_dir: Path) -> dict[str, Any]:
    data = load_frozen_data(data_dir)
    lookahead_check = run_lookahead_check(data)
    features = build_feature_rows(data)
    columns = feature_columns(features)
    train, validation, test = split_by_instrument(features)
    agents = fit_agents(train, columns)
    raw_validation = predict_records(validation, agents, columns, None)
    calibrators = fit_calibrators(raw_validation)
    validation_records = predict_records(validation, agents, columns, calibrators)
    test_records = predict_records(test, agents, columns, calibrators)
    policy_summaries, daily_rows = simulate(validation_records, test_records)
    instrument_policy_summaries = per_instrument_policy_summaries(validation_records, test_records)

    result = {
        "timestamp": datetime.now().isoformat(),
        "mode": "historical_backtest_paper_only",
        "pre_registration_commit_hash": PREREGISTRATION_COMMIT,
        "code_commit_hash": git_commit_hash(),
        "data_dir": str(data_dir),
        "rng_seed": RNG_SEED,
        "lookahead_check": lookahead_check,
        "rows": {"train": len(train), "validation": len(validation), "test": len(test)},
        "date_ranges": {
            "train": date_range(train),
            "validation": date_range(validation),
            "test": date_range(test),
        },
        "policy_summaries": policy_summaries,
        "validation_calibration": calibration_summary(validation_records),
        "test_calibration": calibration_summary(test_records),
        "instrument_test_calibration": per_instrument_summary(test_records),
        "instrument_policy_summaries": instrument_policy_summaries,
        "success_criteria": evaluate_success(policy_summaries, instrument_policy_summaries),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "phase6_better_agents_results.json").write_text(json.dumps(result, indent=2, default=str))
    pd.DataFrame(daily_rows).to_csv(output_dir / "phase6_daily_pnl.csv", index=False)
    pd.DataFrame(test_records).to_csv(output_dir / "phase6_prediction_ledger.csv", index=False)
    write_report(output_dir, result)
    return result


def date_range(frame: pd.DataFrame) -> dict[str, str]:
    return {
        "start": str(pd.to_datetime(frame["prediction_date"]).min().date()),
        "end": str(pd.to_datetime(frame["prediction_date"]).max().date()),
    }


def run_lookahead_check(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
    checks = {}
    for instrument, frame in data.items():
        date = pd.Timestamp(frame.iloc[len(frame) // 2]["Date"])
        visible = visible_before(frame, date)
        max_visible = pd.to_datetime(visible["Date"]).max()
        checks[instrument] = {
            "prediction_date": str(date.date()),
            "max_visible_date": str(max_visible.date()),
            "passed": bool(max_visible < date),
        }
    return {
        "passed": all(row["passed"] for row in checks.values()),
        "instrument_checks": checks,
    }


def per_instrument_policy_summaries(
    validation_records: list[dict[str, Any]],
    test_records: list[dict[str, Any]],
) -> dict[str, Any]:
    summaries = {}
    for instrument in sorted({record["instrument"] for record in test_records}):
        instrument_test = [record for record in test_records if record["instrument"] == instrument]
        instrument_validation = [record for record in validation_records if record["instrument"] == instrument]
        policy_summary, _ = simulate(instrument_validation, instrument_test)
        summaries[instrument] = policy_summary
    return summaries


def evaluate_success(policy_summaries: dict[str, Any], instrument_policy_summaries: dict[str, Any]) -> dict[str, Any]:
    by_instrument = {
        instrument: summary["headline"]["B_minus_P_return_pct"] > 0
        for instrument, summary in instrument_policy_summaries.items()
    }
    criteria = {
        "B_beats_P_return": policy_summaries["headline"]["B_minus_P_return_pct"] > 0,
        "B_beats_P_sharpe": policy_summaries["headline"]["B_minus_P_sharpe"] > 0,
        "B_beats_P_after_costs": policy_summaries["headline"]["B_costed_minus_P_costed_return_pct"] > 0,
        "B_beats_P_instrument_share": round(sum(by_instrument.values()) / len(by_instrument), 4),
    }
    criteria["supported"] = (
        criteria["B_beats_P_return"]
        and criteria["B_beats_P_sharpe"]
        and criteria["B_beats_P_after_costs"]
        and criteria["B_beats_P_instrument_share"] > 0.6
    )
    criteria["instrument_B_beats_P"] = by_instrument
    return criteria


def write_report(output_dir: Path, result: dict[str, Any]) -> None:
    verdict = (
        "Phase 6 found a candidate calibration edge under the pre-registered criteria."
        if result["success_criteria"]["supported"]
        else "Phase 6 remains a null under the pre-registered criteria."
    )
    policies = result["policy_summaries"]
    lines = [
        "# NSE Phase 6 Better Agents Results",
        "",
        f"**Date:** {datetime.now().date()}",
        f"**Mode:** `{result['mode']}`",
        f"**Pre-registration commit hash:** `{result['pre_registration_commit_hash']}`",
        f"**Executable code commit hash:** `{result['code_commit_hash']}`",
        "",
        "## Lookahead Check",
        "",
        f"- Passed: `{result['lookahead_check']['passed']}`",
        "",
        "## Verdict",
        "",
        verdict,
        "",
        "This is paper only: no live orders, no brokerage connection, and no real capital.",
        "",
        "## Split",
        "",
        f"- Train rows: `{result['rows']['train']}` ({result['date_ranges']['train']['start']} to {result['date_ranges']['train']['end']})",
        f"- Validation rows: `{result['rows']['validation']}` ({result['date_ranges']['validation']['start']} to {result['date_ranges']['validation']['end']})",
        f"- Test rows: `{result['rows']['test']}` ({result['date_ranges']['test']['start']} to {result['date_ranges']['test']['end']})",
        "",
        "## A/B/P Test Returns",
        "",
        "| Arm | Return | P&L | Sharpe-style | Positive Days |",
        "|---|---:|---:|---:|---:|",
    ]
    for policy in ["A_equal", "B_trust", "P_random", "A_equal_costed", "B_trust_costed", "P_random_costed"]:
        row = policies[policy]
        lines.append(
            f"| {policy} | {row['total_return_pct']:.4f}% | {row['total_pnl']:.2f} | "
            f"{row['sharpe_style_ratio']:.4f} | {row['positive_days']}/{row['days']} |"
        )

    headline = policies["headline"]
    lines.extend([
        "",
        "## Headline",
        "",
        f"- B-P return: `{headline['B_minus_P_return_pct']:.4f}%`",
        f"- B-P Sharpe-style: `{headline['B_minus_P_sharpe']:.4f}`",
        f"- Costed B-P return: `{headline['B_costed_minus_P_costed_return_pct']:.4f}%`",
        f"- B beats P instrument share: `{result['success_criteria']['B_beats_P_instrument_share']:.1%}`",
        "",
        "## Per-Instrument B vs P",
        "",
        "| Instrument | B Return | P Return | B-P | Costed B-P |",
        "|---|---:|---:|---:|---:|",
    ])
    for instrument, summary in result["instrument_policy_summaries"].items():
        lines.append(
            f"| {instrument} | {summary['B_trust']['total_return_pct']:.4f}% | "
            f"{summary['P_random']['total_return_pct']:.4f}% | "
            f"{summary['headline']['B_minus_P_return_pct']:.4f}% | "
            f"{summary['headline']['B_costed_minus_P_costed_return_pct']:.4f}% |"
        )
    lines.extend([
        "",
        "## Test Calibration",
        "",
        "| Agent | Predictions | Hit Rate | Avg Confidence | Calibration Error |",
        "|---|---:|---:|---:|---:|",
    ])
    for agent, row in result["test_calibration"].items():
        lines.append(
            f"| {agent} | {row['predictions']} | {row['hit_rate']:.1%} | "
            f"{row['avg_confidence']:.1%} | {row['calibration_error']:.1%} |"
        )
    lines.append("")
    (output_dir / "PHASE6_BETTER_AGENTS_RESULTS.md").write_text("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    freeze_parser = subparsers.add_parser("freeze")
    freeze_parser.add_argument("--output-dir", type=Path, default=DEFAULT_DATA_DIR)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    run_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)

    args = parser.parse_args(argv)
    if args.command == "freeze":
        metadata = freeze_data(args.output_dir)
        print(f"Frozen Phase 6 data to {args.output_dir}")
        print(json.dumps(metadata["instruments"], indent=2))
        return 0
    if args.command == "run":
        result = run_experiment(args.data_dir, args.output_dir)
        print(f"Wrote Phase 6 results to {args.output_dir}")
        print(f"Pre-registration commit hash: {result['pre_registration_commit_hash']}")
        print(f"Executable code commit hash: {result['code_commit_hash']}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
