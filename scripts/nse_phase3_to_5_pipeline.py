#!/usr/bin/env python3
"""Run AgentCo NSE Phases 3-5 on frozen data only."""
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
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from evals.financial_calibration_toolkit.calibration_analyzer import calibration_summary
from evals.financial_calibration_toolkit.nse_data_loader import load_frozen_real_instruments, visible_before
from evals.financial_calibration_toolkit.trust_scoring import original_trust
from evals.financial_calibration_toolkit.walk_forward_engine import position_from_weighted_signal, summarize_pnl


DEFAULT_PREREGISTRATION_COMMIT = "5464d2df1fd3f27f7aec943c959171ef5b9b5cec"
CAPITAL = 1_000_000.0
RNG_SEED = 42
FEATURE_COLUMNS = [
    "ret_1",
    "ret_2",
    "ret_5",
    "ret_10",
    "vol_10",
    "vol_20",
    "ma20_distance",
    "ma50_distance",
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


def build_feature_frame(instrument: str, df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    dates = sorted(pd.to_datetime(df["Date"]).tolist())
    for i, current_date in enumerate(dates[:-1]):
        visible = visible_before(df, current_date)
        if len(visible) < 60:
            continue

        closes = visible["Close"].astype(float)
        volumes = visible["Volume"].astype(float)
        current_close = float(df.loc[df["Date"] == current_date, "Close"].iloc[0])
        next_date = dates[i + 1]
        next_close = float(df.loc[df["Date"] == next_date, "Close"].iloc[0])

        returns = closes.pct_change()
        log_returns = np.log(closes).diff()
        ma20 = float(closes.tail(20).mean())
        ma50 = float(closes.tail(50).mean())
        vol20 = float(log_returns.tail(20).std())
        rsi14 = compute_rsi(closes.tail(15).to_numpy())
        volume_std = float(volumes.tail(20).std()) or 1.0
        volume_z20 = (float(volumes.iloc[-1]) - float(volumes.tail(20).mean())) / volume_std

        rows.append({
            "instrument": instrument,
            "prediction_date": current_date,
            "resolution_date": next_date,
            "ret_1": float(returns.iloc[-1]),
            "ret_2": float(closes.iloc[-1] / closes.iloc[-3] - 1.0),
            "ret_5": float(closes.iloc[-1] / closes.iloc[-6] - 1.0),
            "ret_10": float(closes.iloc[-1] / closes.iloc[-11] - 1.0),
            "vol_10": float(log_returns.tail(10).std()),
            "vol_20": vol20,
            "ma20_distance": float(closes.iloc[-1] / ma20 - 1.0),
            "ma50_distance": float(closes.iloc[-1] / ma50 - 1.0),
            "rsi14": rsi14 / 100.0,
            "volume_z20": float(volume_z20),
            "trend_up": 1.0 if closes.iloc[-1] > ma20 else 0.0,
            "vol_high": 1.0 if vol20 > 0.025 else 0.0,
            "label_up": 1 if next_close > current_close else 0,
            "market_return": float(next_close / current_close - 1.0),
        })

    frame = pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan).dropna()
    return frame.reset_index(drop=True)


def compute_rsi(closes: np.ndarray) -> float:
    deltas = np.diff(closes)
    gains = np.clip(deltas, 0, None)
    losses = -np.clip(deltas, None, 0)
    avg_gain = float(np.mean(gains)) if len(gains) else 0.0
    avg_loss = float(np.mean(losses)) if len(losses) else 0.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def split_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_end = int(len(frame) * 0.50)
    val_end = int(len(frame) * 0.75)
    return frame.iloc[:train_end].copy(), frame.iloc[train_end:val_end].copy(), frame.iloc[val_end:].copy()


def fit_agents(train: pd.DataFrame) -> dict[str, Any]:
    x_train = train[FEATURE_COLUMNS]
    y_train = train["label_up"]
    agents: dict[str, Any] = {
        "LogisticRegression": make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1000, random_state=RNG_SEED, class_weight="balanced"),
        ),
        "GradientBoosting": GradientBoostingClassifier(random_state=RNG_SEED, n_estimators=80, max_depth=2),
    }
    for model in agents.values():
        model.fit(x_train, y_train)

    regime_models = {}
    for regime_value in [0.0, 1.0]:
        subset = train[train["trend_up"] == regime_value]
        if len(subset) >= 40 and subset["label_up"].nunique() == 2:
            model = GradientBoostingClassifier(random_state=RNG_SEED, n_estimators=60, max_depth=2)
            model.fit(subset[FEATURE_COLUMNS], subset["label_up"])
            regime_models[regime_value] = model
    agents["RegimeSpecificGradientBoosting"] = regime_models
    return agents


def raw_prob(agent_name: str, model: Any, row: pd.Series, fallback: Any) -> float:
    features = pd.DataFrame([row[FEATURE_COLUMNS].to_dict()])
    if agent_name == "RegimeSpecificGradientBoosting":
        regime_model = model.get(float(row["trend_up"]))
        if regime_model is None:
            regime_model = fallback
        return float(regime_model.predict_proba(features)[0, 1])
    return float(model.predict_proba(features)[0, 1])


def build_predictions(frame: pd.DataFrame, agents: dict[str, Any], calibrators: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    records = []
    fallback = agents["GradientBoosting"]
    for _, row in frame.iterrows():
        for agent_name, model in agents.items():
            probability = raw_prob(agent_name, model, row, fallback)
            confidence = calibrated_confidence(agent_name, probability, calibrators) if calibrators else abs(probability - 0.5) * 2.0
            confidence = max(0.5, min(0.95, confidence))
            prediction = "up" if probability >= 0.5 else "down"
            hit = (prediction == "up" and row["label_up"] == 1) or (prediction == "down" and row["label_up"] == 0)
            records.append({
                "instrument": row["instrument"],
                "agent": agent_name,
                "prediction_date": row["prediction_date"],
                "resolution_date": row["resolution_date"],
                "prediction": prediction,
                "probability_up": probability,
                "confidence": confidence,
                "hit": bool(hit),
                "market_return": float(row["market_return"]),
            })
    return records


def fit_calibrators(validation_records: list[dict[str, Any]]) -> dict[str, Any]:
    calibrators = {}
    for agent in sorted({r["agent"] for r in validation_records}):
        subset = [r for r in validation_records if r["agent"] == agent]
        fallback = sum(1 for r in subset if r["hit"]) / len(subset)
        bins = []
        for low, high in [(0.0, 0.45), (0.45, 0.55), (0.55, 0.65), (0.65, 1.01)]:
            bucket = [r for r in subset if low <= r["probability_up"] < high]
            if len(bucket) >= 10:
                bins.append((low, high, sum(1 for r in bucket if r["hit"]) / len(bucket)))
        calibrators[agent] = {"fallback": fallback, "bins": bins}
    return calibrators


def calibrated_confidence(agent: str, probability: float, calibrators: dict[str, Any] | None) -> float:
    if not calibrators or agent not in calibrators:
        return 0.5 + abs(probability - 0.5)
    config = calibrators[agent]
    for low, high, empirical_hit_rate in config["bins"]:
        if low <= probability < high:
            return empirical_hit_rate
    return config["fallback"]


def simulate_test(validation_records: list[dict[str, Any]], test_records: list[dict[str, Any]], seed: int) -> dict[str, Any]:
    by_date: dict[pd.Timestamp, list[dict[str, Any]]] = defaultdict(list)
    for record in test_records:
        by_date[pd.to_datetime(record["prediction_date"])].append(record)

    histories = defaultdict(list)
    for record in validation_records:
        histories[record["agent"]].append(record)

    rng = np.random.RandomState(seed)
    policies = {
        "equal_ml": {"pnl": [], "cash": CAPITAL, "previous_position": 0.0, "halt": 0},
        "trust_ml": {"pnl": [], "cash": CAPITAL, "previous_position": 0.0, "halt": 0},
        "random_ml": {"pnl": [], "cash": CAPITAL, "previous_position": 0.0, "halt": 0},
        "risk_managed_trust_ml": {"pnl": [], "cash": CAPITAL, "previous_position": 0.0, "halt": 0},
        "costed_risk_managed_trust_ml": {"pnl": [], "cash": CAPITAL, "previous_position": 0.0, "halt": 0},
    }

    daily_rows = []
    for date in sorted(by_date):
        day_records = sorted(by_date[date], key=lambda r: r["agent"])
        market_return = day_records[0]["market_return"]
        agent_signals = {
            r["agent"]: (r["confidence"] if r["prediction"] == "up" else -r["confidence"])
            for r in day_records
        }
        trust_weights = {r["agent"]: original_trust(histories[r["agent"]]).trust for r in day_records}
        policy_weights = {
            "equal_ml": {agent: 1.0 for agent in agent_signals},
            "trust_ml": trust_weights,
            "random_ml": {agent: float(rng.uniform(0.0, 1.0)) for agent in agent_signals},
            "risk_managed_trust_ml": trust_weights,
            "costed_risk_managed_trust_ml": trust_weights,
        }
        for policy, state in policies.items():
            weighted_signal = weighted_average_signal(agent_signals, policy_weights[policy])
            if policy in {"risk_managed_trust_ml", "costed_risk_managed_trust_ml"}:
                weighted_signal = apply_risk_controls(weighted_signal, state)
            current_position = position_from_weighted_signal(weighted_signal, CAPITAL)
            gross_pnl = current_position * market_return
            cost = 0.0
            if policy == "costed_risk_managed_trust_ml":
                turnover = abs(current_position - state["previous_position"])
                if turnover > 0:
                    cost = turnover * 0.001 + 50.0
            pnl = gross_pnl - cost
            state["cash"] += pnl
            state["pnl"].append(pnl)
            state["previous_position"] = current_position
            daily_rows.append({
                "date": str(pd.to_datetime(date).date()),
                "policy": policy,
                "position": round(current_position, 4),
                "market_return": round(market_return, 8),
                "gross_pnl": round(gross_pnl, 4),
                "cost": round(cost, 4),
                "net_pnl": round(pnl, 4),
                "cash": round(state["cash"], 4),
            })
        for record in day_records:
            histories[record["agent"]].append(record)

    summaries = {policy: summarize_pnl(state["pnl"], CAPITAL) for policy, state in policies.items()}
    summaries["trust_ml"]["vs_random_pct"] = round(summaries["trust_ml"]["return_pct"] - summaries["random_ml"]["return_pct"], 4)
    summaries["costed_risk_managed_trust_ml"]["vs_random_pct"] = round(
        summaries["costed_risk_managed_trust_ml"]["return_pct"] - summaries["random_ml"]["return_pct"],
        4,
    )
    return {"summaries": summaries, "daily_rows": daily_rows}


def weighted_average_signal(signals: dict[str, float], weights: dict[str, float]) -> float:
    total_weight = sum(weights.values())
    if total_weight == 0:
        return 0.0
    return sum(signals[agent] * weights[agent] for agent in signals) / total_weight


def apply_risk_controls(signal: float, state: dict[str, Any]) -> float:
    drawdown = max(0.0, (CAPITAL - state["cash"]) / CAPITAL)
    if state["halt"] > 0:
        state["halt"] -= 1
        return 0.0
    if drawdown > 0.02:
        state["halt"] = 5
        return 0.0
    if drawdown > 0.01:
        return signal * 0.5
    return signal


def run_pipeline(data_dir: Path, seed: int, pre_registration_commit: str) -> dict[str, Any]:
    instruments = load_frozen_real_instruments(data_dir)
    instrument_results = {}
    all_test_records = []
    all_validation_records = []
    trust_vs_random = []
    costed_vs_random = []

    for instrument, df in instruments.items():
        frame = build_feature_frame(instrument, df)
        train, validation, test = split_frame(frame)
        agents = fit_agents(train)
        raw_validation = build_predictions(validation, agents, None)
        calibrators = fit_calibrators(raw_validation)
        validation_records = build_predictions(validation, agents, calibrators)
        test_records = build_predictions(test, agents, calibrators)
        simulation = simulate_test(validation_records, test_records, seed)
        trust_delta = simulation["summaries"]["trust_ml"]["vs_random_pct"]
        costed_delta = simulation["summaries"]["costed_risk_managed_trust_ml"]["vs_random_pct"]
        trust_vs_random.append(trust_delta)
        costed_vs_random.append(costed_delta)
        all_test_records.extend(test_records)
        all_validation_records.extend(validation_records)
        instrument_results[instrument] = {
            "rows": {"train": len(train), "validation": len(validation), "test": len(test)},
            "calibration_validation": calibration_summary(validation_records),
            "calibration_test": calibration_summary(test_records),
            "policy_summaries": simulation["summaries"],
        }

    aggregate = {
        "instruments": len(instrument_results),
        "trust_beats_random_count": sum(1 for value in trust_vs_random if value > 0),
        "trust_beats_random_share": round(sum(1 for value in trust_vs_random if value > 0) / len(trust_vs_random), 4),
        "median_trust_minus_random_pct": round(float(np.median(trust_vs_random)), 4),
        "mean_trust_minus_random_pct": round(float(np.mean(trust_vs_random)), 4),
        "costed_risk_beats_random_count": sum(1 for value in costed_vs_random if value > 0),
        "costed_risk_beats_random_share": round(sum(1 for value in costed_vs_random if value > 0) / len(costed_vs_random), 4),
        "median_costed_risk_minus_random_pct": round(float(np.median(costed_vs_random)), 4),
        "mean_costed_risk_minus_random_pct": round(float(np.mean(costed_vs_random)), 4),
    }

    return {
        "timestamp": datetime.now().isoformat(),
        "pre_registration_commit_hash": pre_registration_commit,
        "code_commit_hash": git_commit_hash(),
        "data_dir": str(data_dir),
        "rng_seed": seed,
        "blocked_items": [
            "Paper-to-live and small-capital trading were not executed; they require brokerage integration and user authorization.",
            "Alternative data signals were not added because no frozen sentiment/options-flow datasets exist in the repo.",
            "LSTM was not implemented because the frozen sample is too small for a defensible sequence model evaluation.",
        ],
        "aggregate": aggregate,
        "overall_validation_calibration": calibration_summary(all_validation_records),
        "overall_test_calibration": calibration_summary(all_test_records),
        "instrument_results": instrument_results,
    }


def write_report(output_dir: Path, results: dict[str, Any]) -> None:
    aggregate = results["aggregate"]
    if aggregate["trust_beats_random_share"] > 0.6 and aggregate["median_trust_minus_random_pct"] > 0:
        verdict = "Improved ML agents produced a candidate calibration signal requiring Phase 2b retesting."
    else:
        verdict = "Improved ML agents did not rescue the calibration edge on the available frozen NSE data."

    lines = [
        "# NSE Phases 3-5 Results",
        "",
        f"**Date:** {datetime.now().date()}",
        f"**Pre-registration commit hash:** `{results['pre_registration_commit_hash']}`",
        f"**Executable code commit hash:** `{results['code_commit_hash']}`",
        f"**Frozen data:** `{results['data_dir']}`",
        "",
        "## Verdict",
        "",
        verdict,
        "",
        "## Aggregate",
        "",
        f"- Trust ML beats random: `{aggregate['trust_beats_random_count']}/{aggregate['instruments']}` instruments (`{aggregate['trust_beats_random_share']:.1%}`)",
        f"- Median trust-random return: `{aggregate['median_trust_minus_random_pct']:.4f}%`",
        f"- Costed risk-managed trust beats random: `{aggregate['costed_risk_beats_random_count']}/{aggregate['instruments']}` instruments (`{aggregate['costed_risk_beats_random_share']:.1%}`)",
        f"- Median costed-risk-random return: `{aggregate['median_costed_risk_minus_random_pct']:.4f}%`",
        "",
        "## Instrument Results",
        "",
        "| Instrument | Test Days | Trust-Random | Costed Risk-Random | Trust Return | Random Return | Costed Risk Return |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for instrument, row in results["instrument_results"].items():
        summaries = row["policy_summaries"]
        lines.append(
            f"| {instrument} | {row['rows']['test']} | "
            f"{summaries['trust_ml']['vs_random_pct']:.4f}% | "
            f"{summaries['costed_risk_managed_trust_ml']['vs_random_pct']:.4f}% | "
            f"{summaries['trust_ml']['return_pct']:.4f}% | "
            f"{summaries['random_ml']['return_pct']:.4f}% | "
            f"{summaries['costed_risk_managed_trust_ml']['return_pct']:.4f}% |"
        )

    lines.extend([
        "",
        "## Test Calibration",
        "",
        "| Agent | Predictions | Hit Rate | Avg Confidence | Calibration Error |",
        "|---|---:|---:|---:|---:|",
    ])
    for agent, row in results["overall_test_calibration"].items():
        lines.append(
            f"| {agent} | {row['predictions']} | {row['hit_rate']:.1%} | "
            f"{row['avg_confidence']:.1%} | {row['calibration_error']:.1%} |"
        )

    lines.extend([
        "",
        "## Blocked Items",
        "",
    ])
    for item in results["blocked_items"]:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "Full calibration curves and per-instrument policy summaries are in `phase3_to_5_results.json`.",
        "",
    ])
    (output_dir / "PHASE3_TO_5_RESULTS.md").write_text("\n".join(lines))


def write_phase5_docs(docs_dir: Path) -> None:
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "research_paper_draft.md").write_text(
        """# Fair Testing of Calibration-Weighted Decision-Making on Real Markets

## Abstract

AgentCo tested whether calibration-weighted decision-making improves paper-trading outcomes on frozen real NSE market data. Across pre-registered STOP 2, Phase 1, Phase 2, and Phase 3-4 tests, trust-weighting did not reliably outperform random-placebo weighting. The dominant diagnostic was persistent overconfidence: agents expressed confidence materially above realized hit rates.

## Method

The framework used frozen data, strict walk-forward feature construction, pre-registration before execution, random-placebo controls, and calibration curves as the primary diagnostic. Later phases added trained ML agents, chronological train/validation/test splits, transaction costs, and risk controls.

## Result

No deployable edge was found. Where paper improvements appeared in isolated windows, they failed the locked cross-market consistency criteria or were not robust after costs and risk controls.

## Interpretation

The result does not falsify calibration-weighted decision-making in general. It shows that on this frozen NSE sample, with these agents and limited data, calibration signal is not separable from market noise.
"""
    )
    (docs_dir / "internal_lessons.md").write_text(
        """# AgentCo Calibration Market Lessons

- Pre-registration prevented post-hoc reinterpretation of noisy wins.
- Random-placebo weighting was essential; equal-weight baselines alone were misleading.
- Calibration curves were more informative than returns.
- Better model classes did not automatically fix overconfidence.
- Live validation remains blocked until broker integration, frozen live/paper comparison rules, and user-authorized capital limits are defined.
"""
    )
    (docs_dir / "open_source_toolkit.md").write_text(
        """# Financial Calibration Toolkit

Reusable modules live under `evals/financial_calibration_toolkit`:

- `nse_data_loader.py`: frozen data loading and strict past-only slicing
- `calibration_analyzer.py`: confidence-bin calibration summaries
- `trust_scoring.py`: trust score snapshots
- `walk_forward_engine.py`: P&L and position helpers

The toolkit is intentionally small and dependency-light so future experiments can reuse the integrity structure without inheriting NSE-specific scripts.
"""
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("evals/experiments/nse_data_frozen"))
    parser.add_argument("--output-dir", type=Path, default=Path("evals/experiments/nse_phase3_to_5_results"))
    parser.add_argument("--seed", type=int, default=RNG_SEED)
    parser.add_argument("--pre-registration-commit", default=DEFAULT_PREREGISTRATION_COMMIT)
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = run_pipeline(args.data_dir, args.seed, args.pre_registration_commit)
    with open(args.output_dir / "phase3_to_5_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    rows = []
    for instrument, row in results["instrument_results"].items():
        summaries = row["policy_summaries"]
        rows.append({
            "instrument": instrument,
            "test_days": row["rows"]["test"],
            "trust_minus_random_pct": summaries["trust_ml"]["vs_random_pct"],
            "costed_risk_minus_random_pct": summaries["costed_risk_managed_trust_ml"]["vs_random_pct"],
            "trust_return_pct": summaries["trust_ml"]["return_pct"],
            "random_return_pct": summaries["random_ml"]["return_pct"],
            "costed_risk_return_pct": summaries["costed_risk_managed_trust_ml"]["return_pct"],
        })
    pd.DataFrame(rows).to_csv(args.output_dir / "phase3_to_5_policy_summary.csv", index=False)
    write_report(args.output_dir, results)
    write_phase5_docs(args.output_dir / "phase5_docs")
    print(f"Wrote Phase 3-5 results to {args.output_dir}")
    print(f"Pre-registration commit hash: {results['pre_registration_commit_hash']}")
    print(f"Executable code commit hash: {results['code_commit_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
