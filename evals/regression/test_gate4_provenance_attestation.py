from dataclasses import replace

from provenance import AttestationVerifier


def test_action_attestation_verifies_and_tamper_fails():
    verifier = AttestationVerifier()
    attestation = verifier.attest(
        principal_id="agent-a",
        tool_id="health_check",
        input_payload={"x": 1},
        output_payload={"ok": True},
        trusted_confidence=0.8,
        risk_level="low",
        evidence_refs=["e1"],
    )

    assert verifier.verify(attestation, verifier.public_key_b64)
    tampered = replace(attestation, output_hash="0" * 64)
    assert not verifier.verify(tampered, verifier.public_key_b64)


def test_attestation_requires_measured_environment_quote():
    verifier = AttestationVerifier()
    attestation = verifier.attest(
        principal_id="agent-a",
        tool_id="irreversible_tool",
        input_payload={},
        output_payload={},
        trusted_confidence=0.8,
        risk_level="high",
    )
    assert verifier.verify(attestation)
    assert not verifier.verify(replace(attestation, tee_quote=""))
