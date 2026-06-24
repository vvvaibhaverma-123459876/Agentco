from __future__ import annotations

from dataclasses import dataclass


PROTECTED_SURFACES = {
    "calibration/evidence/evidence_kernel.py",
    "calibration/firewall/firewall.py",
    "backend/src/services/provenance.service.ts",
    "reserve/keys/agentco_reserve_public.pem",
}


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    requires_human: bool = False


class ConstitutionCompiler:
    def compile(self, rules: list[dict]) -> list[dict]:
        return [{**rule, "compiled": True} for rule in rules]


class PolicyEngine:
    def __init__(self, rules: list[dict] | None = None):
        self.rules = rules or []

    def evaluate(self, action: dict) -> PolicyDecision:
        risk = action.get("risk_level", "low")
        path = action.get("path")
        if path in PROTECTED_SURFACES:
            return PolicyDecision(False, "protected_surface", requires_human=True)
        if risk == "critical":
            return PolicyDecision(False, "critical_requires_human", requires_human=True)
        if risk == "high" and not action.get("approved"):
            return PolicyDecision(False, "high_requires_approval")
        for rule in self.rules:
            if rule.get("deny_tool") == action.get("tool"):
                return PolicyDecision(False, "policy_denied_tool")
        return PolicyDecision(True, "allowed")
