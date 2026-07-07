# V1 Severity Reachability — Phase 6.5

Verdict: ROUTINE. Across the 18 LIVE V1 agents, YES=0, CONDITIONAL=0, NO=18. The V1 high/critical block exists in `BaseAgent.run()`, but the live autonomy specialist path does not call `run()`; it calls each specialist's HTTP `/execute` route, which calls `handle_action()` and returns observations/artifacts without any V1 `RiskLevel`.

Branch base note: `origin/main` had not yet merged `fix/audit-phase6-v1-retirement` when this investigation began, so `audit/phase6.5-severity-reachability` was branched from `fix/audit-phase6-v1-retirement`.

## Task 1 — How Severity Is Assigned

The V1 severity enum is `RiskLevel`:

```python
# agents/core/types.py:10
class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

The V1 block trigger is in `BaseAgent.run()`:

```python
# agents/core/base_agent.py:102
async def run(self, task: dict[str, Any]) -> AgentOutput:
    output = await self.execute_task(task)
    ...
    if output.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL) or output.requires_human_approval:
        await self._write_audit(task, output, require_ack=True)
        request_id = await self._request_human_approval(task, output, require_record=True)
        raise GovernanceUnavailableError(
            f"human approval required for {self.AGENT_ID}; override_request_id={request_id}"
        )
```

There is also a generic scorer, but the LIVE specialist path does not call it:

```python
# agents/core/confidence_scorer.py:7
def compute_risk_level(confidence_score: float, action_category: str) -> RiskLevel:
    irreversible_actions = {"config_change", "agent_retirement", "contract_sign", "data_delete"}
    financial_actions = {"spend_approval", "budget_allocation", "vendor_payment"}

    if action_category in irreversible_actions or confidence_score < 0.3:
        return RiskLevel.CRITICAL
    if action_category in financial_actions and confidence_score < 0.7:
        return RiskLevel.HIGH
    if confidence_score < 0.5:
        return RiskLevel.HIGH
    if confidence_score < 0.7:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
```

`SpecialistAgent.execute_task()` hardcodes low severity if `BaseAgent.run()` is called directly:

```python
# agents/autonomy/specialist_agent.py:266
async def execute_task(self, task: Dict[str, Any]) -> AgentOutput:
    result = self.handle_action(task)
    return AgentOutput(
        content=json.dumps(result),
        confidence_score=0.7,
        risk_level=RiskLevel.LOW,
        rationale=f"Executed bounded specialist action for role {self.role}.",
        requires_human_approval=False,
    )
```

But the live invocation path bypasses `run()` entirely. The TypeScript service spawns `python3.13 -m agents.autonomy.${role}`:

```ts
// backend/src/services/team-activation.service.ts:661
const args = [
  '-m', `agents.autonomy.${role}`,
  '--specialist-id', specialistId,
  '--port', port.toString(),
  '--role', role,
  '--budget', JSON.stringify(budget),
];
```

The active execution path calls the specialist HTTP server:

```ts
// backend/src/services/team-activation.service.ts:519
const response = await fetch(`${specialist.httpEndpoint}/execute`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Signature': signature,
    'X-Timestamp': timestamp,
  },
  body: payload,
  signal: controller.signal,
});
```

The `/execute` route validates the action, then calls `handle_action()` directly and returns plain JSON. It does not construct `AgentOutput`, call `compute_risk_level()`, or call `BaseAgent.run()`:

```python
# agents/autonomy/specialist_agent.py:370
# Now execute the action
result = self.handle_action(action_spec)

response_data = {
    'status': 'completed',
    'observations': result.get('observations', {}),
    'artifacts': result.get('artifacts', []),
    'tokens_used': self.tokens_used,
    'errors': result.get('errors'),
    'rate_limit': rate_info,
}
```

## Task 2 — Per-Agent Reachability Table

| agent | severity source | can it emit high/critical? | evidence | invoked from |
|---|---|---:|---|---|
| `SpecialistAgent` | `execute_task()` hardcodes `RiskLevel.LOW`; live `/execute` bypasses `execute_task()` and `run()` | NO | `agents/autonomy/specialist_agent.py:266`, `agents/autonomy/specialist_agent.py:370` | base class for spawned `python3.13 -m agents.autonomy.${role}` specialists |
| `BackgroundResearcherAgent` | no severity assignment; `handle_action()` returns dict observations/artifacts | NO | `agents/autonomy/background_researcher.py:12`, `agents/autonomy/background_researcher.py:25`, common `/execute` at `agents/autonomy/specialist_agent.py:370` | `TeamActivationService.spawnSpecialistProcess()` -> `/execute` |
| `ClaimValidatorAgent` | no severity assignment; `handle_action()` returns dict observations/artifacts | NO | `agents/autonomy/claim_validator.py:13`, `agents/autonomy/claim_validator.py:26`, common `/execute` at `agents/autonomy/specialist_agent.py:370` | same |
| `CodeReviewerAgent` | no V1 severity assignment; observation field `severity: "medium"` is plain payload, not `RiskLevel` | NO | `agents/autonomy/code_reviewer.py:12`, `agents/autonomy/code_reviewer.py:24`, common `/execute` at `agents/autonomy/specialist_agent.py:370` | same |
| `ComparativeAnalystAgent` | no severity assignment; `handle_action()` returns dict observations/artifacts | NO | `agents/autonomy/comparative_analyst.py:6`, `agents/autonomy/comparative_analyst.py:15`, common `/execute` at `agents/autonomy/specialist_agent.py:370` | same |
| `ContradictionHunterAgent` | no severity assignment; `handle_action()` returns dict observations/artifacts | NO | `agents/autonomy/contradiction_hunter.py:12`, `agents/autonomy/contradiction_hunter.py:24`, common `/execute` at `agents/autonomy/specialist_agent.py:370` | same |
| `DataAnalystAgent` | no severity assignment; `handle_action()` returns dict observations/artifacts | NO | `agents/autonomy/data_analyst.py:12`, `agents/autonomy/data_analyst.py:24`, common `/execute` at `agents/autonomy/specialist_agent.py:370` | same |
| `DocAnalyzerAgent` | no severity assignment; `handle_action()` returns dict observations/artifacts | NO | `agents/autonomy/doc_analyzer.py:12`, `agents/autonomy/doc_analyzer.py:24`, common `/execute` at `agents/autonomy/specialist_agent.py:370` | same |
| `EvidenceLinkerAgent` | no severity assignment; `handle_action()` returns dict observations/artifacts | NO | `agents/autonomy/evidence_linker.py:12`, `agents/autonomy/evidence_linker.py:24`, common `/execute` at `agents/autonomy/specialist_agent.py:370` | same |
| `EvidenceSummarizerAgent` | overrides `execute_task()` to return a dict, but live path still uses `handle_action()`; no `RiskLevel` emitted | NO | `agents/autonomy/evidence_summarizer.py:14`, `agents/autonomy/evidence_summarizer.py:31`, `agents/autonomy/evidence_summarizer.py:43`, common `/execute` at `agents/autonomy/specialist_agent.py:370` | same |
| `FetcherAgent` | no severity assignment; `handle_action()` returns dict observations/artifacts | NO | `agents/autonomy/fetcher.py:12`, `agents/autonomy/fetcher.py:22`, common `/execute` at `agents/autonomy/specialist_agent.py:370` | same |
| `QualityAuditorAgent` | no severity assignment; `handle_action()` returns dict observations/artifacts | NO | `agents/autonomy/quality_auditor.py:6`, `agents/autonomy/quality_auditor.py:15`, common `/execute` at `agents/autonomy/specialist_agent.py:370` | same |
| `ResearcherAgent` | no severity assignment; `handle_action()` returns dict observations/artifacts | NO | `agents/autonomy/researcher.py:14`, `agents/autonomy/researcher.py:28`, common `/execute` at `agents/autonomy/specialist_agent.py:370` | same |
| `ReviewerAgent` | no severity assignment; `handle_action()` returns dict observations/artifacts | NO | `agents/autonomy/reviewer.py:12`, `agents/autonomy/reviewer.py:21`, common `/execute` at `agents/autonomy/specialist_agent.py:370` | same |
| `SentimentAnalyzerAgent` | no severity assignment; `handle_action()` returns dict observations/artifacts | NO | `agents/autonomy/sentiment_analyzer.py:6`, `agents/autonomy/sentiment_analyzer.py:15`, common `/execute` at `agents/autonomy/specialist_agent.py:370` | same |
| `SourceValidatorAgent` | no severity assignment; `handle_action()` returns dict observations/artifacts | NO | `agents/autonomy/source_validator.py:12`, `agents/autonomy/source_validator.py:24`, common `/execute` at `agents/autonomy/specialist_agent.py:370` | same |
| `SynthesizerAgent` | no severity assignment; `handle_action()` returns dict observations/artifacts | NO | `agents/autonomy/synthesizer.py:12`, `agents/autonomy/synthesizer.py:24`, common `/execute` at `agents/autonomy/specialist_agent.py:370` | same |
| `TemporalAnalystAgent` | no severity assignment; `handle_action()` returns dict observations/artifacts | NO | `agents/autonomy/temporal_analyst.py:6`, `agents/autonomy/temporal_analyst.py:15`, common `/execute` at `agents/autonomy/specialist_agent.py:370` | same |

No rows are CONDITIONAL. Severity is not caller-supplied in the live specialist HTTP payload. The payload contains `actionType`, `objective`, `args`, `goalId`, and `specialistId`; it has no `risk_level`/`severity` field consumed by the Python route:

```ts
// backend/src/services/action-executor.service.ts:588
const taskPayload = {
  actionType: primaryActionType,
  objective,
  args: primaryArgs,
  goalId: parentGoalId,
  specialistId: specialist.specialistId,
};
```

## Task 3 — Proof

Because every LIVE V1 agent is `NO`, Phase 6.5 adds one proof test for the highest-risk-looking role, `QualityAuditorAgent`. The test drives its standard `/execute` path and monkeypatches `BaseAgent.run()` plus `_request_human_approval()` to fail if governance is touched.

```python
# agents/tests/test_phase65_v1_severity_reachability.py:14
def test_quality_auditor_standard_execute_path_does_not_touch_v1_governance(monkeypatch):
    """The live /execute path should complete without calling BaseAgent.run()."""
```

Verification:

```text
python3.13 -m pytest agents/tests/test_phase65_v1_severity_reachability.py -q
1 passed in 0.26s
```

## Task 4 — Phase 7 Sizing

Recommendation: ROUTINE.

Reason: no live autonomy flow can currently reach the V1 high/critical block through the specialist path. The remaining migration reason is audit durability and architectural cleanup, not an urgent runtime landmine.

Suggested Phase 7 batches:

| batch | agents | estimate | rationale |
|---|---|---|---|
| 1 | `SpecialistAgent`, `FetcherAgent`, `ReviewerAgent`, `QualityAuditorAgent`, `CodeReviewerAgent` | structural for `SpecialistAgent`, mechanical once adapter exists for role subclasses | Build the V2 HTTP-specialist adapter first, then migrate the safest/read-only and proof-covered roles. |
| 2 | `ResearcherAgent`, `BackgroundResearcherAgent`, `SourceValidatorAgent`, `EvidenceSummarizerAgent`, `EvidenceLinkerAgent`, `DocAnalyzerAgent` | structural for real web/DB evidence paths, mechanical for role shell | These share evidence acquisition/processing semantics and should migrate with one audit-writer and evidence-persistence contract. |
| 3 | `ClaimValidatorAgent`, `DataAnalystAgent`, `ContradictionHunterAgent`, `SynthesizerAgent`, `ComparativeAnalystAgent`, `TemporalAnalystAgent`, `SentimentAnalyzerAgent` | mostly mechanical after claim/evidence V2 adapter exists | These primarily transform evidence into claims/analysis payloads and share the same `handle_action()` pattern. |

Per-agent estimate:

| agent | estimate | note |
|---|---|---|
| `SpecialistAgent` | structural | Must preserve HTTP server, budget accounting, HMAC, process lifecycle, and map to `BaseAgentV2` constructor/audit/escalation interfaces. |
| `BackgroundResearcherAgent` | mechanical after adapter | Role shell plus bounded action handlers. |
| `ClaimValidatorAgent` | mechanical after adapter | Claim generation/validation handler remains payload-oriented. |
| `CodeReviewerAgent` | mechanical after adapter | Payload-only review observations; no V1 severity semantics. |
| `ComparativeAnalystAgent` | mechanical after adapter | Payload-only comparison observations. |
| `ContradictionHunterAgent` | mechanical after adapter | Payload-only contradiction observations. |
| `DataAnalystAgent` | mechanical after adapter | Payload-only statistical observations. |
| `DocAnalyzerAgent` | mechanical after adapter | Payload-only document observations. |
| `EvidenceLinkerAgent` | mechanical after adapter | Payload-only evidence-link observations. |
| `EvidenceSummarizerAgent` | structural-light | Has an incorrect `execute_task()` override shape and DB reads; migrate with evidence adapter tests. |
| `FetcherAgent` | structural-light | Real web fetch plus DB evidence persistence should be wired to V2 audit durability. |
| `QualityAuditorAgent` | mechanical after adapter | Payload-only audit observations; covered by Phase 6.5 proof. |
| `ResearcherAgent` | structural-light | Real web search/fetch, DB persistence, evidence loading. |
| `ReviewerAgent` | mechanical after adapter | Simplest progress-only role. |
| `SentimentAnalyzerAgent` | mechanical after adapter | Payload-only sentiment observations. |
| `SourceValidatorAgent` | mechanical after adapter | Payload-only source-validation observations. |
| `SynthesizerAgent` | mechanical after adapter | Payload-only synthesis observations. |
| `TemporalAnalystAgent` | mechanical after adapter | Payload-only temporal observations. |
