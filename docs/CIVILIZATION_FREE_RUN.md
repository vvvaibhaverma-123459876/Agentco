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
6. promotion gate
7. prediction registration
8. report artifacts under `audit_artifacts/civilization_free_run/<run_id>/`

The society agenda is not just a note: it carries `societyId`, `institutionId`, `taskType`, and `executionDomain`, and fixture bounded execution consumes that route. Calibration agendas produce evidence-promotion work; research agendas produce research-ingestion work.

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
- grounded claims can be promoted
- ungrounded claims are blocked
- prediction registration is attempted
- report, event, and claim artifacts are written

## Still Partial

This is not the full civilization objective yet.

- self-assessment still uses shallow claim/evidence backlog signals
- society agendas are persisted records, not a complete society scheduler
- contradiction detection is only respected by the promotion gate; it is not yet an active discovery stage
- agent spawn proposals and self-improvement proposals are not yet part of the free-run pass
- `read_only_web` depends on the external arXiv/LLM path and remains environment-limited

Next integrated increments should deepen self-assessment, then add contradiction detection and structured proposal stages into the same free-run runtime.
