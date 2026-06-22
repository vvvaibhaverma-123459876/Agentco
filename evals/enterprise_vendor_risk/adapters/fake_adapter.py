"""
Fake deterministic adapter for testing without external models.
"""
import hashlib
import json
from datetime import datetime

from .base import BaseAdapter, VendorRiskResponse, TrialResult


class FakeDeterministicAdapter(BaseAdapter):
    """Deterministic fake model that makes realistic decisions based on task content."""

    def __init__(self, seed: int = 42):
        super().__init__("fake:deterministic")
        self.seed = seed

    def predict(self, task: dict) -> TrialResult:
        """Make deterministic prediction based on task content hash."""
        start_time = datetime.now()

        try:
            task_id = task.get('task_id', '')
            expected = task.get('expected', {})
            policy = task.get('policy', {})
            evidence = task.get('evidence', [])

            # Deterministic prediction based on task_id and content
            decision_hash = int(hashlib.md5(task_id.encode()).hexdigest(), 16)

            # Use hash to pick decision deterministically
            expected_decision = expected.get('decision', 'escalate')
            expected_risk = expected.get('risk_level', 'medium')

            # Simulate decision-making
            decision = expected_decision
            risk_level = expected_risk

            # Confidence based on evidence count and completeness
            evidence_count = len(evidence)
            base_confidence = 0.6 + (min(evidence_count, 5) / 10.0)
            confidence = min(0.95, base_confidence)

            # Evidence IDs
            evidence_ids = [e.get('evidence_id', '') for e in evidence[:3]]

            # Missing info
            missing_info = expected.get('expected_missing_info', [])

            # Policy checks (simplified)
            policy_checks = []
            for policy_id, policy_value in policy.items():
                if decision == 'approve' and policy_value in [True, 'required']:
                    policy_checks.append({
                        'policy_id': policy_id,
                        'status': 'pass',
                        'reason': f'Evidence supports {policy_id}'
                    })
                elif decision in ['reject', 'escalate']:
                    policy_checks.append({
                        'policy_id': policy_id,
                        'status': 'unknown' if decision == 'escalate' else 'fail',
                        'reason': f'Policy {policy_id} requires review'
                    })

            # Create response
            response = VendorRiskResponse(
                decision=decision,
                risk_level=risk_level,
                confidence=confidence,
                trusted_confidence=max(0.5, confidence - 0.1),
                answer=f"Determined to {decision} this vendor.",
                evidence_ids=evidence_ids,
                missing_information=missing_info,
                policy_checks=policy_checks,
                tool_calls_used=[],
                abstained=False,
                abstain_reason=None,
            )

            # Validate
            errors = self.validate_response(response)

            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

            result = TrialResult(
                task_id=task_id,
                model_id=self.model_id,
                status='completed' if not errors else 'failed',
                raw_output=json.dumps(response.__dict__),
                parsed_output=response if not errors else None,
                latency_ms=elapsed_ms,
                usage=None,
                errors=errors,
            )

            return result

        except Exception as e:
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            return TrialResult(
                task_id=task.get('task_id', 'unknown'),
                model_id=self.model_id,
                status='failed',
                errors=[str(e)],
                latency_ms=elapsed_ms,
            )
