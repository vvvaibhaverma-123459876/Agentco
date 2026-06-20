#!/usr/bin/env python3
"""NSE Three-Arm Walk-Forward Engine (STOP 2).

Runs Arm A (equal), B (trust), P (random-placebo) in parallel on frozen real NSE data.
Pre-registered hypothesis locked before this runs.

Headline metric: B vs P (trust vs random weighting)
Null interpretation: locked (cannot be reinterpreted after results)
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np

try:
    import yfinance as yf
except ImportError:
    yf = None


def load_real_data(dataset_dir: Path) -> dict[str, pd.DataFrame]:
    """Load frozen real NSE data."""
    data = {}
    for csv_file in sorted(dataset_dir.glob("*_REAL.csv")):
        instrument_name = csv_file.stem.replace("_REAL", "").replace("_", " ").title()
        df = pd.read_csv(csv_file)
        df["Date"] = pd.to_datetime(df["Date"])
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")
        df = df[["Date", "Close", "Volume"]].sort_values("Date").reset_index(drop=True)
        data[instrument_name] = df

    return data


def get_data_up_to(
    data: dict[str, pd.DataFrame],
    cutoff_date: datetime | str,
) -> dict[str, pd.DataFrame]:
    """Get data strictly before cutoff_date (lookahead protection)."""
    if isinstance(cutoff_date, str):
        cutoff_date = pd.to_datetime(cutoff_date)

    result = {}
    for instrument_name, df in data.items():
        visible = df[pd.to_datetime(df["Date"]) < cutoff_date].copy()
        result[instrument_name] = visible

    return result


class TechnicalAgent:
    """RSI + MACD technical analysis agent."""

    def forecast(self, data: dict[str, pd.DataFrame], prediction_date: datetime) -> dict[str, Any]:
        """Generate directional forecast using technical indicators."""
        # Ensure data is strictly before prediction_date
        assert all(data[name]["Date"].max() < prediction_date for name in data if len(data[name]) > 0), \
            "LOOKAHEAD DETECTED in Technical agent"

        instrument = [k for k in data.keys() if "nifty" in k.lower() and "bank" not in k.lower()][0] if data else "NIFTY 50"
        if len(data.get(instrument, pd.DataFrame())) < 14:
            return {"prediction": "neutral", "confidence": 0.5}

        closes = data[instrument]["Close"].values
        high = data[instrument]["Close"].max()
        low = data[instrument]["Close"].min()

        # RSI(14)
        deltas = np.diff(closes[-15:])
        seed = abs(deltas[:1]).sum()
        up = seed if deltas[0] > 0 else 0
        down = seed if deltas[0] < 0 else -deltas[0]

        for delta in deltas[1:]:
            up = up * 13/14 + max(delta, 0) / 14
            down = down * 13/14 - min(delta, 0) / 14

        rs = up / max(down, 0.0001)
        rsi = 100.0 - 100.0 / (1.0 + rs)

        # MACD (simplified)
        ema12 = closes[-12:].mean()
        ema26 = closes[-26:].mean() if len(closes) >= 26 else ema12
        macd = ema12 - ema26
        signal = (closes[-9:].mean() if len(closes) >= 9 else closes.mean())
        histogram = macd - signal

        # Signals
        rsi_signal = (1.0 if rsi < 30 else (-1.0 if rsi > 70 else 0.0))
        macd_signal = (1.0 if histogram > 0 else -1.0)

        combined = rsi_signal + macd_signal
        prediction = "up" if combined > 0 else ("down" if combined < 0 else "neutral")
        confidence = min(0.75, 0.5 + abs(combined) * 0.15)

        return {"prediction": prediction, "confidence": confidence}


class RegimeAgent:
    """Trend + volatility regime classification agent."""

    def forecast(self, data: dict[str, pd.DataFrame], prediction_date: datetime) -> dict[str, Any]:
        """Generate directional forecast based on market regime."""
        assert all(data[name]["Date"].max() < prediction_date for name in data if len(data[name]) > 0), \
            "LOOKAHEAD DETECTED in Regime agent"

        instrument = [k for k in data.keys() if "nifty" in k.lower() and "bank" not in k.lower()][0] if data else "NIFTY 50"
        if len(data.get(instrument, pd.DataFrame())) < 20:
            return {"prediction": "neutral", "confidence": 0.5}

        closes = data[instrument]["Close"].values[-20:]
        returns = np.diff(np.log(closes))

        # Trend
        sma20 = closes.mean()
        current_price = closes[-1]
        trend = 1.0 if current_price > sma20 else -1.0

        # Volatility
        realized_vol = np.std(returns)
        vol_regime = "low" if realized_vol < 0.015 else ("high" if realized_vol > 0.025 else "normal")

        # Prediction
        confidence = 0.5
        prediction = "neutral"

        if vol_regime == "low":
            prediction = "up" if trend > 0 else "down"
            confidence = 0.70
        elif vol_regime == "high":
            confidence = 0.45  # Uncertain in high vol
        else:
            prediction = "up" if trend > 0 else "down"
            confidence = 0.60

        return {"prediction": prediction, "confidence": confidence}


class MeanReversionAgent:
    """Mean reversion agent (price vs moving average)."""

    def forecast(self, data: dict[str, pd.DataFrame], prediction_date: datetime) -> dict[str, Any]:
        """Generate directional forecast based on mean reversion signal."""
        assert all(data[name]["Date"].max() < prediction_date for name in data if len(data[name]) > 0), \
            "LOOKAHEAD DETECTED in MeanReversion agent"

        instrument = [k for k in data.keys() if "nifty" in k.lower() and "bank" not in k.lower()][0] if data else "NIFTY 50"
        if len(data.get(instrument, pd.DataFrame())) < 50:
            return {"prediction": "neutral", "confidence": 0.5}

        closes = data[instrument]["Close"].values
        ma50 = closes[-50:].mean()
        current = closes[-1]
        distance_pct = abs(current - ma50) / ma50

        if current > ma50:
            prediction = "down"  # Expect reversion downward
            confidence = min(0.75, 0.5 + distance_pct * 5.0)
        else:
            prediction = "up"  # Expect reversion upward
            confidence = min(0.75, 0.5 + distance_pct * 5.0)

        return {"prediction": prediction, "confidence": confidence}


def compute_trust_score(resolved_predictions: list[dict]) -> float:
    """Compute trust from past-resolved predictions only."""
    if len(resolved_predictions) == 0:
        return 0.5

    hits = sum(1 for p in resolved_predictions if p.get("hit", False))
    hit_rate = hits / len(resolved_predictions)

    avg_confidence = statistics.mean(p["confidence"] for p in resolved_predictions)

    # Corrected penalty function (no cliff)
    if avg_confidence <= hit_rate:
        calibration_error = hit_rate - avg_confidence
        trust = hit_rate + 0.05 * calibration_error
    else:
        calibration_error = avg_confidence - hit_rate
        trust = hit_rate - 0.1 * calibration_error

    return max(0.0, min(1.0, trust))


def size_position(
    arm_type: str,
    agent_predictions: dict[str, dict],
    trust_scores: dict[str, float],
    rng: np.random.RandomState,
    capital: float = 1_000_000,
) -> float:
    """Size paper position for one day."""
    signals = []
    weights = []

    for agent_name, pred in agent_predictions.items():
        if pred["prediction"] == "up":
            signal = pred["confidence"]
        elif pred["prediction"] == "down":
            signal = -pred["confidence"]
        else:
            signal = 0.0

        signals.append(signal)

        if arm_type == "A":  # Equal-weighted
            weights.append(1.0)
        elif arm_type == "B":  # Trust-weighted
            trust = trust_scores.get(agent_name, 0.5)
            weights.append(trust)
        elif arm_type == "P":  # Random-placebo
            random_weight = rng.uniform(0.0, 1.0)
            weights.append(random_weight)

    if not signals or not weights:
        return 0.0

    # Weighted average signal
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0

    weighted_signal = sum(s * w for s, w in zip(signals, weights)) / total_weight

    # Position sizing: ±5% per ±1.0 signal
    position_size = capital * weighted_signal * 0.05
    position_size = max(-0.05 * capital, min(0.05 * capital, position_size))

    return position_size


def run_three_arm_walkforward(
    real_data: dict[str, pd.DataFrame],
    output_dir: Path,
) -> dict[str, Any]:
    """Run full three-arm walk-forward on frozen real NSE data."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize agents
    agents = {
        "Technical": TechnicalAgent(),
        "Regime": RegimeAgent(),
        "MeanReversion": MeanReversionAgent(),
    }

    # Initialize tracking
    results = {
        "A": {"daily_pnl": [], "positions": [], "cash": []},
        "B": {"daily_pnl": [], "positions": [], "cash": []},
        "P": {"daily_pnl": [], "positions": [], "cash": []},
    }

    prediction_ledger = []
    trust_history = {"A": defaultdict(lambda: defaultdict(float)), "B": defaultdict(lambda: defaultdict(float)),
                     "P": defaultdict(lambda: defaultdict(float))}

    # Get unique trading dates (sorted)
    all_dates = set()
    for df in real_data.values():
        all_dates.update(pd.to_datetime(df["Date"]))
    trading_dates = sorted(list(all_dates))

    print(f"\nWalk-forward: {len(trading_dates)} trading days")
    print(f"Date range: {trading_dates[0].date()} to {trading_dates[-1].date()}\n")

    # Initial state
    capital = 1_000_000
    # Find NIFTY 50 by fuzzy name match
    nifty_key = [k for k in real_data.keys() if "nifty" in k.lower() and "bank" not in k.lower()][0]
    rng = np.random.RandomState(42)  # Fixed seed for reproducibility

    # Walk forward
    for i, current_date in enumerate(trading_dates):
        if i % 50 == 0:
            print(f"  Day {i+1}/{len(trading_dates)}: {current_date.date()}")

        # Get data strictly before current_date
        visible_data = get_data_up_to(real_data, current_date)

        # Agents generate predictions
        agent_predictions = {}
        for agent_name, agent in agents.items():
            try:
                pred = agent.forecast(visible_data, current_date)
                agent_predictions[agent_name] = pred
            except AssertionError as e:
                print(f"ERROR: {e}")
                return {}

        # Register predictions for resolution tomorrow
        next_date_idx = i + 1
        if next_date_idx < len(trading_dates):
            next_date = trading_dates[next_date_idx]
            for agent_name, pred in agent_predictions.items():
                prediction_ledger.append({
                    "agent": agent_name,
                    "prediction_date": current_date,
                    "resolution_date": next_date,
                    "prediction": pred["prediction"],
                    "confidence": pred["confidence"],
                    "resolved": False,
                    "actual_close": None,
                    "hit": None,
                })

        # Resolve predictions from yesterday (if any)
        if i > 0:
            actual_close = real_data[nifty_key].loc[real_data[nifty_key]["Date"] == current_date, "Close"]
            if len(actual_close) > 0:
                actual_close_val = actual_close.iloc[0]

                for pred in prediction_ledger:
                    if pred["resolution_date"] == current_date and not pred["resolved"]:
                        pred["resolved"] = True
                        pred["actual_close"] = actual_close_val

                        # Score: did prediction match actual direction?
                        if i > 1:
                            prior_close = real_data[nifty_key].loc[real_data[nifty_key]["Date"] == pred["prediction_date"], "Close"]
                            if len(prior_close) > 0:
                                direction = "up" if actual_close_val > prior_close.iloc[0] else ("down" if actual_close_val < prior_close.iloc[0] else "flat")
                                pred["hit"] = (direction == pred["prediction"]) or (direction == "flat" and pred["prediction"] == "neutral")

                        # Update trust scores for this agent
                        resolved_for_agent = [p for p in prediction_ledger if p["agent"] == pred["agent"] and p["resolved"]]
                        trust = compute_trust_score(resolved_for_agent)

                        # Update for all arms (they use same predictions/trust)
                        for arm in ["A", "B", "P"]:
                            trust_history[arm][current_date][pred["agent"]] = trust

        # Size positions for today (for tomorrow's resolution)
        if i < len(trading_dates) - 1:
            for arm in ["A", "B", "P"]:
                # Get current trust scores for this arm
                arm_trust = trust_history[arm][current_date]

                # Size position
                position = size_position(arm, agent_predictions, arm_trust, rng, capital)
                results[arm]["positions"].append(position)

                # Compute P&L (for next day's close)
                # For simplicity: assume position is held overnight
                # P&L = position * (next_close - current_close) / current_close
                if i < len(trading_dates) - 1:
                    current_close = real_data[nifty_key].loc[real_data[nifty_key]["Date"] == current_date, "Close"]
                    next_close_date = trading_dates[i + 1]
                    next_close = real_data[nifty_key].loc[real_data[nifty_key]["Date"] == next_close_date, "Close"]

                    if len(current_close) > 0 and len(next_close) > 0:
                        close_change = (next_close.iloc[0] - current_close.iloc[0]) / current_close.iloc[0]
                        daily_pnl = position * close_change
                        results[arm]["daily_pnl"].append(daily_pnl)

                        # Update cash
                        if len(results[arm]["cash"]) > 0:
                            new_cash = results[arm]["cash"][-1] + daily_pnl
                        else:
                            new_cash = capital + daily_pnl

                        results[arm]["cash"].append(new_cash)

    # Summary
    print(f"\nWalk-forward complete. {len(prediction_ledger)} predictions registered.")

    summary = {
        "timestamp": datetime.now().isoformat(),
        "window": f"{trading_dates[0].date()} to {trading_dates[-1].date()}",
        "trading_days": len(trading_dates),
        "predictions_registered": len(prediction_ledger),
        "arms": {},
    }

    for arm in ["A", "B", "P"]:
        if results[arm]["cash"]:
            final_cash = results[arm]["cash"][-1]
            total_return_pct = 100.0 * (final_cash - capital) / capital
            daily_returns = [r / capital for r in results[arm]["daily_pnl"]]
            avg_daily = statistics.mean(daily_returns) if daily_returns else 0
            std_daily = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0
            sharpe = avg_daily / max(std_daily, 0.0001)

            summary["arms"][arm] = {
                "initial_capital": capital,
                "final_cash": round(final_cash, 2),
                "total_return_pct": round(total_return_pct, 2),
                "avg_daily_return": round(avg_daily * 100, 4),
                "daily_std_dev": round(std_daily * 100, 4),
                "sharpe_ratio": round(sharpe, 4),
                "positive_days": sum(1 for r in results[arm]["daily_pnl"] if r > 0),
                "total_days": len(results[arm]["daily_pnl"]),
            }

    # Headline: B vs P
    if "B" in summary["arms"] and "P" in summary["arms"]:
        b_return = summary["arms"]["B"]["final_cash"] - capital
        p_return = summary["arms"]["P"]["final_cash"] - capital
        b_vs_p = b_return - p_return
        b_vs_p_pct = 100.0 * b_vs_p / capital if capital > 0 else 0

        summary["headline_b_vs_p"] = {
            "b_minus_p_dollars": round(b_vs_p, 2),
            "b_minus_p_pct": round(b_vs_p_pct, 2),
            "interpretation": "B (trust) beats P (random)" if b_vs_p > 0 else ("B (trust) loses to P (random)" if b_vs_p < 0 else "B ≈ P (no edge detected)"),
        }

    return summary, results, prediction_ledger


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("evals/experiments/nse_data_frozen"))
    parser.add_argument("--output-dir", type=Path, default=Path("evals/experiments/nse_walkforward_results"))

    args = parser.parse_args(argv)

    print("\n" + "="*70)
    print("STOP 2: THREE-ARM WALK-FORWARD ON REAL NSE DATA")
    print("="*70)

    # Load real data
    print("\n[PHASE 1] Loading frozen real NSE data...")
    real_data = load_real_data(args.data_dir)
    print(f"  Loaded {len(real_data)} instruments")
    for name, df in real_data.items():
        print(f"    {name:15s}: {len(df):4d} days")

    # Run walk-forward
    print("\n[PHASE 2] Running three-arm walk-forward...")
    summary, results, ledger = run_three_arm_walkforward(real_data, args.output_dir)

    if not summary:
        print("ERROR: Walk-forward failed")
        return 1

    # Save results
    summary_path = args.output_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n✓ Results saved to {summary_path}")

    # Save prediction ledger for calibration analysis
    if ledger:
        ledger_path = args.output_dir / "prediction_ledger.csv"
        ledger_df = pd.DataFrame(ledger)
        # Convert datetime objects to strings for CSV
        if "prediction_date" in ledger_df.columns:
            ledger_df["prediction_date"] = ledger_df["prediction_date"].astype(str)
        if "resolution_date" in ledger_df.columns:
            ledger_df["resolution_date"] = ledger_df["resolution_date"].astype(str)
        ledger_df.to_csv(ledger_path, index=False)
        print(f"✓ Prediction ledger saved to {ledger_path}")

    # Print summary
    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)
    print(f"\nHEADLINE (B vs P):")
    if "headline_b_vs_p" in summary:
        hl = summary["headline_b_vs_p"]
        print(f"  B (trust) vs P (random): ${hl['b_minus_p_dollars']:,.0f} ({hl['b_minus_p_pct']:.2f}%)")
        print(f"  Interpretation: {hl['interpretation']}")

    print(f"\nAll Arms:")
    for arm in ["A", "B", "P"]:
        if arm in summary["arms"]:
            s = summary["arms"][arm]
            print(f"\n  Arm {arm}:")
            print(f"    Final cash: ${s['final_cash']:,.0f}")
            print(f"    Total return: {s['total_return_pct']:.2f}%")
            print(f"    Sharpe ratio: {s['sharpe_ratio']:.4f}")
            print(f"    Win days: {s['positive_days']}/{s['total_days']}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
