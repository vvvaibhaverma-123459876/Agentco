#!/usr/bin/env python3
"""Canonical paper-only NSE trust-weighting fair test.

This implements the pre-registered two-arm test in
evals/experiments/nse_trust_weighting_hypothesis.md.
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PREREGISTRATION_COMMIT = "5e6491a49e80fb931a5faa9e42392fd37b5cf6c6"
TEST_START = pd.Timestamp("2025-12-12")
TEST_END = pd.Timestamp("2026-06-19")
INITIAL_CAPITAL = 1_000_000.0
MAX_GROSS_SLEEVE = 0.05
PLACEBO_SEED = 42
INSTRUMENTS = ["NIFTY 50", "BANK NIFTY", "RELIANCE", "HDFCBANK", "TCS", "INFY", "ICICIBANK"]
STOCKS = {"RELIANCE", "HDFCBANK", "TCS", "INFY", "ICICIBANK"}
AGENTS = ["TechnicalAgent", "RegimeAgent", "MeanReversionAgent"]


@dataclass(frozen=True)
class VisibleMarketData:
    instrument: str
    prediction_date: pd.Timestamp
    frame: pd.DataFrame

    def __post_init__(self) -> None:
        if len(self.frame) > 0:
            max_date = pd.to_datetime(self.frame["Date"]).max()
            if max_date >= self.prediction_date:
                raise AssertionError(
                    f"LOOKAHEAD DETECTED for {self.instrument}: {max_date.date()} >= {self.prediction_date.date()}"
                )


def git_commit_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def load_frozen_real_data(data_dir: Path) -> dict[str, pd.DataFrame]:
    data = {}
    for csv_path in sorted(data_dir.glob("*_REAL.csv")):
        name = csv_path.stem.replace("_REAL", "").replace("_", " ").upper()
        df = pd.read_csv(csv_path)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")
        invalid_rows = int((df["Date"].isna() | df["Close"].isna()).sum())
        df = df[["Date", "Close", "Volume"]].dropna(subset=["Date", "Close"])
        df = df.sort_values("Date").drop_duplicates(subset=["Date"], keep="last").reset_index(drop=True)
        df.attrs["invalid_rows_dropped"] = invalid_rows
        data[name] = df
    return {name: data[name] for name in INSTRUMENTS if name in data}


def visible_data(df: pd.DataFrame, instrument: str, prediction_date: pd.Timestamp) -> VisibleMarketData:
    visible = df[df["Date"] < prediction_date].copy()
    return VisibleMarketData(instrument=instrument, prediction_date=prediction_date, frame=visible)


def close_on(df: pd.DataFrame, date: pd.Timestamp) -> float | None:
    rows = df[df["Date"] == date]
    if len(rows) == 0:
        return None
    return float(rows.iloc[0]["Close"])


def next_trading_date(df: pd.DataFrame, prediction_date: pd.Timestamp, offset: int = 1) -> pd.Timestamp | None:
    future = df[df["Date"] > prediction_date]["Date"].tolist()
    if len(future) < offset:
        return None
    return pd.Timestamp(future[offset - 1])


def technical_forecast(visible: VisibleMarketData) -> dict[str, Any]:
    frame = visible.frame
    if len(frame) < 26:
        return {"prediction": "neutral", "confidence": 0.5}
    closes = frame["Close"].astype(float).to_numpy()
    rsi = compute_rsi(closes[-15:])
    ema12 = np.mean(closes[-12:])
    ema26 = np.mean(closes[-26:])
    macd_signal = 1.0 if ema12 > ema26 else -1.0
    rsi_signal = 1.0 if rsi < 30 else (-1.0 if rsi > 70 else 0.0)
    combined = rsi_signal + macd_signal
    prediction = "up" if combined > 0 else ("down" if combined < 0 else "neutral")
    confidence = min(0.75, 0.5 + abs(combined) * 0.125)
    return {"prediction": prediction, "confidence": confidence}


def regime_forecast(visible: VisibleMarketData) -> dict[str, Any]:
    frame = visible.frame
    if len(frame) < 20:
        return {"prediction": "neutral", "confidence": 0.5}
    closes = frame["Close"].astype(float).to_numpy()
    recent = closes[-20:]
    returns = np.diff(np.log(recent))
    trend_up = recent[-1] > np.mean(recent)
    vol = float(np.std(returns))
    if vol > 0.025:
        return {"prediction": "neutral", "confidence": 0.45}
    return {"prediction": "up" if trend_up else "down", "confidence": 0.65 if vol < 0.015 else 0.58}


def mean_reversion_forecast(visible: VisibleMarketData) -> dict[str, Any]:
    frame = visible.frame
    if len(frame) < 50:
        return {"prediction": "neutral", "confidence": 0.5}
    closes = frame["Close"].astype(float).to_numpy()
    ma50 = float(np.mean(closes[-50:]))
    current = float(closes[-1])
    distance = abs(current / ma50 - 1.0)
    return {"prediction": "down" if current > ma50 else "up", "confidence": min(0.75, 0.5 + distance * 4.0)}


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


def agent_forecast(agent: str, visible: VisibleMarketData) -> dict[str, Any]:
    if agent == "TechnicalAgent":
        return technical_forecast(visible)
    if agent == "RegimeAgent":
        return regime_forecast(visible)
    if agent == "MeanReversionAgent":
        return mean_reversion_forecast(visible)
    raise ValueError(f"unknown agent: {agent}")


def trust_score(history: list[dict[str, Any]]) -> float:
    if not history:
        return 0.5
    hit_rate = sum(1 for row in history if row["hit"]) / len(history)
    avg_confidence = statistics.mean(row["confidence"] for row in history)
    if avg_confidence <= hit_rate:
        trust = hit_rate + 0.05 * (hit_rate - avg_confidence)
    else:
        trust = hit_rate - 0.1 * (avg_confidence - hit_rate)
    return max(0.0, min(1.0, trust))


def prediction_signal(prediction: str, confidence: float) -> float:
    if prediction == "up":
        return confidence
    if prediction == "down":
        return -confidence
    return 0.0


def calibration_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    output = {}
    for agent in sorted({row["agent"] for row in records}):
        subset = [row for row in records if row["agent"] == agent]
        hit_rate = sum(1 for row in subset if row["hit"]) / len(subset)
        avg_confidence = statistics.mean(row["confidence"] for row in subset)
        output[agent] = {
            "predictions": len(subset),
            "hit_rate": round(hit_rate, 4),
            "avg_confidence": round(avg_confidence, 4),
            "calibration_error": round(avg_confidence - hit_rate, 4),
            "confidence_bins": confidence_bins(subset),
        }
    return output


def confidence_bins(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        confidence = row["confidence"]
        if confidence < 0.55:
            bucket = "0.45-0.55"
        elif confidence < 0.65:
            bucket = "0.55-0.65"
        elif confidence < 0.75:
            bucket = "0.65-0.75"
        else:
            bucket = "0.75-1.00"
        grouped[bucket].append(row)
    rows = []
    for bucket, subset in sorted(grouped.items()):
        hit_rate = sum(1 for row in subset if row["hit"]) / len(subset)
        avg_confidence = statistics.mean(row["confidence"] for row in subset)
        rows.append({
            "bucket": bucket,
            "n": len(subset),
            "hit_rate": round(hit_rate, 4),
            "avg_confidence": round(avg_confidence, 4),
            "calibration_error": round(avg_confidence - hit_rate, 4),
        })
    return rows


def summarize_returns(daily_pnl: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    pnl = [row[f"{arm}_pnl"] for row in daily_pnl]
    daily_returns = [value / INITIAL_CAPITAL for value in pnl]
    std = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0.0
    sharpe = statistics.mean(daily_returns) / std if std > 0 else 0.0
    return {
        "total_pnl": round(sum(pnl), 4),
        "total_return_pct": round(100.0 * sum(pnl) / INITIAL_CAPITAL, 4),
        "sharpe_style_ratio": round(sharpe, 4),
        "positive_days": sum(1 for value in pnl if value > 0),
        "total_days": len(pnl),
    }


def run_walk_forward(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
    nifty_dates = data["NIFTY 50"]["Date"]
    trading_dates = [pd.Timestamp(date) for date in nifty_dates[(nifty_dates >= TEST_START) & (nifty_dates <= TEST_END)]]

    ledger: list[dict[str, Any]] = []
    resolved_history: dict[str, list[dict[str, Any]]] = defaultdict(list)
    daily_pnl = []
    position_ledger = []
    rng = np.random.RandomState(PLACEBO_SEED)

    for prediction_date in trading_dates:
        for row in ledger:
            if not row["resolved"] and pd.Timestamp(row["resolution_date"]) <= prediction_date:
                row["resolved"] = True
                row["hit"] = resolve_prediction(row, data)
                if row["hit"] is not None:
                    resolved_history[row["agent"]].append(row)

        day_a_pnl = 0.0
        day_b_pnl = 0.0
        day_p_pnl = 0.0
        active_instruments = [name for name, df in data.items() if close_on(df, prediction_date) is not None]
        sleeve_capital = INITIAL_CAPITAL / len(active_instruments)

        for instrument in active_instruments:
            df = data[instrument]
            next_date = next_trading_date(df, prediction_date, 1)
            if next_date is None:
                continue
            current_close = close_on(df, prediction_date)
            next_close = close_on(df, next_date)
            if current_close is None or next_close is None:
                continue

            visible = visible_data(df, instrument, prediction_date)
            directional_predictions = []
            for agent in AGENTS:
                forecast = agent_forecast(agent, visible)
                directional_predictions.append({
                    "agent": agent,
                    "prediction": forecast["prediction"],
                    "confidence": forecast["confidence"],
                })
                ledger.append(register_directional(agent, instrument, prediction_date, next_date, forecast))
                ledger.extend(register_secondary_predictions(agent, instrument, prediction_date, forecast, visible, data))

            signals = {
                row["agent"]: prediction_signal(row["prediction"], row["confidence"])
                for row in directional_predictions
            }
            equal_weights = {agent: 1.0 for agent in signals}
            trust_weights = {agent: trust_score(resolved_history[agent]) for agent in signals}
            placebo_weights = {agent: float(rng.uniform(0.0, 1.0)) for agent in signals}
            a_signal = weighted_signal(signals, equal_weights)
            b_signal = weighted_signal(signals, trust_weights)
            p_signal = weighted_signal(signals, placebo_weights)
            a_position = max(-MAX_GROSS_SLEEVE * sleeve_capital, min(MAX_GROSS_SLEEVE * sleeve_capital, a_signal * MAX_GROSS_SLEEVE * sleeve_capital))
            b_position = max(-MAX_GROSS_SLEEVE * sleeve_capital, min(MAX_GROSS_SLEEVE * sleeve_capital, b_signal * MAX_GROSS_SLEEVE * sleeve_capital))
            p_position = max(-MAX_GROSS_SLEEVE * sleeve_capital, min(MAX_GROSS_SLEEVE * sleeve_capital, p_signal * MAX_GROSS_SLEEVE * sleeve_capital))
            close_return = (next_close - current_close) / current_close
            a_pnl = a_position * close_return
            b_pnl = b_position * close_return
            p_pnl = p_position * close_return
            day_a_pnl += a_pnl
            day_b_pnl += b_pnl
            day_p_pnl += p_pnl
            position_ledger.append({
                "date": str(prediction_date.date()),
                "instrument": instrument,
                "next_trading_date": str(next_date.date()),
                "arm_a_position": round(a_position, 6),
                "arm_b_position": round(b_position, 6),
                "arm_p_position": round(p_position, 6),
                "arm_a_pnl": round(a_pnl, 6),
                "arm_b_pnl": round(b_pnl, 6),
                "arm_p_pnl": round(p_pnl, 6),
                "trust_weights": {agent: round(trust_weights[agent], 6) for agent in trust_weights},
                "placebo_weights": {agent: round(placebo_weights[agent], 6) for agent in placebo_weights},
            })

        daily_pnl.append({
            "date": str(prediction_date.date()),
            "arm_a_pnl": round(day_a_pnl, 6),
            "arm_b_pnl": round(day_b_pnl, 6),
            "arm_p_pnl": round(day_p_pnl, 6),
            "arm_a_cash": round(INITIAL_CAPITAL + sum(row["arm_a_pnl"] for row in daily_pnl) + day_a_pnl, 6),
            "arm_b_cash": round(INITIAL_CAPITAL + sum(row["arm_b_pnl"] for row in daily_pnl) + day_b_pnl, 6),
            "arm_p_cash": round(INITIAL_CAPITAL + sum(row["arm_p_pnl"] for row in daily_pnl) + day_p_pnl, 6),
        })

    for row in ledger:
        if not row["resolved"]:
            row["resolved"] = True
            row["hit"] = resolve_prediction(row, data)

    resolved_records = [row for row in ledger if row.get("hit") is not None]
    arm_a = summarize_returns(daily_pnl, "arm_a")
    arm_b = summarize_returns(daily_pnl, "arm_b")
    arm_p = summarize_returns(daily_pnl, "arm_p")
    return {
        "summary": {
            "mode": "historical_backtest_paper_only",
            "pre_registration_commit_hash": PREREGISTRATION_COMMIT,
            "code_commit_hash": git_commit_hash(),
            "placebo_seed": PLACEBO_SEED,
            "test_start": str(TEST_START.date()),
            "test_end": str(TEST_END.date()),
            "trading_days": len(trading_dates),
            "initial_capital": INITIAL_CAPITAL,
            "arm_a_equal": arm_a,
            "arm_b_trust": arm_b,
            "arm_p_random_placebo": arm_p,
            "headline": {
                "b_minus_a_pnl": round(arm_b["total_pnl"] - arm_a["total_pnl"], 4),
                "b_minus_a_return_pct": round(arm_b["total_return_pct"] - arm_a["total_return_pct"], 4),
                "b_minus_a_sharpe": round(arm_b["sharpe_style_ratio"] - arm_a["sharpe_style_ratio"], 4),
                "b_minus_p_pnl": round(arm_b["total_pnl"] - arm_p["total_pnl"], 4),
                "b_minus_p_return_pct": round(arm_b["total_return_pct"] - arm_p["total_return_pct"], 4),
                "b_minus_p_sharpe": round(arm_b["sharpe_style_ratio"] - arm_p["sharpe_style_ratio"], 4),
                "hypothesis_result": "supported" if arm_b["sharpe_style_ratio"] > arm_a["sharpe_style_ratio"] else "falsified_for_this_window",
            },
            "prediction_counts": {
                "registered": len(ledger),
                "resolved_scored": len(resolved_records),
                "post_hoc_false": sum(1 for row in ledger if row["post_hoc"] is False),
            },
            "calibration": calibration_summary(resolved_records),
        },
        "prediction_ledger": ledger,
        "daily_pnl": daily_pnl,
        "position_ledger": position_ledger,
    }


def register_directional(
    agent: str,
    instrument: str,
    prediction_date: pd.Timestamp,
    resolution_date: pd.Timestamp,
    forecast: dict[str, Any],
) -> dict[str, Any]:
    return {
        "prediction_id": f"{prediction_date.date()}:{instrument}:{agent}:direction_next_session",
        "agent": agent,
        "instrument": instrument,
        "prediction_type": "direction_next_session",
        "prediction_date": prediction_date,
        "resolution_date": resolution_date,
        "claim": f"{instrument} closes higher on {resolution_date.date()} than on {prediction_date.date()}",
        "prediction": forecast["prediction"],
        "confidence": float(forecast["confidence"]),
        "resolution_rule": "raw Close(resolution_date) > raw Close(prediction_date)",
        "post_hoc": False,
        "resolved": False,
        "hit": None,
    }


def register_secondary_predictions(
    agent: str,
    instrument: str,
    prediction_date: pd.Timestamp,
    forecast: dict[str, Any],
    visible: VisibleMarketData,
    data: dict[str, pd.DataFrame],
) -> list[dict[str, Any]]:
    rows = []
    df = data[instrument]
    next_date = next_trading_date(df, prediction_date, 1)
    if next_date is not None and len(visible.frame) >= 20:
        threshold = float(visible.frame["Close"].tail(20).mean())
        threshold_prediction = "above" if forecast["prediction"] == "up" else "below_or_equal"
        rows.append({
            "prediction_id": f"{prediction_date.date()}:{instrument}:{agent}:threshold_next_session",
            "agent": agent,
            "instrument": instrument,
            "prediction_type": "threshold_next_session",
            "prediction_date": prediction_date,
            "resolution_date": next_date,
            "claim": f"{instrument} closes above visible 20-session MA {threshold:.4f} on {next_date.date()}",
            "prediction": threshold_prediction,
            "threshold": threshold,
            "confidence": float(forecast["confidence"]),
            "resolution_rule": "raw Close(resolution_date) > threshold computed before prediction_date",
            "post_hoc": False,
            "resolved": False,
            "hit": None,
        })

    if instrument in STOCKS and "NIFTY 50" in data:
        stock_resolution = next_trading_date(data[instrument], prediction_date, 5)
        nifty_resolution = next_trading_date(data["NIFTY 50"], prediction_date, 5)
        if stock_resolution is not None and nifty_resolution is not None:
            rows.append({
                "prediction_id": f"{prediction_date.date()}:{instrument}:{agent}:relative_5_session",
                "agent": agent,
                "instrument": instrument,
                "prediction_type": "relative_5_session",
                "prediction_date": prediction_date,
                "resolution_date": stock_resolution,
                "nifty_resolution_date": nifty_resolution,
                "claim": f"{instrument} outperforms NIFTY 50 over next 5 trading sessions",
                "prediction": "outperform" if forecast["prediction"] == "up" else "underperform_or_equal",
                "confidence": float(forecast["confidence"]),
                "resolution_rule": "stock 5-session raw-close return > NIFTY 50 5-session raw-close return",
                "post_hoc": False,
                "resolved": False,
                "hit": None,
            })
    return rows


def resolve_prediction(row: dict[str, Any], data: dict[str, pd.DataFrame]) -> bool | None:
    instrument = row["instrument"]
    df = data[instrument]
    prediction_date = pd.Timestamp(row["prediction_date"])
    resolution_date = pd.Timestamp(row["resolution_date"])
    prediction_close = close_on(df, prediction_date)
    resolution_close = close_on(df, resolution_date)
    if prediction_close is None or resolution_close is None:
        return None

    if row["prediction_type"] == "direction_next_session":
        actual = "up" if resolution_close > prediction_close else ("down" if resolution_close < prediction_close else "neutral")
        return actual == row["prediction"]
    if row["prediction_type"] == "threshold_next_session":
        actual = "above" if resolution_close > float(row["threshold"]) else "below_or_equal"
        return actual == row["prediction"]
    if row["prediction_type"] == "relative_5_session":
        nifty_prediction_close = close_on(data["NIFTY 50"], prediction_date)
        nifty_resolution_close = close_on(data["NIFTY 50"], pd.Timestamp(row["nifty_resolution_date"]))
        if nifty_prediction_close is None or nifty_resolution_close is None:
            return None
        stock_return = resolution_close / prediction_close - 1.0
        nifty_return = nifty_resolution_close / nifty_prediction_close - 1.0
        actual = "outperform" if stock_return > nifty_return else "underperform_or_equal"
        return actual == row["prediction"]
    raise ValueError(f"unknown prediction type: {row['prediction_type']}")


def weighted_signal(signals: dict[str, float], weights: dict[str, float]) -> float:
    total_weight = sum(weights.values())
    if total_weight == 0:
        return 0.0
    return sum(signals[agent] * weights[agent] for agent in signals) / total_weight


def write_data_source_doc(output_dir: Path, data: dict[str, pd.DataFrame]) -> None:
    rows = []
    for instrument, df in data.items():
        rows.append(
            f"| {instrument} | {len(df)} | {pd.to_datetime(df['Date']).min().date()} | "
            f"{pd.to_datetime(df['Date']).max().date()} | {df.attrs.get('invalid_rows_dropped', 0)} |"
        )
    text = "\n".join([
        "# Frozen NSE Dataset Source",
        "",
        "Source: yfinance NSE tickers, previously fetched into committed local CSV files.",
        "",
        "The canonical test uses raw `Close`, not adjusted close. Adjusted close can be retroactively rewritten after future splits/dividends, which is a lookahead vector for historical prediction tests.",
        "",
        "Known limitations: yfinance can differ from official NSE records; raw close is not a total-return series; this fixed index/large-cap universe does not prove behavior on illiquid, delisted, options, crypto, or commodities markets.",
        "",
        "| Instrument | Rows Used | First Date | Last Date | Invalid Rows Dropped |",
        "|---|---:|---:|---:|---:|",
        *rows,
        "",
    ])
    (output_dir / "FROZEN_NSE_DATA_SOURCE.md").write_text(text)


def write_report(output_dir: Path, results: dict[str, Any]) -> None:
    summary = results["summary"]
    headline = summary["headline"]
    verdict = (
        "Trust-weighting beat equal-weighting on the pre-registered Sharpe-style metric."
        if headline["hypothesis_result"] == "supported"
        else "Trust-weighting did not beat equal-weighting on the pre-registered Sharpe-style metric."
    )
    lines = [
        "# Canonical NSE Trust-Weighting Fair Test Results",
        "",
        f"**Date:** {datetime.now().date()}",
        f"**Mode:** `{summary['mode']}`",
        f"**Pre-registration commit hash:** `{summary['pre_registration_commit_hash']}`",
        f"**Executable code commit hash:** `{summary['code_commit_hash']}`",
        f"**Window:** `{summary['test_start']}` to `{summary['test_end']}`",
        "",
        "## Verdict",
        "",
        verdict,
        "",
        "This is paper only. There were no live orders, no broker connection, and no real capital. Because this canonical run has no slippage or transaction-cost model, even a positive result would overstate live tradability.",
        "",
        "## Arm Results",
        "",
        "| Arm | Total Return | Total P&L | Sharpe-Style Ratio | Positive Days |",
        "|---|---:|---:|---:|---:|",
        f"| A equal-weighted | {summary['arm_a_equal']['total_return_pct']:.4f}% | {summary['arm_a_equal']['total_pnl']:.2f} | {summary['arm_a_equal']['sharpe_style_ratio']:.4f} | {summary['arm_a_equal']['positive_days']}/{summary['arm_a_equal']['total_days']} |",
        f"| B trust-weighted | {summary['arm_b_trust']['total_return_pct']:.4f}% | {summary['arm_b_trust']['total_pnl']:.2f} | {summary['arm_b_trust']['sharpe_style_ratio']:.4f} | {summary['arm_b_trust']['positive_days']}/{summary['arm_b_trust']['total_days']} |",
        f"| P random-placebo | {summary['arm_p_random_placebo']['total_return_pct']:.4f}% | {summary['arm_p_random_placebo']['total_pnl']:.2f} | {summary['arm_p_random_placebo']['sharpe_style_ratio']:.4f} | {summary['arm_p_random_placebo']['positive_days']}/{summary['arm_p_random_placebo']['total_days']} |",
        "",
        "## Headline",
        "",
        f"- B minus A return: `{headline['b_minus_a_return_pct']:.4f}%`",
        f"- B minus A P&L: `{headline['b_minus_a_pnl']:.2f}`",
        f"- B minus A Sharpe-style ratio: `{headline['b_minus_a_sharpe']:.4f}`",
        f"- B minus P return: `{headline['b_minus_p_return_pct']:.4f}%`",
        f"- B minus P P&L: `{headline['b_minus_p_pnl']:.2f}`",
        f"- B minus P Sharpe-style ratio: `{headline['b_minus_p_sharpe']:.4f}`",
        f"- Pre-registered result: `{headline['hypothesis_result']}`",
        "",
        "## Prediction Ledger",
        "",
        f"- Registered predictions: `{summary['prediction_counts']['registered']}`",
        f"- Resolved/scored predictions: `{summary['prediction_counts']['resolved_scored']}`",
        f"- `post_hoc=False` predictions: `{summary['prediction_counts']['post_hoc_false']}`",
        "",
        "## Calibration",
        "",
        "| Agent | Predictions | Hit Rate | Avg Confidence | Calibration Error |",
        "|---|---:|---:|---:|---:|",
    ]
    for agent, row in summary["calibration"].items():
        lines.append(
            f"| {agent} | {row['predictions']} | {row['hit_rate']:.1%} | "
            f"{row['avg_confidence']:.1%} | {row['calibration_error']:.1%} |"
        )
    lines.extend([
        "",
        "## What This Proves",
        "",
        "- The frozen NSE market data can mechanically verify pre-registered claims without an LLM in the resolution path.",
        "- The implementation enforces strict past-only agent inputs and includes a passing lookahead regression test.",
        "- The reported verdict applies only to this frozen dataset, these deterministic agents, this paper sizing rule, and this test window.",
        "",
        "## What This Does Not Prove",
        "",
        "- It does not prove live profitability.",
        "- It does not prove the result generalizes to other markets, longer windows, options, crypto, commodities, or live execution.",
        "- It does not prove calibration-weighting is generally useful or useless; it tests this concrete implementation under this concrete protocol.",
        "",
    ])
    (output_dir / "CANONICAL_NSE_TRUST_WEIGHTING_RESULTS.md").write_text("\n".join(lines))


def serialize_ledger(rows: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for column in ["prediction_date", "resolution_date", "nifty_resolution_date"]:
        if column in df.columns:
            df[column] = df[column].astype(str)
    df = df.replace({"NaT": "", "nan": ""})
    return df


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("evals/experiments/nse_data_frozen"))
    parser.add_argument("--output-dir", type=Path, default=Path("evals/experiments/nse_canonical_trust_weighting_results"))
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = load_frozen_real_data(args.data_dir)
    results = run_walk_forward(data)
    with open(args.output_dir / "canonical_nse_trust_weighting_results.json", "w") as f:
        json.dump(results["summary"], f, indent=2)
    serialize_ledger(results["prediction_ledger"]).to_csv(args.output_dir / "prediction_ledger.csv", index=False)
    pd.DataFrame(results["daily_pnl"]).to_csv(args.output_dir / "daily_pnl.csv", index=False)
    pd.DataFrame(results["position_ledger"]).to_csv(args.output_dir / "position_ledger.csv", index=False)
    write_data_source_doc(args.output_dir, data)
    write_report(args.output_dir, results)
    print(f"Wrote canonical NSE results to {args.output_dir}")
    print(f"Pre-registration commit hash: {PREREGISTRATION_COMMIT}")
    print(f"Executable code commit hash: {results['summary']['code_commit_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
