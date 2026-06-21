"""
Resolution Checker
==================
For each unresolved prediction in the ledger whose resolution_date has passed:
  1. Fetch the resolution_url
  2. Ask LLM: does the page confirm the claim TRUE or FALSE?
  3. If LLM confidence >= 0.8: resolve in ledger (scores it)
  4. If LLM confidence < 0.8: mark as needs_human_review
  5. Update TrustController for research-agent
  6. Print before/after trusted_confidence
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg2
from openai import OpenAI

from calibration import create_calibration_engine
from calibration.resolution.source_independence import (
    CircularResolutionError,
    validate_independent_sources,
)
from agents.core.tools.web_scraper import fetch_page

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

DB_URL = os.environ.get("DATABASE_URL", "postgresql://agentco:password@localhost:5432/agentco")


def _llm_client() -> OpenAI:
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    return OpenAI(api_key=api_key, base_url=base_url)


def _check_claim_against_page(
    claim: str,
    page_text: str,
    client: OpenAI,
    model: str,
) -> dict:
    """
    Ask the LLM whether page_text confirms the claim TRUE or FALSE.
    Returns {outcome: bool, confidence: float, evidence: str}
    or {outcome: None, confidence: 0.0, evidence: str} if undecidable.
    """
    prompt = f"""You are a fact-checker. Given a claim and page text, determine if the claim is TRUE or FALSE.

Claim: {claim}

Page text (truncated to 3000 chars):
{page_text[:3000]}

Rules:
- Return TRUE only if the page explicitly confirms the claim
- Return FALSE only if the page explicitly contradicts the claim
- If the page does not address the claim, set confidence to 0.0
- evidence: one sentence explaining your decision

Return ONLY JSON (no prose, no code fences):
{{
  "outcome": true,
  "confidence": 0.85,
  "evidence": "The page states that..."
}}"""

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        raw = resp.choices[0].message.content or ""
        raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        parsed = json.loads(raw)
        return {
            "outcome": bool(parsed.get("outcome", False)),
            "confidence": float(parsed.get("confidence", 0.0)),
            "evidence": str(parsed.get("evidence", "")),
            "usage": resp.usage,
        }
    except Exception as exc:
        return {
            "outcome": None,
            "confidence": 0.0,
            "evidence": f"LLM error: {exc}",
            "usage": None,
        }


def run(agent_filter: str = "research-agent", min_confidence: float = 0.8):
    main_conn = psycopg2.connect(DB_URL)
    main_conn.autocommit = True

    svc_conn = psycopg2.connect(DB_URL)
    svc_conn.autocommit = True
    with svc_conn.cursor() as cur:
        cur.execute("SET ROLE resolution_service;")

    engine   = create_calibration_engine(db=main_conn)
    ledger   = engine["ledger"]
    resolution_svc = engine["resolution"]
    trust    = engine["trust"]

    client = _llm_client()
    model  = os.environ.get("LLM_MODEL_STANDARD", "gpt-4o-mini")

    now = datetime.now(timezone.utc)

    # All unresolved predictions
    all_unresolved = ledger.list_unresolved()
    agent_preds = [p for p in all_unresolved if p.producing_agent_id == agent_filter]
    eligible    = [p for p in agent_preds if p.resolution_date <= now]
    pending     = [p for p in agent_preds if p.resolution_date > now]

    print(f"\n{'='*64}")
    print(f"RESOLUTION CHECKER  —  {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*64}")
    print(f"  Unresolved predictions for {agent_filter!r}: {len(agent_preds)}")
    print(f"  Eligible (resolution_date <= now)          : {len(eligible)}")
    print(f"  Still pending (resolution_date in future)  : {len(pending)}")

    trust_before = trust.trusted_confidence(
        stated=0.80, subject_id=agent_filter, subject_type="agent",
        domain="technology", claim_type="news_fact", horizon_class="short",
    )
    print(f"\n  trust_confidence BEFORE : {trust_before:.4f}\n")

    token_usage = {"prompt": 0, "completion": 0, "total": 0}
    results: list[dict] = []

    for pred in eligible:
        print(f"  Checking: {pred.prediction_id[:8]}… — {pred.claim[:70]}")
        resolution_url = pred.ground_truth_source
        claim_source_url = ""
        if isinstance(pred.confidence_basis, dict):
            claim_source_url = str(pred.confidence_basis.get("source") or "")

        try:
            validate_independent_sources(claim_source_url, resolution_url)
        except CircularResolutionError as exc:
            print(f"    → circular_resolution_rejected: {exc}")
            results.append({
                "prediction_id": pred.prediction_id,
                "claim": pred.claim,
                "stated_confidence": pred.probability,
                "outcome": None,
                "llm_confidence": 0.0,
                "evidence": str(exc),
                "resolved": False,
                "status": "circular_resolution_rejected",
                "log_score": None,
                "brier_score": None,
            })
            continue

        # Fetch resolution URL
        page = fetch_page(resolution_url, timeout=15)
        if "error" in page or not page.get("text"):
            print(f"    → page fetch failed ({page.get('error', 'no text')}) — skipping")
            results.append({
                "prediction_id": pred.prediction_id,
                "claim": pred.claim,
                "stated_confidence": pred.probability,
                "outcome": None,
                "llm_confidence": 0.0,
                "evidence": f"page_fetch_failed: {page.get('error', '')}",
                "resolved": False,
                "status": "fetch_failed",
                "log_score": None,
                "brier_score": None,
            })
            continue

        verdict = _check_claim_against_page(pred.claim, page["text"], client, model)
        if verdict["usage"]:
            token_usage["prompt"]     += verdict["usage"].prompt_tokens or 0
            token_usage["completion"] += verdict["usage"].completion_tokens or 0
            token_usage["total"]      += verdict["usage"].total_tokens or 0

        llm_conf = verdict["confidence"]
        outcome  = verdict["outcome"]
        evidence = verdict["evidence"]

        print(f"    → outcome={outcome}  llm_confidence={llm_conf:.2f}  evidence: {evidence[:60]}")

        if outcome is not None and llm_conf >= min_confidence:
            # Resolve in ledger (in-memory + DB persistence via resolution_service role)
            try:
                resolved_record = resolution_svc.resolve(
                    prediction_id=pred.prediction_id,
                    outcome=outcome,
                    ground_truth_source=resolution_url,
                    evidence={
                        "page_url": resolution_url,
                        "llm_confidence": llm_conf,
                        "evidence_sentence": evidence,
                        "model": model,
                        "resolution_source_type": "external_web_page",
                    },
                    resolver_id="resolution-service-checker",
                    resolver_type="service",
                    claim_source_url=claim_source_url,
                    resolution_url=resolution_url,
                )
                # Persist to DB with resolution_service role
                ledger._db = svc_conn
                ledger.persist_resolution(resolved_record)
                ledger._db = main_conn

                print(f"    → RESOLVED: {outcome}  log_score={resolved_record.log_score:.4f}  "
                      f"brier={resolved_record.brier_score:.4f}")
                results.append({
                    "prediction_id": pred.prediction_id,
                    "claim": pred.claim,
                    "stated_confidence": pred.probability,
                    "outcome": outcome,
                    "llm_confidence": llm_conf,
                    "evidence": evidence,
                    "resolved": True,
                    "status": "resolved",
                    "log_score": resolved_record.log_score,
                    "brier_score": resolved_record.brier_score,
                })
            except Exception as exc:
                print(f"    → resolution error: {exc}")
                results.append({
                    "prediction_id": pred.prediction_id,
                    "claim": pred.claim,
                    "stated_confidence": pred.probability,
                    "outcome": outcome,
                    "llm_confidence": llm_conf,
                    "evidence": evidence,
                    "resolved": False,
                    "status": f"resolution_error: {exc}",
                    "log_score": None,
                    "brier_score": None,
                })
        else:
            status = "needs_human_review" if outcome is None else f"low_confidence_{llm_conf:.2f}"
            print(f"    → {status}")
            results.append({
                "prediction_id": pred.prediction_id,
                "claim": pred.claim,
                "stated_confidence": pred.probability,
                "outcome": outcome,
                "llm_confidence": llm_conf,
                "evidence": evidence,
                "resolved": False,
                "status": status,
                "log_score": None,
                "brier_score": None,
            })

    for pred in pending:
        results.append({
            "prediction_id": pred.prediction_id,
            "claim": pred.claim,
            "stated_confidence": pred.probability,
            "outcome": None,
            "llm_confidence": None,
            "evidence": "",
            "resolved": False,
            "status": f"pending_until_{pred.resolution_date.strftime('%Y-%m-%dT%H:%M:%SZ')}",
            "log_score": None,
            "brier_score": None,
        })

    trust_after = trust.trusted_confidence(
        stated=0.80, subject_id=agent_filter, subject_type="agent",
        domain="technology", claim_type="news_fact", horizon_class="short",
    )

    main_conn.close()
    svc_conn.close()

    # Print complete table
    print(f"\n{'='*64}")
    print("FULL PREDICTION TABLE")
    print(f"{'='*64}\n")
    fmt_hdr = f"{'prediction_id':<38} {'conf':>5} {'outcome':<7} {'score':>7} {'status'}"
    print(fmt_hdr)
    print("-" * len(fmt_hdr))
    for r in results:
        pid  = r["prediction_id"][:36]
        conf = f"{r['stated_confidence']:.2f}"
        out  = str(r["outcome"]) if r["outcome"] is not None else "—"
        sc   = f"{r['log_score']:.4f}" if r["log_score"] is not None else "—"
        st   = r["status"]
        print(f"{pid:<38} {conf:>5} {out:<7} {sc:>7}  {st}")

    print(f"\n  trust_confidence BEFORE : {trust_before:.4f}")
    print(f"  trust_confidence AFTER  : {trust_after:.4f}")
    print(f"  Δ                       : {trust_after - trust_before:+.4f}")
    cost_usd = token_usage["prompt"] * 0.00000015 + token_usage["completion"] * 0.0000006
    print(f"\n  LLM tokens (resolution) : {token_usage['total']}")
    print(f"  Estimated cost          : ${cost_usd:.4f}")

    # Update the internet_predictions.md with resolution results
    _update_markdown(results, trust_before, trust_after, token_usage, cost_usd)
    print(f"\n  Updated → evals/acceptance/internet_predictions.md\n")

    return results


def _update_markdown(
    results: list[dict],
    trust_before: float,
    trust_after: float,
    tokens: dict,
    cost: float,
) -> None:
    out_path = ROOT / "evals" / "acceptance" / "internet_predictions.md"
    existing = out_path.read_text() if out_path.exists() else ""

    resolution_section = [
        "",
        "---",
        "",
        "## Resolution Results",
        "",
        f"**Checked at:** {datetime.now(timezone.utc).isoformat()}",
        f"**trust_confidence before:** {trust_before:.4f}",
        f"**trust_confidence after:** {trust_after:.4f}",
        f"**LLM tokens (resolution):** {tokens['total']}",
        f"**Estimated cost (resolution):** ${cost:.4f}",
        "",
        "| prediction_id | claim | stated_conf | outcome | log_score | status |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        pid   = r["prediction_id"]
        claim = r["claim"][:50] + ("…" if len(r["claim"]) > 50 else "")
        conf  = f"{r['stated_confidence']:.2f}"
        out   = str(r["outcome"]) if r["outcome"] is not None else "—"
        sc    = f"{r['log_score']:.4f}" if r["log_score"] is not None else "—"
        st    = r["status"]
        resolution_section.append(f"| `{pid}` | {claim} | {conf} | {out} | {sc} | {st} |")

    out_path.write_text(existing + "\n".join(resolution_section))


if __name__ == "__main__":
    run()
