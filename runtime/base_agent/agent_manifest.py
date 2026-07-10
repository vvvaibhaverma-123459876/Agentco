from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentProtocolProfile:
    agent_id: str
    classification: str
    implementation: str | None
    entrypoint: str
    allowed_actions: tuple[str, ...]
    allowed_tools: tuple[str, ...] = ()
    runtime_contract: str = "BaseAgentV2"
    notes: str = ""


ACTIVE_AGENT_PROFILES: tuple[AgentProtocolProfile, ...] = (
    AgentProtocolProfile(
        "ceo-agent",
        "active",
        "agents.executive.ceo_agent_v2.CEOAgentV2",
        "CEOAgentV2.run",
        ("strategic_pivot", "approve_budget", "budget_approval"),
    ),
    AgentProtocolProfile(
        "cfo-agent",
        "active",
        "agents.executive.cfo_agent_v2.CFOAgentV2",
        "CFOAgentV2.run",
        ("approve_spend", "runway_check", "financial_forecast"),
    ),
    AgentProtocolProfile(
        "coo-agent",
        "active",
        "agents.executive.coo_agent_v2.COOAgentV2",
        "COOAgentV2.run",
        ("structural_change", "set_operational_target"),
    ),
    AgentProtocolProfile(
        "coder-agent",
        "active",
        "agents.engineering.coder_agent_v2.CoderAgentV2",
        "CoderAgentV2.run",
        ("write_code", "scope_change", "security_alert"),
    ),
    AgentProtocolProfile(
        "reviewer-agent",
        "active",
        "agents.engineering.reviewer_agent_v2.ReviewerAgentV2",
        "ReviewerAgentV2.run",
        ("approve_review", "merge_pr", "reject_pr"),
    ),
    AgentProtocolProfile(
        "devops-agent",
        "active",
        "agents.engineering.devops_agent_v2.DevOpsAgentV2",
        "DevOpsAgentV2.run",
        ("deploy", "auto_rollback", "rollback_failed_escalation", "novel_incident_hard_pause"),
    ),
    AgentProtocolProfile(
        "pm-agent",
        "active",
        "agents.product.pm_agent_v2.PMAgentV2",
        "PMAgentV2.run",
        ("prioritize_feature", "approve_scope_change", "update_roadmap"),
    ),
    AgentProtocolProfile(
        "privacy-agent",
        "active",
        "agents.legal.privacy_agent_v2.PrivacyAgentV2",
        "PrivacyAgentV2.run",
        ("breach_response", "compliance_check", "data_access_request"),
    ),
    AgentProtocolProfile(
        "config-agent",
        "active",
        "agents.people_ops.config_agent_v2.ConfigAgentV2",
        "ConfigAgentV2.run",
        ("update_prompt", "rollback_prompt", "update_permissions"),
    ),
    AgentProtocolProfile(
        "research-agent",
        "active",
        None,
        "CivilizationService -> DurableExecutionService(record_observation)",
        ("record_observation",),
        runtime_contract="TypeScript DurableExecutionService",
        notes="Active durable identity for Civilization RAG route; audit/provenance/finalization are owned by DurableExecutionService.",
    ),
    AgentProtocolProfile(
        "calibration-reasoner",
        "active",
        None,
        "CivilizationService -> DurableExecutionService(record_observation)",
        ("record_observation",),
        runtime_contract="TypeScript DurableExecutionService",
        notes="Active durable identity for Civilization symbolic route; audit/provenance/finalization are owned by DurableExecutionService.",
    ),
)

PYTHON_ACTIVE_AGENT_PROFILES: tuple[AgentProtocolProfile, ...] = tuple(
    profile
    for profile in ACTIVE_AGENT_PROFILES
    if profile.runtime_contract == "BaseAgentV2"
)

TS_DURABLE_ACTIVE_AGENT_PROFILES: tuple[AgentProtocolProfile, ...] = tuple(
    profile
    for profile in ACTIVE_AGENT_PROFILES
    if profile.runtime_contract == "TypeScript DurableExecutionService"
)


EXPERIMENTAL_AGENT_PROFILES: tuple[AgentProtocolProfile, ...] = tuple(
    AgentProtocolProfile(
        agent_id,
        "experimental",
        implementation,
        "TeamActivationService -> python -m agents.autonomy.<role> -> SpecialistAgent /execute",
        (),
        notes="V1 autonomy specialist process; not advertised as production governed runtime.",
    )
    for agent_id, implementation in (
        ("specialist-agent", "agents.autonomy.specialist_agent.SpecialistAgent"),
        ("background-researcher-specialist", "agents.autonomy.background_researcher.BackgroundResearcherAgent"),
        ("claim-validator-specialist", "agents.autonomy.claim_validator.ClaimValidatorAgent"),
        ("code-reviewer-specialist", "agents.autonomy.code_reviewer.CodeReviewerAgent"),
        ("comparative-analyst-specialist", "agents.autonomy.comparative_analyst.ComparativeAnalystAgent"),
        ("contradiction-hunter-specialist", "agents.autonomy.contradiction_hunter.ContradictionHunterAgent"),
        ("data-analyst-specialist", "agents.autonomy.data_analyst.DataAnalystAgent"),
        ("doc-analyzer-specialist", "agents.autonomy.doc_analyzer.DocAnalyzerAgent"),
        ("evidence-linker-specialist", "agents.autonomy.evidence_linker.EvidenceLinkerAgent"),
        ("evidence-summarizer-specialist", "agents.autonomy.evidence_summarizer.EvidenceSummarizerAgent"),
        ("fetcher-specialist", "agents.autonomy.fetcher.FetcherAgent"),
        ("quality-auditor-specialist", "agents.autonomy.quality_auditor.QualityAuditorAgent"),
        ("researcher-specialist", "agents.autonomy.researcher.ResearcherAgent"),
        ("reviewer-specialist", "agents.autonomy.reviewer.ReviewerAgent"),
        ("sentiment-analyzer-specialist", "agents.autonomy.sentiment_analyzer.SentimentAnalyzerAgent"),
        ("source-validator-specialist", "agents.autonomy.source_validator.SourceValidatorAgent"),
        ("synthesizer-specialist", "agents.autonomy.synthesizer.SynthesizerAgent"),
        ("temporal-analyst-specialist", "agents.autonomy.temporal_analyst.TemporalAnalystAgent"),
    )
)


DEPRECATED_AGENT_PROFILES: tuple[AgentProtocolProfile, ...] = tuple(
    AgentProtocolProfile(agent_id, "deprecated", None, "archive/agents_v1", (), notes="Archived V1 department agent.")
    for agent_id in (
        "prioritizer-agent", "architect-agent", "ux-agent", "brand-agent",
        "ab-agent", "sdr-agent", "ae-agent", "revops-agent", "content-agent", "seo-agent",
        "ads-agent", "analytics-agent", "support-agent", "success-agent", "voice-agent",
        "performance-agent", "recruiter-agent", "contract-agent", "risk-agent",
    )
)


TEST_ONLY_AGENT_PROFILES: tuple[AgentProtocolProfile, ...] = (
    AgentProtocolProfile("test-agent", "test-only", None, "runtime/tests", ()),
    AgentProtocolProfile("e2e-dispatch-agent", "test-only", None, "agents/tests/integration", ()),
)


ALL_AGENT_PROFILES: tuple[AgentProtocolProfile, ...] = (
    ACTIVE_AGENT_PROFILES
    + EXPERIMENTAL_AGENT_PROFILES
    + DEPRECATED_AGENT_PROFILES
    + TEST_ONLY_AGENT_PROFILES
)


def active_agent_ids() -> set[str]:
    return {profile.agent_id for profile in ACTIVE_AGENT_PROFILES}
