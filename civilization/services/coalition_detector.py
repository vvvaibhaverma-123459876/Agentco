"""Coalition detection: coordinated false claims (Phase 5)."""
from __future__ import annotations

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class CoalitionDetector:
    """Detect coordinated false claims."""

    def detect_coordinated_false_claims(self, institution_id: str, claims: list[dict]) -> dict:
        """
        Detect coordinated false claims via clique detection.

        Args:
            institution_id: Institution ID
            claims: list of {claim_id, source_origin, agents, accuracy}

        Returns:
            {detected, coalition_members, shared_origin, clique_size}
        """
        if not claims or len(claims) < 4:
            return {
                "detected": False,
                "coalition_members": [],
                "shared_origin": None,
                "clique_size": 0,
            }

        # Build graph: origin -> claims
        origin_claims = defaultdict(list)
        for claim in claims:
            origin = claim.get("source_origin", "unknown")
            accuracy = claim.get("accuracy", 1.0)
            if accuracy < 0.5:  # False claim
                origin_claims[origin].append(claim)

        # Find cliques (origins with 3+ false claims)
        cliques = [(origin, claims_list) for origin, claims_list in origin_claims.items() if len(claims_list) >= 3]

        if not cliques:
            return {
                "detected": False,
                "coalition_members": [],
                "shared_origin": None,
                "clique_size": 0,
            }

        # Largest clique
        largest_origin, largest_clique = max(cliques, key=lambda x: len(x[1]))
        coalition_members = [c.get("agent", "unknown") for c in largest_clique]

        return {
            "detected": True,
            "coalition_members": coalition_members,
            "shared_origin": largest_origin,
            "clique_size": len(largest_clique),
            "rationale": f"Found clique of {len(largest_clique)} false claims from {largest_origin}",
        }
