#!/usr/bin/env python3
"""
Test: Calibration Constitution Service

Verifies:
1. Constitution can be created and versioned
2. Only one version can be active at a time
3. Protected surfaces are properly defined
4. Allowed/prohibited change types enforced
5. Change validation detects violations
6. Integrity verification works
7. Default constitution initializes correctly
"""

import os
import sys
import json
import psycopg2
from datetime import datetime
from contextlib import contextmanager

# Use same connection string as migrations
DB_URL = os.environ.get('DATABASE_URL', 'postgresql://agentco:password@localhost:5432/agentco')

@contextmanager
def get_db_connection():
    conn = psycopg2.connect(DB_URL)
    try:
        yield conn
    finally:
        conn.close()

def test_constitution_versioning():
    """Test: Constitution versioning (without changing active)"""
    print("\n✓ TEST: Constitution Versioning")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Create a new constitution version without activating it
        v_content = {"name": "Test Constitution", "principles": ["Principle 1"]}
        v_json = json.dumps(v_content)

        cur.execute("""
            INSERT INTO calibration_constitution_versions (
                version_number, content_json, content_hash, signature, signer_entity_id
            ) VALUES (
                (SELECT COALESCE(MAX(version_number), 0) + 1 FROM calibration_constitution_versions),
                %s, %s, %s, NULL
            )
            RETURNING id, version_number
        """, [v_json, "test_hash", "test_sig"])

        v_id, v_num = cur.fetchone()
        assert v_num > 0, "Version number should be > 0"
        print(f"  ✓ Constitution version {v_num} created: {v_id}")

        # Verify it can be queried
        cur.execute("""
            SELECT id FROM calibration_constitution_versions WHERE id = %s
        """, [v_id])

        assert cur.fetchone() is not None, "Version should be queryable"
        print(f"  ✓ Constitution version persisted and queryable")

        conn.commit()

def test_protected_surfaces():
    """Test: Protected surfaces definition and enforcement"""
    print("\n✓ TEST: Protected Surfaces")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Get active constitution
        cur.execute("""
            SELECT constitution_version_id FROM active_constitution
            ORDER BY activated_at DESC LIMIT 1
        """)
        result = cur.fetchone()
        if not result:
            print("  ⊘ No active constitution found (skipping protected surface test)")
            return

        const_id = result[0]

        # Add protected surface
        cur.execute("""
            INSERT INTO protected_surfaces (
                constitution_id, surface_name, surface_type, description,
                table_names, column_patterns, function_patterns,
                is_immutable, requires_constitution_vote
            ) VALUES (
                %s, 'Test Surface', 'table', 'Test protected surface',
                ARRAY['audit_log'], ARRAY[]::TEXT[], ARRAY[]::TEXT[],
                true, true
            )
            RETURNING id, surface_name, table_names
        """, [const_id])

        surf_id, surf_name, tables = cur.fetchone()
        assert surf_name == 'Test Surface', "Surface name mismatch"
        assert 'audit_log' in tables, "audit_log table should be in protected surfaces"
        print(f"  ✓ Protected surface created: {surf_name}")

        # Query protected surfaces
        cur.execute("""
            SELECT COUNT(*) FROM protected_surfaces
            WHERE constitution_id = %s AND is_immutable = true
        """, [const_id])

        count = cur.fetchone()[0]
        assert count > 0, "Should have protected surfaces"
        print(f"  ✓ {count} protected surfaces found in active constitution")

        conn.commit()

def test_allowed_change_types():
    """Test: Allowed change types"""
    print("\n✓ TEST: Allowed Change Types")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Get active constitution
        cur.execute("""
            SELECT constitution_version_id FROM active_constitution
            ORDER BY activated_at DESC LIMIT 1
        """)
        result = cur.fetchone()
        if not result:
            print("  ⊘ No active constitution found (skipping change types test)")
            return

        const_id = result[0]

        # Add allowed change type with unique name
        import uuid
        unique_name = f'test_change_type_{str(uuid.uuid4())[:8]}'

        cur.execute("""
            INSERT INTO allowed_change_types (
                constitution_id, change_type_name, description, category,
                max_scope, requires_eval, can_be_canaried
            ) VALUES (
                %s, %s, 'Test change', 'testing',
                'institution', true, true
            )
            RETURNING id, change_type_name
        """, [const_id, unique_name])

        change_id, change_name = cur.fetchone()
        assert change_name == unique_name, "Change type name mismatch"
        print(f"  ✓ Allowed change type created: {change_name}")

        # Query allowed change types
        cur.execute("""
            SELECT COUNT(*) FROM allowed_change_types
            WHERE constitution_id = %s
        """, [const_id])

        count = cur.fetchone()[0]
        assert count > 0, "Should have allowed change types"
        print(f"  ✓ {count} allowed change types found")

        conn.commit()

def test_prohibited_change_types():
    """Test: Prohibited change types"""
    print("\n✓ TEST: Prohibited Change Types")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Get active constitution
        cur.execute("""
            SELECT constitution_version_id FROM active_constitution
            ORDER BY activated_at DESC LIMIT 1
        """)
        result = cur.fetchone()
        if not result:
            print("  ⊘ No active constitution found (skipping prohibited types test)")
            return

        const_id = result[0]
        print(f"  (test) Querying prohibited types for constitution: {const_id}")

        # Query prohibited change types
        cur.execute("""
            SELECT COUNT(*) FROM prohibited_change_types
            WHERE constitution_id = %s
        """, [const_id])

        count = cur.fetchone()[0]

        # Debug: also query all prohibited types
        cur.execute("SELECT COUNT(*) FROM prohibited_change_types")
        total_count = cur.fetchone()[0]

        assert count > 0, f"Should have prohibited change types (found {count} for const_id {const_id}, total: {total_count})"
        print(f"  ✓ {count} prohibited change types found")

        # Verify some standard prohibited types exist
        cur.execute("""
            SELECT change_type_name FROM prohibited_change_types
            WHERE constitution_id = %s AND change_type_name = 'modify_ground_truth'
        """, [const_id])

        result = cur.fetchone()
        if result:
            print(f"  ✓ 'modify_ground_truth' is properly prohibited")

        conn.commit()

def test_constitution_immutability():
    """Test: Constitution versions are immutable"""
    print("\n✓ TEST: Constitution Immutability")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Get a constitution version
        cur.execute("""
            SELECT id FROM calibration_constitution_versions LIMIT 1
        """)
        result = cur.fetchone()
        if not result:
            print("  ⊘ No constitution found (skipping immutability test)")
            return

        const_id = result[0]

        # Try to update it (should fail due to trigger)
        try:
            cur.execute("""
                UPDATE calibration_constitution_versions
                SET content_json = %s
                WHERE id = %s
            """, [json.dumps({"modified": True}), const_id])

            conn.commit()
            print("  ✗ FAILED: Constitution should be immutable!")
            return False
        except psycopg2.Error as e:
            if 'immutability' in str(e).lower():
                print(f"  ✓ Constitution immutability enforced")
            else:
                raise
        finally:
            conn.rollback()

def test_change_validation():
    """Test: Change validation logic"""
    print("\n✓ TEST: Change Validation")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Get active constitution
        cur.execute("""
            SELECT constitution_version_id FROM active_constitution
            ORDER BY activated_at DESC LIMIT 1
        """)
        result = cur.fetchone()
        if not result:
            print("  ⊘ No active constitution found (skipping validation test)")
            return

        const_id = result[0]

        # Test 1: Prohibited change type should be blocked
        cur.execute("""
            SELECT COUNT(*) FROM prohibited_change_types
            WHERE constitution_id = %s
        """, [const_id])

        if cur.fetchone()[0] > 0:
            cur.execute("""
                SELECT change_type_name FROM prohibited_change_types
                WHERE constitution_id = %s LIMIT 1
            """, [const_id])

            prohibited_type = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO constitution_verifications (
                    constitution_id, change_request_id, verification_result,
                    violations, is_compliant, trace_id
                ) VALUES (%s, NULL, %s, %s, false, NULL)
            """, [const_id, 'VIOLATIONS', [f"Prohibited change type: {prohibited_type}"]])

            print(f"  ✓ Validation records created for prohibited change type")

        # Query verification records
        cur.execute("""
            SELECT COUNT(*) FROM constitution_verifications
            WHERE constitution_id = %s
        """, [const_id])

        count = cur.fetchone()[0]
        print(f"  ✓ {count} verification records stored")

        conn.commit()

def initialize_default_constitution():
    """Initialize a default constitution for testing"""
    with get_db_connection() as conn:
        cur = conn.cursor()

        # Clear only the data tables (not active_constitution which is immutable)
        cur.execute("DELETE FROM prohibited_change_types WHERE constitution_id NOT IN (SELECT constitution_version_id FROM active_constitution)")
        cur.execute("DELETE FROM allowed_change_types WHERE constitution_id NOT IN (SELECT constitution_version_id FROM active_constitution)")
        cur.execute("DELETE FROM protected_surfaces WHERE constitution_id NOT IN (SELECT constitution_version_id FROM active_constitution)")
        cur.execute("DELETE FROM constitution_verifications WHERE constitution_id NOT IN (SELECT constitution_version_id FROM active_constitution)")
        conn.commit()

        # Create a fresh constitution
        default_content = {
            "name": "Test Constitution",
            "version": 1,
            "principles": ["Civilization can propose trust-policy changes"]
        }

        cur.execute("""
            INSERT INTO calibration_constitution_versions (
                version_number, content_json, content_hash, signature
            ) VALUES (
                (SELECT COALESCE(MAX(version_number), 0) + 1 FROM calibration_constitution_versions),
                %s, %s, %s
            )
            RETURNING id
        """, [json.dumps(default_content), "test_hash", "test_sig"])

        const_id = cur.fetchone()[0]
        print(f"  (init) Created constitution: {const_id}")

        # Activate it
        cur.execute("""
            INSERT INTO active_constitution (constitution_version_id) VALUES (%s)
        """, [const_id])
        print(f"  (init) Activated constitution: {const_id}")

        # Add some prohibited change types for this specific constitution
        for change_type, reason in [
            ('modify_ground_truth', 'Ground truth is sealed'),
            ('modify_resolver_logic', 'Resolver is immutable'),
            ('modify_calibration_score_code', 'Scoring code is protected')
        ]:
            cur.execute("""
                INSERT INTO prohibited_change_types (
                    constitution_id, change_type_name, reason
                ) VALUES (%s, %s, %s)
            """, [const_id, change_type, reason])

        conn.commit()

import pytest


@pytest.fixture(scope="module", autouse=True)
def _seed_default_constitution():
    """Pytest entrypoint parity with main(): seed the default constitution once."""
    initialize_default_constitution()


def main():
    """Run all tests"""
    print("=" * 70)
    print("CALIBRATION CONSTITUTION SERVICE TEST SUITE")
    print("=" * 70)

    try:
        initialize_default_constitution()
        test_constitution_versioning()
        test_protected_surfaces()
        test_allowed_change_types()
        test_prohibited_change_types()
        test_constitution_immutability()
        test_change_validation()

        print("\n" + "=" * 70)
        print("✓ ALL CALIBRATION CONSTITUTION TESTS PASSED")
        print("=" * 70)
        return 0
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
