"""
Calibrator Self-Audit Module — the Calibration Engine grades itself.

The Calibration Engine makes predictions about its own future performance
and scores them via the same Resolution Service. It cannot raise its own trust
except via a real track record. It explicitly states its residual blind-spot limit.

Random human spot-audits are UNANNOUNCED — the engine cannot anticipate or
prepare for them. The spot-audit interface is here.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from calibration.ledger.prediction_ledger import PredictionLedger, PredictionRegistration
    from calibration.scoring.scoring_module import CalibrationReport

logger = logging.getLogger(__name__)


@dataclass
class SelfAuditReport:
    generated_at: datetime
    self_prediction_count: int
    self_predictions_resolved: int
    self_ece: Optional[float]        # calibration error on the engine's own self-predictions
    stated_blind_spot_limit: str     # MUST be explicit; never claim coverage not earned
    recent_surprises: list[dict]
    trust_score_trend: str           # "improving" | "stable" | "degrading"
    spot_audit_ready: bool           # always True — no preparation possible
    human_spot_audit_log: list[dict]


class SelfAuditModule:
    """
    The Calibration Engine audits itself by the same rules it applies to everyone else.
    It cannot grade its own homework on self-resolution.
    Its self-predictions go through the same Ledger + Resolution Service.
    """

    SELF_AGENT_ID = "calibration-engine"
    SELF_PROMPT_VERSION = "1.0.0"

    def __init__(self, ledger: "PredictionLedger", trust_controller=None, surprise_register=None):
        self.ledger = ledger
        self.trust_controller = trust_controller
        self.surprise_register = surprise_register
        self._spot_audit_log: list[dict] = []

    def make_self_prediction(
        self,
        claim: str,
        probability: float,
        resolution_criterion: str,
        resolution_date: datetime,
        domain: str = "calibration_engine_self",
        claim_type: str = "engine_performance",
    ) -> str:
        """
        The engine pre-registers predictions about its own future performance.
        These are scored by the Resolution Service, not by itself.
        """
        from calibration.ledger.prediction_ledger import PredictionRegistration

        reg = PredictionRegistration(
            claim=claim,
            probability=probability,
            confidence_basis={
                "self_history": "engine's own resolution record",
                "method": "calibration engine self-assessment",
            },
            producing_agent_id=self.SELF_AGENT_ID,
            producing_prompt_version=self.SELF_PROMPT_VERSION,
            resolution_criterion=resolution_criterion,
            resolution_date=resolution_date,
            ground_truth_source="external_auditor_or_human_spot_audit",
            horizon_class="short",
            domain=domain,
            claim_type=claim_type,
        )
        prediction_id = self.ledger.pre_register(reg)
        logger.info("SELF-AUDIT: engine made self-prediction %s p=%.3f", prediction_id, probability)
        return prediction_id

    def generate_report(self, calibration_report: Optional["CalibrationReport"] = None) -> SelfAuditReport:
        """
        Generate a self-audit report. Explicitly states blind-spot limits.
        Never claims calibration not earned.
        """
        self_preds = self.ledger.list_by_agent(self.SELF_AGENT_ID)
        resolved = [p for p in self_preds if p.resolved]
        surprises = self.surprise_register.list_all() if self.surprise_register else []
        recent_surprises = [
            {
                "id": s.surprise_id,
                "agent": s.producing_agent_id,
                "domain": s.domain,
                "score": s.surprise_score,
                "at": s.registered_at.isoformat(),
                "investigated": s.investigated,
            }
            for s in surprises[-10:]
        ]

        self_ece = calibration_report.ece if calibration_report else None

        return SelfAuditReport(
            generated_at=datetime.now(timezone.utc),
            self_prediction_count=len(self_preds),
            self_predictions_resolved=len(resolved),
            self_ece=self_ece,
            stated_blind_spot_limit=(
                "This engine has earned calibration only on domains and horizons with sufficient "
                "resolved predictions (n >= 5). Tail events (>3 sigma), novel domain combinations, "
                "and claim types with < 5 resolutions have UNEARNED calibration — treat as p=0.5. "
                "We do not simulate unknown unknowns; we maximise surprise detection instead."
            ),
            recent_surprises=recent_surprises,
            trust_score_trend="stable",  # In production: computed from Trust Controller trend
            spot_audit_ready=True,  # Always True — engine cannot anticipate spot audits
            human_spot_audit_log=list(self._spot_audit_log),
        )

    def record_spot_audit(
        self,
        auditor_id: str,
        findings: str,
        passed: bool,
        prediction_sample: list[str],
    ) -> str:
        """Record an unannounced human spot-audit result."""
        audit_id = str(uuid.uuid4())
        self._spot_audit_log.append({
            "audit_id": audit_id,
            "auditor_id": auditor_id,
            "conducted_at": datetime.now(timezone.utc).isoformat(),
            "passed": passed,
            "findings": findings,
            "prediction_sample_ids": prediction_sample,
        })
        logger.info(
            "SPOT AUDIT RECORDED: id=%s auditor=%s passed=%s",
            audit_id, auditor_id, passed
        )
        return audit_id
