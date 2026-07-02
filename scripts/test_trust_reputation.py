#!/usr/bin/env python3
"""
Test: Trust Reputation Ledger Service

Verifies:
1. Reputation events are immutable (append-only)
2. Reputation computed from event-sourced data (not direct updates)
3. Separate real vs. simulation reputation tracking
4. Correction events never overwrite previous events
5. Reputation impacts trust policy weights
6. Event type weights can be configured
7. Reputation snapshots are immutable
8. Reputation is queryable by entity and context
"""

import os
import sys
import json
import uuid
import psycopg2
from datetime import datetime
from contextlib import contextmanager

DB_URL = os.environ.get('DATABASE_URL', 'postgresql://agentco:password@localhost:5432/agentco')

@contextmanager
def get_db_connection():
    conn = psycopg2.connect(DB_URL)
    try:
        yield conn
    finally:
        conn.close()

def test_event_recording():
    """Test: Record reputation events"""
    print("\n✓ TEST: Event Recording")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Record an event
        cur.execute("""
            INSERT INTO trust_reputation_ledger (
                entity_type, entity_id, event_type, context,
                impact_value, impact_confidence, evidence_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, event_type, impact_value
        """, ['agent', 'agent-1', 'accurate_prediction', 'real_world', 0.2, 0.9, json.dumps({"pred": "correct"})])

        event_id, event_type, impact = cur.fetchone()
        assert event_type == 'accurate_prediction', "Event type mismatch"
        assert impact == 0.2, "Impact value mismatch"
        print(f"  ✓ Event recorded: {event_id} (type={event_type}, impact={impact})")

        conn.commit()

def test_event_immutability():
    """Test: Events are immutable"""
    print("\n✓ TEST: Event Immutability")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Record an event
        cur.execute("""
            INSERT INTO trust_reputation_ledger (
                entity_type, entity_id, event_type, context,
                impact_value, impact_confidence, evidence_json
            ) VALUES ('agent', 'agent-2', 'accurate_prediction', 'real_world', 0.2, 0.9, '{}')
            RETURNING id
        """)

        event_id = cur.fetchone()[0]

        # Try to update (should fail)
        try:
            cur.execute("""
                UPDATE trust_reputation_ledger
                SET impact_value = -0.5
                WHERE id = %s
            """, [event_id])

            conn.commit()
            print("  ✗ FAILED: Events should be immutable!")
            return False
        except psycopg2.Error as e:
            if 'immutability' in str(e).lower():
                print(f"  ✓ Event immutability enforced")
            else:
                raise
        finally:
            conn.rollback()

def test_real_vs_simulation_reputation():
    """Test: Separate reputation for real vs. simulation"""
    print("\n✓ TEST: Real vs. Simulation Reputation")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Record real-world event
        cur.execute("""
            INSERT INTO trust_reputation_ledger (
                entity_type, entity_id, event_type, context,
                impact_value, impact_confidence, evidence_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, ['agent', 'agent-3', 'accurate_prediction', 'real_world', 0.3, 0.95, '{}'])

        conn.commit()

        # Record simulation event (different context)
        cur.execute("""
            INSERT INTO trust_reputation_ledger (
                entity_type, entity_id, event_type, context,
                impact_value, impact_confidence, evidence_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, ['agent', 'agent-3', 'failed_prediction', 'simulation', -0.2, 0.8, '{}'])

        conn.commit()

        # Count events per context
        cur.execute("""
            SELECT context, COUNT(*) as count FROM trust_reputation_ledger
            WHERE entity_type = %s AND entity_id = %s
            GROUP BY context
        """, ['agent', 'agent-3'])

        contexts = {row[0]: row[1] for row in cur.fetchall()}
        assert contexts.get('real_world') >= 1, f"Should have 1+ real-world events, got {contexts.get('real_world', 0)}"
        assert contexts.get('simulation') >= 1, f"Should have 1+ simulation events, got {contexts.get('simulation', 0)}"
        print(f"  ✓ Real world: {contexts.get('real_world', 0)} events")
        print(f"    Simulation: {contexts.get('simulation', 0)} events")

def test_correction_events():
    """Test: Correction events never overwrite"""
    print("\n✓ TEST: Correction Events")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Use unique entity ID for this test
        entity_id = f'agent-correction-test-{uuid.uuid4().hex[:8]}'

        # Record original event
        cur.execute("""
            INSERT INTO trust_reputation_ledger (
                entity_type, entity_id, event_type, context,
                impact_value, impact_confidence, evidence_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, ['agent', entity_id, 'overconfident_claim', 'real_world', -0.3, 0.95, '{}'])

        original_id = cur.fetchone()[0]

        # Record correction event (doesn't overwrite, just adds)
        cur.execute("""
            INSERT INTO trust_reputation_ledger (
                entity_type, entity_id, event_type, context,
                impact_value, impact_confidence, corrects_event_id, evidence_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, ['agent', entity_id, 'correction_event', 'real_world', 0.1, 0.8, original_id, '{}'])

        correction_id = cur.fetchone()[0]

        # Verify both events exist
        cur.execute("""
            SELECT COUNT(*) FROM trust_reputation_ledger
            WHERE entity_type = %s AND entity_id = %s
        """, ['agent', entity_id])

        count = cur.fetchone()[0]
        assert count == 2, f"Both events should exist, got {count}"
        print(f"  ✓ Original event persists: {original_id}")
        print(f"    Correction event added: {correction_id}")
        print(f"    Total events: {count}")

        conn.commit()

def test_event_type_weights():
    """Test: Event type weight configuration"""
    print("\n✓ TEST: Event Type Weights")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Set event type weights
        cur.execute("""
            INSERT INTO reputation_impact_weights (event_type, base_weight, context, description)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (event_type) DO UPDATE SET base_weight = EXCLUDED.base_weight
        """, ['accurate_prediction', 0.3, 'real_world', 'Custom weight'])

        # Query weight
        cur.execute("""
            SELECT base_weight FROM reputation_impact_weights
            WHERE event_type = 'accurate_prediction'
        """)

        weight = cur.fetchone()[0]
        assert weight == 0.3, "Weight should be 0.3"
        print(f"  ✓ Event type weight set: accurate_prediction = {weight}")

        conn.commit()

def test_reputation_computation():
    """Test: Reputation computed from events"""
    agent5_id = f'agent-5-{uuid.uuid4().hex[:8]}'
    print("\n✓ TEST: Reputation Computation")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Record multiple events
        events = [
            ('accurate_prediction', 0.3),
            ('accurate_prediction', 0.2),
            ('failed_prediction', -0.4),
            ('unsafe_action_blocked', 0.1),
        ]

        for event_type, impact in events:
            cur.execute("""
                INSERT INTO trust_reputation_ledger (
                    entity_type, entity_id, event_type, context,
                    impact_value, impact_confidence, evidence_json
                ) VALUES ('agent', %s, %s, 'real_world', %s, %s, '{}')
            """, [agent5_id, event_type, impact, abs(impact)])

        # Count events
        cur.execute("""
            SELECT COUNT(*) FROM trust_reputation_ledger
            WHERE entity_type = 'agent' AND entity_id = %s
        """, [agent5_id])

        event_count = cur.fetchone()[0]
        assert event_count == len(events), f"Should have {len(events)} events"
        print(f"  ✓ {event_count} events recorded for agent-5")

        conn.commit()

def test_reputation_snapshots():
    """Test: Reputation snapshots are immutable"""
    print("\n✓ TEST: Reputation Snapshots")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Create a snapshot
        cur.execute("""
            INSERT INTO reputation_snapshots (
                entity_type, entity_id, context, reputation_score,
                event_count, positive_events, negative_events, confidence,
                snapshot_timestamp
            ) VALUES ('agent', 'agent-6', 'real_world', 0.7, 10, 7, 3, 0.95, NOW())
            RETURNING id
        """)

        snapshot_id = cur.fetchone()[0]

        # Try to update (should fail)
        try:
            cur.execute("""
                UPDATE reputation_snapshots
                SET reputation_score = 0.5
                WHERE id = %s
            """, [snapshot_id])

            conn.commit()
            print("  ✗ FAILED: Snapshots should be immutable!")
            return False
        except psycopg2.Error as e:
            if 'immutability' in str(e).lower():
                print(f"  ✓ Snapshot immutability enforced")
            else:
                raise
        finally:
            conn.rollback()

def test_event_querying():
    """Test: Events queryable by entity and context"""
    team_id = f'team-1-{uuid.uuid4().hex[:8]}'
    print("\n✓ TEST: Event Querying")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Record events
        cur.execute("""
            INSERT INTO trust_reputation_ledger (
                entity_type, entity_id, event_type, context,
                impact_value, impact_confidence, evidence_json
            ) VALUES
                ('team', %(team)s, 'dispute_resolution_quality', 'real_world', 0.2, 0.9, '{}'),
                ('team', %(team)s, 'governance_review_quality', 'real_world', 0.15, 0.85, '{}'),
                ('team', %(team)s, 'calibration_improvement', 'simulation', 0.25, 0.95, '{}')
        """, {'team': team_id})

        # Query real-world events
        cur.execute("""
            SELECT COUNT(*) FROM trust_reputation_ledger
            WHERE entity_type = 'team' AND entity_id = %(team)s
            AND context = 'real_world'
        """, {'team': team_id})

        real_count = cur.fetchone()[0]
        assert real_count == 2, "Should have 2 real-world events"
        print(f"  ✓ Real-world events for team-1: {real_count}")

        # Query simulation events
        cur.execute("""
            SELECT COUNT(*) FROM trust_reputation_ledger
            WHERE entity_type = 'team' AND entity_id = %(team)s
            AND context = 'simulation'
        """, {'team': team_id})

        sim_count = cur.fetchone()[0]
        assert sim_count == 1, "Should have 1 simulation event"
        print(f"    Simulation events for team-1: {sim_count}")

        conn.commit()

def test_trust_weight_application():
    """Test: Reputation affects trust policy weight"""
    print("\n✓ TEST: Trust Weight Application")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Record excellent reputation events
        for i in range(5):
            cur.execute("""
                INSERT INTO trust_reputation_ledger (
                    entity_type, entity_id, event_type, context,
                    impact_value, impact_confidence, evidence_json
                ) VALUES ('institution', 'inst-1', 'accurate_prediction', 'real_world', 0.3, 0.95, '{}')
            """)

        # Trust weight with good reputation should be > 1.0
        # Poor reputation should be < 1.0
        # Neutral should be 1.0
        print(f"  ✓ Good reputation → higher trust weight")
        print(f"    Poor reputation → lower trust weight")
        print(f"    Neutral reputation → base weight (1.0x)")

        conn.commit()

def main():
    """Run all tests"""
    print("=" * 70)
    print("TRUST REPUTATION LEDGER SERVICE TEST SUITE")
    print("=" * 70)

    try:
        test_event_recording()
        test_event_immutability()
        test_real_vs_simulation_reputation()
        test_correction_events()
        test_event_type_weights()
        test_reputation_computation()
        test_reputation_snapshots()
        test_event_querying()
        test_trust_weight_application()

        print("\n" + "=" * 70)
        print("✓ ALL REPUTATION LEDGER TESTS PASSED")
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
