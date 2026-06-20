#!/usr/bin/env python3
"""B2B SaaS four-arm experiment with trust-weighted decisions.

Runs Arm A (control), B (trust-weighted), C (CEO excluded), D (symmetric brake).
Agents make forecasts → trust scores calculated → decisions weighted.

Implements pre-registered hypothesis from B2B_SAAS_PRE_REGISTERED_HYPOTHESIS.md
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
from scripts.b2b_saas_agents import B2BSaaSAgents, calculate_agent_trust


@dataclass
class ArmConfig:
    """Configuration for an experimental arm."""
    name: str
    use_trust_weighting: bool = False
    exclude_ceo: bool = False
    use_symmetric_brake: bool = False


def run_arm(
    seed: int,
    arm_config: ArmConfig,
    months: int = 36,
) -> dict[str, Any]:
    """Run one arm of the experiment."""
    oracle = B2BSaaSOracle(seed)
    agents = B2BSaaSAgents(seed)
    state = B2BSaaSState()
    monthly_results = []
    shutdown_month = None
    trust_history = {}

    for month in range(1, months + 1):
        # Get base control policy decisions
        base_policy = control_policy(month)
        ad_spend = base_policy["ad_spend"]
        price = base_policy["price"]
        churn_rate = base_policy["churn_rate"]

        # Generate agent forecasts (always, for diagnostics)
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

        # Get oracle outcome FIRST (before weighting, to resolve forecasts)
        state.monthly_churn_rate = churn_rate
        outcome = oracle.monthly_outcome(month, state, ad_spend, price)

        # Now calculate trust scores based on actual outcome
        # Growth Marketer: CAC forecast vs actual
        gm_forecast = forecasts["growth_marketer"]
        gm_forecast.actual_value = outcome["actual_cac"]
        gm_trust, gm_hit = calculate_agent_trust(gm_forecast, tolerance=0.15)

        # Finance Controller: runway forecast vs actual cash
        fc_forecast = forecasts["finance_controller"]
        if state.cash_balance < 50_000:
            fc_forecast.actual_value = state.cash_balance / max(1, state.cash_balance + 1)  # Low runway
        else:
            fc_forecast.actual_value = 18.0  # High runway (dummy value for comparison)
        fc_trust, fc_hit = calculate_agent_trust(fc_forecast, tolerance=0.30)

        # Product Manager: price elasticity (harder to resolve, use pseudo-truth)
        pm_forecast = forecasts["product_manager"]
        pm_forecast.actual_value = 0.5  # Neutral pseudo-truth
        pm_trust, pm_hit = calculate_agent_trust(pm_forecast, tolerance=0.25)

        # Operations Manager: churn forecast vs actual
        om_forecast = forecasts["operations_manager"]
        om_forecast.actual_value = outcome["churn_rate"]
        om_trust, om_hit = calculate_agent_trust(om_forecast, tolerance=0.025)

        # Founder CEO: pseudo-truth (hard to resolve, give them random trust)
        ceo_rng = random.Random(seed ^ month)
        ceo_trust = ceo_rng.uniform(0.0, 1.0)

        # Store trust history for weighting
        if arm_config.use_trust_weighting:
            trust_history.update({
                "Growth Marketer": gm_trust,
                "Finance Controller": fc_trust,
                "Product Manager": pm_trust,
                "Operations Manager": om_trust,
                "Founder CEO": ceo_trust,
            })

            # Apply trust weighting to decisions
            if arm_config.exclude_ceo:
                trust_history.pop("Founder CEO", None)

            # Growth Marketer: weight ad spend
            gm_t = trust_history.get("Growth Marketer", 0.5)
            ad_spend = ad_spend * (2.0 * gm_t)

            # Finance Controller: brake spending (symmetric weighting)
            if arm_config.use_symmetric_brake:
                fc_t = trust_history.get("Finance Controller", 0.5)
                finance_brake = 1.0 - fc_t
                ad_spend = ad_spend * finance_brake

            ad_spend = min(max(ad_spend, 0), 90_000)

            # Product Manager: weight price
            pm_t = trust_history.get("Product Manager", 0.5)
            price = price * (2.0 * pm_t)

        # Now re-run oracle with weighted decisions
        state.monthly_churn_rate = churn_rate
        outcome = oracle.monthly_outcome(month, state, ad_spend, price)

        outcome["month"] = month
        outcome["arm"] = arm_config.name
        outcome["seed"] = seed
        outcome["gm_trust"] = gm_trust if arm_config.use_trust_weighting else 0.5
        outcome["fc_trust"] = fc_trust if arm_config.use_trust_weighting else 0.5
        outcome["pm_trust"] = pm_trust if arm_config.use_trust_weighting else 0.5
        outcome["om_trust"] = om_trust if arm_config.use_trust_weighting else 0.5
        outcome["ceo_trust"] = ceo_trust if (arm_config.use_trust_weighting and not arm_config.exclude_ceo) else 0.5

        monthly_results.append(outcome)

        # Update state
        state.customers = outcome["ending_customers"]
        state.cash_balance = outcome["cash_balance"]
        state.cumulative_months = month

        # Check for shutdown
        if state.cash_balance < 0 and shutdown_month is None:
            shutdown_month = month
            state.cash_balance = 0

    # Summary
    final_cash = state.cash_balance
    is_profitable = (shutdown_month is None and final_cash > 0)
    profitable_months = sum(1 for r in monthly_results if r["operating_profit"] > 0)

    return {
        "seed": seed,
        "arm": arm_config.name,
        "final_cash_balance": final_cash,
        "profitable_months": profitable_months,
        "is_profitable": is_profitable,
        "shutdown_month": shutdown_month,
        "final_customers": monthly_results[-1]["ending_customers"] if monthly_results else 0,
        "monthly_results": monthly_results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+",
                       default=[1234, 1235, 1236, 1237, 1238,
                               2001, 2002, 2003, 2004, 2005,
                               3333, 3334, 3335, 3336, 3337,
                               4999, 5000, 5001, 5002, 5003,
                               6789, 7000, 8000, 9000, 9999],
                       help="Pre-registered 25 seeds")
    parser.add_argument("--output", type=Path, default=Path("evals/experiments/b2b_saas_four_arm_results.json"))
    parser.add_argument("--csv", type=Path, default=Path("evals/experiments/b2b_saas_four_arm_monthly.csv"))

    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Define the four arms
    arms = [
        ArmConfig(name="Arm A: Control", use_trust_weighting=False),
        ArmConfig(name="Arm B: Trust-Weighted", use_trust_weighting=True),
        ArmConfig(name="Arm C: CEO Excluded", use_trust_weighting=True, exclude_ceo=True),
        ArmConfig(name="Arm D: Symmetric Brake", use_trust_weighting=True, use_symmetric_brake=True),
    ]

    # Run experiment
    print(f"Running four-arm experiment on {len(args.seeds)} seeds...")
    all_results = {}

    for arm in arms:
        print(f"\n{arm.name}:")
        arm_results = []

        for i, seed in enumerate(args.seeds, 1):
            result = run_arm(seed, arm, months=36)
            arm_results.append(result)

            status = "PROFITABLE" if result["is_profitable"] else "LOSS"
            print(f"  [{i:2d}/{len(args.seeds)}] Seed {seed:4d}: ${result['final_cash_balance']:10.0f} ({status})")

        all_results[arm.name] = arm_results

    # Analysis
    print(f"\n{'='*70}")
    print("FOUR-ARM ANALYSIS")
    print(f"{'='*70}\n")

    # Primary analysis: count seeds where B > A
    arm_a_results = {r["seed"]: r for r in all_results["Arm A: Control"]}
    arm_b_results = {r["seed"]: r for r in all_results["Arm B: Trust-Weighted"]}

    b_wins = 0
    for seed in args.seeds:
        if arm_b_results[seed]["final_cash_balance"] > arm_a_results[seed]["final_cash_balance"]:
            b_wins += 1

    win_pct = 100.0 * b_wins / len(args.seeds)
    passes_test = b_wins >= 14  # Pre-registered threshold

    print(f"PRIMARY METRIC: Arm B vs Arm A")
    print(f"Arm B wins: {b_wins}/{len(args.seeds)} seeds ({win_pct:.1f}%)")
    print(f"Pre-registered threshold: ≥14/25 (56%)")
    print(f"Hypothesis: {'✓ SUPPORTED' if passes_test else '✗ FALSIFIED'}\n")

    # Per-arm summary stats
    for arm_name in [a.name for a in arms]:
        results = all_results[arm_name]
        cash_balances = [r["final_cash_balance"] for r in results]
        profitable_count = sum(1 for r in results if r["is_profitable"])

        mean_cash = statistics.mean(cash_balances)
        sd_cash = statistics.stdev(cash_balances) if len(cash_balances) > 1 else 0

        print(f"{arm_name}:")
        print(f"  Profitable: {profitable_count}/25")
        print(f"  Mean cash: ${mean_cash:,.0f}")
        print(f"  Std dev:   ${sd_cash:,.0f}")
        print(f"  Min:       ${min(cash_balances):,.0f}")
        print(f"  Max:       ${max(cash_balances):,.0f}")
        print()

    # Spread analysis: Arm B - Arm A
    print("SPREAD ANALYSIS (Arm B - Arm A):")
    spreads = []
    for seed in args.seeds:
        b_cash = arm_b_results[seed]["final_cash_balance"]
        a_cash = arm_a_results[seed]["final_cash_balance"]
        spread = b_cash - a_cash
        spreads.append(spread)

    mean_spread = statistics.mean(spreads)
    sd_spread = statistics.stdev(spreads) if len(spreads) > 1 else 0
    min_spread = min(spreads)
    max_spread = max(spreads)

    print(f"  Mean spread:   ${mean_spread:+,.0f}")
    print(f"  Std dev spread: ${sd_spread:,.0f}")
    print(f"  Min spread:    ${min_spread:+,.0f}")
    print(f"  Max spread:    ${max_spread:+,.0f}")

    if sd_spread < 100_000:
        print(f"  → NOISE PATTERN (low variance, possible uniform offset)")
    else:
        print(f"  → SIGNAL PATTERN (high variance, clustered wins)")

    # Save results
    summary = {
        "timestamp": datetime.now().isoformat(),
        "primary_metric": {
            "arm_b_wins": b_wins,
            "total_seeds": len(args.seeds),
            "win_pct": win_pct,
            "pre_registered_threshold": 14,
            "hypothesis_status": "SUPPORTED" if passes_test else "FALSIFIED",
        },
        "spread_analysis": {
            "mean_spread": mean_spread,
            "stdev_spread": sd_spread,
            "min_spread": min_spread,
            "max_spread": max_spread,
        },
        "all_results": all_results,
    }

    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nResults saved to {args.output}")

    # Save monthly data
    with open(args.csv, "w") as f:
        writer = None
        for arm_name, results in all_results.items():
            for result in results:
                for monthly in result["monthly_results"]:
                    if writer is None:
                        writer = csv.DictWriter(f, fieldnames=monthly.keys())
                        writer.writeheader()
                    writer.writerow(monthly)
    print(f"Monthly data saved to {args.csv}")

    return 0 if passes_test else 1


if __name__ == "__main__":
    sys.exit(main())
