"""Source-independence checks for verifiable calibration paths."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


IGNORED_QUERY_PREFIXES = ("utm_",)
IGNORED_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


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
    """Return a stable URL form suitable for same-source comparisons."""
    parsed = urlparse((url or "").strip())
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    query_items = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lower = key.lower()
        if lower in IGNORED_QUERY_KEYS or any(lower.startswith(p) for p in IGNORED_QUERY_PREFIXES):
            continue
        query_items.append((key, value))
    query = urlencode(sorted(query_items))
    return urlunparse((scheme, netloc, path, "", query, ""))


def source_domain(url: str) -> str:
    parsed = urlparse((url or "").strip())
    return parsed.netloc.lower()


def source_fingerprint(canonical_url: str, owner: str = "") -> str:
    payload = json.dumps(
        {"canonical_url": canonical_url, "owner": owner or ""},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def evidence_hash(evidence: object) -> str:
    payload = json.dumps(evidence or {}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


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
    if not claim_source.raw_url or not resolution_source.raw_url:
        return IndependenceResult("rejected", "missing_source_lineage")
    if claim_source.canonical_url == resolution_source.canonical_url:
        return IndependenceResult("rejected", "same_canonical_url")
    if producer_agent_id and resolver_id and producer_agent_id == resolver_id:
        return IndependenceResult("rejected", "producer_cannot_resolve_own_claim")
    if resolved_at < outcome_available_at:
        return IndependenceResult("rejected", "resolution_before_outcome_available")
    if dispute_status not in {"none", "resolved"}:
        return IndependenceResult("rejected", f"disputed_claim:{dispute_status}")
    same_domain = claim_source.domain and claim_source.domain == resolution_source.domain
    same_owner = claim_source.owner and claim_source.owner == resolution_source.owner
    if (same_domain or same_owner) and not additional_independent_evidence:
        return IndependenceResult("rejected", "same_domain_or_owner_requires_independent_evidence")
    return IndependenceResult("accepted")


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
