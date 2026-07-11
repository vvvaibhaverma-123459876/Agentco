from __future__ import annotations

import json
import os
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from runtime.base_agent.audit_writer import AuditUnavailableError, AuditWriter, InMemoryAuditWriter
from runtime.controlled_learning.schema import (
    LEARNING_ARTIFACT_VERSION,
    LEARNING_PIPELINE_VERSION,
    BenchmarkImpact,
    LearningArtifact,
    LearningState,
    PromotionEvent,
    ProtectedSurface,
    RollbackTrigger,
    artifact_id_for,
    stable_json,
)
from runtime.evaluation.schema import EvaluationAuditEntry


class ControlledLearningError(RuntimeError):
    """Raised when a learning artifact violates the controlled promotion protocol."""


class LearningArtifactStore:
    def __init__(self) -> None:
        self._artifacts: dict[str, LearningArtifact] = {}
        self._fingerprints: dict[str, str] = {}

    def put(self, artifact: LearningArtifact) -> LearningArtifact:
        existing = self._artifacts.get(artifact.artifact_id)
        fingerprint = artifact.fingerprint()
        if existing is not None and self._fingerprints[artifact.artifact_id] != fingerprint:
            raise ControlledLearningError(f"historical artifact cannot be altered: {artifact.artifact_id}")
        self._artifacts[artifact.artifact_id] = artifact
        self._fingerprints[artifact.artifact_id] = fingerprint
        return artifact

    def get(self, artifact_id: str) -> LearningArtifact:
        try:
            return self._artifacts[artifact_id]
        except KeyError as exc:
            raise ControlledLearningError(f"unknown learning artifact: {artifact_id}") from exc

    def all(self) -> tuple[LearningArtifact, ...]:
        return tuple(self._artifacts.values())


class FileLearningArtifactStore(LearningArtifactStore):
    """JSON-backed artifact repository proving artifacts persist across runs."""

    def __init__(self, path: Path):
        super().__init__()
        self.path = path
        if path.exists():
            payload = json.loads(path.read_text())
            for item in payload:
                artifact = _artifact_from_dict(item)
                super().put(artifact)

    def put(self, artifact: LearningArtifact) -> LearningArtifact:
        result = super().put(artifact)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([asdict(item) for item in self.all()], indent=2, sort_keys=True) + "\n")
        return result


def _artifact_from_dict(data: dict[str, Any]) -> LearningArtifact:
    impact = BenchmarkImpact(**data["benchmark_impact"])
    promotions = tuple(PromotionEvent(**event) for event in data.get("promotion_history", ()))
    rollbacks = tuple(PromotionEvent(**event) for event in data.get("rollback_history", ()))
    return LearningArtifact(
        artifact_id=data["artifact_id"],
        source_observations=tuple(data["source_observations"]),
        evaluation_record_ids=tuple(data["evaluation_record_ids"]),
        proposed_change=data["proposed_change"],
        evidence_refs=tuple(data["evidence_refs"]),
        benchmark_impact=impact,
        proposer_id=data["proposer_id"],
        approval_status=data["approval_status"],
        artifact_version=data["artifact_version"],
        state=data["state"],
        promotion_history=promotions,
        rollback_history=rollbacks,
        previous_active_artifact_id=data.get("previous_active_artifact_id"),
        created_at=data["created_at"],
    )


class ControlledLearningPipeline:
    PROTECTED_SURFACES: set[ProtectedSurface] = {"prompt", "policy", "tool", "model", "memory_rule"}

    def __init__(self, store: LearningArtifactStore | None = None, audit_writer: AuditWriter | None = None):
        production = os.environ.get("AGENTCO_ENV") in {"production", "staging"} or os.environ.get("NODE_ENV") == "production"
        if production and store is None:
            raise ControlledLearningError("production controlled learning requires an explicit durable artifact repository")
        if production and audit_writer is None:
            raise AuditUnavailableError("production controlled learning requires an explicit durable audit writer")
        self.store = store or LearningArtifactStore()
        self.audit_writer = audit_writer or InMemoryAuditWriter(allow_test_mode=True)
        self.active_versions: dict[str, str] = {}

    def propose(
        self,
        *,
        proposer_id: str,
        source_observations: tuple[str, ...],
        evaluation_record_ids: tuple[str, ...],
        proposed_change: dict[str, Any],
        evidence_refs: tuple[str, ...],
        benchmark_impact: BenchmarkImpact,
    ) -> LearningArtifact:
        artifact_id = artifact_id_for(proposer_id, proposed_change, evidence_refs)
        artifact = LearningArtifact(
            artifact_id=artifact_id,
            source_observations=source_observations,
            evaluation_record_ids=evaluation_record_ids,
            proposed_change=proposed_change,
            evidence_refs=evidence_refs,
            benchmark_impact=benchmark_impact,
            proposer_id=proposer_id,
            approval_status="pending",
            artifact_version=LEARNING_ARTIFACT_VERSION,
        )
        return self.store.put(artifact)

    def evaluate_offline(self, artifact_id: str) -> LearningArtifact:
        artifact = self.store.get(artifact_id)
        self._require_phase10_evidence(artifact)
        self._reject_tampered_evidence(artifact)
        state: LearningState = "rejected" if artifact.benchmark_impact.regression else "evaluated"
        return self.store.put(replace(artifact, state=state, approval_status="rejected" if state == "rejected" else "evaluated"))

    def approve(self, artifact_id: str, *, approver_id: str, authorization_id: str) -> LearningArtifact:
        artifact = self.store.get(artifact_id)
        if artifact.state != "evaluated":
            raise ControlledLearningError("only evaluated artifacts can be approved")
        if approver_id == artifact.proposer_id:
            raise ControlledLearningError("self-approved learning changes are rejected")
        if not authorization_id:
            raise ControlledLearningError("production changes require explicit authorization")
        return self.store.put(replace(artifact, state="approved", approval_status=f"approved:{approver_id}:{authorization_id}"))

    def stage_canary(self, artifact_id: str, *, actor_id: str) -> LearningArtifact:
        artifact = self.store.get(artifact_id)
        if artifact.state != "approved":
            raise ControlledLearningError("only approved artifacts can enter canary")
        event = self._audit_event(artifact, "approved", "canary", actor_id, "staged canary")
        return self.store.put(replace(artifact, state="canary", promotion_history=artifact.promotion_history + (event,)))

    def promote(self, artifact_id: str, *, actor_id: str) -> LearningArtifact:
        artifact = self.store.get(artifact_id)
        if artifact.state == "promoted":
            return artifact
        if artifact.state != "canary":
            raise ControlledLearningError("only canary artifacts can be promoted")
        self._require_phase10_evidence(artifact)
        self._block_regressions(artifact)
        self._reject_unauthorized_mutation(actor_id, artifact)
        surface = self._surface(artifact)
        previous = self.active_versions.get(surface)
        event = self._audit_event(artifact, "canary", "promoted", actor_id, "promoted controlled learning artifact")
        promoted = replace(
            artifact,
            state="promoted",
            previous_active_artifact_id=previous,
            promotion_history=artifact.promotion_history + (event,),
        )
        self.active_versions[surface] = artifact.artifact_id
        return self.store.put(promoted)

    def rollback(self, artifact_id: str, *, actor_id: str, trigger: RollbackTrigger) -> LearningArtifact:
        artifact = self.store.get(artifact_id)
        if artifact.state not in {"canary", "promoted"}:
            raise ControlledLearningError("only canary/promoted artifacts can be rolled back")
        surface = self._surface(artifact)
        previous = artifact.previous_active_artifact_id
        if previous:
            self.active_versions[surface] = previous
        else:
            self.active_versions.pop(surface, None)
        event = self._audit_event(artifact, artifact.state, "rolled_back", actor_id, f"rollback:{trigger}")
        return self.store.put(replace(artifact, state="rolled_back", rollback_history=artifact.rollback_history + (event,)))

    def monitor(self, artifact_id: str, *, actor_id: str) -> LearningArtifact:
        artifact = self.store.get(artifact_id)
        trigger = rollback_trigger_for(artifact)
        if trigger is None:
            return artifact
        return self.rollback(artifact_id, actor_id=actor_id, trigger=trigger)

    def _surface(self, artifact: LearningArtifact) -> str:
        surface = artifact.proposed_change.get("surface")
        if surface not in self.PROTECTED_SURFACES:
            raise ControlledLearningError(f"unsupported production surface: {surface}")
        return str(surface)

    def _require_phase10_evidence(self, artifact: LearningArtifact) -> None:
        if not artifact.evaluation_record_ids:
            raise ControlledLearningError("promotion requires Phase 10 evaluation evidence")
        if not all(record_id.startswith("phase10:") for record_id in artifact.evaluation_record_ids):
            raise ControlledLearningError("evaluation evidence must be Phase 10 records")
        if os.environ.get("AGENTCO_ENV") in {"production", "staging"} or os.environ.get("NODE_ENV") == "production":
            raise ControlledLearningError(
                "production promotion requires record-backed Phase 10 evidence repository integration"
            )

    def _reject_tampered_evidence(self, artifact: LearningArtifact) -> None:
        if any(ref.startswith("tampered:") for ref in artifact.evidence_refs):
            raise ControlledLearningError("tampered evidence is rejected")

    def _block_regressions(self, artifact: LearningArtifact) -> None:
        if artifact.benchmark_impact.regression:
            raise ControlledLearningError("benchmark regressions block promotion")

    def _reject_unauthorized_mutation(self, actor_id: str, artifact: LearningArtifact) -> None:
        if actor_id == artifact.proposer_id:
            raise ControlledLearningError("proposer cannot directly modify production behavior")
        if not artifact.approval_status.startswith("approved:"):
            raise ControlledLearningError("production mutation requires prior approval")
        self._surface(artifact)

    def _audit_event(
        self,
        artifact: LearningArtifact,
        from_state: LearningState,
        to_state: LearningState,
        actor_id: str,
        reason: str,
    ) -> PromotionEvent:
        event_id = f"{artifact.artifact_id}:{from_state}->{to_state}:{reason}"
        entry = EvaluationAuditEntry(
            agent_id=actor_id,
            prompt_version=LEARNING_PIPELINE_VERSION,
            action_type="decision",
            description=stable_json({
                "artifact_id": artifact.artifact_id,
                "from_state": from_state,
                "to_state": to_state,
                "reason": reason,
                "artifact_version": artifact.artifact_version,
            }),
            stated_confidence=1.0,
            trusted_confidence=1.0,
            risk_level="medium",
            domain="controlled_learning",
            prediction_id=None,
            override_id=None,
            outcome=to_state,
            attempt_id=event_id,
            trace_id=event_id,
        )
        ack = self.audit_writer.write(entry)
        if not ack or not ack.get("log_id"):
            raise AuditUnavailableError("learning promotion event was not audited")
        return PromotionEvent(
            event_id=event_id,
            artifact_id=artifact.artifact_id,
            from_state=from_state,
            to_state=to_state,
            actor_id=actor_id,
            reason=reason,
            audit_log_id=ack["log_id"],
            audit_backend=ack.get("backend", "unknown"),
        )


def rollback_trigger_for(artifact: LearningArtifact) -> RollbackTrigger | None:
    impact = artifact.benchmark_impact
    if impact.regression:
        return "benchmark_regression"
    if impact.calibration_delta > 0.05:
        return "calibration_degradation"
    if impact.unsupported_claim_delta > 0.02:
        return "unsupported_claim_increase"
    if artifact.approval_status.startswith("rejected"):
        return "policy_or_authorization_failure"
    if any(not event.audit_log_id for event in artifact.promotion_history + artifact.rollback_history):
        return "audit_chain_failure"
    return None
