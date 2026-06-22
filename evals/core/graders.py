"""
Grader Engine — implements various grading strategies for eval trials.

Graders assess model/agent outputs against expected/reference outputs
and produce structured GradingResult objects with correctness scores,
flags, and explanations.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Optional

from evals.core.schema import GradingResult


class BaseGrader(ABC):
    """Base class for all graders."""

    @abstractmethod
    def grade(self, output: Any, expected: Any, **kwargs) -> GradingResult:
        """
        Grade a trial output against expected output.

        Args:
            output: Model/agent output
            expected: Expected/reference output
            **kwargs: Additional context (task_id, input, etc.)

        Returns:
            GradingResult with correctness, score, flags, and explanation
        """
        pass


class ExactMatchGrader(BaseGrader):
    """
    Exact string match grader.

    Case-sensitive by default; configurable.
    """

    def __init__(self, case_sensitive: bool = True, strip_whitespace: bool = True):
        self.case_sensitive = case_sensitive
        self.strip_whitespace = strip_whitespace

    def grade(self, output: Any, expected: Any, **kwargs) -> GradingResult:
        """Grade by exact string match."""
        out_str = str(output).strip() if self.strip_whitespace else str(output)
        exp_str = str(expected).strip() if self.strip_whitespace else str(expected)

        if not self.case_sensitive:
            out_str = out_str.lower()
            exp_str = exp_str.lower()

        correctness = out_str == exp_str
        return GradingResult(
            correctness=correctness,
            score=1.0 if correctness else 0.0,
            explanation="Exact string match" if correctness else f"Expected '{exp_str}', got '{out_str}'",
            grader_version="1.0",
        )


class NormalizedStringMatchGrader(BaseGrader):
    """
    Normalized string match grader.

    Normalizes whitespace, punctuation, and case before comparison.
    """

    def grade(self, output: Any, expected: Any, **kwargs) -> GradingResult:
        """Grade by normalized string match."""

        def normalize(s: str) -> str:
            # Convert to lowercase
            s = s.lower()
            # Remove punctuation
            s = re.sub(r'[^\w\s]', '', s)
            # Normalize whitespace
            s = ' '.join(s.split())
            return s

        out_str = normalize(str(output))
        exp_str = normalize(str(expected))

        correctness = out_str == exp_str
        return GradingResult(
            correctness=correctness,
            score=1.0 if correctness else 0.0,
            explanation="Normalized string match" if correctness else f"Expected '{exp_str}', got '{out_str}'",
            grader_version="1.0",
        )


class BinaryCorrectnesGrader(BaseGrader):
    """
    Binary correctness grader (True/False expected output).
    """

    def grade(self, output: Any, expected: Any, **kwargs) -> GradingResult:
        """Grade binary correctness."""
        # Interpret output as boolean
        out_bool = self._to_bool(output)
        exp_bool = self._to_bool(expected)

        if out_bool is None or exp_bool is None:
            return GradingResult(
                correctness=False,
                score=0.0,
                explanation="Could not interpret output or expected as boolean",
                tool_error_flag=True,
            )

        correctness = out_bool == exp_bool
        return GradingResult(
            correctness=correctness,
            score=1.0 if correctness else 0.0,
            explanation=f"Boolean match: {out_bool} vs {exp_bool}",
        )

    def _to_bool(self, value: Any) -> Optional[bool]:
        """Convert value to boolean."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lower_val = value.lower().strip()
            if lower_val in ('true', 'yes', '1'):
                return True
            if lower_val in ('false', 'no', '0'):
                return False
        if isinstance(value, (int, float)):
            return bool(value)
        return None


class JsonFieldGrader(BaseGrader):
    """
    Grader for JSON-structured outputs.

    Compares specific fields within JSON objects.
    """

    def __init__(self, fields: Optional[list[str]] = None):
        self.fields = fields or []

    def grade(self, output: Any, expected: Any, **kwargs) -> GradingResult:
        """Grade JSON field match."""
        # Parse if string
        out_obj = output if isinstance(output, dict) else {}
        exp_obj = expected if isinstance(expected, dict) else {}

        if not self.fields:
            # Compare entire objects if no fields specified
            correctness = out_obj == exp_obj
            return GradingResult(
                correctness=correctness,
                score=1.0 if correctness else 0.0,
                explanation="JSON object match" if correctness else "JSON mismatch",
            )

        # Compare specified fields
        matches = 0
        mismatches = []
        for field in self.fields:
            out_val = out_obj.get(field)
            exp_val = exp_obj.get(field)
            if out_val == exp_val:
                matches += 1
            else:
                mismatches.append(f"{field}: expected {exp_val}, got {out_val}")

        score = matches / len(self.fields) if self.fields else 0.0
        correctness = score == 1.0

        explanation = f"Fields matched: {matches}/{len(self.fields)}"
        if mismatches:
            explanation += "; " + "; ".join(mismatches)

        return GradingResult(
            correctness=correctness,
            score=score,
            explanation=explanation,
        )


class AbstentionAwareGrader(BaseGrader):
    """
    Grader that handles abstention.

    Marks trials where abstention is appropriate as correct,
    flags inappropriate abstention or predictions.
    """

    def __init__(self, allow_abstention: bool = True):
        self.allow_abstention = allow_abstention

    def grade(self, output: Any, expected: Any, abstained: bool = False, **kwargs) -> GradingResult:
        """Grade with abstention awareness."""
        exp_bool = expected.get('should_abstain', False) if isinstance(expected, dict) else False

        if abstained and exp_bool:
            # Appropriate abstention
            return GradingResult(
                correctness=True,
                score=1.0,
                explanation="Appropriate abstention",
            )

        if abstained and not exp_bool:
            # Inappropriate abstention
            return GradingResult(
                correctness=False,
                score=0.0,
                explanation="Inappropriate abstention (task was answerable)",
                policy_violation_flag=True,
            )

        if not abstained and exp_bool:
            # Should have abstained but didn't
            return GradingResult(
                correctness=False,
                score=0.0,
                explanation="Should have abstained (task was too uncertain)",
                policy_violation_flag=True,
            )

        # Normal prediction case
        exp_answer = expected.get('answer') if isinstance(expected, dict) else expected
        return GradingResult(
            correctness=output == exp_answer,
            score=1.0 if output == exp_answer else 0.0,
            explanation=f"Answer match" if output == exp_answer else f"Expected {exp_answer}, got {output}",
        )


class ToolUseSuccessGrader(BaseGrader):
    """
    Grader for tool-use tasks.

    Checks if correct tools were called and produced expected results.
    """

    def grade(self, output: Any, expected: Any, tool_calls: Optional[list[dict]] = None, **kwargs) -> GradingResult:
        """Grade tool-use success."""
        tool_calls = tool_calls or []

        exp_tools = expected.get('tool_calls', []) if isinstance(expected, dict) else []
        exp_result = expected.get('result') if isinstance(expected, dict) else expected

        # Check tool calls
        if not tool_calls:
            return GradingResult(
                correctness=False,
                score=0.0,
                explanation="No tool calls made",
                tool_error_flag=True,
            )

        # Check result
        result_match = output == exp_result
        if result_match:
            return GradingResult(
                correctness=True,
                score=1.0,
                explanation=f"Tool-use successful ({len(tool_calls)} tools called)",
            )

        return GradingResult(
            correctness=False,
            score=0.5,
            explanation=f"Tools called but result mismatch: expected {exp_result}, got {output}",
        )


class GraderRegistry:
    """Registry of available graders."""

    _graders: dict[str, type[BaseGrader]] = {
        'exact_match': ExactMatchGrader,
        'normalized_string': NormalizedStringMatchGrader,
        'binary': BinaryCorrectnesGrader,
        'json_field': JsonFieldGrader,
        'abstention_aware': AbstentionAwareGrader,
        'tool_use': ToolUseSuccessGrader,
    }

    @classmethod
    def get_grader(cls, grader_id: str, **kwargs) -> BaseGrader:
        """Get grader by ID."""
        grader_class = cls._graders.get(grader_id)
        if not grader_class:
            raise ValueError(f"Unknown grader: {grader_id}")
        return grader_class(**kwargs)

    @classmethod
    def register(cls, grader_id: str, grader_class: type[BaseGrader]):
        """Register a custom grader."""
        cls._graders[grader_id] = grader_class

    @classmethod
    def list_graders(cls) -> list[str]:
        """List available grader IDs."""
        return list(cls._graders.keys())
