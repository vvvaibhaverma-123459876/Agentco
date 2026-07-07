# Archived V1 Department Agents

This archive contains department-style V1 agents that were classified `DEAD` in `docs/audit/PHASE5_NOTES.md`: the classes existed, but no active backend route, autonomy loop, Makefile target, cron path, or documented CLI instantiated them.

They were archived in Phase 6 after the V1 fail-closed change `672b76e`, which made `agents.core.base_agent.BaseAgent.run()` block high/critical actions by raising `GovernanceUnavailableError` after audit/override recording. V1 does not have working approval-resume infrastructure; current approval-gated execution lives in `runtime.base_agent.base_agent_v2.BaseAgentV2`.

Active replacements:

- Engineering: `CoderAgentV2`, `ReviewerAgentV2`, `DevOpsAgentV2`
- Executive: `CEOAgentV2`, `CFOAgentV2`, `COOAgentV2`
- Legal: `PrivacyAgentV2`
- People Ops: `ConfigAgentV2`
- Product: `PMAgentV2`
- Other archived roles have no active V2 replacement yet.

Archived V1 classes: `SuccessAgent`, `SupportAgent`, `VoiceAgent`, `ABAgent`, `BrandAgent`, `UXAgent`, `ArchitectAgent`, `CoderAgent`, `DevOpsAgent`, `ReviewerAgent` (engineering), `CEOAgent`, `CFOAgent`, `COOAgent`, `ContractAgent`, `PrivacyAgent`, `RiskAgent`, `AdsAgent`, `AnalyticsAgent`, `ContentAgent`, `SEOAgent`, `ConfigAgent`, `PerformanceAgent`, `RecruiterAgent`, `PMAgent`, `PrioritizerAgent`, `ResearchAgent`, `AEAgent`, `RevOpsAgent`, and `SDRAgent`.

Archived tests excluded from default pytest collection:

- `archive/agents_v1/tests/agents/engineering/test_devops_agent.py::test_deploy_without_reviewer_approval_blocked`
- `archive/agents_v1/tests/agents/engineering/test_devops_agent.py::test_rollback_triggered_by_error_rate`
- `archive/agents_v1/tests/agents/engineering/test_devops_agent.py::test_no_rollback_when_metrics_healthy`
- `archive/agents_v1/tests/agents/executive/test_ceo_agent.py::test_strategic_pivot_requires_human_approval`
- `archive/agents_v1/tests/agents/executive/test_ceo_agent.py::test_routine_goal_setting_autonomous`
