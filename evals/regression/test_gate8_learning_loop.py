from learning.cycle import AutonomousLearningLoop


def test_learning_loop_produces_claim_hypothesis_experiment_memory_and_governed_adaptation():
    loop = AutonomousLearningLoop()
    result = loop.run("Independent source reports calibration drift. Review should happen.")

    assert result["claims"]
    assert result["hypothesis"]["claim_id"] == result["claims"][0].claim_id
    assert result["experiment"]["status"] == "proposed"
    assert result["memory_event"].provenance_ref
    assert result["adaptation_proposal"].status == "governance_required"
    assert result["governed"]
