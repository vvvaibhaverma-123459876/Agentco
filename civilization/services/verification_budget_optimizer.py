"""Verification budget optimization (Phase 8)."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class VerificationBudgetOptimizer:
    """Optimize verification allocation via knapsack."""

    def allocate_budget(self, claims_to_verify: list[dict], budget_tokens: int) -> dict:
        """
        Allocate budget: knapsack optimization.

        Args:
            claims_to_verify: list of {claim_id, voi, cost_tokens}
            budget_tokens: Total budget

        Returns:
            {allocation: [{claim_id, tokens}], roi_scores: {claim_id: roi}}
        """
        if not claims_to_verify or budget_tokens <= 0:
            return {"allocation": [], "roi_scores": {}}

        # Sort by VOI/cost (ROI)
        roi_list = []
        for claim in claims_to_verify:
            voi = claim.get("voi", 0.5)
            cost = claim.get("cost_tokens", 100)
            roi = voi / max(cost, 1)
            roi_list.append((claim["claim_id"], roi, voi, cost))

        roi_list.sort(key=lambda x: x[1], reverse=True)

        # Greedy allocation
        allocation = []
        remaining = budget_tokens
        roi_scores = {}

        for claim_id, roi, voi, cost in roi_list:
            if remaining >= cost:
                allocation.append({"claim_id": claim_id, "tokens": cost})
                roi_scores[claim_id] = roi
                remaining -= cost

        return {
            "allocation": allocation,
            "roi_scores": roi_scores,
            "remaining_tokens": remaining,
        }
