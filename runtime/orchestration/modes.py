from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping


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


RUNTIME_MODES: dict[str, RuntimeMode] = {
    "production": RuntimeMode(
        "production",
        (
            "python",
            "node",
            "npm",
            "backend_build",
            "frontend_build",
            "postgres",
            "migrations",
            "core_db_schema",
            "redis",
            "kafka",
            "vault",
            "prometheus",
            "grafana",
            "resolution_service",
            "sensitive_route_auth",
            "production_secret_posture",
            "filesystem_reports",
        ),
        ("openai_connectivity",),
        {},
        ("deterministic_llm", "file_ledger", "in_memory_db", "auth_bypass", "env_secrets"),
        True,
        True,
        False,
        True,
    ),
    "local_full": RuntimeMode(
        "local_full",
        ("python", "node", "npm", "postgres", "migrations", "core_db_schema", "filesystem_reports", "sensitive_route_auth"),
        ("docker_daemon", "kafka", "redis", "vault", "prometheus", "grafana", "openai_connectivity", "resolution_service"),
        {
            "kafka": "in_process_event_bus",
            "redis": "memory_cache",
            "vault": "env_secret_provider",
            "prometheus": "json_metrics_writer",
            "grafana": "metrics_json_only",
            "openai_connectivity": "disabled_live_llm",
            "resolution_service": "disable_primary_ledger_resolution",
        },
        ("deterministic_llm", "in_memory_db"),
        True,
        True,
        False,
        True,
    ),
    "local_native": RuntimeMode(
        "local_native",
        ("python", "node", "npm", "postgres", "migrations", "core_db_schema", "filesystem_reports", "sensitive_route_auth"),
        ("docker_daemon", "kafka", "redis", "vault", "prometheus", "grafana", "openai_connectivity", "resolution_service"),
        {
            "docker_daemon": "native_services",
            "kafka": "in_process_event_bus",
            "redis": "memory_cache",
            "vault": "env_secret_provider",
            "prometheus": "json_metrics_writer",
            "grafana": "metrics_json_only",
            "openai_connectivity": "disabled_live_llm",
            "resolution_service": "disable_primary_ledger_resolution",
        },
        ("deterministic_llm", "in_memory_db"),
        True,
        True,
        False,
        True,
    ),
    "offline_fixture": RuntimeMode(
        "offline_fixture",
        ("python", "filesystem_reports"),
        ("node", "npm", "postgres", "core_db_schema"),
        {
            "postgres": "file_backed_smoke_ledger",
            "openai_connectivity": "deterministic_fixture_llm",
            "kafka": "file_event_log",
            "redis": "memory_cache",
            "vault": "env_secret_provider",
            "prometheus": "json_metrics_writer",
            "grafana": "metrics_json_only",
            "resolution_service": "disable_primary_ledger_resolution",
        },
        (),
        False,
        False,
        True,
        True,
    ),
    "ci_smoke": RuntimeMode(
        "ci_smoke",
        ("python", "filesystem_reports"),
        ("node", "npm"),
        {
            "postgres": "file_backed_smoke_ledger",
            "openai_connectivity": "deterministic_fixture_llm",
            "kafka": "file_event_log",
            "redis": "memory_cache",
            "vault": "env_secret_provider",
            "prometheus": "json_metrics_writer",
            "grafana": "metrics_json_only",
            "resolution_service": "disable_primary_ledger_resolution",
        },
        (),
        False,
        False,
        True,
        True,
    ),
    "degraded": RuntimeMode(
        "degraded",
        ("python", "filesystem_reports", "sensitive_route_auth"),
        (),
        {
            "kafka": "in_process_event_bus",
            "redis": "memory_cache",
            "vault": "env_secret_provider",
            "prometheus": "json_metrics_writer",
            "grafana": "metrics_json_only",
            "resolution_service": "disable_primary_ledger_resolution",
        },
        ("auth_bypass", "governance_bypass"),
        True,
        False,
        False,
        True,
    ),
}


def service_ok(status: str | None) -> bool:
    return status == "real"


def choose_runtime_mode(requested: str, service_status: Mapping[str, str]) -> str:
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
    if postgres_ok:
        return "local_native"
    return "offline_fixture"


def is_production_like_env(env: Mapping[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    agentco_env = values.get("AGENTCO_ENV", "").lower()
    node_env = values.get("NODE_ENV", "").lower()
    return agentco_env in {"production", "staging"} or node_env == "production"


def fixture_fallback_allowed(mode_name: str, env: Mapping[str, str] | None = None) -> bool:
    if is_production_like_env(env):
        return False
    return mode_name in {"offline_fixture", "ci_smoke"}


def assert_fixture_fallback_allowed(mode_name: str, env: Mapping[str, str] | None = None) -> None:
    if not fixture_fallback_allowed(mode_name, env):
        raise RuntimeError(
            f"deterministic fixture fallback is only allowed in offline_fixture/ci_smoke outside staging/production; requested={mode_name}"
        )


def classify_mode(mode_name: str, service_status: Mapping[str, str]) -> dict:
    mode = RUNTIME_MODES[mode_name]
    missing_required = [s for s in mode.required_services if not service_ok(service_status.get(s))]
    fallbacks = []
    disabled = []
    for service, status in service_status.items():
        if status in ("real", "not_required"):
            continue
        fallback = mode.allowed_fallbacks.get(service)
        if fallback:
            fallbacks.append({"service": service, "fallback": fallback, "status": status})
        elif service in mode.required_services:
            disabled.append(f"{service}:required_unavailable")
        else:
            disabled.append(service)
    return {
        "mode": mode.name,
        "can_continue": not missing_required,
        "missing_required": missing_required,
        "fallbacks_used": fallbacks,
        "disabled_capabilities": disabled,
    }
