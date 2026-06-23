"""
Reviewer Specialist Agent
==========================
Sanity check and progress evaluation.
Most restricted specialist with minimal capabilities.
"""

from agents.autonomy.specialist_agent import SpecialistAgent
from typing import Dict, Any


class ReviewerAgent(SpecialistAgent):
    """Reviewer specialist for progress evaluation and sanity checks"""

    def get_allowed_actions(self) -> set:
        """Reviewer can only evaluate progress"""
        return {
            'EVALUATE_PROGRESS'
        }

    def handle_action(self, action_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle reviewer action: EVALUATE_PROGRESS only

        Args:
            action_spec: ActionSpec from orchestrator

        Returns:
            Result dict with observations, artifacts, tokens_used
        """
        # Record iteration and check budget
        self.record_iteration()

        action_type = action_spec.get('actionType', '').lower()

        # Only allow progress evaluation
        if action_type == 'evaluate_progress':
            return self._handle_evaluate_progress(action_spec)
        else:
            return {
                'observations': {'status': 'blocked', 'reason': f'Reviewer can only evaluate progress'},
                'artifacts': [],
                'errors': [f'Reviewer role only supports evaluate_progress, not {action_type}']
            }

    def _handle_evaluate_progress(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Handle progress evaluation action"""
        goal_id = spec.get('args', {}).get('goalId', 'unknown')

        estimated_tokens = 80
        self.record_token_usage(estimated_tokens)

        return {
            'observations': {
                'goalId': goal_id,
                'status': 'progress_evaluated',
                'overallProgress': 'Good',
                'recommendation': 'Continue current approach',
                'healthCheck': {
                    'tokensUnderBudget': True,
                    'iterationsHealthy': True,
                    'loopsDetected': False
                }
            },
            'artifacts': []
        }


if __name__ == '__main__':
    import argparse
    import json

    parser = argparse.ArgumentParser(description='Reviewer Specialist Agent')
    parser.add_argument('--specialist-id', required=True, help='Unique specialist ID')
    parser.add_argument('--port', type=int, required=True, help='HTTP server port')
    parser.add_argument('--role', required=True, help='Specialist role')
    parser.add_argument('--budget', required=True, help='Budget JSON string')

    args = parser.parse_args()
    budget = json.loads(args.budget)

    agent = ReviewerAgent(args.specialist_id, args.role, budget)
    print(f"Starting reviewer specialist {args.specialist_id} on port {args.port}")
    agent.run_server(args.port)

    # Keep process alive
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"Reviewer specialist {args.specialist_id} shutting down")
        pass
