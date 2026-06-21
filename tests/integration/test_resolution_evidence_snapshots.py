from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")

DSN = os.environ.get("AGENTCO_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DSN, reason="AGENTCO_TEST_DATABASE_URL not set - real Postgres required"
)

ROOT = Path(__file__).resolve().parents[2]


def _sql(path: str) -> str:
    return (ROOT / path).read_text()


def _apply_migrations(cur) -> None:
    for tbl in (
        "resolution_evidence_snapshots",
        "calibration_credentials",
        "credential_domains",
        "prediction_ledger",
    ):
        cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
    cur.execute(_sql("backend/src/db/migrations/011_prediction_ledger.sql"))
    cur.execute(_sql("reserve/migrations/001_reserve_extension.sql"))
    cur.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='resolution_service') "
        "THEN CREATE ROLE resolution_service LOGIN PASSWORD 'test'; END IF; END $$;"
    )
    cur.execute("GRANT USAGE ON SCHEMA public TO resolution_service;")
    cur.execute("GRANT INSERT, SELECT, UPDATE ON prediction_ledger TO resolution_service;")
    cur.execute(_sql("backend/src/db/migrations/017_resolution_evidence_snapshots.sql"))


@pytest.fixture()
def db():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        _apply_migrations(cur)
    yield conn
    with conn.cursor() as cur:
        for tbl in (
            "resolution_evidence_snapshots",
            "calibration_credentials",
            "credential_domains",
            "prediction_ledger",
        ):
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
    conn.close()


def _seed_prediction(db) -> str:
    from calibration import create_calibration_engine
    from calibration.ledger.prediction_ledger import PredictionRegistration

    cal = create_calibration_engine(db=db)
    return cal["ledger"].pre_register(
        PredictionRegistration(
            claim="Snapshot integration fixture resolves true.",
            probability=0.72,
            confidence_basis={"fixture": "resolution_evidence_snapshots"},
            producing_agent_id="snapshot-agent",
            producing_prompt_version="test",
            resolution_criterion="external fixture resolves true",
            resolution_date=datetime.now(timezone.utc) - timedelta(days=1),
            ground_truth_source="https://truth.example/snapshot-fixture",
            horizon_class="short",
            domain="integration",
            claim_type="fixture",
            claim_source_url="https://claims.example/snapshot-fixture",
        )
    )


def _resolve_with_snapshot(prediction_id: str):
    from calibration import create_calibration_engine

    res_conn = psycopg2.connect(DSN)
    res_conn.autocommit = True
    with res_conn.cursor() as cur:
        cur.execute("SET ROLE resolution_service;")
    cal = create_calibration_engine(db=res_conn)
    record = cal["ledger"].get(prediction_id)
    assert record is not None
    resolved = cal["resolution"].resolve(
        prediction_id=prediction_id,
        outcome=True,
        ground_truth_source="https://truth.example/snapshot-fixture",
        evidence={
            "source_url": "https://truth.example/snapshot-fixture",
            "resolution_source_type": "external_document",
            "resolution_content_hash": "snapshot-resolution-content-v1",
        },
        resolver_id="resolution-service",
        resolver_type="service",
        claim_source_url="https://claims.example/snapshot-fixture",
        resolution_url="https://truth.example/snapshot-fixture",
    )
    cal["ledger"].persist_resolution(resolved)
    res_conn.close()
    return resolved


def test_migration_creates_resolution_evidence_snapshot_table(db):
    with db.cursor() as cur:
        cur.execute("SELECT to_regclass('public.resolution_evidence_snapshots')")
        assert cur.fetchone()[0] == "resolution_evidence_snapshots"


def test_snapshot_inserted_and_linked_on_resolution(db):
    prediction_id = _seed_prediction(db)
    _resolve_with_snapshot(prediction_id)

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT prediction_id, resolver_id, resolver_type,
                   claim_source_fingerprint, resolution_source_fingerprint,
                   independence_verdict, evidence, evidence_hash
              FROM resolution_evidence_snapshots
             WHERE prediction_id = %s
            """,
            (prediction_id,),
        )
        row = cur.fetchone()

    assert row is not None
    assert str(row[0]) == prediction_id
    assert row[1] == "resolution-service"
    assert row[2] == "service"
    assert row[3]["canonical_url"] == "https://claims.example/snapshot-fixture"
    assert row[4]["canonical_url"] == "https://truth.example/snapshot-fixture"
    assert row[5]["independent"] is True
    assert row[6]["source_url"] == "https://truth.example/snapshot-fixture"
    assert len(row[7]) == 64


def test_snapshot_is_append_only_for_update_and_delete(db):
    prediction_id = _seed_prediction(db)
    _resolve_with_snapshot(prediction_id)

    with pytest.raises(psycopg2.errors.RaiseException, match="append-only"):
        with db.cursor() as cur:
            cur.execute(
                "UPDATE resolution_evidence_snapshots SET evidence_hash = 'tampered' WHERE prediction_id = %s",
                (prediction_id,),
            )
    db.rollback()

    with pytest.raises(psycopg2.errors.RaiseException, match="append-only"):
        with db.cursor() as cur:
            cur.execute(
                "DELETE FROM resolution_evidence_snapshots WHERE prediction_id = %s",
                (prediction_id,),
            )
    db.rollback()


def test_resolution_fails_if_snapshot_cannot_be_inserted(db):
    prediction_id = _seed_prediction(db)
    with db.cursor() as cur:
        cur.execute("DROP TABLE resolution_evidence_snapshots")

    with pytest.raises(RuntimeError, match="snapshot could not be persisted"):
        _resolve_with_snapshot(prediction_id)

    with db.cursor() as cur:
        cur.execute("SELECT resolved FROM prediction_ledger WHERE prediction_id = %s", (prediction_id,))
        assert cur.fetchone()[0] is False


def test_resolution_evidence_survives_reload(db):
    prediction_id = _seed_prediction(db)
    _resolve_with_snapshot(prediction_id)

    reloaded = psycopg2.connect(DSN)
    reloaded.autocommit = True
    try:
        with reloaded.cursor() as cur:
            cur.execute(
                "SELECT evidence_hash FROM resolution_evidence_snapshots WHERE prediction_id = %s",
                (prediction_id,),
            )
            evidence_hash = cur.fetchone()[0]
        assert len(evidence_hash) == 64
    finally:
        reloaded.close()
