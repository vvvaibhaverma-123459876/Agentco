from governance import ConstitutionCompiler, PolicyEngine


def test_policy_mechanically_blocks_high_critical_and_protected_surfaces():
    engine = PolicyEngine(ConstitutionCompiler().compile([{"deny_tool": "unsafe_tool"}]))

    assert not engine.evaluate({"risk_level": "high"}).allowed
    critical = engine.evaluate({"risk_level": "critical"})
    assert not critical.allowed and critical.requires_human
    protected = engine.evaluate({"path": "calibration/evidence/evidence_kernel.py", "risk_level": "low"})
    assert not protected.allowed and protected.reason == "protected_surface"
    assert not engine.evaluate({"tool": "unsafe_tool", "risk_level": "low"}).allowed
    assert engine.evaluate({"tool": "safe_tool", "risk_level": "low"}).allowed
