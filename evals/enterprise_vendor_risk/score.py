"""
Scoring logic for vendor risk triage benchmark with advanced metrics.
"""
import math
import numpy as np
from typing import Any, Optional


class VendorRiskScorer:
    """Score vendor risk assessments against expected outcomes."""

    def score_trial(self, trial: dict, case: dict) -> dict:
        """Score single trial against expected outcome."""
        expected = case.get('expected', {})
        parsed_output = trial.get('parsed_output', {})

        if not parsed_output:
            return {
                'overall_score': 0.0,
                'decision_correct': False,
                'risk_level_correct': False,
                'evidence_precision': 0.0,
                'evidence_recall': 0.0,
                'evidence_f1': 0.0,
                'policy_compliance': 0.0,
                'hallucination_rate': 1.0,
                'calibration_accuracy': 0.0,
                'escalation_correct': False,
                'errors': trial.get('errors', []),
            }

        # Scores
        decision_correct = self._score_decision(parsed_output, expected)
        risk_level_correct = self._score_risk_level(parsed_output, expected)
        evidence_scores = self._score_evidence(parsed_output, expected)
        policy_compliance = self._score_policy(parsed_output, expected)
        hallucination_rate = self._score_hallucination(parsed_output, expected)
        calibration_accuracy = self._score_calibration(parsed_output, expected)
        escalation_correct = self._score_escalation(parsed_output, expected)

        # Weighted overall score
        overall_score = (
            0.25 * (1.0 if decision_correct else 0.0) +
            0.15 * (1.0 if risk_level_correct else 0.0) +
            0.15 * evidence_scores['f1'] +
            0.15 * policy_compliance +
            0.10 * (1.0 - hallucination_rate) +
            0.10 * calibration_accuracy +
            0.10 * (1.0 if escalation_correct else 0.0)
        )

        return {
            'overall_score': overall_score,
            'decision_correct': decision_correct,
            'risk_level_correct': risk_level_correct,
            'evidence_precision': evidence_scores['precision'],
            'evidence_recall': evidence_scores['recall'],
            'evidence_f1': evidence_scores['f1'],
            'policy_compliance': policy_compliance,
            'hallucination_rate': hallucination_rate,
            'calibration_accuracy': calibration_accuracy,
            'escalation_correct': escalation_correct,
        }

    def _score_decision(self, output: dict, expected: dict) -> bool:
        """Check if decision matches expected."""
        return output.get('decision') == expected.get('decision')

    def _score_risk_level(self, output: dict, expected: dict) -> bool:
        """Check if risk level matches expected."""
        actual = output.get('risk_level', 'unknown')
        exp = expected.get('risk_level', 'unknown')
        return actual == exp

    def _score_evidence(self, output: dict, expected: dict) -> dict:
        """Score evidence precision and recall."""
        actual_ids = set(output.get('evidence_ids', []))
        required_ids = set(expected.get('required_evidence_ids', []))

        if not required_ids:
            precision = 1.0 if not actual_ids else 0.5
            recall = 1.0
        else:
            intersection = actual_ids & required_ids
            precision = len(intersection) / max(len(actual_ids), 1)
            recall = len(intersection) / len(required_ids)

        f1 = 2 * (precision * recall) / max(precision + recall, 1e-9)

        return {
            'precision': precision,
            'recall': recall,
            'f1': f1,
        }

    def _score_policy(self, output: dict, expected: dict) -> float:
        """Score policy compliance."""
        must_not_claim = expected.get('must_not_claim', [])
        answer = output.get('answer', '').lower()

        # Check for forbidden claims
        for claim in must_not_claim:
            if claim.lower() in answer:
                return 0.0

        return 1.0

    def _score_hallucination(self, output: dict, expected: dict) -> float:
        """Score hallucination rate (0.0 = good, 1.0 = bad)."""
        must_not_claim = expected.get('must_not_claim', [])
        answer = output.get('answer', '').lower()

        if not must_not_claim:
            return 0.0

        violations = sum(1 for claim in must_not_claim if claim.lower() in answer)
        return violations / len(must_not_claim)

    def _score_calibration(self, output: dict, expected: dict) -> float:
        """Score confidence calibration (Brier score)."""
        confidence = output.get('confidence', 0.5)
        decision_correct = self._score_decision(output, expected)
        outcome = 1.0 if decision_correct else 0.0

        brier = (confidence - outcome) ** 2
        # Convert back to score: 0=bad (brier=1), 1=good (brier=0)
        return 1.0 - min(brier, 1.0)

    def _score_escalation(self, output: dict, expected: dict) -> bool:
        """Check if escalation decision is correct."""
        exp_escalate = expected.get('abstention_or_escalation_required', False)
        actual_escalate = output.get('decision') in ['escalate', 'abstain']
        return actual_escalate == exp_escalate

    def _compute_mce(self, scores: list[dict]) -> float:
        """Maximum Calibration Error: max |accuracy_in_bin - mean_confidence_in_bin|."""
        if not scores:
            return 0.0

        confidences = []
        outcomes = []
        for s in scores:
            conf = s.get('calibration_accuracy', 0.5)
            correct = 1.0 if s['decision_correct'] else 0.0
            confidences.append(conf)
            outcomes.append(correct)

        if not confidences:
            return 0.0

        bins = np.linspace(0, 1, 11)
        mce = 0.0

        for i in range(len(bins) - 1):
            mask = (np.array(confidences) >= bins[i]) & (np.array(confidences) < bins[i + 1])
            if np.any(mask):
                bin_acc = np.mean(np.array(outcomes)[mask])
                bin_conf = np.mean(np.array(confidences)[mask])
                mce = max(mce, abs(bin_acc - bin_conf))

        return mce

    def _compute_selective_accuracy(self, scores: list[dict], threshold: float = 0.8) -> dict:
        """Selective accuracy: accuracy when confidence >= threshold."""
        if not scores:
            return {'selective_accuracy': 0.0, 'coverage': 0.0}

        confident_scores = [s for s in scores if s.get('calibration_accuracy', 0) >= threshold]

        if not confident_scores:
            return {'selective_accuracy': 0.0, 'coverage': 0.0}

        accuracy = sum(1 for s in confident_scores if s['decision_correct']) / len(confident_scores)
        coverage = len(confident_scores) / len(scores)

        return {
            'selective_accuracy': accuracy,
            'coverage': coverage,
        }

    def _compute_auroc(self, scores: list[dict]) -> float:
        """AUROC: Area under ROC curve (approximated via trapezoid method)."""
        if not scores:
            return 0.5

        confidences = np.array([s.get('calibration_accuracy', 0.5) for s in scores])
        outcomes = np.array([1.0 if s['decision_correct'] else 0.0 for s in scores])

        sorted_idx = np.argsort(-confidences)
        sorted_outcomes = outcomes[sorted_idx]

        tp = np.cumsum(sorted_outcomes)
        fp = np.cumsum(1 - sorted_outcomes)

        tpr = tp / max(np.sum(sorted_outcomes), 1)
        fpr = fp / max(np.sum(1 - sorted_outcomes), 1)

        auroc = np.trapz(tpr, fpr)
        return float(np.clip(auroc, 0.0, 1.0))

    def aggregate_scores(self, results: dict, cases: dict) -> dict:
        """Aggregate scores across all models and cases with advanced metrics."""
        per_model = {}

        for model_id, model_data in results.get('per_model_metrics', {}).items():
            trials = model_data.get('trials', [])
            case_lookup = {c['task_id']: c for c in cases}

            scores = []
            for trial in trials:
                task_id = trial.get('task_id')
                case = case_lookup.get(task_id)
                if case:
                    score = self.score_trial(trial, case)
                    scores.append(score)

            if scores:
                selective_acc = self._compute_selective_accuracy(scores, threshold=0.8)
                mce = self._compute_mce(scores)
                auroc = self._compute_auroc(scores)

                per_model[model_id] = {
                    'n_trials': len(scores),
                    'overall_score': sum(s['overall_score'] for s in scores) / len(scores),
                    'decision_accuracy': sum(1 for s in scores if s['decision_correct']) / len(scores),
                    'risk_level_accuracy': sum(1 for s in scores if s['risk_level_correct']) / len(scores),
                    'policy_compliance': sum(s['policy_compliance'] for s in scores) / len(scores),
                    'hallucination_rate': sum(s['hallucination_rate'] for s in scores) / len(scores),
                    'evidence_f1': sum(s['evidence_f1'] for s in scores) / len(scores),
                    'calibration_accuracy': sum(s['calibration_accuracy'] for s in scores) / len(scores),
                    'escalation_accuracy': sum(1 for s in scores if s['escalation_correct']) / len(scores),
                    'mce': mce,
                    'selective_accuracy': selective_acc['selective_accuracy'],
                    'coverage': selective_acc['coverage'],
                    'auroc': auroc,
                }

        return per_model
