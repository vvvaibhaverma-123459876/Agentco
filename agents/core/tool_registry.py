"""Dynamic tool registry with per-agent access enforcement (principle of least privilege)."""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Tool definitions available in the system
_TOOL_REGISTRY: dict[str, dict] = {}
_TOOL_HANDLERS: dict[str, Callable] = {}

# Per-agent allowed tools — enforced at runtime, not just in prompts
AGENT_TOOL_PERMISSIONS: dict[str, set[str]] = {
    "ceo-agent": {"okr_registry", "event_bus", "audit_log", "board_report_generator", "market_intelligence_feed", "human_override_interface", "financial_summary_reader", "operational_health_reader"},
    "cfo-agent": {"financial_monitor", "spend_approver", "budget_allocator", "event_bus", "audit_log", "human_override_interface"},
    "coo-agent": {"okr_registry", "workflow_orchestrator", "capacity_monitor", "event_bus", "audit_log"},
    "pm-agent": {"spec_registry", "research_reader", "okr_registry", "event_bus", "audit_log"},
    "research-agent": {"web_search", "web_scraper", "claim_extractor", "transcript_analyzer", "survey_tool", "competitor_monitor", "event_bus", "audit_log"},
    "prioritizer-agent": {"priority_stack", "feature_scorer", "roadmap_registry", "event_bus", "audit_log"},
    "architect-agent": {"code_repository", "adr_registry", "tech_debt_registry", "event_bus", "audit_log"},
    "coder-agent": {"code_repository", "test_runner", "event_bus", "audit_log"},
    "reviewer-agent": {"code_repository", "merge_approver", "security_scanner", "event_bus", "audit_log"},
    "devops-agent": {"ci_cd_pipeline", "infrastructure_monitor", "rollback_executor", "alerting", "event_bus", "audit_log"},
    "ux-agent": {"design_system", "wireframe_tool", "event_bus", "audit_log"},
    "brand-agent": {"design_system", "content_reviewer", "event_bus", "audit_log"},
    "ab-agent": {"experiment_runner", "stats_engine", "event_bus", "audit_log"},
    "sdr-agent": {"crm", "outreach_sequencer", "lead_scorer", "event_bus", "audit_log"},
    "ae-agent": {"crm", "proposal_generator", "event_bus", "audit_log"},
    "revops-agent": {"crm", "pipeline_analytics", "revenue_forecast", "event_bus", "audit_log"},
    "content-agent": {"content_cms", "web_search", "event_bus", "audit_log"},
    "seo-agent": {"seo_tool", "web_search", "event_bus", "audit_log"},
    "ads-agent": {"ads_platform", "budget_tracker", "event_bus", "audit_log"},
    "analytics-agent": {"analytics_platform", "attribution_model", "event_bus", "audit_log"},
    "support-agent": {"ticket_system", "knowledge_base", "event_bus", "audit_log"},
    "success-agent": {"crm", "health_score_engine", "event_bus", "audit_log"},
    "voice-agent": {"transcript_analyzer", "sentiment_analyzer", "shared_knowledge", "event_bus", "audit_log"},
    "performance-agent": {"metrics_reader", "event_bus", "audit_log"},  # READ ONLY — no write to agent configs
    "recruiter-agent": {"eval_runner", "model_benchmark", "event_bus", "audit_log"},  # staging only
    "config-agent": {"prompt_registry", "permission_manager", "rollback_executor", "human_override_interface", "event_bus", "audit_log"},
    "contract-agent": {"contract_repository", "playbook_reader", "event_bus", "audit_log"},
    "risk-agent": {"risk_register", "regulatory_monitor", "event_bus", "audit_log"},
    "privacy-agent": {"data_flow_mapper", "compliance_scanner", "human_override_interface", "event_bus", "audit_log"},
}


def register_tool(name: str, definition: dict, handler: Callable) -> None:
    _TOOL_REGISTRY[name] = definition
    _TOOL_HANDLERS[name] = handler


def get_tools_for_agent(agent_id: str) -> list[dict]:
    """Returns tool definitions (OpenAI-compatible schema) filtered to agent permissions."""
    allowed = AGENT_TOOL_PERMISSIONS.get(agent_id, set())
    return [_TOOL_REGISTRY[t] for t in allowed if t in _TOOL_REGISTRY]


async def execute_tool(agent_id: str, tool_name: str, tool_input: dict[str, Any]) -> Any:
    """Execute a tool, enforcing access control at runtime."""
    allowed = AGENT_TOOL_PERMISSIONS.get(agent_id, set())
    if tool_name not in allowed:
        raise PermissionError(f"Agent {agent_id!r} does not have permission to use tool {tool_name!r}")
    if tool_name not in _TOOL_HANDLERS:
        raise KeyError(f"Tool {tool_name!r} is not registered")
    return await _TOOL_HANDLERS[tool_name](tool_input)
