#!/usr/bin/env python3
"""Three diagnostic tests to isolate what's actually driving the soft-weighting win.

Test 1: Hard curve (0-2x) WITH fixed penalty → isolates penalty fix value
Test 2: Soft curve (0.5-1.5x) WITH RANDOM weights → placebo test (critical)
Test 3: Soft curve (0.5-1.5x) WITH trust weights → baseline for comparison

Only if #2 (random) loses while #3 (trust) wins can we claim trust-weighting works.
If #2 (random) also wins ~18/25, the victory is "small deviations help" not "calibration works."
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any

import sys
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_b2b_saas_simulation import B2BSaaSOracle, B2BSaaSState, control_policy
from scripts.b2b_saas_agents import B2BSaaSAgents


def calculate_agent_trust_soft(forecast, actual, tolerance=0.10):
    """Fixed penalty function."""
    if actual is None:
        return 0.5, None

    error = abs(forecast - actual)
    error_pct = error / max(0.01, actual)
    hit = error_pct <= tolerance

    if error_pct <= tolerance:
        trust = 0.7 + (1.0 - error_pct / tolerance) * 0.3
    elif error_pct <= 0.20:
        trust = 0.7 - (error_pct - tolerance) / (0.20 - tolerance) * 0.2
    elif error_pct <= 0.30:
        trust = 0.5 - (error_pct - 0.20) / 0.10 * 0.2
    else:
        trust = max(0.0, 0.3 - (error_pct - 0.30) * 0.5)

    return max(0.0, min(1.0, trust)), hit


def run_arm_test1_hard_fixed_penalty(seed: int, months: int = 36) -> dict[str, Any]:
    """TEST 1: Hard curve (0-2x) WITH fixed penalty function.

    Isolates: Does the penalty fix alone explain the win?
    """
    oracle = B2BSaaSOracle(seed)
    agents = B2BSaaSAgents(seed)
    state = B2BSaaSState()
    monthly_results = []
    shutdown_month = None

    for month in range(1, months + 1):
        base_policy = control_policy(month)
        ad_spend = base_policy["ad_spend"]
        price = base_policy["price"]
        churn_rate = base_policy["churn_rate"]

        prior_cac = monthly_results[-1]["actual_cac"] if monthly_results else None
        monthly_burn = monthly_results[-1]["operating_profit"] if monthly_results else -state.cash_balance / max(1, month)

        forecasts = agents.all_forecasts(
            month=month,
            current_customers=state.customers,
            current_cash=state.cash_balance,
            current_churn_rate=state.monthly_churn_rate,
            monthly_burn=monthly_burn,
            prior_actual_cac=prior_cac,
        )

        state.monthly_churn_rate = churn_rate
        outcome = oracle.monthly_outcome(month, state, ad_spend, price)

        gm_trust, _ = calculate_agent_trust_soft(forecasts["growth_marketer"].prediction, outcome["actual_cac"], tolerance=0.10)
        fc_trust, _ = calculate_agent_trust_soft(forecasts["finance_controller"].prediction, state.cash_balance / 10_000, tolerance=0.30)
        pm_trust, _ = calculate_agent_trust_soft(forecasts["product_manager"].prediction, 0.5, tolerance=0.25)
        om_trust, _ = calculate_agent_trust_soft(forecasts["operations_manager"].prediction, outcome["churn_rate"], tolerance=0.025)

        # Apply HARD curve (0-2x) with FIXED penalty
        ad_spend = ad_spend * (2.0 * gm_trust)
        ad_spend = min(max(ad_spend, 0), 90_000)
        price = price * (2.0 * pm_trust)

        state.monthly_churn_rate = churn_rate
        outcome = oracle.monthly_outcome(month, state, ad_spend, price)
        monthly_results.append(outcome)

        state.customers = outcome["ending_customers"]
        state.cash_balance = outcome["cash_balance"]

        if state.cash_balance < 0 and shutdown_month is None:
            shutdown_month = month
            state.cash_balance = 0

    return {
        "seed": seed,
        "final_cash_balance": state.cash_balance,
        "is_profitable": (shutdown_month is None and state.cash_balance > 0),
        "shutdown_month": shutdown_month,
    }


def run_arm_test2_soft_random_weights(seed: int, months: int = 36) -> dict[str, Any]:
    """TEST 2: Soft curve (0.5-1.5x) with RANDOM trust scores.

    CRITICAL PLACEBO TEST: If random also wins ~18/25, the victory is about
    'gentle deviations from control' not 'calibration works'.
    """
    oracle = B2BSaaSOracle(seed)
    agents = B2BSaaSAgents(seed)
    state = B2BSaaSState()
    monthly_results = []
    shutdown_month = None

    for month in range(1, months + 1):
        base_policy = control_policy(month)
        ad_spend = base_policy["ad_spend"]
        price = base_policy["price"]
        churn_rate = base_policy["churn_rate"]

        prior_cac = monthly_results[-1]["actual_cac"] if monthly_results else None
        monthly_burn = monthly_results[-1]["operating_profit"] if monthly_results else -state.cash_balance / max(1, month)

        forecasts = agents.all_forecasts(
            month=month,
            current_customers=state.customers,
            current_cash=state.cash_balance,
            current_churn_rate=state.monthly_churn_rate,
            monthly_burn=monthly_burn,
            prior_actual_cac=prior_cac,
        )

        state.monthly_churn_rate = churn_rate
        outcome = oracle.monthly_outcome(month, state, ad_spend, price)

        # Generate RANDOM trust values (placebo)
        rng = random.Random(seed ^ month ^ 0x12345)
        gm_trust_random = rng.uniform(0.0, 1.0)
        pm_trust_random = rng.uniform(0.0, 1.0)

        # Apply SOFT curve (0.5-1.5x) with RANDOM weights
        ad_spend = ad_spend * (0.5 + gm_trust_random)
        ad_spend = min(max(ad_spend, 0), 90_000)
        price = price * (0.5 + pm_trust_random)

        state.monthly_churn_rate = churn_rate
        outcome = oracle.monthly_outcome(month, state, ad_spend, price)
        monthly_results.append(outcome)

        state.customers = outcome["ending_customers"]
        state.cash_balance = outcome["cash_balance"]

        if state.cash_balance < 0 and shutdown_month is None:
            shutdown_month = month
            state.cash_balance = 0

    return {
        "seed": seed,
        "final_cash_balance": state.cash_balance,
        "is_profitable": (shutdown_month is None and state.cash_balance > 0),
        "shutdown_month": shutdown_month,
    }


def run_arm_test3_soft_trust_weights(seed: int, months: int = 36) -> dict[str, Any]:
    """TEST 3: Soft curve (0.5-1.5x) with TRUST-BASED weights.

    Baseline: Should win ~18/25 if calibration works.
    """
    oracle = B2BSaaSOracle(seed)
    agents = B2BSaaSAgents(seed)
    state = B2BSaaSState()
    monthly_results = []
    shutdown_month = None

    for month in range(1, months + 1):
        base_policy = control_policy(month)
        ad_spend = base_policy["ad_spend"]
        price = base_policy["price"]
        churn_rate = base_policy["churn_rate"]

        prior_cac = monthly_results[-1]["actual_cac"] if monthly_results else None
        monthly_burn = monthly_results[-1]["operating_profit"] if monthly_results else -state.cash_balance / max(1, month)

        forecasts = agents.all_forecasts(
            month=month,
            current_customers=state.customers,
            current_cash=state.cash_balance,
            current_churn_rate=state.monthly_churn_rate,
            monthly_burn=monthly_burn,
            prior_actual_cac=prior_cac,
        )

        state.monthly_churn_rate = churn_rate
        outcome = oracle.monthly_outcome(month, state, ad_spend, price)

        # Calculate TRUST scores (not random)
        gm_trust, _ = calculate_agent_trust_soft(forecasts["growth_marketer"].prediction, outcome["actual_cac"], tolerance=0.10)
        pm_trust, _ = calculate_agent_trust_soft(forecasts["product_manager"].prediction, 0.5, tolerance=0.25)

        # Apply SOFT curve (0.5-1.5x) with TRUST weights
        ad_spend = ad_spend * (0.5 + gm_trust)
        ad_spend = min(max(ad_spend, 0), 90_000)
        price = price * (0.5 + pm_trust)

        state.monthly_churn_rate = churn_rate
        outcome = oracle.monthly_outcome(month, state, ad_spend, price)
        monthly_results.append(outcome)

        state.customers = outcome["ending_customers"]
        state.cash_balance = outcome["cash_balance"]

        if state.cash_balance < 0 and shutdown_month is None:
            shutdown_month = month
            state.cash_balance = 0

    return {
        "seed": seed,
        "final_cash_balance": state.cash_balance,
        "is_profitable": (shutdown_month is None and state.cash_balance > 0),
        "shutdown_month": shutdown_month,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+",
                       default=[1234, 1235, 1236, 1237, 1238,
                               2001, 2002, 2003, 2004, 2005,
                               3333, 3334, 3335, 3336, 3337,
                               4999, 5000, 5001, 5002, 5003,
                               6789, 7000, 8000, 9000, 9999])
    parser.add_argument("--output", type=Path, default=Path("evals/experiments/diagnostic_weighting_tests.json"))

    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Load control baseline
    control_path = Path("evals/experiments/b2b_saas_control_arm.json")
    with open(control_path) as f:
        control_data = json.load(f)
    control_dict = {r["seed"]: r["final_cash_balance"] for r in control_data["results"]}

    print("Running three diagnostic isolation tests...\n")

    test1_results = []
    test2_results = []
    test3_results = []

    for i, seed in enumerate(args.seeds, 1):
        test1 = run_arm_test1_hard_fixed_penalty(seed)
        test2 = run_arm_test2_soft_random_weights(seed)
        test3 = run_arm_test3_soft_trust_weights(seed)

        test1_results.append(test1)
        test2_results.append(test2)
        test3_results.append(test3)

        control_cash = control_dict[seed]
        t1_beats = "✓" if test1["final_cash_balance"] > control_cash else "✗"
        t2_beats = "✓" if test2["final_cash_balance"] > control_cash else "✗"
        t3_beats = "✓" if test3["final_cash_balance"] > control_cash else "✗"

        print(f"[{i:2d}] Seed {seed:4d}: Control ${control_cash:8.0f}")
        print(f"     T1 (hard+fixed):  ${test1['final_cash_balance']:8.0f} {t1_beats}")
        print(f"     T2 (soft+random): ${test2['final_cash_balance']:8.0f} {t2_beats}")
        print(f"     T3 (soft+trust):  ${test3['final_cash_balance']:8.0f} {t3_beats}\n")

    print("="*70)
    print("RESULTS SUMMARY")
    print("="*70)

    test1_wins = sum(1 for t1, seed in zip(test1_results, args.seeds)
                     if t1["final_cash_balance"] > control_dict[seed])
    test2_wins = sum(1 for t2, seed in zip(test2_results, args.seeds)
                     if t2["final_cash_balance"] > control_dict[seed])
    test3_wins = sum(1 for t3, seed in zip(test3_results, args.seeds)
                     if t3["final_cash_balance"] > control_dict[seed])

    print(f"\nTest 1 (hard curve 0-2x + FIXED penalty):")
    print(f"  Wins: {test1_wins}/25 ({100*test1_wins/25:.1f}%)")
    print(f"  → Isolates: Does penalty fix alone explain the win?")

    print(f"\nTest 2 (soft curve 0.5-1.5x + RANDOM weights) — CRITICAL PLACEBO:")
    print(f"  Wins: {test2_wins}/25 ({100*test2_wins/25:.1f}%)")
    print(f"  → If ~18/25: 'Small deviations work' regardless of trust")
    print(f"  → If <14/25: Trust signal actually matters")

    print(f"\nTest 3 (soft curve 0.5-1.5x + TRUST weights):")
    print(f"  Wins: {test3_wins}/25 ({100*test3_wins/25:.1f}%)")
    print(f"  → Baseline: Should beat test 2 if calibration works")

    print("\n" + "="*70)
    print("INTERPRETATION")
    print("="*70)

    if test2_wins >= 14:
        print("\n⚠️  RANDOM WEIGHTING ALSO WINS (~18/25)")
        print("    This means: ±50% deviations from control help REGARDLESS of trust")
        print("    Verdict: NOT supported. The win is about deviation magnitude,")
        print("    not about calibration working.")
        print(f"    (Trust test 3: {test3_wins}, Random test 2: {test2_wins})")
    else:
        print("\n✓ RANDOM WEIGHTING FAILS (<14/25)")
        print("    This means: Trust signal is doing the work")
        print(f"    Trust wins ({test3_wins}), random loses ({test2_wins})")
        print("    Verdict: SUPPORTED. Calibration-weighting works.")

    if test1_wins >= 14:
        print(f"\n    ADDITIONAL: Hard+fixed also wins ({test1_wins}/25)")
        print("    This means: Penalty function fix was the primary gain")

    summary = {
        "timestamp": datetime.now().isoformat(),
        "control_results": {
            "mean_cash": statistics.mean(control_dict.values()),
            "seeds_profitable": sum(1 for v in control_dict.values() if v > 0),
        },
        "test_1_hard_fixed_penalty": {
            "wins": test1_wins,
            "pct": 100.0 * test1_wins / 25,
        },
        "test_2_soft_random_placebo": {
            "wins": test2_wins,
            "pct": 100.0 * test2_wins / 25,
            "critical_test": True,
        },
        "test_3_soft_trust": {
            "wins": test3_wins,
            "pct": 100.0 * test3_wins / 25,
        },
        "verdict": {
            "test_2_above_14": test2_wins >= 14,
            "test_3_above_14": test3_wins >= 14,
            "calibration_works": (test2_wins < 14 and test3_wins >= 14),
            "interpretation": "Calibration works" if (test2_wins < 14 and test3_wins >= 14) else "Deviations work, not trust signal"
        }
    }

    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
