#!/usr/bin/env python3
"""
Verify LEVEL_3 Database Evidence

This script queries the database to verify that real data was persisted by the
LEVEL_3 autonomy loop. It checks for evidence that:
- Tasks were created
- Goals were created
- Plans were created
- Episodes were created
- Trajectories were recorded
- Outcomes were persisted
- Learner runs were executed
- Candidates were generated
- Eval runs were executed
- Scorecards were created

Exit code:
  0 = All evidence found
  1 = Missing evidence
"""

import os
import sys
import json
from datetime import datetime, timedelta

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    print("❌ psycopg2 not installed. Install with: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)


def get_database_url():
    """Get DATABASE_URL from environment."""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)
    return db_url


def connect_db(db_url):
    """Connect to database."""
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}", file=sys.stderr)
        sys.exit(1)


def count_recent_records(cursor, table_name, minutes=5):
    """Count records created in the last N minutes."""
    try:
        query = sql.SQL(
            "SELECT COUNT(*) FROM {} WHERE created_at > NOW() - INTERVAL '{} minutes'"
        ).format(
            sql.Identifier(table_name),
            sql.Literal(minutes)
        )
        # Use format_query to properly handle the literal
        query_str = f"""
            SELECT COUNT(*) FROM {table_name}
            WHERE created_at > NOW() - INTERVAL '{minutes} minutes'
        """
        cursor.execute(query_str)
        return cursor.fetchone()[0]
    except Exception as e:
        print(f"   ⚠️  Could not query {table_name}: {e}")
        return 0


def main():
    db_url = get_database_url()
    conn = connect_db(db_url)
    cursor = conn.cursor()

    print("📊 Verifying LEVEL_3 database evidence...")
    print("")

    # List of critical tables and what they represent
    # Only include tables from enabled migrations
    evidence_checks = [
        ("autonomy_tasks", "Autonomy tasks created"),
        ("autonomy_goals", "Goals created"),
        ("autonomy_plans", "Plans created"),
        ("autonomy_plan_steps", "Plan steps executed"),
        ("autonomy_episodes", "Memory episodes created"),
        ("autonomy_actions", "Actions in episodes"),
        ("trajectory_store", "Trajectories recorded"),
        ("autonomy_outcomes", "Outcomes persisted"),
        ("reward_calculations", "Rewards calculated"),
        ("replay_batches", "Replay batches created"),
        ("learner_runs", "Learner runs executed"),
        ("learner_candidates", "Candidates generated"),
        ("artifacts", "Artifacts created"),
        ("eval_runs", "Eval runs executed"),
        ("eval_scorecards", "Eval scorecards created"),
    ]

    found_count = 0
    missing_count = 0
    evidence_summary = {}

    for table_name, description in evidence_checks:
        count = count_recent_records(cursor, table_name, minutes=10)
        evidence_summary[table_name] = count

        if count > 0:
            print(f"   ✅ {table_name:30s} {count:3d} records  ({description})")
            found_count += 1
        else:
            print(f"   ❌ {table_name:30s} {count:3d} records  ({description})")
            missing_count += 1

    print("")

    # Check for trace context
    try:
        cursor.execute("""
            SELECT COUNT(DISTINCT trace_id) FROM observability_traces
            WHERE created_at > NOW() - INTERVAL '10 minutes'
        """)
        trace_count = cursor.fetchone()[0]
        if trace_count > 0:
            print(f"   ✅ Unique trace IDs                 {trace_count:3d} traces")
        else:
            print(f"   ⚠️  No trace IDs found (optional)")
    except Exception as e:
        print(f"   ⚠️  Could not verify traces: {e}")

    print("")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Summary
    total_checks = found_count + missing_count
    if missing_count == 0:
        print(f"✅ ALL EVIDENCE FOUND ({found_count}/{total_checks} tables)")
        print("")
        print("Database verification passed. LEVEL_3 created real persisted records.")

        # Save evidence summary
        try:
            cursor.execute("""
                SELECT
                  COUNT(*) FROM autonomy_tasks,
                  (SELECT COUNT(*) FROM learner_candidates) as candidates,
                  (SELECT COUNT(*) FROM eval_scorecards) as scorecards,
                  (SELECT COUNT(*) FROM audit_events) as audits
            """)
        except:
            pass

        conn.close()
        sys.exit(0)
    else:
        print(f"❌ MISSING EVIDENCE ({found_count}/{total_checks} tables found)")
        print("")
        print("Database verification FAILED. Not all expected records were created.")
        print("")
        print("Missing records in:")
        for table_name, description in evidence_checks:
            if evidence_summary.get(table_name, 0) == 0:
                print(f"  - {table_name} ({description})")

        conn.close()
        sys.exit(1)


if __name__ == "__main__":
    main()
