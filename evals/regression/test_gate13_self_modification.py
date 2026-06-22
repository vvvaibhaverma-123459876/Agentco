from self_modification import ChangeProposal, SelfModificationKernel


def test_self_modification_blocks_protected_surface_and_failed_tests():
    kernel = SelfModificationKernel()
    protected = ChangeProposal("agent", ["calibration/evidence/evidence_kernel.py"], "faster", "high", ["pytest"], "revert patch")
    assert kernel.evaluate(protected, tests_passed=True).status == "blocked_protected_surface"

    failed = ChangeProposal("agent", ["README.md"], "docs", "low", ["pytest"], "revert patch")
    assert kernel.evaluate(failed, tests_passed=False).status == "blocked_failed_tests"

    safe = ChangeProposal("agent", ["docs/refoundation/NOTE.md"], "docs", "low", ["pytest"], "revert patch")
    assert kernel.evaluate(safe, tests_passed=True).status == "accepted_for_governance"
