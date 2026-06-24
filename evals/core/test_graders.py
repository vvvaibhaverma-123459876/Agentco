"""
Tests for grader engine implementations.
"""
import pytest
from evals.core.graders import (
    ExactMatchGrader,
    NormalizedStringMatchGrader,
    BinaryCorrectnesGrader,
    JsonFieldGrader,
    AbstentionAwareGrader,
    ToolUseSuccessGrader,
    GraderRegistry,
)


class TestExactMatchGrader:
    """Test exact match grader."""

    def test_exact_match_pass(self):
        """Exact match passes."""
        grader = ExactMatchGrader()
        result = grader.grade("hello", "hello")
        assert result.correctness is True
        assert result.score == 1.0

    def test_exact_match_fail(self):
        """Exact match fails for different strings."""
        grader = ExactMatchGrader()
        result = grader.grade("hello", "world")
        assert result.correctness is False
        assert result.score == 0.0

    def test_case_sensitive(self):
        """Case sensitivity matters by default."""
        grader = ExactMatchGrader(case_sensitive=True)
        result = grader.grade("Hello", "hello")
        assert result.correctness is False

    def test_case_insensitive(self):
        """Case insensitivity when configured."""
        grader = ExactMatchGrader(case_sensitive=False)
        result = grader.grade("Hello", "hello")
        assert result.correctness is True

    def test_whitespace_stripping(self):
        """Whitespace is stripped by default."""
        grader = ExactMatchGrader(strip_whitespace=True)
        result = grader.grade("  hello  ", "hello")
        assert result.correctness is True


class TestNormalizedStringMatchGrader:
    """Test normalized string match grader."""

    def test_normalized_match(self):
        """Normalized strings match."""
        grader = NormalizedStringMatchGrader()
        result = grader.grade("Hello, World!", "hello world")
        assert result.correctness is True

    def test_punctuation_removed(self):
        """Punctuation is normalized."""
        grader = NormalizedStringMatchGrader()
        result = grader.grade("Hello.", "Hello")
        assert result.correctness is True

    def test_normalized_fail(self):
        """Different normalized strings fail."""
        grader = NormalizedStringMatchGrader()
        result = grader.grade("hello", "world")
        assert result.correctness is False


class TestBinaryCorrectnesGrader:
    """Test binary correctness grader."""

    def test_bool_match(self):
        """Boolean values match."""
        grader = BinaryCorrectnesGrader()
        result = grader.grade(True, True)
        assert result.correctness is True

    def test_bool_mismatch(self):
        """Boolean values mismatch."""
        grader = BinaryCorrectnesGrader()
        result = grader.grade(True, False)
        assert result.correctness is False

    def test_string_bool_true(self):
        """String 'true' is interpreted as True."""
        grader = BinaryCorrectnesGrader()
        result = grader.grade("true", True)
        assert result.correctness is True

    def test_string_bool_false(self):
        """String 'false' is interpreted as False."""
        grader = BinaryCorrectnesGrader()
        result = grader.grade("false", False)
        assert result.correctness is True

    def test_numeric_bool(self):
        """Numbers are interpreted as bool."""
        grader = BinaryCorrectnesGrader()
        result1 = grader.grade(1, True)
        assert result1.correctness is True
        result2 = grader.grade(0, False)
        assert result2.correctness is True


class TestJsonFieldGrader:
    """Test JSON field grader."""

    def test_full_object_match(self):
        """Full object matching."""
        grader = JsonFieldGrader(fields=[])  # No specific fields
        result = grader.grade({'a': 1, 'b': 2}, {'a': 1, 'b': 2})
        assert result.correctness is True

    def test_field_match(self):
        """Specific field matching."""
        grader = JsonFieldGrader(fields=['answer'])
        result = grader.grade({'answer': 42, 'other': 'ignored'}, {'answer': 42})
        assert result.correctness is True

    def test_field_mismatch(self):
        """Field mismatch detected."""
        grader = JsonFieldGrader(fields=['answer'])
        result = grader.grade({'answer': 42}, {'answer': 43})
        assert result.correctness is False
        assert result.score == 0.0

    def test_multiple_fields_partial_match(self):
        """Partial field matching."""
        grader = JsonFieldGrader(fields=['answer', 'confidence'])
        result = grader.grade(
            {'answer': 42, 'confidence': 0.9},
            {'answer': 42, 'confidence': 0.8},
        )
        assert result.correctness is False
        assert result.score == 0.5  # 1 out of 2 fields match


class TestAbstentionAwareGrader:
    """Test abstention-aware grader."""

    def test_appropriate_abstention(self):
        """Appropriate abstention is marked correct."""
        grader = AbstentionAwareGrader()
        result = grader.grade(None, {'should_abstain': True}, abstained=True)
        assert result.correctness is True

    def test_inappropriate_abstention(self):
        """Inappropriate abstention is marked incorrect."""
        grader = AbstentionAwareGrader()
        result = grader.grade(None, {'should_abstain': False}, abstained=True)
        assert result.correctness is False
        assert result.policy_violation_flag is True

    def test_should_abstain_but_didnt(self):
        """Failing to abstain when appropriate is incorrect."""
        grader = AbstentionAwareGrader()
        result = grader.grade('answer', {'should_abstain': True}, abstained=False)
        assert result.correctness is False
        assert result.policy_violation_flag is True

    def test_normal_prediction_correct(self):
        """Normal prediction matches expected."""
        grader = AbstentionAwareGrader()
        result = grader.grade(42, {'answer': 42, 'should_abstain': False}, abstained=False)
        assert result.correctness is True


class TestToolUseSuccessGrader:
    """Test tool-use success grader."""

    def test_no_tool_calls(self):
        """No tool calls returns error."""
        grader = ToolUseSuccessGrader()
        result = grader.grade('result', {'result': 'expected'}, tool_calls=[])
        assert result.correctness is False
        assert result.tool_error_flag is True

    def test_tool_use_success(self):
        """Correct tool use is marked successful."""
        grader = ToolUseSuccessGrader()
        result = grader.grade(
            'correct_result',
            {'result': 'correct_result', 'tool_calls': ['search']},
            tool_calls=[{'name': 'search', 'args': {}}],
        )
        assert result.correctness is True

    def test_tool_use_result_mismatch(self):
        """Tool-use result mismatch is partial success."""
        grader = ToolUseSuccessGrader()
        result = grader.grade(
            'wrong_result',
            {'result': 'correct_result'},
            tool_calls=[{'name': 'search', 'args': {}}],
        )
        assert result.correctness is False
        assert result.score == 0.5


class TestGraderRegistry:
    """Test grader registry."""

    def test_get_exact_match_grader(self):
        """Get exact match grader by ID."""
        grader = GraderRegistry.get_grader('exact_match')
        assert isinstance(grader, ExactMatchGrader)

    def test_get_normalized_string_grader(self):
        """Get normalized string grader by ID."""
        grader = GraderRegistry.get_grader('normalized_string')
        assert isinstance(grader, NormalizedStringMatchGrader)

    def test_unknown_grader_raises(self):
        """Unknown grader ID raises error."""
        with pytest.raises(ValueError, match="Unknown grader"):
            GraderRegistry.get_grader('nonexistent')

    def test_list_graders(self):
        """List available graders."""
        graders = GraderRegistry.list_graders()
        assert 'exact_match' in graders
        assert 'normalized_string' in graders
        assert 'binary' in graders

    def test_register_custom_grader(self):
        """Register and retrieve custom grader."""
        from evals.core.graders import BaseGrader

        class DummyGrader(BaseGrader):
            def grade(self, output, expected, **kwargs):
                from evals.core.schema import GradingResult
                return GradingResult(correctness=True, score=1.0)

        GraderRegistry.register('dummy', DummyGrader)
        grader = GraderRegistry.get_grader('dummy')
        assert isinstance(grader, DummyGrader)
