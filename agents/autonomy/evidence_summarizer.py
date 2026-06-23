"""
Evidence Summarizer Specialist Agent
=====================================
Passive evidence analysis and extraction.
Restricted to evidence processing only.
"""

from agents.autonomy.specialist_agent import SpecialistAgent
from typing import Dict, Any
import uuid


class EvidenceSummarizerAgent(SpecialistAgent):
    """Evidence summarizer specialist with passive analysis capabilities"""

    def get_allowed_actions(self) -> set:
        """Evidence summarizer can extract and analyze evidence only"""
        return {
            'EXTRACT_EVIDENCE',
            'UPDATE_MEMORY',
            'EVALUATE_PROGRESS'
        }

    def handle_action(self, action_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle evidence summarizer action: EXTRACT_EVIDENCE, UPDATE_MEMORY, EVALUATE_PROGRESS

        Args:
            action_spec: ActionSpec from orchestrator

        Returns:
            Result dict with observations, artifacts, tokens_used
        """
        # Record iteration and check budget
        self.record_iteration()

        action_type = action_spec.get('actionType', '').lower()

        # Only allow passive operations
        if action_type == 'extract_evidence':
            return self._handle_extract_evidence(action_spec)
        elif action_type == 'update_memory':
            return self._handle_update_memory(action_spec)
        elif action_type == 'evaluate_progress':
            return self._handle_evaluate_progress(action_spec)
        else:
            return {
                'observations': {'status': 'blocked', 'reason': f'EvidenceSummarizer cannot perform {action_type}'},
                'artifacts': [],
                'errors': [f'This role does not support {action_type}']
            }

    def _handle_extract_evidence(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Handle evidence extraction action"""
        source_id = spec.get('args', {}).get('sourceId', '')

        if not source_id:
            return {
                'observations': {'status': 'blocked', 'reason': 'No source ID provided'},
                'artifacts': []
            }

        # Simulate extraction and summarization
        summary = {
            'source_id': source_id,
            'summary': f'Summary of evidence from {source_id}',
            'key_points': ['Point 1', 'Point 2', 'Point 3']
        }

        estimated_tokens = 120
        self.record_token_usage(estimated_tokens)

        # Create summarized evidence ID
        artifact_id = str(uuid.uuid4())

        return {
            'observations': {
                'sourceId': source_id,
                'summary': summary['summary'],
                'pointsExtracted': len(summary['key_points']),
                'status': 'extraction_completed'
            },
            'artifacts': [artifact_id]
        }

    def _handle_update_memory(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory update action"""
        content = spec.get('args', {}).get('content', '')

        if not content:
            return {
                'observations': {'status': 'blocked', 'reason': 'No memory content provided'},
                'artifacts': []
            }

        memory_id = str(uuid.uuid4())

        estimated_tokens = 40
        self.record_token_usage(estimated_tokens)

        return {
            'observations': {
                'memoryId': memory_id,
                'contentLength': len(str(content)),
                'status': 'memory_updated'
            },
            'artifacts': [memory_id]
        }

    def _handle_evaluate_progress(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Handle progress evaluation action"""
        estimated_tokens = 50
        self.record_token_usage(estimated_tokens)

        return {
            'observations': {
                'status': 'progress_evaluated',
                'evidenceProcessed': 3,
                'summariesGenerated': 2
            },
            'artifacts': []
        }


if __name__ == '__main__':
    import argparse
    import json

    parser = argparse.ArgumentParser(description='Evidence Summarizer Specialist Agent')
    parser.add_argument('--specialist-id', required=True, help='Unique specialist ID')
    parser.add_argument('--port', type=int, required=True, help='HTTP server port')
    parser.add_argument('--role', required=True, help='Specialist role')
    parser.add_argument('--budget', required=True, help='Budget JSON string')

    args = parser.parse_args()
    budget = json.loads(args.budget)

    agent = EvidenceSummarizerAgent(args.specialist_id, args.role, budget)
    print(f"Starting evidence_summarizer specialist {args.specialist_id} on port {args.port}")
    agent.run_server(args.port)

    # Keep process alive
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"Evidence summarizer specialist {args.specialist_id} shutting down")
        pass
