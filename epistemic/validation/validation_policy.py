from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationPolicy:
    policy_id: str
    boundary: str
    domain: str | None
    claim_type: str | None
    risk_level: str | None
    required_evidence: list[str]
    required_institutions: list[str]
    minimum_validation_ring: int
    external_validation_required: bool
    promotion_target: str
    active: bool = True


SEED_POLICIES = [
    ValidationPolicy("internal_ledger_fact_v1", "R0_internal_state", None, None, None, ["ledger_row", "audit_log"], [], 2, False, "internally_verified"),
    ValidationPolicy("software_execution_claim_v1", "R2_software_execution", None, None, None, ["test_result", "ci_build_artifact"], [], 7, False, "mechanically_resolved"),
    ValidationPolicy("simulation_claim_v1", "R3_simulation_truth", None, None, None, ["dataset_snapshot"], [], 3, False, "simulation_validated"),
    ValidationPolicy("external_empirical_claim_v1", "R5_external_empirical_reality", None, None, None, ["external_document"], [], 6, True, "externally_grounded"),
    ValidationPolicy("future_outcome_prediction_v1", "R6_future_outcome", None, None, None, ["external_api_response"], [], 6, True, "reality_validated"),
    ValidationPolicy("normative_governance_claim_v1", "R7_normative_judgment", None, None, None, ["court_or_governance_ruling"], [], 4, False, "institutionally_verified"),
    ValidationPolicy("strategic_business_claim_v1", "R8_strategic_business_claim", None, None, None, ["market_outcome_data"], [], 6, True, "externally_grounded"),
]
