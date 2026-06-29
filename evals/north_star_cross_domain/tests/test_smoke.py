from evals.north_star_cross_domain.run_smoke import CASES, run_benchmark


def test_north_star_smoke_has_required_domains():
    result = run_benchmark()
    assert set(result["domains"]) == {
        "vendor_risk",
        "medical-triage-safe-info",
        "financial-risk-disclosure",
        "code-change-risk-review",
    }
    assert len(CASES) == 4


def test_north_star_smoke_scores_required_dimensions():
    result = run_benchmark()
    for row in result["cases"]:
        scores = row["scores"]
        assert scores["decision_correctness"] == 1.0
        assert scores["escalation_correctness"] == 1.0
        assert scores["evidence_recall"] == 1.0
        assert scores["hallucination_trap_avoidance"] == 1.0
        assert scores["confidence_band_correctness"] == 1.0
    assert result["is_smoke_skeleton"] is True
    assert result["not_proof_of_general_intelligence"] is True
