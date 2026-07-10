"""
Unit Tests for Specialist Agents
==================================
Tests for HTTP server functionality, budget enforcement, and action handling.
"""

import pytest
import json
import time
from datetime import datetime
from agents.autonomy.specialist_agent import SpecialistAgent
from agents.autonomy.researcher import ResearcherAgent
from agents.autonomy.fetcher import FetcherAgent
from agents.autonomy.evidence_summarizer import EvidenceSummarizerAgent
from agents.autonomy.claim_validator import ClaimValidatorAgent
from agents.autonomy.reviewer import ReviewerAgent


class TestSpecialistAgentBase:
    """Test SpecialistAgent base class functionality"""

    def test_specialist_initialization(self):
        """Test specialist agent initialization"""
        budget = {'tokens': 1000, 'iterations': 10, 'seconds': 60}
        agent = ResearcherAgent('test-123', 'researcher', budget)

        assert agent.specialist_id == 'test-123'
        assert agent.role == 'researcher'
        assert agent.budget == budget
        assert agent.tokens_used == 0
        assert agent.iterations_used == 0

    def test_budget_tracking(self):
        """Test budget usage tracking"""
        budget = {'tokens': 1000, 'iterations': 10, 'seconds': 60}
        agent = ResearcherAgent('test-456', 'researcher', budget)

        agent.record_token_usage(100)
        assert agent.tokens_used == 100

        agent.record_iteration()
        assert agent.iterations_used == 1

    def test_token_budget_exceeded(self):
        """Test token budget enforcement"""
        budget = {'tokens': 100, 'iterations': 10, 'seconds': 60}
        agent = ResearcherAgent('test-789', 'researcher', budget)

        # Use 100 tokens (at limit)
        agent.record_token_usage(100)
        agent.check_budget()  # Should not raise

        # Exceeding the budget raises as soon as usage is recorded
        with pytest.raises(RuntimeError, match='Token budget exceeded'):
            agent.record_token_usage(50)
            agent.check_budget()

    def test_iteration_budget_exceeded(self):
        """Test iteration budget enforcement"""
        budget = {'tokens': 10000, 'iterations': 3, 'seconds': 60}
        agent = ResearcherAgent('test-iter', 'researcher', budget)

        agent.record_iteration()
        agent.record_iteration()
        agent.record_iteration()

        # Next iteration should fail
        with pytest.raises(RuntimeError, match='Iteration budget exceeded'):
            agent.record_iteration()

    def test_time_budget_exceeded(self):
        """Test time budget enforcement"""
        budget = {'tokens': 10000, 'iterations': 100, 'seconds': 1}
        agent = ResearcherAgent('test-time', 'researcher', budget)

        # Sleep past budget
        time.sleep(1.1)

        with pytest.raises(RuntimeError, match='Time budget exceeded'):
            agent.check_budget()

    def test_get_status(self):
        """Test status reporting"""
        budget = {'tokens': 1000, 'iterations': 10, 'seconds': 60}
        agent = ResearcherAgent('test-status', 'researcher', budget)

        agent.record_token_usage(250)
        agent.record_iteration()

        status = agent.get_status()
        assert status['specialist_id'] == 'test-status'
        assert status['role'] == 'researcher'
        assert status['tokens_used'] == 250
        assert status['iterations_used'] == 1
        assert status['budget'] == budget


class TestResearcherAgent:
    """Test ResearcherAgent implementation"""

    def test_web_search_action(self):
        """Test web search action handling"""
        budget = {'tokens': 10000, 'iterations': 100, 'seconds': 60}
        agent = ResearcherAgent('researcher-1', 'researcher', budget)
        agent.real_web_search = lambda query: {
            'status': 'search_completed',
            'query': query,
            'results': [
                {'url': 'https://example.com/agents', 'title': 'Agents', 'snippet': 'Autonomous agents fixture'}
            ],
        }
        agent.persist_evidence = lambda **_kwargs: 'artifact-search-1'

        action_spec = {
            'actionType': 'web_search',
            'args': {'query': 'autonomous agents'},
            'objective': 'Search for information'
        }

        result = agent.handle_action(action_spec)

        assert result['observations']['status'] == 'search_completed'
        assert 'resultsFound' in result['observations']
        assert len(result['artifacts']) > 0

    def test_fetch_page_action(self):
        """Test fetch page action handling"""
        budget = {'tokens': 10000, 'iterations': 100, 'seconds': 60}
        agent = ResearcherAgent('researcher-2', 'researcher', budget)
        agent.real_fetch_page = lambda url: {
            'status': 'fetch_completed',
            'url': url,
            'title': 'Example fixture',
            'content': 'Fetched fixture content',
            'content_type': 'text/html',
            'content_length': 23,
        }
        agent.persist_evidence = lambda **_kwargs: 'artifact-fetch-1'

        action_spec = {
            'actionType': 'fetch_page',
            'args': {'url': 'https://example.com'},
            'objective': 'Fetch page content'
        }

        result = agent.handle_action(action_spec)

        assert result['observations']['status'] == 'fetch_completed'
        assert 'artifacts' in result

    def test_generate_claim_action(self):
        """Test claim generation with evidence"""
        budget = {'tokens': 10000, 'iterations': 100, 'seconds': 60}
        agent = ResearcherAgent('researcher-3', 'researcher', budget)
        agent.persist_claim = lambda **_kwargs: 'claim-fixture-1'

        action_spec = {
            'actionType': 'generate_claim',
            'args': {
                'claimText': 'AI systems are becoming more autonomous',
                'supportSourceIds': ['source-1', 'source-2']
            },
            'objective': 'Generate claim'
        }

        result = agent.handle_action(action_spec)

        assert result['observations']['status'] == 'claim_generated'
        assert 'claimId' in result['observations']
        assert len(result['artifacts']) > 0

    def test_unsupported_action(self):
        """Test handling of unsupported action types"""
        budget = {'tokens': 10000, 'iterations': 100, 'seconds': 60}
        agent = ResearcherAgent('researcher-4', 'researcher', budget)

        action_spec = {
            'actionType': 'unsupported_action',
            'args': {},
            'objective': 'This should fail'
        }

        result = agent.handle_action(action_spec)

        assert 'errors' in result
        assert len(result['errors']) > 0


class TestFetcherAgent:
    """Test FetcherAgent with restricted capabilities"""

    def test_fetch_allowed(self):
        """Test that fetcher can handle FETCH_PAGE"""
        budget = {'tokens': 5000, 'iterations': 20, 'seconds': 120}
        agent = FetcherAgent('fetcher-1', 'fetcher', budget)
        agent.real_fetch_page = lambda url: {
            'status': 'fetch_completed',
            'url': url,
            'title': 'Example fixture',
            'content': 'Fetched fixture content',
            'content_type': 'text/html',
            'content_length': 23,
        }
        agent.persist_evidence = lambda **_kwargs: 'artifact-fetch-1'

        action_spec = {
            'actionType': 'fetch_page',
            'args': {'url': 'https://example.com'},
            'objective': 'Fetch'
        }

        result = agent.handle_action(action_spec)
        assert result['observations']['status'] == 'fetch_completed'

    def test_search_blocked(self):
        """Test that fetcher CANNOT perform search"""
        budget = {'tokens': 5000, 'iterations': 20, 'seconds': 120}
        agent = FetcherAgent('fetcher-2', 'fetcher', budget)

        action_spec = {
            'actionType': 'web_search',
            'args': {'query': 'test'},
            'objective': 'Search'
        }

        result = agent.handle_action(action_spec)
        assert 'errors' in result
        assert 'does not support' in result['errors'][0]


class TestEvidenceSummarizerAgent:
    """Test EvidenceSummarizerAgent"""

    def test_extract_evidence(self):
        """Test evidence extraction against a real seeded evidence row"""
        import os
        import uuid

        if not os.environ.get('DATABASE_URL'):
            pytest.skip('DATABASE_URL not set; extraction reads real autonomy_evidence rows')

        from agents.db.connection import get_db

        source_id = f'src-{uuid.uuid4().hex[:12]}'
        db = get_db()
        try:
            db.execute_query(
                """INSERT INTO autonomy_evidence (source_id, url, title, snippet, retrieved_at)
                   VALUES (%s, %s, %s, %s, NOW())""",
                [source_id, 'https://example.org/specialist-evidence',
                 'Specialist evidence fixture', 'A short snippet used to verify real extraction.'],
            )
        except Exception as exc:
            pytest.skip(f'Postgres unavailable for evidence extraction test: {exc}')

        budget = {'tokens': 3000, 'iterations': 15, 'seconds': 180}
        agent = EvidenceSummarizerAgent('summarizer-1', 'evidence_summarizer', budget)

        action_spec = {
            'actionType': 'extract_evidence',
            'args': {'sourceId': source_id},
            'objective': 'Extract'
        }

        result = agent.handle_action(action_spec)
        assert result['observations']['status'] == 'extraction_completed'

        # Unknown sources must block honestly rather than fabricate output
        missing = agent.handle_action({
            'actionType': 'extract_evidence',
            'args': {'sourceId': f'missing-{uuid.uuid4().hex[:8]}'},
            'objective': 'Extract'
        })
        assert missing['observations']['status'] == 'blocked'

    def test_claim_generation_blocked(self):
        """Test that summarizer cannot generate claims"""
        budget = {'tokens': 3000, 'iterations': 15, 'seconds': 180}
        agent = EvidenceSummarizerAgent('summarizer-2', 'evidence_summarizer', budget)

        action_spec = {
            'actionType': 'generate_claim',
            'args': {'claimText': 'test', 'supportSourceIds': ['s1']},
            'objective': 'Generate claim'
        }

        result = agent.handle_action(action_spec)
        assert 'errors' in result


class TestClaimValidatorAgent:
    """Test ClaimValidatorAgent"""

    def test_generate_validated_claim(self):
        """Test claim generation with validation"""
        budget = {'tokens': 5000, 'iterations': 25, 'seconds': 200}
        agent = ClaimValidatorAgent('validator-1', 'claim_validator', budget)

        action_spec = {
            'actionType': 'generate_claim',
            'args': {
                'claimText': 'This is a well-validated claim',
                'supportSourceIds': ['ev-1']
            },
            'objective': 'Validate claim'
        }

        result = agent.handle_action(action_spec)
        assert result['observations']['status'] == 'claim_generated'
        assert result['observations']['confidence'] == 0.8

    def test_claim_without_evidence_blocked(self):
        """Test that unsupported claims are blocked"""
        budget = {'tokens': 5000, 'iterations': 25, 'seconds': 200}
        agent = ClaimValidatorAgent('validator-2', 'claim_validator', budget)

        action_spec = {
            'actionType': 'generate_claim',
            'args': {
                'claimText': 'Unsupported claim',
                'supportSourceIds': []  # No evidence!
            },
            'objective': 'Invalid'
        }

        result = agent.handle_action(action_spec)
        assert result['observations']['status'] == 'blocked'


class TestReviewerAgent:
    """Test ReviewerAgent"""

    def test_evaluate_progress(self):
        """Test progress evaluation"""
        budget = {'tokens': 1000, 'iterations': 5, 'seconds': 60}
        agent = ReviewerAgent('reviewer-1', 'reviewer', budget)

        action_spec = {
            'actionType': 'evaluate_progress',
            'args': {'goalId': 'goal-1'},
            'objective': 'Evaluate'
        }

        result = agent.handle_action(action_spec)
        assert result['observations']['status'] == 'progress_evaluated'
        assert 'healthCheck' in result['observations']

    def test_reviewer_restricted(self):
        """Test that reviewer can only evaluate progress"""
        budget = {'tokens': 1000, 'iterations': 5, 'seconds': 60}
        agent = ReviewerAgent('reviewer-2', 'reviewer', budget)

        action_spec = {
            'actionType': 'fetch_page',
            'args': {'url': 'https://example.com'},
            'objective': 'Fetch'
        }

        result = agent.handle_action(action_spec)
        assert 'errors' in result
        assert 'evaluate_progress' in result['errors'][0]
