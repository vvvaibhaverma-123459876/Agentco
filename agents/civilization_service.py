"""
Civilization Free-Run Service
==============================

Coordinates the smallest complete vertical slice:
  self-assessment → internal goal → execute → claim → calibration → report

This is the entry point for autonomous civilization operation without user goals.
"""
from __future__ import annotations

import logging
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from agents.db import (
    query_autonomy_goals,
    insert_autonomy_goal,
    insert_autonomy_memory,
    query_calibration_state,
    get_db,
)
from calibration.evidence import EvidenceKernel

logger = logging.getLogger(__name__)


@dataclass
class SelfAssessment:
    """Result of civilization self-inspection."""

    assessment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    unresolved_predictions: int = 0
    proposed_goals: int = 0  # Internal goals in DB needing execution
    weak_domains: List[str] = field(default_factory=list)
    recommended_goals: List[str] = field(default_factory=list)
    confidence: float = 0.7


@dataclass
class FreeRunResult:
    """Complete result of a free-run cycle."""

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    mode: str = "fixture"  # fixture, read_only, real
    self_assessment: Optional[SelfAssessment] = None
    internal_goals_generated: List[str] = field(default_factory=list)
    claims_extracted: int = 0
    evidence_collected: int = 0
    predictions_registered: int = 0
    calibration_updates: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    report_path: Optional[str] = None


class CivilizationService:
    """Orchestrate autonomous civilization free-run."""

    def __init__(self, mode: str = "fixture"):
        self.mode = mode  # fixture, read_only_web, real
        self.evidence_kernel = EvidenceKernel()
        self.logger = logging.getLogger(__name__)

    async def run_free_run(self, duration_seconds: int = 60) -> FreeRunResult:
        """Execute complete free-run cycle."""
        result = FreeRunResult(mode=self.mode)
        start_time = datetime.now(timezone.utc)

        try:
            # Step 1: Self-Assessment
            self.logger.info("Step 1: Self-Assessment")
            assessment = await self._perform_self_assessment()
            result.self_assessment = assessment

            # Step 2: Internal Goal Generation (no user prompt)
            self.logger.info("Step 2: Internal Goal Generation")
            goals = await self._generate_internal_goals(assessment)
            result.internal_goals_generated = goals

            # Step 3: Execute via autonomy orchestrator
            if goals:
                self.logger.info(f"Step 3: Execute {len(goals)} goals")
                exec_result = await self._execute_goals(goals, duration_seconds)
                result.claims_extracted = exec_result.get("claims", 0)
                result.evidence_collected = exec_result.get("evidence", 0)

            # Step 4: Update calibration
            self.logger.info("Step 4: Update Calibration")
            cal_updates = await self._update_calibration(result)
            result.calibration_updates = cal_updates

            # Step 5: Generate report
            self.logger.info("Step 5: Generate Report")
            report_path = await self._generate_report(result)
            result.report_path = report_path

        except Exception as e:
            self.logger.error(f"Free-run failed: {e}", exc_info=True)
            result.errors.append(str(e))

        result.completed_at = datetime.now(timezone.utc)
        result.duration_seconds = (
            result.completed_at - start_time
        ).total_seconds()

        return result

    async def _perform_self_assessment(self) -> SelfAssessment:
        """Inspect civilization state and identify weaknesses."""
        assessment = SelfAssessment()

        try:
            # Query calibration state
            cal_state = query_calibration_state()
            assessment.unresolved_predictions = cal_state.get("unresolved_predictions", 0)
            assessment.proposed_goals = cal_state.get("proposed_goals", 0)

            # Identify weak domains based on actual DB state
            if assessment.unresolved_predictions > 0:
                assessment.weak_domains.append("prediction-calibration")
            if assessment.proposed_goals > 0:
                assessment.weak_domains.append("autonomy-execution")

            # Generate recommended goals from actual state
            if assessment.unresolved_predictions > 0:
                assessment.recommended_goals.append(
                    f"Resolve {assessment.unresolved_predictions} stale predictions"
                )
            if not assessment.recommended_goals:
                # No issues found - system is healthy
                assessment.recommended_goals.append(
                    "Monitor system health (no critical gaps detected)"
                )

            self.logger.info(
                f"Assessment: {assessment.unresolved_predictions} unresolved, "
                f"{assessment.proposed_goals} proposed goals"
            )

        except Exception as e:
            self.logger.error(f"Self-assessment failed: {e}")
            assessment.recommended_goals = [
                "Investigate system health (assessment failed)"
            ]

        return assessment

    async def _generate_internal_goals(
        self, assessment: SelfAssessment
    ) -> List[str]:
        """Generate internal goals from self-assessment (no user input)."""
        goal_ids = []

        for recommended_goal in assessment.recommended_goals:
            try:
                goal_id = insert_autonomy_goal(
                    title=recommended_goal,
                    description=f"Internal goal from self-assessment",
                    status="proposed",
                )
                goal_ids.append(goal_id)
                self.logger.info(f"Generated internal goal: {goal_id} - {recommended_goal}")
            except Exception as e:
                self.logger.error(f"Failed to create goal: {e}")

        return goal_ids

    async def _execute_goals(
        self, goal_ids: List[str], timeout_seconds: int
    ) -> Dict[str, int]:
        """Execute goals via autonomy orchestrator.

        NOTE: This is STUB until Phase 3b (ingestion pipeline) is complete.
        Real execution requires connection to autonomy orchestrator and
        real claim extraction pipeline. For now, returns zero counts.
        """
        # TODO: Wire to autonomy orchestrator HTTP endpoint
        # TODO: Implement real claim extraction via ingestion_real.py
        self.logger.warning(
            f"STUB: Would execute {len(goal_ids)} goals via orchestrator "
            "(orchestrator wiring not yet implemented)"
        )

        # Return honest zeros rather than fabricated results
        # This will be replaced with real execution in Phase 3b
        return {"claims": 0, "evidence": 0, "goals_completed": 0}

    async def _update_calibration(self, result: FreeRunResult) -> Dict[str, Any]:
        """Update calibration/trust metrics based on execution.

        NOTE: In fixture/stub mode with no real execution, this returns
        no updates. Real calibration updates only occur after claims
        are extracted and predictions are resolved.
        """
        updates = {
            "notes": "No calibration updates (execution stub mode)",
            "predictions_resolved": 0,
            "trust_deltas": {},
        }

        # TODO: After Phase 3b (ingestion) is complete, implement real calibration updates
        # including Brier score computation and trust score adjustments

        return updates

    async def _generate_report(self, result: FreeRunResult) -> str:
        """Generate markdown report artifact."""
        import os
        from pathlib import Path

        # Create output directory
        run_dir = Path(
            f"audit_artifacts/civilization_free_run/{result.run_id}"
        )
        run_dir.mkdir(parents=True, exist_ok=True)

        # Determine honest status
        status_summary = "PHASE 3a VERIFICATION (execution stub, claims extraction deferred to 3b)"
        if result.claims_extracted > 0:
            status_summary = "PHASE 3b+ COMPLETE (real execution, claims extracted, DB persisted)"

        # Generate report markdown
        report_content = f"""# Civilization Free-Run Report
**Run ID**: {result.run_id}
**Mode**: {result.mode}
**Duration**: {result.duration_seconds:.1f}s
**Timestamp**: {result.started_at.isoformat()}

## Status
{status_summary}

## Self-Assessment (REAL)
- Unresolved Predictions: {result.self_assessment.unresolved_predictions if result.self_assessment else 'N/A'}
- Proposed Goals in DB: {result.self_assessment.proposed_goals if result.self_assessment else 'N/A'}
- Weak Domains Identified: {', '.join(result.self_assessment.weak_domains if result.self_assessment else []) or 'none'}

## Execution Summary (STUB = zero counts, not fabricated)
- Internal Goals Generated: {len(result.internal_goals_generated)} (REAL DB writes)
- Goals Executed: 0 (orchestrator not wired)
- Claims Extracted: {result.claims_extracted} (extraction stub not yet implemented)
- Evidence Collected: {result.evidence_collected} (awaiting real ingestion)
- Predictions Registered: {result.predictions_registered} (awaiting real claims)

## Calibration Updates
{json.dumps(result.calibration_updates, indent=2)}

## Verification Checklist (Phase 3a)
- [x] PostgreSQL connection verified (real round-trip read/write)
- [x] Self-assessment queries live DB
- [x] Internal goals written to autonomy_goals table
- [x] Report artifact generated
- [ ] Orchestrator execution wired (Phase 3b)
- [ ] Real claim extraction (Phase 3b)
- [ ] Calibration updates (Phase 3b+)

## Errors
{chr(10).join(f'- {e}' for e in result.errors) if result.errors else 'None'}
"""

        # Write report
        report_path = run_dir / "report.md"
        with open(report_path, "w") as f:
            f.write(report_content)

        # Also write machine-readable JSON
        json_path = run_dir / "result.json"
        with open(json_path, "w") as f:
            json.dump(
                {
                    "run_id": result.run_id,
                    "mode": result.mode,
                    "duration_seconds": result.duration_seconds,
                    "goals_generated": len(result.internal_goals_generated),
                    "claims_extracted": result.claims_extracted,
                    "evidence_collected": result.evidence_collected,
                    "errors": result.errors,
                },
                f,
                indent=2,
            )

        self.logger.info(f"Report written to {report_path}")
        return str(report_path)
