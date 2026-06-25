from runtime.orchestration.doctor import Check, build_report
from runtime.orchestration.modes import choose_runtime_mode, classify_mode


def test_docker_unavailable_native_postgres_selects_local_native():
    status = {"docker_daemon": "blocked", "postgres": "real"}
    assert choose_runtime_mode("local_full", status) == "local_native"


def test_kafka_unavailable_uses_in_process_bus_outside_production():
    status = {"python": "real", "filesystem_reports": "real", "postgres": "real", "migrations": "real", "core_db_schema": "real", "kafka": "missing"}
    result = classify_mode("local_native", status)
    assert {"service": "kafka", "fallback": "in_process_event_bus", "status": "missing"} in result["fallbacks_used"]


def test_missing_openai_fake_only_offline():
    status = {"python": "real", "filesystem_reports": "real", "openai_connectivity": "missing"}
    offline = classify_mode("offline_fixture", status)
    prod = classify_mode("production", status)
    assert any(item["fallback"] == "deterministic_fixture_llm" for item in offline["fallbacks_used"])
    assert not any(item.get("fallback") == "deterministic_fixture_llm" for item in prod["fallbacks_used"])


def test_production_rejects_fake_llm_fallback():
    status = {"python": "real", "filesystem_reports": "real", "postgres": "real", "migrations": "real", "core_db_schema": "real", "vault": "real", "resolution_service": "real", "sensitive_route_auth": "real", "openai_connectivity": "missing"}
    result = classify_mode("production", status)
    assert not result["fallbacks_used"]


def test_resolution_service_missing_disables_primary_resolution_without_bypass():
    status = {"python": "real", "filesystem_reports": "real", "postgres": "real", "migrations": "real", "core_db_schema": "real", "resolution_service": "missing"}
    result = classify_mode("local_native", status)
    assert {"service": "resolution_service", "fallback": "disable_primary_ledger_resolution", "status": "missing"} in result["fallbacks_used"]


def test_doctor_report_schema_and_fallback_status():
    checks = [
        Check("python", "real", "3.13").to_dict(),
    ]
    # build_report expects Check objects, not dicts.
    report = build_report(
        "local_native",
        [
            Check("python", "real", "3.13"),
            Check("node", "real", "node"),
            Check("npm", "real", "npm"),
            Check("postgres", "real", "pg"),
            Check("migrations", "real", "runner"),
            Check("core_db_schema", "real", "schema"),
            Check("filesystem_reports", "real", "reports"),
            Check("kafka", "missing", "no kafka"),
        ],
    )
    assert set(["can_continue", "selected_runtime_mode", "disabled_capabilities", "fallbacks_used", "required_fixes", "safe_next_command"]).issubset(report)
    assert any(item["service"] == "kafka" for item in report["fallbacks_used"])


def test_sensitive_routes_not_downgraded_by_degraded_mode():
    status = {"python": "real", "filesystem_reports": "real", "sensitive_route_auth": "broken"}
    result = classify_mode("degraded", status)
    assert "sensitive_route_auth" in result["disabled_capabilities"]
