"""
Calibration Updates for Civilization Free-Run
==============================================

Computes calibration metrics from predictions, updates trust scores,
and stores deltas to database.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from agents.db import get_db

logger = logging.getLogger(__name__)


@dataclass
class PredictionRecord:
    """A prediction registered in the ledger."""

    prediction_id: str
    claim_id: str
    claim_text: str
    probability: float  # 0.0-1.0
    confidence_basis: str
    producing_agent_id: str
    domain: str
    resolved: bool
    resolved_outcome: Optional[bool] = None
    brier_score: Optional[float] = None


@dataclass
class CalibrationDelta:
    """Change to calibration/trust metrics."""

    delta_id: str
    agent_id: str
    metric_type: str  # brier_score, trust_score, calibration_error
    old_value: float
    new_value: float
    delta: float
    reason: str
    timestamp: datetime


class CalibrationUpdater:
    """Update calibration metrics and trust scores."""

    def __init__(self):
        self.db = get_db()

    def register_prediction(
        self,
        claim_id: str,
        claim_text: str,
        probability: float,
        domain: str = "autonomy",
        agent_id: str = "civilization-service",
        confidence_basis: str = "internal-assessment",
    ) -> str:
        """Register a new prediction in the ledger.

        Args:
            claim_id: The autonomy_claims.id
            claim_text: The claim being predicted
            probability: Predicted probability (0.0-1.0)
            domain: Domain of prediction (default: autonomy)
            agent_id: Agent making prediction (default: civilization-service)
            confidence_basis: Basis for confidence estimate

        Returns:
            prediction_id (UUID)
        """
        prediction_id = str(uuid.uuid4())

        try:
            import json
            from datetime import timedelta

            # Register with all required NOT NULL fields
            now = datetime.now(timezone.utc)
            resolution_date = now + timedelta(days=7)  # 7-day resolution window

            self.db.execute_update(
                """INSERT INTO prediction_ledger
                   (prediction_id, claim, probability, confidence_basis,
                    producing_agent_id, producing_prompt_version,
                    resolution_criterion, resolution_date, ground_truth_source,
                    horizon_class, domain, claim_type,
                    post_hoc, resolved, was_surprise, hardness,
                    created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    prediction_id,
                    claim_text,
                    probability,
                    json.dumps({"basis": confidence_basis}),  # confidence_basis is jsonb
                    agent_id,
                    "civilization-service-v1",  # producing_prompt_version
                    "external",  # resolution_criterion
                    resolution_date,  # resolution_date
                    "pending",  # ground_truth_source
                    "medium",  # horizon_class (must be 'short', 'medium', or 'long')
                    domain,
                    "factual",  # claim_type
                    False,  # post_hoc
                    False,  # resolved (unresolved initially)
                    False,  # was_surprise
                    0.5,  # hardness (0-1 scale)
                    now,  # created_at
                ),
            )
            logger.info(
                f"Registered prediction {prediction_id}: {claim_text[:50]}... "
                f"(p={probability:.2f}, domain={domain})"
            )
            return prediction_id

        except Exception as e:
            logger.error(f"Failed to register prediction: {e}")
            raise

    def compute_brier_scores(self, agent_id: str) -> Dict[str, Any]:
        """Compute Brier score for an agent's predictions.

        Brier Score = mean((predicted_prob - actual_outcome)^2)
        Range: 0 (perfect) to 1 (worst)

        Args:
            agent_id: Agent to score

        Returns:
            Metrics dict with brier_score, count, etc.
        """
        try:
            # Query agent's resolved predictions
            resolved = self.db.execute_query(
                """SELECT prediction_id, probability, resolved_outcome
                   FROM prediction_ledger
                   WHERE producing_agent_id = %s AND resolved = true""",
                (agent_id,),
                fetch_all=True,
            )

            if not resolved:
                return {
                    "agent_id": agent_id,
                    "brier_score": None,
                    "count": 0,
                    "reason": "no resolved predictions",
                }

            # Compute Brier score
            brier_sum = 0.0
            for row in resolved:
                pred_prob = float(row["probability"])
                actual = 1.0 if row["resolved_outcome"] else 0.0
                brier_sum += (pred_prob - actual) ** 2

            brier_score = brier_sum / len(resolved)

            return {
                "agent_id": agent_id,
                "brier_score": round(brier_score, 4),
                "count": len(resolved),
                "direction": "good" if brier_score < 0.25 else "poor",
            }

        except Exception as e:
            logger.error(f"Brier score computation failed: {e}")
            return {
                "agent_id": agent_id,
                "brier_score": None,
                "error": str(e),
            }

    def update_agent_trust(
        self, agent_id: str, brier_score: Optional[float]
    ) -> CalibrationDelta:
        """Update agent trust score based on Brier score.

        Trust formula:
        - Brier < 0.15: trust += 0.1 (excellent calibration)
        - Brier 0.15-0.25: trust += 0.05 (good calibration)
        - Brier 0.25-0.35: trust no change (acceptable)
        - Brier > 0.35: trust -= 0.1 (poor calibration)

        Args:
            agent_id: Agent to update
            brier_score: Computed Brier score

        Returns:
            CalibrationDelta record
        """
        delta = CalibrationDelta(
            delta_id=str(uuid.uuid4()),
            agent_id=agent_id,
            metric_type="trust_score",
            old_value=0.0,
            new_value=0.0,
            delta=0.0,
            reason="no change",
            timestamp=datetime.now(timezone.utc),
        )

        if brier_score is None:
            delta.reason = "no resolved predictions to compute from"
            return delta

        # Determine trust adjustment
        if brier_score < 0.15:
            trust_delta = 0.1
            reason = "excellent calibration (Brier < 0.15)"
        elif brier_score < 0.25:
            trust_delta = 0.05
            reason = "good calibration (Brier 0.15-0.25)"
        elif brier_score < 0.35:
            trust_delta = 0.0
            reason = "acceptable calibration (Brier 0.25-0.35)"
        else:
            trust_delta = -0.1
            reason = "poor calibration (Brier > 0.35)"

        # For now, just record the delta (don't actually update agent trust)
        # In full system, would update agent_registry.trust_score
        delta.delta = trust_delta
        delta.reason = reason
        delta.new_value = 0.5 + trust_delta  # Assuming baseline of 0.5

        logger.info(f"Trust adjustment for {agent_id}: {reason} (delta={trust_delta:+.2f})")

        return delta

    def record_calibration_delta(self, delta: CalibrationDelta) -> bool:
        """Store calibration delta to database.

        Args:
            delta: CalibrationDelta to record

        Returns:
            True if successful
        """
        try:
            # For now, just log (no calibration_deltas table yet)
            # In full system, would INSERT to calibration_deltas table
            logger.debug(
                f"Recorded calibration delta: {delta.agent_id} {delta.metric_type} "
                f"{delta.old_value} → {delta.new_value} ({delta.delta:+.3f})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to record calibration delta: {e}")
            return False

    def get_calibration_summary(self) -> Dict[str, Any]:
        """Get overall calibration health summary.

        Returns:
            Summary of system calibration state
        """
        try:
            # Count predictions by status
            total_pred = self.db.execute_query(
                "SELECT COUNT(*) as count FROM prediction_ledger",
                fetch_one=True,
            )
            resolved_pred = self.db.execute_query(
                "SELECT COUNT(*) as count FROM prediction_ledger WHERE resolved = true",
                fetch_one=True,
            )

            total = total_pred.get("count", 0) if total_pred else 0
            resolved = resolved_pred.get("count", 0) if resolved_pred else 0

            return {
                "total_predictions": total,
                "resolved_predictions": resolved,
                "unresolved_predictions": total - resolved,
                "resolution_rate": round(resolved / total, 2) if total > 0 else 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Calibration summary failed: {e}")
            return {"error": str(e)}


def update_calibration_from_claims(
    claim_ids: List[str], agent_id: str = "civilization-service"
) -> Dict[str, Any]:
    """Convenience function: register predictions from claims and update calibration.

    Args:
        claim_ids: Claims to register as predictions
        agent_id: Agent making predictions

    Returns:
        Summary of calibration updates
    """
    updater = CalibrationUpdater()

    registered = []
    errors = []

    # Register each claim as a prediction
    for claim_id in claim_ids:
        try:
            # In a real system, would fetch claim from DB to get text, domain
            pred_id = updater.register_prediction(
                claim_id=claim_id,
                claim_text=f"Claim {claim_id}",  # Would fetch from autonomy_claims
                probability=0.7,  # Would estimate from claim confidence
                domain="autonomy",
                agent_id=agent_id,
            )
            registered.append(pred_id)
        except Exception as e:
            errors.append(f"Failed to register {claim_id}: {e}")

    # Compute calibration for agent
    brier_result = updater.compute_brier_scores(agent_id)
    brier_score = brier_result.get("brier_score")

    # Update trust
    trust_delta = updater.update_agent_trust(agent_id, brier_score)
    updater.record_calibration_delta(trust_delta)

    return {
        "predictions_registered": len(registered),
        "registered_ids": registered,
        "brier_score": brier_score,
        "trust_delta": trust_delta.delta,
        "errors": errors,
    }
