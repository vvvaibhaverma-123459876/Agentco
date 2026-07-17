from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import socket
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from .evidence import canonical_json, git
from .providers import ProviderConfigurationError, _host_matches_allowlist, _validate_provider_url


ROOT = Path(__file__).resolve().parents[1]
GENESIS_V5 = ROOT / "benchmarks" / "capability_genesis_v5"

PROVIDER_CONFIG_SCHEMA = ROOT / "schemas" / "real_provider_config.schema.json"
PROVIDER_PREFLIGHT_SCHEMA = ROOT / "schemas" / "real_provider_preflight.schema.json"
AUTHORIZATION_SCHEMA = ROOT / "schemas" / "real_provider_campaign_authorization.schema.json"
EXECUTION_EVIDENCE_SCHEMA = ROOT / "schemas" / "real_provider_execution_evidence.schema.json"

PROTOCOL_IDENTITY = "governed-capability-protocol-baseline-v3"
GENESIS_IDENTITY = "governed-capability-genesis-v5"


class ReadinessError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_hash(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def schema_validate(path: Path, value: Any) -> None:
    schema = load_json(path)
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
    if errors:
        joined = "; ".join(error.message for error in errors)
        raise ReadinessError("schema_validation_failed", f"{path.name}: {joined}")


def _env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def provider_config_from_env(provider: str = "openai_compatible") -> dict[str, Any]:
    if provider != "openai_compatible":
        raise ReadinessError("unsupported_readiness_provider", f"Batch 09A readiness currently supports openai_compatible, got {provider}")
    return {
        "provider_name": provider,
        "model_identifier": _env("OPENAI_MODEL"),
        "api_base_url": _env("OPENAI_BASE_URL"),
        "credential_reference": "env:OPENAI_API_KEY" if _env("OPENAI_API_KEY") else None,
        "provider_host_allowlist": [item.strip() for item in (_env("AGENTCO_PROVIDER_HOST_ALLOWLIST") or "").split(",") if item.strip()],
        "request_timeout_seconds": float(_env("OPENAI_TIMEOUT_SECONDS") or "30"),
        "retry_limit": int(_env("OPENAI_MAX_RETRIES") or "2"),
        "concurrency_limit": int(_env("AGENTCO_PROVIDER_CONCURRENCY_LIMIT") or "1"),
        "token_budget": int(_env("AGENTCO_PROVIDER_TOKEN_BUDGET") or "24000"),
        "monetary_budget_usd": float(_env("AGENTCO_PROVIDER_MONETARY_BUDGET_USD") or "10.0"),
        "campaign_execution_budget": {
            "max_calls": int(_env("AGENTCO_PROVIDER_MAX_CALLS") or "24"),
            "max_retries_total": int(_env("AGENTCO_PROVIDER_MAX_RETRIES_TOTAL") or "48"),
        },
        "dns_resolution_policy": {
            "resolve_before_connect": True,
            "reject_forbidden_ranges": True,
            "fail_on_ambiguous_resolution": True,
        },
        "redirect_policy": {"enabled": False, "max_redirects": 0},
        "model_identity_verification_mode": _env("AGENTCO_MODEL_IDENTITY_MODE") or "strict_response_match_or_hold",
        "region_or_deployment": _env("OPENAI_DEPLOYMENT_REGION"),
    }


def _invalid_allowlist_entry(entry: str) -> bool:
    if not entry or entry in {"*", "*."}:
        return True
    if entry.startswith("*."):
        suffix = entry[2:]
        return not suffix or "*" in suffix or suffix.count(".") < 1
    return "*" in entry or "/" in entry or "://" in entry


def _resolved_addresses(host: str, port: int) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ReadinessError("dns_resolution_failed", f"provider host {host!r} could not be resolved") from exc
    addresses = sorted({info[4][0] for info in infos})
    if not addresses:
        raise ReadinessError("dns_resolution_empty", f"provider host {host!r} resolved to no addresses")
    return addresses


def _address_forbidden(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_provider_config(config: dict[str, Any], *, resolve_dns: bool = True) -> dict[str, Any]:
    schema_validate(PROVIDER_CONFIG_SCHEMA, config)
    failures: list[dict[str, str]] = []
    required = ["model_identifier", "api_base_url", "credential_reference"]
    for key in required:
        if not config.get(key):
            failures.append({"code": f"missing_{key}", "message": f"{key} is required"})
    if not config.get("provider_host_allowlist"):
        failures.append({"code": "missing_provider_host_allowlist", "message": "provider host allowlist is required"})
    for entry in config.get("provider_host_allowlist") or []:
        if _invalid_allowlist_entry(str(entry).strip()):
            failures.append({"code": "ambiguous_allowlist_entry", "message": f"ambiguous allowlist entry: {entry}"})
    if not isinstance(config.get("model_identifier"), str) or not (config.get("model_identifier") or "").strip():
        failures.append({"code": "invalid_model_identifier", "message": "model identifier must be a non-empty string"})
    for key in ["request_timeout_seconds", "retry_limit", "concurrency_limit", "token_budget", "monetary_budget_usd"]:
        value = config.get(key)
        if not isinstance(value, (int, float)) or value < 0:
            failures.append({"code": f"invalid_{key}", "message": f"{key} must be non-negative"})
    if config.get("redirect_policy", {}).get("enabled") is True:
        failures.append({"code": "redirects_not_permitted", "message": "real-provider readiness requires redirects disabled"})
    if config.get("request_timeout_seconds", 0) <= 0:
        failures.append({"code": "invalid_timeout", "message": "request timeout must be positive"})
    if config.get("retry_limit", 0) > config.get("campaign_execution_budget", {}).get("max_retries_total", 0):
        failures.append({"code": "conflicting_retry_budget", "message": "per-request retry limit exceeds campaign retry budget"})
    endpoint_identity: dict[str, Any] = {}
    url = config.get("api_base_url") or ""
    allowlist = config.get("provider_host_allowlist") or []
    if url and allowlist:
        try:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme != "https":
                raise ProviderConfigurationError("provider URL must use HTTPS for real-provider campaigns")
            if parsed.username or parsed.password:
                raise ProviderConfigurationError("provider URL must not include user-info")
            if not parsed.hostname:
                raise ProviderConfigurationError("provider URL must include hostname")
            if not _host_matches_allowlist(parsed.hostname, allowlist):
                raise ProviderConfigurationError("provider host is not allowlisted")
            endpoint_identity.update({"hostname": parsed.hostname, "scheme": parsed.scheme, "port": parsed.port or 443})
            if resolve_dns:
                addresses = _resolved_addresses(parsed.hostname, parsed.port or 443)
                endpoint_identity["resolved_addresses"] = addresses
                forbidden = [address for address in addresses if _address_forbidden(address)]
                if forbidden:
                    failures.append({"code": "forbidden_resolved_address", "message": f"provider host resolved to forbidden addresses: {forbidden}"})
        except (ProviderConfigurationError, ReadinessError, ValueError) as exc:
            failures.append({"code": "invalid_provider_endpoint", "message": str(exc)})
    status = "valid" if not failures else "invalid"
    result = {
        "status": status,
        "failure_codes": [failure["code"] for failure in failures],
        "failures": failures,
        "endpoint_identity": endpoint_identity,
        "configuration_hash": provider_config_hash(config),
        "secret_values_recorded": False,
    }
    return result


def provider_config_hash(config: dict[str, Any]) -> str:
    redacted = dict(config)
    redacted["credential_reference"] = config.get("credential_reference")
    return stable_hash(redacted)


def provider_preflight(config: dict[str, Any], *, resolve_dns: bool = True, allow_model_call: bool = False) -> dict[str, Any]:
    validation = validate_provider_config(config, resolve_dns=resolve_dns)
    model_call_allowed = allow_model_call or os.getenv("AGENTCO_PROVIDER_PREFLIGHT_ALLOW_MODEL_CALL") == "1"
    matrix = {
        "provider_name": config.get("provider_name"),
        "configuration_present": validation["status"] == "valid",
        "endpoint_valid": "invalid_provider_endpoint" not in validation["failure_codes"],
        "TLS_policy_valid": bool((config.get("api_base_url") or "").startswith("https://")),
        "host_allowlisted": "missing_provider_host_allowlist" not in validation["failure_codes"] and "invalid_provider_endpoint" not in validation["failure_codes"],
        "model_configured": bool(config.get("model_identifier")),
        "credentials_present": bool(config.get("credential_reference")),
        "network_check_permitted": resolve_dns,
        "provider_reachable": "not_verified",
        "model_access_verified": "not_verified",
        "model_call_allowed": model_call_allowed,
        "failure_codes": validation["failure_codes"],
        "configuration_hash": validation["configuration_hash"],
        "endpoint_identity": validation["endpoint_identity"],
    }
    if validation["status"] != "valid":
        status = "invalid_configuration"
    elif not model_call_allowed:
        status = "unavailable_external_verification"
    else:
        status = "ready_for_authorized_identity_check"
    matrix["provider_preflight"] = status
    matrix["execution_attempted"] = False
    schema_validate(PROVIDER_PREFLIGHT_SCHEMA, matrix)
    return matrix


def current_source_identity() -> dict[str, str]:
    return {"commit": git("rev-parse", "HEAD"), "tree": git("rev-parse", "HEAD^{tree}")}


def validate_authorization(authorization: dict[str, Any], config: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    schema_validate(AUTHORIZATION_SCHEMA, authorization)
    now = now or datetime.now(timezone.utc)
    source = current_source_identity()
    failures: list[dict[str, str]] = []
    if authorization.get("campaign_id") != GENESIS_IDENTITY:
        failures.append({"code": "campaign_mismatch", "message": "authorization campaign does not match Genesis V5"})
    if authorization.get("source_commit") != source["commit"]:
        failures.append({"code": "source_commit_mismatch", "message": "authorization source commit does not match current HEAD"})
    if authorization.get("source_tree") != source["tree"]:
        failures.append({"code": "source_tree_mismatch", "message": "authorization source tree does not match current tree"})
    if authorization.get("provider") != config.get("provider_name"):
        failures.append({"code": "provider_mismatch", "message": "authorization provider differs from configuration"})
    if authorization.get("model") != config.get("model_identifier"):
        failures.append({"code": "model_mismatch", "message": "authorization model differs from configuration"})
    if authorization.get("endpoint") != config.get("api_base_url"):
        failures.append({"code": "endpoint_mismatch", "message": "authorization endpoint differs from configuration"})
    expiry = datetime.fromisoformat(authorization["authorization_expiry"].replace("Z", "+00:00"))
    if expiry <= now:
        failures.append({"code": "authorization_expired", "message": "authorization has expired"})
    if authorization.get("maximum_calls", 0) > config.get("campaign_execution_budget", {}).get("max_calls", 0):
        failures.append({"code": "authorization_call_budget_exceeds_config", "message": "authorization calls exceed configured campaign budget"})
    if authorization.get("maximum_tokens", 0) > config.get("token_budget", 0):
        failures.append({"code": "authorization_token_budget_exceeds_config", "message": "authorization tokens exceed configured budget"})
    if authorization.get("maximum_cost_usd", 0) > config.get("monetary_budget_usd", 0):
        failures.append({"code": "authorization_cost_budget_exceeds_config", "message": "authorization cost exceeds configured budget"})
    if authorization.get("signature_required") and not authorization.get("signature"):
        failures.append({"code": "authorization_signature_missing", "message": "authorization requires a signature"})
    return {"status": "valid" if not failures else "invalid", "failure_codes": [f["code"] for f in failures], "failures": failures, "authorization_hash": stable_hash(authorization)}


def load_genesis_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for split in ["development", "validation", "hidden"]:
        for case in load_json(GENESIS_V5 / split / "cases.json"):
            enriched = dict(case)
            enriched["split"] = split
            cases.append(enriched)
    return cases


def genesis_case_manifest() -> dict[str, Any]:
    cases = load_genesis_cases()
    seen: set[str] = set()
    entries: list[dict[str, Any]] = []
    failures: list[str] = []
    for case in cases:
        case_id = case["case_id"]
        if case_id in seen:
            failures.append(f"duplicate case_id {case_id}")
        seen.add(case_id)
        provider_visible = {
            "case_id": case_id,
            "domain": case["domain"],
            "task": case.get("task") or case.get("request", {}).get("prompt"),
            "input": case.get("request"),
            "timeout": case.get("timeout"),
            "budget": case.get("budget"),
            "tool_permissions": case.get("tool_permissions", []),
            "external_data_policy": case.get("external_data_policy", "none"),
        }
        if "expected" in canonical_json(provider_visible).lower() or "api_key" in canonical_json(provider_visible).lower():
            failures.append(f"provider-visible forbidden field in {case_id}")
        entries.append({
            "case_id": case_id,
            "domain": case["domain"],
            "split": case["split"],
            "task": provider_visible["task"],
            "input_hash": stable_hash(provider_visible["input"]),
            "expected_output_form": case.get("expected_output_form") or case.get("domain"),
            "scoring_rubric": case.get("rubric_id"),
            "critical_failure_conditions": case.get("critical_failure_conditions", ["hidden leakage", "credential exposure", "unauthorized tool use"]),
            "timeout": provider_visible["timeout"],
            "maximum_tokens": (provider_visible["budget"] or {}).get("max_tokens"),
            "tool_permissions": provider_visible["tool_permissions"],
            "external_data_policy": provider_visible["external_data_policy"],
            "evaluator_requirements": {"rubric_id": case.get("rubric_id"), "scorer_id": case.get("scorer_id")},
            "evidence_requirements": ["provider_request_id", "redacted_request", "redacted_response", "budget_settlement", "evaluator_result"],
            "case_hash": stable_hash(provider_visible),
        })
    domains = sorted({entry["domain"] for entry in entries})
    manifest = {
        "manifest_id": "capability-genesis-v5-case-manifest-real-provider-readiness-v1",
        "genesis_campaign_id": GENESIS_IDENTITY,
        "protocol_identity": PROTOCOL_IDENTITY,
        "case_count": len(entries),
        "domains": domains,
        "cases": sorted(entries, key=lambda item: item["case_id"]),
        "validation_errors": failures,
    }
    manifest["case_manifest_hash"] = stable_hash({k: v for k, v in manifest.items() if k != "case_manifest_hash"})
    return manifest


def threshold_specification() -> dict[str, Any]:
    return {
        "decisions": ["REAL_CAPABILITY_BASELINE_ACCEPTED", "REAL_CAPABILITY_BASELINE_REJECTED", "HOLD_FOR_MORE_EVIDENCE", "INVALID_CAMPAIGN"],
        "status_classes": ["case_completed", "case_failed", "case_timed_out", "case_denied", "evidence_unavailable", "evaluator_unavailable", "invalid_response", "infrastructure_failure"],
        "minimums": {
            "executed_cases": 18,
            "completed_cases": 18,
            "supported_domains": 8,
            "capability_task_domains": 4,
            "aggregate_correctness": 0.70,
            "per_domain_correctness": 0.60,
            "schema_validity_rate": 1.0,
            "evidence_completeness_rate": 1.0,
            "evaluator_coverage_rate": 1.0,
            "cost_compliance_rate": 1.0,
            "latency_compliance_rate": 0.95,
        },
        "maximums": {"critical_failure_rate": 0.0, "timeout_rate": 0.10},
        "hold_policy": "HOLD_FOR_MORE_EVIDENCE is neither success nor failure and cannot establish supported domains or aggregate correctness.",
    }


def dry_run_result(config: dict[str, Any] | None = None) -> dict[str, Any]:
    source = current_source_identity()
    case_manifest = genesis_case_manifest()
    result = {
        "mode": "dry_run",
        "capability_effect": "none",
        "real_provider_execution": False,
        "source_commit": source["commit"],
        "source_tree": source["tree"],
        "planned_cases": 24,
        "simulated_reservations": 24,
        "simulated_evidence_records": 24,
        "mock_or_deterministic_outputs_count_as_capability": False,
        "case_manifest_hash": case_manifest["case_manifest_hash"],
        "provider_configuration_hash": provider_config_hash(config) if config else None,
    }
    result["semantic_hash"] = stable_hash(result)
    return result


def real_provider_hold_result(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or provider_config_from_env()
    preflight = provider_preflight(config, resolve_dns=False)
    return {
        "campaign_id": GENESIS_IDENTITY,
        "decision": "HOLD_FOR_MORE_EVIDENCE",
        "provider_preflight": preflight["provider_preflight"],
        "execution_attempted": False,
        "planned_executions": 24,
        "executed_cases": 0,
        "completed_cases": 0,
        "failed_cases": 0,
        "timed_out_cases": 0,
        "evidence_unavailable_cases": 24,
        "supported_domains": [],
        "aggregate_correctness": None,
        "provider_configuration_hash": preflight.get("configuration_hash"),
        "capability_claims_permitted": False,
    }


def budget_settlement_valid(record: dict[str, Any]) -> bool:
    reserved = float(record.get("reserved_amount", 0))
    consumed = float(record.get("consumed_amount", 0))
    released = float(record.get("released_amount", 0))
    return abs(reserved - consumed - released) < 1e-9 and float(record.get("unreleased_amount", 0)) == 0.0


def execution_evidence_example() -> dict[str, Any]:
    source = current_source_identity()
    evidence = {
        "campaign_id": GENESIS_IDENTITY,
        "case_id": "example",
        "attempt_id": "example-attempt",
        "source_commit": source["commit"],
        "source_tree": source["tree"],
        "provider": "openai_compatible",
        "model": "configured-model",
        "endpoint_identity": {"hostname": "api.example.test", "resolved_addresses": ["203.0.113.10"]},
        "request_timestamp": "2026-07-17T00:00:00Z",
        "response_timestamp": "2026-07-17T00:00:01Z",
        "latency_ms": 1000,
        "terminal_status": "evidence_unavailable",
        "redacted_request": {},
        "redacted_response": {},
        "provider_request_id": None,
        "token_usage": {},
        "cost": {},
        "retry_history": [],
        "timeout_history": [],
        "evaluator_result": None,
        "audit_references": [],
        "artifact_location": "artifacts/capability-runtime/governed-capability-genesis-v5",
    }
    evidence["semantic_hash"] = stable_hash({k: v for k, v in evidence.items() if k != "semantic_hash"})
    schema_validate(EXECUTION_EVIDENCE_SCHEMA, evidence)
    return evidence
