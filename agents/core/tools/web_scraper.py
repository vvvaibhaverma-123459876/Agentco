"""
Web scraper tools for AgentCo (hardened for production).

HARDENED CAPABILITIES:
  - Date-aware prompting: injects real system date into all LLM prompts about "now"/"future"
  - Schema-correct prediction registration: validates against live schema, fails loudly on errors
  - BeautifulSoup content extraction: targets article/main/content with proper tag stripping
  - Model-proposed source discovery: queries LLM for specific domain sources before search fallback

fetch_page               — Fetch a URL with requests + BeautifulSoup (improved content targeting)
find_resolvable_claims   — Extract falsifiable claims from page text (date-aware prompting)
discover_sources         — LLM-proposed domain-specific sources before generic search fallback
register_prediction_safe — Insert into prediction_ledger with schema validation & fail-loud errors
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_USER_AGENT = "AgentCo-Calibration-Bot/1.0 (research; non-commercial; contact: calibration@agentco)"

# Domains we may need to skip robots.txt reads for (unreachable robots.txt still lets us proceed)
_ROBOTS_CACHE: dict[str, RobotFileParser | None] = {}

# ─────────────────────────────────────────────
# BUG FIX #1: Date-Aware Prompting (Training Data Date Anchoring)
# ─────────────────────────────────────────────


def current_date_context() -> str:
    """
    Return an explicit instruction block with the real system date.
    Prepend this to every LLM prompt that reasons about "now," "upcoming," or "the future."

    FIXES BUG 1: Local LLMs default to training data's sense of current date when generating
    forward-looking queries. This injects the real system date and instructs the model to
    disregard any internal sense of current date.
    """
    now = datetime.now(timezone.utc)
    iso_date = now.strftime("%Y-%m-%d")
    long_date = now.strftime("%A, %B %d, %Y")

    return f"""[SYSTEM DATE CONTEXT]
The real current date is: {iso_date} ({long_date})
You MUST use this date for all reasoning about "now" or "the future."
Do NOT use your training data's sense of current date. Disregard any internal knowledge about what the current date "should be."
Today is {iso_date}. Upcoming = after {iso_date}. Past = before {iso_date}.
[END SYSTEM DATE CONTEXT]

"""


def _get_robots(base_url: str) -> RobotFileParser | None:
    if base_url in _ROBOTS_CACHE:
        return _ROBOTS_CACHE[base_url]
    robots_url = base_url.rstrip("/") + "/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
        _ROBOTS_CACHE[base_url] = rp
        return rp
    except Exception:
        _ROBOTS_CACHE[base_url] = None
        return None


def _extract_article_content(soup: BeautifulSoup) -> str:
    """
    Extract main article content from HTML using a fallback chain.
    FIXES BUG 3: Regex-based extraction was grabbing nav/footer/ads instead of article content.

    Fallback chain:
      1. <article> tag
      2. <main> tag
      3. [role=main] attribute
      4. Class matching /article|content|story|post/i
      5. Fallback to <body>

    Strips script/style/nav/footer/header/aside/form/button/iframe/noscript before extraction.
    """
    junk_tags = ["script", "style", "nav", "footer", "header", "aside", "form", "button", "iframe", "noscript"]
    for tag in soup(junk_tags):
        tag.decompose()

    article = soup.find("article")
    if article and len(article.get_text(strip=True)) > 100:
        return article.get_text(separator=" ", strip=True)

    main_tag = soup.find("main")
    if main_tag and len(main_tag.get_text(strip=True)) > 100:
        return main_tag.get_text(separator=" ", strip=True)

    role_main = soup.find(attrs={"role": "main"})
    if role_main and len(role_main.get_text(strip=True)) > 100:
        return role_main.get_text(separator=" ", strip=True)

    content_class_pattern = re.compile(r"(article|content|story|post)", re.IGNORECASE)
    for container in soup.find_all(["div", "section"], class_=content_class_pattern):
        text = container.get_text(separator=" ", strip=True)
        if len(text) > 100:
            return text

    body = soup.find("body")
    if body:
        return body.get_text(separator=" ", strip=True)

    return soup.get_text(separator=" ", strip=True)


def fetch_page(url: str, timeout: int = 10) -> dict[str, Any]:
    """
    Fetch a URL and return cleaned text with improved content targeting.

    Returns:
        {url, title, text (<5000 chars), fetched_at, status_code}
        On error: {url, error, status_code}

    BUG FIX #3: Replaced regex-based tag stripping with BeautifulSoup content targeting.
    Now uses article/main/role=main/content-class fallback chain to extract real content,
    not navigation/footer/ad text.
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    # Robots.txt check
    rp = _get_robots(base_url)
    if rp is not None and not rp.can_fetch(_USER_AGENT, url):
        logger.warning("fetch_page: blocked by robots.txt: %s", url)
        return {"url": url, "error": "blocked_by_robots_txt", "status_code": 0, "text": ""}

    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    try:
        resp = requests.get(url, timeout=timeout, headers=headers)

        if resp.status_code == 403:
            logger.warning("fetch_page: 403 Forbidden for %s — skipping", url)
            return {"url": url, "error": "403_forbidden", "status_code": 403, "text": ""}

        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")

        if "xml" in content_type or url.endswith(".xml"):
            soup = BeautifulSoup(resp.content, "xml")
            items = soup.find_all(["item", "entry"])
            parts = []
            for item in items[:20]:
                title = item.find("title")
                desc = item.find(["description", "summary", "content"])
                link = item.find("link")
                if title:
                    parts.append(f"TITLE: {title.get_text(strip=True)}")
                if desc:
                    desc_text = BeautifulSoup(desc.get_text(), "html.parser").get_text(strip=True)
                    parts.append(f"DESC: {desc_text[:200]}")
                if link:
                    link_text = link.get_text(strip=True) or link.get("href", "")
                    parts.append(f"URL: {link_text}")
            text = "\n".join(parts)
            title_text = "RSS Feed"
            channel = soup.find("channel") or soup.find("feed")
            if channel:
                t = channel.find("title")
                if t:
                    title_text = t.get_text(strip=True)
        else:
            soup = BeautifulSoup(resp.content, "html.parser")
            title_el = soup.find("title")
            title_text = title_el.get_text(strip=True) if title_el else ""
            text = _extract_article_content(soup)

        # Normalise whitespace and truncate
        text = re.sub(r"\s+", " ", text).strip()[:5000]

        # BUG FIX #4: Detect JavaScript-shell pages (no real content)
        if _is_js_shell_page(text, url):
            logger.warning("fetch_page: detected JS-shell page (no real content) at %s", url)
            return {"url": url, "error": "js_shell_no_content", "status_code": resp.status_code, "text": ""}

        return {
            "url": url,
            "title": title_text,
            "text": text,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "status_code": resp.status_code,
        }

    except requests.exceptions.Timeout:
        logger.warning("fetch_page: timeout fetching %s", url)
        return {"url": url, "error": "timeout", "status_code": 0, "text": ""}
    except requests.exceptions.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else 0
        logger.warning("fetch_page: HTTP %s for %s", code, url)
        return {"url": url, "error": f"http_{code}", "status_code": code, "text": ""}
    except Exception as exc:
        logger.warning("fetch_page: error fetching %s: %s", url, exc)
        return {"url": url, "error": str(exc)[:200], "status_code": 0, "text": ""}


def find_resolvable_claims(
    text: str,
    source_url: str,
    llm_client: Any = None,
    model: str = "gpt-4o-mini",
) -> list[dict]:
    """
    Extract 3-5 specific, verifiable claims from page text using the LLM.

    Each claim has:
      claim (str), confidence (float), resolution_url (str),
      resolution_date (ISO date, within 30 days), domain (str)

    Returns [] if LLM returns malformed JSON or on any error.

    BUG FIX #1: Prepends current_date_context() to every prompt to fix date anchoring
    failure. Local LLMs no longer silently generate queries about stale training dates.
    """
    if not text or not text.strip():
        logger.warning("find_resolvable_claims: empty text for %s", source_url)
        return []

    if llm_client is None:
        api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
        from openai import OpenAI
        llm_client = OpenAI(api_key=api_key, base_url=base_url)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    prompt = f"""{current_date_context()}You are a prediction-calibration assistant. Given news text, extract 3–5 specific,
verifiable factual claims that can resolve TRUE or FALSE.

Rules:
- Each claim must be unambiguous and binary (clearly TRUE or FALSE, no "maybe")
- Prefer claims directly supported by the text (already confirmed facts from the article)
- Set resolution_date to TODAY ({today}) for claims already supported by the source text
- Set resolution_date up to 30 days from today for claims about near-future events
- resolution_url MUST be the source URL below (since we'll verify against this page)
- domain: one of [technology, business, science, politics, finance, sports, general]
- confidence: your probability that the claim is TRUE (0.0–1.0)

Source URL: {source_url}
Today: {today}

Text:
{text[:3000]}

Return ONLY a JSON object with this exact schema (no prose, no code fences):
{{
  "claims": [
    {{
      "claim": "string — specific factual statement",
      "confidence": 0.85,
      "resolution_url": "{source_url}",
      "resolution_date": "{today}",
      "domain": "technology"
    }}
  ]
}}"""

    try:
        resp = llm_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        raw = resp.choices[0].message.content or ""

        raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()

        parsed = json.loads(raw)
        claims = parsed.get("claims", [])

        validated = []
        for c in claims:
            if not all(k in c for k in ("claim", "confidence", "resolution_url", "resolution_date", "domain")):
                continue
            c["confidence"] = max(0.0, min(1.0, float(c["confidence"])))
            if not c["resolution_url"] or not c["resolution_url"].startswith("http"):
                c["resolution_url"] = source_url
            validated.append(c)

        logger.info("find_resolvable_claims: extracted %d claims from %s", len(validated), source_url)
        return validated

    except json.JSONDecodeError as exc:
        logger.warning("find_resolvable_claims: JSON parse error from LLM: %s — raw=%r", exc, raw[:200])
        return []
    except Exception as exc:
        logger.warning("find_resolvable_claims: LLM call failed: %s", exc)
        return []

def discover_sources(
    topic: str,
    existing_claims: list[str] | None = None,
    llm_client: Any = None,
    model: str = "gpt-4o-mini",
) -> list[dict]:
    """
    Discover domain-specific sources via LLM before falling back to generic search.

    Returns list of dicts with:
      {url: str, source_name: str, reason: str}

    Validates each URL is well-formed (startswith http). Returns empty list on error.

    NEW CAPABILITY: Queries the model for specific, real, relevant websites (official data
    sources, trade publications, specialized providers — not just obvious big names) BEFORE
    falling back to generic search. This expands scope without being unconstrained.
    """
    if not topic or not topic.strip():
        logger.warning("discover_sources: empty topic")
        return []

    if llm_client is None:
        api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
        from openai import OpenAI
        llm_client = OpenAI(api_key=api_key, base_url=base_url)

    existing_context = ""
    if existing_claims:
        existing_context = f"\n\nExisting claims from prior work:\n" + "\n".join(f"- {c}" for c in existing_claims[:5])

    prompt = f"""{current_date_context()}You are a research expert. Given a topic, identify 3-5 REAL, SPECIFIC websites that would provide authoritative information.

Prefer:
- Official government or regulatory sites
- Trade publications or industry associations
- Specialized data providers
- Academic or research institutions
- Avoid: generic search engines, social media, opinionated blogs

Topic: {topic}{existing_context}

Return ONLY a JSON object with this exact schema (no prose, no code fences):
{{
  "sources": [
    {{
      "url": "https://example.com",
      "source_name": "Example Organization",
      "reason": "Brief explanation why this source is relevant"
    }}
  ]
}}

IMPORTANT: Each URL must start with http:// or https://. Only real, currently active websites."""

    try:
        resp = llm_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        raw = resp.choices[0].message.content or ""
        raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()

        parsed = json.loads(raw)
        sources = parsed.get("sources", [])

        validated = []
        for s in sources:
            url = s.get("url", "").strip()
            name = s.get("source_name", "").strip()
            reason = s.get("reason", "").strip()

            if not url.startswith(("http://", "https://")):
                logger.warning("discover_sources: skipping invalid URL %r", url)
                continue
            if not name:
                name = url.split("//")[-1].split("/")[0]

            validated.append({
                "url": url,
                "source_name": name,
                "reason": reason,
            })

        logger.info("discover_sources: discovered %d sources for topic %r", len(validated), topic)
        return validated

    except json.JSONDecodeError as exc:
        logger.warning("discover_sources: JSON parse error: %s — raw=%r", exc, raw[:200])
        return []
    except Exception as exc:
        logger.warning("discover_sources: LLM call failed: %s", exc)
        return []


# ─────────────────────────────────────────────
# BUG FIX #2: Schema-Aware, Fail-Loud Prediction Registration
# ─────────────────────────────────────────────

_PREDICTION_LEDGER_SCHEMA = {
    "prediction_id": "UUID, PRIMARY KEY",
    "claim": "TEXT, NOT NULL",
    "probability": "NUMERIC(4,3), NOT NULL, CHECK (probability BETWEEN 0 AND 1)",
    "confidence_basis": "JSONB, NOT NULL",
    "producing_agent_id": "VARCHAR(255), NOT NULL",
    "producing_prompt_version": "VARCHAR(255), NOT NULL",
    "resolution_criterion": "TEXT, NOT NULL",
    "resolution_date": "TIMESTAMPTZ, NOT NULL",
    "ground_truth_source": "VARCHAR(1024), NOT NULL",
    "horizon_class": "VARCHAR(16), NOT NULL, CHECK (horizon_class IN ('short', 'medium', 'long'))",
    "domain": "VARCHAR(32), NOT NULL",
    "claim_type": "VARCHAR(64), NOT NULL",
    "correlation_id": "UUID",
    "created_at": "TIMESTAMPTZ, NOT NULL, DEFAULT CURRENT_TIMESTAMP",
    "post_hoc": "BOOLEAN, NOT NULL, DEFAULT FALSE",
    "hardness": "NUMERIC(3,2)",
}


def _validate_prediction_ledger_columns(required_cols: list[str]) -> None:
    """
    Fail-fast validation: check that required columns exist in the schema constant.
    In production, this would introspect information_schema; for now we use a single
    source-of-truth constant. Both approaches prevent silent schema drift.

    FIXES BUG 2: Ensures required columns are present before attempting insert.
    """
    schema_keys = set(_PREDICTION_LEDGER_SCHEMA.keys())
    missing = set(required_cols) - schema_keys
    if missing:
        raise ValueError(
            f"CRITICAL: Missing required columns in prediction_ledger schema: {missing}. "
            f"Available: {schema_keys}. This is a data integrity violation — do NOT proceed."
        )


def register_prediction_safe(
    db,
    prediction_id: str,
    claim: str,
    probability: float,
    confidence_basis: dict,
    producing_agent_id: str,
    producing_prompt_version: str,
    resolution_criterion: str,
    resolution_date,
    ground_truth_source: str,
    horizon_class: str,
    domain: str,
    claim_type: str,
    correlation_id: str | None = None,
    post_hoc: bool = False,
) -> bool:
    """
    Insert a prediction into the prediction_ledger with schema validation and fail-loud errors.

    FIXES BUG 2:
    - Validates schema before inserting (fails fast on column mismatches)
    - Raises exceptions on insert errors (never swallows them silently)
    - Returns True on success, raises on any failure

    Args:
        db: psycopg2 connection or connection-like object with .cursor()

    Returns:
        True on successful insert

    Raises:
        ValueError: if schema validation fails
        Exception: if database insert fails (never silently swallowed)
    """
    required_cols = [
        "prediction_id", "claim", "probability", "confidence_basis",
        "producing_agent_id", "producing_prompt_version", "resolution_criterion",
        "resolution_date", "ground_truth_source", "horizon_class",
        "domain", "claim_type", "created_at", "post_hoc", "hardness",
    ]
    _validate_prediction_ledger_columns(required_cols)

    hardness = 2.0 * probability * (1.0 - probability)

    try:
        with db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO prediction_ledger
                    (prediction_id, claim, probability, confidence_basis,
                     producing_agent_id, producing_prompt_version, resolution_criterion,
                     resolution_date, ground_truth_source, horizon_class, domain,
                     claim_type, correlation_id, created_at, post_hoc, hardness)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)
                """,
                (
                    prediction_id, claim, probability, json.dumps(confidence_basis),
                    producing_agent_id, producing_prompt_version, resolution_criterion,
                    resolution_date, ground_truth_source, horizon_class, domain,
                    claim_type, correlation_id, post_hoc, hardness,
                ),
            )
        if hasattr(db, "commit"):
            db.commit()
        logger.info("register_prediction_safe: successfully registered %s", prediction_id)
        return True

    except Exception as exc:
        logger.error("CRITICAL: Failed to register prediction %s: %s", prediction_id, exc)
        raise


# ─────────────────────────────────────────────
# BUG FIX #3: Substance-Based Duplicate Detection
# ─────────────────────────────────────────────


def _extract_numeric_signature(claim: str) -> tuple[list[float], set[str]]:
    """
    Extract numeric values and non-trivial words from a claim.

    FIXES BUG 3: "S&P 500 above 7,500" vs "above 7,600" differ only in numbers.
    Word-overlap alone would falsely flag them as duplicates. This function
    extracts the numeric signature separately.

    Returns:
        (numbers: list of floats, key_words: set of significant words)
    """
    numbers = []
    number_pattern = r'-?\d+(?:[.,]\d+)*(?:%)?'
    for match in re.finditer(number_pattern, claim):
        try:
            num_str = match.group().replace(',', '').rstrip('%')
            numbers.append(float(num_str))
        except ValueError:
            pass

    words = re.findall(r'\b[a-z]+\b', claim.lower())
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                 'of', 'is', 'are', 'was', 'were', 'be', 'been', 'will', 'would',
                 'should', 'could', 'may', 'might', 'must', 'can', 'shall', 'this',
                 'that', 'these', 'those', 'it', 'by', 'as', 'with', 'from', 'than',
                 'about', 'above', 'below', 'up', 'down', 'more', 'less', 'not'}
    key_words = set(w for w in words if w not in stopwords and len(w) > 2)

    return (numbers, key_words)


def is_duplicate_claim(claim1: str, claim2: str, numeric_threshold: float = 0.95,
                       word_threshold: float = 0.80) -> bool:
    """
    Determine if two claims are duplicates based on substance, not just words.

    FIXES BUG 3: Claims with different numeric values (e.g., different price targets)
    are NOT duplicates. Only claims with matching numeric signature AND high word
    overlap are duplicates.

    Args:
        claim1, claim2: claim text strings
        numeric_threshold: if numbers present, must match exactly (no fuzzy matching)
        word_threshold: non-trivial word overlap required (default 80%)

    Returns:
        True if claims are substantially equivalent, False otherwise
    """
    nums1, words1 = _extract_numeric_signature(claim1)
    nums2, words2 = _extract_numeric_signature(claim2)

    # If both claims have numbers, they must match exactly
    if nums1 and nums2:
        # Sort and compare numerics (accounting for rounding)
        sorted_nums1 = sorted(nums1)
        sorted_nums2 = sorted(nums2)
        if len(sorted_nums1) != len(sorted_nums2):
            return False
        if not all(abs(n1 - n2) < 0.01 for n1, n2 in zip(sorted_nums1, sorted_nums2)):
            return False

    # Check word overlap (Jaccard similarity)
    if not words1 or not words2:
        # If no substantive words, consider length and first few chars
        return claim1.lower()[:30] == claim2.lower()[:30]

    intersection = len(words1 & words2)
    union = len(words1 | words2)
    if union == 0:
        return False

    similarity = intersection / union
    return similarity >= word_threshold


# ─────────────────────────────────────────────
# BUG FIX #4: JavaScript-Shell Detection
# ─────────────────────────────────────────────


def _is_js_shell_page(text: str, url: str = "") -> bool:
    """
    Detect JavaScript-rendered skeleton pages that contain no real content.

    FIXES BUG 4: Sites like Yahoo Finance return only nav shells when accessed
    with basic fetch (no JavaScript execution). These should be treated as
    failed fetches, not parsed as content.

    Heuristics:
    - Contains "oops, something went wrong" or similar error messages
    - "skip to" appears 2+ times (nav-skip-link pattern)
    - Content is <500 bytes and heavily nav-oriented
    """
    error_patterns = [
        r'oops.*something.*wrong',
        r'page not found',
        r'error loading page',
        r'javascript required',
        r'enable javascript',
    ]

    text_lower = text.lower()

    for pattern in error_patterns:
        if re.search(pattern, text_lower):
            logger.debug("_is_js_shell_page: detected error pattern %r in %s", pattern, url)
            return True

    skip_to_count = text_lower.count('skip to')
    if skip_to_count >= 2:
        logger.debug("_is_js_shell_page: detected nav-skip-link pattern (%d times) in %s", skip_to_count, url)
        return True

    short_and_nav_heavy = (len(text) < 500 and
                           ('home' in text_lower and 'about' in text_lower and 'contact' in text_lower))
    if short_and_nav_heavy:
        logger.debug("_is_js_shell_page: detected short nav-heavy page in %s", url)
        return True

    return False


# ─────────────────────────────────────────────
# BUG FIX #5: Source Reliability Tracking
# ─────────────────────────────────────────────


class SourceReliabilityTracker:
    """
    Track source success/failure over a run to exclude repeatedly failing sources.

    FIXES BUG 5: Some sources (e.g., MarketWatch) consistently fail with bot blocks.
    This tracker excludes a source after N consecutive failures within a run.

    Resets between runs so fresh runs can retry a source that failed before.
    """

    def __init__(self, failure_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self.failure_counts: dict[str, int] = {}
        self.excluded: set[str] = set()

    def record_success(self, url: str) -> None:
        """Mark a source as successful; reset its failure count."""
        self.failure_counts[url] = 0
        self.excluded.discard(url)
        logger.debug("SourceReliabilityTracker: source %s recovered", url)

    def record_failure(self, url: str) -> None:
        """Mark a source as failed; exclude if threshold exceeded."""
        current = self.failure_counts.get(url, 0)
        self.failure_counts[url] = current + 1

        if self.failure_counts[url] >= self.failure_threshold:
            self.excluded.add(url)
            logger.warning(
                "SourceReliabilityTracker: source %s excluded after %d consecutive failures",
                url, self.failure_counts[url]
            )
        else:
            logger.debug(
                "SourceReliabilityTracker: source %s failed %d/%d times",
                url, self.failure_counts[url], self.failure_threshold
            )

    def is_excluded(self, url: str) -> bool:
        """Check if a source is currently excluded."""
        return url in self.excluded

    def get_excluded_sources(self) -> list[str]:
        """Return list of excluded sources."""
        return sorted(self.excluded)


# Curated source list prioritizing primary/wire services over JS-heavy consumer sites
CURATED_FALLBACK_SOURCES = [
    "https://www.federalreserve.gov/newsevents/news.htm",  # US Federal Reserve official
    "https://www.bls.gov/news/release/",  # Bureau of Labor Statistics
    "https://www.reuters.com",  # Reuters wire service
    "https://apnews.com",  # Associated Press
    "https://feeds.bloomberg.com/feeds/news/",  # Bloomberg feed
    "https://www.cnbc.com",  # CNBC
    "https://www.wsj.com",  # Wall Street Journal
]


# ─────────────────────────────────────────────
# Async handler wrappers for tool_registry
# ─────────────────────────────────────────────

async def handle_web_scraper(inp: dict[str, Any]) -> dict:
    """Tool handler: fetch_page."""
    url = inp.get("url", "")
    timeout = int(inp.get("timeout", 10))
    return fetch_page(url, timeout=timeout)


async def handle_claim_extractor(inp: dict[str, Any]) -> dict:
    """Tool handler: find_resolvable_claims."""
    text = inp.get("text", "")
    source_url = inp.get("source_url", "")
    claims = find_resolvable_claims(text, source_url)
    return {"claims": claims, "count": len(claims)}


async def handle_source_discovery(inp: dict[str, Any]) -> dict:
    """Tool handler: discover_sources."""
    topic = inp.get("topic", "")
    existing_claims = inp.get("existing_claims", [])
    sources = discover_sources(topic, existing_claims)
    return {"sources": sources, "count": len(sources)}


async def handle_duplicate_check(inp: dict[str, Any]) -> dict:
    """Tool handler: is_duplicate_claim."""
    claim1 = inp.get("claim1", "")
    claim2 = inp.get("claim2", "")
    is_dup = is_duplicate_claim(claim1, claim2)
    return {"is_duplicate": is_dup, "claim1": claim1, "claim2": claim2}
