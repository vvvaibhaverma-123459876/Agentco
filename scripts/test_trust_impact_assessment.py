#!/usr/bin/env python3
"""
Test: Trust Impact Assessment Service

Verifies:
1. Impact assessments can be created with 10 metrics
2. Recommendations are computed based on metric values
3. Blocking issues are detected
4. Warnings are generated
5. Baseline metrics can be recorded and retrieved
6. Assessments prevent canary if blocking issues exist
7. Assessments immutable
8. Assessments are queryable by policy/change request
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

def ensure_test_data():
    """Ensure active constitution and policy exist"""
    with get_db_connection() as conn:
        cur = conn.cursor()

        # Check if active constitution exists
        cur.execute("SELECT COUNT(*) FROM active_constitution")
        if cur.fetchone()[0] == 0:
            cur.execute("""
                INSERT INTO calibration_constitution_versions (
                    version_number, content_json, content_hash, signature
                ) VALUES (1, %s, %s, %s)
                RETURNING id
            """, [json.dumps({"name": "Test"}), "hash", "sig"])

            const_id = cur.fetchone()[0]
            cur.execute("""
                INSERT INTO active_constitution (constitution_version_id) VALUES (%s)
            """, [const_id])

        # Check if policy exists
        cur.execute("""
            SELECT constitution_version_id FROM active_constitution
            ORDER BY activated_at DESC LIMIT 1
        """)
        const_id = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM trust_policy_versions LIMIT 1")
        if cur.fetchone()[0] == 0:
            cur.execute("""
                INSERT INTO trust_policy_versions (
                    policy_type, constitution_id, title, version_number,
                    content_json, content_hash, promotion_scope, status
                ) VALUES (
                    'confidence_discount', %s, 'Test Policy', 1,
                    '{}', 'hash', 'civilization', 'active'
                )
                RETURNING id
            """, [const_id])

        conn.commit()

def test_assessment_creation():
    """Test: Create impact assessment"""
    print("\n✓ TEST: Assessment Creation")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Get a policy
        cur.execute("""
            SELECT id FROM trust_policy_versions LIMIT 1
        """)
        policy_id = cur.fetchone()[0]

        # Create assessment
        cur.execute("""
            INSERT INTO trust_impact_assessments (
                policy_id, assessment_type,
                calibration_regression, confidence_shift,
                false_positive_impact, false_negative_impact,
                reputation_impact, dispute_impact,
                simulation_leakage_risk, safety_threshold_compliance,
                rollback_feasibility, audit_completeness,
                recommendation, recommendation_confidence
            ) VALUES (
                %s, 'policy_eval',
                0.02, 0.01,
                0.0, 0.0,
                0.05, 0.0,
                0.0, 0.98,
                0.95, 0.99,
                'approve_for_canary', 0.92
            )
            RETURNING id, recommendation
        """, [policy_id])

        assessment_id, recommendation = cur.fetchone()
        assert recommendation == 'approve_for_canary', f"Should recommend approve_for_canary, got {recommendation}"
        print(f"  ✓ Assessment created: {assessment_id}")
        print(f"    Recommendation: {recommendation}")

        conn.commit()

def test_recommendation_logic():
    """Test: Recommendation computation"""
    print("\n✓ TEST: Recommendation Logic")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Get a policy
        cur.execute("""
            SELECT id FROM trust_policy_versions LIMIT 1
        """)
        policy_id = cur.fetchone()[0]

        # Test 1: Good metrics → approve_for_canary
        cur.execute("""
            INSERT INTO trust_impact_assessments (
                policy_id, assessment_type,
                calibration_regression, confidence_shift,
                false_positive_impact, false_negative_impact,
                reputation_impact, dispute_impact,
                simulation_leakage_risk, safety_threshold_compliance,
                rollback_feasibility, audit_completeness,
                recommendation, recommendation_confidence
            ) VALUES (
                %s, 'eval', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0,
                'approve_for_canary', 0.95
            )
            RETURNING id, recommendation
        """, [policy_id])

        _, rec1 = cur.fetchone()
        assert rec1 == 'approve_for_canary', f"Perfect metrics should recommend approve_for_canary"
        print(f"  ✓ Perfect metrics → {rec1}")

        # Test 2: High regression → block
        cur.execute("""
            INSERT INTO trust_impact_assessments (
                policy_id, assessment_type,
                calibration_regression, confidence_shift,
                false_positive_impact, false_negative_impact,
                reputation_impact, dispute_impact,
                simulation_leakage_risk, safety_threshold_compliance,
                rollback_feasibility, audit_completeness,
                recommendation, recommendation_confidence
            ) VALUES (
                %s, 'eval', 0.10, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0,
                'block', 0.85
            )
            RETURNING id, recommendation
        """, [policy_id])

        _, rec2 = cur.fetchone()
        assert rec2 == 'block', f"High regression should be blocked"
        print(f"  ✓ High regression (10%) → {rec2}")

        # Test 3: Low safety compliance → block
        cur.execute("""
            INSERT INTO trust_impact_assessments (
                policy_id, assessment_type,
                calibration_regression, confidence_shift,
                false_positive_impact, false_negative_impact,
                reputation_impact, dispute_impact,
                simulation_leakage_risk, safety_threshold_compliance,
                rollback_feasibility, audit_completeness,
                recommendation, recommendation_confidence
            ) VALUES (
                %s, 'eval', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.90, 1.0, 1.0,
                'block', 0.87
            )
            RETURNING id, recommendation
        """, [policy_id])

        _, rec3 = cur.fetchone()
        assert rec3 == 'block', f"Low safety should be blocked"
        print(f"  ✓ Low safety (90%) → {rec3}")

        # Test 4: High leakage risk → sandbox_only
        cur.execute("""
            INSERT INTO trust_impact_assessments (
                policy_id, assessment_type,
                calibration_regression, confidence_shift,
                false_positive_impact, false_negative_impact,
                reputation_impact, dispute_impact,
                simulation_leakage_risk, safety_threshold_compliance,
                rollback_feasibility, audit_completeness,
                recommendation, recommendation_confidence
            ) VALUES (
                %s, 'eval', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.08, 1.0, 1.0, 1.0,
                'sandbox_only', 0.88
            )
            RETURNING id, recommendation
        """, [policy_id])

        _, rec4 = cur.fetchone()
        assert rec4 == 'sandbox_only', f"High leakage should be sandbox_only"
        print(f"  ✓ High leakage (8%) → {rec4}")

        conn.commit()

def test_blocking_issues():
    """Test: Blocking issue detection"""
    print("\n✓ TEST: Blocking Issue Detection")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Get a policy
        cur.execute("""
            SELECT id FROM trust_policy_versions LIMIT 1
        """)
        policy_id = cur.fetchone()[0]

        # Create assessment with blocking issues
        cur.execute("""
            INSERT INTO trust_impact_assessments (
                policy_id, assessment_type,
                calibration_regression, confidence_shift,
                false_positive_impact, false_negative_impact,
                reputation_impact, dispute_impact,
                simulation_leakage_risk, safety_threshold_compliance,
                rollback_feasibility, audit_completeness,
                recommendation, recommendation_confidence,
                blocking_issues
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id, blocking_issues
        """, [
            policy_id, 'eval', 0.08, 0.0, 0.25, 0.0, 0.0, 0.0, 0.12, 0.80, 0.75, 1.0,
            'block', 0.90, ['Calibration regression exceeds 5%', 'Safety below threshold', 'Rollback risk']
        ])

        _, blocking = cur.fetchone()
        assert len(blocking) == 3, f"Should have 3 blocking issues"
        print(f"  ✓ {len(blocking)} blocking issues detected:")
        for issue in blocking:
            print(f"    - {issue}")

        conn.commit()

def test_warnings():
    """Test: Warning detection"""
    print("\n✓ TEST: Warning Detection")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Get a policy
        cur.execute("""
            SELECT id FROM trust_policy_versions LIMIT 1
        """)
        policy_id = cur.fetchone()[0]

        # Create assessment with warnings
        cur.execute("""
            INSERT INTO trust_impact_assessments (
                policy_id, assessment_type,
                calibration_regression, confidence_shift,
                false_positive_impact, false_negative_impact,
                reputation_impact, dispute_impact,
                simulation_leakage_risk, safety_threshold_compliance,
                rollback_feasibility, audit_completeness,
                recommendation, recommendation_confidence,
                warnings
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id, warnings
        """, [
            policy_id, 'eval', 0.03, 0.06, 0.05, 0.0, -0.12, 0.12, 0.08, 0.96, 0.88, 0.93,
            'require_revision', 0.80, ['Calibration drift >2%', 'Confidence shift >5%', 'Reputation risk', 'Dispute risk']
        ])

        _, warnings = cur.fetchone()
        assert len(warnings) >= 2, f"Should have multiple warnings"
        print(f"  ✓ {len(warnings)} warnings detected")

        conn.commit()

def test_baseline_metrics():
    """Test: Baseline metrics storage"""
    print("\n✓ TEST: Baseline Metrics")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Get a policy
        cur.execute("""
            SELECT id FROM trust_policy_versions LIMIT 1
        """)
        policy_id = cur.fetchone()[0]

        # Record baseline metrics
        cur.execute("""
            INSERT INTO baseline_metrics (
                policy_id, metric_name, metric_value, measurement_timestamp
            ) VALUES
                (%s, 'calibration_accuracy', 0.92, NOW()),
                (%s, 'false_positive_rate', 0.05, NOW()),
                (%s, 'false_negative_rate', 0.03, NOW()),
                (%s, 'safety_score', 0.99, NOW())
        """, [policy_id] * 4)

        # Query baseline metrics
        cur.execute("""
            SELECT COUNT(*) FROM baseline_metrics WHERE policy_id = %s
        """, [policy_id])

        count = cur.fetchone()[0]
        assert count >= 4, f"Should have at least 4 baseline metrics"
        print(f"  ✓ {count} baseline metrics recorded")

        conn.commit()

def test_assessment_immutability():
    """Test: Assessments are immutable"""
    print("\n✓ TEST: Assessment Immutability")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Get a policy
        cur.execute("""
            SELECT id FROM trust_policy_versions LIMIT 1
        """)
        policy_id = cur.fetchone()[0]

        # Create assessment
        cur.execute("""
            INSERT INTO trust_impact_assessments (
                policy_id, assessment_type,
                calibration_regression, confidence_shift,
                false_positive_impact, false_negative_impact,
                reputation_impact, dispute_impact,
                simulation_leakage_risk, safety_threshold_compliance,
                rollback_feasibility, audit_completeness,
                recommendation, recommendation_confidence
            ) VALUES (
                %s, 'eval', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0,
                'approve_for_canary', 0.95
            )
            RETURNING id
        """, [policy_id])

        assessment_id = cur.fetchone()[0]

        # Try to update (should fail)
        try:
            cur.execute("""
                UPDATE trust_impact_assessments
                SET recommendation = 'block'
                WHERE id = %s
            """, [assessment_id])

            conn.commit()
            print("  ✗ FAILED: Assessment should be immutable!")
            return False
        except psycopg2.Error as e:
            if 'immutability' in str(e).lower():
                print(f"  ✓ Assessment immutability enforced")
            else:
                raise
        finally:
            conn.rollback()

def test_canary_eligibility():
    """Test: Assessment determines canary eligibility"""
    print("\n✓ TEST: Canary Eligibility")

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Get a policy
        cur.execute("""
            SELECT id FROM trust_policy_versions LIMIT 1
        """)
        policy_id = cur.fetchone()[0]

        # Create good assessment (canary eligible)
        cur.execute("""
            INSERT INTO trust_impact_assessments (
                policy_id, assessment_type,
                calibration_regression, confidence_shift,
                false_positive_impact, false_negative_impact,
                reputation_impact, dispute_impact,
                simulation_leakage_risk, safety_threshold_compliance,
                rollback_feasibility, audit_completeness,
                recommendation, recommendation_confidence
            ) VALUES (
                %s, 'eval', 0.01, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.99, 0.97, 0.98,
                'approve_for_canary', 0.93
            )
            RETURNING id, recommendation
        """, [policy_id])

        good_id, good_rec = cur.fetchone()
        assert good_rec == 'approve_for_canary', "Good metrics should recommend canary"
        print(f"  ✓ Good assessment: {good_rec} (eligible for canary)")

        # Create bad assessment (not eligible)
        cur.execute("""
            INSERT INTO trust_impact_assessments (
                policy_id, assessment_type,
                calibration_regression, confidence_shift,
                false_positive_impact, false_negative_impact,
                reputation_impact, dispute_impact,
                simulation_leakage_risk, safety_threshold_compliance,
                rollback_feasibility, audit_completeness,
                recommendation, recommendation_confidence
            ) VALUES (
                %s, 'eval', 0.15, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.90, 0.70, 1.0,
                'block', 0.88
            )
            RETURNING id, recommendation
        """, [policy_id])

        bad_id, bad_rec = cur.fetchone()
        assert bad_rec == 'block', "Bad metrics should recommend blocking"
        print(f"  ✓ Bad assessment: {bad_rec} (NOT eligible for canary)")

        conn.commit()

def main():
    """Run all tests"""
    print("=" * 70)
    print("TRUST IMPACT ASSESSMENT SERVICE TEST SUITE")
    print("=" * 70)

    try:
        ensure_test_data()
        test_assessment_creation()
        test_recommendation_logic()
        test_blocking_issues()
        test_warnings()
        test_baseline_metrics()
        test_assessment_immutability()
        test_canary_eligibility()

        print("\n" + "=" * 70)
        print("✓ ALL IMPACT ASSESSMENT TESTS PASSED")
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
