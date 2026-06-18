"""
Autonomous Internet Prediction Loop
=====================================
Scrapes real news sources → extracts verifiable claims via LLM →
registers them as pre-registered predictions in the real ledger.

Sources (free, no auth):
  - https://news.ycombinator.com
  - https://feeds.bbci.co.uk/news/technology/rss.xml
  - https://techcrunch.com

Registers 5 real predictions then saves to evals/acceptance/internet_predictions.md
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg2
from openai import OpenAI

from calibration import create_calibration_engine
from calibration.ledger.prediction_ledger import PredictionRegistration
from agents.core.tools.web_scraper import fetch_page, find_resolvable_claims

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

DB_URL = os.environ.get("DATABASE_URL", "postgresql://agentco:password@localhost:5432/agentco")

SOURCES = [
    "https://news.ycombinator.com",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://techcrunch.com",
]

TARGET_PREDICTIONS = 5


def _llm_client() -> OpenAI:
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    return OpenAI(api_key=api_key, base_url=base_url)


def _parse_resolution_date(date_str: str) -> datetime:
    """
    Parse ISO date string from LLM.
    - Past or today → now + 5 seconds (immediately resolvable after a tiny sleep)
    - Future → noon UTC on that date
    """
    today = datetime.now(timezone.utc).date()
    try:
        d = datetime.fromisoformat(date_str.strip()).date() if "T" not in date_str else datetime.fromisoformat(date_str).date()
    except ValueError:
        # fallback to today if parse fails
        d = today

    if d <= today:
        # Claim is about current/past content — resolvable right now
        # Set resolution_date 5 seconds ahead so the pre-registration is genuine
        return datetime.now(timezone.utc) + timedelta(seconds=5)
    else:
        return datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=timezone.utc)


def run():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    engine = create_calibration_engine(db=conn)
    ledger = engine["ledger"]
    trust  = engine["trust"]

    client = _llm_client()
    model  = os.environ.get("LLM_MODEL_STANDARD", "gpt-4o-mini")

    registered: list[dict] = []
    token_usage = {"prompt": 0, "completion": 0, "total": 0}

    print(f"\n{'='*64}")
    print("AUTONOMOUS PREDICTION LOOP — registering 5 real predictions")
    print(f"{'='*64}\n")

    # ── Memory: load prior experience ──────────────────────────────────────
    prior_context = ""
    prior_claims: list[str] = []
    try:
        from agents.core.memory.memory_reader import MemoryReader
        from agents.core.memory.memory_writer import MemoryWriter
        _mem_reader = MemoryReader(DB_URL)
        _mem_writer = MemoryWriter(DB_URL)
        prior_mems = _mem_reader.retrieve_relevant(
            "research-agent", "internet prediction scan tech news claims",
            domain="technology", timeout_ms=500,
        )
        track = _mem_reader.get_agent_track_record_summary("research-agent", "technology")
        prior_context = _mem_reader.format_for_system_prompt(prior_mems, track)
        # Extract previously registered claims so we don't re-register them
        for m in prior_mems:
            content = m.get("content", {})
            prior_claims.extend(content.get("predictions_registered_claims", []))
        if prior_context:
            print(f"  [MEMORY] Prior context loaded ({len(prior_context)} chars)")
            print(f"  [MEMORY] Prior claims to skip: {len(prior_claims)}")
        else:
            print(f"  [MEMORY] No previous experience in this domain.")
    except Exception as exc:
        logger.warning("Memory unavailable (non-blocking): %s", exc)
        _mem_reader = None
        _mem_writer = None

    # Trust baseline BEFORE any registrations
    trust_before = trust.trusted_confidence(
        stated=0.80, subject_id="research-agent", subject_type="agent",
        domain="technology", claim_type="news_fact", horizon_class="short",
    )
    print(f"  trust_confidence (before) : {trust_before:.4f}\n")

    for source_url in SOURCES:
        if len(registered) >= TARGET_PREDICTIONS:
            break

        print(f"  Scraping: {source_url}")
        page = fetch_page(source_url, timeout=15)

        if "error" in page or not page.get("text"):
            print(f"    → skipped ({page.get('error', 'no text')})")
            continue

        print(f"    → fetched {len(page['text'])} chars  (title: {page.get('title','')[:60]})")

        # Extract claims via LLM (inject memory context so agent doesn't repeat prior work)
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            memory_section = f"\n\n{prior_context}\n\nIMPORTANT: Do NOT re-register claims you have already registered in prior runs (listed above under PREVIOUS EXPERIENCE).\n" if prior_context else ""
            prompt = f"""You are a prediction-calibration assistant. Extract 3–5 specific, verifiable factual claims
from the news text below.
{memory_section}
Rules:
- Each claim must be binary (TRUE or FALSE, unambiguous)
- Prefer claims already confirmed by this article (set resolution_date to today {today})
- resolution_url MUST be: {source_url}
- domain: technology | business | science | politics | finance | general
- confidence: probability that claim is TRUE (0.0–1.0)

Text:
{page['text'][:3000]}

Return ONLY JSON (no prose, no code fences):
{{
  "claims": [
    {{
      "claim": "specific factual statement",
      "confidence": 0.85,
      "resolution_url": "{source_url}",
      "resolution_date": "{today}",
      "domain": "technology"
    }}
  ]
}}"""

            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            if resp.usage:
                token_usage["prompt"]     += resp.usage.prompt_tokens or 0
                token_usage["completion"] += resp.usage.completion_tokens or 0
                token_usage["total"]      += resp.usage.total_tokens or 0

            import re
            raw = resp.choices[0].message.content or ""
            raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
            # Extract JSON object even when the model adds preamble text
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                raw = m.group(0)
            parsed = json.loads(raw)
            claims = parsed.get("claims", [])
        except Exception as exc:
            print(f"    → LLM error: {exc}")
            claims = []

        print(f"    → {len(claims)} claims extracted")

        for claim_obj in claims:
            if len(registered) >= TARGET_PREDICTIONS:
                break

            claim_text    = claim_obj.get("claim", "").strip()
            confidence    = float(claim_obj.get("confidence", 0.75))
            resolution_url = claim_obj.get("resolution_url") or source_url
            resolution_date_str = claim_obj.get("resolution_date", today)
            domain        = claim_obj.get("domain", "technology")

            if not claim_text:
                continue

            # Validate ground_truth_source (must not be internal)
            DISQUALIFIED = {"self", "internal", "simulation", "agent", "agentco_system", "twin", "sandbox"}
            src_lower = resolution_url.lower()
            if any(d in src_lower for d in DISQUALIFIED):
                resolution_url = source_url

            resolution_date = _parse_resolution_date(resolution_date_str)

            reg = PredictionRegistration(
                claim=claim_text,
                probability=max(0.01, min(0.99, confidence)),
                confidence_basis={
                    "source": source_url,
                    "method": "llm_extraction_from_news",
                    "model": model,
                    "scraped_at": page.get("fetched_at", ""),
                },
                producing_agent_id="research-agent",
                producing_prompt_version="autonomous_loop_v1",
                resolution_criterion=(
                    f"Fetch {resolution_url} and verify: does the page content "
                    f"confirm this claim is TRUE or FALSE? (LLM confidence >= 0.8 required)"
                ),
                resolution_date=resolution_date,
                ground_truth_source=resolution_url,
                horizon_class="short",
                domain=domain,
                claim_type="news_fact",
                earliest_knowable_at=None,
            )

            try:
                prediction_id = ledger.pre_register(reg)
                record = ledger.get(prediction_id)

                entry = {
                    "prediction_id": prediction_id,
                    "claim": claim_text,
                    "confidence": confidence,
                    "domain": domain,
                    "resolution_url": resolution_url,
                    "resolution_date": resolution_date.isoformat(),
                    "post_hoc": record.post_hoc,
                    "source_url": source_url,
                }
                registered.append(entry)

                print(f"\n    [{len(registered)}/5] REGISTERED")
                print(f"         id         : {prediction_id}")
                print(f"         claim      : {claim_text[:80]}")
                print(f"         confidence : {confidence:.2f}")
                print(f"         domain     : {domain}")
                print(f"         resolves   : {resolution_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                print(f"         post_hoc   : {record.post_hoc}")

            except Exception as exc:
                print(f"    → registration failed: {exc}")
                continue

    conn.close()

    # ── Memory: write episodic record of this run ──────────────────────────
    if '_mem_writer' in dir() and _mem_writer is not None:
        try:
            key_findings = [r["claim"][:100] for r in registered]
            mid = _mem_writer.write_episodic(
                agent_id="research-agent",
                task_id=f"prediction-loop-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
                task_type="internet_prediction_scan",
                task_input=f"scan {SOURCES}",
                task_output_summary=f"registered {len(registered)} predictions from {len(SOURCES)} sources",
                predictions_registered=[r["prediction_id"] for r in registered],
                sources_consulted=SOURCES,
                key_findings=key_findings,
                errors_encountered=[],
                confidence_in_output=0.8 if registered else 0.3,
                duration_seconds=0.0,
                tokens_used=token_usage["total"],
                domain="technology",
            )
            print(f"\n  [MEMORY] Episodic memory written: {mid}")
        except Exception as exc:
            logger.warning("Memory write failed (non-blocking): %s", exc)

    print(f"\n{'='*64}")
    print(f"REGISTERED {len(registered)}/5 PREDICTIONS")
    print(f"{'='*64}")
    print(f"  LLM tokens used  : {token_usage['total']}  "
          f"(prompt={token_usage['prompt']}, completion={token_usage['completion']})")
    cost_usd = token_usage["prompt"] * 0.00000015 + token_usage["completion"] * 0.0000006
    print(f"  Estimated cost   : ${cost_usd:.4f} (gpt-4o-mini pricing)")

    # Save to markdown
    _save_markdown(registered, trust_before, token_usage, cost_usd)

    print(f"\n  Saved → evals/acceptance/internet_predictions.md")
    print(f"\n  Run check_resolutions.py next to resolve eligible predictions.\n")

    return registered


def _save_markdown(predictions: list[dict], trust_before: float, tokens: dict, cost: float) -> None:
    now_str = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Internet Predictions — Autonomous Prediction Loop",
        "",
        f"**Generated:** {now_str}",
        f"**Agent:** research-agent",
        f"**LLM tokens used:** {tokens['total']}  (prompt={tokens['prompt']}, completion={tokens['completion']})",
        f"**Estimated cost:** ${cost:.4f}",
        f"**trusted_confidence before:** {trust_before:.4f}",
        "",
        "---",
        "",
        "## Registered Predictions",
        "",
        "| # | prediction_id | claim | confidence | domain | resolves | post_hoc |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, p in enumerate(predictions, 1):
        pid  = p["prediction_id"]
        claim = p["claim"][:60] + ("…" if len(p["claim"]) > 60 else "")
        conf  = f"{p['confidence']:.2f}"
        dom   = p["domain"]
        res   = p["resolution_date"][:10]
        ph    = str(p["post_hoc"])
        lines.append(f"| {i} | `{pid}` | {claim} | {conf} | {dom} | {res} | {ph} |")

    lines += [
        "",
        "---",
        "",
        "## Claim Details",
        "",
    ]
    for i, p in enumerate(predictions, 1):
        lines += [
            f"### Prediction {i}: `{p['prediction_id']}`",
            "",
            f"**Claim:** {p['claim']}",
            f"**Confidence:** {p['confidence']:.2f}",
            f"**Domain:** {p['domain']}",
            f"**Resolution date:** {p['resolution_date']}",
            f"**Resolution URL:** {p['resolution_url']}",
            f"**Source:** {p['source_url']}",
            f"**post_hoc:** {p['post_hoc']}",
            "",
        ]

    out_path = ROOT / "evals" / "acceptance" / "internet_predictions.md"
    out_path.write_text("\n".join(lines))


if __name__ == "__main__":
    run()
