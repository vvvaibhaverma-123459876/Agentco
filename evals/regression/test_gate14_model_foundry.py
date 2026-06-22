from foundry import ModelFoundry


def test_trace_to_training_example_preserves_lineage_and_trust_weight():
    foundry = ModelFoundry()
    trace = foundry.capture_trace(
        task_request="Resolve claim",
        claims_used=["claim-1"],
        evidence_used=["evidence-1"],
        actions=["action-1"],
        outcome="Claim blocked for weak evidence",
        calibration_update={"trusted_confidence": 0.72},
        approvals=["approval-1"],
    )
    example = foundry.build_example(trace.trace_id)
    foundry.add_to_dataset("v1", example)
    exported = foundry.export_dataset("v1")

    assert exported[0]["lineage_refs"] == ["claim-1", "evidence-1", "action-1"]
    assert exported[0]["trust_weight"] == 0.72
