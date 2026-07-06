# Phase 5 Notes — Closeout and Merge Readiness

## Task 1 — V1 Governance Semantics

Answer: after `672b76e`, V1 high/critical actions cannot execute successfully through `BaseAgent.run()`; a recorded or granted human approval has no resume path, and `run()` raises `GovernanceUnavailableError` unconditionally after audit/override recording.

Relevant `agents/core/base_agent.py` code:

```python
output = await self.execute_task(task)
...
if output.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL) or output.requires_human_approval:
    await self._write_audit(task, output, require_ack=True)
    request_id = await self._request_human_approval(task, output, require_record=True)
    raise GovernanceUnavailableError(
        f"human approval required for {self.AGENT_ID}; override_request_id={request_id}"
    )
...
return output
```

Outcome trace:

| Case | Path | Outcome |
|---|---|---|
| Low/medium output without `requires_human_approval` | `execute_task()` -> confidence validation -> `_write_audit(require_ack=False)` -> `return output` | Executes and returns. Audit failures are logged and counted but non-blocking. |
| High/critical output or `requires_human_approval=True` | `execute_task()` -> confidence validation -> `_write_audit(require_ack=True)` -> `_request_human_approval(require_record=True)` -> `raise GovernanceUnavailableError` | Always blocks. If audit or override recording fails, the same error class is raised earlier. If override recording succeeds, the output still is not returned. |

Phase 5 semantic correction: this is de facto V1 high/critical disablement, not working approval-gated execution. V1 has no code path that consumes a granted approval and resumes the action. Use `BaseAgentV2` for approval-gated execution semantics.

### V1 Instantiation Reachability

Search scope: Python and TypeScript production paths, backend routes/services, `child_process`/`subprocess`, scripts referenced by `Makefile` or docs, and non-test direct constructors. Test-only constructors are excluded.

| subclass | instantiated by | reachable from | verdict |
|---|---|---|---|
| `BackgroundResearcherAgent` (`agents/autonomy/background_researcher.py`) | module main block constructs `BackgroundResearcherAgent(...)` | `ActionExecutorService.handleSpawnSpecialist()` -> `TeamActivationService.spawnSpecialistProcess()` -> `python3.13 -m agents.autonomy.<role>` | LIVE |
| `ClaimValidatorAgent` (`agents/autonomy/claim_validator.py`) | module main block constructs `ClaimValidatorAgent(...)` | `ActionExecutorService.handleSpawnSpecialist()` -> `TeamActivationService.spawnSpecialistProcess()` -> `python3.13 -m agents.autonomy.<role>` | LIVE |
| `CodeReviewerAgent` (`agents/autonomy/code_reviewer.py`) | module main block constructs `CodeReviewerAgent(...)` | `ActionExecutorService.handleSpawnSpecialist()` -> `TeamActivationService.spawnSpecialistProcess()` -> `python3.13 -m agents.autonomy.<role>` | LIVE |
| `ComparativeAnalystAgent` (`agents/autonomy/comparative_analyst.py`) | module main block constructs `ComparativeAnalystAgent(...)` | `ActionExecutorService.handleSpawnSpecialist()` -> `TeamActivationService.spawnSpecialistProcess()` -> `python3.13 -m agents.autonomy.<role>` | LIVE |
| `ContradictionHunterAgent` (`agents/autonomy/contradiction_hunter.py`) | module main block constructs `ContradictionHunterAgent(...)` | `ActionExecutorService.handleSpawnSpecialist()` -> `TeamActivationService.spawnSpecialistProcess()` -> `python3.13 -m agents.autonomy.<role>` | LIVE |
| `DataAnalystAgent` (`agents/autonomy/data_analyst.py`) | module main block constructs `DataAnalystAgent(...)` | `ActionExecutorService.handleSpawnSpecialist()` -> `TeamActivationService.spawnSpecialistProcess()` -> `python3.13 -m agents.autonomy.<role>` | LIVE |
| `DocAnalyzerAgent` (`agents/autonomy/doc_analyzer.py`) | module main block constructs `DocAnalyzerAgent(...)` | `ActionExecutorService.handleSpawnSpecialist()` -> `TeamActivationService.spawnSpecialistProcess()` -> `python3.13 -m agents.autonomy.<role>` | LIVE |
| `EvidenceLinkerAgent` (`agents/autonomy/evidence_linker.py`) | module main block constructs `EvidenceLinkerAgent(...)` | `ActionExecutorService.handleSpawnSpecialist()` -> `TeamActivationService.spawnSpecialistProcess()` -> `python3.13 -m agents.autonomy.<role>` | LIVE |
| `EvidenceSummarizerAgent` (`agents/autonomy/evidence_summarizer.py`) | module main block constructs `EvidenceSummarizerAgent(...)` | `ActionExecutorService.handleSpawnSpecialist()` -> `TeamActivationService.spawnSpecialistProcess()` -> `python3.13 -m agents.autonomy.<role>` | LIVE |
| `FetcherAgent` (`agents/autonomy/fetcher.py`) | module main block constructs `FetcherAgent(...)` | `ActionExecutorService.handleSpawnSpecialist()` -> `TeamActivationService.spawnSpecialistProcess()` -> `python3.13 -m agents.autonomy.<role>` | LIVE |
| `QualityAuditorAgent` (`agents/autonomy/quality_auditor.py`) | module main block constructs `QualityAuditorAgent(...)` | `ActionExecutorService.handleSpawnSpecialist()` -> `TeamActivationService.spawnSpecialistProcess()` -> `python3.13 -m agents.autonomy.<role>` | LIVE |
| `ResearcherAgent` (`agents/autonomy/researcher.py`) | module main block constructs `ResearcherAgent(...)` | `ActionExecutorService.handleSpawnSpecialist()` -> `TeamActivationService.spawnSpecialistProcess()` -> `python3.13 -m agents.autonomy.<role>` | LIVE |
| `ReviewerAgent` (`agents/autonomy/reviewer.py`) | module main block constructs `ReviewerAgent(...)` | `ActionExecutorService.handleSpawnSpecialist()` -> `TeamActivationService.spawnSpecialistProcess()` -> `python3.13 -m agents.autonomy.<role>` | LIVE |
| `SentimentAnalyzerAgent` (`agents/autonomy/sentiment_analyzer.py`) | module main block constructs `SentimentAnalyzerAgent(...)` | `ActionExecutorService.handleSpawnSpecialist()` -> `TeamActivationService.spawnSpecialistProcess()` -> `python3.13 -m agents.autonomy.<role>` | LIVE |
| `SourceValidatorAgent` (`agents/autonomy/source_validator.py`) | module main block constructs `SourceValidatorAgent(...)` | `ActionExecutorService.handleSpawnSpecialist()` -> `TeamActivationService.spawnSpecialistProcess()` -> `python3.13 -m agents.autonomy.<role>` | LIVE |
| `SpecialistAgent` (`agents/autonomy/specialist_agent.py`) | Not directly; abstract base used by autonomy role modules | Backend `spawn_specialist` -> `TeamActivationService` -> role module subclass | LIVE BASE |
| `SynthesizerAgent` (`agents/autonomy/synthesizer.py`) | module main block constructs `SynthesizerAgent(...)` | `ActionExecutorService.handleSpawnSpecialist()` -> `TeamActivationService.spawnSpecialistProcess()` -> `python3.13 -m agents.autonomy.<role>` | LIVE |
| `TemporalAnalystAgent` (`agents/autonomy/temporal_analyst.py`) | module main block constructs `TemporalAnalystAgent(...)` | `ActionExecutorService.handleSpawnSpecialist()` -> `TeamActivationService.spawnSpecialistProcess()` -> `python3.13 -m agents.autonomy.<role>` | LIVE |
| `SuccessAgent` (`agents/customer_experience/success_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `SupportAgent` (`agents/customer_experience/support_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `VoiceAgent` (`agents/customer_experience/voice_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `ABAgent` (`agents/design/ab_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `BrandAgent` (`agents/design/brand_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `UXAgent` (`agents/design/ux_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `ArchitectAgent` (`agents/engineering/architect_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `CoderAgent` (`agents/engineering/coder_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `DevOpsAgent` (`agents/engineering/devops_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `ReviewerAgent` (`agents/engineering/reviewer_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `CEOAgent` (`agents/executive/ceo_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `CFOAgent` (`agents/executive/cfo_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `COOAgent` (`agents/executive/coo_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `ContractAgent` (`agents/legal/contract_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `PrivacyAgent` (`agents/legal/privacy_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `RiskAgent` (`agents/legal/risk_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `AdsAgent` (`agents/marketing/ads_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `AnalyticsAgent` (`agents/marketing/analytics_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `ContentAgent` (`agents/marketing/content_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `SEOAgent` (`agents/marketing/seo_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `ConfigAgent` (`agents/people_ops/config_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `PerformanceAgent` (`agents/people_ops/performance_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `RecruiterAgent` (`agents/people_ops/recruiter_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `PMAgent` (`agents/product/pm_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `PrioritizerAgent` (`agents/product/prioritizer_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `ResearchAgent` (`agents/product/research_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `AEAgent` (`agents/sales/ae_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `RevOpsAgent` (`agents/sales/revops_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |
| `SDRAgent` (`agents/sales/sdr_agent.py`) | No non-test instantiation found | No backend route, autonomy loop, Makefile target, or documented CLI invokes this class directly | DEAD |

### Phase 6 Retire Recommendation

Do not retire `SpecialistAgent` or the 17 autonomy subclasses without replacing the active `spawn_specialist` path.

Recommended Phase 6 retire/archive list: all DEAD department-style V1 classes in `agents/customer_experience`, `agents/design`, `agents/engineering/*_agent.py` V1 files, `agents/executive/*_agent.py` V1 files, `agents/legal/*_agent.py` V1 files, `agents/marketing`, `agents/people_ops/*_agent.py` V1 files, `agents/product/*_agent.py` V1 files, and `agents/sales`. Keep V2 equivalents where present.

## Task 2 — `decision_log` Chain Continuity Across Writers

Writers read:

| Writer | File | Fields hashed | Serialization | Hash |
|---|---|---|---|---|
| TypeScript `AuditLogService` | `backend/src/services/audit-log.service.ts` | `log_id`, `timestamp`, `prev_hash`, `agent_id`, `action_type`, `input_summary`, `output_summary`, `confidence_score`, `risk_level`, `human_approved`, `human_approver_id`, `downstream_events`, `session_id` | Before Phase 5: `JSON.stringify(fields)` insertion order. After Phase 5: sorted-key compact JSON via `canonicalDecisionLogContent()` with normalized timestamp and confidence. Verifier also accepts the old TS insertion-order form for immutable legacy rows. | SHA-256 over `prev_hash + canonicalContent`. |
| Python `DurableAuditWriter` | `runtime/base_agent/audit_writer.py` | Same field set as TypeScript. | Before Phase 5: compact JSON with insertion order and Python UTC `+00:00` timestamp text. After Phase 5: `json.dumps(..., sort_keys=True, separators=(",", ":"))` and millisecond UTC `Z` timestamp. | SHA-256 over `prev_hash + canonicalContent`. |

Finding: the two writers were not using an explicit shared canonical serialization contract. They happened to use the same field order for many rows, but key ordering was implicit and timestamp text differed by runtime (`Z` vs `+00:00`). Phase 5 canonicalized both writers to sorted-key compact JSON and millisecond UTC `Z` timestamps.

Live-service test added: `backend/tests/audit-chain-cross-writer.test.ts` writes TS -> Python -> TS entries with one session id, then calls `AuditLogService.verifyChainIntegrity()` over the chain. It returns early with `SKIP: decision_log live-service test requires Postgres/migrations: ...` when the database or migrations are absent.
