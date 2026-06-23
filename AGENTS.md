# AgentCo Autonomy Invariants

This document defines durable architectural rules for autonomous agent behavior in AgentCo. These invariants apply to all changes to autonomy systems and are enforced via code structure, database constraints, and tests.

## Core Invariants

### 1. Decision → Execution Rule

**Every autonomous decision must result in one of:**
1. Real action execution with observable outcome (status = COMPLETED, BLOCKED, or FAILED)
2. Explicit structured failure with reason (blockedReason documented)

**Never:** a decision logged without either executing or producing a structured error.

**Why:** Prevents silent failures and ensures all decisions are observable. A "decided but not executed" state is a bug, not a feature.

**Enforcement:**
- ActionSpec must route to a handler in ActionExecutor
- Every handler must set ActionResult.status to a valid enum (not leave it null)
- BlockedReason must be populated if status = BLOCKED
- Tests verify: no decision produces neither COMPLETED nor BLOCKED nor FAILED

**Examples:**
```typescript
// ✅ CORRECT: Decision produces observable outcome
const result = await executor.executeAction(spec);
assert(result.status in [COMPLETED, BLOCKED, FAILED]);

// ❌ WRONG: Decision logged but action has no handler
case ActionType.UNKNOWN:
  console.log('Unknown action, ignoring'); // Silent failure!
  break;
```

### 2. Evidence → Claim Rule

**No claim can be marked "supported" without evidence.**

**Claims must:**
- Reference support_source_ids (non-empty JSONB array)
- Include at least one source URL or artifact ID
- Be marked as "draft" or "unsupported" if evidence is insufficient

**Why:** Prevents fabricated knowledge. Claims are only valuable if traceable to evidence.

**Enforcement:**
- GENERATE_CLAIM action requires supportSourceIds argument (non-empty)
- Database constraint: `CHECK (jsonb_array_length(support_source_ids) > 0)` prevents empty arrays
- Executor blocks claim generation if supportSourceIds is empty with specific blockedReason
- Tests verify: every "supported" claim in database has non-empty support sources

**Examples:**
```typescript
// ✅ CORRECT: Claim backed by evidence
{
  text: "AI autonomy research shows rapid progress",
  status: "supported",
  support_source_ids: ["https://arxiv.org/abs/2401.00000", "https://research.example.com"],
  confidence: 0.85
}

// ❌ WRONG: Unsupported claim marked as supported
{
  text: "AI autonomy will surpass humans",
  status: "supported",
  support_source_ids: [],  // DATABASE CONSTRAINT PREVENTS THIS
  confidence: 0.9
}
```

### 3. Loop Detection → Adaptation Rule

**Repeated identical no-op actions must trigger adaptation, not silent looping.**

**Detection thresholds:**
- **Identical action repeat:** Same action type + same args ≥ 3 times → generate reflection + force REPLAN
- **No-progress streak:** 5+ consecutive actions with 0 new artifacts → generate reflection + force TERMINATE

**Adaptation mechanisms (in order of preference):**
1. **Reflection:** Store failure pattern summary in autonomy_memory
2. **Replan:** Trigger REPLAN action type (executor records loop detection event)
3. **Fallback:** Force different action type (e.g., WEB_SEARCH → FETCH_PAGE)
4. **Termination:** Graceful TERMINATE with clear reason

**Why:** Prevents infinite loops. Guarantees the system makes progress or fails cleanly.

**Enforcement:**
- LoopDetectorService.detectLoop() runs after every action
- On detection, generateReflection() creates compact failure summary
- Reflection is passed to next planner iteration
- Tests verify: identical action 3+ times triggers replan (not looping indefinitely)

**Examples:**
```
Loop detected: IDENTICAL_ACTION_REPEAT
Action: WEB_SEARCH(query='autonomy')
Repeated: 3 times
Artifacts: 0 new
Reflection: "Searched same query 3x without finding useful results. 
             Try different query terms or fetch a source directly."

Next action: FETCH_PAGE (forced different type)
```

### 4. Multi-Agent Boundaries Rule

**If team/society activation is used, it must be backed by real infrastructure with hard boundaries.**

**Requirements:**
1. Only registered specialist roles can spawn (whitelist approach)
2. Each specialist has explicit budget:
   - Token limit (LLM call budget)
   - Iteration limit (max steps)
   - Time limit (hard wall-clock timeout)
3. No unconstrained nesting:
   - Max depth: 2 levels (parent → specialist, specialist ≤ one sub-specialist)
   - Max parallel workers: 3 per parent goal
   - All resources pool across siblings (shared budget)
4. Results bubble back as evidence/artifacts to parent goal
5. Specialists are stateless within their scope (no cross-goal memory mutations)

**Why:** Prevents runaway agent spawning, resource exhaustion, and coordination deadlocks.

**Never:**
- "Create a team" as a language-only decision with no backend instantiation
- Unbounded nesting (agents spawning agents spawning agents...)
- Shared mutable state between agents
- Timeouts without a hard interrupt mechanism

**Enforcement:**
- TeamActivationService enforces role whitelist and budgets
- Database table autonomy_team_activations tracks all spawnings
- Orchestrator rejects spawn requests exceeding limits (returns BLOCKED)
- Tests verify: budget exhaustion terminates specialist, agents don't exceed nesting depth

**Examples:**
```typescript
// ✅ CORRECT: Registered role with explicit budget
const specialist = await teamActivation.activateSpecialist({
  role: 'researcher',                    // registered role
  objective: 'Find evidence on AI autonomy',
  parentGoalId: goal.id,
  budgets: {
    tokens: 2000,                       // hard LLM token limit
    iterations: 10,                     // hard step limit
    seconds: 60                         // hard time limit
  }
});

// ❌ WRONG: Unregistered role, no budgets
await teamActivation.activateSpecialist({
  role: 'magical_oracle',               // NOT in registry!
  objective: 'Solve everything'
  // no budgets specified
});
```

## Code Review Checklist

When reviewing changes to autonomy services (action-executor, loop-detector, orchestrator, team-activation):

- [ ] **Decision → Execution**: All ActionType cases handled? Every action produces status enum?
- [ ] **Evidence → Claim**: Claim generation requires supportSourceIds? DB constraint in place?
- [ ] **Loop Detection**: Tests verify 3+ identical triggers replan? 5+ no-progress triggers terminate?
- [ ] **Adaptation**: Is reflection generated when loop detected? Passed to planner on next iteration?
- [ ] **Multi-Agent**: Team activations bounded by role registry and budgets? No unbounded spawning?
- [ ] **Tests**: New features covered? Both happy path and failure cases?
- [ ] **Observability**: Events logged for all major transitions? State changes traceable?

## Examples of Violations and Fixes

### Violation 1: Decision Without Execution

**Code:**
```typescript
// ❌ BAD: Action decided but never executed
case ActionType.REPLAN:
  console.log('Replan not yet implemented');
  break;  // Action status left undefined!
```

**Fix:**
```typescript
// ✅ GOOD: Action produces structured outcome
case ActionType.REPLAN:
  result.status = ActionStatus.COMPLETED;
  result.observations.replanId = uuidv4();
  // Handler records replan event to database
  break;
```

### Violation 2: Unsupported Claim

**Code:**
```typescript
// ❌ BAD: Claim without evidence
const claim = {
  text: 'AI will achieve AGI in 5 years',
  status: 'supported',
  support_source_ids: []  // No evidence!
};
```

**Fix:**
```typescript
// ✅ GOOD: Claim backed by sources or marked draft
const spec: ActionSpec = {
  actionType: ActionType.GENERATE_CLAIM,
  args: {
    claimText: 'AI autonomy research shows progress',
    supportSourceIds: ['source-uuid-1', 'source-uuid-2'],  // REQUIRED
    confidence: 0.85
  }
};
// Executor verifies non-empty sources before storing
```

### Violation 3: Silent Loop

**Code:**
```typescript
// ❌ BAD: Repeated action causes silent loop
for (let i = 0; i < maxIterations; i++) {
  const action = await planner.planNext();
  const result = await executor.execute(action);
  // No loop detection, no adaptation
  // If action fails 5x, just keeps repeating
}
```

**Fix:**
```typescript
// ✅ GOOD: Loop detection triggers adaptation
for (let i = 0; i < maxIterations; i++) {
  const action = await planner.planNext(reflectionHistory);  // Pass prior learnings
  const result = await executor.execute(action);
  
  // Check for loops after every action
  const loopDetection = loopDetector.detectLoop(actionHistory);
  if (loopDetection.isLooping) {
    const reflection = loopDetector.generateReflection(loopDetection);
    await memory.store(reflection);
    reflectionHistory.push(reflection);
    
    // Force different action type or terminate
    if (loopDetection.recommendation === 'terminate') {
      break;
    }
  }
}
```

### Violation 4: Unbounded Multi-Agent Spawning

**Code:**
```typescript
// ❌ BAD: Agents spawn agents with no limits
async function solveGoal(goal) {
  for (const subgoal of goal.subgoals) {
    const agent = spawn(Agent, { goal: subgoal });  // Unbounded!
    results.push(await agent.run());
  }
}
```

**Fix:**
```typescript
// ✅ GOOD: Explicit role registry and budgets
async function solveGoal(goal, parentId) {
  const validRoles = ['researcher', 'fetcher', 'summarizer'];
  
  for (const subgoal of goal.subgoals.slice(0, 3)) {  // Max 3 per parent
    const role = mapGoalToRole(subgoal);
    if (!validRoles.includes(role)) {
      return { status: 'BLOCKED', blockedReason: 'Unknown role' };
    }
    
    const specialist = await teamActivation.activateSpecialist({
      role,
      objective: subgoal.description,
      parentGoalId: parentId,
      budgets: { tokens: 2000, iterations: 10, seconds: 60 }
    });
    
    results.push(specialist.results);
  }
}
```

## Testing These Invariants

Every autonomy service test must cover:

**1. Decision → Execution**
```typescript
it('should not allow unknown action types to pass silently', async () => {
  const spec: ActionSpec = { actionType: UNKNOWN_TYPE, ... };
  const result = await executor.executeAction(spec);
  expect(result.status).toEqual(ActionStatus.BLOCKED);
  expect(result.blockedReason).toBeDefined();
});
```

**2. Evidence → Claim**
```typescript
it('should block claim generation without evidence sources', async () => {
  const spec: ActionSpec = {
    actionType: ActionType.GENERATE_CLAIM,
    args: { claimText: '...', supportSourceIds: [] }
  };
  const result = await executor.executeAction(spec);
  expect(result.status).toEqual(ActionStatus.BLOCKED);
});
```

**3. Loop Detection → Adaptation**
```typescript
it('should generate reflection when 5+ no-progress actions detected', () => {
  const history = Array(5).fill({
    actionType: ActionType.EVALUATE_PROGRESS,
    newArtifacts: 0
  });
  const detection = loopDetector.detectLoop(history);
  expect(detection.isLooping).toBe(true);
  
  const reflection = loopDetector.generateReflection(detection);
  expect(reflection.type).toBe('reflection');
  expect(reflection.summary).toContain('no progress');
});
```

**4. Multi-Agent Boundaries**
```typescript
it('should reject spawn requests exceeding depth limit', async () => {
  const result = await teamActivation.activateSpecialist({
    role: 'researcher',
    parentGoalId: goal.id,
    depth: 3  // Max 2!
  });
  expect(result.status).toBe('BLOCKED');
});
```

## When to Violate These Rules

These are invariants for normal autonomous operation. The only exception is **when a rule is explicitly disabled for a specific scenario**:

- Safety testing: May temporarily disable multi-agent limits to stress-test the system
- Evaluation: May allow unlimited depth to measure agent capability ceiling
- Recovery: May bypass reflection requirement during crash recovery

**But:** Violations must be:
1. Documented in code (comment with reason and date)
2. Behind a feature flag or environment variable
3. Not in the default/production path
4. Auditable (logged when activated)

**Never** violate these rules silently or by accident.

## Related Documentation

- `docs/AUTONOMY_ACTION_LOOP.md` — Full technical reference
- `backend/tests/action-loop.test.ts` — Example tests for invariants
- `backend/tests/multi-agent-activation.test.ts` — Team activation boundaries
- `backend/tests/reflection-replan.test.ts` — Loop detection and adaptation

## History

- **2026-06-23** — Initial invariants documented for autonomy action loop and multi-agent systems
- Related to: Autonomy Action Loop Implementation (commit 7fbf7e7)
