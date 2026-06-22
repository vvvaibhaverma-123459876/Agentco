"""
Tests for canonical uncertainty schema.
"""
import pytest
from calibration.uncertainty.schema import UncertaintySignal, from_legacy_confidence


class TestUncertaintySignal:
    """Test canonical uncertainty signal."""

    def test_basic_creation(self):
        """Create basic uncertainty signal."""
        sig = UncertaintySignal(stated_confidence=0.9)
        assert sig.stated_confidence == 0.9
        assert sig.abstained is False
        assert sig.abstain_reason is None

    def test_validation_confidence_in_range(self):
        """Confidence must be in [0, 1]."""
        with pytest.raises(ValueError, match="stated_confidence must be in"):
            UncertaintySignal(stated_confidence=1.5)

        with pytest.raises(ValueError, match="stated_confidence must be in"):
            UncertaintySignal(stated_confidence=-0.1)

        # Valid edge cases
        UncertaintySignal(stated_confidence=0.0)
        UncertaintySignal(stated_confidence=1.0)

    def test_validation_entropy_non_negative(self):
        """Entropy must be non-negative."""
        with pytest.raises(ValueError, match="semantic_entropy must be non-negative"):
            UncertaintySignal(semantic_entropy=-0.1)

        # Valid
        UncertaintySignal(semantic_entropy=0.0)
        UncertaintySignal(semantic_entropy=5.0)  # e.g., log(e^5)

    def test_validation_abstention_requires_reason(self):
        """If abstained=True, reason must be provided."""
        with pytest.raises(ValueError, match="abstain_reason is required"):
            UncertaintySignal(abstained=True)

        # Valid
        UncertaintySignal(abstained=True, abstain_reason="low_confidence")
        UncertaintySignal(abstained=False)  # No reason required if not abstaining

    def test_serialization_round_trip(self):
        """Serialize and deserialize."""
        original = UncertaintySignal(
            stated_confidence=0.85,
            trusted_confidence=0.75,
            semantic_entropy=1.2,
            abstained=False,
            method_versions={'calibration': '1.0'},
        )
        data = original.to_dict()
        reconstructed = UncertaintySignal.from_dict(data)
        assert reconstructed.stated_confidence == original.stated_confidence
        assert reconstructed.trusted_confidence == original.trusted_confidence
        assert reconstructed.semantic_entropy == original.semantic_entropy
        assert reconstructed.method_versions == original.method_versions

    def test_get_primary_uncertainty_estimate(self):
        """Priority order for primary uncertainty estimate."""
        # Priority 1: semantic_entropy
        sig1 = UncertaintySignal(
            stated_confidence=0.9,
            semantic_entropy=1.5,
        )
        assert sig1.get_primary_uncertainty_estimate() == 1.5

        # Priority 2: token_entropy
        sig2 = UncertaintySignal(
            stated_confidence=0.9,
            token_entropy=2.0,
        )
        assert sig2.get_primary_uncertainty_estimate() == 2.0

        # Priority 3: 1 - trusted_confidence
        sig3 = UncertaintySignal(
            stated_confidence=0.9,
            trusted_confidence=0.8,
        )
        assert abs(sig3.get_primary_uncertainty_estimate() - 0.2) < 1e-9

        # Priority 4: 1 - stated_confidence
        sig4 = UncertaintySignal(
            stated_confidence=0.9,
        )
        assert abs(sig4.get_primary_uncertainty_estimate() - 0.1) < 1e-9

        # None if no uncertainty signals
        sig5 = UncertaintySignal()
        assert sig5.get_primary_uncertainty_estimate() is None

    def test_all_confidence_fields_validated(self):
        """All confidence fields must be in [0, 1]."""
        with pytest.raises(ValueError):
            UncertaintySignal(p_true=1.5)

        with pytest.raises(ValueError):
            UncertaintySignal(p_ik=-0.1)

        with pytest.raises(ValueError):
            UncertaintySignal(answer_frequency=2.0)

        # Valid
        UncertaintySignal(
            p_true=0.5,
            p_ik=0.3,
            answer_frequency=0.7,
        )

    def test_backward_compatibility_helper(self):
        """from_legacy_confidence helper works."""
        sig = from_legacy_confidence(stated=0.9, trusted=0.8)
        assert sig.stated_confidence == 0.9
        assert sig.trusted_confidence == 0.8

        sig2 = from_legacy_confidence(stated=0.85)
        assert sig2.stated_confidence == 0.85
        assert sig2.trusted_confidence is None

    def test_abstention_with_reason(self):
        """Abstention captures reason and prevents predictions."""
        sig = UncertaintySignal(
            abstained=True,
            abstain_reason="insufficient_confidence",
            stated_confidence=0.3,
        )
        assert sig.abstained is True
        assert sig.abstain_reason == "insufficient_confidence"

    def test_raw_signals_preserved(self):
        """Raw signals dictionary is preserved."""
        raw = {'ensemble_votes': {'A': 5, 'B': 3}, 'generation_tokens': 45}
        sig = UncertaintySignal(raw_signals=raw)
        assert sig.raw_signals == raw
        assert sig.to_dict()['raw_signals'] == raw
