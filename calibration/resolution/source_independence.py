"""Source-independence checks for verifiable calibration paths."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from calibration.resolution.independence_engine import (
    build_source_fingerprint,
    evaluate_resolution_independence,
    evidence_snapshot_hash,
)


class CircularResolutionError(ValueError):
    """Raised when a claim is resolved against the exact source it came from."""


@dataclass(frozen=True)
class SourceLineage:
    """Canonical source identity used for independence checks."""

    raw_url: str
    canonical_url: str
    domain: str
    owner: str
    fingerprint: str


@dataclass(frozen=True)
class IndependenceResult:
    status: str
    failure_reason: str = ""


def canonical_source_url(url: str) -> str:
    from calibration.resolution.independence_engine import canonical_source_url as _canonical
    return _canonical(url)


def source_domain(url: str) -> str:
    from calibration.resolution.independence_engine import source_domain as _domain
    return _domain(url)


def source_fingerprint(canonical_url: str, owner: str = "") -> str:
    payload = json.dumps(
        {"canonical_url": canonical_url, "owner": owner or ""},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def evidence_hash(evidence: object) -> str:
    return evidence_snapshot_hash(evidence)


def build_source_lineage(raw_url: str, owner: str = "") -> SourceLineage:
    canonical = canonical_source_url(raw_url)
    return SourceLineage(
        raw_url=raw_url or "",
        canonical_url=canonical,
        domain=source_domain(canonical),
        owner=owner or "",
        fingerprint=source_fingerprint(canonical, owner),
    )


def evaluate_independence(
    *,
    claim_source: SourceLineage,
    resolution_source: SourceLineage,
    producer_agent_id: str,
    resolver_id: str,
    outcome_available_at: datetime,
    resolved_at: datetime | None = None,
    dispute_status: str = "none",
    additional_independent_evidence: bool = False,
) -> IndependenceResult:
    """
    Evaluate hard independence invariants before scoring can update trust.

    Same-domain or same-owner resolution is allowed only when an additional
    independent evidence package is present. Exact same canonical URL is always
    rejected.
    """
    resolved_at = resolved_at or datetime.now(timezone.utc)
    if resolved_at < outcome_available_at:
        return IndependenceResult("rejected", "resolution_before_outcome_available")
    if dispute_status not in {"none", "resolved"}:
        return IndependenceResult("rejected", f"disputed_claim:{dispute_status}")
    verdict = evaluate_resolution_independence(
        claim_source=build_source_fingerprint(
            claim_source.raw_url,
            publisher_owner=claim_source.owner,
        ),
        resolution_source=build_source_fingerprint(
            resolution_source.raw_url,
            publisher_owner=resolution_source.owner,
        ),
        producing_agent_id=producer_agent_id,
        resolver_id=resolver_id,
        resolver_type=None,
        production=True,
    )
    if not verdict.independent:
        return IndependenceResult("rejected", verdict.reason)
    if verdict.severity == "warn" and not additional_independent_evidence:
        return IndependenceResult("rejected", verdict.reason)
    return IndependenceResult("accepted" if verdict.severity == "pass" else "warn")


def validate_independent_sources(claim_source_url: str, resolution_url: str) -> None:
    """
    Refuse exact same-URL verification.

    The product claim is not "the page repeats itself"; it is that an external
    check was performed. Same domain can be legitimate for some publications,
    but the exact same canonical URL is circular.
    """
    source = canonical_source_url(claim_source_url)
    resolution = canonical_source_url(resolution_url)
    if source and resolution and source == resolution:
        raise CircularResolutionError(
            f"circular resolution rejected: claim source and resolution source are the same URL ({source})"
        )
