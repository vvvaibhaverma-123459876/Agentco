"""Shared types for AgentCo agent runtime."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TrustLevel(str, Enum):
    VERIFIED = "verified"       # 0.9–1.0
    TRUSTED = "trusted"         # 0.7–0.89
    PROVISIONAL = "provisional" # 0.5–0.69
    UNVERIFIED = "unverified"   # 0.3–0.49
    REJECTED = "rejected"       # <0.3


class AgentLifecycle(str, Enum):
    PROVISIONED = "provisioned"
    STAGING = "staging"
    CANARY = "canary"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class ActionType(str, Enum):
    DECISION = "decision"
    API_CALL = "api_call"
    EVENT_PUBLISHED = "event_published"
    ESCALATION = "escalation"


@dataclass
class AgentEvent:
    event_type: str
    producer_agent_id: str
    confidence_score: float
    payload: dict[str, Any]
    risk_level: RiskLevel
    requires_ack: bool
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    correlation_id: Optional[str] = None
    ttl_seconds: int = 86400


@dataclass
class AuditEntry:
    agent_id: str
    action_type: ActionType
    input_summary: str
    output_summary: str
    confidence_score: float
    risk_level: RiskLevel
    human_approved: bool = False
    human_approver_id: Optional[str] = None
    downstream_events: list[str] = field(default_factory=list)
    log_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    session_id: Optional[str] = None


@dataclass
class AgentOutput:
    content: Any
    confidence_score: float
    risk_level: RiskLevel
    rationale: str
    requires_human_approval: bool = False
    escalation_reason: Optional[str] = None

    def trust_level(self) -> TrustLevel:
        if self.confidence_score >= 0.9:
            return TrustLevel.VERIFIED
        elif self.confidence_score >= 0.7:
            return TrustLevel.TRUSTED
        elif self.confidence_score >= 0.5:
            return TrustLevel.PROVISIONAL
        elif self.confidence_score >= 0.3:
            return TrustLevel.UNVERIFIED
        return TrustLevel.REJECTED


@dataclass
class OverrideRequest:
    agent_id: str
    action: str
    risk_score: float
    context: dict[str, Any]
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    status: str = "pending"
    resolved_by: Optional[str] = None
    resolution: Optional[str] = None
