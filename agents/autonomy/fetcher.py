"""
Fetcher Specialist Agent
========================
Read-only data gathering: fetch pages only.
Restricted tool access for safety.
"""

from agents.autonomy.specialist_agent import SpecialistAgent
from typing import Dict, Any
import uuid


class FetcherAgent(SpecialistAgent):
    """Fetcher specialist with limited, safe tool access"""

    def handle_action(self, action_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle fetcher action: FETCH_PAGE or EVALUATE_PROGRESS only

        Args:
            action_spec: ActionSpec from orchestrator

        Returns:
            Result dict with observations, artifacts, tokens_used
        """
        # Record iteration and check budget
        self.record_iteration()

        action_type = action_spec.get('actionType', '').lower()

        # Only allow specific actions
        if action_type == 'fetch_page':
            return self._handle_fetch_page(action_spec)
        elif action_type == 'evaluate_progress':
            return self._handle_evaluate_progress(action_spec)
        else:
            return {
                'observations': {'status': 'blocked', 'reason': f'Fetcher cannot perform {action_type}'},
                'artifacts': [],
                'errors': [f'Fetcher role does not support {action_type}']
            }

    def _handle_fetch_page(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Handle page fetch action"""
        url = spec.get('args', {}).get('url', '')

        if not url:
            return {
                'observations': {'status': 'blocked', 'reason': 'No URL provided'},
                'artifacts': []
            }

        # Simulate page fetch (in real implementation, would use web adapter)
        content = f"Content from {url}. This is a fetcher result."
        title = f"Page: {url.split('/')[-1]}"

        # Estimate tokens
        estimated_tokens = len(content) // 4
        self.record_token_usage(estimated_tokens)

        # Create evidence ID
        artifact_id = str(uuid.uuid4())

        return {
            'observations': {
                'url': url,
                'title': title,
                'contentLength': len(content),
                'status': 'fetch_completed'
            },
            'artifacts': [artifact_id]
        }

    def _handle_evaluate_progress(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Handle progress evaluation action"""
        estimated_tokens = 50
        self.record_token_usage(estimated_tokens)

        return {
            'observations': {
                'status': 'progress_evaluated',
                'progress': 'Fetcher ready'
            },
            'artifacts': []
        }
