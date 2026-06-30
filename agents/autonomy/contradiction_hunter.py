"""
Contradiction Hunter Specialist Agent
======================================
Find contradictions in claims and evidence.
"""

from agents.autonomy.specialist_agent import SpecialistAgent
from typing import Dict, Any
import uuid


class ContradictionHunterAgent(SpecialistAgent):
    """Find contradictions in claims and evidence"""

    def get_allowed_actions(self) -> set:
        """Return allowed action types for this specialist"""
        return {
            'EXTRACT_EVIDENCE',
            'GENERATE_CLAIM',
            'UPDATE_MEMORY',
            'EVALUATE_PROGRESS',
        }

    def handle_action(self, action_spec: Dict[str, Any]) -> Dict[str, Any]:
        self.record_iteration()
        action_type = action_spec.get('actionType', '').lower()

        if action_type == 'extract_evidence':
            return self._handle_extract_evidence(action_spec)
        elif action_type == 'generate_claim':
            return self._handle_generate_claim(action_spec)
        elif action_type == 'evaluate_progress':
            return self._handle_evaluate_progress(action_spec)
        else:
            return {'observations': {'status': 'blocked', 'reason': f'{action_type} not allowed'}, 'artifacts': []}

    def _handle_extract_evidence(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        estimated_tokens = 120
        self.record_token_usage(estimated_tokens)
        evidence_id = str(uuid.uuid4())
        return {
            'observations': {
                'status': 'extraction_completed',
                'evidenceId': evidence_id,
                'contradictionsFound': 2
            },
            'artifacts': [evidence_id]
        }

    def _handle_generate_claim(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        claim_text = spec.get('args', {}).get('claimText', '')
        support_source_ids = spec.get('args', {}).get('supportSourceIds', [])
        if not claim_text or not support_source_ids:
            return {'observations': {'status': 'blocked'}, 'artifacts': []}
        estimated_tokens = 100
        self.record_token_usage(estimated_tokens)
        claim_id = str(uuid.uuid4())
        return {
            'observations': {
                'claimId': claim_id,
                'status': 'contradiction_claim_generated',
                'claimType': 'counter_claim',
                'confidenceScore': 0.75
            },
            'artifacts': [claim_id]
        }

    def _handle_evaluate_progress(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        estimated_tokens = 80
        self.record_token_usage(estimated_tokens)
        return {
            'observations': {
                'status': 'progress_evaluated',
                'contradictionsAnalyzed': 4,
                'counterClaimsGenerated': 2,
                'readinessForResolution': 0.7
            },
            'artifacts': []
        }


if __name__ == '__main__':
    import argparse, json, time
    parser = argparse.ArgumentParser(description='Contradiction Hunter Specialist Agent')
    parser.add_argument('--specialist-id', required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--role', required=True)
    parser.add_argument('--budget', required=True)
    args = parser.parse_args()
    budget = json.loads(args.budget)
    agent = ContradictionHunterAgent(args.specialist_id, args.role, budget)
    print(f"Starting contradiction_hunter specialist {args.specialist_id} on port {args.port}")
    agent.run_server(args.port)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
