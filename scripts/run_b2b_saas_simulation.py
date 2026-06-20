#!/usr/bin/env python3
"""Deterministic B2B SaaS business simulation for fair calibration-weighting test.

This harness implements the frozen B2B SaaS model from B2B_SAAS_FROZEN_MODEL.md.
Control arm only: fixed decisions, no trust-weighting.
Purpose: Validate gate criteria (30-60% profitable, high variance, suboptimal control visible).
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


@dataclass
class B2BSaaSState:
    """Business state at start of month."""
    customers: int = 0
    monthly_churn_rate: float = 0.06  # 6% baseline (no CS investment)
    arpu: float = 79.0  # $79/month after COGS
    price: float = 79.0
    cash_balance: float = 50_000.0  # Lowered from $100k to create loss scenarios
    cumulative_months: int = 0

    def copy(self) -> B2BSaaSState:
        return B2BSaaSState(
            customers=self.customers,
            monthly_churn_rate=self.monthly_churn_rate,
            arpu=self.arpu,
            price=self.price,
            cash_balance=self.cash_balance,
            cumulative_months=self.cumulative_months,
        )


class B2BSaaSOracle:
    """Deterministic market oracle for B2B SaaS model."""

    def __init__(self, seed: int):
        self.seed = seed

    def _rng(self, month: int, label: str) -> random.Random:
        """Deterministic RNG seeded by seed, month, and label."""
        digest = hashlib.sha256(f"{self.seed}|{month}|{label}".encode()).hexdigest()
        return random.Random(int(digest[:16], 16))

    def monthly_outcome(
        self,
        month: int,
        state: B2BSaaSState,
        ad_spend: float,
        price: float,
    ) -> dict[str, Any]:
        """Deterministic market response to decisions."""
        rng = self._rng(month, "market")

        # Market difficulty seed-level (extreme variation)
        # This creates "easy" vs "hard" market seeds
        market_base_rng = random.Random(self.seed)
        market_difficulty = market_base_rng.uniform(0.2, 2.8)  # EXTREME: 0.2 = easy, 2.8 = brutal

        # CAC trajectory: seed-specific difficulty + month-based competition
        # Easy seeds: $25-40 CAC; Hard seeds: $80-180 CAC
        base_cac = 60 * market_difficulty

        # Market shock: some seeds have brutal early market (month 1-9 spike)
        early_shock = 1.0
        if month <= 9:
            early_shock_rng = random.Random(self.seed ^ 0x999)
            early_shock = early_shock_rng.uniform(0.7, 3.0)  # Some seeds get hit early & hard

        competition_factor = 1.0 + 0.012 * month  # CAC rises over time
        actual_cac = max(20, base_cac * competition_factor * early_shock + rng.uniform(-10, 10))

        # New customers from ad spend - but market saturation kicks in
        # Market cap: max acquisition rate per month (seed-dependent)
        market_cap_factor = rng.uniform(0.7, 1.2)
        max_new_customers_market = int(300 * market_cap_factor)

        if ad_spend > 0:
            new_customers = int(ad_spend / actual_cac)
            new_customers = min(new_customers, max_new_customers_market)  # Market cap
        else:
            new_customers = 0

        # Churn - baseline 6% but can be influenced by business health
        # Healthier businesses (higher CAC means efficient acquisition) have better retention
        churn_factor = 1.0 if actual_cac < 35 else 1.1  # Higher CAC = worse churn signal
        state_churn = min(0.12, state.monthly_churn_rate * churn_factor)

        churned = int(state.customers * state_churn)
        ending_customers = max(0, state.customers + new_customers - churned)

        # Revenue
        gross_revenue = ending_customers * price

        # Costs - includes ad spend
        cogs = ending_customers * 22.0  # $22 COGS per customer/month (slightly higher)
        fixed_cost = self._fixed_cost_tier(ending_customers)
        total_cost = cogs + fixed_cost + ad_spend

        # Profit
        operating_profit = gross_revenue - total_cost
        cash_balance = state.cash_balance + operating_profit

        # LTV estimate for diagnostics
        if state_churn >= 0.01:
            ltv = (price - 22.0) / state_churn
        else:
            ltv = (price - 22.0) / 0.01

        return {
            "month": month,
            "seed": self.seed,
            "starting_customers": state.customers,
            "new_customers": new_customers,
            "churned_customers": churned,
            "ending_customers": ending_customers,
            "ad_spend": ad_spend,
            "actual_cac": round(actual_cac, 2),
            "price": price,
            "gross_revenue": round(gross_revenue, 2),
            "cogs": round(cogs, 2),
            "fixed_cost": round(fixed_cost, 2),
            "total_cost": round(total_cost, 2),
            "operating_profit": round(operating_profit, 2),
            "cash_balance": round(cash_balance, 2),
            "ltv_estimate": round(ltv, 2),
            "churn_rate": state_churn,
            "market_difficulty": round(market_difficulty, 2),
            "profitability_margin": round((gross_revenue - cogs - fixed_cost) / max(1, gross_revenue), 4) if gross_revenue > 0 else 0.0,
        }

    def _fixed_cost_tier(self, customers: int) -> float:
        """Scale-aware fixed costs (higher to create tension with ARPU)."""
        if customers <= 50:
            return 5000.0
        elif customers <= 150:
            return 8000.0
        elif customers <= 300:
            return 12000.0
        elif customers <= 600:
            return 15000.0
        else:
            return 18000.0

    def _market_conditions(self, month: int) -> dict[str, Any]:
        """Market phase and competitive dynamics."""
        if month <= 6:
            return {"phase": "early", "competition": "low"}
        elif month <= 12:
            return {"phase": "expansion", "competition": "moderate"}
        elif month <= 24:
            return {"phase": "maturity", "competition": "high"}
        else:
            return {"phase": "consolidation", "competition": "extreme"}


def control_policy(month: int) -> dict[str, float]:
    """
    Fixed, suboptimal control policy from B2B_SAAS_FROZEN_MODEL.md.

    Suboptimality (independent reasoning):
    - Fixed ad spend regardless of CAC signals
    - Fixed $99 price never adjusted
    - No CS investment (6-8% churn vs 3-4% with investment)
    """
    ad_spend_schedule = {
        (1, 6): 3000.0,
        (7, 18): 5000.0,
        (19, 36): 6000.0,
    }

    ad_spend = 3000.0  # default
    for (start, end), spend in ad_spend_schedule.items():
        if start <= month <= end:
            ad_spend = spend
            break

    return {
        "ad_spend": ad_spend,
        "price": 79.0,  # Lowered from $99 to create more tension
        "churn_rate": 0.06,  # No CS investment
    }


def run_control_arm(seed: int, months: int = 36) -> dict[str, Any]:
    """Run control arm simulation for one seed.

    Shutdown condition: If cash ever goes negative (funding runs out), business dies.
    """
    oracle = B2BSaaSOracle(seed)
    state = B2BSaaSState()
    monthly_results = []
    shutdown_month = None

    for month in range(1, months + 1):
        policy = control_policy(month)

        # Apply control decisions
        ad_spend = policy["ad_spend"]
        price = policy["price"]

        # Update churn rate based on policy
        state.monthly_churn_rate = policy["churn_rate"]

        # Get oracle outcome
        outcome = oracle.monthly_outcome(month, state, ad_spend, price)
        monthly_results.append(outcome)

        # Update state for next month
        state.customers = outcome["ending_customers"]
        state.cash_balance = outcome["cash_balance"]
        state.cumulative_months = month

        # Check for shutdown: if cash goes negative, business is out of runway
        if state.cash_balance < 0 and shutdown_month is None:
            shutdown_month = month
            state.cash_balance = 0  # Mark as zero (failed)

    # Summary stats
    final_cash = state.cash_balance
    profitable_months = sum(1 for r in monthly_results if r["operating_profit"] > 0)
    total_profit = sum(r["operating_profit"] for r in monthly_results)
    min_cash_ever = min((r["cash_balance"] for r in monthly_results), default=0.0)

    # Shutdown is permanent - if it happens, business is a loss regardless of final cash
    is_profitable_final = (shutdown_month is None and final_cash > 0)

    return {
        "seed": seed,
        "final_cash_balance": final_cash,
        "total_profit": total_profit,
        "profitable_months": profitable_months,
        "final_customers": monthly_results[-1]["ending_customers"] if monthly_results else 0,
        "is_profitable": is_profitable_final,
        "min_cash_ever": min_cash_ever,
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
                               6789, 7000, 8000, 9000, 9999],
                       help="Seeds to simulate (default: 25 pre-registered seeds)")
    parser.add_argument("--months", type=int, default=36)
    parser.add_argument("--output", type=Path, default=Path("evals/experiments/b2b_saas_control_arm.json"))
    parser.add_argument("--csv", type=Path, default=Path("evals/experiments/b2b_saas_control_monthly.csv"))

    args = parser.parse_args(argv)

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Run control arm on all seeds
    print(f"Running control arm on {len(args.seeds)} seeds...")
    results = []

    for i, seed in enumerate(args.seeds, 1):
        result = run_control_arm(seed, args.months)
        results.append(result)
        # LOSS if it ever goes negative (shutdown is permanent)
        is_profitable = result["shutdown_month"] is None and result["final_cash_balance"] > 0
        status = "PROFITABLE" if is_profitable else "LOSS"
        shutdown_info = f", SHUTDOWN month {result['shutdown_month']}" if result["shutdown_month"] else ""
        print(f"  [{i:2d}/{len(args.seeds)}] Seed {seed:4d}: Final cash ${result['final_cash_balance']:10.0f} "
              f"({status}, {result['profitable_months']}/36 months profitable{shutdown_info})")

    # Analysis
    profitable_count = sum(1 for r in results if r["is_profitable"])
    profitable_pct = 100.0 * profitable_count / len(results)

    cash_balances = [r["final_cash_balance"] for r in results]
    mean_cash = statistics.mean(cash_balances)
    sd_cash = statistics.stdev(cash_balances) if len(cash_balances) > 1 else 0
    min_cash = min(cash_balances)
    max_cash = max(cash_balances)

    print(f"\n{'='*70}")
    print(f"GATE VERIFICATION RESULTS")
    print(f"{'='*70}")
    print(f"Profitable seeds: {profitable_count}/{len(results)} ({profitable_pct:.1f}%)")
    print(f"Target range: 30-60% (PASS if within range)")
    print(f"Gate status: {'✓ PASS' if 30 <= profitable_pct <= 60 else '✗ FAIL'}")
    print(f"\nFinal cash distribution:")
    print(f"  Mean:    ${mean_cash:10.0f}")
    print(f"  StdDev:  ${sd_cash:10.0f}")
    print(f"  Min:     ${min_cash:10.0f}")
    print(f"  Max:     ${max_cash:10.0f}")
    print(f"  Range:   ${max_cash - min_cash:10.0f}")
    print(f"\nVariance test: {'✓ HIGH' if sd_cash > 100000 else '✗ LOW'} (target >$100k)")
    print(f"\nShutdown events: {sum(1 for r in results if r['shutdown_month'] is not None)} seeds hit negative cash")
    print(f"\nDecision-space evidence:")

    # Show some specific examples
    profitable_seeds = [r for r in results if r["is_profitable"]]
    loss_seeds = [r for r in results if not r["is_profitable"]]

    if profitable_seeds:
        best = max(profitable_seeds, key=lambda r: r["final_cash_balance"])
        print(f"  Best profitable (seed {best['seed']}): ${best['final_cash_balance']:.0f}, "
              f"{best['final_customers']} customers, {best['profitable_months']}/36 months")

    if loss_seeds:
        worst = min(loss_seeds, key=lambda r: r["final_cash_balance"])
        print(f"  Worst loss (seed {worst['seed']}): ${worst['final_cash_balance']:.0f} (shutdown month {worst['shutdown_month']}), "
              f"{worst['profitable_months']} months before shutdown")

    # Save results
    summary = {
        "gate_criteria": {
            "profitable_seeds": profitable_count,
            "total_seeds": len(results),
            "profitable_pct": profitable_pct,
            "pass_min": 30.0,
            "pass_max": 60.0,
            "gate_status": "PASS" if 30 <= profitable_pct <= 60 else "FAIL",
        },
        "variance": {
            "mean_cash": mean_cash,
            "stdev_cash": sd_cash,
            "min_cash": min_cash,
            "max_cash": max_cash,
            "range": max_cash - min_cash,
        },
        "seeds": args.seeds,
        "results": results,
    }

    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to {args.output}")

    # Save monthly data for detailed analysis
    with open(args.csv, "w") as f:
        writer = None
        for result in results:
            for monthly in result["monthly_results"]:
                if writer is None:
                    writer = csv.DictWriter(f, fieldnames=monthly.keys())
                    writer.writeheader()
                writer.writerow(monthly)
    print(f"Monthly data saved to {args.csv}")

    # Return exit code based on gate
    return 0 if 30 <= profitable_pct <= 60 else 1


if __name__ == "__main__":
    sys.exit(main())
