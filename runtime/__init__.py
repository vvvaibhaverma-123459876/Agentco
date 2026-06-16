"""
AgentCo V2 Runtime — Layer 0-wired agent infrastructure.

Every agent built on this runtime:
- Pre-registers falsifiable claims before acting
- Uses trusted_confidence() not stated confidence
- Carries producer_prompt_version in every event envelope
- Blocks on human approval; no auto-approve on timeout
"""
from .base_agent.base_agent_v2 import BaseAgentV2
from .confidence.confidence_v2 import ConfidenceV2, TrustedOutput
from .escalation.escalation_gate import EscalationGate, HumanApprovalRequired

__all__ = ["BaseAgentV2", "ConfidenceV2", "TrustedOutput", "EscalationGate", "HumanApprovalRequired"]
