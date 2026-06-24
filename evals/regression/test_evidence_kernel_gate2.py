import pytest

from calibration.evidence import EvidenceKernel, SourceIndependenceEngine


def test_same_source_resolution_is_mechanically_rejected():
    kernel = EvidenceKernel()
    claim = kernel.create_claim(
        "Agentco has a passing external validation suite",
        source_uri="https://example.com/report?utm_source=self",
        source_type="web",
    )

    with pytest.raises(ValueError, match="not independent"):
        kernel.resolve_claim(
            claim.claim_id,
            outcome="true",
            resolver_uri="https://www.example.com/report",
            resolver_type="web",
            evidence_refs=[],
        )


def test_declared_derivative_source_cannot_resolve_or_promote():
    independence = SourceIndependenceEngine()
    independence.register_derivative("https://origin.example/report", "https://mirror.example/copy")
    kernel = EvidenceKernel(independence)
    claim = kernel.create_claim(
        "The benchmark passed",
        source_uri="https://origin.example/report",
        source_type="web",
    )
    kernel.attach_evidence(
        claim.claim_id,
        source_uri="https://mirror.example/copy",
        source_type="web",
        supports_or_refutes="supports",
        strength=1.0,
        evidence_quality="EXTERNAL-VALIDATED",
        raw_excerpt_or_pointer="copied report",
    )

    assert not kernel.promote_claim(claim.claim_id).allowed
    with pytest.raises(ValueError, match="not independent"):
        kernel.resolve_claim(
            claim.claim_id,
            outcome="true",
            resolver_uri="https://mirror.example/copy",
            resolver_type="web",
            evidence_refs=[],
        )


def test_simulation_and_fixture_evidence_cannot_promote():
    kernel = EvidenceKernel()
    claim = kernel.create_claim(
        "Policy X is safe",
        source_uri="https://agentco.local/simulation",
        source_type="simulation",
    )
    kernel.attach_evidence(
        claim.claim_id,
        source_uri="https://independent.example/replay",
        source_type="fixture",
        supports_or_refutes="supports",
        strength=1.0,
        evidence_quality="FIXTURE",
        raw_excerpt_or_pointer="fixture says safe",
    )
    kernel.attach_evidence(
        claim.claim_id,
        source_uri="https://another-independent.example/sim",
        source_type="simulation",
        supports_or_refutes="supports",
        strength=1.0,
        evidence_quality="simulated",
        raw_excerpt_or_pointer="simulation says safe",
    )

    decision = kernel.promote_claim(claim.claim_id)
    assert not decision.allowed
    assert "FIXTURE evidence cannot promote" in decision.reasons
    assert "simulated evidence cannot promote" in decision.reasons


def test_external_independent_evidence_promotes_without_contradiction():
    kernel = EvidenceKernel()
    claim = kernel.create_claim(
        "The release gate passed",
        source_uri="https://agentco.example/claim",
        source_type="internal",
    )
    kernel.attach_evidence(
        claim.claim_id,
        source_uri="https://external-validator.example/result",
        source_type="benchmark",
        supports_or_refutes="supports",
        strength=0.95,
        evidence_quality="EXTERNAL-VALIDATED",
        raw_excerpt_or_pointer="external validator pass",
    )

    decision = kernel.promote_claim(claim.claim_id)
    assert decision.allowed
    assert decision.independence_score == 1.0
    assert kernel.claims[claim.claim_id].promotion_status == "promoted"


def test_contradiction_blocks_promotion():
    kernel = EvidenceKernel()
    claim = kernel.create_claim(
        "the action is allowed",
        source_uri="https://agentco.example/a",
        source_type="internal",
    )
    kernel.create_claim(
        "the action is not allowed",
        source_uri="https://external.example/b",
        source_type="web",
    )
    kernel.attach_evidence(
        claim.claim_id,
        source_uri="https://validator.example/result",
        source_type="benchmark",
        supports_or_refutes="supports",
        strength=0.99,
        evidence_quality="EXTERNAL-VALIDATED",
        raw_excerpt_or_pointer="validator pass",
    )

    decision = kernel.promote_claim(claim.claim_id)
    assert not decision.allowed
    assert "contradiction or refuting evidence present" in decision.reasons


def test_evidence_kernel_api_surface_and_source_reliability_update():
    kernel = EvidenceKernel()
    claim = kernel.create_claim(
        "external source reliability updates",
        source_uri="https://source.example/claim",
        source_type="web",
    )
    artifact = kernel.attach_evidence(
        claim.claim_id,
        source_uri="https://validator.example/result",
        source_type="benchmark",
        supports_or_refutes="supports",
        strength=0.9,
        evidence_quality="EXTERNAL-VALIDATED",
        raw_excerpt_or_pointer="validator pass",
    )
    resolution = kernel.resolve_claim(
        claim.claim_id,
        outcome="true",
        resolver_uri="https://resolver.example/outcome",
        resolver_type="external_benchmark",
        evidence_refs=[artifact.artifact_id],
    )

    assert kernel.list_claims() == [claim]
    assert kernel.list_evidence(claim.claim_id) == [artifact]
    assert kernel.claim_graph(claim.claim_id)["resolution"] == resolution
    report = kernel.source_reliability_report("https://source.example/claim")[0]
    assert report.historical_claim_count == 1
    assert report.resolved_true_count == 1
    assert report.unresolved_count == 0

    demoted = kernel.demote_claim(claim.claim_id, "stale")
    assert demoted.promotion_status == "demoted"
