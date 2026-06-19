"""
Web scraper tool for AgentCo agents.

Fixes three production bugs:
  Bug 1 - Date anchoring: LLMs default to training-era dates; every prompt now
           receives the real system date via current_date_context().
  Bug 2 - Schema mismatch: registration uses exact prediction_ledger column names
           and raises immediately on any DB error — never swallows.
  Bug 3 - Regex HTML extraction: replaced with BeautifulSoup; strips nav/footer/
           header/aside/script/style and walks article → main → role=main →
           .content-class → body fallback chain.

New capability:
  discover_sources() — model proposes up to 5 real URLs before generic search.
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Date context helper (Bug 1 fix)
# ---------------------------------------------------------------------------

def current_date_context() -> str:
    """Return a short string that anchors LLM prompts to today's real date."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"Today's date is {today} (UTC). Use this date — not your training data — for all temporal reasoning."


# ---------------------------------------------------------------------------
# HTML content extraction (Bug 3 fix)
# ---------------------------------------------------------------------------

_NOISE_TAGS = {"script", "style", "nav", "footer", "header", "aside"}
_CONTENT_CLASS_RE = re.compile(r"\b(article|content|main|post|entry|body)\b", re.I)


def _strip_noise(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()


def fetch_page(url: str, timeout: int = 15) -> str:
    """
    Fetch a URL and return its main text content.

    Extraction order:
      1. <article>
      2. <main>
      3. element with role="main"
      4. element whose class matches content-like pattern
      5. <body> fallback
    Returns empty string on network error (caller decides how to handle).
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; AgentCo/1.0; +https://agentco.ai)"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException:
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")
    _strip_noise(soup)

    container = (
        soup.find("article")
        or soup.find("main")
        or soup.find(attrs={"role": "main"})
        or next(
            (
                el
                for el in soup.find_all(True)
                if el.get("class")
                and any(_CONTENT_CLASS_RE.search(c) for c in el.get("class", []))
            ),
            None,
        )
        or soup.find("body")
    )

    if container is None:
        return soup.get_text(" ", strip=True)

    return container.get_text(" ", strip=True)


# ---------------------------------------------------------------------------
# Schema-correct prediction registration (Bug 2 fix)
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = {
    "claim",
    "probability",
    "confidence_basis",
    "producing_agent_id",
    "producing_prompt_version",
    "resolution_criterion",
    "resolution_date",
    "ground_truth_source",
    "horizon_class",
    "domain",
}


def register_prediction(record: dict[str, Any]) -> str:
    """
    Insert one row into prediction_ledger using exact column names.

    Required keys in *record*:
        claim, probability, confidence_basis, producing_agent_id,
        producing_prompt_version, resolution_criterion, resolution_date,
        ground_truth_source, horizon_class, domain

    Optional keys:
        claim_type (default "general"), correlation_id, post_hoc (default False)

    Returns the new prediction_id (UUID string).
    Raises ValueError for missing keys; raises psycopg2 errors for DB failures —
    never swallows any error.
    """
    missing = _REQUIRED_FIELDS - record.keys()
    if missing:
        raise ValueError(f"register_prediction: missing required fields: {sorted(missing)}")

    prediction_id = str(uuid.uuid4())
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set — cannot register prediction")

    sql = """
        INSERT INTO prediction_ledger (
            prediction_id,
            claim,
            probability,
            confidence_basis,
            producing_agent_id,
            producing_prompt_version,
            resolution_criterion,
            resolution_date,
            ground_truth_source,
            horizon_class,
            domain,
            claim_type,
            correlation_id,
            post_hoc
        ) VALUES (
            %(prediction_id)s,
            %(claim)s,
            %(probability)s,
            %(confidence_basis)s,
            %(producing_agent_id)s,
            %(producing_prompt_version)s,
            %(resolution_criterion)s,
            %(resolution_date)s,
            %(ground_truth_source)s,
            %(horizon_class)s,
            %(domain)s,
            %(claim_type)s,
            %(correlation_id)s,
            %(post_hoc)s
        )
    """
    params = {
        **record,
        "prediction_id": prediction_id,
        "claim_type": record.get("claim_type", "general"),
        "correlation_id": record.get("correlation_id"),
        "post_hoc": record.get("post_hoc", False),
    }

    import json as _json

    # psycopg2 needs JSONB as a string
    if isinstance(params.get("confidence_basis"), dict):
        params["confidence_basis"] = _json.dumps(params["confidence_basis"])

    conn = psycopg2.connect(db_url)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
    finally:
        conn.close()

    return prediction_id


# ---------------------------------------------------------------------------
# Source discovery (new capability)
# ---------------------------------------------------------------------------

def discover_sources(
    topic: str,
    existing_claims: list[str] | None = None,
    llm_client: Any = None,
    model: str = "gpt-4o-mini",
    max_sources: int = 5,
) -> list[str]:
    """
    Ask the LLM to propose up to *max_sources* real, checkable URLs for *topic*.

    Injects current_date_context() so the model reasons about live sources, not
    training-era archives.  The model is instructed to return one URL per line
    and nothing else.

    Returns a list of URLs (may be empty if the model returns nothing useful or
    if no llm_client is provided).
    """
    if llm_client is None:
        return []

    date_ctx = current_date_context()
    existing_note = ""
    if existing_claims:
        snippet = "; ".join(existing_claims[:3])
        existing_note = f"\nExisting claims to cross-check: {snippet}"

    prompt = (
        f"{date_ctx}\n\n"
        f"You are a research assistant. Propose up to {max_sources} real, publicly "
        f"accessible URLs that would contain reliable, current information about:\n\n"
        f"  {topic}{existing_note}\n\n"
        "Requirements:\n"
        "- Each URL must be a real page that exists today.\n"
        "- Prefer primary sources (official sites, peer-reviewed papers, government data).\n"
        "- Output ONLY the URLs, one per line, no explanations, no markdown.\n"
        f"- Maximum {max_sources} URLs."
    )

    try:
        resp = llm_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300,
        )
        raw = resp.choices[0].message.content or ""
    except Exception:
        return []

    urls: list[str] = []
    for line in raw.splitlines():
        line = line.strip().lstrip("•-*0123456789. ")
        if line.startswith("http://") or line.startswith("https://"):
            urls.append(line)
        if len(urls) >= max_sources:
            break

    return urls
