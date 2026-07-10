"""
Real pytest test for civilization free-run positive path.

This test creates actual database rows, stubs the orchestrator,
and verifies the complete run_free_run flow including calibration updates.
"""
import asyncio
import json
import uuid
from unittest.mock import patch, AsyncMock

import pytest

# Import at module level to avoid repeated imports
from agents.db import get_db
from agents.civilization_service import CivilizationService


def _db_or_skip():
    db = get_db()
    try:
        db.connect()
    except Exception as exc:
        pytest.skip(f"Postgres civilization integration unavailable: {exc}")
    return db


@pytest.fixture
def test_data():
    """Create real test data in DB (in FK order). Cleanup after test."""
    db = _db_or_skip()

    # Create goal
    goal_id = str(uuid.uuid4())
    db.execute_update(
        """INSERT INTO autonomy_goals
           (id, title, status, source, proposed_by, domain, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, NOW())""",
        (goal_id, "Test Goal", "proposed", "agent_proposed", "test", "autonomy"),
    )

    # Create action
    action_id = str(uuid.uuid4())
    db.execute_update(
        """INSERT INTO autonomy_goal_actions
           (id, action_id, goal_id, action_type, objective, created_at)
           VALUES (%s, %s, %s, %s, %s, NOW())""",
        (str(uuid.uuid4()), action_id, goal_id, "web_search", "Test"),
    )

    # Create evidence
    evidence_source_id = str(uuid.uuid4())
    evidence_id = str(uuid.uuid4())
    db.execute_update(
        """INSERT INTO autonomy_evidence
           (id, source_id, action_id, url, title, snippet, retrieved_at,
            content_hash, source_type, is_public_access, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s, %s, %s, NOW())""",
        (evidence_id, evidence_source_id, action_id, "http://example.com",
         "Test", "snippet", "hash", "web", True),
    )

    # Create claim
    claim_id = str(uuid.uuid4())
    db.execute_update(
        """INSERT INTO autonomy_claims
           (id, claim_id, action_id, text, status, confidence,
            support_source_ids, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())""",
        (str(uuid.uuid4()), claim_id, action_id, "Test claim",
         "proposed", 0.75, json.dumps([evidence_source_id])),
    )

    yield {
        "goal_id": goal_id,
        "action_id": action_id,
        "claim_id": claim_id,
        "evidence_id": evidence_id,
        "evidence_source_id": evidence_source_id,
    }

    # Cleanup: delete test data
    try:
        db.execute_update("DELETE FROM autonomy_claims WHERE claim_id = %s", (claim_id,))
        db.execute_update("DELETE FROM autonomy_evidence WHERE id = %s", (evidence_id,))
        db.execute_update("DELETE FROM autonomy_goal_actions WHERE action_id = %s", (action_id,))
        db.execute_update("DELETE FROM autonomy_goals WHERE id = %s", (goal_id,))
    except Exception as e:
        print(f"Cleanup warning: {e}")


@pytest.mark.asyncio
async def test_execute_goals_positive_path(test_data):
    """Test _execute_goals with real claim/evidence matching."""
    service = CivilizationService(mode="fixture")

    # Stub orchestrator to return the artifact IDs
    artifact_ids = [test_data["claim_id"], test_data["evidence_source_id"]]

    with patch('agents.civilization_service.execute_goal_via_orchestrator') as mock_exec:
        mock_exec.return_value = {
            "status": "success",
            "artifact_ids": artifact_ids,
            "actionsExecuted": 1,
            "reason": "test",
        }

        result = await service._execute_goals([test_data["goal_id"]], 10)

    # Assertions
    assert result['claims'] == 1, f"Expected 1 claim, got {result['claims']}"
    assert result['evidence'] == 1, f"Expected 1 evidence, got {result['evidence']}"
    assert test_data["claim_id"] in result['claim_ids'], "Claim ID not matched"


@pytest.mark.asyncio
async def test_run_free_run_positive_path(test_data):
    """Test full run_free_run with claims > 0 (includes calibration)."""
    service = CivilizationService(mode="fixture")

    # Stub orchestrator
    artifact_ids = [test_data["claim_id"], test_data["evidence_source_id"]]

    with patch('agents.civilization_service.execute_goal_via_orchestrator') as mock_exec:
        mock_exec.return_value = {
            "status": "success",
            "artifact_ids": artifact_ids,
            "actionsExecuted": 1,
            "reason": "test",
        }

        # Also stub internal goal generation to use our test goal
        with patch('agents.civilization_service.insert_autonomy_goal') as mock_goal:
            mock_goal.return_value = test_data["goal_id"]

            result = await service.run_free_run(duration_seconds=10)

    # Assertions
    assert result.claims_extracted > 0, "No claims extracted"
    assert result.report_path is not None, "No report generated"
    assert len(result.errors) == 0, f"Unexpected errors: {result.errors}"

    # Check calibration updates
    assert result.calibration_updates is not None
    assert result.calibration_updates.get('predictions_registered', 0) > 0, \
        "No predictions registered"

    # Verify report exists and contains Phase 3c status
    with open(result.report_path) as f:
        report = f.read()

    assert "PHASE 3" in report, "Report missing phase status"
    assert "Predictions Registered:" in report, "Report missing calibration section"
