"""PostgreSQL connection and query helpers for AgentCo Python services."""
from __future__ import annotations

import os
import logging
from typing import Any, Optional, List, Dict
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Singleton-like wrapper for PostgreSQL connection."""

    _instance: Optional[DatabaseConnection] = None

    def __init__(self):
        self.conn = None
        self.dsn = os.environ.get("DATABASE_URL")
        if not self.dsn:
            raise RuntimeError("DATABASE_URL environment variable not set")

    @classmethod
    def get_instance(cls) -> DatabaseConnection:
        if cls._instance is None:
            cls._instance = DatabaseConnection()
        return cls._instance

    def connect(self) -> psycopg2.extensions.connection:
        """Get or create database connection."""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(self.dsn)
        return self.conn

    def close(self) -> None:
        """Close database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()
            self.conn = None

    def execute_query(
        self,
        query: str,
        params: tuple = (),
        fetch_one: bool = False,
        fetch_all: bool = True,
    ) -> Any:
        """Execute SELECT query and return results."""
        try:
            conn = self.connect()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query, params)
            if fetch_one:
                result = cur.fetchone()
            elif fetch_all:
                result = cur.fetchall()
            else:
                result = None
            cur.close()
            return result
        except Exception as e:
            # Rollback failed query to prevent transaction abort
            if self.conn and not self.conn.closed:
                self.conn.rollback()
            logger.error(f"Query failed: {e}")
            raise

    def execute_update(
        self, query: str, params: tuple = ()
    ) -> int:
        """Execute INSERT/UPDATE/DELETE and return affected rows."""
        try:
            conn = self.connect()
            cur = conn.cursor()
            cur.execute(query, params)
            affected = cur.rowcount
            conn.commit()
            cur.close()
            return affected
        except Exception as e:
            if self.conn and not self.conn.closed:
                self.conn.rollback()
            logger.error(f"Update failed: {e}")
            raise

    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute multiple INSERT/UPDATE statements."""
        try:
            conn = self.connect()
            cur = conn.cursor()
            total = 0
            for params in params_list:
                cur.execute(query, params)
                total += cur.rowcount
            conn.commit()
            cur.close()
            return total
        except Exception as e:
            if self.conn and not self.conn.closed:
                self.conn.rollback()
            logger.error(f"Batch update failed: {e}")
            raise


# Singleton accessor
def get_db() -> DatabaseConnection:
    """Get database connection instance."""
    return DatabaseConnection.get_instance()


# High-level query helpers
def query_autonomy_goals(limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch autonomy goals from database."""
    db = get_db()
    rows = db.execute_query(
        "SELECT id, goal_id, objective, status, depth FROM autonomy_goals LIMIT %s",
        (limit,),
        fetch_all=True,
    )
    return rows or []


def query_autonomy_evidence(action_id: str) -> List[Dict[str, Any]]:
    """Fetch evidence for a specific action.

    Args:
        action_id: The action_id from autonomy_goal_actions (not goal_id)
    """
    db = get_db()
    rows = db.execute_query(
        """SELECT id, source_id, url, title, snippet, source_type, is_public_access
           FROM autonomy_evidence WHERE action_id = %s""",
        (action_id,),
        fetch_all=True,
    )
    return rows or []


def insert_autonomy_memory(
    action_id: str, content: Dict[str, Any]
) -> str:
    """Insert memory entry and return memory_id."""
    import json
    import uuid
    from datetime import datetime

    db = get_db()
    memory_id = str(uuid.uuid4())
    db.execute_update(
        """INSERT INTO autonomy_memory (id, action_id, content, timestamp, created_at)
           VALUES (%s, %s, %s, %s, %s)""",
        (memory_id, action_id, json.dumps(content), datetime.utcnow(), datetime.utcnow()),
    )
    return memory_id


def query_calibration_state() -> Dict[str, Any]:
    """Query overall calibration health metrics."""
    db = get_db()

    # Count unresolved predictions (resolved=false)
    unresolved = db.execute_query(
        "SELECT COUNT(*) as count FROM prediction_ledger WHERE resolved = false",
        fetch_one=True,
    )

    # Count proposed goals (internal goals needing execution)
    proposed_goals = db.execute_query(
        "SELECT COUNT(*) as count FROM autonomy_goals WHERE status = 'proposed'",
        fetch_one=True,
    )

    return {
        "unresolved_predictions": unresolved.get("count", 0) if unresolved else 0,
        "proposed_goals": proposed_goals.get("count", 0) if proposed_goals else 0,
    }


def insert_autonomy_goal(
    title: str, description: str = "", status: str = "proposed"
) -> str:
    """Create new autonomy goal and return goal_id."""
    import uuid
    from datetime import datetime

    db = get_db()
    goal_id = str(uuid.uuid4())
    db.execute_update(
        """INSERT INTO autonomy_goals
           (id, title, description, status, source, proposed_by, domain, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            goal_id,
            title,
            description,
            status,
            "agent_proposed",
            "civilization-service",
            "autonomy",
            datetime.utcnow(),
        ),
    )
    return goal_id
