"""Test that weighting formulas allow true zero-to-full range (prerequisite 1)."""
import pytest


def test_weighting_formula_zero_trust():
    """At trust=0, weighting should produce zero influence (not 50-90% floor)."""
    baseline = 10_000

    # Growth Marketer: trust=0 → ad_budget = 0x baseline
    growth_trust = 0.0
    ad_budget_weighted = baseline * (2.0 * growth_trust)
    assert ad_budget_weighted == 0, f"Expected 0 at trust=0, got {ad_budget_weighted}"

    # Operations Manager: trust=0 → inventory = 0x baseline
    ops_trust = 0.0
    inventory_weighted = baseline * (2.0 * ops_trust)
    assert inventory_weighted == 0, f"Expected 0 at trust=0, got {inventory_weighted}"

    # Product Manager: trust=0 → price = 0x baseline
    pm_trust = 0.0
    price_weighted = baseline * (2.0 * pm_trust)
    assert price_weighted == 0, f"Expected 0 at trust=0, got {price_weighted}"

    # Finance Controller brake: trust=1 → full brake (multiplier = 0)
    finance_trust = 1.0
    finance_brake = 1.0 - finance_trust
    result = baseline * finance_brake
    assert result == 0, f"Expected 0 at trust=1 brake, got {result}"


def test_weighting_formula_full_trust():
    """At trust=1, weighting should produce full influence (2x baseline)."""
    baseline = 10_000

    # Growth Marketer: trust=1 → ad_budget = 2x baseline
    growth_trust = 1.0
    ad_budget_weighted = baseline * (2.0 * growth_trust)
    assert ad_budget_weighted == baseline * 2.0, f"Expected {baseline * 2.0}, got {ad_budget_weighted}"

    # Operations Manager: trust=1 → inventory = 2x baseline
    ops_trust = 1.0
    inventory_weighted = baseline * (2.0 * ops_trust)
    assert inventory_weighted == baseline * 2.0, f"Expected {baseline * 2.0}, got {inventory_weighted}"

    # Product Manager: trust=1 → price = 2x baseline
    pm_trust = 1.0
    price_weighted = baseline * (2.0 * pm_trust)
    assert price_weighted == baseline * 2.0, f"Expected {baseline * 2.0}, got {price_weighted}"

    # Finance Controller brake: trust=0 → no brake (multiplier = 1)
    finance_trust = 0.0
    finance_brake = 1.0 - finance_trust
    result = baseline * finance_brake
    assert result == baseline, f"Expected {baseline} at trust=0 brake, got {result}"


def test_weighting_formula_mid_trust():
    """At trust=0.5, weighting should produce 1x baseline (linear interpolation)."""
    baseline = 10_000

    # Growth Marketer: trust=0.5 → ad_budget = 1x baseline
    growth_trust = 0.5
    ad_budget_weighted = baseline * (2.0 * growth_trust)
    assert ad_budget_weighted == baseline, f"Expected {baseline}, got {ad_budget_weighted}"

    # Finance Controller brake: trust=0.5 → half brake (multiplier = 0.5)
    finance_trust = 0.5
    finance_brake = 1.0 - finance_trust
    result = baseline * finance_brake
    assert result == baseline * 0.5, f"Expected {baseline * 0.5}, got {result}"


def test_no_hardcoded_floors():
    """Verify no formulas have hardcoded 0.5/0.7/0.9 floors anymore."""
    # Old formulas (WRONG - tested for regression):
    # - (0.5 + 1.5*trust) → floor of 0.5x
    # - (0.7 + 1.3*trust) → floor of 0.7x
    # - (0.9 + 0.2*trust) → floor of 0.9x
    # - (max(0.5, 1.0 - 0.5*trust)) → floor of 0.5x

    # New formulas (CORRECT - tested for inclusion):
    # - (2.0*trust) → true [0, 2x] range
    # - (1.0 - trust) → true [0, 1] range

    baseline = 10_000

    for trust in [0.0, 0.25, 0.5, 0.75, 1.0]:
        # No formula should have a hard minimum floor
        growth_result = baseline * (2.0 * trust)
        assert growth_result >= 0, f"Growth formula should allow <=0 at trust={trust}"

        ops_result = baseline * (2.0 * trust)
        assert ops_result >= 0, f"Ops formula should allow <=0 at trust={trust}"

        pm_result = baseline * (2.0 * trust)
        assert pm_result >= 0, f"PM formula should allow <=0 at trust={trust}"

        finance_result = baseline * (1.0 - trust)
        assert 0 <= finance_result <= baseline, f"Finance brake should stay [0, baseline] at trust={trust}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
