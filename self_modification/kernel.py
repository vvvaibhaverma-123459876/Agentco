from __future__ import annotations

from dataclasses import dataclass

from governance.policy import PROTECTED_SURFACES


@dataclass
class ChangeProposal:
    proposer: str
    affected_files: list[str]
    expected_improvement: str
    risk: str
    tests_to_pass: list[str]
    rollback_plan: str
    status: str = "proposed"


class SelfModificationKernel:
    def evaluate(self, proposal: ChangeProposal, tests_passed: bool) -> ChangeProposal:
        if any(path in PROTECTED_SURFACES for path in proposal.affected_files) and proposal.risk != "critical-approved":
            proposal.status = "blocked_protected_surface"
        elif not tests_passed:
            proposal.status = "blocked_failed_tests"
        elif not proposal.rollback_plan:
            proposal.status = "blocked_no_rollback"
        else:
            proposal.status = "accepted_for_governance"
        return proposal
