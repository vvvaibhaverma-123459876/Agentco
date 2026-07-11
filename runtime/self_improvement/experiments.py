from __future__ import annotations

import json
import os
from dataclasses import asdict, replace
from typing import Any

from runtime.base_agent.audit_writer import AuditUnavailableError, AuditWriter, InMemoryAuditWriter
from runtime.controlled_learning.schema import BenchmarkImpact
from runtime.evaluation.evaluators import EvaluationError, PostgresEvaluationStore
from runtime.evaluation.schema import EvaluationAuditEntry
from runtime.self_improvement.schema import (
    IMPROVEMENT_EXPERIMENT_VERSION,
    ExperimentKind,
    ExperimentOutcome,
    ExperimentUsage,
    ImprovementExperiment,
    ResourceBudget,
    RiskLevel,
    experiment_id_for,
    stable_json,
)


class SelfImprovementError(RuntimeError):
    """Raised when a bounded self-improvement experiment violates scope or safety controls."""


class ExperimentStore:
    def __init__(self) -> None:
        self._experiments: dict[str, ImprovementExperiment] = {}
        self._fingerprints: dict[str, str] = {}

    def put(self, experiment: ImprovementExperiment) -> ImprovementExperiment:
        existing = self._experiments.get(experiment.experiment_id)
        fingerprint = experiment.fingerprint()
        if existing is not None:
            if self._fingerprints[experiment.experiment_id] != fingerprint:
                raise SelfImprovementError(f"historical experiment cannot be altered: {experiment.experiment_id}")
            if existing.audit_log_id is None and experiment.audit_log_id is not None:
                self._experiments[experiment.experiment_id] = experiment
                return experiment
            return existing
        self._experiments[experiment.experiment_id] = experiment
        self._fingerprints[experiment.experiment_id] = fingerprint
        return experiment

    def all(self) -> tuple[ImprovementExperiment, ...]:
        return tuple(self._experiments.values())


class PostgresExperimentStore(ExperimentStore):
    """Postgres-backed bounded self-improvement experiment repository."""

    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise SelfImprovementError("PostgresExperimentStore requires a database DSN")
        super().__init__()
        self._dsn = dsn

    def put(self, experiment: ImprovementExperiment) -> ImprovementExperiment:
        payload = asdict(experiment)
        fingerprint = experiment.fingerprint()
        psycopg2 = _psycopg2()
        conn = psycopg2.connect(self._dsn)
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO runtime_improvement_experiments
                      (experiment_id, experiment_version, proposer_id, evaluator,
                       experiment_kind, outcome, promotion_recommendation,
                       payload, immutable_fingerprint, audit_log_id, audit_backend)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)
                    ON CONFLICT (experiment_id) DO UPDATE
                       SET audit_log_id = COALESCE(runtime_improvement_experiments.audit_log_id, EXCLUDED.audit_log_id),
                           audit_backend = COALESCE(runtime_improvement_experiments.audit_backend, EXCLUDED.audit_backend)
                     WHERE runtime_improvement_experiments.immutable_fingerprint = EXCLUDED.immutable_fingerprint
                    RETURNING payload, audit_log_id, audit_backend
                    """,
                    [
                        experiment.experiment_id,
                        experiment.experiment_version,
                        experiment.proposer_id,
                        experiment.evaluator,
                        experiment.experiment_kind,
                        experiment.outcome,
                        experiment.promotion_recommendation,
                        json.dumps(payload, sort_keys=True, default=str),
                        fingerprint,
                        experiment.audit_log_id,
                        experiment.audit_backend,
                    ],
                )
                row = cur.fetchone()
                if row is None:
                    raise SelfImprovementError(f"historical experiment cannot be altered: {experiment.experiment_id}")
            conn.commit()
            return _experiment_from_row(row[0], row[1], row[2])
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def all(self) -> tuple[ImprovementExperiment, ...]:
        psycopg2 = _psycopg2()
        conn = psycopg2.connect(self._dsn)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT payload, audit_log_id, audit_backend FROM runtime_improvement_experiments ORDER BY created_at, experiment_id"
                )
                return tuple(_experiment_from_row(row[0], row[1], row[2]) for row in cur.fetchall())
        finally:
            conn.close()


def configured_experiment_store() -> PostgresExperimentStore:
    dsn = os.environ.get("AGENTCO_EXPERIMENT_DATABASE_URL") or os.environ.get("DATABASE_URL") or os.environ.get("AGENTCO_TEST_DATABASE_URL")
    if not dsn:
        raise SelfImprovementError("production self-improvement requires AGENTCO_EXPERIMENT_DATABASE_URL or DATABASE_URL")
    return PostgresExperimentStore(dsn)


def configured_evaluation_store() -> PostgresEvaluationStore | None:
    dsn = os.environ.get("AGENTCO_EVALUATION_DATABASE_URL") or os.environ.get("DATABASE_URL") or os.environ.get("AGENTCO_TEST_DATABASE_URL")
    return PostgresEvaluationStore(dsn) if dsn else None


def _experiment_from_dict(data: dict[str, Any]) -> ImprovementExperiment:
    if isinstance(data, str):
        data = json.loads(data)
    return ImprovementExperiment(
        experiment_id=data["experiment_id"],
        hypothesis=data["hypothesis"],
        target_capability=data["target_capability"],
        proposed_change=data["proposed_change"],
        evidence_refs=tuple(data["evidence_refs"]),
        benchmark_refs=tuple(data["benchmark_refs"]),
        allowed_scope=tuple(data["allowed_scope"]),
        resource_budget=ResourceBudget(**data["resource_budget"]),
        risk_level=data["risk_level"],
        evaluator=data["evaluator"],
        proposer_id=data["proposer_id"],
        experiment_kind=data["experiment_kind"],
        outcome=data["outcome"],
        promotion_recommendation=data["promotion_recommendation"],
        resource_usage=ExperimentUsage(**data["resource_usage"]),
        safety_violations=tuple(data.get("safety_violations", ())),
        audit_log_id=data.get("audit_log_id"),
        audit_backend=data.get("audit_backend"),
        experiment_version=data["experiment_version"],
        created_at=data["created_at"],
    )


def _experiment_from_row(data: dict[str, Any], audit_log_id: Any, audit_backend: str | None) -> ImprovementExperiment:
    experiment = _experiment_from_dict(data)
    return replace(
        experiment,
        audit_log_id=str(audit_log_id) if audit_log_id is not None else experiment.audit_log_id,
        audit_backend=audit_backend or experiment.audit_backend,
    )


class BoundedExperimentRunner:
    ALLOWED_KINDS: set[ExperimentKind] = {
        "prompt_variant",
        "policy_proposal",
        "tool_selection_strategy",
        "memory_rule_proposal",
        "model_routing_strategy",
    }
    FORBIDDEN_CHANGE_TYPES = {"model_weight_update", "unrestricted_code_rewrite"}
    PRODUCTION_SURFACES = {"production_data", "credential", "policy", "tool", "model", "memory_rule"}

    def __init__(
        self,
        store: ExperimentStore | None = None,
        audit_writer: AuditWriter | None = None,
        evaluation_store: Any | None = None,
    ):
        production = os.environ.get("AGENTCO_ENV") in {"production", "staging"} or os.environ.get("NODE_ENV") == "production"
        if production and store is None:
            store = configured_experiment_store()
        if production and evaluation_store is None:
            evaluation_store = configured_evaluation_store()
        if production and store is None:
            raise SelfImprovementError("production self-improvement requires an explicit durable experiment repository")
        if production and audit_writer is None:
            raise AuditUnavailableError("production self-improvement requires an explicit durable audit writer")
        if production and isinstance(audit_writer, InMemoryAuditWriter):
            raise AuditUnavailableError("production self-improvement cannot use InMemoryAuditWriter")
        self.store = store or ExperimentStore()
        self.audit_writer = audit_writer or InMemoryAuditWriter(allow_test_mode=True)
        self.evaluation_store = evaluation_store
        self.production_state: dict[str, str] = {"prompt": "prompt-v1", "policy": "policy-v1"}

    def run(
        self,
        *,
        hypothesis: str,
        target_capability: str,
        proposed_change: dict[str, Any],
        evidence_refs: tuple[str, ...],
        benchmark_refs: tuple[str, ...],
        allowed_scope: tuple[str, ...],
        resource_budget: ResourceBudget,
        risk_level: RiskLevel,
        evaluator: str,
        proposer_id: str,
        experiment_kind: ExperimentKind,
        requested_tools: tuple[str, ...] = (),
        allowed_tools: tuple[str, ...] = (),
        resource_usage: ExperimentUsage | None = None,
        benchmark_impact: BenchmarkImpact | None = None,
        wants_production_mutation: bool = False,
        approval_actor: str | None = None,
    ) -> ImprovementExperiment:
        resource_budget.validate()
        experiment_id = experiment_id_for(
            hypothesis=hypothesis,
            target_capability=target_capability,
            proposed_change=proposed_change,
            allowed_scope=allowed_scope,
            proposer_id=proposer_id,
        )
        existing = next((item for item in self.store.all() if item.experiment_id == experiment_id), None)
        if existing is not None:
            return existing

        usage = resource_usage or ExperimentUsage(seconds=1, spend_cents=1, tool_calls=len(requested_tools), scope_items=len(allowed_scope))
        violations = self._violations(
            proposed_change=proposed_change,
            evidence_refs=evidence_refs,
            benchmark_refs=benchmark_refs,
            allowed_scope=allowed_scope,
            resource_budget=resource_budget,
            resource_usage=usage,
            experiment_kind=experiment_kind,
            requested_tools=requested_tools,
            allowed_tools=allowed_tools,
            wants_production_mutation=wants_production_mutation,
            proposer_id=proposer_id,
            approval_actor=approval_actor,
        )
        outcome: ExperimentOutcome = "accepted"
        recommendation = "propose_phase11_artifact"
        if violations:
            outcome = "blocked"
            recommendation = "none"
        elif benchmark_impact and benchmark_impact.regression:
            outcome = "rejected"
            recommendation = "none"

        experiment = ImprovementExperiment(
            experiment_id=experiment_id,
            hypothesis=hypothesis,
            target_capability=target_capability,
            proposed_change=proposed_change,
            evidence_refs=evidence_refs,
            benchmark_refs=benchmark_refs,
            allowed_scope=allowed_scope,
            resource_budget=resource_budget,
            risk_level=risk_level,
            evaluator=evaluator,
            proposer_id=proposer_id,
            experiment_kind=experiment_kind,
            outcome=outcome,
            promotion_recommendation=recommendation,
            resource_usage=usage,
            safety_violations=tuple(violations),
        )
        ack = self._audit(experiment)
        audited = replace(experiment, audit_log_id=ack["log_id"], audit_backend=ack.get("backend", "unknown"))
        return self.store.put(audited)

    def _violations(
        self,
        *,
        proposed_change: dict[str, Any],
        evidence_refs: tuple[str, ...],
        benchmark_refs: tuple[str, ...],
        allowed_scope: tuple[str, ...],
        resource_budget: ResourceBudget,
        resource_usage: ExperimentUsage,
        experiment_kind: ExperimentKind,
        requested_tools: tuple[str, ...],
        allowed_tools: tuple[str, ...],
        wants_production_mutation: bool,
        proposer_id: str,
        approval_actor: str | None,
    ) -> list[str]:
        violations: list[str] = []
        if experiment_kind not in self.ALLOWED_KINDS:
            violations.append("unsupported_experiment_kind")
        if proposed_change.get("change_type") in self.FORBIDDEN_CHANGE_TYPES:
            violations.append("forbidden_change_type")
        if not allowed_scope:
            violations.append("missing_scope")
        if not evidence_refs or not benchmark_refs:
            violations.append("missing_evidence_or_benchmark_refs")
        if os.environ.get("AGENTCO_ENV") in {"production", "staging"} or os.environ.get("NODE_ENV") == "production":
            if self.evaluation_store is None:
                violations.append("missing_durable_evaluation_store")
            else:
                for ref in evidence_refs:
                    try:
                        record = self.evaluation_store.get(ref)
                    except EvaluationError:
                        violations.append("missing_evaluation_record")
                        continue
                    if not record.passed:
                        violations.append("failed_evaluation_record")
                    if record.agent_id != proposed_change.get("subject_id", record.agent_id):
                        violations.append("wrong_subject_evaluation_record")
        if any(ref.startswith("tampered:") for ref in evidence_refs):
            violations.append("tampered_evidence")
        if any(item.startswith("production:") for item in allowed_scope):
            violations.append("scope_escape")
        if wants_production_mutation:
            violations.append("production_mutation_rejected")
        if set(requested_tools) - set(allowed_tools):
            violations.append("unauthorized_tool")
        if resource_usage.seconds > resource_budget.max_seconds:
            violations.append("time_budget_exceeded")
        if resource_usage.spend_cents > resource_budget.max_spend_cents:
            violations.append("spend_budget_exceeded")
        if resource_usage.tool_calls > resource_budget.max_tool_calls:
            violations.append("tool_budget_exceeded")
        if resource_usage.scope_items > resource_budget.max_scope_items:
            violations.append("scope_budget_exceeded")
        if approval_actor == proposer_id:
            violations.append("self_approval_rejected")
        return violations

    def _audit(self, experiment: ImprovementExperiment) -> dict[str, str]:
        entry = EvaluationAuditEntry(
            agent_id=experiment.evaluator,
            prompt_version=IMPROVEMENT_EXPERIMENT_VERSION,
            action_type="decision",
            description=stable_json({
                "experiment_id": experiment.experiment_id,
                "hypothesis": experiment.hypothesis,
                "outcome": experiment.outcome,
                "promotion_recommendation": experiment.promotion_recommendation,
                "safety_violations": experiment.safety_violations,
            }),
            stated_confidence=1.0,
            trusted_confidence=1.0,
            risk_level="medium" if experiment.outcome == "accepted" else "low",
            domain="bounded_self_improvement",
            prediction_id=None,
            override_id=None,
            outcome=experiment.outcome,
            attempt_id=experiment.experiment_id,
            trace_id=experiment.experiment_id,
        )
        ack = self.audit_writer.write(entry)
        if not ack or not ack.get("log_id"):
            raise AuditUnavailableError("self-improvement experiment was not audited")
        return ack


def _psycopg2() -> Any:
    try:
        import psycopg2
    except Exception as exc:
        raise SelfImprovementError("psycopg2 is required for durable experiment storage") from exc
    return psycopg2
