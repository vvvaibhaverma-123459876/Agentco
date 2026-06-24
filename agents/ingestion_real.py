"""
Real Claim Extraction for Civilization Free-Run
================================================

Extracts structured claims from text with classification, evidence attachment,
and database persistence. Replaces the stub ingestion/claim_extractor.py.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional

from agents.db import get_db

logger = logging.getLogger(__name__)


@dataclass
class ExtractedClaim:
    """Structured claim extracted from text."""

    claim_id: str
    text: str
    claim_type: str  # factual, prediction, opinion, instruction, unsupported
    confidence: float  # 0.0-1.0
    source_text: str  # original context
    evidence_ids: List[str]  # supporting evidence IDs


class ClaimExtractor:
    """Extract and classify claims from text."""

    def __init__(self):
        self.db = get_db()

    def extract_from_text(self, text: str, source_id: str = "") -> List[ExtractedClaim]:
        """Extract claims from plain text.

        Args:
            text: Raw text to extract from
            source_id: Optional source evidence ID (for claim linking)

        Returns:
            List of ExtractedClaim objects with classification
        """
        claims = []

        # Step 1: Segment into candidate sentences
        sentences = self._segment_sentences(text)

        # Step 2: Classify each sentence
        for sentence in sentences:
            if not sentence or len(sentence.split()) < 2:
                continue

            claim_type = self._classify_sentence(sentence)

            # Only process factual claims and predictions
            if claim_type in ("factual", "prediction"):
                claim = ExtractedClaim(
                    claim_id=str(uuid.uuid4()),
                    text=sentence,
                    claim_type=claim_type,
                    confidence=self._estimate_confidence(sentence, claim_type),
                    source_text=sentence,
                    evidence_ids=[source_id] if source_id else [],
                )
                claims.append(claim)
                logger.debug(f"Extracted {claim_type} claim: {sentence[:60]}...")

        return claims

    def persist_claims(
        self, claims: List[ExtractedClaim], action_id: str
    ) -> Dict[str, Any]:
        """Store extracted claims to database.

        Args:
            claims: List of ExtractedClaim objects
            action_id: The autonomy action that generated these claims

        Returns:
            Summary of persisted claims
        """
        persisted_ids = []
        errors = []

        for claim in claims:
            try:
                self.db.execute_update(
                    """INSERT INTO autonomy_claims
                       (id, claim_id, action_id, text, status, confidence, support_source_ids, derived_from_action_ids)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        str(uuid.uuid4()),
                        claim.claim_id,
                        action_id,
                        claim.text,
                        "proposed",  # Start as proposed, promote after evidence check
                        claim.confidence,
                        json.dumps(claim.evidence_ids),
                        json.dumps([action_id]),
                    ),
                )
                persisted_ids.append(claim.claim_id)
                logger.info(f"Persisted claim {claim.claim_id}: {claim.text[:50]}...")
            except Exception as e:
                errors.append(f"Failed to persist claim: {e}")
                logger.error(f"Claim persist failed: {e}")

        return {
            "total_extracted": len(claims),
            "total_persisted": len(persisted_ids),
            "persisted_ids": persisted_ids,
            "errors": errors,
        }

    def _segment_sentences(self, text: str) -> List[str]:
        """Split text into candidate sentences.

        Handles common sentence delimiters and normalizes whitespace.
        """
        # Split on sentence boundaries
        sentences = re.split(r"[.!?]+\s+", text)

        # Clean and filter
        cleaned = []
        for sent in sentences:
            sent = sent.strip()
            # Remove isolated punctuation and very short fragments
            if sent and len(sent.split()) >= 2:
                cleaned.append(sent)

        return cleaned

    def _classify_sentence(self, sentence: str) -> str:
        """Classify sentence type.

        Categories:
        - factual: states a fact (e.g., "Paris is in France")
        - prediction: states a claim about future/unresolved (e.g., "AI will improve calibration")
        - opinion: evaluative statement (e.g., "That's a great idea")
        - instruction: commands/procedures (e.g., "Run the test")
        - unsupported: vague or unsupported (e.g., "Something happened")
        """
        # Heuristics for classification
        lower_sent = sentence.lower()

        # Prediction markers
        if any(
            marker in lower_sent
            for marker in [
                "will",
                "should",
                "might",
                "could",
                "predict",
                "forecast",
                "expect",
                "estimated",
            ]
        ):
            return "prediction"

        # Opinion markers
        if any(
            marker in lower_sent
            for marker in ["think", "believe", "good", "bad", "great", "awful", "seem"]
        ):
            return "opinion"

        # Instruction markers
        if any(
            marker in lower_sent
            for marker in ["run", "execute", "do", "make", "create", "build", "test"]
        ) and (sentence.startswith(("Run", "Execute", "Do", "Make", "Create", "Build"))):
            return "instruction"

        # Default to factual if it has a subject+verb
        if re.search(r"\b\w+\s+(is|are|was|were|has|have|been)\b", sentence):
            return "factual"

        # Vague/unsupported
        if (
            any(
                marker in lower_sent
                for marker in ["something", "someone", "somehow", "somewhere"]
            )
        ):
            return "unsupported"

        # Default: treat as factual assertion
        return "factual"

    def _estimate_confidence(self, sentence: str, claim_type: str) -> float:
        """Estimate confidence in the claim (0.0-1.0).

        Factual claims get higher base confidence.
        Predictions get lower confidence (unresolved).
        Short sentences get lower confidence (less specificity).
        """
        base = {"factual": 0.75, "prediction": 0.6, "opinion": 0.4}.get(claim_type, 0.5)

        # Adjust for sentence length (longer = more specific)
        word_count = len(sentence.split())
        if word_count < 5:
            base -= 0.1
        elif word_count > 20:
            base += 0.05

        # Clip to [0, 1]
        return max(0.0, min(1.0, base))


def extract_and_persist(
    text: str, action_id: str, source_id: str = ""
) -> Dict[str, Any]:
    """Convenience function: extract claims from text and persist to DB.

    Args:
        text: Raw text to extract from
        action_id: The autonomy action that generated this text
        source_id: Optional source evidence ID

    Returns:
        Dictionary with extraction results
    """
    extractor = ClaimExtractor()

    # Extract
    claims = extractor.extract_from_text(text, source_id)
    logger.info(
        f"Extracted {len(claims)} claims from {len(text)} characters of text"
    )

    # Persist
    result = extractor.persist_claims(claims, action_id)

    return result
