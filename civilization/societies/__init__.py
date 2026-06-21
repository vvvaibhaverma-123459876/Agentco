"""Society layer — multi-institution governance and reputation aggregation."""

from .society_model import Society, SocietyMembership
from .society_service import (
    create_society,
    get_society,
    list_societies,
    admit_institution,
    retire_institution,
    suspend_institution_from_society,
    get_society_members,
    assign_external_reviewer,
)
from .society_reputation_service import (
    compute_society_reputation,
    update_society_reputation,
    aggregate_member_reputations,
)
from .society_governance_service import (
    propose_admission,
    get_active_proposals,
    approve_proposal,
    reject_proposal,
    can_society_judge_dispute,
    resolve_inter_institution_dispute,
)

__all__ = [
    "Society",
    "SocietyMembership",
    "create_society",
    "get_society",
    "list_societies",
    "admit_institution",
    "retire_institution",
    "suspend_institution_from_society",
    "get_society_members",
    "assign_external_reviewer",
    "compute_society_reputation",
    "update_society_reputation",
    "aggregate_member_reputations",
    "propose_admission",
    "get_active_proposals",
    "approve_proposal",
    "reject_proposal",
    "can_society_judge_dispute",
    "resolve_inter_institution_dispute",
]
