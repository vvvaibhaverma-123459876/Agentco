"""
Specialist Agent Base Class
============================
Foundation for all specialist agents.
Handles HTTP server, budget tracking, and action execution.
"""

from agents.base_agent import BaseAgent
from flask import Flask, request, jsonify
import threading
import json
from datetime import datetime
from typing import Dict, Any, Optional


class SpecialistAgent(BaseAgent):
    """Base specialist agent with HTTP server for orchestrator communication"""

    def __init__(self, specialist_id: str, role: str, budget: Dict[str, int]):
        """
        Initialize specialist agent

        Args:
            specialist_id: Unique identifier for this specialist instance
            role: Specialist role (researcher, fetcher, etc.)
            budget: {"tokens": int, "iterations": int, "seconds": int}
        """
        super().__init__(name=f"{role}_specialist_{specialist_id}")
        self.specialist_id = specialist_id
        self.role = role
        self.budget = budget  # {tokens, iterations, seconds}

        self.tokens_used = 0
        self.iterations_used = 0
        self.start_time = datetime.now()

        # Flask app for HTTP communication
        self.app = Flask(f"specialist_{specialist_id}")
        self.setup_routes()

    def setup_routes(self):
        """Register HTTP endpoints for orchestrator communication"""

        @self.app.route('/execute', methods=['POST'])
        def execute_action():
            """Execute action spec and return result"""
            try:
                action_spec = request.json
                if not action_spec:
                    return jsonify({
                        'status': 'failed',
                        'errors': ['No action spec provided']
                    }), 400

                # Check budget before executing
                self.check_budget()

                # Execute action (subclass implements)
                result = self.handle_action(action_spec)

                return jsonify({
                    'status': 'completed',
                    'observations': result.get('observations', {}),
                    'artifacts': result.get('artifacts', []),
                    'tokens_used': self.tokens_used,
                    'errors': result.get('errors')
                }), 200

            except RuntimeError as e:
                # Budget exceeded or other constraint violation
                return jsonify({
                    'status': 'failed',
                    'errors': [str(e)]
                }), 429  # 429 Too Many Requests (budget exceeded)

            except Exception as e:
                return jsonify({
                    'status': 'failed',
                    'errors': [str(e)]
                }), 500

        @self.app.route('/status', methods=['GET'])
        def status():
            """Return specialist status and budget usage"""
            elapsed = (datetime.now() - self.start_time).total_seconds()
            return jsonify({
                'specialist_id': self.specialist_id,
                'role': self.role,
                'status': 'running',
                'tokens_used': self.tokens_used,
                'iterations_used': self.iterations_used,
                'elapsed_seconds': elapsed,
                'budget': self.budget
            }), 200

        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return jsonify({'status': 'healthy'}), 200

    def handle_action(self, action_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an action based on its spec.
        Must be implemented by subclasses.

        Args:
            action_spec: ActionSpec from orchestrator

        Returns:
            {
                'observations': dict,
                'artifacts': list of artifact IDs,
                'errors': optional error list
            }
        """
        raise NotImplementedError(f"handle_action not implemented for {self.role}")

    def check_budget(self):
        """Check if any budget is exceeded, raise if so"""
        elapsed = (datetime.now() - self.start_time).total_seconds()

        if elapsed > self.budget['seconds']:
            raise RuntimeError(
                f"Time budget exceeded: {elapsed:.1f}s > {self.budget['seconds']}s"
            )

        if self.tokens_used > self.budget['tokens']:
            raise RuntimeError(
                f"Token budget exceeded: {self.tokens_used} > {self.budget['tokens']}"
            )

        if self.iterations_used > self.budget['iterations']:
            raise RuntimeError(
                f"Iteration budget exceeded: {self.iterations_used} > {self.budget['iterations']}"
            )

    def record_token_usage(self, tokens: int):
        """Record token usage and check budget"""
        self.tokens_used += tokens
        self.check_budget()

    def record_iteration(self):
        """Record action iteration and check budget"""
        self.iterations_used += 1
        self.check_budget()

    def run_server(self, port: int):
        """
        Run Flask server in background thread

        Args:
            port: Port number to listen on

        Returns:
            Thread reference
        """
        def run():
            self.app.run(host='127.0.0.1', port=port, debug=False, threaded=True)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread

    def get_status(self) -> Dict[str, Any]:
        """Get current specialist status"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return {
            'specialist_id': self.specialist_id,
            'role': self.role,
            'tokens_used': self.tokens_used,
            'iterations_used': self.iterations_used,
            'elapsed_seconds': elapsed,
            'budget': self.budget
        }
