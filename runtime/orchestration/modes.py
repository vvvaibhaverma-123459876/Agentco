"""Runtime mode policy for AgentCo.

Modes are policy, not implementation magic: fallbacks are only allowed when
listed here and surfaced in doctor reports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


SERVICE_NAMES = [
    "python",
    "python_dependencies",
    "node",
    "npm",
    "backend_build",
    "frontend_build",
    "docker_cli",
    "docker_daemon",
    "docker_compose",
    "postgres",
    "migration_dependencies",
    "migrations",
    "core_db_schema",
    "redis",
    "kafka",
    "vault",
    "prometheus",
    "grafana",
    "openai_env",
    "openai_connectivity",
    "resolution_service",
    "backend_health",
    "sensitive_route_auth",
    "filesystem_reports",
]


@dataclass(frozen=True)
class RuntimeMode:
    name: str
    required_services: tuple[str, ...]
    optional_services: tuple[str, ...]
    allowed_fallbacks: Mapping[str, str]
    forbidden_fallbacks: tuple[str, ...]
    live_llm_allowed: bool
    db_writes_allowed: bool
    simulated_data_allowed: bool
    unsafe_actions_fail_closed: bool

    def fallback_for(self, service: str) -> str | None:
        return self.allowed_fallbacks.get(service)


RUNTIME_MODES: dict[str, RuntimeMode] = {
    "production": RuntimeMode(
        name="production",
        required_services=(
            "python",
            "node",
            "npm",
            "backend_build",
            "frontend_build",
            "postgres",
            "migration_dependencies",
            "migrations",
            "core_db_schema",
            "vault",
            "resolution_service",
            "sensitive_route_auth",
            "filesystem_reports",
        ),
        optional_services=("kafka", "redis", "prometheus", "grafana", "openai_connectivity"),
        allowed_fallbacks={},
        forbidden_fallbacks=("fake_llm", "in_memory_db", "file_ledger", "env_secrets", "memory_cache", "in_process_event_bus"),
        live_llm_allowed=True,
        db_writes_allowed=True,
        simulated_data_allowed=False,
        unsafe_actions_fail_closed=True,
    ),
    "local_full": RuntimeMode(
        name="local_full",
        required_services=("python", "node", "npm", "postgres", "migration_dependencies", "migrations", "core_db_schema", "filesystem_reports"),
        optional_services=("docker_daemon", "docker_compose", "kafka", "redis", "vault", "prometheus", "grafana", "openai_connectivity", "resolution_service"),
        allowed_fallbacks={
            "kafka": "in_process_event_bus",
            "redis": "memory_cache",
            "vault": "env_secret_provider",
            "prometheus": "json_metrics_writer",
            "grafana": "metrics_json_only",
            "openai_connectivity": "disabled_live_llm",
            "resolution_service": "disable_primary_ledger_resolution",
        },
        forbidden_fallbacks=("fake_llm", "in_memory_db"),
        live_llm_allowed=True,
        db_writes_allowed=True,
        simulated_data_allowed=False,
        unsafe_actions_fail_closed=True,
    ),
    "local_native": RuntimeMode(
        name="local_native",
        required_services=("python", "node", "npm", "postgres", "migration_dependencies", "migrations", "core_db_schema", "filesystem_reports"),
        optional_services=("docker_daemon", "kafka", "redis", "vault", "prometheus", "grafana", "openai_connectivity", "resolution_service"),
        allowed_fallbacks={
            "docker_daemon": "native_services",
            "kafka": "in_process_event_bus",
            "redis": "memory_cache",
            "vault": "env_secret_provider",
            "prometheus": "json_metrics_writer",
            "grafana": "metrics_json_only",
            "openai_connectivity": "disabled_live_llm",
            "resolution_service": "disable_primary_ledger_resolution",
        },
        forbidden_fallbacks=("fake_llm", "in_memory_db"),
        live_llm_allowed=True,
        db_writes_allowed=True,
        simulated_data_allowed=False,
        unsafe_actions_fail_closed=True,
    ),
    "offline_fixture": RuntimeMode(
        name="offline_fixture",
        required_services=("python", "filesystem_reports"),
        optional_services=("node", "npm", "postgres", "core_db_schema"),
        allowed_fallbacks={
            "postgres": "file_backed_smoke_ledger",
            "openai_connectivity": "deterministic_fixture_llm",
            "kafka": "file_event_log",
            "redis": "memory_cache",
            "vault": "env_secret_provider",
            "prometheus": "json_metrics_writer",
            "grafana": "metrics_json_only",
            "resolution_service": "disable_primary_ledger_resolution",
        },
        forbidden_fallbacks=(),
        live_llm_allowed=False,
        db_writes_allowed=False,
        simulated_data_allowed=True,
        unsafe_actions_fail_closed=True,
    ),
    "ci_smoke": RuntimeMode(
        name="ci_smoke",
        required_services=("python", "filesystem_reports"),
        optional_services=("node", "npm"),
        allowed_fallbacks={
            "postgres": "file_backed_smoke_ledger",
            "openai_connectivity": "deterministic_fixture_llm",
            "kafka": "file_event_log",
            "redis": "memory_cache",
            "vault": "env_secret_provider",
            "prometheus": "json_metrics_writer",
            "grafana": "metrics_json_only",
            "resolution_service": "disable_primary_ledger_resolution",
        },
        forbidden_fallbacks=(),
        live_llm_allowed=False,
        db_writes_allowed=False,
        simulated_data_allowed=True,
        unsafe_actions_fail_closed=True,
    ),
    "degraded": RuntimeMode(
        name="degraded",
        required_services=("python", "filesystem_reports"),
        optional_services=tuple(SERVICE_NAMES),
        allowed_fallbacks={
            "kafka": "in_process_event_bus",
            "redis": "memory_cache",
            "vault": "env_secret_provider",
            "prometheus": "json_metrics_writer",
            "grafana": "metrics_json_only",
            "openai_connectivity": "disabled_live_llm",
            "resolution_service": "disable_primary_ledger_resolution",
            "postgres": "read_only_or_offline_only",
        },
        forbidden_fallbacks=("auth_bypass", "governance_bypass"),
        live_llm_allowed=True,
        db_writes_allowed=False,
        simulated_data_allowed=False,
        unsafe_actions_fail_closed=True,
    ),
}


def service_ok(status: str | None) -> bool:
    return status == "real"


def choose_runtime_mode(requested: str, service_status: Mapping[str, str]) -> str:
    """Select the safest mode compatible with observed services."""

    if requested in ("production", "offline_fixture", "ci_smoke"):
        return requested

    postgres_ok = service_ok(service_status.get("postgres"))
    docker_ok = service_ok(service_status.get("docker_daemon"))
    if requested == "local_full":
        if docker_ok and postgres_ok:
            return "local_full"
        if postgres_ok:
            return "local_native"
        return "degraded"

    if requested == "local_native":
        return "local_native" if postgres_ok else "degraded"

    if requested == "degraded":
        return "degraded"

    if postgres_ok:
        return "local_native"
    return "offline_fixture"


def classify_mode(mode_name: str, service_status: Mapping[str, str]) -> dict:
    mode = RUNTIME_MODES[mode_name]
    missing_required = [
        service for service in mode.required_services
        if not service_ok(service_status.get(service))
    ]
    fallbacks_used = []
    disabled = []
    for service, status in service_status.items():
        if service_ok(status) or status == "not_required":
            continue
        fallback = mode.fallback_for(service)
        if fallback:
            fallbacks_used.append({"service": service, "fallback": fallback, "status": status})
        elif service in mode.required_services:
            disabled.append(f"{service}:required_unavailable")
        else:
            disabled.append(service)
    return {
        "mode": mode.name,
        "can_continue": len(missing_required) == 0,
        "missing_required": missing_required,
        "fallbacks_used": fallbacks_used,
        "disabled_capabilities": disabled,
    }
