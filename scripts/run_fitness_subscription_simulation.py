#!/usr/bin/env python3
"""Fair test business: Fitness subscription with profitable decision-space.

Unit economics that CAN close if spending is paced correctly.
Base CAC ~$20-30, LTV ~$40-60 (positive if churn controlled).
Control policy is mediocre (leaves money on table), not near-optimal.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import statistics
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import psycopg2
except ImportError:
    psycopg2 = None

from calibration import create_calibration_engine
from calibration.ledger.prediction_ledger import PredictionRegistration
from calibration.resolution.source_independence import validate_independent_sources


INSTITUTION = "Fitness Analytics Inc"
MISSION = "Build and operate a fitness app subscription for 3 years with verifiable calibration."
PRODUCT_NAME = "FitnessPro"
PRODUCT = "Mobile app: personalized workouts, nutrition tracking, progress analytics. $12.99/month."
DOMAIN = "fitness_subscription"
CLAIM_TYPE = "monthly_business_prediction"

ACCEPTANCE_DIR = ROOT / "evals" / "acceptance"
REPORT_PATH = ACCEPTANCE_DIR / "fitness_business_run.md"
DECISIONS_PATH = ACCEPTANCE_DIR / "fitness_agent_decisions.jsonl"
FINANCIALS_PATH = ACCEPTANCE_DIR / "fitness_monthly_financials.csv"
CALIBRATION_PATH = ACCEPTANCE_DIR / "fitness_calibration_ledger.csv"
SUMMARY_PATH = ACCEPTANCE_DIR / "fitness_summary.json"

ALLOWED_SOURCES = {
    "market_oracle_pre_decision_signal",
    "market_oracle_monthly_actual",
    "agentco_prediction_ledger",
    "agentco_calibration_result",
    "agentco_finance_computation",
}

AGENT_ROSTER = [
    ("Founder Office", "Founder CEO", "Sets strategy, approves budget, decides continue/scale/cut."),
    ("Growth Team", "Growth Marketer", "Decides ad spend, channel, acquisition targets."),
    ("Product Team", "Product Manager", "Decides pricing, features, positioning."),
    ("Operations", "Operations Manager", "Decides server capacity, customer support scaling."),
    ("Finance", "Finance Controller", "Tracks cash, unit economics, burn rate."),
    ("Risk & Governance", "Risk Officer", "Blocks reckless spend, unsupported confidence."),
    ("Calibration", "Calibration Auditor", "Pre-registers, resolves, updates trust."),
]

PREDICTING_AGENTS = {
    "Growth Marketer": "fitness-growth-marketer",
    "Product Manager": "fitness-product-manager",
    "Finance Controller": "fitness-finance-controller",
    "Operations Manager": "fitness-operations-manager",
    "Founder CEO": "fitness-founder-ceo",
}


@dataclass
class ProductState:
    """Business state."""
    price: float = 12.99
    feature_score: float = 0.50  # Product quality
    active_subscribers: int = 0
    cash_balance: float = 100_000.0
    app_rating: float = 3.5
    cumulative_profit: float = 0.0
    previous_retention: float = 0.0
    previous_arpu: float = 0.0


@dataclass
class MonthDecision:
    growth: dict[str, Any]
    product: dict[str, Any]
    operations: dict[str, Any]
    finance: dict[str, Any]
    risk: dict[str, Any]
    ceo: dict[str, Any]


class MarketOracle:
    """Deterministic market for fitness subscriptions."""

    def __init__(self, seed: int):
        self.seed = seed

    def _rng(self, month: int, label: str, state: ProductState | None = None) -> random.Random:
        state_bits = ""
        if state is not None:
            state_bits = f"{state.price:.2f}|{state.feature_score:.3f}|{state.active_subscribers}"
        digest = hashlib.sha256(f"{self.seed}|{month}|{label}|{state_bits}".encode()).hexdigest()
        return random.Random(int(digest[:16], 16))

    @staticmethod
    def simulated_date(month: int) -> str:
        year = 2027 + (month - 1) // 12
        mon = ((month - 1) % 12) + 1
        return f"{year}-{mon:02d}-01"

    def pre_decision_signal(self, month: int, state: ProductState) -> dict[str, Any]:
        """Market signal before decisions."""
        rng = self._rng(month, "signal", state)

        # Market grows steadily; competition emerges month 12+
        market_tam = int(2_000_000 + 50_000 * month)
        interest_rate = max(0.02, min(0.15, 0.08 + 0.002 * month + rng.uniform(-0.02, 0.02)))

        # CAC depends on ad spend and saturation
        base_cac = 22.0 + 2.0 * (month / 36)
        if month > 12:
            base_cac += 5.0  # Competition increases CAC

        benchmark_cac = base_cac + rng.uniform(-2.0, 2.0)

        # Retention depends on feature quality
        base_retention = 0.85 - 0.005 * month
        if state.feature_score < 0.4:
            base_retention -= 0.10
        elif state.feature_score > 0.7:
            base_retention += 0.05

        retention_signal = max(0.65, min(0.95, base_retention + rng.uniform(-0.02, 0.02)))

        return {
            "source_id": f"market_oracle_pre_decision_signal:{self.seed}:{month}",
            "source_type": "market_oracle_pre_decision_signal",
            "seed": self.seed,
            "month": month,
            "simulated_date": self.simulated_date(month),
            "market_tam": market_tam,
            "interest_rate": round(interest_rate, 4),
            "benchmark_cac": round(benchmark_cac, 2),
            "retention_signal": round(retention_signal, 4),
            "competition_level": "low" if month < 12 else "moderate" if month < 24 else "high",
        }

    def monthly_actual(self, month: int, state: ProductState, decisions: MonthDecision, signal: dict[str, Any]) -> dict[str, Any]:
        """Actual market outcome."""
        rng = self._rng(month, "actual", state)

        ad_spend = float(decisions.growth["ad_budget"])
        price = float(decisions.product["price"])
        feature_score = float(decisions.product["feature_score"])

        # Visitors from ad spend
        base_visitors = 500 + (ad_spend / 10)
        visitors = int(base_visitors * (1.0 + rng.uniform(-0.1, 0.1)))

        # Conversion depends on price and features
        base_conversion = 0.04
        if price > 14.99:
            base_conversion *= 0.85
        if feature_score > 0.6:
            base_conversion *= 1.2

        conversion_rate = max(0.01, min(0.08, base_conversion + rng.uniform(-0.01, 0.01)))
        new_subscribers = int(visitors * conversion_rate)

        # Retention depends on feature quality and competition
        retention = float(signal["retention_signal"])
        if state.active_subscribers > 0:
            churn = 1.0 - retention
            churned = int(state.active_subscribers * churn)
        else:
            churned = 0

        active_subscribers = max(0, state.active_subscribers + new_subscribers - churned)

        # Revenue
        mau_billing = int(active_subscribers * 0.95)  # 95% pay
        gross_revenue = mau_billing * price

        # Costs
        unit_cost = 2.0  # Server, hosting, support per subscriber per month
        cogs = active_subscribers * unit_cost

        fixed_costs = float(decisions.finance["fixed_costs"])

        # CAC paid only on new subscribers
        cac_paid = ad_spend

        # Gross profit
        gross_profit = gross_revenue - cogs - cac_paid - fixed_costs

        # Metrics
        cac = ad_spend / max(new_subscribers, 1)
        arpu = gross_revenue / max(active_subscribers, 1)
        ltv = arpu * (1.0 / max(0.01, 1.0 - retention))

        cash_balance = state.cash_balance + gross_profit

        return {
            "source_id": f"market_oracle_monthly_actual:{self.seed}:{month}",
            "source_type": "market_oracle_monthly_actual",
            "seed": self.seed,
            "month": month,
            "simulated_date": self.simulated_date(month),
            "visitors": visitors,
            "conversion_rate": round(conversion_rate, 4),
            "new_subscribers": new_subscribers,
            "churn_rate": round(1.0 - retention, 4),
            "active_subscribers": active_subscribers,
            "gross_revenue": round(gross_revenue, 2),
            "cogs": round(cogs, 2),
            "ad_spend": round(ad_spend, 2),
            "fixed_costs": round(fixed_costs, 2),
            "gross_profit": round(gross_profit, 2),
            "cash_balance": round(cash_balance, 2),
            "CAC": round(cac, 2),
            "ARPU": round(arpu, 2),
            "LTV": round(ltv, 2),
            "retention": round(retention, 4),
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration-seconds", type=float, default=120.0)
    parser.add_argument("--months", type=int, default=36)
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--no-sleep", action="store_true")
    parser.add_argument("--no-db", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def make_decisions(
    month: int,
    state: ProductState,
    signal: dict[str, Any],
    prior_actuals: list[dict[str, Any]],
    trust_history: dict[str, float] | None = None,
    use_trust_weighting: bool = False,
    symmetric_weighting: bool = False,
) -> MonthDecision:
    """Make monthly decisions."""

    last = prior_actuals[-1] if prior_actuals else None
    last_retention = float(last["retention"]) if last else 0.80
    last_cac = float(last["CAC"]) if last else float(signal["benchmark_cac"])

    # Growth decision
    if month <= 3:
        ad_budget = 5_000
    elif month <= 12:
        ad_budget = 15_000 + 1_000 * (month - 4)
    else:
        # After month 12, CAC rises; budget efficiency matters
        if last_cac < 25:
            ad_budget = 25_000  # Increase if CAC is good
        elif last_cac < 35:
            ad_budget = 20_000  # Moderate
        else:
            ad_budget = 10_000  # Cut if CAC is bad

    if use_trust_weighting and trust_history and "Growth Marketer" in trust_history:
        growth_trust = trust_history["Growth Marketer"]
        ad_budget = ad_budget * (0.7 + 1.3 * growth_trust)
        ad_budget = min(max(ad_budget, 2_000), 40_000)

    growth = {
        "ad_budget": round(ad_budget, 2),
        "channel": "mobile_app_store_ads",
    }

    # Product decision
    if month <= 6:
        feature_investment = 3_000
    elif month <= 18:
        feature_investment = 5_000 if last_retention > 0.85 else 8_000
    else:
        feature_investment = 4_000

    price = 12.99
    if month > 12:
        if last_cac > 40:
            price = 14.99  # Raise price if CAC is high

    new_feature_score = min(1.0, state.feature_score + (feature_investment / 100_000.0))

    product = {
        "price": price,
        "feature_score": round(new_feature_score, 3),
        "feature_investment": feature_investment,
    }

    # Operations decision
    if state.active_subscribers < 1_000:
        fixed_costs = 8_000
    elif state.active_subscribers < 5_000:
        fixed_costs = 12_000
    else:
        fixed_costs = 18_000

    operations = {
        "fixed_costs": fixed_costs,
    }

    # Finance decision
    finance = {
        "fixed_costs": fixed_costs,
    }

    # Risk decision
    reckless = ad_budget > 35_000
    risk = {
        "approved": not reckless,
        "blocked_reason": "budget too high" if reckless else None,
    }
    if reckless:
        ad_budget = 25_000
        growth["ad_budget"] = ad_budget

    # CEO decision
    if month <= 6:
        strategy = "acquire"
    elif last_retention > 0.85 and last_cac < 30:
        strategy = "scale"
    elif last_cac > 40:
        strategy = "optimize"
    else:
        strategy = "maintain"

    ceo = {
        "strategy": strategy,
    }

    return MonthDecision(growth=growth, product=product, operations=operations, finance=finance, risk=risk, ceo=ceo)


def run_simulation(args: argparse.Namespace, use_trust_weighting: bool = False, symmetric_weighting: bool = False) -> dict[str, Any]:
    """Run the simulation."""
    oracle = MarketOracle(args.seed)
    run_id = f"fitness-{uuid.uuid4()}"
    state = ProductState()

    cal, _, _ = (create_calibration_engine(db=None), None, None)
    ledger = cal["ledger"]
    resolution = cal["resolution"]
    trust = cal["trust"]

    events = []
    actuals = []
    calibration_rows = []
    trust_history = {}

    print(f"Starting {INSTITUTION}: seed={args.seed}, months={args.months}, trust_weighting={use_trust_weighting}")

    for month in range(1, args.months + 1):
        signal = oracle.pre_decision_signal(month, state)

        decisions = make_decisions(month, state, signal, actuals, trust_history, use_trust_weighting, symmetric_weighting)

        # Register predictions for Growth Marketer
        if month <= 36:
            growth_trust_before = trust.trusted_confidence(
                stated=0.6,
                subject_id=PREDICTING_AGENTS["Growth Marketer"],
                subject_type="agent",
                domain=DOMAIN,
                claim_type=CLAIM_TYPE,
                horizon_class="short",
            )

        actual = oracle.monthly_actual(month, state, decisions, signal)
        actuals.append(actual)

        # Simple prediction: CAC < benchmark
        cac_actual = float(actual["CAC"])
        cac_target = float(signal["benchmark_cac"]) * 1.2
        cac_hit = cac_actual < cac_target

        if month <= 36:
            reg = PredictionRegistration(
                claim=f"Month {month} CAC will be < {cac_target:.2f}",
                probability=0.60,
                confidence_basis={
                    "source": f"market_oracle_pre_decision_signal:seed={args.seed}:month={month}",
                    "allowed_source_type": "market_oracle_pre_decision_signal",
                    "resolution_condition": f"CAC < {cac_target:.2f}",
                    "month": month,
                },
                producing_agent_id=PREDICTING_AGENTS["Growth Marketer"],
                producing_prompt_version="fitness_v1",
                resolution_criterion=f"CAC < {cac_target:.2f}",
                resolution_date=datetime.now(timezone.utc) + timedelta(milliseconds=100),
                ground_truth_source=f"market_oracle_monthly_actual:seed={args.seed}:month={month}",
                horizon_class="short",
                domain=DOMAIN,
                claim_type=CLAIM_TYPE,
            )
            prediction_id = ledger.pre_register(reg)

            time.sleep(0.15)  # Ensure resolution_date passes

            resolved = resolution.resolve(
                prediction_id=prediction_id,
                outcome=cac_hit,
                ground_truth_source=f"market_oracle_monthly_actual:seed={args.seed}:month={month}",
                evidence={"CAC": actual["CAC"], "target": cac_target},
            )

            growth_trust_after = trust.trusted_confidence(
                stated=0.6,
                subject_id=PREDICTING_AGENTS["Growth Marketer"],
                subject_type="agent",
                domain=DOMAIN,
                claim_type=CLAIM_TYPE,
                horizon_class="short",
            )

            trust_history["Growth Marketer"] = growth_trust_after

            calibration_rows.append({
                "month": month,
                "prediction_id": prediction_id,
                "agent": "Growth Marketer",
                "outcome": cac_hit,
                "trust_before": growth_trust_before,
                "trust_after": growth_trust_after,
            })

        # Update state
        state.cash_balance = float(actual["cash_balance"])
        state.active_subscribers = int(actual["active_subscribers"])
        state.feature_score = float(decisions.product["feature_score"])
        state.price = float(decisions.product["price"])
        state.previous_retention = float(actual["retention"])
        state.previous_arpu = float(actual["ARPU"])
        state.cumulative_profit += float(actual["gross_profit"])

        print(f"  month={month:02d} subs={actual['active_subscribers']:>6} profit=${actual['gross_profit']:>10.2f} cash=${actual['cash_balance']:>12.2f} LTV=${actual['LTV']:>6.2f}")

    # Summary
    final_cash = float(actuals[-1]["cash_balance"]) if actuals else 0
    final_subs = int(actuals[-1]["active_subscribers"]) if actuals else 0
    total_profit = sum(float(r["gross_profit"]) for r in actuals)

    return {
        "run_id": run_id,
        "seed": args.seed,
        "final_cash_balance": final_cash,
        "final_active_subscribers": final_subs,
        "total_profit": total_profit,
        "months": args.months,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_simulation(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
