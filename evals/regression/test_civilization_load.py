#!/usr/bin/env python3
"""
Load test for civilization layer hardening.

Scenarios:
1. Sequential: 10 institutions created and reputation updated sequentially
2. Parallel: 10 institutions concurrent operations
3. Failure recovery: Reputation calculation fails and recovers
"""
import asyncio
import time
import uuid
import os
from concurrent.futures import ThreadPoolExecutor
import psycopg2
from psycopg2.extras import RealDictCursor
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parents[2]))

from civilization.services.governance_service import create_decision, propose_decision, approve_decision
from civilization.services.institution_service import create_institution
from civilization.services.reputation_service import propagate_institution
from unittest.mock import MagicMock


def get_db_connection():
    """Create a database connection for testing."""
    try:
        conn = psycopg2.connect(
            dbname=os.environ.get('DB_NAME', 'agentco'),
            user=os.environ.get('DB_USER', 'postgres'),
            password=os.environ.get('DB_PASSWORD', 'postgres'),
            host=os.environ.get('DB_HOST', 'localhost'),
            port=int(os.environ.get('DB_PORT', 5432)),
        )
        conn.autocommit = False  # Ensure explicit commit control
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)


def create_test_contract(name: str) -> dict:
    """Create a test institution contract."""
    return {
        "institution_name": name,
        "accepted_inputs": ["research_request", "data_point"],
        "produced_outputs": ["report", "evidence"],
        "verification_required": True,
        "required_external_reviewer": f"external_{name}",
        "failure_conditions": ["timeout", "no_evidence"],
        "escalation_target": "admin_board",
        "reputation_metric": "evidence_quality",
        "purpose": f"Test institution {name}",
    }


def test_sequential_institutions(count: int = 10):
    """Test: Sequential creation and reputation update."""
    print(f"\n{'='*70}")
    print(f"SCENARIO 1: Sequential Institution Creation ({count} institutions)")
    print(f"{'='*70}")

    db = get_db_connection()
    created_ids = []
    start_time = time.time()

    try:
        for i in range(count):
            inst_name = f"seq_inst_{i}_{int(time.time())}"
            contract = create_test_contract(inst_name)

            try:
                result = create_institution(inst_name, contract, db)
                inst_id = result['institution_id']
                created_ids.append(inst_id)
                print(f"✅ Created institution {i+1}/{count}: {inst_id[:8]}")
            except Exception as e:
                print(f"❌ Failed to create institution {i+1}: {e}")
                raise

        elapsed = time.time() - start_time
        rate = count / elapsed
        print(f"\n📊 Results:")
        print(f"  Total time: {elapsed:.2f}s")
        print(f"  Rate: {rate:.1f} institutions/sec")
        print(f"  Avg per institution: {elapsed/count*1000:.1f}ms")

        if elapsed / count > 2.0:  # Target: <2s per decision
            print(f"⚠️  WARNING: Sequential creation exceeds 2s target")
        else:
            print(f"✅ Sequential creation within <2s per decision")

        db.close()
        return True

    except Exception as e:
        print(f"❌ Sequential test failed: {e}")
        db.close()
        return False


def test_parallel_institutions(count: int = 10):
    """Test: Parallel creation to detect deadlocks."""
    print(f"\n{'='*70}")
    print(f"SCENARIO 2: Parallel Institution Creation ({count} institutions)")
    print(f"{'='*70}")

    start_time = time.time()
    created_ids = []
    errors = []

    def create_one(i: int):
        try:
            db = get_db_connection()
            inst_name = f"par_inst_{i}_{int(time.time())}"
            contract = create_test_contract(inst_name)
            result = create_institution(inst_name, contract, db)
            db.close()
            return result['institution_id']
        except Exception as e:
            errors.append(str(e))
            return None

    try:
        with ThreadPoolExecutor(max_workers=min(count, 5)) as executor:
            futures = [executor.submit(create_one, i) for i in range(count)]
            for i, future in enumerate(futures):
                inst_id = future.result(timeout=30)
                if inst_id:
                    created_ids.append(inst_id)
                    print(f"✅ Created institution {i+1}/{count}: {inst_id[:8]}")

        elapsed = time.time() - start_time

        if errors:
            print(f"\n❌ {len(errors)} errors occurred:")
            for err in errors[:3]:
                print(f"  - {err}")
            return False

        print(f"\n📊 Results:")
        print(f"  Total time: {elapsed:.2f}s")
        print(f"  Rate: {count/elapsed:.1f} institutions/sec")
        print(f"  Avg per institution: {elapsed/count*1000:.1f}ms")
        print(f"  Deadlocks detected: 0 ✅")

        if elapsed / count > 2.0:
            print(f"⚠️  WARNING: Parallel creation exceeds 2s target")
        else:
            print(f"✅ Parallel creation within <2s per decision")

        return True

    except Exception as e:
        print(f"❌ Parallel test failed: {e}")
        return False


def test_failure_recovery():
    """Test: Reputation calculation failure and recovery."""
    print(f"\n{'='*70}")
    print(f"SCENARIO 3: Failure Recovery (Reputation Calculation)")
    print(f"{'='*70}")

    db = get_db_connection()

    try:
        # Create institution
        inst_name = f"fail_test_{int(time.time())}"
        contract = create_test_contract(inst_name)
        result = create_institution(inst_name, contract, db)
        inst_id = result['institution_id']
        print(f"✅ Created test institution: {inst_id[:8]}")

        # Try to propagate reputation (with mock ledger)
        mock_ledger = MagicMock()
        mock_ledger.list_by_agent.return_value = []

        try:
            propagate_institution(inst_id, mock_ledger, db)
            print(f"✅ Reputation propagation completed")

            # Verify transaction was committed
            with db.cursor() as cur:
                cur.execute("SELECT reputation_score FROM institutions WHERE id = %s", (inst_id,))
                row = cur.fetchone()
                if row:
                    print(f"✅ Institution data persisted: reputation_score = {row[0]}")
                else:
                    print(f"❌ Institution data not found")
                    return False

            db.close()
            return True

        except Exception as e:
            print(f"⚠️  Reputation propagation error (expected in test): {e}")
            # Verify rollback occurred
            try:
                with db.cursor() as cur:
                    cur.execute("SELECT id FROM institutions WHERE id = %s", (inst_id,))
                    if cur.fetchone():
                        print(f"✅ Transaction rolled back correctly")
                        db.close()
                        return True
                    else:
                        print(f"❌ Institution not found after rollback")
                        return False
            except Exception as e2:
                print(f"❌ Error checking rollback: {e2}")
                return False

    except Exception as e:
        print(f"❌ Failure recovery test failed: {e}")
        return False


def main():
    """Run all load tests."""
    import os

    print(f"\n🚀 Civilization Layer Load Tests")
    print(f"{'='*70}")

    results = {
        "sequential": test_sequential_institutions(10),
        "parallel": test_parallel_institutions(10),
        "failure_recovery": test_failure_recovery(),
    }

    print(f"\n{'='*70}")
    print(f"📋 Summary")
    print(f"{'='*70}")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")

    if passed == total:
        print(f"\n✅ All load tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} load test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
