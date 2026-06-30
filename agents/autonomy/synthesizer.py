"""
Synthesizer Specialist Agent
=============================
Combine multiple claims into higher-level conclusions.
"""

from agents.autonomy.specialist_agent import SpecialistAgent
from typing import Dict, Any
import uuid


class SynthesizerAgent(SpecialistAgent):
    """Synthesize multiple claims into conclusions"""

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

        if action_type == 'generate_claim':
            return self._handle_generate_claim(action_spec)
        elif action_type == 'update_memory':
            return self._handle_update_memory(action_spec)
        elif action_type == 'evaluate_progress':
            return self._handle_evaluate_progress(action_spec)
        else:
            return {'observations': {'status': 'blocked', 'reason': f'{action_type} not allowed'}, 'artifacts': []}

    def _handle_generate_claim(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        claim_text = spec.get('args', {}).get('claimText', '')
        support_source_ids = spec.get('args', {}).get('supportSourceIds', [])
        if not claim_text or not support_source_ids:
            return {'observations': {'status': 'blocked'}, 'artifacts': []}
        estimated_tokens = 140
        self.record_token_usage(estimated_tokens)
        claim_id = str(uuid.uuid4())
        return {
            'observations': {
                'claimId': claim_id,
                'status': 'meta_claim_generated',
                'claimType': 'synthesis',
                'sourcesIntegrated': len(support_source_ids),
                'confidenceScore': 0.8
            },
            'artifacts': [claim_id]
        }

    def _handle_update_memory(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        estimated_tokens = 70
        self.record_token_usage(estimated_tokens)
        memory_id = str(uuid.uuid4())
        return {
            'observations': {
                'memoryId': memory_id,
                'status': 'synthesis_recorded',
                'synthesisDepth': 2
            },
            'artifacts': [memory_id]
        }

    def _handle_evaluate_progress(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        estimated_tokens = 90
        self.record_token_usage(estimated_tokens)
        return {
            'observations': {
                'status': 'progress_evaluated',
                'claimsSynthesized': 5,
                'metaClaimsGenerated': 2,
                'integrationQuality': 0.85
            },
            'artifacts': []
        }


if __name__ == '__main__':
    import argparse, json, time
    parser = argparse.ArgumentParser(description='Synthesizer Specialist Agent')
    parser.add_argument('--specialist-id', required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--role', required=True)
    parser.add_argument('--budget', required=True)
    args = parser.parse_args()
    budget = json.loads(args.budget)
    agent = SynthesizerAgent(args.specialist_id, args.role, budget)
    print(f"Starting synthesizer specialist {args.specialist_id} on port {args.port}")
    agent.run_server(args.port)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
