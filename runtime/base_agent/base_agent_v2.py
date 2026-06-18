"""
BaseAgentV2 — V2 agent contract.

Every agent subclassing BaseAgentV2 MUST:
1. Pre-register falsifiable forward claims before acting
2. Use trusted_confidence() not stated confidence in decisions
3. Carry producer_prompt_version in every event envelope
4. Block on human approval — no auto-approve on timeout

The audit log captures: agent_id, prompt_version, action, trusted_confidence,
stated_confidence, prediction_id (if a claim was pre-registered), and all
downstream events triggered.
"""
from __future__ import annotations

import hashlib
import hmac
import asyncio
import json
import logging
import os
import uuid
from abc import abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from calibration.ledger.prediction_ledger import PredictionRegistration
from runtime.base_agent.llm_client import client_for
from runtime.base_agent.model_tiers import model_for
from runtime.base_agent.spend_guardrail import SpendGuardrail
from runtime.base_agent.structured_output import get_validated_output

logger = logging.getLogger(__name__)

_HMAC_KEY = os.environ.get("EVENT_BUS_HMAC_KEY", "dev-insecure-key").encode()


@dataclass
class AgentActionV2:
    """Represents a single action an agent is about to take."""
    action_type: str
    description: str
    payload: dict
    risk_level: str = "low"          # "low" | "medium" | "high" | "critical"
    stated_confidence: float = 0.7
    domain: str = "general"
    claim_type: str = "general"
    horizon_class: str = "short"


@dataclass
class AuditEntryV2:
    agent_id: str
    prompt_version: str
    action_type: str
    description: str
    stated_confidence: float
    trusted_confidence: float
    risk_level: str
    domain: str
    prediction_id: Optional[str]
    override_id: Optional[str]
    outcome: str                    # "executed" | "blocked" | "rejected"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))


def _sign_envelope(envelope: dict) -> str:
    body = json.dumps(envelope, sort_keys=True, default=str).encode()
    return hmac.new(_HMAC_KEY, body, hashlib.sha256).hexdigest()


class BaseAgentV2:
    """
    V2 base agent. Subclass and implement `run()`.

    Wire calibration components via `__init__` parameters or set them on the
    instance before calling `execute_action()`.
    """

    PROMPT_VERSION: str = "2.0.0"    # Subclasses MUST override with their own semver

    def __init__(
        self,
        agent_id: str,
        calibration_engine: Optional[dict] = None,
    ):
        self.agent_id = agent_id
        self._cal = calibration_engine or {}
        self._ledger = self._cal.get("ledger")
        self._trust = self._cal.get("trust")
        self._resolution = self._cal.get("resolution")
        self._audit_log: list[AuditEntryV2] = []
        # Reserve engine — wired lazily when a DB-backed ledger is present.
        self._reserve = None

        from runtime.confidence.confidence_v2 import ConfidenceV2
        from runtime.escalation.escalation_gate import EscalationGate
        self._confidence = ConfidenceV2(trust_controller=self._trust)
        self._gate = EscalationGate()

        # LLM client — tier-specific; provider+model resolved from env config
        self._llm_client = client_for(agent_id)
        self._model = model_for(agent_id)
        self.output_schema: dict = {}   # subclasses set this to enforce structured output shape

        # Spend guardrail — halts LLM calls if token/rate cap exceeded
        self._spend = SpendGuardrail(agent_id=agent_id, escalation=self._gate)

        # Experiential memory is optional and non-blocking. It enriches prompts
        # only when the append-only memory schema is available.
        self._memory_context: str = ""
        self._memory_reader = None
        self._memory_writer = None
        self._memory_enabled = os.environ.get("AGENTCO_MEMORY_ENABLED", "1") != "0"
        if self._memory_enabled:
            try:
                db_url = os.environ.get("AGENTCO_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
                if db_url:
                    from agents.core.memory import MemoryReader, MemoryWriter
                    self._memory_reader = MemoryReader(db_url)
                    self._memory_writer = MemoryWriter(db_url)
            except Exception as exc:
                logger.warning("BaseAgentV2(%s): memory unavailable — %s", self.agent_id, exc)

    @abstractmethod
    def run(self, task: dict) -> Any:
        """Agent-specific entrypoint. Must call execute_action() for each action."""
        raise NotImplementedError

    def pre_register_claim(
        self,
        claim: str,
        probability: float,
        resolution_criterion: str,
        resolution_date: datetime,
        domain: str = "general",
        claim_type: str = "general",
        ground_truth_source: str = "external_auditor",
    ) -> Optional[str]:
        """
        Pre-register a falsifiable forward claim in the Prediction Ledger.
        Returns prediction_id, or None if no ledger is wired.
        """
        if self._ledger is None:
            logger.warning("BaseAgentV2(%s): no ledger wired; skipping pre-registration", self.agent_id)
            return None

        reg = PredictionRegistration(
            claim=claim,
            probability=probability,
            confidence_basis={
                "agent_id": self.agent_id,
                "prompt_version": self.PROMPT_VERSION,
                "method": "pre-registered forward claim",
            },
            producing_agent_id=self.agent_id,
            producing_prompt_version=self.PROMPT_VERSION,
            resolution_criterion=resolution_criterion,
            resolution_date=resolution_date,
            ground_truth_source=ground_truth_source,
            horizon_class="short" if (resolution_date - datetime.now(timezone.utc)).days < 31 else "medium",
            domain=domain,
            claim_type=claim_type,
        )
        prediction_id = self._ledger.pre_register(reg)
        logger.info(
            "PRE-REGISTERED: agent=%s prediction=%s p=%.3f claim=%s",
            self.agent_id, prediction_id, probability, claim[:80]
        )
        return prediction_id

    def refresh_reserve_credential(self):
        """
        Recompute and persist a Proof-of-Calibration credential for this agent
        from their current resolved prediction_ledger rows.

        Returns the credential, or None if no DB-backed ledger is wired.
        Requires the Reserve schema (001_reserve_extension.sql) to be applied.
        """
        if self._ledger is None or getattr(self._ledger, "_db", None) is None:
            logger.warning(
                "BaseAgentV2(%s): no DB-backed ledger wired; cannot issue Reserve credential",
                self.agent_id,
            )
            return None
        if self._reserve is None:
            try:
                from reserve import create_reserve_engine
                self._reserve = create_reserve_engine(
                    ledger=self._ledger, db=self._ledger._db
                )
            except Exception as exc:
                logger.warning("BaseAgentV2(%s): Reserve not available — %s", self.agent_id, exc)
                return None
        cred = self._reserve.refresh_credential(self.agent_id)
        logger.info(
            "RESERVE CREDENTIAL ISSUED: agent=%s credential=%s sample_count=%d overall_log=%.4f",
            self.agent_id, cred.credential_id, cred.sample_count, cred.overall_log_score,
        )
        return cred

    def act(self, messages: list[dict], schema: Optional[dict] = None) -> dict:
        """
        Call the local LLM with validate-and-retry.  Subclasses use this instead of
        calling the model directly so malformed output never reaches the event bus.

        Uses self.output_schema by default; pass schema to override for a single call.
        """
        messages = self._inject_memory_context(messages)
        return get_validated_output(
            client=self._llm_client,
            model=self._model,
            messages=messages,
            schema=schema if schema is not None else self.output_schema,
            escalation=self._gate,
            guardrail=self._spend,
        )

    def execute_action(
        self,
        action: AgentActionV2,
        prediction_id: Optional[str] = None,
        pre_approved_token: Optional[str] = None,
    ) -> dict:
        """
        Execute an action through the V2 safety gates:
        1. Resolve trusted_confidence via TrustController (never use stated directly)
        2. Pass through EscalationGate (blocks on human approval if needed)
        3. Emit signed event envelope with producer_prompt_version
        4. Write immutable audit entry

        Returns result dict with outcome, override_id (if any), trusted_confidence.
        """
        from runtime.escalation.escalation_gate import HumanApprovalRequired

        trusted_out = self._confidence.get_trusted(
            agent_id=self.agent_id,
            stated=action.stated_confidence,
            domain=action.domain,
            claim_type=action.claim_type,
            horizon_class=action.horizon_class,
        )

        if trusted_out.degraded:
            logger.warning(
                "CONFIDENCE DEGRADED: agent=%s stated=%.3f trusted=%.3f domain=%s n_samples=%d",
                self.agent_id, trusted_out.stated_confidence,
                trusted_out.trusted_confidence, action.domain, trusted_out.n_samples,
            )

        override_id: Optional[str] = None
        outcome = "executed"

        try:
            override_id = self._gate.check_and_gate(
                agent_id=self.agent_id,
                action_summary=action.description,
                risk_level=action.risk_level,
                trusted_confidence=trusted_out.trusted_confidence,
                stated_confidence=trusted_out.stated_confidence,
                domain=action.domain,
                claim_type=action.claim_type,
                payload=action.payload,
                pre_approved_token=pre_approved_token,
            )
        except HumanApprovalRequired as exc:
            override_id = exc.override_id
            outcome = "blocked"
            self._write_audit(action, trusted_out, prediction_id, override_id, "blocked")
            raise

        # Action cleared — emit signed event envelope
        envelope = self._build_envelope(action, trusted_out, prediction_id)
        logger.info(
            "ACTION EXECUTED: agent=%s action=%s trusted_conf=%.3f risk=%s",
            self.agent_id, action.action_type, trusted_out.trusted_confidence, action.risk_level
        )

        self._write_audit(action, trusted_out, prediction_id, override_id, outcome)
        return {
            "outcome": outcome,
            "override_id": override_id,
            "trusted_confidence": trusted_out.trusted_confidence,
            "stated_confidence": trusted_out.stated_confidence,
            "envelope": envelope,
            "prediction_id": prediction_id,
        }

    def _build_envelope(self, action: AgentActionV2, trusted_out, prediction_id: Optional[str]) -> dict:
        envelope = {
            "event_id": str(uuid.uuid4()),
            "producer_agent_id": self.agent_id,
            "producer_prompt_version": self.PROMPT_VERSION,   # V2 REQUIRED FIELD
            "action_type": action.action_type,
            "confidence_score": trusted_out.trusted_confidence,
            "stated_confidence": trusted_out.stated_confidence,
            "risk_level": action.risk_level,
            "domain": action.domain,
            "claim_type": action.claim_type,
            "prediction_id": prediction_id,
            "payload": action.payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": str(uuid.uuid4()),
        }
        envelope["hmac_signature"] = _sign_envelope(envelope)
        return envelope

    def _write_audit(self, action: AgentActionV2, trusted_out, prediction_id, override_id, outcome: str):
        entry = AuditEntryV2(
            agent_id=self.agent_id,
            prompt_version=self.PROMPT_VERSION,
            action_type=action.action_type,
            description=action.description,
            stated_confidence=trusted_out.stated_confidence,
            trusted_confidence=trusted_out.trusted_confidence,
            risk_level=action.risk_level,
            domain=action.domain,
            prediction_id=prediction_id,
            override_id=override_id,
            outcome=outcome,
        )
        self._audit_log.append(entry)

    def prepare_memory_context(
        self,
        task_description: str,
        domain: str = "general",
        timeout_ms: int = 500,
    ) -> str:
        """
        Retrieve memories and track record for the next task.

        This method is deliberately best-effort: DB failures and timeout failures
        result in an empty or first-run context, never in a blocked agent run.
        """
        if not self._memory_reader:
            self._memory_context = ""
            return self._memory_context
        try:
            memories = self._run_async(
                self._memory_reader.retrieve_relevant(
                    self.agent_id, task_description, domain=domain, timeout_ms=timeout_ms
                )
            )
            track_record = self._run_async(
                self._memory_reader.get_agent_track_record_summary(self.agent_id, domain=domain)
            )
            self._memory_context = self._memory_reader.format_for_system_prompt(memories, track_record)
            return self._memory_context
        except Exception as exc:
            logger.warning("BaseAgentV2(%s): memory retrieval failed — %s", self.agent_id, exc)
            self._memory_context = ""
            return self._memory_context

    def complete_task_memory(
        self,
        task_id: str,
        task_type: str,
        task_input: str,
        task_output_summary: str,
        predictions_registered: Optional[list[str]] = None,
        sources_consulted: Optional[list[str]] = None,
        key_findings: Optional[list[str]] = None,
        errors_encountered: Optional[list[str]] = None,
        confidence_in_output: float = 0.5,
        duration_seconds: float = 0.0,
        tokens_used: int = 0,
        domain: str = "general",
    ) -> Optional[str]:
        """Append an episodic memory for a completed task."""
        if not self._memory_writer:
            return None
        try:
            return self._run_async(
                self._memory_writer.write_episodic(
                    agent_id=self.agent_id,
                    task_id=task_id,
                    task_type=task_type,
                    task_input=task_input,
                    task_output_summary=task_output_summary,
                    predictions_registered=predictions_registered or [],
                    sources_consulted=sources_consulted or [],
                    key_findings=key_findings or [],
                    errors_encountered=errors_encountered or [],
                    confidence_in_output=confidence_in_output,
                    duration_seconds=duration_seconds,
                    tokens_used=tokens_used,
                    domain=domain,
                )
            )
        except Exception as exc:
            logger.warning("BaseAgentV2(%s): episodic memory write failed — %s", self.agent_id, exc)
            return None

    def remember_prediction_lesson(
        self,
        prediction_id: str,
        claim: str,
        stated_confidence: float,
        actual_outcome: bool,
        log_score: float,
        lesson: str,
        domain_insight: str,
        calibration_adjustment: str,
        domain: str,
    ) -> Optional[str]:
        """Append a prediction lesson after external resolution."""
        if not self._memory_writer:
            return None
        try:
            return self._run_async(
                self._memory_writer.write_prediction_lesson(
                    agent_id=self.agent_id,
                    prediction_id=prediction_id,
                    claim=claim,
                    stated_confidence=stated_confidence,
                    actual_outcome=actual_outcome,
                    log_score=log_score,
                    lesson=lesson,
                    domain_insight=domain_insight,
                    calibration_adjustment=calibration_adjustment,
                    domain=domain,
                )
            )
        except Exception as exc:
            logger.warning("BaseAgentV2(%s): prediction lesson write failed — %s", self.agent_id, exc)
            return None

    def _inject_memory_context(self, messages: list[dict]) -> list[dict]:
        if not self._memory_context:
            return messages
        memory_block = {"role": "system", "content": self._memory_context}
        if not messages:
            return [memory_block]
        injected = list(messages)
        insert_at = 1 if injected[0].get("role") == "system" else 0
        injected.insert(insert_at, memory_block)
        return injected

    @staticmethod
    def _run_async(coro):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        raise RuntimeError("BaseAgentV2 memory sync helpers cannot run inside an active event loop")

    def get_audit_log(self) -> list[dict]:
        return [asdict(e) for e in self._audit_log]

    def get_pending_approvals(self):
        return self._gate.list_pending()

    def approve_action(self, override_id: str, approver_id: str) -> str:
        return self._gate.approve(override_id, approver_id)

    def reject_action(self, override_id: str, rejector_id: str) -> None:
        return self._gate.reject(override_id, rejector_id)
