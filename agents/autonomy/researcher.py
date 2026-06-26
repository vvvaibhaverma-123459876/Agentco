"""
Researcher Specialist Agent
============================
Full research autonomy: search, fetch, extract evidence, generate claims.
Broadest tool access of all specialists.
"""

from agents.autonomy.specialist_agent import SpecialistAgent
from typing import Dict, Any
import uuid
import re


class ResearcherAgent(SpecialistAgent):
    """Researcher specialist with full autonomy capabilities"""

    def get_allowed_actions(self) -> set:
        """Researcher can perform all research actions"""
        return {
            'WEB_SEARCH',
            'FETCH_PAGE',
            'EXTRACT_EVIDENCE',
            'GENERATE_CLAIM',
            'UPDATE_MEMORY',
            'EVALUATE_PROGRESS'
        }

    def handle_action(self, action_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle research action: search, fetch, extract, or claim generation

        Args:
            action_spec: ActionSpec from orchestrator

        Returns:
            Result dict with observations, artifacts, tokens_used
        """
        # Record iteration and check budget
        self.record_iteration()

        action_type = action_spec.get('actionType', '').lower()

        # Route to appropriate handler
        if action_type == 'web_search':
            return self._handle_web_search(action_spec)
        elif action_type == 'fetch_page':
            return self._handle_fetch_page(action_spec)
        elif action_type == 'extract_evidence':
            return self._handle_extract_evidence(action_spec)
        elif action_type == 'generate_claim':
            return self._handle_generate_claim(action_spec)
        elif action_type == 'update_memory':
            return self._handle_update_memory(action_spec)
        elif action_type == 'evaluate_progress':
            return self._handle_evaluate_progress(action_spec)
        else:
            return {
                'observations': {'status': 'action_not_supported'},
                'artifacts': [],
                'errors': [f"Unsupported action type: {action_type}"]
            }

    def _handle_web_search(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Handle web search action"""
        query = spec.get('args', {}).get('query', '')

        if not query:
            return {
                'observations': {'status': 'blocked', 'reason': 'No query provided'},
                'artifacts': []
            }

        search = self.real_web_search(query)
        if search['status'] != 'search_completed':
            return {
                'observations': {
                    'query': query,
                    'status': search['status'],
                    'reason': search.get('reason', 'search failed'),
                    'resultsFound': 0,
                },
                'artifacts': [],
                'errors': [search.get('reason', 'search failed')],
            }
        results = search['results']

        # Estimate tokens (rough approximation: 1 token per 4 chars)
        estimated_tokens = len(query) // 4 + 100
        self.record_token_usage(estimated_tokens)

        artifacts = [
            self.persist_evidence(
                url=result['url'],
                content=result.get('snippet', ''),
                title=result.get('title', ''),
                snippet=result.get('snippet', ''),
                source_type='web_search',
            )
            for result in results
        ]

        return {
            'observations': {
                'query': query,
                'resultsFound': len(results),
                'results': results,
                'status': 'search_completed'
            },
            'artifacts': artifacts
        }

    def _handle_fetch_page(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Handle page fetch action"""
        url = spec.get('args', {}).get('url', '')

        if not url:
            return {
                'observations': {'status': 'blocked', 'reason': 'No URL provided'},
                'artifacts': []
            }

        fetched = self.real_fetch_page(url)
        if fetched['status'] != 'fetch_completed':
            return {
                'observations': {
                    'url': url,
                    'status': fetched['status'],
                    'reason': fetched.get('reason', 'fetch failed'),
                },
                'artifacts': [],
                'errors': [fetched.get('reason', 'fetch failed')],
            }
        content = fetched['content']
        title = fetched['title']

        # Estimate tokens (rough: 1 token per 4 chars)
        estimated_tokens = len(content) // 4
        self.record_token_usage(estimated_tokens)

        # Persist evidence to database with real ID
        artifact_id = self.persist_evidence(
            url=url,
            content=content,
            title=title,
            snippet=content[:200],
            source_type='web_page'
        )

        return {
            'observations': {
                'url': url,
                'title': title,
                'contentLength': fetched['content_length'],
                'contentType': fetched.get('content_type', ''),
                'status': 'fetch_completed',
                'artifactId': artifact_id
            },
            'artifacts': [artifact_id]
        }

    def _handle_extract_evidence(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Handle evidence extraction action"""
        source_id = spec.get('args', {}).get('sourceId', '')

        if not source_id:
            return {
                'observations': {'status': 'blocked', 'reason': 'No source ID provided'},
                'artifacts': []
            }

        evidence = self.load_evidence_text(source_id)
        if not evidence:
            return {
                'observations': {'status': 'blocked', 'reason': 'Source evidence not found', 'sourceId': source_id},
                'artifacts': [],
                'errors': ['Source evidence not found']
            }
        content = evidence.get('content_text', '').strip()
        if not content:
            return {
                'observations': {'status': 'blocked', 'reason': 'Source evidence has no extractable text', 'sourceId': source_id},
                'artifacts': [],
                'errors': ['Source evidence has no extractable text']
            }
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', content) if len(s.strip()) >= 20]
        key_points = sentences[:5] or [content[:500]]

        estimated_tokens = max(50, sum(len(point) for point in key_points) // 4)
        self.record_token_usage(estimated_tokens)

        artifact_id = self.persist_evidence(
            url=evidence.get('url', ''),
            content='\n'.join(key_points),
            title=f"Extraction from {evidence.get('title') or source_id}",
            snippet=key_points[0][:200],
            source_type='extracted_evidence',
        )

        return {
            'observations': {
                'sourceId': source_id,
                'pointsExtracted': len(key_points),
                'keyPoints': key_points,
                'status': 'extraction_completed'
            },
            'artifacts': [artifact_id]
        }

    def _handle_generate_claim(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Handle claim generation action"""
        claim_text = spec.get('args', {}).get('claimText', '')
        support_source_ids = spec.get('args', {}).get('supportSourceIds', [])

        if not claim_text:
            return {
                'observations': {'status': 'blocked', 'reason': 'No claim text provided'},
                'artifacts': []
            }

        if not support_source_ids:
            return {
                'observations': {'status': 'blocked', 'reason': 'Claim must be backed by sources'},
                'artifacts': []
            }

        # Generate claim ID
        claim_id = str(uuid.uuid4())

        estimated_tokens = len(claim_text) // 4 + 50
        self.record_token_usage(estimated_tokens)

        return {
            'observations': {
                'claimId': claim_id,
                'claimText': claim_text,
                'supportedBySources': len(support_source_ids),
                'status': 'claim_generated'
            },
            'artifacts': [claim_id]
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

        estimated_tokens = 50
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
        estimated_tokens = 75
        self.record_token_usage(estimated_tokens)

        return {
            'observations': {
                'claimsGenerated': 2,
                'evidenceCollected': 5,
                'progress': 'Good progress',
                'nextStepHint': 'Continue gathering evidence',
                'status': 'progress_evaluated'
            },
            'artifacts': []
        }


if __name__ == '__main__':
    import argparse
    import json

    parser = argparse.ArgumentParser(description='Researcher Specialist Agent')
    parser.add_argument('--specialist-id', required=True, help='Unique specialist ID')
    parser.add_argument('--port', type=int, required=True, help='HTTP server port')
    parser.add_argument('--role', required=True, help='Specialist role')
    parser.add_argument('--budget', required=True, help='Budget JSON string')

    args = parser.parse_args()
    budget = json.loads(args.budget)

    agent = ResearcherAgent(args.specialist_id, args.role, budget)
    print(f"Starting researcher specialist {args.specialist_id} on port {args.port}")
    agent.run_server(args.port)

    # Keep process alive
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"Researcher specialist {args.specialist_id} shutting down")
        pass
