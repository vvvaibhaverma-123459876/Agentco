#!/usr/bin/env python3
"""Phase 2 extended-market NSE tests on frozen real data only."""
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

DEFAULT_PREREGISTRATION_COMMIT = "PENDING_LOCK_COMMIT"
CAPITAL = 1_000_000.0
MIN_ELIGIBLE_DAYS = 100


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


def load_real_instruments(data_dir: Path) -> dict[str, pd.DataFrame]:
    instruments = {}
    for csv_path in sorted(data_dir.glob("*_REAL.csv")):
        name = csv_path.stem.replace("_REAL", "").replace("_", " ").upper()
        df = pd.read_csv(csv_path)
        df["Date"] = pd.to_datetime(df["Date"])
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")
        df = df[["Date", "Close", "Volume"]].dropna(subset=["Date", "Close"])
        instruments[name] = df.sort_values("Date").reset_index(drop=True)
    return instruments


def visible_before(df: pd.DataFrame, prediction_date: pd.Timestamp) -> pd.DataFrame:
    visible = df[df["Date"] < prediction_date].copy()
    if len(visible) > 0:
        assert visible["Date"].max() < prediction_date, "LOOKAHEAD DETECTED"
    return visible


def technical_forecast(visible: pd.DataFrame) -> dict[str, Any]:
    if len(visible) < 14:
        return {"prediction": "neutral", "confidence": 0.5}

    closes = visible["Close"].astype(float).values
    deltas = np.diff(closes[-15:])
    seed = abs(deltas[:1]).sum()
    up = seed if deltas[0] > 0 else 0
    down = seed if deltas[0] < 0 else -deltas[0]

    for delta in deltas[1:]:
        up = up * 13 / 14 + max(delta, 0) / 14
        down = down * 13 / 14 - min(delta, 0) / 14

    rs = up / max(down, 0.0001)
    rsi = 100.0 - 100.0 / (1.0 + rs)

    ema12 = closes[-12:].mean()
    ema26 = closes[-26:].mean() if len(closes) >= 26 else ema12
    signal = closes[-9:].mean() if len(closes) >= 9 else closes.mean()
    histogram = (ema12 - ema26) - signal

    rsi_signal = 1.0 if rsi < 30 else (-1.0 if rsi > 70 else 0.0)
    macd_signal = 1.0 if histogram > 0 else -1.0
    combined = rsi_signal + macd_signal
    prediction = "up" if combined > 0 else ("down" if combined < 0 else "neutral")
    confidence = min(0.75, 0.5 + abs(combined) * 0.15)
    return {"prediction": prediction, "confidence": confidence}


def regime_forecast(visible: pd.DataFrame) -> dict[str, Any]:
    if len(visible) < 20:
        return {"prediction": "neutral", "confidence": 0.5}
    closes = visible["Close"].astype(float).values[-20:]
    returns = np.diff(np.log(closes))
    trend = 1.0 if closes[-1] > closes.mean() else -1.0
    realized_vol = np.std(returns)
    vol_regime = "low" if realized_vol < 0.015 else ("high" if realized_vol > 0.025 else "normal")
    if vol_regime == "low":
        return {"prediction": "up" if trend > 0 else "down", "confidence": 0.70}
    if vol_regime == "high":
        return {"prediction": "neutral", "confidence": 0.45}
    return {"prediction": "up" if trend > 0 else "down", "confidence": 0.60}


def mean_reversion_forecast(visible: pd.DataFrame) -> dict[str, Any]:
    if len(visible) < 50:
        return {"prediction": "neutral", "confidence": 0.5}
    closes = visible["Close"].astype(float).values
    ma50 = closes[-50:].mean()
    current = closes[-1]
    distance_pct = abs(current - ma50) / ma50
    prediction = "down" if current > ma50 else "up"
    confidence = min(0.75, 0.5 + distance_pct * 5.0)
    return {"prediction": prediction, "confidence": confidence}


def forecasts_for_day(visible: pd.DataFrame) -> dict[str, dict[str, Any]]:
    return {
        "Technical": technical_forecast(visible),
        "Regime": regime_forecast(visible),
        "MeanReversion": mean_reversion_forecast(visible),
    }


def trust_original(history: list[dict[str, Any]]) -> TrustSnapshot:
    if not history:
        return TrustSnapshot(0.5, 0.0, 0.5, 0.0, 0)
    hit_rate = sum(1 for r in history if r["hit"]) / len(history)
    avg_confidence = statistics.mean(r["confidence"] for r in history)
    if avg_confidence <= hit_rate:
        trust = hit_rate + 0.05 * (hit_rate - avg_confidence)
    else:
        trust = hit_rate - 0.1 * (avg_confidence - hit_rate)
    return TrustSnapshot(clamp(trust), hit_rate, avg_confidence, avg_confidence - hit_rate, len(history))


def trust_recency_weighted(history: list[dict[str, Any]]) -> TrustSnapshot:
    if not history:
        return TrustSnapshot(0.5, 0.0, 0.5, 0.0, 0)
    latest = max(pd.to_datetime(r["resolution_date"]) for r in history)
    weights = []
    for record in history:
        age = (latest - pd.to_datetime(record["resolution_date"])).days
        weights.append(math.exp(-math.log(2) * age / 63.0))
    weight_sum = sum(weights)
    hit_rate = sum(w * float(r["hit"]) for w, r in zip(weights, history)) / weight_sum
    avg_confidence = sum(w * r["confidence"] for w, r in zip(weights, history)) / weight_sum
    if avg_confidence <= hit_rate:
        trust = hit_rate + 0.05 * (hit_rate - avg_confidence)
    else:
        trust = hit_rate - 0.1 * (avg_confidence - hit_rate)
    return TrustSnapshot(clamp(trust), hit_rate, avg_confidence, avg_confidence - hit_rate, len(history))


def sigmoid_weight(snapshot: TrustSnapshot) -> float:
    return clamp(1.0 / (1.0 + math.exp(-8.0 * (snapshot.trust - 0.5))))


def position(predictions: dict[str, dict[str, Any]], weights: dict[str, float]) -> float:
    weighted_sum = 0.0
    total_weight = 0.0
    for agent, pred in predictions.items():
        if pred["prediction"] == "up":
            signal = pred["confidence"]
        elif pred["prediction"] == "down":
            signal = -pred["confidence"]
        else:
            signal = 0.0
        weight = weights.get(agent, 0.0)
        weighted_sum += signal * weight
        total_weight += weight
    if total_weight == 0:
        return 0.0
    weighted_signal = weighted_sum / total_weight
    return max(-0.05 * CAPITAL, min(0.05 * CAPITAL, CAPITAL * weighted_signal * 0.05))


def build_records(instrument: str, df: pd.DataFrame) -> list[dict[str, Any]]:
    records = []
    dates = sorted(pd.to_datetime(df["Date"]).tolist())
    for i, current_date in enumerate(dates[:-1]):
        next_date = dates[i + 1]
        visible = visible_before(df, current_date)
        predictions = forecasts_for_day(visible)
        current_close = float(df.loc[df["Date"] == current_date, "Close"].iloc[0])
        next_close = float(df.loc[df["Date"] == next_date, "Close"].iloc[0])
        actual_direction = "up" if next_close > current_close else ("down" if next_close < current_close else "flat")
        market_return = (next_close - current_close) / current_close
        for agent, pred in predictions.items():
            hit = (actual_direction == pred["prediction"]) or (
                actual_direction == "flat" and pred["prediction"] == "neutral"
            )
            records.append({
                "instrument": instrument,
                "agent": agent,
                "prediction_date": current_date,
                "resolution_date": next_date,
                "prediction": pred["prediction"],
                "confidence": float(pred["confidence"]),
                "hit": bool(hit),
                "actual_direction": actual_direction,
                "market_return": market_return,
            })
    return records


def window_definitions(dates: list[pd.Timestamp]) -> dict[str, set[pd.Timestamp]]:
    windows: dict[str, set[pd.Timestamp]] = {}
    usable = dates[:-1]
    midpoint = len(usable) // 2
    windows["full"] = set(usable)
    windows["first_half"] = set(usable[:midpoint])
    windows["second_half"] = set(usable[midpoint:])
    block_size = 126
    for start in range(0, len(usable), block_size):
        block = usable[start:start + block_size]
        if len(block) >= MIN_ELIGIBLE_DAYS:
            windows[f"block_{start // block_size + 1:02d}"] = set(block)
    return windows


def simulate_window(records: list[dict[str, Any]], window_dates: set[pd.Timestamp], seed: int) -> dict[str, Any]:
    by_date: dict[pd.Timestamp, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_date[pd.to_datetime(record["prediction_date"])].append(record)

    histories = {agent: [] for agent in ["MeanReversion", "Regime", "Technical"]}
    rng = np.random.RandomState(seed)
    policies = {
        "A_equal": [],
        "B_original": [],
        "P_random": [],
        "C_phase1_recency_sigmoid": [],
    }

    for date in sorted(by_date):
        day_records = sorted(by_date[date], key=lambda r: r["agent"])
        predictions = {r["agent"]: {"prediction": r["prediction"], "confidence": r["confidence"]} for r in day_records}
        market_return = day_records[0]["market_return"]

        if date in window_dates:
            equal_weights = {agent: 1.0 for agent in predictions}
            original_weights = {agent: trust_original(histories[agent]).trust for agent in predictions}
            random_weights = {agent: float(rng.uniform(0.0, 1.0)) for agent in predictions}
            candidate_weights = {agent: sigmoid_weight(trust_recency_weighted(histories[agent])) for agent in predictions}

            for policy, weights in [
                ("A_equal", equal_weights),
                ("B_original", original_weights),
                ("P_random", random_weights),
                ("C_phase1_recency_sigmoid", candidate_weights),
            ]:
                policies[policy].append(position(predictions, weights) * market_return)

        for record in day_records:
            histories[record["agent"]].append(record)

    summary = {}
    for policy, pnl in policies.items():
        summary[policy] = summarize_pnl(pnl)
    return summary


def summarize_pnl(pnl: list[float]) -> dict[str, Any]:
    if not pnl:
        return {"days": 0, "return_pct": 0.0, "sharpe": 0.0, "positive_days": 0}
    returns = [value / CAPITAL for value in pnl]
    std = statistics.stdev(returns) if len(returns) > 1 else 0.0
    sharpe = statistics.mean(returns) / std if std > 0 else 0.0
    return {
        "days": len(pnl),
        "return_pct": round(100.0 * sum(pnl) / CAPITAL, 4),
        "sharpe": round(sharpe, 4),
        "positive_days": sum(1 for value in pnl if value > 0),
    }


def calibration_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    output = {}
    for agent in sorted({r["agent"] for r in records}):
        subset = [r for r in records if r["agent"] == agent]
        hit_rate = sum(1 for r in subset if r["hit"]) / len(subset)
        avg_confidence = statistics.mean(r["confidence"] for r in subset)
        output[agent] = {
            "predictions": len(subset),
            "hit_rate": round(hit_rate, 4),
            "avg_confidence": round(avg_confidence, 4),
            "calibration_error": round(avg_confidence - hit_rate, 4),
            "confidence_bins": confidence_bins(subset),
        }
    return output


def confidence_bins(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        confidence = record["confidence"]
        if confidence < 0.55:
            bucket = "0.45-0.55"
        elif confidence < 0.65:
            bucket = "0.55-0.65"
        elif confidence < 0.75:
            bucket = "0.65-0.75"
        else:
            bucket = "0.75-0.85"
        buckets[bucket].append(record)
    rows = []
    for bucket, subset in sorted(buckets.items()):
        hit_rate = sum(1 for r in subset if r["hit"]) / len(subset)
        avg_confidence = statistics.mean(r["confidence"] for r in subset)
        rows.append({
            "bucket": bucket,
            "n": len(subset),
            "hit_rate": round(hit_rate, 4),
            "avg_confidence": round(avg_confidence, 4),
            "calibration_error": round(avg_confidence - hit_rate, 4),
        })
    return rows


def run_phase2(data_dir: Path, seed: int, pre_registration_commit: str) -> dict[str, Any]:
    instruments = load_real_instruments(data_dir)
    all_records = []
    cells = []
    instrument_calibration = {}

    for instrument, df in instruments.items():
        dates = sorted(pd.to_datetime(df["Date"]).tolist())
        records = build_records(instrument, df)
        all_records.extend(records)
        instrument_calibration[instrument] = calibration_summary(records)
        for window_name, window_dates in window_definitions(dates).items():
            summary = simulate_window(records, window_dates, seed)
            days = summary["B_original"]["days"]
            if days < MIN_ELIGIBLE_DAYS:
                continue
            b_return = summary["B_original"]["return_pct"]
            p_return = summary["P_random"]["return_pct"]
            candidate_return = summary["C_phase1_recency_sigmoid"]["return_pct"]
            cells.append({
                "instrument": instrument,
                "window": window_name,
                "days": days,
                "A_equal_return_pct": summary["A_equal"]["return_pct"],
                "B_original_return_pct": b_return,
                "P_random_return_pct": p_return,
                "C_phase1_recency_sigmoid_return_pct": candidate_return,
                "B_minus_P_pct": round(b_return - p_return, 4),
                "C_minus_P_pct": round(candidate_return - p_return, 4),
                "B_beats_P": b_return > p_return,
                "C_beats_P": candidate_return > p_return,
                "B_sharpe": summary["B_original"]["sharpe"],
                "P_sharpe": summary["P_random"]["sharpe"],
            })

    b_diffs = [cell["B_minus_P_pct"] for cell in cells]
    c_diffs = [cell["C_minus_P_pct"] for cell in cells]
    aggregate = {
        "eligible_cells": len(cells),
        "B_beats_P_cells": sum(1 for cell in cells if cell["B_beats_P"]),
        "B_beats_P_share": round(sum(1 for cell in cells if cell["B_beats_P"]) / len(cells), 4) if cells else 0.0,
        "B_minus_P_median_pct": round(float(np.median(b_diffs)), 4) if b_diffs else 0.0,
        "B_minus_P_mean_pct": round(float(np.mean(b_diffs)), 4) if b_diffs else 0.0,
        "C_beats_P_cells": sum(1 for cell in cells if cell["C_beats_P"]),
        "C_beats_P_share": round(sum(1 for cell in cells if cell["C_beats_P"]) / len(cells), 4) if cells else 0.0,
        "C_minus_P_median_pct": round(float(np.median(c_diffs)), 4) if c_diffs else 0.0,
        "C_minus_P_mean_pct": round(float(np.mean(c_diffs)), 4) if c_diffs else 0.0,
    }

    return {
        "timestamp": datetime.now().isoformat(),
        "pre_registration_commit_hash": pre_registration_commit,
        "code_commit_hash": git_commit_hash(),
        "data_dir": str(data_dir),
        "rng_seed": seed,
        "scope_limitations": [
            "No frozen 2020-2024 real data present; older-window tests not run.",
            "No frozen options, crypto, or commodities data present; alternative-asset tests not run.",
            "No 1,500+ trading-day frozen sample present; longer-sample test not run.",
        ],
        "aggregate": aggregate,
        "cells": cells,
        "instrument_calibration": instrument_calibration,
        "overall_calibration": calibration_summary(all_records),
    }


def write_report(output_dir: Path, results: dict[str, Any]) -> None:
    aggregate = results["aggregate"]
    verdict = (
        "The STOP 2 null generalizes across the currently frozen NSE spot/large-cap set."
        if aggregate["B_beats_P_share"] <= 0.6 or aggregate["B_minus_P_median_pct"] <= 0
        else "Original trust-weighting produced a Phase 2 candidate signal that requires older-window retesting."
    )
    lines = [
        "# NSE Phase 2 Extended Market Results",
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
        "## Scope Limitations",
        "",
    ]
    for item in results["scope_limitations"]:
        lines.append(f"- {item}")

    lines.extend([
        "",
        "## Aggregate",
        "",
        f"- Eligible market-window cells: `{aggregate['eligible_cells']}`",
        f"- Original B beats P: `{aggregate['B_beats_P_cells']}` cells (`{aggregate['B_beats_P_share']:.1%}`)",
        f"- Median B-P return: `{aggregate['B_minus_P_median_pct']:.4f}%`",
        f"- Phase 1 candidate beats P: `{aggregate['C_beats_P_cells']}` cells (`{aggregate['C_beats_P_share']:.1%}`)",
        f"- Median candidate-P return: `{aggregate['C_minus_P_median_pct']:.4f}%`",
        "",
        "## Market-Window Cells",
        "",
        "| Instrument | Window | Days | B-P | Candidate-P | B Beats P |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for cell in results["cells"]:
        lines.append(
            f"| {cell['instrument']} | {cell['window']} | {cell['days']} | "
            f"{cell['B_minus_P_pct']:.4f}% | {cell['C_minus_P_pct']:.4f}% | {cell['B_beats_P']} |"
        )

    lines.extend([
        "",
        "## Overall Calibration",
        "",
        "| Agent | Predictions | Hit Rate | Avg Confidence | Calibration Error |",
        "|---|---:|---:|---:|---:|",
    ])
    for agent, row in results["overall_calibration"].items():
        lines.append(
            f"| {agent} | {row['predictions']} | {row['hit_rate']:.1%} | "
            f"{row['avg_confidence']:.1%} | {row['calibration_error']:.1%} |"
        )

    lines.extend([
        "",
        "Calibration curves by instrument and agent are in `phase2_extended_market_results.json`.",
        "",
    ])
    (output_dir / "PHASE2_EXTENDED_MARKET_RESULTS.md").write_text("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("evals/experiments/nse_data_frozen"))
    parser.add_argument("--output-dir", type=Path, default=Path("evals/experiments/nse_phase2_extended_market_results"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--pre-registration-commit", default=DEFAULT_PREREGISTRATION_COMMIT)
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = run_phase2(args.data_dir, args.seed, args.pre_registration_commit)
    with open(args.output_dir / "phase2_extended_market_results.json", "w") as f:
        json.dump(results, f, indent=2)
    pd.DataFrame(results["cells"]).to_csv(args.output_dir / "phase2_market_window_cells.csv", index=False)
    write_report(args.output_dir, results)
    print(f"Wrote Phase 2 results to {args.output_dir}")
    print(f"Pre-registration commit hash: {results['pre_registration_commit_hash']}")
    print(f"Executable code commit hash: {results['code_commit_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
