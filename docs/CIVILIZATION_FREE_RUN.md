# Civilization Free-Run Runtime

Last updated: 2026-06-25

## What Is Real

The backend has a goal-less free-run vertical slice:

```bash
cd backend
DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco npx ts-node scripts/civilization-free-run.ts --mode fixture
```

The runtime executes:

1. self-assessment from real Postgres state
2. internal goal creation with `source = perception_derived`
3. society agenda persistence in `autonomy_memory`
4. agenda-driven bounded task execution
5. grounded claim creation
6. active contradiction detection
7. governance-bound agent spawn proposal
8. promotion gate
9. prediction registration
10. report artifacts under `audit_artifacts/civilization_free_run/<run_id>/`

The society agenda is not just a note: it carries `societyId`, `institutionId`, `taskType`, and `executionDomain`, and fixture bounded execution consumes that route. Calibration agendas produce evidence-promotion work; research agendas produce research-ingestion work.

Contradiction detection is now an active free-run stage. New claims are compared against recent stored claims for direct polarity conflicts over the same normalized proposition. When a conflict is found, the new claim is marked `contradicted`, `contradicted_by` / `contradicts` links are persisted on the real `autonomy_claims` rows, and promotion blocks the contradicted claim.

Agent spawning is proposal-only in the free-run pass. The runtime maps agenda and contradiction needs to registered specialist roles, copies the role's real default budget from `SPECIALIST_ROLES`, persists an `agent_spawn_proposal` in `autonomy_memory`, writes `agent_spawn_proposals.jsonl`, and does not activate a subprocess or write `autonomy_team_activations`.

## How It Is Tested

```bash
cd backend
RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco npx jest tests/integration/civilization-free-run.test.ts --runInBand --forceExit
```

The integration test uses real Postgres and asserts that:

- the run starts without a user goal
- the internal goal is persisted as perception-derived
- the society agenda is persisted
- the agenda route drives the bounded task objective and claim content
- direct contradictions are detected and persisted before promotion
- agent spawn proposals are persisted with governance review required and bounded budgets
- proposal creation does not activate specialists
- grounded claims can be promoted
- ungrounded claims are blocked
- prediction registration is attempted
- report, event, claim, contradiction, and agent-spawn-proposal artifacts are written

## Still Partial

This is not the full civilization objective yet.

- self-assessment still uses shallow claim/evidence backlog signals
- society agendas are persisted records, not a complete society scheduler
- contradiction detection is conservative and direct-pattern based; it does not yet do semantic contradiction discovery with retrieval or LLM adjudication
- agent spawn proposals are not yet connected to a governance approval queue or benchmark activation lifecycle
- self-improvement proposals are not yet part of the free-run pass
- `read_only_web` depends on the external arXiv/LLM path and remains environment-limited

Next integrated increments should deepen self-assessment, then add structured self-improvement proposals into the same free-run runtime.
