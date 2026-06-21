from __future__ import annotations

from epistemic.claims.claim_model import RealityBoundary

RINGS = {
    0: "Self assertion",
    1: "Same agent memory/check",
    2: "Different agent, same department",
    3: "Different department, same institution",
    4: "Different institution, same society",
    5: "Different society, same civilization",
    6: "External source/oracle/dataset/human/sensor",
    7: "Mechanical/cryptographic/deterministic proof",
}


def minimum_ring_for_claim(boundary: RealityBoundary, risk_level: str, claim_type: str) -> int:
    risk = risk_level.lower()
    ctype = claim_type.lower()
    if boundary == "R0_internal_state":
        minimum = 2
    elif boundary == "R1_formal_truth":
        minimum = 7
    elif boundary == "R2_software_execution":
        minimum = 7
    elif boundary == "R3_simulation_truth":
        minimum = 3
    elif boundary == "R4_institutional_truth":
        minimum = 4
    elif boundary in {"R5_external_empirical_reality", "R6_future_outcome"}:
        minimum = 6
    elif boundary == "R7_normative_judgment":
        minimum = 4
    elif boundary == "R8_strategic_business_claim":
        minimum = 6
    else:
        minimum = 6

    if risk in {"high", "critical"}:
        minimum = max(minimum, 6)
    if any(token in ctype for token in ("financial", "medical", "legal", "real_world")):
        minimum = max(minimum, 6)
    return minimum
