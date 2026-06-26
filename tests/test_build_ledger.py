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
