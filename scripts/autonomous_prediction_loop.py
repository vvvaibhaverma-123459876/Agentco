#!/usr/bin/env python3
"""
Autonomous prediction loop — demonstration script.

Uses the hardened web_scraper tool to:
  1. Discover sources for a topic (LLM-proposed URLs with date context).
  2. Fetch and extract main content from each URL.
  3. Ask the LLM to derive a falsifiable claim with probability.
  4. Register the claim in prediction_ledger (schema-correct, fail-loud).

Usage:
    DATABASE_URL=postgresql://... LLM_API_KEY=sk-... python scripts/autonomous_prediction_loop.py
"""

import os
import sys
from datetime import datetime, timedelta, timezone

# Ensure repo root is on path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.core.tools.web_scraper import (
    current_date_context,
    discover_sources,
    fetch_page,
    register_prediction,
)


def build_llm_client():
    try:
        from openai import OpenAI
    except ImportError:
        print("openai package not installed — skipping LLM calls")
        return None

    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("LLM_API_KEY not set — skipping LLM calls")
        return None
    base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    return OpenAI(api_key=api_key, base_url=base_url)


def derive_claim(client, model: str, context_text: str, topic: str) -> dict:
    """Ask the LLM to derive one falsifiable claim from scraped context."""
    date_ctx = current_date_context()
    prompt = (
        f"{date_ctx}\n\n"
        f"Topic: {topic}\n\n"
        f"Context from sources:\n{context_text[:4000]}\n\n"
        "Produce a single falsifiable prediction as JSON with these exact keys:\n"
        '  "claim": str  — a falsifiable statement about future reality\n'
        '  "probability": float  — your confidence (0.0-1.0)\n'
        '  "horizon_class": "short"|"medium"|"long"\n'
        '  "resolution_criterion": str  — exactly how/when the claim is verified\n'
        '  "ground_truth_source": str  — URL or dataset that will be used to resolve it\n'
        '  "domain": str  — one of: economics, science, politics, technology, health\n\n'
        "Output ONLY the JSON object, no markdown fences."
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=500,
        response_format={"type": "json_object"},
    )
    import json
    return json.loads(resp.choices[0].message.content)


def run_loop(topic: str, agent_id: str = "autonomous_loop_v1", model: str = "gpt-4o-mini"):
    client = build_llm_client()

    print(f"[loop] topic: {topic}")
    print(f"[loop] {current_date_context()}")

    # 1. Discover sources
    sources = discover_sources(topic, llm_client=client, model=model)
    if not sources:
        print("[loop] no sources discovered — using empty context")
        context_text = f"No sources found for topic: {topic}"
    else:
        print(f"[loop] discovered {len(sources)} source(s)")
        pages = []
        for url in sources:
            print(f"[loop]   fetching {url}")
            text = fetch_page(url)
            if text:
                pages.append(text[:2000])
        context_text = "\n\n---\n\n".join(pages) if pages else "No content extracted."

    if client is None:
        print("[loop] no LLM client — skipping claim derivation and registration")
        return

    # 2. Derive claim
    try:
        claim_data = derive_claim(client, model, context_text, topic)
    except Exception as e:
        print(f"[loop] claim derivation failed: {e}")
        return

    print(f"[loop] claim: {claim_data.get('claim')}")
    print(f"[loop] probability: {claim_data.get('probability')}")

    # 3. Register prediction (schema-correct, fail-loud)
    horizon_days = {"short": 30, "medium": 180, "long": 730}
    horizon_class = claim_data.get("horizon_class", "short")
    resolution_date = datetime.now(timezone.utc) + timedelta(
        days=horizon_days.get(horizon_class, 30)
    )

    record = {
        "claim": claim_data["claim"],
        "probability": float(claim_data["probability"]),
        "confidence_basis": {
            "sources": sources,
            "model": model,
            "context_length": len(context_text),
        },
        "producing_agent_id": agent_id,
        "producing_prompt_version": "autonomous_loop_v1.0",
        "resolution_criterion": claim_data.get("resolution_criterion", "manual review"),
        "resolution_date": resolution_date.isoformat(),
        "ground_truth_source": claim_data.get("ground_truth_source", "manual"),
        "horizon_class": horizon_class,
        "domain": claim_data.get("domain", "general"),
    }

    try:
        pid = register_prediction(record)
        print(f"[loop] registered prediction_id={pid}")
    except Exception as e:
        print(f"[loop] registration FAILED (not swallowed): {e}")
        raise


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "global AI adoption trends in 2025"
    run_loop(topic)
