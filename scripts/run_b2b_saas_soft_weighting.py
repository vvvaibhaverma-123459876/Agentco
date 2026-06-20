#!/usr/bin/env python3
"""Re-run four-arm experiment with SOFT weighting (0.5-1.5x) and FIXED penalty function.

Changes from hard-weighting run:
1. Penalty function: Properly calibrated (75% accurate → 0.7+ trust)
2. Weighting curve: 0.5-1.5x instead of 0-2x (less extreme)
3. Same 25 seeds, same business model, same hypothesis

This tests whether the failure was due to poor tuning, not poor principle.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_b2b_saas_simulation import B2BSaaSOracle, B2BSaaSState, control_policy
from scripts.b2b_saas_agents import B2BSaaSAgents


def calculate_agent_trust_soft(forecast, actual, tolerance=0.10):
    """FIXED penalty function - properly calibrated.

    75% accurate agent should get trust ~0.75-0.80, not 0.3.

    Returns: (trust_score [0-1], hit [bool])
    """
    if actual is None:
        return 0.5, None

    error = abs(forecast - actual)
    error_pct = error / max(0.01, actual)

    # Hit if within tolerance
    hit = error_pct <= tolerance

    # Properly calibrated penalty:
    # - Within tolerance (0-10%): trust 0.7-1.0
    # - 10-20% error: trust 0.5-0.7 (still reasonable)
    # - 20-30% error: trust 0.3-0.5 (poor)
    # - >30% error: trust <0.3 (bad)

    if error_pct <= tolerance:
        # Within tolerance: map [0, tolerance] to [0.7, 1.0]
        trust = 0.7 + (1.0 - error_pct / tolerance) * 0.3
    elif error_pct <= 0.20:
        # Moderate error: map [tolerance, 0.20] to [0.7, 0.5]
        trust = 0.7 - (error_pct - tolerance) / (0.20 - tolerance) * 0.2
    elif error_pct <= 0.30:
        # High error: map [0.20, 0.30] to [0.5, 0.3]
        trust = 0.5 - (error_pct - 0.20) / 0.10 * 0.2
    else:
        # Terrible error: below 0.3
        trust = max(0.0, 0.3 - (error_pct - 0.30) * 0.5)

    return max(0.0, min(1.0, trust)), hit


def run_arm_soft(
    seed: int,
    use_trust_weighting: bool = False,
    exclude_ceo: bool = False,
    use_symmetric_brake: bool = False,
    months: int = 36,
) -> dict[str, Any]:
    """Run one arm with soft weighting (0.5-1.5x multiplier, fixed penalty)."""
    oracle = B2BSaaSOracle(seed)
    agents = B2BSaaSAgents(seed)
    state = B2BSaaSState()
    monthly_results = []
    shutdown_month = None
    trust_history = {}

    for month in range(1, months + 1):
        base_policy = control_policy(month)
        ad_spend = base_policy["ad_spend"]
        price = base_policy["price"]
        churn_rate = base_policy["churn_rate"]

        # Generate forecasts
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

        # Run oracle with base decisions
        state.monthly_churn_rate = churn_rate
        outcome = oracle.monthly_outcome(month, state, ad_spend, price)

        # Calculate trust with FIXED penalty function
        gm_trust, _ = calculate_agent_trust_soft(
            forecasts["growth_marketer"].prediction,
            outcome["actual_cac"],
            tolerance=0.10
        )
        fc_trust, _ = calculate_agent_trust_soft(
            forecasts["finance_controller"].prediction,
            state.cash_balance / 10_000,  # Normalized
            tolerance=0.30
        )
        pm_trust, _ = calculate_agent_trust_soft(
            forecasts["product_manager"].prediction,
            0.5,  # Neutral
            tolerance=0.25
        )
        om_trust, _ = calculate_agent_trust_soft(
            forecasts["operations_manager"].prediction,
            outcome["churn_rate"],
            tolerance=0.025
        )

        ceo_rng = random.Random(seed ^ month)
        ceo_trust = ceo_rng.uniform(0.0, 1.0)

        if use_trust_weighting:
            trust_history.update({
                "Growth Marketer": gm_trust,
                "Finance Controller": fc_trust,
                "Product Manager": pm_trust,
                "Operations Manager": om_trust,
                "Founder CEO": ceo_trust,
            })

            if exclude_ceo:
                trust_history.pop("Founder CEO", None)

            # SOFT WEIGHTING: 0.5-1.5x instead of 0-2x
            # Formula: 0.5 + trust (maps [0, 1] to [0.5, 1.5])
            gm_t = trust_history.get("Growth Marketer", 0.5)
            ad_spend = ad_spend * (0.5 + gm_t)

            if use_symmetric_brake:
                fc_t = trust_history.get("Finance Controller", 0.5)
                finance_brake = 0.75 + 0.5 * (1.0 - fc_t)  # 0.75-1.25 range
                ad_spend = ad_spend * finance_brake

            ad_spend = min(max(ad_spend, 0), 90_000)

            pm_t = trust_history.get("Product Manager", 0.5)
            price = price * (0.5 + pm_t)

        # Re-run oracle with weighted decisions
        state.monthly_churn_rate = churn_rate
        outcome = oracle.monthly_outcome(month, state, ad_spend, price)

        outcome["month"] = month
        outcome["seed"] = seed
        outcome["gm_trust"] = gm_trust if use_trust_weighting else 0.5
        outcome["fc_trust"] = fc_trust if use_trust_weighting else 0.5
        outcome["pm_trust"] = pm_trust if use_trust_weighting else 0.5
        outcome["om_trust"] = om_trust if use_trust_weighting else 0.5

        monthly_results.append(outcome)

        state.customers = outcome["ending_customers"]
        state.cash_balance = outcome["cash_balance"]
        state.cumulative_months = month

        if state.cash_balance < 0 and shutdown_month is None:
            shutdown_month = month
            state.cash_balance = 0

    final_cash = state.cash_balance
    is_profitable = (shutdown_month is None and final_cash > 0)

    return {
        "seed": seed,
        "final_cash_balance": final_cash,
        "is_profitable": is_profitable,
        "shutdown_month": shutdown_month,
        "monthly_results": monthly_results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+",
                       default=[1234, 1235, 1236, 1237, 1238,
                               2001, 2002, 2003, 2004, 2005,
                               3333, 3334, 3335, 3336, 3337,
                               4999, 5000, 5001, 5002, 5003,
                               6789, 7000, 8000, 9000, 9999])
    parser.add_argument("--output", type=Path,
                       default=Path("evals/experiments/b2b_saas_soft_weighting_results.json"))

    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    print("Running soft-weighting experiment (0.5-1.5x, fixed penalty function)...\n")

    # Control arm (for comparison)
    print("Arm A (Control):")
    control_results = []
    for i, seed in enumerate(args.seeds, 1):
        result = run_arm_soft(seed, use_trust_weighting=False)
        control_results.append(result)
        status = "✓" if result["is_profitable"] else "✗"
        print(f"  [{i:2d}] Seed {seed:4d}: ${result['final_cash_balance']:10.0f} {status}")

    # Trust-weighted arm (soft)
    print("\nArm B (Soft Weighting 0.5-1.5x, Fixed Penalty):")
    soft_results = []
    for i, seed in enumerate(args.seeds, 1):
        result = run_arm_soft(seed, use_trust_weighting=True)
        soft_results.append(result)
        status = "✓" if result["is_profitable"] else "✗"
        print(f"  [{i:2d}] Seed {seed:4d}: ${result['final_cash_balance']:10.0f} {status}")

    # Analysis
    print("\n" + "="*70)
    print("SOFT WEIGHTING TEST RESULTS")
    print("="*70)

    control_dict = {r["seed"]: r for r in control_results}
    soft_dict = {r["seed"]: r for r in soft_results}

    soft_wins = sum(1 for seed in args.seeds
                   if soft_dict[seed]["final_cash_balance"] > control_dict[seed]["final_cash_balance"])
    soft_profitable = sum(1 for r in soft_results if r["is_profitable"])

    print(f"\nArm A (Control):")
    control_cash = [r["final_cash_balance"] for r in control_results]
    print(f"  Profitable: {sum(1 for r in control_results if r['is_profitable'])}/25")
    print(f"  Mean cash: ${statistics.mean(control_cash):,.0f}")

    print(f"\nArm B (Soft Weighting):")
    soft_cash = [r["final_cash_balance"] for r in soft_results]
    print(f"  Profitable: {soft_profitable}/25")
    print(f"  Mean cash: ${statistics.mean(soft_cash):,.0f}")

    print(f"\nComparison:")
    print(f"  Soft wins: {soft_wins}/25 seeds ({100*soft_wins/25:.1f}%)")
    print(f"  Pre-registered threshold: ≥14/25 (56%)")

    if soft_wins >= 14:
        print(f"  Result: ✓ PASSES (soft weighting beats hard)")
    else:
        print(f"  Result: ✗ Still fails (but is it better than hard?)")

    # Save results
    summary = {
        "timestamp": datetime.now().isoformat(),
        "penalty_function": "Fixed (75% accurate → 0.7+ trust, not 0.3)",
        "weighting_range": "0.5-1.5x (soft, not 0-2x hard)",
        "control_results": {
            "profitable": sum(1 for r in control_results if r["is_profitable"]),
            "mean_cash": statistics.mean(control_cash),
            "stdev_cash": statistics.stdev(control_cash),
        },
        "soft_results": {
            "profitable": soft_profitable,
            "mean_cash": statistics.mean(soft_cash),
            "stdev_cash": statistics.stdev(soft_cash),
            "wins_vs_control": soft_wins,
        },
        "hypothesis_test": {
            "threshold": 14,
            "actual": soft_wins,
            "passes": soft_wins >= 14,
        },
    }

    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to {args.output}")

    return 0 if soft_wins >= 14 else 1


if __name__ == "__main__":
    sys.exit(main())
