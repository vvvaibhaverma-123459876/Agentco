#!/usr/bin/env python3
"""Agent forecasting for B2B SaaS business model.

Agents make predictions about market outcomes based on heuristics.
Predictions are deterministic per seed and independently reasoned.
Trust scores are calculated based on forecast accuracy vs. oracle.

Agents:
1. Growth Marketer: Predicts CAC trend (lower on easy seeds, terrible on hard)
2. Finance Controller: Predicts cash runway (good on stable, bad on volatile)
3. Product Manager: Predicts price elasticity (good on some, bad on others)
4. Operations Manager: Predicts customer churn (good baseline, bad on shocks)
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Any


@dataclass
class AgentForecast:
    """A single agent forecast with confidence."""
    agent_name: str
    prediction: float
    confidence: float
    reasoning: str
    actual_value: float | None = None
    error: float | None = None
    hit: bool | None = None


class B2BSaaSAgents:
    """Agent forecasting engine for B2B SaaS."""

    def __init__(self, seed: int):
        self.seed = seed
        # Each agent has seed-specific heuristic quality
        # Some agents are naturally better on certain seed types
        base_rng = random.Random(seed)
        self.agent_quality = {
            "growth_marketer": base_rng.uniform(0.4, 1.0),
            "finance_controller": base_rng.uniform(0.4, 1.0),
            "product_manager": base_rng.uniform(0.4, 1.0),
            "operations_manager": base_rng.uniform(0.4, 1.0),
        }

    def _agent_rng(self, agent_name: str, month: int, label: str) -> random.Random:
        """Deterministic RNG for agent predictions."""
        digest = hashlib.sha256(f"{self.seed}|{agent_name}|{month}|{label}".encode()).hexdigest()
        return random.Random(int(digest[:16], 16))

    def growth_marketer_cac_forecast(
        self,
        month: int,
        current_customers: int,
        prior_actual_cac: float | None,
    ) -> AgentForecast:
        """Forecast CAC based on month and customer count.

        Better at: Easy seeds where CAC stays low
        Worse at: Hard seeds with market shocks
        """
        rng = self._agent_rng("growth_marketer", month, "cac")
        quality = self.agent_quality["growth_marketer"]

        # Base forecast: scale-based prediction
        # Assumption: CAC improves with scale (usually true early, breaks in competition)
        scale_factor = max(0.6, min(1.5, current_customers / 500.0))  # Improves to 500 customers
        base_cac_forecast = 50 * (1.0 / max(scale_factor, 0.5))  # Improves with scale

        # Confidence varies by agent quality and market knowledge
        confidence = 0.5 + 0.3 * quality + rng.uniform(-0.1, 0.1)

        # Error based on agent quality (good agents have smaller errors)
        error_range = 30 * (1.0 - quality)
        noise = rng.uniform(-error_range, error_range)

        forecast_cac = max(25, base_cac_forecast + noise)

        reasoning = (
            f"CAC forecast: Scale factor {scale_factor:.2f} suggests CAC of ${forecast_cac:.0f}. "
            f"Confidence: {confidence:.1%}"
        )

        return AgentForecast(
            agent_name="Growth Marketer",
            prediction=forecast_cac,
            confidence=max(0.1, min(0.95, confidence)),
            reasoning=reasoning,
        )

    def finance_controller_margin_forecast(
        self,
        month: int,
        current_customers: int,
        current_cash: float,
        monthly_burn: float,
    ) -> AgentForecast:
        """Forecast unit margin and runway.

        Better at: Stable markets with consistent burn
        Worse at: Volatile markets with shocks
        """
        rng = self._agent_rng("finance_controller", month, "margin")
        quality = self.agent_quality["finance_controller"]

        # Base forecast: current burn extrapolated
        if current_customers > 0:
            estimated_arpu = 79.0
            estimated_cogs = current_customers * 22.0
            estimated_gross_margin = (current_customers * estimated_arpu) - estimated_cogs
            unit_margin = estimated_gross_margin / max(1, current_customers)
        else:
            unit_margin = 57.0  # $79 - $22 COGS baseline

        # Runway forecast in months
        if monthly_burn < 0:
            runway = current_cash / abs(monthly_burn)  # Months until cash depletes
        else:
            runway = 999  # Profitable, long runway

        confidence = 0.4 + 0.4 * quality + rng.uniform(-0.1, 0.1)

        # Error: good agents predict runway well, bad agents are way off
        error_range = 12 * (1.0 - quality)  # Months of error
        runway_noise = rng.uniform(-error_range, error_range)
        forecast_runway = max(1, runway + runway_noise)

        reasoning = (
            f"Unit margin: ~${unit_margin:.0f}/customer. "
            f"Cash runway: ~{forecast_runway:.1f} months at current burn. "
            f"Confidence: {confidence:.1%}"
        )

        return AgentForecast(
            agent_name="Finance Controller",
            prediction=forecast_runway,
            confidence=max(0.1, min(0.95, confidence)),
            reasoning=reasoning,
        )

    def product_manager_price_elasticity_forecast(
        self,
        month: int,
        current_churn_rate: float,
    ) -> AgentForecast:
        """Forecast price elasticity (can we raise price?).

        Better at: Consistent churn markets
        Worse at: Volatile churn markets
        """
        rng = self._agent_rng("product_manager", month, "elasticity")
        quality = self.agent_quality["product_manager"]

        # Base forecast: high churn = low elasticity (can't raise price)
        # Low churn = high elasticity (can raise price)
        if current_churn_rate < 0.05:
            elasticity_forecast = 0.8  # High elasticity, can raise significantly
        elif current_churn_rate < 0.08:
            elasticity_forecast = 0.6  # Moderate elasticity
        else:
            elasticity_forecast = 0.3  # Low elasticity, risky to raise

        # Agent quality affects confidence
        confidence = 0.5 + 0.25 * quality + rng.uniform(-0.1, 0.1)

        # Error based on quality
        error_range = 0.3 * (1.0 - quality)
        noise = rng.uniform(-error_range, error_range)
        forecast_elasticity = max(0.1, min(1.0, elasticity_forecast + noise))

        reasoning = (
            f"Churn rate: {current_churn_rate:.1%}. "
            f"Estimated price elasticity: {forecast_elasticity:.1%}. "
            f"Confidence: {confidence:.1%}"
        )

        return AgentForecast(
            agent_name="Product Manager",
            prediction=forecast_elasticity,
            confidence=max(0.1, min(0.95, confidence)),
            reasoning=reasoning,
        )

    def operations_manager_churn_forecast(
        self,
        month: int,
        prior_churn_rate: float,
        customer_count: int,
    ) -> AgentForecast:
        """Forecast next month's churn rate.

        Better at: Steady-state predictions
        Worse at: Market shocks
        """
        rng = self._agent_rng("operations_manager", month, "churn")
        quality = self.agent_quality["operations_manager"]

        # Base forecast: churn tends to persist + slight trend
        base_forecast = prior_churn_rate

        # Age effect: churn often improves with product maturity
        if month > 12:
            base_forecast *= 0.95  # Slight improvement after year 1
        elif month > 6:
            base_forecast *= 0.98

        confidence = 0.5 + 0.35 * quality + rng.uniform(-0.1, 0.1)

        # Error based on quality
        error_range = 0.04 * (1.0 - quality)
        noise = rng.uniform(-error_range, error_range)
        forecast_churn = max(0.02, min(0.20, base_forecast + noise))

        reasoning = (
            f"Prior churn: {prior_churn_rate:.1%}, month {month}. "
            f"Forecasted churn: {forecast_churn:.1%}. "
            f"Confidence: {confidence:.1%}"
        )

        return AgentForecast(
            agent_name="Operations Manager",
            prediction=forecast_churn,
            confidence=max(0.1, min(0.95, confidence)),
            reasoning=reasoning,
        )

    def all_forecasts(
        self,
        month: int,
        current_customers: int,
        current_cash: float,
        current_churn_rate: float,
        monthly_burn: float,
        prior_actual_cac: float | None,
    ) -> dict[str, AgentForecast]:
        """Generate all four agent forecasts for the month."""
        return {
            "growth_marketer": self.growth_marketer_cac_forecast(
                month, current_customers, prior_actual_cac
            ),
            "finance_controller": self.finance_controller_margin_forecast(
                month, current_customers, current_cash, monthly_burn
            ),
            "product_manager": self.product_manager_price_elasticity_forecast(
                month, current_churn_rate
            ),
            "operations_manager": self.operations_manager_churn_forecast(
                month, current_churn_rate, current_customers
            ),
        }


def calculate_agent_trust(
    forecast: AgentForecast,
    tolerance: float = 0.1,
) -> tuple[float, bool]:
    """Calculate trust score based on forecast accuracy.

    Returns: (trust_score [0-1], hit [bool])

    Trust = 1 if within tolerance, decays to 0 as error grows.
    """
    if forecast.actual_value is None:
        return 0.5, None  # No data

    error = abs(forecast.prediction - forecast.actual_value)
    error_pct = error / max(0.01, forecast.actual_value)

    # Hit if within tolerance
    hit = error_pct <= tolerance

    # Trust: decay from 1 at tolerance to 0 at 2x tolerance
    if error_pct <= tolerance:
        trust = 1.0 - (error_pct / tolerance) * 0.3  # Stay above 0.7
    else:
        trust = max(0.0, 1.0 - (error_pct / tolerance))

    return max(0.0, min(1.0, trust)), hit
