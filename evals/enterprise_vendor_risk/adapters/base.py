"""
Base adapter interface for vendor risk triage benchmark.

All LLM/agent adapters must implement this interface.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class VendorRiskResponse:
    """Standardized response from model/agent."""
    decision: str  # "approve" | "reject" | "escalate" | "abstain"
    risk_level: str  # "low" | "medium" | "high" | "critical" | "unknown"
    confidence: float  # 0.0-1.0
    trusted_confidence: Optional[float] = None
    answer: str = ""
    evidence_ids: list[str] = None
    missing_information: list[str] = None
    policy_checks: list[dict] = None
    tool_calls_used: list[str] = None
    abstained: bool = False
    abstain_reason: Optional[str] = None

    def __post_init__(self):
        if self.evidence_ids is None:
            self.evidence_ids = []
        if self.missing_information is None:
            self.missing_information = []
        if self.policy_checks is None:
            self.policy_checks = []
        if self.tool_calls_used is None:
            self.tool_calls_used = []


@dataclass
class TrialResult:
    """Complete trial execution result."""
    task_id: str
    model_id: str
    status: str  # "completed" | "failed" | "not_run"
    skip_reason: Optional[str] = None
    raw_output: str = ""
    parsed_output: Optional[VendorRiskResponse] = None
    latency_ms: float = 0.0
    usage: Optional[dict] = None
    errors: list[str] = None
    trace: list[dict] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.trace is None:
            self.trace = []

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            'task_id': self.task_id,
            'model_id': self.model_id,
            'status': self.status,
            'skip_reason': self.skip_reason,
            'raw_output': self.raw_output,
            'parsed_output': self.parsed_output.__dict__ if self.parsed_output else None,
            'latency_ms': self.latency_ms,
            'usage': self.usage,
            'errors': self.errors,
            'trace': self.trace,
        }


class BaseAdapter(ABC):
    """Abstract base for model adapters."""

    def __init__(self, model_id: str):
        self.model_id = model_id

    @abstractmethod
    def predict(self, task: dict) -> TrialResult:
        """
        Run model on a vendor risk task.

        Returns TrialResult with parsed response or error details.
        """
        pass

    def validate_response(self, response: VendorRiskResponse) -> list[str]:
        """Validate response against schema."""
        errors = []

        if response.decision not in ["approve", "reject", "escalate", "abstain"]:
            errors.append(f"Invalid decision: {response.decision}")

        if response.risk_level not in ["low", "medium", "high", "critical", "unknown"]:
            errors.append(f"Invalid risk_level: {response.risk_level}")

        if not (0.0 <= response.confidence <= 1.0):
            errors.append(f"Confidence must be 0-1, got {response.confidence}")

        if response.trusted_confidence is not None and not (0.0 <= response.trusted_confidence <= 1.0):
            errors.append(f"Trusted confidence must be 0-1, got {response.trusted_confidence}")

        if response.abstained and not response.abstain_reason:
            errors.append("Abstain_reason required when abstained=True")

        return errors
