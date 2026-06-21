"""Resolution Independence Engine.

This module is the production-facing source-independence check for calibration
resolution. It is deterministic and intentionally conservative: exact circular
sources and resolver/producer conflicts reject, while weaker ownership/domain
signals produce dispute-ready warnings.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


IGNORED_QUERY_PREFIXES = ("utm_",)
IGNORED_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
INTERNAL_SOURCE_MARKERS = (
    "self",
    "internal",
    "simulation",
    "agentco",
    "agentco_system",
    "twin",
    "sandbox",
)


@dataclass(frozen=True)
class SourceFingerprint:
    raw_url: str
    canonical_url: str
    domain: str
    normalized_domain: str
    content_hash: str | None
    fetched_at: datetime | None
    source_type: str | None
    publisher: str | None = None
    publisher_owner: str | None = None


@dataclass(frozen=True)
class IndependenceVerdict:
    independent: bool
    reason: str
    severity: Literal["pass", "warn", "reject"]
    claim_source: SourceFingerprint
    resolution_source: SourceFingerprint
    same_canonical_url: bool
    same_domain: bool
    same_content_hash: bool
    same_publisher_owner: bool | None
    resolver_conflict: bool


def canonical_source_url(url: str) -> str:
    """Return a canonical URL for exact same-source comparisons."""
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
    return urlparse((url or "").strip()).netloc.lower()


def normalize_domain(domain: str) -> str:
    domain = (domain or "").lower().strip(".")
    return domain[4:] if domain.startswith("www.") else domain


def stable_json_hash(value: object) -> str:
    payload = json.dumps(value or {}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def content_hash(content: str | bytes | None) -> str | None:
    if content is None:
        return None
    raw = content if isinstance(content, bytes) else content.encode()
    return hashlib.sha256(raw).hexdigest()


def source_fingerprint_hash(source: SourceFingerprint) -> str:
    return stable_json_hash(to_jsonable(asdict(source)))


def to_jsonable(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    return value


def build_source_fingerprint(
    raw_url: str | None,
    *,
    content_hash: str | None = None,
    fetched_at: datetime | None = None,
    source_type: str | None = None,
    publisher: str | None = None,
    publisher_owner: str | None = None,
) -> SourceFingerprint:
    raw = raw_url or ""
    canonical = canonical_source_url(raw) if raw else ""
    domain = source_domain(canonical)
    return SourceFingerprint(
        raw_url=raw,
        canonical_url=canonical,
        domain=domain,
        normalized_domain=normalize_domain(domain),
        content_hash=content_hash or None,
        fetched_at=fetched_at,
        source_type=source_type or None,
        publisher=publisher or None,
        publisher_owner=publisher_owner or None,
    )


def evaluate_resolution_independence(
    *,
    claim_source: SourceFingerprint,
    resolution_source: SourceFingerprint,
    producing_agent_id: str | None,
    resolver_id: str | None,
    resolver_type: str | None,
    production: bool = True,
) -> IndependenceVerdict:
    """Return an independence verdict with dispute-ready metadata."""
    same_canonical_url = bool(
        claim_source.canonical_url
        and resolution_source.canonical_url
        and claim_source.canonical_url == resolution_source.canonical_url
    )
    same_domain = bool(
        claim_source.normalized_domain
        and resolution_source.normalized_domain
        and claim_source.normalized_domain == resolution_source.normalized_domain
    )
    same_content_hash = bool(
        claim_source.content_hash
        and resolution_source.content_hash
        and claim_source.content_hash == resolution_source.content_hash
    )
    same_publisher_owner = None
    if claim_source.publisher_owner and resolution_source.publisher_owner:
        same_publisher_owner = claim_source.publisher_owner.lower() == resolution_source.publisher_owner.lower()
    resolver_conflict = bool(producing_agent_id and resolver_id and producing_agent_id == resolver_id)

    reason = "independent"
    severity: Literal["pass", "warn", "reject"] = "pass"
    independent = True

    if not resolution_source.raw_url:
        independent, severity, reason = False, "reject", "missing_resolution_source"
    elif production and not resolver_id:
        independent, severity, reason = False, "reject", "missing_resolver_identity"
    elif same_canonical_url:
        independent, severity, reason = False, "reject", "same_canonical_url"
    elif same_content_hash:
        independent, severity, reason = False, "reject", "same_content_hash"
    elif resolver_conflict:
        independent, severity, reason = False, "reject", "producer_resolver_conflict"
    elif _is_internal_source(resolution_source):
        independent, severity, reason = False, "reject", "internal_resolution_source"
    elif same_publisher_owner:
        severity, reason = "warn", "same_publisher_owner_requires_secondary_independent_source"
    elif same_domain:
        severity, reason = "warn", "same_domain_different_canonical_url"

    return IndependenceVerdict(
        independent=independent,
        reason=reason,
        severity=severity,
        claim_source=claim_source,
        resolution_source=resolution_source,
        same_canonical_url=same_canonical_url,
        same_domain=same_domain,
        same_content_hash=same_content_hash,
        same_publisher_owner=same_publisher_owner,
        resolver_conflict=resolver_conflict,
    )


def evidence_snapshot_hash(evidence: object) -> str:
    return stable_json_hash(evidence)


def verdict_to_dict(verdict: IndependenceVerdict) -> dict:
    return to_jsonable(asdict(verdict))  # type: ignore[return-value]


def _is_internal_source(source: SourceFingerprint) -> bool:
    haystack = " ".join(
        item.lower()
        for item in (
            source.raw_url,
            source.canonical_url,
            source.domain,
            source.source_type or "",
            source.publisher or "",
            source.publisher_owner or "",
        )
    )
    return any(marker in haystack for marker in INTERNAL_SOURCE_MARKERS)
