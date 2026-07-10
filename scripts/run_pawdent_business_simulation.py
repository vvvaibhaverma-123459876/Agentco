#!/usr/bin/env python3
"""Run a deterministic accelerated PawDent business simulation."""
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
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import psycopg2
except ImportError:  # pragma: no cover - only exercised in incomplete envs
    psycopg2 = None

from calibration import create_calibration_engine
from calibration.ledger.prediction_ledger import PredictionRegistration
from calibration.resolution.source_independence import (
    CircularResolutionError,
    validate_independent_sources,
)


INSTITUTION = "Pet Care Venture Institution"
MISSION = "Launch and operate PawDent for 3 simulated years while improving decisions through verifiable calibration."
PRODUCT_NAME = "PawDent"
PRODUCT = "Monthly dog dental-care kit with dental chews, brushing wipes, breath strips, and a mobile reminder/tracking experience."
DOMAIN = "pet_care_subscription"
CLAIM_TYPE = "monthly_business_prediction"

ACCEPTANCE_DIR = Path(os.environ.get("AGENTCO_ACCEPTANCE_DIR", ROOT / "evals" / "acceptance"))
REPORT_PATH = ACCEPTANCE_DIR / "pawdent_business_run.md"
DECISIONS_PATH = ACCEPTANCE_DIR / "pawdent_agent_decisions.jsonl"
FINANCIALS_PATH = ACCEPTANCE_DIR / "pawdent_monthly_financials.csv"
CALIBRATION_PATH = ACCEPTANCE_DIR / "pawdent_calibration_ledger.csv"
SUMMARY_PATH = ACCEPTANCE_DIR / "pawdent_summary.json"

ALLOWED_SOURCES = {
    "market_oracle_pre_decision_signal",
    "market_oracle_monthly_actual",
    "agentco_prediction_ledger",
    "agentco_calibration_result",
    "agentco_finance_computation",
}

AGENT_ROSTER = [
    ("Founder Office", "Founder CEO", "Sets strategy, approves pivots, and decides whether to continue, raise, cut, or shut down."),
    ("Market Intelligence Team", "Market Research Agent", "Requests market studies and identifies customer segments."),
    ("Product Team", "Product Manager", "Chooses bundle, roadmap, packaging, and customer promises."),
    ("Growth Team", "Growth Marketer", "Chooses channels, creative angle, ad budget, and acquisition targets."),
    ("Growth Team", "Sales & Partnerships Agent", "Chooses vet clinics, groomers, pet stores, or D2C focus."),
    ("Operations Team", "Operations Manager", "Chooses inventory, suppliers, buffers, fulfillment capacity, and quality controls."),
    ("Finance Team", "Finance Controller", "Tracks cash, runway, unit economics, margin, burn, and funding need."),
    ("Risk & Governance Team", "Risk Officer", "Blocks circular verification, unsupported confidence, reckless spend, and low-trust decisions."),
    ("Calibration Office", "Calibration Auditor", "Pre-registers predictions, resolves them, and updates trust."),
    ("Learning Office", "Learning Agent", "Extracts lessons and changes operating policy."),
]

PREDICTING_AGENTS = {
    "Growth Marketer": "pawdent-growth-marketer",
    "Product Manager": "pawdent-product-manager",
    "Finance Controller": "pawdent-finance-controller",
    "Operations Manager": "pawdent-operations-manager",
    "Founder CEO": "pawdent-founder-ceo",
}


@dataclass
class ProductState:
    price: float = 29.0
    quality_score: float = 0.58
    reminder_score: float = 0.35
    packaging_score: float = 0.45
    promise: str = "easy preventive dental routine"
    supplier_reliability: float = 0.74
    active_subscribers: int = 0
    cash_balance: float = 250_000.0
    vet_partnerships: int = 0
    groomer_partnerships: int = 0
    pet_store_partnerships: int = 0
    operating_policy: str = "pilot carefully, cap spend until conversion and retention are resolved"
    cumulative_profit: float = 0.0
    previous_health_score: float = 0.0
    previous_nps: float = 0.0


@dataclass
class MonthDecision:
    product: dict[str, Any]
    pricing: dict[str, Any]
    growth: dict[str, Any]
    partnership: dict[str, Any]
    operations: dict[str, Any]
    finance: dict[str, Any]
    risk: dict[str, Any]
    ceo: dict[str, Any]


@dataclass
class ClaimSpec:
    agent: str
    team: str
    claim: str
    confidence: float
    claim_source: str
    resolution_source: str
    resolution_condition: str
    expected: float
    kind: str


class MarketOracle:
    """Deterministic synthetic market reality engine for PawDent."""

    def __init__(self, seed: int):
        self.seed = seed

    def _rng(self, month: int, label: str, product_state: ProductState | None = None) -> random.Random:
        state_bits = ""
        if product_state is not None:
            state_bits = f"{product_state.price:.2f}|{product_state.quality_score:.3f}|{product_state.supplier_reliability:.3f}|{product_state.active_subscribers}|{product_state.cash_balance:.2f}"
        digest = hashlib.sha256(f"{self.seed}|{month}|{label}|{state_bits}".encode()).hexdigest()
        return random.Random(int(digest[:16], 16))

    @staticmethod
    def simulated_date(month: int) -> str:
        year = 2027 + (month - 1) // 12
        mon = ((month - 1) % 12) + 1
        return f"{year}-{mon:02d}-01"

    def pre_decision_signal(self, month: int, product_state: ProductState) -> dict[str, Any]:
        rng = self._rng(month, "pre_signal", product_state)
        seasonality = 1.0 + 0.10 * math.sin((month - 2) / 12.0 * 2.0 * math.pi)
        competitor_pressure = 0.10 if month < 15 else min(0.42, 0.15 + 0.012 * (month - 15))
        macro_shock_state = "normal"
        if month in {17, 18, 19}:
            macro_shock_state = "household_budget_pressure"
        elif month in {28, 29}:
            macro_shock_state = "shipping_cost_spike"

        market_size = int((185_000 + 1700 * month) * seasonality * (1.0 + rng.uniform(-0.025, 0.025)))
        survey_interest = round(max(0.05, min(0.72, 0.22 + 0.25 * product_state.quality_score - 0.004 * (product_state.price - 29) + rng.uniform(-0.035, 0.035))), 4)
        benchmark_cac = round(22 + 18 * competitor_pressure + rng.uniform(-2.5, 2.5), 2)
        supply_quote_unit_cost = round(8.8 + 3.5 * product_state.quality_score + (1.0 if macro_shock_state == "shipping_cost_spike" else 0.0) + rng.uniform(-0.35, 0.35), 2)
        willingness_to_pay = {
            "preventive_health": round(31 + 9 * product_state.quality_score + rng.uniform(-1.5, 1.5), 2),
            "convenience_seekers": round(25 + 5 * product_state.reminder_score + rng.uniform(-1.2, 1.2), 2),
            "price_sensitive": round(18 + rng.uniform(-1.0, 1.0), 2),
        }
        segments = {
            "preventive_health": round(0.38 + 0.04 * math.sin(month / 6), 4),
            "convenience_seekers": round(0.34 + 0.03 * math.cos(month / 5), 4),
            "price_sensitive": round(0.28 - 0.02 * math.sin(month / 6), 4),
        }
        signal = {
            "source_id": f"market_oracle_pre_decision_signal:{self.seed}:{month}",
            "source_type": "market_oracle_pre_decision_signal",
            "seed": self.seed,
            "month": month,
            "simulated_date": self.simulated_date(month),
            "market_size": market_size,
            "customer_segments": segments,
            "willingness_to_pay": willingness_to_pay,
            "survey_sample": {
                "n": 220 + month * 3,
                "interest_rate": survey_interest,
                "top_objection": "does my dog accept the routine" if product_state.quality_score < 0.7 else "price for monthly replenishment",
            },
            "customer_interview_snippets": [
                "I know brushing matters but I forget after the first week.",
                "A vet-endorsed routine would make me more likely to try it.",
                "I need the kit to be easier than a toothbrush battle.",
            ],
            "channel_benchmark_sample": {
                "d2c_paid_social_cac": benchmark_cac,
                "search_cac": round(benchmark_cac * 1.18, 2),
                "vet_referral_cac": round(benchmark_cac * 0.72, 2),
            },
            "supply_quote_sample": {
                "unit_cost": supply_quote_unit_cost,
                "lead_time_days": 21 + int(8 * (1.0 - product_state.supplier_reliability)),
            },
            "competitor_rumor_or_public_signal": "national pet brand testing dental bundle" if month >= 15 else "fragmented dental treat aisle with no routine-led subscription leader",
            "competitor_pressure": round(competitor_pressure, 4),
            "seasonality": round(seasonality, 4),
            "supply_reliability": round(product_state.supplier_reliability, 4),
            "macro_shock_state": macro_shock_state,
        }
        signal["market_state_hash"] = self._hash(signal)
        return signal

    def monthly_actual(self, month: int, product_state: ProductState, decisions: MonthDecision, signal: dict[str, Any]) -> dict[str, Any]:
        rng = self._rng(month, "actual", product_state)
        price = float(decisions.pricing["price"])
        ad_spend = float(decisions.growth["ad_budget"])
        quality = float(product_state.quality_score)
        competitor_pressure = float(signal["competitor_pressure"])
        seasonality = float(signal["seasonality"])
        macro = signal["macro_shock_state"]

        channel = decisions.growth["primary_channel"]
        channel_factor = {"paid_social": 1.0, "search": 0.85, "vet_referral": 0.62, "content": 0.45}[channel]
        partnership_lift = 1.0 + 0.018 * product_state.vet_partnerships + 0.010 * product_state.groomer_partnerships + 0.006 * product_state.pet_store_partnerships
        price_drag = max(0.42, 1.0 - max(price - 29.0, 0.0) * 0.025)
        quality_lift = 0.70 + quality * 0.62 + product_state.reminder_score * 0.18
        macro_drag = 0.90 if macro == "household_budget_pressure" else 1.0
        visitors = int((ad_spend / 2.4 + 900 * channel_factor) * seasonality * partnership_lift * macro_drag * (1.0 + rng.uniform(-0.08, 0.08)))
        visitors = max(0, visitors)

        conversion_rate = max(0.004, min(0.18, (0.018 + 0.045 * quality + 0.020 * product_state.reminder_score) * price_drag * (1.0 - 0.45 * competitor_pressure) * (1.0 + rng.uniform(-0.12, 0.12))))
        trial_orders = int(visitors * conversion_rate)
        paid_subscribers = int(trial_orders * (0.68 + 0.18 * quality + rng.uniform(-0.035, 0.035)))
        churn_rate = max(0.025, min(0.22, 0.145 - 0.07 * quality - 0.025 * product_state.reminder_score + 0.055 * competitor_pressure - 0.006 * product_state.vet_partnerships + rng.uniform(-0.012, 0.012)))
        churned_subscribers = int(product_state.active_subscribers * churn_rate)
        active_subscribers = max(0, product_state.active_subscribers + paid_subscribers - churned_subscribers)

        available_units = int(decisions.operations["inventory_units"])
        demand_units = product_state.active_subscribers + paid_subscribers
        stockout_units = max(0, demand_units - available_units)
        stockout_rate = round(stockout_units / demand_units, 4) if demand_units else 0.0
        stockout_risk = min(0.95, stockout_rate + max(0.0, 0.12 - product_state.supplier_reliability * 0.08))

        served_subscriptions = max(0, demand_units - stockout_units)
        refund_rate = max(0.004, min(0.14, 0.075 - 0.055 * quality + 0.045 * stockout_rate + rng.uniform(-0.008, 0.008)))
        refunds = int(served_subscriptions * refund_rate)
        nps = int(max(-20, min(78, 8 + 72 * quality + 12 * product_state.reminder_score - 55 * stockout_rate - 38 * refund_rate - 12 * competitor_pressure + rng.uniform(-5, 5))))
        support_tickets = int(served_subscriptions * max(0.015, 0.08 - 0.04 * quality + 0.05 * stockout_rate + rng.uniform(-0.006, 0.006)))
        repeat_purchase_rate = round(max(0.10, min(0.92, 0.45 + 0.38 * quality + 0.08 * product_state.reminder_score - 0.20 * refund_rate - 0.10 * stockout_rate)), 4)

        unit_cost = float(signal["supply_quote_sample"]["unit_cost"]) + float(decisions.product["quality_investment"]) * 0.0009
        shipping_cost = 4.4 + (1.2 if macro == "shipping_cost_spike" else 0.0) + rng.uniform(-0.25, 0.25)
        gross_revenue = served_subscriptions * price
        refund_dollars = refunds * price
        cogs = served_subscriptions * unit_cost
        shipping_total = served_subscriptions * shipping_cost
        support_cost = support_tickets * 5.25
        operating_cost = float(decisions.finance["fixed_operating_cost"])
        gross_margin = gross_revenue - refund_dollars - cogs - shipping_total
        operating_profit = gross_margin - ad_spend - support_cost - operating_cost
        cash_balance = product_state.cash_balance + operating_profit
        cac = round(ad_spend / paid_subscribers, 2) if paid_subscribers else round(ad_spend, 2)
        arpu = round(price * (1.0 - refund_rate), 2)
        ltv_estimate = round(arpu * max(1.0, (1.0 / max(churn_rate, 0.01))) * max(0.0, (price - unit_cost - shipping_cost) / price), 2)
        health_score = round(0.35 * min(cash_balance / 250_000.0, 1.4) + 0.25 * min(active_subscribers / 4500.0, 1.2) + 0.20 * max(0.0, nps / 70.0) + 0.20 * (1.0 if operating_profit > 0 else 0.35), 4)

        actual = {
            "source_id": f"market_oracle_monthly_actual:{self.seed}:{month}",
            "source_type": "market_oracle_monthly_actual",
            "seed": self.seed,
            "month": month,
            "simulated_date": self.simulated_date(month),
            "market_size": signal["market_size"],
            "customer_segments": signal["customer_segments"],
            "willingness_to_pay": signal["willingness_to_pay"],
            "conversion_rate": round(conversion_rate, 4),
            "CAC_by_channel": {
                channel: cac,
                "paid_social": round(cac * (1.0 if channel == "paid_social" else 1.16), 2),
                "search": round(cac * (1.0 if channel == "search" else 1.24), 2),
                "vet_referral": round(cac * (1.0 if channel == "vet_referral" else 0.74), 2),
            },
            "churn": round(churn_rate, 4),
            "refunds": refunds,
            "support_tickets": support_tickets,
            "NPS": nps,
            "repeat_purchase_rate": repeat_purchase_rate,
            "unit_cost": round(unit_cost, 2),
            "shipping_cost": round(shipping_cost, 2),
            "stockout_risk": round(stockout_risk, 4),
            "competitor_events": "competitor launched dental subscription discount" if month in {16, 17, 24} else "no major new public competitor event",
            "visitors": visitors,
            "leads": int(visitors * 0.24),
            "trial_orders": trial_orders,
            "paid_subscribers": paid_subscribers,
            "active_subscribers": active_subscribers,
            "churned_subscribers": churned_subscribers,
            "price": round(price, 2),
            "gross_revenue": round(gross_revenue, 2),
            "COGS": round(cogs, 2),
            "shipping_total": round(shipping_total, 2),
            "ad_spend": round(ad_spend, 2),
            "support_cost": round(support_cost, 2),
            "refund_dollars": round(refund_dollars, 2),
            "gross_margin": round(gross_margin, 2),
            "operating_profit": round(operating_profit, 2),
            "net_profit_loss": round(operating_profit, 2),
            "cash_balance": round(cash_balance, 2),
            "CAC": cac,
            "LTV_estimate": ltv_estimate,
            "ARPU": arpu,
            "stockout_rate": stockout_rate,
            "refund_rate": round(refund_rate, 4),
            "health_score": health_score,
            "macro_shock_state": macro,
            "competitor_pressure": round(competitor_pressure, 4),
            "seasonality": round(seasonality, 4),
            "supply_reliability": round(product_state.supplier_reliability, 4),
        }
        actual["market_state_hash"] = self._hash(actual)
        return actual

    @staticmethod
    def _hash(payload: dict[str, Any]) -> str:
        clean = {k: v for k, v in payload.items() if k != "market_state_hash"}
        return hashlib.sha256(json.dumps(clean, sort_keys=True, default=str).encode()).hexdigest()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration-seconds", type=float, default=300.0)
    parser.add_argument("--months", type=int, default=36)
    parser.add_argument("--seed", type=int, default=7319)
    parser.add_argument("--no-sleep", action="store_true")
    parser.add_argument("--no-db", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def resolution_dsn(db_url: str) -> str:
    parsed = urlparse(db_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    db = parsed.path.lstrip("/") or "agentco"
    password = os.environ.get("RESOLUTION_SERVICE_PASSWORD")
    if not password:
        if os.environ.get("AGENTCO_ENV") == "production":
            raise RuntimeError("RESOLUTION_SERVICE_PASSWORD must be set in production")
        password = "resolution-service-dev-password"
    return f"postgresql://resolution_service:{quote(password, safe='')}@{host}:{port}/{db}"


def phase_for_month(month: int) -> str:
    if month <= 3:
        return "idea exploration and customer discovery"
    if month <= 6:
        return "MVP design and pilot"
    if month <= 12:
        return "public launch and early growth"
    if month <= 24:
        return "scaling, retention, partnerships, and product iterations"
    return "maturity, competition, survival, expansion, or shutdown"


def source(source_type: str, detail: str) -> str:
    if source_type not in ALLOWED_SOURCES:
        raise ValueError(f"unsupported source type: {source_type}")
    return f"{source_type}:{detail}"


def event(
    *,
    run_id: str,
    seed: int,
    month: int,
    simulated_date: str,
    team: str,
    agent: str,
    role: str,
    call_type: str,
    input_sources: list[str],
    decision: dict[str, Any],
    confidence: float | None,
    prediction_id: str | None,
    claim_source: str | None,
    resolution_source: str | None,
    actual_outcome: Any,
    trust_before: float | None,
    trust_after: float | None,
    business_impact: dict[str, Any] | None,
    rationale: str,
    blocked_by_risk_officer: bool = False,
    circular_verification_flag: bool = False,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "seed": seed,
        "month": month,
        "simulated_date": simulated_date,
        "institution": INSTITUTION,
        "team": team,
        "agent": agent,
        "role": role,
        "call_type": call_type,
        "input_sources": input_sources,
        "decision": decision,
        "confidence": confidence,
        "prediction_id": prediction_id,
        "claim_source": claim_source,
        "resolution_source": resolution_source,
        "actual_outcome": actual_outcome,
        "trust_before": trust_before,
        "trust_after": trust_after,
        "business_impact": business_impact,
        "rationale": rationale,
        "blocked_by_risk_officer": blocked_by_risk_officer,
        "circular_verification_flag": circular_verification_flag,
    }


def make_decisions(
    month: int,
    state: ProductState,
    signal: dict[str, Any],
    prior_actuals: list[dict[str, Any]],
    trust_history: dict[str, float] | None = None,
    use_trust_weighting: bool = False,
    exclude_ceo_from_strategy: bool = False,
    symmetric_weighting: bool = False,
) -> MonthDecision:
    phase = phase_for_month(month)
    last = prior_actuals[-1] if prior_actuals else None
    last_nps = float(last["NPS"]) if last else 0.0
    last_stockout = float(last["stockout_rate"]) if last else 0.0
    last_churn = float(last["churn"]) if last else 0.0
    last_cac = float(last["CAC"]) if last else float(signal["channel_benchmark_sample"]["d2c_paid_social_cac"])

    quality_investment = 4000 if month <= 6 else (6500 if last_nps < 35 or last_churn > 0.10 else 3000)
    reminder_investment = 2500 if month in {4, 5, 9, 15, 21} else 900
    product = {
        "bundle": ["dental chews", "brushing wipes", "breath strips", "mobile reminder/tracking"],
        "quality_investment": quality_investment,
        "reminder_investment": reminder_investment,
        "roadmap": "pilot routine adherence" if month <= 6 else ("retention and vet education" if month <= 24 else "mature refill experience"),
        "customer_promise": "make preventive dog dental care easy to remember and repeat",
    }

    median_wtp = statistics.median(signal["willingness_to_pay"].values())
    price = 24.0 if month <= 3 else (27.0 if month <= 6 else min(39.0, max(27.0, round(median_wtp - 2.0))))
    if last and float(last["conversion_rate"]) < 0.025 and price > 29:
        price -= 2.0

    if use_trust_weighting and trust_history and "Product Manager" in trust_history:
        pm_trust = trust_history["Product Manager"]
        # FIXED: True zero-to-full range [0, baseline*2]
        price = price * (2.0 * pm_trust)

    pricing = {"price": round(price, 2), "pricing_reason": "anchored to oracle willingness-to-pay signal and prior conversion"}

    if month <= 3:
        ad_budget = 3000
        channel = "content"
        target_acquisitions = 0
    elif month <= 6:
        ad_budget = 9000
        channel = "paid_social"
        target_acquisitions = 140
    elif month <= 12:
        ad_budget = min(42_000, 15_000 + 2500 * (month - 7))
        channel = "paid_social"
        target_acquisitions = 350 + 45 * (month - 7)
    else:
        efficiency_factor = 0.75 if last_cac > 90 else 1.0
        ad_budget = min(max(state.cash_balance * 0.08 * efficiency_factor, 12_000), 85_000)
        channel = "vet_referral" if state.vet_partnerships >= 4 and month >= 14 else ("search" if signal["competitor_pressure"] > 0.25 else "paid_social")
        target_acquisitions = int(ad_budget / max(35, last_cac))

    if use_trust_weighting and trust_history and "Growth Marketer" in trust_history:
        growth_trust = trust_history["Growth Marketer"]
        # FIXED: True zero-to-full range [0, baseline*2]
        # trust=0 -> 0x (fully discredited), trust=1 -> 2x (fully trusted)
        ad_budget = ad_budget * (2.0 * growth_trust)

        # Arm D: Symmetric weighting - Finance Controller can brake spending
        if symmetric_weighting and "Finance Controller" in trust_history:
            finance_trust = trust_history["Finance Controller"]
            # FIXED: Finance brake allows full range [0, 1]
            # trust=1 -> 0x multiplier (full brake), trust=0 -> 1x (no brake)
            finance_brake = 1.0 - finance_trust
            ad_budget = ad_budget * finance_brake

        ad_budget = min(max(ad_budget, 0), 90_000)

    growth = {
        "primary_channel": channel,
        "creative_angle": "preventive health without daily brushing friction",
        "ad_budget": round(ad_budget, 2),
        "target_acquisitions": target_acquisitions,
    }

    partnership_type = "D2C only"
    if month >= 7 and month % 3 == 1:
        partnership_type = "vet clinics"
    elif month >= 13 and month % 4 == 0:
        partnership_type = "groomers"
    elif month >= 25 and month % 5 == 0:
        partnership_type = "pet stores"
    partnership = {
        "focus": partnership_type,
        "monthly_outreach": 0 if partnership_type == "D2C only" else 45,
        "rationale": "vet and grooming channels improve trust and retention once product proof exists",
    }

    expected_orders = max(int(state.active_subscribers * (1.0 - min(last_churn, 0.18))) + target_acquisitions, target_acquisitions + 60)
    inventory_units = int(math.ceil(expected_orders * (1.20 + max(last_stockout, 0.02)) / 25.0) * 25)

    if use_trust_weighting and trust_history and "Operations Manager" in trust_history:
        ops_trust = trust_history["Operations Manager"]
        # FIXED: True zero-to-full range [0, baseline*2]
        inventory_units = int(inventory_units * (2.0 * ops_trust))

    operations = {
        "inventory_units": inventory_units,
        "supplier": "quality_checked_dental_kit_supplier",
        "stock_buffer": round(inventory_units / max(expected_orders, 1) - 1.0, 3),
        "quality_controls": "incoming lot checks and monthly chew acceptance review",
    }

    fixed_cost = 18_000 if month <= 6 else (32_000 if month <= 18 else 48_000)
    if state.cash_balance < 90_000:
        fixed_cost *= 0.72
    finance = {
        "fixed_operating_cost": round(fixed_cost, 2),
        "cash_control": "cap spend" if state.cash_balance < 120_000 else "fund measured growth",
        "funding_need": state.cash_balance < 80_000,
    }

    reckless_spend = ad_budget > max(20_000, state.cash_balance * 0.22)
    risk = {
        "approved": not reckless_spend,
        "blocked_reason": "ad budget exceeds risk cap" if reckless_spend else None,
        "confidence_policy": "agent confidence must be ledger-resolved before it can loosen spend caps",
    }
    if reckless_spend:
        growth["ad_budget"] = round(max(3000, state.cash_balance * 0.12), 2)
        risk["approved_after_adjustment"] = True

    if use_trust_weighting and not exclude_ceo_from_strategy and trust_history and "Founder CEO" in trust_history:
        ceo_trust = trust_history["Founder CEO"]
        if ceo_trust < 0.40:
            strategy = "cut burn and preserve runway"
        elif ceo_trust > 0.75:
            strategy = "scale carefully" if month > 6 else ("pilot" if month > 3 else "explore")
        else:
            strategy = "explore" if month <= 3 else ("pilot" if month <= 6 else ("scale carefully" if state.cash_balance > 90_000 else "cut burn and preserve runway"))
    else:
        strategy = "explore" if month <= 3 else ("pilot" if month <= 6 else ("scale carefully" if state.cash_balance > 90_000 else "cut burn and preserve runway"))

    ceo = {
        "strategy": strategy,
        "continue_business": state.cash_balance > 20_000,
        "phase": phase,
    }
    return MonthDecision(product=product, pricing=pricing, growth=growth, partnership=partnership, operations=operations, finance=finance, risk=risk, ceo=ceo)


def claim_specs(month: int, simulated_date: str, signal: dict[str, Any], decisions: MonthDecision, state: ProductState) -> list[ClaimSpec]:
    claim_src = source("market_oracle_pre_decision_signal", f"seed={signal['seed']}:month={month}")
    resolution_src = source("market_oracle_monthly_actual", f"seed={signal['seed']}:month={month}")
    benchmark_cac = float(signal["channel_benchmark_sample"]["d2c_paid_social_cac"])
    revenue_floor = max(500.0, (state.active_subscribers + decisions.growth["target_acquisitions"] * 0.5) * decisions.pricing["price"] * 0.55)
    runway_floor = 2.0 if month < 18 else 1.0
    stockout_ceiling = 0.16 if decisions.operations["stock_buffer"] < 0.25 else 0.10
    health_floor = state.previous_health_score + (-0.02 if month <= 3 else 0.01)
    return [
        ClaimSpec("Growth Marketer", "Growth Team", f"Month {month} CAC will be <= {benchmark_cac * 1.65:.2f}.", 0.62, claim_src, resolution_src, f"CAC <= {benchmark_cac * 1.65:.2f}", benchmark_cac * 1.65, "cac_max"),
        ClaimSpec("Product Manager", "Product Team", f"Month {month} conversion rate will be >= {max(0.012, signal['survey_sample']['interest_rate'] * 0.11):.4f}.", 0.58, claim_src, resolution_src, "conversion rate meets floor", max(0.012, signal["survey_sample"]["interest_rate"] * 0.11), "conversion_min"),
        ClaimSpec("Finance Controller", "Finance Team", f"Month {month} gross revenue will be >= {revenue_floor:.2f}.", 0.60, claim_src, resolution_src, "gross revenue meets forecast floor", revenue_floor, "revenue_min"),
        ClaimSpec("Operations Manager", "Operations Team", f"Month {month} stockout risk will be <= {stockout_ceiling:.4f}.", 0.64, claim_src, resolution_src, "stockout risk stays below ceiling", stockout_ceiling, "stockout_max"),
        ClaimSpec("Founder CEO", "Founder Office", f"Month {month} strategy will improve business health score.", 0.56, claim_src, resolution_src, "health score improves versus policy baseline", health_floor, "health_min"),
    ]


def evaluate_claim(spec: ClaimSpec, actual: dict[str, Any]) -> tuple[bool, str]:
    if spec.kind == "cac_max":
        outcome = float(actual["CAC"]) <= spec.expected
        op = "<=" if outcome else ">"
        return outcome, f"CAC actual {actual['CAC']} {op} {spec.expected:.2f}"
    if spec.kind == "conversion_min":
        outcome = float(actual["conversion_rate"]) >= spec.expected
        op = ">=" if outcome else "<"
        return outcome, f"conversion actual {actual['conversion_rate']} {op} {spec.expected:.4f}"
    if spec.kind == "revenue_min":
        outcome = float(actual["gross_revenue"]) >= spec.expected
        op = ">=" if outcome else "<"
        return outcome, f"gross revenue actual {actual['gross_revenue']} {op} {spec.expected:.2f}"
    if spec.kind == "stockout_max":
        outcome = float(actual["stockout_risk"]) <= spec.expected
        op = "<=" if outcome else ">"
        return outcome, f"stockout risk actual {actual['stockout_risk']} {op} {spec.expected:.4f}"
    if spec.kind == "health_min":
        outcome = float(actual["health_score"]) >= spec.expected
        op = ">=" if outcome else "<"
        return outcome, f"health score actual {actual['health_score']} {op} {spec.expected:.4f}"
    raise ValueError(f"unknown claim kind: {spec.kind}")


def connect_calibration(use_db: bool) -> tuple[dict[str, Any], Any, Any]:
    if not use_db:
        return create_calibration_engine(db=None), None, None
    if psycopg2 is None:
        raise SystemExit("ERROR: psycopg2 is required for database-backed simulation.")
    db_url = os.environ.get("DATABASE_URL", "postgresql://agentco:password@localhost:5432/agentco")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        svc_conn = psycopg2.connect(resolution_dsn(db_url))
        svc_conn.autocommit = True
    except psycopg2.OperationalError as exc:
        raise SystemExit("ERROR: Database unavailable. Run `make migrate` with RESOLUTION_SERVICE_PASSWORD set.") from exc
    return create_calibration_engine(db=conn), conn, svc_conn


def run_simulation(args: argparse.Namespace, use_trust_weighting: bool = False, exclude_ceo_from_strategy: bool = False, symmetric_weighting: bool = False) -> dict[str, Any]:
    if args.months <= 0:
        raise ValueError("--months must be positive")
    oracle = MarketOracle(args.seed)
    run_id = f"pawdent-{uuid.uuid4()}"
    state = ProductState()
    cal, conn, svc_conn = connect_calibration(use_db=not args.no_db)
    ledger = cal["ledger"]
    resolution = cal["resolution"]
    trust = cal["trust"]

    events: list[dict[str, Any]] = []
    actuals: list[dict[str, Any]] = []
    financials: list[dict[str, Any]] = []
    calibration_rows: list[dict[str, Any]] = []
    product_roadmap: list[dict[str, Any]] = []
    circular_rejection = ""
    month_seconds = args.duration_seconds / args.months if args.months else 0.0
    trust_history: dict[str, float] = {}

    print(f"Starting {INSTITUTION}: run_id={run_id}, seed={args.seed}, months={args.months}, trust_weighting={use_trust_weighting}, symmetric={symmetric_weighting}")
    for month in range(1, args.months + 1):
        month_started = time.monotonic()
        simulated_date = oracle.simulated_date(month)
        signal = oracle.pre_decision_signal(month, state)
        pre_source = source("market_oracle_pre_decision_signal", f"seed={args.seed}:month={month}")
        actual_source = source("market_oracle_monthly_actual", f"seed={args.seed}:month={month}")
        validate_independent_sources(pre_source, actual_source)

        events.append(event(
            run_id=run_id, seed=args.seed, month=month, simulated_date=simulated_date,
            team="Market Intelligence Team", agent="Market Research Agent", role="Requests market studies and identifies customer segments.",
            call_type="market_context", input_sources=[pre_source],
            decision={"segments": signal["customer_segments"], "survey_sample": signal["survey_sample"], "competitor_signal": signal["competitor_rumor_or_public_signal"]},
            confidence=None, prediction_id=None, claim_source=None, resolution_source=None,
            actual_outcome=None, trust_before=None, trust_after=None, business_impact=None,
            rationale="read only pre-decision oracle signals; no monthly actuals exposed",
        ))

        decisions = make_decisions(month, state, signal, actuals, trust_history, use_trust_weighting, exclude_ceo_from_strategy, symmetric_weighting)
        role_by_agent = {agent: role for _, agent, role in AGENT_ROSTER}
        team_by_agent = {agent: team for team, agent, _ in AGENT_ROSTER}

        for agent, call_type, decision_payload in [
            ("Founder CEO", "strategy_call", decisions.ceo),
            ("Product Manager", "product_decision", decisions.product | decisions.pricing),
            ("Growth Marketer", "ad_budget_and_channel", decisions.growth),
            ("Sales & Partnerships Agent", "partnership_decision", decisions.partnership),
            ("Operations Manager", "inventory_and_quality", decisions.operations),
            ("Finance Controller", "cash_and_unit_economics", decisions.finance),
            ("Risk Officer", "risk_approval", decisions.risk),
        ]:
            events.append(event(
                run_id=run_id, seed=args.seed, month=month, simulated_date=simulated_date,
                team=team_by_agent[agent], agent=agent, role=role_by_agent[agent], call_type=call_type,
                input_sources=[pre_source, source("agentco_finance_computation", f"month={month}:prior_state")],
                decision=decision_payload, confidence=None, prediction_id=None,
                claim_source=None, resolution_source=None, actual_outcome=None,
                trust_before=None, trust_after=None, business_impact=None,
                rationale="deterministic policy using pre-decision oracle signals and prior resolved months",
                blocked_by_risk_officer=agent != "Risk Officer" and decisions.risk.get("blocked_reason") is not None,
            ))

        product_roadmap.append({"month": month, "phase": phase_for_month(month), **decisions.product})

        registered: list[tuple[ClaimSpec, str, float]] = []
        for spec in claim_specs(month, simulated_date, signal, decisions, state):
            agent_id = PREDICTING_AGENTS[spec.agent]
            trust_before = trust.trusted_confidence(
                stated=spec.confidence,
                subject_id=agent_id,
                subject_type="agent",
                domain=DOMAIN,
                claim_type=CLAIM_TYPE,
                horizon_class="short",
            )
            resolution_date = (
                datetime.now(timezone.utc) - timedelta(milliseconds=1)
                if args.no_db
                else datetime.now(timezone.utc) + timedelta(milliseconds=5)
            )
            reg = PredictionRegistration(
                claim=spec.claim,
                probability=round(spec.confidence, 4),
                confidence_basis={
                    "source": spec.claim_source,
                    "allowed_source_type": "market_oracle_pre_decision_signal",
                    "resolution_condition": spec.resolution_condition,
                    "month": month,
                    "simulated_date": simulated_date,
                },
                producing_agent_id=agent_id,
                producing_prompt_version="pawdent_business_simulation_v1",
                resolution_criterion=spec.resolution_condition,
                resolution_date=resolution_date,
                ground_truth_source=spec.resolution_source,
                horizon_class="short",
                domain=DOMAIN,
                claim_type=CLAIM_TYPE,
                historical_registration_reason="accelerated no-db simulation resolves synthetic monthly actuals immediately" if args.no_db else None,
            )
            prediction_id = ledger.pre_register(reg)
            registered.append((spec, prediction_id, trust_before))
            events.append(event(
                run_id=run_id, seed=args.seed, month=month, simulated_date=simulated_date,
                team=spec.team, agent=spec.agent, role=role_by_agent[spec.agent],
                call_type="pre_registered_claim", input_sources=[spec.claim_source, source("agentco_prediction_ledger", f"prediction={prediction_id}")],
                decision={"claim": spec.claim, "resolution_condition": spec.resolution_condition},
                confidence=spec.confidence, prediction_id=prediction_id,
                claim_source=spec.claim_source, resolution_source=spec.resolution_source,
                actual_outcome=None, trust_before=trust_before, trust_after=None,
                business_impact=None, rationale="claim registered before monthly market actual was revealed",
            ))

        if month == 1:
            try:
                validate_independent_sources(pre_source, pre_source)
            except CircularResolutionError as exc:
                circular_rejection = f"circular verification rejected in month 1: {exc}"
                events.append(event(
                    run_id=run_id, seed=args.seed, month=month, simulated_date=simulated_date,
                    team="Risk & Governance Team", agent="Risk Officer", role=role_by_agent["Risk Officer"],
                    call_type="circular_verification_rejection", input_sources=[pre_source],
                    decision={"rejected": True, "reason": str(exc)},
                    confidence=None, prediction_id=registered[0][1], claim_source=pre_source,
                    resolution_source=pre_source, actual_outcome=None,
                    trust_before=None, trust_after=None, business_impact=None,
                    rationale="same-source verification cannot resolve a market claim",
                    blocked_by_risk_officer=True, circular_verification_flag=True,
                ))
            else:
                raise RuntimeError("circular verification was not rejected")

        time.sleep(0.01)
        actual = oracle.monthly_actual(month, state, decisions, signal)
        actuals.append(actual)

        for spec, prediction_id, trust_before in registered:
            outcome, explanation = evaluate_claim(spec, actual)
            resolved = resolution.resolve(
                prediction_id=prediction_id,
                outcome=outcome,
                ground_truth_source=spec.resolution_source,
                evidence={
                    "source_id": actual["source_id"],
                    "source_type": "market_oracle_monthly_actual",
                    "market_state_hash": actual["market_state_hash"],
                    "explanation": explanation,
                },
            )
            if svc_conn is not None:
                ledger._db = svc_conn
                ledger.persist_resolution(resolved)
                ledger._db = conn
            trust_after = trust.trusted_confidence(
                stated=spec.confidence,
                subject_id=PREDICTING_AGENTS[spec.agent],
                subject_type="agent",
                domain=DOMAIN,
                claim_type=CLAIM_TYPE,
                horizon_class="short",
            )
            row = {
                "run_id": run_id,
                "seed": args.seed,
                "month": month,
                "simulated_date": simulated_date,
                "prediction_id": prediction_id,
                "agent": spec.agent,
                "claim": spec.claim,
                "confidence": spec.confidence,
                "claim_source": spec.claim_source,
                "resolution_source": spec.resolution_source,
                "outcome": outcome,
                "trust_before": trust_before,
                "trust_after": trust_after,
                "calibration_delta": round(trust_after - trust_before, 6),
                "explanation": explanation,
            }
            calibration_rows.append(row)
            trust_history[spec.agent] = trust_after
            events.append(event(
                run_id=run_id, seed=args.seed, month=month, simulated_date=simulated_date,
                team="Calibration Office", agent="Calibration Auditor", role=role_by_agent["Calibration Auditor"],
                call_type="resolve_prediction", input_sources=[spec.resolution_source, source("agentco_calibration_result", f"prediction={prediction_id}")],
                decision=row, confidence=spec.confidence, prediction_id=prediction_id,
                claim_source=spec.claim_source, resolution_source=spec.resolution_source,
                actual_outcome=outcome, trust_before=trust_before, trust_after=trust_after,
                business_impact={"gross_revenue": actual["gross_revenue"], "operating_profit": actual["operating_profit"], "cash_balance": actual["cash_balance"]},
                rationale="resolved against market oracle monthly actual only after preregistration",
            ))

        mistake = None
        if actual["operating_profit"] < 0:
            mistake = "monthly operation lost money"
        elif actual["stockout_rate"] > 0.08:
            mistake = "inventory constrained demand"
        elif actual["NPS"] < 30:
            mistake = "customer satisfaction below target"
        lesson = "raise quality and retention controls" if actual["NPS"] < 35 else ("increase inventory buffer" if actual["stockout_rate"] > 0.08 else "continue measured operating plan")
        policy_change = "prioritize retention before more spend" if actual["churn"] > 0.10 else ("increase stock buffer next month" if actual["stockout_rate"] > 0.08 else "keep spend tied to resolved CAC")
        state.operating_policy = policy_change
        events.append(event(
            run_id=run_id, seed=args.seed, month=month, simulated_date=simulated_date,
            team="Learning Office", agent="Learning Agent", role=role_by_agent["Learning Agent"],
            call_type="learning_update", input_sources=[actual_source, source("agentco_calibration_result", f"month={month}")],
            decision={"lesson": lesson, "mistake": mistake, "policy_change": policy_change},
            confidence=None, prediction_id=None, claim_source=None, resolution_source=actual_source,
            actual_outcome={"NPS": actual["NPS"], "operating_profit": actual["operating_profit"], "stockout_rate": actual["stockout_rate"]},
            trust_before=None, trust_after=None,
            business_impact={"cash_balance": actual["cash_balance"], "active_subscribers": actual["active_subscribers"]},
            rationale="updated next-month policy from resolved actuals and calibration results",
        ))

        financials.append(actual)
        state.cash_balance = float(actual["cash_balance"])
        state.active_subscribers = int(actual["active_subscribers"])
        state.cumulative_profit += float(actual["operating_profit"])
        state.previous_health_score = float(actual["health_score"])
        state.previous_nps = float(actual["NPS"])
        state.quality_score = min(0.91, state.quality_score + decisions.product["quality_investment"] / 220_000.0 - (0.006 if actual["refund_rate"] > 0.06 else 0.0))
        state.reminder_score = min(0.88, state.reminder_score + decisions.product["reminder_investment"] / 180_000.0)
        state.packaging_score = min(0.82, state.packaging_score + 0.006)
        state.supplier_reliability = min(0.94, max(0.55, state.supplier_reliability + (0.012 if actual["stockout_rate"] < 0.05 else -0.018)))
        if decisions.partnership["focus"] == "vet clinics":
            state.vet_partnerships += 1
        elif decisions.partnership["focus"] == "groomers":
            state.groomer_partnerships += 1
        elif decisions.partnership["focus"] == "pet stores":
            state.pet_store_partnerships += 1

        print(
            f"month={month:02d} date={simulated_date} active={actual['active_subscribers']} "
            f"revenue={actual['gross_revenue']:.2f} profit={actual['operating_profit']:.2f} cash={actual['cash_balance']:.2f}"
        )
        if not args.no_sleep:
            remaining = month_seconds - (time.monotonic() - month_started)
            if remaining > 0 and month < args.months:
                time.sleep(remaining)

    outputs = write_outputs(
        run_id=run_id,
        seed=args.seed,
        months=args.months,
        duration_seconds=args.duration_seconds,
        events=events,
        financials=financials,
        calibration_rows=calibration_rows,
        product_roadmap=product_roadmap,
        circular_rejection=circular_rejection,
        final_state=state,
    )
    if conn is not None:
        conn.close()
    if svc_conn is not None:
        svc_conn.close()
    return outputs


def write_outputs(
    *,
    run_id: str,
    seed: int,
    months: int,
    duration_seconds: float,
    events: list[dict[str, Any]],
    financials: list[dict[str, Any]],
    calibration_rows: list[dict[str, Any]],
    product_roadmap: list[dict[str, Any]],
    circular_rejection: str,
    final_state: ProductState,
) -> dict[str, Any]:
    ACCEPTANCE_DIR.mkdir(parents=True, exist_ok=True)
    with DECISIONS_PATH.open("w") as fh:
        for item in events:
            fh.write(json.dumps(item, sort_keys=True, default=str) + "\n")

    financial_fields = [
        "run_id", "seed", "month", "simulated_date", "source_id", "market_state_hash",
        "visitors", "leads", "trial_orders", "paid_subscribers", "active_subscribers",
        "churned_subscribers", "CAC", "LTV_estimate", "ARPU", "price", "gross_revenue",
        "COGS", "shipping_total", "ad_spend", "support_cost", "refund_dollars",
        "gross_margin", "operating_profit", "cash_balance", "NPS", "stockout_rate",
        "refund_rate", "conversion_rate", "churn", "support_tickets",
    ]
    with FINANCIALS_PATH.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=financial_fields)
        writer.writeheader()
        for row in financials:
            writer.writerow({field: (run_id if field == "run_id" else seed if field == "seed" else row.get(field, "")) for field in financial_fields})

    calibration_fields = [
        "run_id", "seed", "month", "simulated_date", "prediction_id", "agent",
        "claim", "confidence", "claim_source", "resolution_source", "outcome",
        "trust_before", "trust_after", "calibration_delta", "explanation",
    ]
    with CALIBRATION_PATH.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=calibration_fields)
        writer.writeheader()
        writer.writerows(calibration_rows)

    total_revenue = round(sum(float(r["gross_revenue"]) for r in financials), 2)
    total_profit = round(sum(float(r["operating_profit"]) for r in financials), 2)
    final_cash = round(float(financials[-1]["cash_balance"]), 2) if financials else 0.0
    final_active = int(financials[-1]["active_subscribers"]) if financials else 0
    profitable_months = sum(1 for r in financials if float(r["operating_profit"]) > 0)
    final_status = "failed"
    if final_cash > 0 and final_active > 500:
        final_status = "survived"
    if final_cash > 300_000 and total_profit > 0:
        final_status = "profitable"
    if final_active > 12_000 and total_revenue > 4_000_000:
        final_status = "venture-scale"

    trust_by_agent: dict[str, dict[str, float]] = {}
    for row in calibration_rows:
        trust_by_agent[row["agent"]] = {
            "last_trust": round(float(row["trust_after"]), 4),
            "resolved_claims": trust_by_agent.get(row["agent"], {}).get("resolved_claims", 0) + 1,
        }
    leaderboard = sorted(trust_by_agent.items(), key=lambda kv: kv[1]["last_trust"], reverse=True)
    correct = [r for r in calibration_rows if r["outcome"]]
    wrong = [r for r in calibration_rows if not r["outcome"]]
    biggest_correct = max(correct, key=lambda r: float(r["trust_after"]) - float(r["trust_before"]), default=None)
    biggest_wrong = min(wrong, key=lambda r: float(r["calibration_delta"]), default=None)
    learned = "PawDent worked when acquisition was paced by resolved CAC and retention, but stockouts and quality gaps could erase demand gains."
    next_plan = [
        "Keep the subscription live only if cash remains above a six-month operating buffer.",
        "Expand vet partnerships in markets where churn is below 8%.",
        "Raise supplier redundancy before increasing paid media.",
        "Continue monthly preregistered forecasts for CAC, revenue, stockout risk, conversion, and business health.",
    ]

    summary = {
        "run_id": run_id,
        "seed": seed,
        "institution": INSTITUTION,
        "product": PRODUCT_NAME,
        "months": months,
        "duration_seconds": duration_seconds,
        "total_revenue": total_revenue,
        "total_profit": total_profit,
        "final_cash_balance": final_cash,
        "final_active_subscribers": final_active,
        "profitable_months": profitable_months,
        "final_business_status": final_status,
        "circular_verification_rejection": circular_rejection,
        "biggest_correct_call": biggest_correct,
        "biggest_wrong_call": biggest_wrong,
        "agent_trust_leaderboard": leaderboard,
        "what_the_institution_learned": learned,
        "next_12_month_plan": next_plan,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True, default=str))

    decision_rows = "\n".join(
        f"| {e['month']} | {e['team']} | {e['agent']} | {e['call_type']} | {e['rationale']} |"
        for e in events
    )
    timeline_rows = "\n".join(
        f"| {r['month']} | {r['simulated_date']} | {phase_for_month(int(r['month']))} | {r['active_subscribers']} | {r['gross_revenue']:.2f} | {r['operating_profit']:.2f} | {r['cash_balance']:.2f} | {r['NPS']} | {r['market_state_hash'][:12]} |"
        for r in financials
    )
    claim_rows = "\n".join(
        f"| {r['month']} | `{r['prediction_id']}` | {r['agent']} | {r['claim']} | {r['outcome']} | {r['trust_before']:.4f}->{r['trust_after']:.4f} |"
        for r in calibration_rows
    )
    growth_rows = "\n".join(
        f"| {r['month']} | {r['active_subscribers']} | {r['paid_subscribers']} | {r['churned_subscribers']} | {r['CAC']} | {r['LTV_estimate']} | {r['ARPU']} |"
        for r in financials
    )
    roadmap_rows = "\n".join(
        f"| {r['month']} | {r['phase']} | {r['roadmap']} | {r['quality_investment']} | {r['reminder_investment']} |"
        for r in product_roadmap
    )
    leaderboard_rows = "\n".join(
        f"| {agent} | {data['last_trust']:.4f} | {int(data['resolved_claims'])} |"
        for agent, data in leaderboard
    )
    roster_rows = "\n".join(f"| {team} | {agent} | {role} |" for team, agent, role in AGENT_ROSTER)

    report = [
        "# PawDent Business Simulation",
        "",
        "## Institution Charter",
        f"**Name:** {INSTITUTION}",
        f"**Mission:** {MISSION}",
        "",
        "## Product Launched",
        f"`{PRODUCT_NAME}`: {PRODUCT}",
        "",
        "## Market Simulator Contract",
        "The market simulator is a deterministic oracle, not an agent. It fabricates market reality only from seed, month, product state, pricing, channel spend, customer satisfaction, competitor pressure, seasonality, supply reliability, and macro shock state. Every monthly actual carries `source_id`, `seed`, `month`, `simulated_date`, and `market_state_hash`.",
        f"- Seed: `{seed}`",
        f"- First market_state_hash: `{financials[0]['market_state_hash'] if financials else ''}`",
        "",
        "## Agent Roster",
        "| Team | Agent | Role |",
        "|---|---|---|",
        roster_rows,
        "",
        "## What Agent Took What Call?",
        "| Month | Team | Agent | Call type | Rationale |",
        "|---:|---|---|---|---|",
        decision_rows,
        "",
        "## 36-Month Timeline",
        "| Month | Date | Phase | Active subscribers | Revenue | Operating profit | Cash | NPS | State hash |",
        "|---:|---|---|---:|---:|---:|---:|---:|---|",
        timeline_rows,
        "",
        "## Monthly Agent Decision Table",
        "See the call ledger above and `pawdent_agent_decisions.jsonl` for every structured decision event.",
        "",
        "## Pre-Registered Claims and Calibration",
        "| Month | Prediction id | Agent | Claim | Outcome | Trust change |",
        "|---:|---|---|---|---|---|",
        claim_rows,
        "",
        "## Actual Market Outcomes",
        "Actuals came only from `market_oracle_monthly_actual` rows in `pawdent_monthly_financials.csv`.",
        "",
        "## Circular Verification Rejection",
        circular_rejection,
        "",
        "## Product Roadmap Evolution",
        "| Month | Phase | Roadmap | Quality investment | Reminder investment |",
        "|---:|---|---|---:|---:|",
        roadmap_rows,
        "",
        "## Marketing Decisions",
        "Marketing decisions are recorded as `ad_budget_and_channel` events with source-tracked inputs.",
        "",
        "## Operations Decisions",
        "Operations decisions are recorded as `inventory_and_quality` events and affected stockouts, refunds, support tickets, and margin.",
        "",
        "## Finance Decisions",
        "Finance decisions are recorded as `cash_and_unit_economics` events and shaped fixed operating costs, runway, and funding need.",
        "",
        "## P&L Summary",
        f"- Total revenue: `{total_revenue:.2f}`",
        f"- Total operating profit: `{total_profit:.2f}`",
        f"- Final cash balance: `{final_cash:.2f}`",
        f"- Profitable months: `{profitable_months}`",
        "",
        "## Customer Growth Chart",
        "| Month | Active subscribers | New paid subscribers | Churned subscribers | CAC | LTV estimate | ARPU |",
        "|---:|---:|---:|---:|---:|---:|---:|",
        growth_rows,
        "",
        "## Biggest Correct Call",
        json.dumps(biggest_correct, sort_keys=True, default=str) if biggest_correct else "No correct claims.",
        "",
        "## Biggest Wrong Call",
        json.dumps(biggest_wrong, sort_keys=True, default=str) if biggest_wrong else "No wrong claims.",
        "",
        "## Agent Trust Leaderboard",
        "| Agent | Last trust | Resolved claims |",
        "|---|---:|---:|",
        leaderboard_rows,
        "",
        "## Final Business Status",
        final_status,
        "",
        "## What The Institution Learned",
        learned,
        "",
        "## Next 12-Month Plan",
        "\n".join(f"- {item}" for item in next_plan),
        "",
    ]
    REPORT_PATH.write_text("\n".join(report))
    return summary


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_simulation(args)
    print(f"Report: {REPORT_PATH}")
    print(f"Decision ledger: {DECISIONS_PATH}")
    print(f"Financials: {FINANCIALS_PATH}")
    print(f"Calibration ledger: {CALIBRATION_PATH}")
    print(f"Summary: {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
