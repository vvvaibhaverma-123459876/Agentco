"""
Autonomy Goal Manager

Controls what agents can pursue. Prevents unconstrained self-generated goals.
All goals must have risk assessment and approval.
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
import uuid


@dataclass
class Goal:
    """Autonomy goal"""
    id: str
    title: str
    description: str
    domain: str
    risk_level: str  # low, medium, high, critical
    autonomy_level_allowed: int  # 0-6
    status: str  # proposed, under_review, approved, active, completed, rejected
    created_at: datetime
    proposed_by: str
    owning_agent_id: Optional[str] = None
    expected_value: Optional[float] = None
    success_criteria: Optional[dict] = None
    stop_conditions: Optional[dict] = None


class GoalManager:
    """Manage autonomous system goals"""

    def __init__(self):
        self.goals: dict[str, Goal] = {}

    def propose_goal(
        self,
        title: str,
        description: str,
        domain: str,
        risk_level: str,
        autonomy_level_allowed: int,
        proposed_by: str,
        owning_agent_id: Optional[str] = None,
        expected_value: Optional[float] = None,
    ) -> Goal:
        """
        Propose a new goal

        Goals are proposals and must go through approval before activation.
        """
        goal_id = str(uuid.uuid4())

        # Validate autonomy level
        if autonomy_level_allowed < 0 or autonomy_level_allowed > 6:
            raise ValueError(f"Invalid autonomy level: {autonomy_level_allowed}")

        # Validate risk level
        if risk_level not in ['low', 'medium', 'high', 'critical']:
            raise ValueError(f"Invalid risk level: {risk_level}")

        # Create goal
        goal = Goal(
            id=goal_id,
            title=title,
            description=description,
            domain=domain,
            risk_level=risk_level,
            autonomy_level_allowed=autonomy_level_allowed,
            status='proposed',
            created_at=datetime.now(),
            proposed_by=proposed_by,
            owning_agent_id=owning_agent_id,
            expected_value=expected_value,
        )

        self.goals[goal_id] = goal
        return goal

    def assess_risk(self, goal_id: str) -> dict:
        """Assess risk level of goal"""
        goal = self.goals.get(goal_id)
        if not goal:
            raise ValueError(f"Goal not found: {goal_id}")

        return {
            'goal_id': goal_id,
            'current_risk_level': goal.risk_level,
            'autonomy_level_allowed': goal.autonomy_level_allowed,
            'requires_human_approval': goal.risk_level in ['high', 'critical'],
            'requires_domain_approval': goal.autonomy_level_allowed > 2,
        }

    def check_conflicts(self, goal_id: str) -> List[str]:
        """Check for conflicts with other goals"""
        goal = self.goals.get(goal_id)
        if not goal:
            raise ValueError(f"Goal not found: {goal_id}")

        conflicts = []
        for other_id, other in self.goals.items():
            if other_id == goal_id:
                continue

            # Check for resource/objective conflicts
            if other.domain == goal.domain and other.status in ['active', 'approved']:
                conflicts.append(other_id)

        return conflicts

    def approve_goal(self, goal_id: str, approved_by: str) -> Goal:
        """Approve a proposed goal"""
        goal = self.goals.get(goal_id)
        if not goal:
            raise ValueError(f"Goal not found: {goal_id}")

        if goal.status != 'proposed':
            raise ValueError(f"Cannot approve goal in status: {goal.status}")

        goal.status = 'approved'
        return goal

    def activate_goal(self, goal_id: str) -> Goal:
        """Activate an approved goal"""
        goal = self.goals.get(goal_id)
        if not goal:
            raise ValueError(f"Goal not found: {goal_id}")

        if goal.status != 'approved':
            raise ValueError(f"Cannot activate goal in status: {goal.status}")

        goal.status = 'active'
        return goal

    def reject_goal(self, goal_id: str, reason: str) -> Goal:
        """Reject a proposed goal"""
        goal = self.goals.get(goal_id)
        if not goal:
            raise ValueError(f"Goal not found: {goal_id}")

        if goal.status not in ['proposed', 'under_review']:
            raise ValueError(f"Cannot reject goal in status: {goal.status}")

        goal.status = 'rejected'
        return goal

    def pause_goal(self, goal_id: str) -> Goal:
        """Pause an active goal"""
        goal = self.goals.get(goal_id)
        if not goal:
            raise ValueError(f"Goal not found: {goal_id}")

        if goal.status != 'active':
            raise ValueError(f"Cannot pause goal in status: {goal.status}")

        goal.status = 'paused'
        return goal

    def complete_goal(self, goal_id: str) -> Goal:
        """Mark goal as completed"""
        goal = self.goals.get(goal_id)
        if not goal:
            raise ValueError(f"Goal not found: {goal_id}")

        if goal.status != 'active':
            raise ValueError(f"Cannot complete goal in status: {goal.status}")

        goal.status = 'completed'
        return goal

    def list_active_goals(self) -> List[Goal]:
        """Get all active goals"""
        return [g for g in self.goals.values() if g.status == 'active']

    def list_goals_by_agent(self, agent_id: str) -> List[Goal]:
        """Get all goals for an agent"""
        return [g for g in self.goals.values() if g.owning_agent_id == agent_id]


# Global goal manager
_goal_manager: Optional[GoalManager] = None


def get_goal_manager() -> GoalManager:
    """Get or create global goal manager"""
    global _goal_manager
    if _goal_manager is None:
        _goal_manager = GoalManager()
    return _goal_manager
