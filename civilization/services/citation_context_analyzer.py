"""Citation context analysis (Phase 7)."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class CitationContextAnalyzer:
    """Extract and analyze citation context."""

    CONTEXT_STRENGTHS = {
        "proves": 0.9,
        "demonstrates": 0.85,
        "shows": 0.8,
        "suggests": 0.6,
        "may indicate": 0.5,
        "correlated with": 0.7,
        "disputed claim": 0.2,
        "controversial": 0.3,
        "alleged": 0.4,
    }

    def context_strength(self, citation_text: str) -> float:
        """Extract strength from citation text."""
        text_lower = citation_text.lower()

        for phrase, strength in self.CONTEXT_STRENGTHS.items():
            if phrase in text_lower:
                return strength

        return 0.5  # Neutral default

    def extract_context(self, citation: str) -> dict:
        """Extract context type and strength."""
        strength = self.context_strength(citation)

        # Infer context type
        context_type = "neutral"
        if strength > 0.8:
            context_type = "strong_support"
        elif strength < 0.4:
            context_type = "weak_support"
        elif "dispute" in citation.lower() or "contro" in citation.lower():
            context_type = "disputed"

        return {
            "context_type": context_type,
            "strength": strength,
            "text": citation[:100],
        }
