from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "backend/src/db/migrations/018_refoundation_canonical_schema.sql"
ROLLBACK = ROOT / "backend/src/db/rollbacks/018_refoundation_canonical_schema.down.sql"
MATRIX = ROOT / "docs/refoundation/IMPLEMENTATION_MATRIX.md"
CONTRACTS = ROOT / "docs/refoundation/LAYER_CONTRACTS.md"
ARCHITECTURE = ROOT / "docs/architecture/agentco_architecture.md"


def test_canonical_schema_declares_required_tables():
    sql = MIGRATION.read_text()
    for table in [
        "principals",
        "constitutions",
        "policies",
        "workflow_intents",
        "claims",
        "evidence_artifacts",
        "sources",
        "resolutions",
        "calibration_cells",
        "action_attestations",
        "override_cases",
        "memory_events",
        "benchmark_eval_runs",
    ]:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql


def test_canonical_schema_has_down_migration_contract():
    rollback = ROLLBACK.read_text()
    for table in [
        "benchmark_eval_runs",
        "memory_events",
        "override_cases",
        "action_attestations",
        "calibration_cells",
        "resolutions",
        "sources",
        "evidence_artifacts",
        "workflow_intents",
        "policies",
        "constitutions",
        "principals",
    ]:
        assert f"DROP TABLE IF EXISTS {table}" in rollback


def test_foundational_layer_contracts_are_documented():
    text = CONTRACTS.read_text()
    for contract in [
        "Substrate Runtime",
        "Evidence Kernel",
        "Source Independence",
        "Durable Execution",
        "Provenance",
        "Uncertainty",
    ]:
        assert contract in text


def test_current_modules_are_mapped_to_layers():
    matrix = MATRIX.read_text()
    architecture = ARCHITECTURE.read_text()
    for module in [
        "backend/src/services/audit-log.service.ts",
        "calibration/*",
        "reserve/*",
        "runtime/confidence",
        "learning/*",
        "agents/*",
        "frontend/src/app/*",
    ]:
        assert module in matrix or module in architecture
