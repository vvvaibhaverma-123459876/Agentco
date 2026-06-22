from calibration.uncertainty import ConformalPredictor, UncertaintyStack


def test_trusted_confidence_is_lower_when_history_warrants():
    stack = UncertaintyStack()
    assert stack.trusted_confidence(0.9, historical_multiplier=0.5) == 0.45


def test_conformal_coverage_threshold_and_abstention():
    conformal = ConformalPredictor(alpha=0.2)
    conformal.fit([0.05, 0.1, 0.2, 0.4, 0.8])
    assert conformal.covers(0.4)
    assert not conformal.covers(0.9)

    decision = UncertaintyStack(abstention_threshold=0.5).decide(
        stated_confidence=0.6,
        historical_multiplier=0.5,
        candidates=["approve", "reject", "escalate"],
    )
    assert decision.should_abstain
    assert decision.reason == "uncertainty_above_threshold"


def test_calibration_metrics_are_computed():
    metrics = UncertaintyStack().metrics([0.9, 0.2, 0.7], [True, False, False])
    assert set(metrics) == {"brier", "log_score", "ece", "coverage"}
    assert metrics["coverage"] == 2 / 3
