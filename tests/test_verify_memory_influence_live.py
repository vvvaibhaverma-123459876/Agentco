from scripts.verify_memory_influence_live import validate_memory_influence


def test_memory_influence_validation_accepts_marker_and_cap():
    marker = "AGENTCO_MEMORY_INFLUENCE_TEST"
    memory_context = f"Calibration lesson: {marker}: cap confidence at 0.62 and escalate."
    output = {
        "decision": "escalate",
        "confidence": 0.6,
        "memory_used": True,
        "memory_marker": marker,
        "memory_adjustment_applied": f"{marker}: cap confidence at 0.62",
        "missing_information": ["SOC 2 Type II report", "signed DPA", "subprocessor list"],
    }
    validation = validate_memory_influence(marker=marker, memory_context=memory_context, model_output=output)
    assert validation["passed"] is True
    assert validation["score"] == 1.0


def test_memory_influence_validation_rejects_missing_marker():
    marker = "AGENTCO_MEMORY_INFLUENCE_TEST"
    memory_context = "No usable memory."
    output = {
        "decision": "escalate",
        "confidence": 0.6,
        "memory_used": True,
        "memory_marker": marker,
        "missing_information": ["SOC 2 Type II report", "signed DPA", "subprocessor list"],
    }
    validation = validate_memory_influence(marker=marker, memory_context=memory_context, model_output=output)
    assert validation["passed"] is False
    assert validation["checks"]["memory_context_contains_marker"] is False


def test_memory_influence_validation_rejects_overconfidence():
    marker = "AGENTCO_MEMORY_INFLUENCE_TEST"
    memory_context = f"Calibration lesson: {marker}: cap confidence at 0.62 and escalate."
    output = {
        "decision": "escalate",
        "confidence": 0.9,
        "memory_used": True,
        "memory_marker": marker,
        "missing_information": ["SOC 2 Type II report", "signed DPA", "subprocessor list"],
    }
    validation = validate_memory_influence(marker=marker, memory_context=memory_context, model_output=output)
    assert validation["passed"] is False
    assert validation["checks"]["confidence_cap_applied"] is False


def test_memory_influence_validation_rejects_approval():
    marker = "AGENTCO_MEMORY_INFLUENCE_TEST"
    memory_context = f"Calibration lesson: {marker}: cap confidence at 0.62 and escalate."
    output = {
        "decision": "approve",
        "confidence": 0.6,
        "memory_used": True,
        "memory_marker": marker,
        "missing_information": ["SOC 2 Type II report", "signed DPA", "subprocessor list"],
    }
    validation = validate_memory_influence(marker=marker, memory_context=memory_context, model_output=output)
    assert validation["passed"] is False
    assert validation["checks"]["decision_escalates"] is False
