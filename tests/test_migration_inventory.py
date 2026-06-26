from pathlib import Path
import re


MIGRATIONS = Path("backend/src/db/migrations")


def test_active_migrations_have_monotonic_numeric_prefixes():
    active = sorted(path.name for path in MIGRATIONS.glob("*.sql"))
    prefixes = []
    for name in active:
        match = re.match(r"^(\d+)([a-z]?)_", name)
        assert match, f"migration lacks ordered prefix: {name}"
        prefixes.append((int(match.group(1)), match.group(2)))
    assert prefixes == sorted(prefixes)
    assert len(active) == len(set(active))


def test_disabled_migrations_are_not_silent_runtime_capabilities():
    disabled = sorted(path.name for path in MIGRATIONS.glob("*.sql.disabled"))
    assert disabled, "expected disabled migrations to be explicitly inventoried"

    report = Path("reports/system_run/latest/MIGRATION_STATUS_REPORT.md").read_text()
    for name in disabled:
        assert name in report
        assert "unsupported/future" in report


def test_agent_tasks_view_replaces_nonexistent_durable_tasks_path():
    migration = (MIGRATIONS / "075_agent_tasks_canonical_view.sql").read_text()
    assert "CREATE OR REPLACE VIEW agent_tasks" in migration
    assert "FROM workflow_tasks" in migration
