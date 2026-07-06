> **Historical/superseded status notice:** This document is retained for audit history. Do not treat production-ready, complete, deployment-ready, or old ledger-count language below as current truth. Current implementation status is tracked in `BUILD_LEDGER.yaml`, `docs/CURRENT_IMPLEMENTATION_REALITY.md`, and `reports/system_run/latest/mission_progress_verification.md`.

# Autonomy Loop with Specialist Delegation

## Overview

The active autonomy delegation path includes 17 registered `agents/autonomy/*` specialist roles that the TypeScript orchestrator can spawn to delegate work. This document describes that narrow end-to-end flow.

Reachability note: this path is separate from the department-style V1/V2 agent classes under `agents/executive`, `agents/legal`, `agents/marketing`, `agents/sales`, and similar directories. Those classes are repository inventory and test targets unless reached through a separate caller; the `spawn_specialist` action does not instantiate them.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Autonomy Orchestrator                     │
│  executeAutonomyActionLoop() - 20-step supervised loop      │
└────────────────┬────────────────────────────────────────────┘
                 │
        ┌────────┴─────────┐
        │                  │
        ▼                  ▼
   [Inline Actions]  [Specialist Delegation]
   - WEB_SEARCH         SPAWN_SPECIALIST
   - FETCH_PAGE         action type
   - EXTRACT_EVIDENCE
   - GENERATE_CLAIM
        │                  │
        └────────┬─────────┘
                 │
        ┌────────▼────────────────┐
        │ ActionExecutorService   │
        │ - Validates action      │
        │ - Routes to handler     │
        │ - Waits for results     │
        │ - Persists to DB        │
        └────────┬────────────────┘
                 │
        ┌────────▼───────────────────────┐
        │ TeamActivationService          │
        │ - Allocates loopback port      │
        │ - Spawns Python subprocess     │
        │ - Polls /status endpoint       │
        │ - Terminates on completion     │
        └────────┬───────────────────────┘
                 │
        ┌────────▼───────────────────────────┐
        │ Python Specialist Agent (HTTP)     │
        │ - /execute - POST action spec      │
        │ - /status - GET current state      │
        │ - handle_action() - Route action   │
        │ - persist_evidence() - Save to DB  │
        │ - persist_claim() - Save to DB     │
        └────────┬───────────────────────────┘
                 │
        ┌────────▼─────────────────────┐
        │ Database Results              │
        │ autonomy_evidence (goal_id)   │
        │ autonomy_claims (goal_id)     │
        │ autonomy_team_activations     │
        └──────────────────────────────┘
```

## 17 Specialist Roles

### Original Specialists (5)
- **researcher**: Search, fetch, extract evidence (broadest access)
- **fetcher**: Read-only page fetching
- **evidence_summarizer**: Evidence analysis and extraction
- **claim_validator**: Validate and generate claims
- **reviewer**: Progress evaluation

### Tier 1 Specialists (6) - Existing ActionTypes
- **data_analyst**: Statistics, patterns, metrics analysis
- **source_validator**: Credibility checking, bias detection
- **evidence_linker**: Cross-reference patterns, connection mapping
- **contradiction_hunter**: Find conflicting claims, generate counter-claims
- **synthesizer**: Combine claims into meta-conclusions
- **background_researcher**: Deep contextual and historical research

### Tier 2 Specialists (6) - Domain-Specific
- **code_reviewer**: Code analysis, bug detection, performance review
- **doc_analyzer**: PDF/spec extraction, structured data parsing
- **sentiment_analyzer**: Opinion analysis, bias detection, emotional weight
- **comparative_analyst**: Entity comparison across multiple dimensions
- **temporal_analyst**: Timeline construction, causality analysis
- **quality_auditor**: Compliance checking, standards auditing

## How It Works

### 1. Planner Evaluates Specialist Fit

When planning the next action, the planner:
1. Analyzes current goal text
2. Checks if evidence already exists (prevents empty spawning)
3. Matches goal keywords to specialist roles
4. Recommends top 3 specialist matches
5. LLM decides: inline action OR spawn_specialist

**Example:**
```
Goal: "Analyze the code for security vulnerabilities"
↓
Evidence exists: Yes (3 pieces)
↓
Recommended specialists: [code_reviewer, quality_auditor, evidence_linker]
↓
LLM decision: "spawn_specialist with role='code_reviewer'"
```

### 2. Executor Spawns Specialist

ActionExecutor.handleSpawnSpecialist():
1. Validates role exists in specialist registry
2. Calls TeamActivationService.activateSpecialist()
3. Asks the OS for an available loopback port
4. Spawns Python subprocess: `python3.13 -m agents.autonomy.{role}` by default, or `AGENTCO_PYTHON` when configured
5. Passes arguments: specialist_id, port, role, budget

**Subprocess Start:**
```bash
python3.13 -m agents.autonomy.code_reviewer \
  --specialist-id abc123 \
  --port 54567 \
  --role code_reviewer \
  --budget '{"tokens": 7000, "iterations": 20, "seconds": 200}'
```

### 3. Specialist Starts HTTP Server

SpecialistAgent.__init__():
1. Inherits from BaseAgent (audit trail, memory, events)
2. Creates Flask app
3. Registers HTTP routes:
   - POST /execute - Accept ActionSpec
   - GET /status - Report current state
   - GET /health - Health check

**Endpoints Available:**
```
POST http://127.0.0.1:54567/execute
Content-Type: application/json

{
  "actionId": "action-123",
  "actionType": "fetch_page",
  "objective": "Fetch and analyze code",
  "args": { "url": "https://github.com/..." }
}

Response:
{
  "status": "completed",
  "observations": { ... },
  "artifacts": ["evidence-id-1", "evidence-id-2"],
  "tokens_used": 245
}
```

### 4. Executor Waits for Completion

ActionExecutor.waitForSpecialistCompletion():
1. Polls autonomy_team_activations table every 500ms
2. Checks specialist_id status field
3. Waits up to 30 seconds
4. Reads results JSON from database
5. Returns artifact/evidence/claim IDs

**Result Structure:**
```json
{
  "artifacts": ["artifact-1", "artifact-2"],
  "evidence": ["evidence-1", "evidence-2"],
  "claims": ["claim-1"]
}
```

### 5. Executor Persists Results

ActionExecutor.persistSpecialistResults():
1. Links evidence to parent goal: `UPDATE autonomy_evidence SET goal_id = ... WHERE id = ...`
2. Links claims to parent goal: `UPDATE autonomy_claims SET goal_id = ... WHERE id = ...`
3. Stores results in autonomy_team_activations.results JSONB
4. Marks specialist status as 'completed'

**Database State After:**
```sql
-- Evidence now linked to parent goal
SELECT * FROM autonomy_evidence WHERE goal_id = 'parent-goal-id';
  -- Shows evidence created by specialist

-- Claims now linked to parent goal
SELECT * FROM autonomy_claims WHERE goal_id = 'parent-goal-id';
  -- Shows claims generated by specialist

-- Specialist record updated
SELECT * FROM autonomy_team_activations WHERE specialist_id = 'abc123';
  -- status = 'completed'
  -- results = { "artifacts": [...], "evidence": [...], "claims": [...] }
```

### 6. Next Iteration Sees Specialist Work

The orchestrator's next iteration:
1. Queries autonomy_evidence for parent goal_id
2. Queries autonomy_claims for parent goal_id
3. Sees artifacts created by specialist
4. Planner uses this evidence for next decision
5. Cycle repeats

**Example Progression:**
```
Iteration 1:
  Action: search for "code vulnerabilities"
  Result: Found 3 articles (generic search)

Iteration 2:
  Planner: "Evidence exists, spawn code_reviewer"
  Action: spawn_specialist with role="code_reviewer"
  Result: Specialist analyzes code, generates 5 issues, 2 claims

Iteration 3:
  Planner sees: 8 evidence items + 2 claims
  Action: generate_claim (synthesize specialist findings)
  Result: High-confidence claim about vulnerabilities

Iteration 4:
  Planner: Progress sufficient, terminate successfully
```

## Budget Enforcement

Each specialist has strict budgets:

```typescript
{
  tokens: 7000,      // LLM token usage limit
  iterations: 20,    // Max action steps
  seconds: 200       // Wall-clock timeout
}
```

If specialist exceeds budget:
- Python agent: `check_budget()` raises RuntimeError
- HTTP response: 429 Too Many Requests
- Executor detects: Sets action status FAILED
- Orchestrator: Logs failure, may terminate goal

## Real Database Persistence

Python specialists don't return stub UUIDs anymore. When they call:

```python
evidence_id = self.persist_evidence(
    url="https://github.com/...",
    content="<actual page content>",
    title="Code Review Results",
    source_type="specialist_output"
)
```

This actually:
1. Connects to PostgreSQL (via DATABASE_URL)
2. Inserts into autonomy_evidence table
3. Computes content_hash from real content
4. Returns real evidence_id from database
5. If DB connection retry exhaustion occurs: raises and reports structured failure; it does not return an unpersisted/stub ID

Same for claims via `persist_claim()`.

## Error Handling

### Specialist Timeout
- If specialist doesn't complete in 30s: mark action FAILED
- Action executor kills subprocess (SIGTERM then SIGKILL)
- Database records timeout in autonomy_team_activations

### Budget Exceeded
- Specialist agent exits with RuntimeError
- Process termination detected
- Action executor: "Specialist timed out before completion"
- Status: FAILED

### Database Unavailable
- Python specialist retries the database connection path.
- If persistence still fails, evidence/claim creation raises and the specialist action reports failure without artifacts.
- Stub UUID fallback is not part of the active persistence path.

## Testing the Full Loop

### Prerequisites
```bash
# PostgreSQL running
brew install postgresql
brew services start postgresql

# Create database
createdb agentco

# Apply migrations
cd backend
export DATABASE_URL="postgresql://localhost/agentco"
npm run db:migrate

# Set LLM key
export LLM_API_KEY="sk-..."

# Install Python dependencies
pip3 install psycopg2 flask requests beautifulsoup4
```

### Run Full Test
```bash
./scripts/run_full_autonomy_loop_with_specialists.sh
```

Expected output:
```
[1/6] Checking prerequisites...
✅ Prerequisites found

[2/6] Checking environment variables...
✅ Environment variables configured

[3/6] Building backend TypeScript...
✅ Backend built successfully

[4/6] Starting backend server...
✅ Backend started (PID: 12345)

[5/6] Testing API connectivity...
✅ API is responding

[6/6] Running autonomy action loop...
Goal: "Research the latest advancements in autonomous agents..."

✅ Autonomy loop completed
   Goal ID: goal-abc123
   Evidence collected: 12
   Claims generated: 4
   Actions executed: 8
   Specialists spawned: 2

✅ Specialist delegation successful!
   specialist_id | specialist_role | status
   --------------|-----------------|----------
   spec-001      | researcher      | completed
   spec-002      | data_analyst    | completed
```

## Monitoring

### Real-Time Monitoring
```bash
# Watch specialist processes
watch "ps aux | grep 'agents.autonomy'"

# Watch database activity
watch "psql $DATABASE_URL -c 'SELECT COUNT(*) FROM autonomy_team_activations WHERE status = \"active\";'"

# Monitor orchestrator logs
tail -f /tmp/backend.log | grep -i specialist
```

### Post-Run Analysis
```sql
-- See all specialists spawned for a goal
SELECT specialist_id, specialist_role, status, budget_tokens, tokens_used
FROM autonomy_team_activations
WHERE parent_goal_id = 'goal-abc123';

-- See evidence created by specialists
SELECT id, url, source_type, retrieved_at
FROM autonomy_evidence
WHERE goal_id = 'goal-abc123' AND source_type = 'specialist_output';

-- See claims backed by specialist evidence
SELECT claim_id, text, confidence, support_source_ids
FROM autonomy_claims
WHERE goal_id = 'goal-abc123';
```

## Performance Characteristics

### Typical Loop Iteration
- **Planner decision**: 500ms (LLM call)
- **Inline action**: 1-2 seconds
- **Specialist spawning**: 2-3 seconds (process start)
- **Specialist execution**: 5-30 seconds (depends on action)
- **Result persistence**: <100ms
- **Total per iteration**: 7-35 seconds

### Resource Usage
- **Per specialist process**: ~50-100MB RAM
- **Concurrent limit**: 3 per parent goal (enforced in code)
- **Max budget per specialist**: 200 seconds wall-clock
- **Token limit**: Usually 7000-12000 tokens

## Next Steps

### Optional Enhancements
1. **Specialist Chaining**: Spawn one specialist to process another's output
2. **Resource Limits**: Use cgroups/containers to enforce CPU/memory limits
3. **Parallel Execution**: Run multiple specialists concurrently (currently sequential)
4. **Caching**: Cache specialist results to avoid re-processing
5. **Learning**: Store successful specialist patterns for future goals

### Production Deployment
1. Run specialists in containers (Docker)
2. Use container orchestration (Kubernetes)
3. Implement health checks and auto-restart
4. Add monitoring/alerting (Prometheus, Grafana)
5. Scale horizontally based on load

## Architecture Decisions

### Why HTTP Instead of Direct Calls?
- Process isolation (specialist crash doesn't crash orchestrator)
- Language agnostic (could run specialists in any language)
- Easy to monitor (HTTP is standard)
- Fault tolerance (can retry HTTP requests)

### Why Budget Enforcement?
- Prevents runaway specialists (e.g., infinite loops)
- Enforces resource fairness
- Allows orchestrator to timeout hung agents
- Supports testing with small budgets

### Why Database Persistence?
- Specialists can't lose results on crash
- Enables result auditing
- Allows manual inspection of specialist work
- Supports long-running loops (restart-safe)

## See Also

- `backend/src/services/team-activation.service.ts` - Specialist spawning
- `backend/src/services/action-executor.service.ts` - Result persistence
- `backend/src/services/autonomy-action-planner.service.ts` - Specialist selection
- `agents/autonomy/specialist_agent.py` - Base class
- `scripts/run_full_autonomy_loop_with_specialists.sh` - Test script
