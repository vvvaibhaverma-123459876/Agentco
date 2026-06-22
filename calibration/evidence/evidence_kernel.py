from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


EvidenceQuality = Literal["REAL", "FIXTURE", "EXTERNAL-VALIDATED", "simulated", "unresolved"]
EvidenceDirection = Literal["supports", "refutes"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold().strip())


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SourceIdentity:
    canonical_uri: str
    domain: str
    independence_group: str


class SourceIndependenceEngine:
    """Canonical source-independence engine for Gate 2.

    It intentionally treats exact URL, same registered independence group, and
    declared derivative relationships as non-independent. This makes circular
    resolution mechanically impossible before any promotion logic runs.
    """

    def __init__(self) -> None:
        self._derivatives: dict[str, set[str]] = {}
        self._group_by_domain: dict[str, str] = {}

    def canonicalize_url(self, uri: str) -> str:
        parsed = urlparse(uri.strip())
        scheme = (parsed.scheme or "https").lower()
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = re.sub(r"/+", "/", parsed.path or "/")
        if path != "/":
            path = path.rstrip("/")
        query = urlencode(
            sorted(
                (k, v)
                for k, v in parse_qsl(parsed.query, keep_blank_values=True)
                if not k.lower().startswith("utm_")
            )
        )
        return urlunparse((scheme, netloc, path, "", query, ""))

    def identify(self, uri: str, independence_group: str | None = None) -> SourceIdentity:
        canonical = self.canonicalize_url(uri)
        domain = urlparse(canonical).netloc
        group = independence_group or self._group_by_domain.get(domain) or domain
        self._group_by_domain.setdefault(domain, group)
        return SourceIdentity(canonical, domain, group)

    def register_derivative(self, source_uri: str, derivative_uri: str) -> None:
        source = self.identify(source_uri).canonical_uri
        derivative = self.identify(derivative_uri).canonical_uri
        self._derivatives.setdefault(source, set()).add(derivative)
        self._derivatives.setdefault(derivative, set()).add(source)

    def independence_score(
        self,
        origin_uri: str,
        evidence_uri: str,
        *,
        origin_group: str | None = None,
        evidence_group: str | None = None,
    ) -> float:
        origin = self.identify(origin_uri, origin_group)
        evidence = self.identify(evidence_uri, evidence_group)
        if origin.canonical_uri == evidence.canonical_uri:
            return 0.0
        if evidence.canonical_uri in self._derivatives.get(origin.canonical_uri, set()):
            return 0.0
        if origin.independence_group == evidence.independence_group:
            return 0.0
        if origin.domain == evidence.domain:
            return 0.25
        return 1.0

    def is_independent(
        self,
        origin_uri: str,
        evidence_uri: str,
        *,
        origin_group: str | None = None,
        evidence_group: str | None = None,
        threshold: float = 0.7,
    ) -> bool:
        return (
            self.independence_score(
                origin_uri,
                evidence_uri,
                origin_group=origin_group,
                evidence_group=evidence_group,
            )
            >= threshold
        )


@dataclass
class Claim:
    claim_text: str
    source_uri: str
    source_type: str
    domain: str = "general"
    probability: float | None = None
    originating_agent: str | None = None
    claim_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    normalized_claim: str = field(init=False)
    evidence_status: str = "untrusted"
    promotion_status: str = "unpromoted"
    contradiction_set: set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        self.normalized_claim = _normalize_text(self.claim_text)


@dataclass
class EvidenceArtifact:
    claim_id: str
    source_uri: str
    source_type: str
    supports_or_refutes: EvidenceDirection
    strength: float
    evidence_quality: EvidenceQuality
    extraction_method: str
    raw_excerpt_or_pointer: str
    independence_group: str | None = None
    artifact_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content_hash: str = field(init=False)
    timestamp: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not 0 <= self.strength <= 1:
            raise ValueError("evidence strength must be between 0 and 1")
        self.content_hash = _hash(self.raw_excerpt_or_pointer)


@dataclass(frozen=True)
class PromotionDecision:
    allowed: bool
    reasons: tuple[str, ...]
    independence_score: float


@dataclass
class SourceReliability:
    source_id: str
    domain: str
    historical_claim_count: int = 0
    resolved_true_count: int = 0
    resolved_false_count: int = 0
    unresolved_count: int = 0
    contradiction_count: int = 0

    @property
    def calibration_score(self) -> float | None:
        resolved = self.resolved_true_count + self.resolved_false_count
        if resolved == 0:
            return None
        return self.resolved_true_count / resolved


class EvidenceKernel:
    def __init__(
        self,
        independence_engine: SourceIndependenceEngine | None = None,
        *,
        independence_threshold: float = 0.7,
        strength_threshold: float = 0.7,
    ) -> None:
        self.independence = independence_engine or SourceIndependenceEngine()
        self.independence_threshold = independence_threshold
        self.strength_threshold = strength_threshold
        self.claims: dict[str, Claim] = {}
        self.evidence: dict[str, EvidenceArtifact] = {}
        self.resolutions: dict[str, dict[str, object]] = {}
        self.sources: dict[str, SourceReliability] = {}

    def create_claim(
        self,
        claim_text: str,
        *,
        source_uri: str,
        source_type: str,
        domain: str = "general",
        probability: float | None = None,
        originating_agent: str | None = None,
    ) -> Claim:
        claim = Claim(
            claim_text=claim_text,
            source_uri=source_uri,
            source_type=source_type,
            domain=domain,
            probability=probability,
            originating_agent=originating_agent,
        )
        self.claims[claim.claim_id] = claim
        identity = self.independence.identify(source_uri)
        report = self.sources.setdefault(
            identity.canonical_uri,
            SourceReliability(source_id=identity.canonical_uri, domain=identity.domain),
        )
        report.historical_claim_count += 1
        report.unresolved_count += 1
        self._refresh_contradictions(claim)
        return claim

    def attach_evidence(
        self,
        claim_id: str,
        *,
        source_uri: str,
        source_type: str,
        supports_or_refutes: EvidenceDirection,
        strength: float,
        evidence_quality: EvidenceQuality,
        extraction_method: str = "manual",
        raw_excerpt_or_pointer: str = "",
        independence_group: str | None = None,
    ) -> EvidenceArtifact:
        if claim_id not in self.claims:
            raise KeyError(f"unknown claim_id: {claim_id}")
        artifact = EvidenceArtifact(
            claim_id=claim_id,
            source_uri=source_uri,
            source_type=source_type,
            supports_or_refutes=supports_or_refutes,
            strength=strength,
            evidence_quality=evidence_quality,
            extraction_method=extraction_method,
            raw_excerpt_or_pointer=raw_excerpt_or_pointer,
            independence_group=independence_group,
        )
        self.evidence[artifact.artifact_id] = artifact
        return artifact

    def resolve_claim(
        self,
        claim_id: str,
        *,
        outcome: str,
        resolver_uri: str,
        resolver_type: str,
        evidence_refs: list[str],
    ) -> dict[str, object]:
        claim = self.claims[claim_id]
        score = self.independence.independence_score(claim.source_uri, resolver_uri)
        if score < self.independence_threshold:
            raise ValueError("resolver source is not independent of claim source")
        if claim_id in self.resolutions:
            raise ValueError("claim resolution is write-once")
        resolution = {
            "claim_id": claim_id,
            "outcome": outcome,
            "resolver_type": resolver_type,
            "resolver_uri": resolver_uri,
            "independence_score": score,
            "evidence_refs": tuple(evidence_refs),
            "created_at": _now(),
        }
        self.resolutions[claim_id] = resolution
        identity = self.independence.identify(claim.source_uri)
        report = self.sources.setdefault(
            identity.canonical_uri,
            SourceReliability(source_id=identity.canonical_uri, domain=identity.domain),
        )
        report.unresolved_count = max(0, report.unresolved_count - 1)
        if outcome.casefold() in {"true", "passed", "correct"}:
            report.resolved_true_count += 1
        else:
            report.resolved_false_count += 1
        return resolution

    def promotion_decision(self, claim_id: str) -> PromotionDecision:
        claim = self.claims[claim_id]
        reasons: list[str] = []
        best_score = 0.0
        supporting = [
            item
            for item in self.evidence.values()
            if item.claim_id == claim_id and item.supports_or_refutes == "supports"
        ]
        refuting = [
            item
            for item in self.evidence.values()
            if item.claim_id == claim_id and item.supports_or_refutes == "refutes"
        ]
        if not supporting:
            reasons.append("no supporting evidence")
        if refuting or claim.contradiction_set:
            reasons.append("contradiction or refuting evidence present")
        for item in supporting:
            score = self.independence.independence_score(
                claim.source_uri,
                item.source_uri,
                evidence_group=item.independence_group,
            )
            best_score = max(best_score, score)
            if score < self.independence_threshold:
                reasons.append("supporting evidence is not source-independent")
            if item.evidence_quality in {"FIXTURE", "simulated", "unresolved"}:
                reasons.append(f"{item.evidence_quality} evidence cannot promote")
            if item.strength < self.strength_threshold:
                reasons.append("supporting evidence is below strength threshold")
        allowed = not reasons and best_score >= self.independence_threshold
        return PromotionDecision(allowed, tuple(sorted(set(reasons))), best_score)

    def promote_claim(self, claim_id: str) -> PromotionDecision:
        decision = self.promotion_decision(claim_id)
        claim = self.claims[claim_id]
        if decision.allowed:
            claim.evidence_status = "reality_validated"
            claim.promotion_status = "promoted"
        else:
            claim.promotion_status = "blocked"
        return decision

    def demote_claim(self, claim_id: str, reason: str = "manual") -> Claim:
        claim = self.claims[claim_id]
        claim.promotion_status = "demoted"
        claim.evidence_status = f"demoted:{reason}"
        return claim

    def list_claims(self) -> list[Claim]:
        return list(self.claims.values())

    def list_evidence(self, claim_id: str | None = None) -> list[EvidenceArtifact]:
        artifacts = list(self.evidence.values())
        if claim_id is not None:
            artifacts = [item for item in artifacts if item.claim_id == claim_id]
        return artifacts

    def list_contradictions(self, claim_id: str) -> list[Claim]:
        return [self.claims[item] for item in sorted(self.claims[claim_id].contradiction_set)]

    def claim_graph(self, claim_id: str) -> dict[str, object]:
        claim = self.claims[claim_id]
        return {
            "claim": claim,
            "evidence": self.list_evidence(claim_id),
            "contradictions": self.list_contradictions(claim_id),
            "resolution": self.resolutions.get(claim_id),
        }

    def source_reliability_report(self, source_uri: str | None = None) -> list[SourceReliability]:
        if source_uri is None:
            return list(self.sources.values())
        identity = self.independence.identify(source_uri)
        report = self.sources.get(identity.canonical_uri)
        return [report] if report else []

    def _refresh_contradictions(self, claim: Claim) -> None:
        normalized = claim.normalized_claim
        for other in self.claims.values():
            if other.claim_id == claim.claim_id:
                continue
            if self._contradicts(normalized, other.normalized_claim):
                claim.contradiction_set.add(other.claim_id)
                other.contradiction_set.add(claim.claim_id)

    @staticmethod
    def _contradicts(left: str, right: str) -> bool:
        negative_markers = ("not ", "never ", "no ")
        for marker in negative_markers:
            if left.replace(marker, "", 1) == right or right.replace(marker, "", 1) == left:
                return True
        return False
