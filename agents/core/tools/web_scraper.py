"""
Web scraper tools for AgentCo.

fetch_page      — Fetch a URL with requests + BeautifulSoup.
find_resolvable_claims — Extract falsifiable claims from page text using the LLM.
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


def fetch_page(url: str, timeout: int = 10) -> dict[str, Any]:
    """
    Fetch a URL and return cleaned text.

    Returns:
        {url, title, text (<5000 chars), fetched_at, status_code}
        On error: {url, error, status_code}
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
            # RSS/Atom feed — extract all text from tags
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
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
                tag.decompose()
            title_el = soup.find("title")
            title_text = title_el.get_text(strip=True) if title_el else ""
            text = soup.get_text(separator=" ", strip=True)

        # Normalise whitespace and truncate
        text = re.sub(r"\s+", " ", text).strip()[:5000]

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
    """
    if not text or not text.strip():
        logger.warning("find_resolvable_claims: empty text for %s", source_url)
        return []

    if llm_client is None:
        # Build a minimal OpenAI client from env
        api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
        from openai import OpenAI
        llm_client = OpenAI(api_key=api_key, base_url=base_url)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    max_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    prompt = f"""You are a prediction-calibration assistant. Given news text, extract 3–5 specific,
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

        # Strip code fences if present
        raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()

        parsed = json.loads(raw)
        claims = parsed.get("claims", [])

        validated = []
        for c in claims:
            if not all(k in c for k in ("claim", "confidence", "resolution_url", "resolution_date", "domain")):
                continue
            # Clamp confidence
            c["confidence"] = max(0.0, min(1.0, float(c["confidence"])))
            # Ensure resolution_url is valid (fall back to source_url)
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
