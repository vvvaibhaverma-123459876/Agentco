"""Source-independence checks for verifiable calibration paths."""
from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


IGNORED_QUERY_PREFIXES = ("utm_",)
IGNORED_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


class CircularResolutionError(ValueError):
    """Raised when a claim is resolved against the exact source it came from."""


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
