import json
import sys
import types

from scripts import build_ledger


def test_ledger_loads_and_has_all_layers():
    ledger = build_ledger.load_ledger()
    layers = ledger["layers"]

    for index in range(15):
        assert any(key.startswith(f"L{index}_") for key in layers), f"L{index} missing"


def test_rollups_are_computed_from_items():
    ledger = build_ledger.load_ledger()
    rollups = build_ledger.recompute_rollups(ledger)
    items = build_ledger.iter_items(ledger)

    assert rollups["total_items"] == len(items)
    assert rollups["verified"] == sum(1 for item in items if item["status"] == "verified")


def test_remaining_frontier_only_contains_satisfied_dependencies():
    ledger = build_ledger.load_ledger()
    by_id = {item["id"]: item for item in build_ledger.iter_items(ledger)}
    frontier = build_ledger.ready_frontier(ledger)

    assert frontier
    for item in frontier:
        assert item["status"] != "verified"
        assert all(by_id[dep]["status"] == "verified" for dep in item.get("depends_on", []))


def test_gates_report_no_stub_and_no_simulation_status():
    ledger = build_ledger.load_ledger()
    gates = build_ledger.recompute_gates(ledger)

    assert gates["no_stub"] in {"green", "red"}
    assert gates["no_simulation"] in {"green", "red"}
    assert "_no_stub_hit_count" in gates


def test_gate_findings_include_actionable_locations():
    findings = build_ledger.recompute_gate_findings()

    assert "no_stub" in findings
    assert isinstance(findings["no_stub"], list)
    if findings["no_stub"]:
        first = findings["no_stub"][0]
        assert {"path", "line", "marker", "excerpt"}.issubset(first)
        assert isinstance(first["line"], int)


def test_architecture_report_includes_layer_rollups_and_frontier():
    ledger = build_ledger.load_ledger()
    report = build_ledger.architecture_report(ledger)

    assert report["rollups"]["total_items"] == len(build_ledger.iter_items(ledger))
    assert report["layers"]
    assert {layer["layer"] for layer in report["layers"]} == set(ledger["layers"])
    assert report["ready_frontier"]
    for layer in report["layers"]:
        assert {
            "layer",
            "status",
            "total_items",
            "verified",
            "in_progress",
            "not_started",
            "blocked",
            "percent_verified",
            "ready_items",
        }.issubset(layer)


def test_report_command_writes_machine_readable_architecture_report(tmp_path, capsys):
    output = tmp_path / "build-ledger-report.json"
    args = types.SimpleNamespace(output=str(output))

    assert build_ledger.cmd_report(args) == 0

    printed = json.loads(capsys.readouterr().out)
    persisted = json.loads(output.read_text())
    assert persisted == printed
    assert persisted["meta"]["termination_predicate_met"] is False
    assert persisted["rollups"]["percent_verified"] < 100


def test_sync_db_projects_every_item(monkeypatch):
    executed: list[tuple[str, tuple | None]] = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params=None):
            executed.append((sql, params))

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return Cursor()

    fake_psycopg2 = types.SimpleNamespace(connect=lambda database_url: Connection())
    monkeypatch.setitem(sys.modules, "psycopg2", fake_psycopg2)
    monkeypatch.setenv("DATABASE_URL", "postgresql://agentco:password@localhost:5432/agentco")

    assert build_ledger.cmd_sync_db(types.SimpleNamespace()) == 0

    insert_calls = [params for sql, params in executed if "INSERT INTO build_ledger" in sql]
    assert len(insert_calls) == build_ledger.recompute_rollups(build_ledger.load_ledger())["total_items"]
    assert all(len(params) == 7 for params in insert_calls)
