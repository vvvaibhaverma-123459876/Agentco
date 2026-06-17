"""Reviewer-Agent — ONLY agent authorized to approve merges. Zero tolerance for critical vulns."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentEvent, AgentOutput, RiskLevel


class ReviewerAgent(BaseAgent):
    AGENT_ID = "reviewer-agent"
    DEPARTMENT = "engineering"
    MEMORY_NAMESPACE = "engineering/reviewer"
    COMPETENCY_AREAS = ["code_review", "security_scanning", "test_coverage", "merge_approval"]

    MIN_COVERAGE_THRESHOLD = 0.95  # 95% per spec

    def get_system_prompt(self) -> str:
        with open("agents/prompts/engineering/reviewer_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "")
        if task_type == "review_pr":
            return await self._review_pr(task)
        else:
            messages = [{"role": "user", "content": str(task)}]
            response = await self.llm_call(messages)
            return AgentOutput(content=response, confidence_score=0.85, risk_level=RiskLevel.LOW, rationale="General review task")

    async def _review_pr(self, task: dict) -> AgentOutput:
        pr = task.get("pr", {})
        coverage = task.get("test_coverage", 0.0)
        security_issues = task.get("security_issues", [])
        critical_vulns = [i for i in security_issues if i.get("severity") == "critical"]
        regression_risk = task.get("regression_risk_score", 0.0)

        # ZERO TOLERANCE: critical vulnerabilities block merge
        if critical_vulns:
            return AgentOutput(
                content={"decision": "rejected", "pr_id": pr.get("id"), "reason": f"{len(critical_vulns)} critical security vulnerabilities — must fix before merge", "critical_vulns": critical_vulns},
                confidence_score=0.99,
                risk_level=RiskLevel.CRITICAL,
                rationale="Critical security vulnerabilities detected — zero tolerance policy",
            )

        # Coverage gate
        if coverage < self.MIN_COVERAGE_THRESHOLD:
            return AgentOutput(content={"decision": "rejected", "pr_id": pr.get("id"), "reason": f"Test coverage {coverage:.1%} below {self.MIN_COVERAGE_THRESHOLD:.1%} threshold"}, confidence_score=0.99, risk_level=RiskLevel.HIGH, rationale="Coverage below threshold — PR rejected")

        messages = [{"role": "user", "content": f"Review PR for correctness, security, performance, and standards compliance.\n\nPR: {pr}\nCoverage: {coverage:.1%}\nSecurity issues: {security_issues}\nRegression risk: {regression_risk:.2f}"}]
        response = await self.llm_call(messages, self.get_tools())

        approved = regression_risk < 0.7 and not security_issues

        if approved:
            await self.publish_event(AgentEvent(event_type="engineering.pr.merged", producer_agent_id=self.AGENT_ID, confidence_score=0.90, payload={"pr_id": pr.get("id"), "spec_id": pr.get("spec_id"), "coder_agent_id": pr.get("author_agent_id")}, risk_level=RiskLevel.LOW, requires_ack=False))

        return AgentOutput(
            content={"decision": "approved" if approved else "changes_requested", "pr_id": pr.get("id"), "review": response, "merge_authorized": approved},
            confidence_score=0.90,
            risk_level=RiskLevel.MEDIUM if not approved else RiskLevel.LOW,
            rationale=f"PR {'approved' if approved else 'rejected'} — merge authorization {'granted' if approved else 'denied'}",
        )
