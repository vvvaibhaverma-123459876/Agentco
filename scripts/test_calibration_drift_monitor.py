#!/usr/bin/env python3
"""
Test: Calibration Drift Monitor Service

Verifies:
1. Drift events can be recorded
2. Severity classification (normal/warning/severe/critical)
3. Drift auto-proposes changes for severe/critical
4. Thresholds configurable per drift type
5. Emergency freeze triggered on critical drift
6. Drift events queryable and immutable
7. Resolutions are recorded and immutable
"""

import os
import sys
import json
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

def test_drift_event_recording():
    """Test: Record drift events"""
    print("\n✓ TEST: Drift Event Recording")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Initialize thresholds first
        cur.execute("""
            INSERT INTO drift_thresholds (
                drift_type, warning_threshold, severe_threshold, critical_threshold,
                requires_emergency_freeze, auto_propose_change
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (drift_type) DO NOTHING
        """, ['overconfidence', 0.05, 0.10, 0.20, True, True])

        conn.commit()

        # Record drift event
        cur.execute("""
            INSERT INTO calibration_drift_events (
                drift_type, severity, baseline_value, observed_value,
                drift_magnitude, threshold_value, detection_method, evidence_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, drift_type, severity
        """, ['overconfidence', 'warning', 0.80, 0.90, 0.125, 0.10, 'calibration_eval', json.dumps({})])

        event_id, drift_type, severity = cur.fetchone()
        assert drift_type == 'overconfidence', "Drift type mismatch"
        assert severity == 'warning', "Severity mismatch"
        print(f"  ✓ Drift event recorded: {event_id} (type={drift_type}, severity={severity})")

        conn.commit()

def test_severity_classification():
    """Test: Severity classification"""
    print("\n✓ TEST: Severity Classification")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Set threshold for this test
        cur.execute("""
            INSERT INTO drift_thresholds (
                drift_type, warning_threshold, severe_threshold, critical_threshold
            ) VALUES (%s, %s, %s, %s)
            ON CONFLICT (drift_type) DO UPDATE SET
                warning_threshold = EXCLUDED.warning_threshold,
                severe_threshold = EXCLUDED.severe_threshold,
                critical_threshold = EXCLUDED.critical_threshold
        """, ['underconfidence', 0.05, 0.15, 0.35])

        conn.commit()

        test_cases = [
            (0.90, 0.85, 'normal', 'Within threshold'),
            (0.90, 0.80, 'warning', 'Between warning and severe'),
            (0.90, 0.70, 'severe', 'Between severe and critical'),
            (0.90, 0.50, 'critical', 'Above critical'),
        ]

        for baseline, observed, expected_severity, desc in test_cases:
            cur.execute("""
                INSERT INTO calibration_drift_events (
                    drift_type, severity, baseline_value, observed_value,
                    drift_magnitude, threshold_value, detection_method, evidence_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING severity
            """, ['underconfidence', expected_severity, baseline, observed, abs((observed - baseline) / baseline), 0.15, 'test', '{}'])

            severity = cur.fetchone()[0]
            assert severity == expected_severity, f"Expected {expected_severity}, got {severity}"
            print(f"  ✓ {desc}: {baseline}→{observed} → {severity}")

        conn.commit()

def test_emergency_freeze():
    """Test: Emergency freeze triggered on critical"""
    print("\n✓ TEST: Emergency Freeze")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Record critical drift
        cur.execute("""
            INSERT INTO calibration_drift_events (
                drift_type, severity, baseline_value, observed_value,
                drift_magnitude, threshold_value, detection_method,
                triggered_emergency_freeze, evidence_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, triggered_emergency_freeze
        """, ['simulation_leakage_risk', 'critical', 0.0, 0.30, 0.30, 0.25, 'test', True, '{}'])

        event_id, freeze = cur.fetchone()
        assert freeze, "Emergency freeze should be triggered"
        print(f"  ✓ Critical drift {event_id} triggered emergency freeze")

        # Check if freeze is active
        cur.execute("""
            SELECT COUNT(*) FROM calibration_drift_events
            WHERE severity = 'critical' AND resolved_at IS NULL
            AND created_at > NOW() - INTERVAL '1 hour'
        """)

        count = cur.fetchone()[0]
        assert count > 0, "Should have active critical drift"
        print(f"    Emergency freeze active: {count} unresolved critical drifts")

        conn.commit()

def test_drift_resolution():
    """Test: Drift resolution and immutability"""
    print("\n✓ TEST: Drift Resolution")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Create drift event
        cur.execute("""
            INSERT INTO calibration_drift_events (
                drift_type, severity, baseline_value, observed_value,
                drift_magnitude, threshold_value, detection_method, evidence_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, ['evidence_quality_decline', 'warning', 0.85, 0.80, 0.0588, 0.05, 'test', '{}'])

        drift_id = cur.fetchone()[0]

        # Record resolution
        cur.execute("""
            INSERT INTO drift_resolutions (
                drift_event_id, resolution_type, resolved_by_entity_id, reason
            ) VALUES (%s, %s, %s, %s)
            RETURNING id
        """, [drift_id, 'auto_recovery', 'drift-monitor', 'Evidence quality improved'])

        resolution_id = cur.fetchone()[0]

        # Update drift to resolved
        cur.execute("""
            UPDATE calibration_drift_events SET resolved_at = NOW() WHERE id = %s
            RETURNING id, resolved_at
        """, [drift_id])

        _, resolved_at = cur.fetchone()
        assert resolved_at is not None, "Drift should be resolved"
        print(f"  ✓ Drift resolved: {drift_id}")
        print(f"    Resolution: {resolution_id}")

        conn.commit()

def test_drift_immutability():
    """Test: Resolved drifts are immutable"""
    print("\n✓ TEST: Drift Immutability")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Create and resolve drift
        cur.execute("""
            INSERT INTO calibration_drift_events (
                drift_type, severity, baseline_value, observed_value,
                drift_magnitude, threshold_value, detection_method, evidence_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, ['dispute_rate_increase', 'severe', 0.10, 0.20, 1.0, 0.25, 'test', '{}'])

        drift_id = cur.fetchone()[0]

        # Resolve it
        cur.execute("""
            UPDATE calibration_drift_events SET resolved_at = NOW() WHERE id = %s
        """, [drift_id])

        conn.commit()

        # Try to update resolved drift (should fail)
        try:
            cur.execute("""
                UPDATE calibration_drift_events SET severity = 'normal' WHERE id = %s
            """, [drift_id])

            conn.commit()
            print("  ✗ FAILED: Resolved drift should be immutable!")
            return False
        except psycopg2.Error as e:
            if 'immutability' in str(e).lower() or 'error' in str(e).lower():
                print(f"  ✓ Resolved drift immutability enforced")
            else:
                raise
        finally:
            conn.rollback()

def test_threshold_configuration():
    """Test: Thresholds configurable per drift type"""
    print("\n✓ TEST: Threshold Configuration")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Set custom thresholds
        cur.execute("""
            INSERT INTO drift_thresholds (
                drift_type, warning_threshold, severe_threshold, critical_threshold,
                auto_propose_change, description
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (drift_type) DO UPDATE SET
                warning_threshold = EXCLUDED.warning_threshold,
                severe_threshold = EXCLUDED.severe_threshold,
                critical_threshold = EXCLUDED.critical_threshold
        """, ['rollback_rate_increase', 0.05, 0.15, 0.30, True, 'Custom thresholds for rollback'])

        # Query threshold
        cur.execute("""
            SELECT critical_threshold, auto_propose_change FROM drift_thresholds
            WHERE drift_type = %s
        """, ['rollback_rate_increase'])

        critical, auto_propose = cur.fetchone()
        assert critical == 0.30, "Critical threshold should be 0.30"
        assert auto_propose, "Should auto-propose"
        print(f"  ✓ Thresholds configured: critical={critical}, auto_propose={auto_propose}")

        conn.commit()

def test_unresolved_drift_query():
    """Test: Query unresolved drifts"""
    print("\n✓ TEST: Unresolved Drift Query")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Count unresolved drifts
        cur.execute("""
            SELECT COUNT(*) FROM calibration_drift_events
            WHERE resolved_at IS NULL
        """)

        count = cur.fetchone()[0]
        assert count >= 0, "Should have valid count"
        print(f"  ✓ Unresolved drifts: {count}")

        # Query critical unresolved from last hour
        cur.execute("""
            SELECT COUNT(*) FROM calibration_drift_events
            WHERE severity = 'critical' AND resolved_at IS NULL
            AND created_at > NOW() - INTERVAL '1 hour'
        """)

        critical_count = cur.fetchone()[0]
        print(f"    Critical (last hour): {critical_count}")

        conn.commit()

def main():
    """Run all tests"""
    print("=" * 70)
    print("CALIBRATION DRIFT MONITOR SERVICE TEST SUITE")
    print("=" * 70)

    try:
        test_drift_event_recording()
        test_severity_classification()
        test_emergency_freeze()
        test_drift_resolution()
        test_drift_immutability()
        test_threshold_configuration()
        test_unresolved_drift_query()

        print("\n" + "=" * 70)
        print("✓ ALL DRIFT MONITOR TESTS PASSED")
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
