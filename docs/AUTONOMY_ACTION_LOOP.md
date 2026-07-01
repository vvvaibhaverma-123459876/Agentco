> **Historical/superseded status notice:** This document is retained for audit history. Do not treat production-ready, complete, deployment-ready, or old ledger-count language below as current truth. Current implementation status is tracked in `BUILD_LEDGER.yaml`, `docs/CURRENT_IMPLEMENTATION_REALITY.md`, and `reports/system_run/latest/mission_progress_verification.md`.

# Autonomy Action Loop Implementation

## Overview

The Autonomy Action Loop is a complete end-to-end decision-execution cycle for autonomous agent behavior. It implements the full pipeline:

```
Goal → Plan → Decide Action → Execute → Observe → Evidence → Claims → Loop Detection → Terminate
```

This document describes the architecture, core components, safety constraints, and execution semantics.

## Architecture

### Core Components

**1. Autonomy Action Planner Service** (`autonomy-action-planner.service.ts`)
- Uses LLM reasoning to decide the next action given goal state
- Inputs: current goal, evidence collected, claims generated, loop detection status
- Output: Typed `ActionSpec` with all decision metadata
- Handles loop detection recommendations (replan/terminate)

**2. Action Executor Service** (`action-executor.service.ts`)
- Executes a validated `ActionSpec` and returns typed `ActionResult`
- Supported action types:
  - `WEB_SEARCH`: Record search intent
  - `FETCH_PAGE`: Fetch public web pages
  - `EXTRACT_EVIDENCE`: Extract facts from content
  - `GENERATE_CLAIM`: Create evidence-backed claims (requires sources)
  - `UPDATE_MEMORY`: Record learning
  - `EVALUATE_PROGRESS`: Assess loop progress
  - `REPLAN`: Record loop detection and replan intent
  - `TERMINATE`: Stop autonomy loop
- All results are typed: `ActionResult` with status, observations, artifacts, errors

**3. Loop Detector Service** (`loop-detector.service.ts`)
- Detects infinite loops by analyzing action history
- Two detection modes:
  1. **Identical Action Repeat**: Same action with same args 3+ times → recommend replan
  2. **No Progress Streak**: 5+ consecutive actions with 0 new artifacts → recommend terminate
- Returns typed `LoopDetectionResult` with recommendation

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Autonomy Orchestrator                                       │
│                                                              │
│  executeAutonomyActionLoop(goalText, maxIterations):       │
│    for iteration in 1..maxIterations:                      │
│      1. Create goal (LLM-driven)                           │
│      2. Get current state (claims, evidence)               │
│      3. Detect loops from history                          │
│      4. Plan next action (LLM with state)                  │
│      5. Execute action (typed executor)                    │
│      6. Update history                                     │
│      7. Check for termination or loop                      │
│      8. Continue or break                                  │
│    9. Return results                                       │
└─────────────────────────────────────────────────────────────┘
```

## Core Design Principles

### 1. No Unsupported Claims
- Claims MUST reference at least one evidence source
- Executor blocks `GENERATE_CLAIM` without evidence (`blockedReason` set)
- Database constraint enforces `support_source_ids` is non-empty JSONB array

### 2. No Silent Infinite Loops
- Every action is tracked in `ActionHistory`
- Loop detector runs after each action
- On loop detection:
  - If identical action repeat: trigger REPLAN
  - If no progress: trigger TERMINATE
- Both trigger graceful failure, not silent looping

### 3. Typed Decisions and Results
- `ActionSpec`: Complete decision specification before execution
- `ActionResult`: Typed execution result with status enum
- `LoopDetectionResult`: Explicit loop recommendation (replan/terminate/proceed)
- Database stores typed JSON for evidence/claims, not plain text

### 4. Evidence-Backed Knowledge
- Evidence stored in `autonomy_evidence` with source URLs, type, access level
- Claims linked to evidence via `support_source_ids` (JSONB array)
- Claim generation requires `supportSourceIds` argument validation
- Web sources tagged with `isPublicAccess` and `sourceType`

## Database Schema

### autonomy_actions
Tracks every decided and executed action:
```sql
CREATE TABLE autonomy_actions (
  id VARCHAR(36) PRIMARY KEY,
  action_id VARCHAR(36) UNIQUE,
  action_type VARCHAR(50),        -- WEB_SEARCH, FETCH_PAGE, etc.
  goal_id VARCHAR(36),            -- Links to autonomy_goals
  objective TEXT,                 -- What this action intends to achieve
  args JSONB,                     -- Action-specific arguments
  success_criteria TEXT[],        -- How to verify success
  risk_level VARCHAR(20),         -- low/medium/high
  decided_by VARCHAR(50),         -- 'autonomy_planner', 'loop_detector', etc.
  decided_at TIMESTAMP,           -- When decision was made
  reasoning TEXT,                 -- Why this action was chosen
  status VARCHAR(50),             -- planned/validated/executing/completed/failed/blocked
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  observations JSONB,             -- What was observed during execution
  created_artifacts TEXT[],       -- IDs of created evidence/claims/memory
  errors TEXT[],                  -- Any errors that occurred
  created_at TIMESTAMP
);
```

### autonomy_evidence
Tracks all evidence sources:
```sql
CREATE TABLE autonomy_evidence (
  id VARCHAR(36) PRIMARY KEY,
  source_id VARCHAR(36) UNIQUE,   -- Unique evidence identifier
  action_id VARCHAR(36),          -- Links to autonomy_actions
  url TEXT,                       -- Source URL
  title TEXT,                     -- Document title if available
  snippet TEXT,                   -- Content excerpt
  retrieved_at TIMESTAMP,         -- When fetched
  content_hash VARCHAR(100),      -- For deduplication
  source_type VARCHAR(50),        -- 'web', 'document', 'analysis', etc.
  is_public_access BOOLEAN,       -- Public or auth-required
  created_at TIMESTAMP
);
```

### autonomy_claims
Tracks all generated claims with evidence:
```sql
CREATE TABLE autonomy_claims (
  id VARCHAR(36) PRIMARY KEY,
  claim_id VARCHAR(36) UNIQUE,
  action_id VARCHAR(36),          -- Which action generated this
  text TEXT,                      -- Claim text
  status VARCHAR(50),             -- draft/unsupported/supported/contradicted
  confidence FLOAT,               -- 0.0-1.0
  support_source_ids JSONB,       -- ["source1", "source2"] - MUST NOT BE EMPTY
  support_snippets JSONB,         -- ["snippet1", "snippet2"]
  derived_from_action_ids JSONB,  -- ["action1", "action2"]
  generated_at TIMESTAMP,
  generated_by VARCHAR(50),
  created_at TIMESTAMP,
  CONSTRAINT claim_must_have_evidence CHECK (jsonb_array_length(support_source_ids) > 0)
);
```

### autonomy_loop_detection
Tracks loop detection events:
```sql
CREATE TABLE autonomy_loop_detection (
  id VARCHAR(36) PRIMARY KEY,
  goal_id VARCHAR(36),
  is_looping BOOLEAN,
  loop_type VARCHAR(50),          -- 'identical_action_repeat', 'no_progress_streak'
  streak INT,                     -- How many consecutive matches
  recommendation VARCHAR(50),     -- 'replan', 'terminate', 'proceed'
  detected_at TIMESTAMP,
  created_at TIMESTAMP
);
```

## Usage

### Basic Autonomy Loop

```typescript
import { autonomyOrchestrator } from '../services/autonomy-orchestrator.service';

// Execute a free-running autonomy loop
const result = await autonomyOrchestrator.executeAutonomyActionLoop(
  'Research and document the current state of AI autonomy frameworks',
  maxIterations = 10,
  idempotencyKey = 'optional-unique-key'
);

// Result structure:
{
  goalId: 'goal-uuid',
  claimsGenerated: 3,
  actionsExecuted: 8,
  status: 'completed',
  reason: 'Loop terminated: No progress detected after 5 iterations'
}
```

### API Endpoints

**POST /api/autonomy/action-loop**
```bash
curl -X POST http://localhost:3001/api/autonomy/action-loop \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Research AI autonomy frameworks",
    "maxIterations": 10,
    "idempotencyKey": "optional-key"
  }'
```

**GET /api/autonomy/actions?goalId=...**
Retrieve all actions executed for a goal.

**GET /api/autonomy/evidence?goalId=...**
Retrieve all evidence collected for a goal.

**GET /api/autonomy/claims?goalId=...**
Retrieve all claims generated for a goal.

## Safety Constraints

### Read-Only Internet Access Only
- Web fetching returns public content only
- No form submissions
- No authentication required
- No data mutation on external systems
- No API writes

### No Self-Modification
- Cannot modify core autonomy code
- Cannot modify LLM prompts in production
- Cannot modify safety constraints
- Cannot disable loop detection

### Evidence Requirements
- Every claim must reference at least one evidence source
- Unsupported claims are blocked with `blockedReason`
- Evidence sources recorded with access level and type

### Loop Protection
- Identical action repeat 3+ times triggers replan
- No-progress streak 5+ actions triggers termination
- Both produce clean failure state, not infinite loop

## Testing

### Unit Tests
- Planner output validation
- Executor action dispatch
- Loop detection logic
- Evidence constraint validation

### Integration Tests
- Full research loop: goal → search → fetch → evidence → claims
- Loop detection triggering replan/terminate
- Evidence requirement enforcement
- All action types dispatching correctly

### Run Tests
```bash
npm test -- backend/tests/action-loop.test.ts
```

## Execution Flow Example

```
iteration=1:
  goal: "Research AI autonomy frameworks"
  state: claims=0, evidence=0
  loop_status: clear
  action: WEB_SEARCH("autonomous AI systems")
  result: COMPLETED, searchId=abc123
  
iteration=2:
  state: claims=0, evidence=0
  loop_status: clear
  action: FETCH_PAGE("https://paper.example.com/autonomy")
  result: COMPLETED, sources collected
  
iteration=3:
  state: claims=0, evidence=2
  loop_status: clear
  action: GENERATE_CLAIM(
    text="AI autonomy research shows progress",
    supportSourceIds=["src1", "src2"]
  )
  result: COMPLETED, claimId=xyz789
  
iteration=4:
  state: claims=1, evidence=2
  loop_status: clear
  action: EVALUATE_PROGRESS
  result: COMPLETED
  
iteration=5:
  state: claims=1, evidence=2, actions=4
  loop_status: DETECTED (5 actions, 0 progress last iteration)
  action: TERMINATE(reason="No progress streak")
  result: COMPLETED
  
OUTPUT:
  goalId: goal123
  actionsExecuted: 5
  claimsGenerated: 1
  status: completed
  reason: "Loop detected: no_progress_streak (5 iterations). Forcing termination."
```

## Common Issues and Debugging

### Issue: Claims not generating
**Check:**
1. Evidence sources passed to GENERATE_CLAIM action?
2. `supportSourceIds` non-empty in action args?
3. Evidence stored in `autonomy_evidence` table?

### Issue: Loop detection not triggering
**Check:**
1. Action history being tracked across iterations?
2. Same action repeating with same args?
3. Count ≥ 3 for identical repeat? ≥ 5 for no-progress?

### Issue: Action blocked unexpectedly
**Check:**
1. `ActionResult.status === ActionStatus.BLOCKED`?
2. `ActionResult.blockedReason` provides details?
3. Missing required arguments in `spec.args`?

### Issue: Web fetch failing
**Check:**
1. URL accessible publicly (no auth required)?
2. No 404 or 500 errors?
3. User-Agent header proper?
4. Timeout 5s exceeded?

## Configuration

Environment variables:
```bash
# LLM Configuration
LLM_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini (default) or gpt-4-turbo

# Loop Detection Thresholds
LOOP_MAX_IDENTICAL_REPEAT=3 (default)
LOOP_MAX_NO_PROGRESS_STREAK=5 (default)

# Web Access
WEB_MAX_SEARCHES=10 (default)
WEB_MAX_FETCHES=20 (default)
WEB_FETCH_TIMEOUT_MS=5000 (default)

# Execution
MAX_AUTONOMY_ITERATIONS=10 (default)
AUTONOMY_TIMEOUT_MS=600000 (10 min default)
```

## Future Work

- [ ] Real web search integration (currently mock)
- [ ] Contradiction detection between claims
- [ ] Multi-goal coordination
- [ ] Learning/candidate generation from trajectories
- [ ] Team/institution/society activation mechanics (currently disabled)
- [ ] Real-time streaming of action events
- [ ] Action history persistence across runs

## References

- `src/services/autonomy-orchestrator.service.ts` - Main orchestration logic
- `src/services/action-executor.service.ts` - Action dispatch and execution
- `src/services/autonomy-action-planner.service.ts` - LLM-driven planning
- `src/services/loop-detector.service.ts` - Loop detection logic
- `src/types/action.types.ts` - Type definitions
- `backend/tests/action-loop.test.ts` - Comprehensive test suite
