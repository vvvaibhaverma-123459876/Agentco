from datetime import datetime, timezone
from types import SimpleNamespace

from calibration.trust.trust_controller import TrustController


def test_false_resolution_never_increases_trust():
    tc = TrustController()
    record = SimpleNamespace(
        post_hoc=False,
        prediction_id="pawdent-month-1-cac",
        producing_agent_id="pawdent-growth-marketer",
        domain="pet_care_subscription",
        claim_type="monthly_business_prediction",
        horizon_class="short",
        probability=0.62,
        resolved_outcome=False,
    )

    before = tc.trusted_confidence(
        stated=0.62,
        subject_id=record.producing_agent_id,
        subject_type="agent",
        domain=record.domain,
        claim_type=record.claim_type,
        horizon_class=record.horizon_class,
    )

    tc.ingest_resolution(record)

    after = tc.trusted_confidence(
        stated=0.62,
        subject_id=record.producing_agent_id,
        subject_type="agent",
        domain=record.domain,
        claim_type=record.claim_type,
        horizon_class=record.horizon_class,
    )

    assert after <= before
