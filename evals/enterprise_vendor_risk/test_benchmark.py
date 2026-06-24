"""
Tests for enterprise vendor risk triage benchmark.
"""
import json
import pytest
from pathlib import Path

from evals.enterprise_vendor_risk.adapters.fake_adapter import FakeDeterministicAdapter
from evals.enterprise_vendor_risk.score import VendorRiskScorer
from evals.enterprise_vendor_risk.run_benchmark import load_dataset


class TestDataset:
    """Test dataset schema and content."""

    def test_dataset_loads(self):
        """Dataset loads successfully."""
        cases = load_dataset()
        assert len(cases) == 15
        assert all('task_id' in c for c in cases)
        assert all('vendor_name' in c for c in cases)
        assert all('evidence' in c for c in cases)

    def test_dataset_schema(self):
        """Each case has required fields."""
        cases = load_dataset()
        required_fields = ['task_id', 'vendor_name', 'scenario', 'policy', 'evidence', 'question', 'expected']
        for case in cases:
            for field in required_fields:
                assert field in case, f"Missing {field} in {case['task_id']}"

    def test_expected_schema(self):
        """Expected outcomes have required fields."""
        cases = load_dataset()
        required_exp = ['decision', 'risk_level', 'must_not_claim', 'required_evidence_ids']
        for case in cases:
            exp = case['expected']
            for field in required_exp:
                assert field in exp, f"Missing {field} in {case['task_id']}"


class TestFakeAdapter:
    """Test fake deterministic adapter."""

    def test_fake_adapter_deterministic(self):
        """Fake adapter produces deterministic output."""
        adapter = FakeDeterministicAdapter(seed=42)
        cases = load_dataset()
        case = cases[0]

        result1 = adapter.predict(case)
        result2 = adapter.predict(case)

        assert result1.parsed_output.decision == result2.parsed_output.decision
        assert result1.parsed_output.confidence == result2.parsed_output.confidence

    def test_fake_adapter_response_schema(self):
        """Fake adapter returns valid response schema."""
        adapter = FakeDeterministicAdapter()
        case = load_dataset()[0]

        result = adapter.predict(case)
        assert result.status == 'completed'
        assert result.parsed_output is not None

        response = result.parsed_output
        assert response.decision in ['approve', 'reject', 'escalate', 'abstain']
        assert response.risk_level in ['low', 'medium', 'high', 'critical', 'unknown']
        assert 0.0 <= response.confidence <= 1.0

    def test_fake_adapter_validates_response(self):
        """Adapter validates response schema."""
        adapter = FakeDeterministicAdapter()
        case = load_dataset()[0]

        result = adapter.predict(case)
        errors = adapter.validate_response(result.parsed_output)
        assert len(errors) == 0, f"Validation errors: {errors}"


class TestScoring:
    """Test scoring logic."""

    def test_scorer_perfect_prediction(self):
        """Perfect prediction scores high."""
        scorer = VendorRiskScorer()
        trial = {
            'parsed_output': {
                'decision': 'approve',
                'risk_level': 'low',
                'confidence': 0.95,
                'evidence_ids': ['ev_001_a', 'ev_001_b', 'ev_001_c'],
                'answer': 'This vendor meets all requirements.',
            }
        }
        case = {
            'expected': {
                'decision': 'approve',
                'risk_level': 'low',
                'must_not_claim': [],
                'required_evidence_ids': ['ev_001_a', 'ev_001_b'],
                'abstention_or_escalation_required': False,
            }
        }

        score = scorer.score_trial(trial, case)
        assert score['decision_correct'] is True
        assert score['risk_level_correct'] is True
        assert score['overall_score'] > 0.8

    def test_scorer_wrong_decision(self):
        """Wrong decision scores low."""
        scorer = VendorRiskScorer()
        trial = {
            'parsed_output': {
                'decision': 'reject',
                'risk_level': 'high',
                'confidence': 0.9,
                'evidence_ids': [],
                'answer': 'Reject this vendor.',
            }
        }
        case = {
            'expected': {
                'decision': 'approve',
                'risk_level': 'low',
                'must_not_claim': [],
                'required_evidence_ids': ['ev_001_a'],
                'abstention_or_escalation_required': False,
            }
        }

        score = scorer.score_trial(trial, case)
        assert score['decision_correct'] is False
        assert score['overall_score'] < 0.5

    def test_scorer_hallucination_detection(self):
        """Hallucination in claims is detected."""
        scorer = VendorRiskScorer()
        trial = {
            'parsed_output': {
                'decision': 'approve',
                'risk_level': 'low',
                'confidence': 0.95,
                'evidence_ids': ['ev_001_a'],
                'answer': 'This vendor has confirmed SOC 2 Type II certification.',  # Hallucination
            }
        }
        case = {
            'expected': {
                'decision': 'approve',
                'risk_level': 'low',
                'must_not_claim': ['confirmed SOC 2 Type II'],
                'required_evidence_ids': ['ev_001_a'],
                'abstention_or_escalation_required': False,
            }
        }

        score = scorer.score_trial(trial, case)
        assert score['policy_compliance'] == 0.0

    def test_scorer_aggregate(self):
        """Aggregation works correctly."""
        scorer = VendorRiskScorer()
        cases = load_dataset()[:3]
        adapter = FakeDeterministicAdapter()

        results = {
            'per_model_metrics': {
                'fake:deterministic': {
                    'trials': [adapter.predict(c).to_dict() for c in cases]
                }
            }
        }

        per_model = scorer.aggregate_scores(results, cases)
        assert 'fake:deterministic' in per_model
        assert 'overall_score' in per_model['fake:deterministic']
        assert 'decision_accuracy' in per_model['fake:deterministic']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
