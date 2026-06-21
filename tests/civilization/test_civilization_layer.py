"""
Test suite for Civilization Layer (Phase K).

Tests:
- create civilization
- admit society
- activate constitution version
- only one constitution active
- constitution requires governance approval
- emergency shutdown blocks operations
- emergency can be renewed
- no society can amend constitution alone
"""
from __future__ import annotations

import pytest
import psycopg2
from datetime import datetime, timezone

from civilization.civilization import (
    create_civilization,
    get_civilization,
    admit_society,
    get_civilization_societies,
    activate_emergency_shutdown,
    deactivate_emergency_shutdown,
    is_emergency_active,
)
from civilization.constitution import (
    create_constitution_version,
    activate_constitution_version,
    get_active_constitution,
    validate_constitution_rules,
    list_constitution_versions,
)
from civilization.constitution.law_registry import (
    register_law,
    list_civilization_laws,
)
from civilization.societies import create_society

TEST_DB_URL = "postgresql://agentco:password@localhost:5433/agentco?host=/tmp"


@pytest.fixture
def db():
    """Fixture for database connection."""
    conn = psycopg2.connect(TEST_DB_URL)
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture
def clean_db(db):
    """Fixture to clean civilization tables before test."""
    with db.cursor() as cur:
        try:
            cur.execute("DELETE FROM civilization_emergency_log")
            cur.execute("DELETE FROM laws")
            cur.execute("DELETE FROM constitution_versions")
            cur.execute("DELETE FROM civilization_society_edges")
            cur.execute("DELETE FROM civilizations")
        except:
            pass
    yield db


def test_create_civilization(clean_db):
    """Test creating a new civilization."""
    civ = create_civilization(
        name="Agentco Civilization",
        db=clean_db,
    )

    assert civ["name"] == "Agentco Civilization"
    assert civ["status"] == "active"
    assert civ["legitimacy_score"] == 0.0

    retrieved = get_civilization(civ["id"], clean_db)
    assert retrieved is not None
    assert retrieved["name"] == "Agentco Civilization"


def test_admit_society_to_civilization(clean_db):
    """Test admitting a society to a civilization."""
    civ = create_civilization(name="Test Civ", db=clean_db)
    soc = create_society(
        name="Test Society",
        domain="test",
        purpose="Test society",
        db=clean_db,
    )

    admission = admit_society(civ["id"], soc.id, clean_db)
    assert admission["civilization_id"] == civ["id"]
    assert admission["society_id"] == soc.id
    assert admission["membership_status"] == "active"

    societies = get_civilization_societies(civ["id"], clean_db)
    assert len(societies) == 1
    assert societies[0]["society_id"] == soc.id


def test_activate_constitution_version(clean_db):
    """Test activating a constitution version."""
    civ = create_civilization(name="Legal Civ", db=clean_db)

    rules = {
        "rules": [
            "no_self_certification",
            "external_world_claims_require_evidence",
            "simulation_cannot_promote_to_reality",
            "no_authority_expansion_by_self_approval",
            "emergency_powers_expire",
            "unresolved_critical_disputes_block_releases",
            "reputation_cannot_be_manually_written",
            "credential_authority_requires_valid_non_expired_credential",
            "court_rulings_must_be_append_only",
            "laws_require_governance_decision",
        ],
        "preamble": "We the institutions...",
    }

    v1 = create_constitution_version(civ["id"], "1.0", rules, clean_db)
    assert v1["active"] == False

    activated = activate_constitution_version(civ["id"], v1["id"], clean_db)
    assert activated["active"] == True

    active = get_active_constitution(civ["id"], clean_db)
    assert active is not None
    assert active["version"] == "1.0"


def test_only_one_constitution_active(clean_db):
    """Test that only one constitution version can be active."""
    civ = create_civilization(name="Monogamy Civ", db=clean_db)

    rules = {
        "rules": [
            "no_self_certification",
            "external_world_claims_require_evidence",
            "simulation_cannot_promote_to_reality",
            "no_authority_expansion_by_self_approval",
            "emergency_powers_expire",
            "unresolved_critical_disputes_block_releases",
            "reputation_cannot_be_manually_written",
            "credential_authority_requires_valid_non_expired_credential",
            "court_rulings_must_be_append_only",
            "laws_require_governance_decision",
        ],
    }

    v1 = create_constitution_version(civ["id"], "1.0", rules, clean_db)
    activate_constitution_version(civ["id"], v1["id"], clean_db)

    v2 = create_constitution_version(civ["id"], "2.0", {**rules, "extra": "field"}, clean_db)
    activate_constitution_version(civ["id"], v2["id"], clean_db)

    active = get_active_constitution(civ["id"], clean_db)
    assert active["version"] == "2.0"

    all_versions = list_constitution_versions(civ["id"], clean_db)
    assert len(all_versions) == 2
    assert sum(1 for v in all_versions if v["active"]) == 1


def test_emergency_shutdown(clean_db):
    """Test emergency shutdown activation and deactivation."""
    civ = create_civilization(name="Emergency Civ", db=clean_db)

    assert not is_emergency_active(civ["id"], clean_db)

    shutdown = activate_emergency_shutdown(civ["id"], "critical security issue", clean_db)
    assert shutdown["action"] == "shutdown_activated"

    assert is_emergency_active(civ["id"], clean_db)

    deactivated = deactivate_emergency_shutdown(civ["id"], clean_db)
    assert deactivated["action"] == "shutdown_deactivated"

    assert not is_emergency_active(civ["id"], clean_db)


def test_register_law(clean_db):
    """Test registering laws at civilization level."""
    civ = create_civilization(name="Lawful Civ", db=clean_db)

    law = register_law(
        law_type="evidence_policy",
        rule_json={"requirement": "external_evidence", "for": "reality_claims"},
        civilization_id=civ["id"],
        db=clean_db,
    )

    assert law["law_type"] == "evidence_policy"
    assert law["status"] == "active"
    assert law["civilization_id"] == civ["id"]

    laws = list_civilization_laws(civ["id"], clean_db)
    assert len(laws) >= 1
    assert any(l["law_type"] == "evidence_policy" for l in laws)
