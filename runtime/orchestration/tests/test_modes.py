from runtime.orchestration.doctor import Check, build_report, check_production_secret_posture
from runtime.orchestration.modes import (
    assert_fixture_fallback_allowed,
    choose_runtime_mode,
    classify_mode,
    fixture_fallback_allowed,
)


def test_docker_unavailable_native_postgres_selects_local_native():
    assert choose_runtime_mode("local_full", {"docker_daemon": "blocked", "postgres": "real"}) == "local_native"


def test_kafka_unavailable_selects_in_process_bus_outside_production():
    result = classify_mode("local_native", {"python": "real", "filesystem_reports": "real", "postgres": "real", "migrations": "real", "core_db_schema": "real", "sensitive_route_auth": "real", "kafka": "missing"})
    assert {"service": "kafka", "fallback": "in_process_event_bus", "status": "missing"} in result["fallbacks_used"]


def test_missing_openai_fake_only_offline():
    offline = classify_mode("offline_fixture", {"python": "real", "filesystem_reports": "real", "openai_connectivity": "missing"})
    production = classify_mode("production", {"python": "real", "filesystem_reports": "real", "openai_connectivity": "missing"})
    assert any(f["fallback"] == "deterministic_fixture_llm" for f in offline["fallbacks_used"])
    assert not production["fallbacks_used"]


def test_production_requires_real_infrastructure_no_fallbacks():
    result = classify_mode(
        "production",
        {
            "python": "real",
            "node": "real",
            "npm": "real",
            "backend_build": "real",
            "frontend_build": "real",
            "postgres": "real",
            "migrations": "real",
            "core_db_schema": "real",
            "redis": "missing",
            "kafka": "missing",
            "vault": "missing",
            "prometheus": "missing",
            "grafana": "missing",
            "resolution_service": "real",
            "sensitive_route_auth": "real",
            "production_secret_posture": "real",
            "filesystem_reports": "real",
        },
    )
    assert result["can_continue"] is False
    assert "redis:required_unavailable" in result["disabled_capabilities"]
    assert not result["fallbacks_used"]


def test_production_secret_posture_rejects_dev_defaults(monkeypatch):
    monkeypatch.setenv("AGENTCO_API_KEY", "dev-api-key")
    monkeypatch.setenv("EVENT_BUS_SIGNING_KEY", "dev-key-replace-in-production")
    monkeypatch.setenv("EVENT_BUS_HMAC_KEY", "dev-insecure-key")
    monkeypatch.setenv("JWT_SECRET", "change-me-generate-with-openssl-rand-hex-64")
    monkeypatch.setenv("VAULT_TOKEN", "root")
    monkeypatch.setenv("DATABASE_URL", "postgresql://agentco:password@localhost:5432/agentco")
    check = check_production_secret_posture()
    assert check.status == "blocked"
    assert "AGENTCO_API_KEY" in check.detail


def test_resolution_service_missing_disables_primary_ledger_resolution():
    result = classify_mode("local_native", {"python": "real", "filesystem_reports": "real", "postgres": "real", "migrations": "real", "core_db_schema": "real", "sensitive_route_auth": "real", "resolution_service": "missing"})
    assert {"service": "resolution_service", "fallback": "disable_primary_ledger_resolution", "status": "missing"} in result["fallbacks_used"]


def test_doctor_report_schema_and_fallback_status():
    report = build_report("local_native", [
        Check("python", "real", "3.13"),
        Check("node", "real", "node"),
        Check("npm", "real", "npm"),
        Check("postgres", "real", "postgres"),
        Check("migrations", "real", "runner"),
        Check("core_db_schema", "real", "schema"),
        Check("filesystem_reports", "real", "reports"),
        Check("sensitive_route_auth", "real", "auth"),
        Check("kafka", "missing", "no kafka"),
    ])
    assert report["can_continue"] is True
    assert any(f["service"] == "kafka" for f in report["fallbacks_used"])


def test_sensitive_routes_never_downgraded_by_degraded_mode():
    result = classify_mode("degraded", {"python": "real", "filesystem_reports": "real", "sensitive_route_auth": "broken"})
    assert "sensitive_route_auth:required_unavailable" in result["disabled_capabilities"]


def test_fixture_fallback_only_allowed_in_offline_modes():
    assert fixture_fallback_allowed("offline_fixture", {"AGENTCO_ENV": "development"})
    assert fixture_fallback_allowed("ci_smoke", {"AGENTCO_ENV": "test"})
    assert not fixture_fallback_allowed("local_native", {"AGENTCO_ENV": "development"})


def test_fixture_fallback_forbidden_in_staging_and_production():
    assert not fixture_fallback_allowed("offline_fixture", {"AGENTCO_ENV": "staging"})
    assert not fixture_fallback_allowed("offline_fixture", {"NODE_ENV": "production"})
    try:
        assert_fixture_fallback_allowed("offline_fixture", {"AGENTCO_ENV": "production"})
    except RuntimeError as exc:
        assert "only allowed" in str(exc)
    else:
        raise AssertionError("production allowed deterministic fixture fallback")
