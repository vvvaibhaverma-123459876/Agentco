#!/usr/bin/env python3
"""Phase 1 root-cause diagnostics for NSE calibration-weighted decisions.

Uses frozen NSE data only. All forecasts and trust updates are walk-forward and
strictly past-only.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from nse_three_arm_walkforward import (
    MeanReversionAgent,
    RegimeAgent,
    TechnicalAgent,
    compute_trust_score,
    get_data_up_to,
    load_real_data,
)


AGENTS = {
    "Technical": TechnicalAgent(),
    "Regime": RegimeAgent(),
    "MeanReversion": MeanReversionAgent(),
}

DEFAULT_PREREGISTRATION_COMMIT = "cbfbb85808d195ae6a25031925f83bc02f5fc170"


@dataclass(frozen=True)
class TrustSnapshot:
    trust: float
    hit_rate: float
    avg_confidence: float
    calibration_error: float
    sample_count: int


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def git_commit_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def nifty_key(real_data: dict[str, pd.DataFrame]) -> str:
    return [k for k in real_data if "nifty" in k.lower() and "bank" not in k.lower()][0]


def indicator_snapshot(visible_data: dict[str, pd.DataFrame]) -> dict[str, Any]:
    key = nifty_key(visible_data)
    df = visible_data.get(key, pd.DataFrame())
    if len(df) == 0:
        return {
            "trend": "unknown",
            "volatility": "unknown",
            "regime": "unknown|unknown",
            "rsi_signal": "unknown",
            "macd_signal": "unknown",
            "ma50_side": "unknown",
            "ma50_distance_bucket": "unknown",
        }

    closes = df["Close"].astype(float).values

    trend = "unknown"
    volatility = "unknown"
    if len(closes) >= 20:
        recent = closes[-20:]
        sma20 = float(np.mean(recent))
        trend = "uptrend" if recent[-1] > sma20 else "downtrend"
        returns = np.diff(np.log(recent))
        vol = float(np.std(returns))
        volatility = "low" if vol < 0.015 else ("high" if vol > 0.025 else "normal")

    rsi_signal = "unknown"
    if len(closes) >= 15:
        deltas = np.diff(closes[-15:])
        seed = abs(deltas[:1]).sum()
        up = seed if deltas[0] > 0 else 0
        down = seed if deltas[0] < 0 else -deltas[0]
        for delta in deltas[1:]:
            up = up * 13 / 14 + max(delta, 0) / 14
            down = down * 13 / 14 - min(delta, 0) / 14
        rs = up / max(down, 0.0001)
        rsi = 100.0 - 100.0 / (1.0 + rs)
        rsi_signal = "oversold_up" if rsi < 30 else ("overbought_down" if rsi > 70 else "neutral")

    macd_signal = "unknown"
    if len(closes) >= 12:
        ema12 = closes[-12:].mean()
        ema26 = closes[-26:].mean() if len(closes) >= 26 else ema12
        signal = closes[-9:].mean() if len(closes) >= 9 else closes.mean()
        histogram = (ema12 - ema26) - signal
        macd_signal = "up" if histogram > 0 else "down"

    ma50_side = "unknown"
    ma50_distance_bucket = "unknown"
    if len(closes) >= 50:
        ma50 = float(closes[-50:].mean())
        distance = abs(float(closes[-1]) - ma50) / ma50
        ma50_side = "above_ma50" if closes[-1] > ma50 else "below_ma50"
        if distance < 0.01:
            ma50_distance_bucket = "lt_1pct"
        elif distance < 0.03:
            ma50_distance_bucket = "1_to_3pct"
        else:
            ma50_distance_bucket = "gt_3pct"

    return {
        "trend": trend,
        "volatility": volatility,
        "regime": f"{trend}|{volatility}",
        "rsi_signal": rsi_signal,
        "macd_signal": macd_signal,
        "ma50_side": ma50_side,
        "ma50_distance_bucket": ma50_distance_bucket,
    }


def build_prediction_records(real_data: dict[str, pd.DataFrame]) -> tuple[list[dict[str, Any]], list[pd.Timestamp]]:
    key = nifty_key(real_data)
    trading_dates = sorted(pd.to_datetime(real_data[key]["Date"]).tolist())
    records: list[dict[str, Any]] = []

    for i, current_date in enumerate(trading_dates[:-1]):
        visible_data = get_data_up_to(real_data, current_date)
        features = indicator_snapshot(visible_data)
        next_date = trading_dates[i + 1]

        current_close = real_data[key].loc[real_data[key]["Date"] == current_date, "Close"]
        next_close = real_data[key].loc[real_data[key]["Date"] == next_date, "Close"]
        if len(current_close) == 0 or len(next_close) == 0:
            continue

        current_val = float(current_close.iloc[0])
        next_val = float(next_close.iloc[0])
        direction = "up" if next_val > current_val else ("down" if next_val < current_val else "flat")
        market_return = (next_val - current_val) / current_val

        for agent_name, agent in AGENTS.items():
            pred = agent.forecast(visible_data, current_date)
            hit = (direction == pred["prediction"]) or (direction == "flat" and pred["prediction"] == "neutral")
            records.append({
                "agent": agent_name,
                "prediction_date": current_date,
                "resolution_date": next_date,
                "prediction": pred["prediction"],
                "confidence": float(pred["confidence"]),
                "hit": bool(hit),
                "actual_direction": direction,
                "market_return": market_return,
                **features,
            })

    return records, trading_dates


def split_for_date(date: pd.Timestamp, trading_dates: list[pd.Timestamp]) -> str:
    index = trading_dates.index(date)
    train_end = int(len(trading_dates) * 0.50)
    val_end = int(len(trading_dates) * 0.75)
    if index < train_end:
        return "train"
    if index < val_end:
        return "validation"
    return "test"


def calibration_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for agent in sorted({r["agent"] for r in records}):
        subset = [r for r in records if r["agent"] == agent]
        hits = sum(1 for r in subset if r["hit"])
        avg_conf = statistics.mean(r["confidence"] for r in subset)
        hit_rate = hits / len(subset) if subset else 0.0
        summary[agent] = {
            "predictions": len(subset),
            "hit_rate": round(hit_rate, 4),
            "avg_confidence": round(avg_conf, 4),
            "calibration_error": round(avg_conf - hit_rate, 4),
            "confidence_bins": grouped_calibration(subset, "confidence_bin"),
            "regime_bins": grouped_calibration(subset, "regime"),
        }
    return summary


def grouped_calibration(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if key == "confidence_bin":
            confidence = record["confidence"]
            if confidence < 0.55:
                bucket = "0.45-0.55"
            elif confidence < 0.65:
                bucket = "0.55-0.65"
            elif confidence < 0.75:
                bucket = "0.65-0.75"
            else:
                bucket = "0.75-0.85"
        else:
            bucket = str(record.get(key, "unknown"))
        groups[bucket].append(record)

    rows = []
    for bucket, subset in sorted(groups.items()):
        hit_rate = sum(1 for r in subset if r["hit"]) / len(subset)
        avg_conf = statistics.mean(r["confidence"] for r in subset)
        rows.append({
            "bucket": bucket,
            "n": len(subset),
            "hit_rate": round(hit_rate, 4),
            "avg_confidence": round(avg_conf, 4),
            "calibration_error": round(avg_conf - hit_rate, 4),
        })
    return rows


def indicator_diagnostics(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "Technical.rsi_signal": grouped_calibration([r for r in records if r["agent"] == "Technical"], "rsi_signal"),
        "Technical.macd_signal": grouped_calibration([r for r in records if r["agent"] == "Technical"], "macd_signal"),
        "Regime.trend": grouped_calibration([r for r in records if r["agent"] == "Regime"], "trend"),
        "Regime.volatility": grouped_calibration([r for r in records if r["agent"] == "Regime"], "volatility"),
        "MeanReversion.ma50_side": grouped_calibration([r for r in records if r["agent"] == "MeanReversion"], "ma50_side"),
        "MeanReversion.ma50_distance_bucket": grouped_calibration(
            [r for r in records if r["agent"] == "MeanReversion"],
            "ma50_distance_bucket",
        ),
    }


def trust_snapshot(history: list[dict[str, Any]], formula: str, current_regime: str | None = None) -> TrustSnapshot:
    if formula == "regime_adjusted" and current_regime is not None:
        regime_history = [r for r in history if r["regime"] == current_regime]
        if len(regime_history) >= 20:
            history = regime_history

    if not history:
        return TrustSnapshot(0.5, 0.0, 0.5, 0.0, 0)

    if formula == "recency_weighted":
        latest = max(pd.to_datetime(r["resolution_date"]) for r in history)
        weights = []
        for record in history:
            age = (latest - pd.to_datetime(record["resolution_date"])).days
            weights.append(math.exp(-math.log(2) * age / 63.0))
        weight_sum = sum(weights)
        hit_rate = sum(w * float(r["hit"]) for w, r in zip(weights, history)) / weight_sum
        avg_conf = sum(w * r["confidence"] for w, r in zip(weights, history)) / weight_sum
        synthetic = [{"hit": r["hit"], "confidence": r["confidence"]} for r in history]
        trust = compute_trust_from_rates(hit_rate, avg_conf)
        return TrustSnapshot(trust, hit_rate, avg_conf, max(0.0, avg_conf - hit_rate), len(synthetic))

    hit_rate = sum(1 for r in history if r["hit"]) / len(history)
    avg_conf = statistics.mean(r["confidence"] for r in history)
    if formula == "confidence_adjusted":
        trust = clamp(hit_rate / avg_conf) if avg_conf > 0 else 0.0
    else:
        trust = compute_trust_score(history)
    return TrustSnapshot(trust, hit_rate, avg_conf, max(0.0, avg_conf - hit_rate), len(history))


def compute_trust_from_rates(hit_rate: float, avg_confidence: float) -> float:
    if avg_confidence <= hit_rate:
        trust = hit_rate + 0.05 * (hit_rate - avg_confidence)
    else:
        trust = hit_rate - 0.1 * (avg_confidence - hit_rate)
    return clamp(trust)


def apply_curve(snapshot: TrustSnapshot, curve: str) -> float:
    if curve == "linear":
        return snapshot.trust
    if curve == "dynamic_clipped":
        return clamp(snapshot.trust * max(0.25, 1.0 - snapshot.calibration_error))
    if curve == "sigmoid":
        return clamp(1.0 / (1.0 + math.exp(-8.0 * (snapshot.trust - 0.5))))
    raise ValueError(f"Unknown curve: {curve}")


def position_from_predictions(predictions: list[dict[str, Any]], weights: list[float], capital: float) -> float:
    signals = []
    for pred in predictions:
        if pred["prediction"] == "up":
            signals.append(pred["confidence"])
        elif pred["prediction"] == "down":
            signals.append(-pred["confidence"])
        else:
            signals.append(0.0)
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    weighted_signal = sum(s * w for s, w in zip(signals, weights)) / total_weight
    return max(-0.05 * capital, min(0.05 * capital, capital * weighted_signal * 0.05))


def simulate_policies(records: list[dict[str, Any]], trading_dates: list[pd.Timestamp]) -> dict[str, Any]:
    by_date: dict[pd.Timestamp, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_date[pd.to_datetime(record["prediction_date"])].append(record)

    formulas = ["original", "confidence_adjusted", "recency_weighted", "regime_adjusted"]
    curves = ["linear", "dynamic_clipped", "sigmoid"]
    policies = ["equal", "random"] + [f"{formula}+{curve}" for formula in formulas for curve in curves]
    capital = 1_000_000.0
    rng = np.random.RandomState(42)
    state = {policy: {"cash": capital, "daily_pnl": []} for policy in policies}
    histories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    trust_rows: list[dict[str, Any]] = []

    for date in trading_dates[:-1]:
        day_records = sorted(by_date.get(date, []), key=lambda r: r["agent"])
        if len(day_records) != len(AGENTS):
            continue

        split = split_for_date(date, trading_dates)
        market_return = day_records[0]["market_return"]
        current_regime = day_records[0]["regime"]

        for policy in policies:
            if policy == "equal":
                weights = [1.0 for _ in day_records]
            elif policy == "random":
                weights = [float(rng.uniform(0.0, 1.0)) for _ in day_records]
            else:
                formula, curve = policy.split("+", 1)
                weights = []
                for record in day_records:
                    snapshot = trust_snapshot(histories[record["agent"]], formula, current_regime)
                    weights.append(apply_curve(snapshot, curve))
                    if split == "test":
                        trust_rows.append({
                            "date": str(date.date()),
                            "policy": policy,
                            "agent": record["agent"],
                            "trust": round(snapshot.trust, 6),
                            "weight": round(weights[-1], 6),
                            "history_n": snapshot.sample_count,
                            "hit_rate": round(snapshot.hit_rate, 6),
                            "avg_confidence": round(snapshot.avg_confidence, 6),
                            "calibration_error": round(snapshot.calibration_error, 6),
                        })
            pnl = position_from_predictions(day_records, weights, capital) * market_return
            state[policy]["cash"] += pnl
            state[policy]["daily_pnl"].append({"split": split, "pnl": pnl})

        for record in day_records:
            histories[record["agent"]].append(record)

    summaries: dict[str, Any] = {}
    for policy, values in state.items():
        all_pnl = [row["pnl"] for row in values["daily_pnl"]]
        test_pnl = [row["pnl"] for row in values["daily_pnl"] if row["split"] == "test"]
        summaries[policy] = {
            "final_cash_all": round(capital + sum(all_pnl), 2),
            "return_pct_all": round(100.0 * sum(all_pnl) / capital, 4),
            "return_pct_test": round(100.0 * sum(test_pnl) / capital, 4),
            "test_positive_days": sum(1 for pnl in test_pnl if pnl > 0),
            "test_days": len(test_pnl),
            "test_sharpe": sharpe(test_pnl, capital),
        }

    random_test = summaries["random"]["return_pct_test"]
    for policy, values in summaries.items():
        values["test_vs_random_pct"] = round(values["return_pct_test"] - random_test, 4)

    return {"policy_summaries": summaries, "trust_rows": trust_rows}


def sharpe(pnl: list[float], capital: float) -> float:
    if len(pnl) < 2:
        return 0.0
    returns = [x / capital for x in pnl]
    std = statistics.stdev(returns)
    if std == 0:
        return 0.0
    return round(statistics.mean(returns) / std, 4)


def write_report(output_dir: Path, results: dict[str, Any]) -> None:
    policies = results["policy_summaries"]
    ranked = sorted(policies.items(), key=lambda item: item[1]["test_vs_random_pct"], reverse=True)
    best_policy, best_values = ranked[0]

    lines = [
        "# NSE Phase 1 Root Cause Investigation Results",
        "",
        f"**Date:** {datetime.now().date()}",
        f"**Pre-registration commit hash:** `{results['pre_registration_commit_hash']}`",
        f"**Executable code commit hash:** `{results['code_commit_hash']}`",
        f"**Frozen data:** `{results['data_dir']}`",
        "",
        "## Verdict",
        "",
    ]

    if best_policy == "random" or best_values["test_vs_random_pct"] < 0.5:
        lines.append(
            "No robust held-out calibration edge was found. The STOP 2 null remains the honest interpretation: "
            "agent overconfidence and market noise dominate reasonable trust-score and weighting-curve changes."
        )
    else:
        lines.append(
            f"`{best_policy}` beat random-placebo by {best_values['test_vs_random_pct']} percentage points on held-out data. "
            "This is only a Phase 2 retest candidate, not an edge claim."
        )

    lines.extend([
        "",
        "## Overall Calibration",
        "",
        "| Agent | Predictions | Hit Rate | Avg Confidence | Calibration Error |",
        "|---|---:|---:|---:|---:|",
    ])
    for agent, row in results["calibration"].items():
        lines.append(
            f"| {agent} | {row['predictions']} | {row['hit_rate']:.1%} | "
            f"{row['avg_confidence']:.1%} | {row['calibration_error']:.1%} |"
        )

    lines.extend([
        "",
        "## Held-Out Policy Screen",
        "",
        "| Policy | Test Return | Test vs Random | Test Sharpe | Positive Days |",
        "|---|---:|---:|---:|---:|",
    ])
    for policy, row in ranked:
        lines.append(
            f"| {policy} | {row['return_pct_test']:.4f}% | {row['test_vs_random_pct']:.4f}% | "
            f"{row['test_sharpe']:.4f} | {row['test_positive_days']}/{row['test_days']} |"
        )

    lines.extend([
        "",
        "## Primary Diagnostic",
        "",
        "Calibration curves and indicator/regime buckets are in `phase1_root_cause_results.json`. "
        "The policy screen is secondary and should not be reinterpreted as a trading result.",
        "",
    ])
    (output_dir / "PHASE1_ROOT_CAUSE_RESULTS.md").write_text("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("evals/experiments/nse_data_frozen"))
    parser.add_argument("--output-dir", type=Path, default=Path("evals/experiments/nse_phase1_root_cause_results"))
    parser.add_argument("--pre-registration-commit", default=DEFAULT_PREREGISTRATION_COMMIT)
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    real_data = load_real_data(args.data_dir)
    records, trading_dates = build_prediction_records(real_data)
    for record in records:
        record["split"] = split_for_date(pd.to_datetime(record["prediction_date"]), trading_dates)

    simulation = simulate_policies(records, trading_dates)
    results = {
        "timestamp": datetime.now().isoformat(),
        "pre_registration_commit_hash": args.pre_registration_commit,
        "code_commit_hash": git_commit_hash(),
        "data_dir": str(args.data_dir),
        "trading_days": len(trading_dates),
        "predictions": len(records),
        "split_counts": {
            str(split): int(count)
            for split, count in pd.Series([r["split"] for r in records]).value_counts().items()
        },
        "calibration": calibration_summary(records),
        "indicator_diagnostics": indicator_diagnostics(records),
        "policy_summaries": simulation["policy_summaries"],
    }

    with open(args.output_dir / "phase1_root_cause_results.json", "w") as f:
        json.dump(results, f, indent=2)

    pd.DataFrame(records).to_csv(args.output_dir / "phase1_prediction_diagnostics.csv", index=False)
    pd.DataFrame(simulation["trust_rows"]).to_csv(args.output_dir / "phase1_test_trust_history.csv", index=False)
    write_report(args.output_dir, results)

    print(f"Wrote Phase 1 results to {args.output_dir}")
    print(f"Pre-registration commit hash: {results['pre_registration_commit_hash']}")
    print(f"Executable code commit hash: {results['code_commit_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
