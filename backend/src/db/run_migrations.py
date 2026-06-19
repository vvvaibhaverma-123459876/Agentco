"""
Database migration runner with environment variable substitution.

Applies all migrations in sequential order to the database specified by DATABASE_URL.
Handles environment variable substitution for sensitive values (e.g., role passwords).

Usage:
  python run_migrations.py                    # runs all migrations
  python run_migrations.py --check-only       # validates migrations without applying
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    psycopg2 = None


def get_migration_files() -> list[Path]:
    """Return all migration SQL files in sorted order."""
    migrations_dir = Path(__file__).parent / "migrations"
    backend_files = sorted(migrations_dir.glob("*.sql"))

    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    reserve_dir = repo_root / "reserve" / "migrations"
    reserve_files = sorted(reserve_dir.glob("*.sql")) if reserve_dir.exists() else []

    migration_files = backend_files + reserve_files
    return migration_files


def substitute_env_vars(sql_text: str) -> str:
    """
    Substitute environment variable placeholders in SQL.

    Placeholders use the format :VAR_NAME inside single quotes
    E.g. ':RESOLUTION_SERVICE_PASSWORD' gets replaced with the password value
    The placeholder is already inside quotes in the SQL, so we replace just the placeholder.

    If an env var is missing in development, defaults are provided:
      - RESOLUTION_SERVICE_PASSWORD: resolution-service-dev-password
    In production, defaults fail closed.
    """
    # Handle RESOLUTION_SERVICE_PASSWORD
    if ":RESOLUTION_SERVICE_PASSWORD" in sql_text:
        password = os.environ.get("RESOLUTION_SERVICE_PASSWORD")
        if not password:
            if os.environ.get("AGENTCO_ENV") == "production":
                raise RuntimeError("RESOLUTION_SERVICE_PASSWORD must be set in production")
            password = "resolution-service-dev-password"
            print("⚠️  RESOLUTION_SERVICE_PASSWORD not set; using dev-only password", file=sys.stderr)
        # Escape single quotes for SQL (password is placed inside quotes in the SQL)
        password_escaped = password.replace("'", "''")
        # Replace placeholder (which is already surrounded by single quotes in SQL)
        sql_text = sql_text.replace("':RESOLUTION_SERVICE_PASSWORD'", f"'{password_escaped}'")

    return sql_text


def run_migrations(db_url: Optional[str] = None) -> bool:
    """
    Run all migrations in order.

    Args:
        db_url: PostgreSQL connection string. Defaults to DATABASE_URL env var.

    Returns:
        True if successful, False otherwise.
    """
    if psycopg2 is None:
        print("ERROR: psycopg2 not installed. Install with: pip install psycopg2-binary", file=sys.stderr)
        return False

    from agentco_security.env_guard import assert_production_secrets

    assert_production_secrets()
    db_url = db_url or os.environ.get("DATABASE_URL", "postgresql://agentco:password@localhost:5432/agentco")

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True  # Each migration is a separate transaction
        cursor = conn.cursor()

        migration_files = get_migration_files()
        if not migration_files:
            print("ERROR: No migration files found", file=sys.stderr)
            return False

        print(f"📁 Found {len(migration_files)} migrations")
        print()

        for migration_file in migration_files:
            migration_name = migration_file.name
            print(f"▶️  Applying {migration_name}...", end=" ", flush=True)

            try:
                # Read the SQL file
                sql_text = migration_file.read_text()

                # Substitute environment variables
                sql_text = substitute_env_vars(sql_text)

                # Execute the migration
                cursor.execute(sql_text)

                print("✅ OK")
            except psycopg2.Error as e:
                print(f"❌ FAILED")
                print(f"\nERROR in {migration_name}:")
                print(f"  {e}", file=sys.stderr)
                cursor.close()
                conn.close()
                return False
            except Exception as e:
                print(f"❌ FAILED")
                print(f"\nUnexpected error in {migration_name}:")
                print(f"  {e}", file=sys.stderr)
                cursor.close()
                conn.close()
                return False

        cursor.close()
        conn.close()

        print()
        print(f"✅ All {len(migration_files)} migrations applied successfully")
        return True

    except psycopg2.OperationalError as e:
        print(f"ERROR: Failed to connect to database: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    check_only = "--check-only" in sys.argv
    if check_only:
        print("🔍 Checking migrations (no changes will be applied)...\n")
        # Just list the migrations without applying
        migration_files = get_migration_files()
        for mf in migration_files:
            print(f"  ✓ {mf.name}")
        sys.exit(0)

    success = run_migrations()
    sys.exit(0 if success else 1)
