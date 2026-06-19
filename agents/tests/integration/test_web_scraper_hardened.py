"""
Integration test: register_prediction against real prediction_ledger DB.

Requires DATABASE_URL pointing at a DB with prediction_ledger migrated.
The root conftest.py auto-discovers the socket-based sandbox DB if needed.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

import psycopg2
import pytest

from agents.core.tools.web_scraper import register_prediction


def _have_prediction_ledger() -> bool:
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        return False
    try:
        conn = psycopg2.connect(db_url)
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM information_schema.tables WHERE table_name='prediction_ledger'"
                )
                return cur.fetchone() is not None
    except Exception:
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


pytestmark = pytest.mark.skipif(
    not _have_prediction_ledger(),
    reason="prediction_ledger table not found in DATABASE_URL — run migration 011 first",
)


def _make_record(**overrides) -> dict:
    base = {
        "claim": f"Integration test claim {uuid.uuid4()}",
        "probability": 0.75,
        "confidence_basis": {"test": True, "source": "integration"},
        "producing_agent_id": "integration_test_agent",
        "producing_prompt_version": "test_v1.0",
        "resolution_criterion": "Verified by integration test runner",
        "resolution_date": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
        "ground_truth_source": "https://example.com/test",
        "horizon_class": "medium",
        "domain": "science",
    }
    base.update(overrides)
    return base


class TestRegisterPredictionIntegration:
    def test_insert_and_read_back(self):
        record = _make_record()
        pid = register_prediction(record)

        assert isinstance(pid, str)
        assert len(pid) == 36  # UUID format

        # Read back and verify key fields
        db_url = os.environ["DATABASE_URL"]
        conn = psycopg2.connect(db_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT claim, probability, producing_agent_id, horizon_class, domain, resolved "
                    "FROM prediction_ledger WHERE prediction_id = %s",
                    (pid,),
                )
                row = cur.fetchone()
        finally:
            conn.close()

        assert row is not None, f"prediction_id {pid} not found in prediction_ledger"
        claim, prob, agent_id, horizon, domain, resolved = row
        assert claim == record["claim"]
        assert float(prob) == pytest.approx(0.75, abs=1e-4)
        assert agent_id == "integration_test_agent"
        assert horizon == "medium"
        assert domain == "science"
        assert resolved is False

    def test_duplicate_claim_different_ids(self):
        """Each registration produces a unique prediction_id."""
        record = _make_record(claim="Identical claim text for dedup test")
        pid1 = register_prediction(record)
        pid2 = register_prediction(record)
        assert pid1 != pid2

    def test_ledger_immutability_enforced(self):
        """DB trigger must reject any attempt to UPDATE pre-registration columns."""
        record = _make_record()
        pid = register_prediction(record)

        db_url = os.environ["DATABASE_URL"]
        conn = psycopg2.connect(db_url)
        try:
            with pytest.raises(psycopg2.errors.RaiseException, match="IMMUTABILITY"):
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE prediction_ledger SET claim = 'tampered' WHERE prediction_id = %s",
                            (pid,),
                        )
        finally:
            conn.close()

    def test_missing_required_field_raises_before_db(self):
        record = _make_record()
        del record["probability"]
        with pytest.raises(ValueError, match="probability"):
            register_prediction(record)

    def test_optional_fields_default_correctly(self):
        record = _make_record()
        pid = register_prediction(record)

        db_url = os.environ["DATABASE_URL"]
        conn = psycopg2.connect(db_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT claim_type, post_hoc, correlation_id FROM prediction_ledger WHERE prediction_id = %s",
                    (pid,),
                )
                row = cur.fetchone()
        finally:
            conn.close()

        claim_type, post_hoc, correlation_id = row
        assert claim_type == "general"
        assert post_hoc is False
        assert correlation_id is None
