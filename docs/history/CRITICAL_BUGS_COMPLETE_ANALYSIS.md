# Critical Bugs Analysis - Complete Fix Plan

This document maps ALL critical bugs found in the 5-minute test and defines COMPLETE fixes (not partial).

---

## BUG #1: LLM Parameter Generation Failure

### Severity: CRITICAL (Blocks 26% of actions)

### Current Behavior
```
[Iteration 1/2000] Planning next action...
   Action: web_search - Collect information on emerging trends...
   ⚠️  Action blocked: Web search requires "query" argument

[Iteration 2/2000] Planning next action...
   Action: web_search - Find relevant information on emerging trends...
   ⚠️  Action blocked: Web search requires "query" argument

[Iteration 3/2000] Planning next action...
   Action: web_search - Find relevant information on emerging trends...
   ⚠️  Action blocked: Web search requires "query" argument
```

**Pattern**: Web_search planned 45+ times across all loops WITHOUT query parameter

### Root Cause Analysis

**File**: `backend/src/services/autonomy-action-planner.service.ts`

**Issue Location**: Lines 150-182 (buildSystemPrompt and buildDecisionPrompt)

**Root Cause**:
1. System prompt doesn't provide concrete examples of required parameters
2. User prompt doesn't emphasize that web_search REQUIRES a query
3. JSON parsing doesn't validate required fields before returning
4. No error feedback loop when parameters are missing

**Why it happens**:
- gpt-4o-mini is trained on diverse data
- Without explicit examples, LLM defaults to generic descriptions
- System prompt lists action types but doesn't show parameter examples

### Complete Fix Required

**Fix 1: Enhanced System Prompt with Examples**
```
Location: actionPlanner.buildSystemPrompt()
Changes:
- Add JSON examples for EACH action type showing required parameters
- Mark REQUIRED fields with [REQUIRED]
- Provide 2-3 examples of valid JSON responses
- Add constraint: "ALL required fields MUST be present"
```

**Fix 2: Parameter Validation**
```
Location: actionPlanner.planNextAction() or actionPlanner.createActionSpecFromDecision()
Changes:
- Validate required parameters BEFORE creating ActionSpec
- If required parameters missing: 
  a) Log as validation error
  b) Retry LLM call with explicit instruction
  c) Include error feedback in next prompt
```

**Fix 3: Error Feedback Loop**
```
Location: actionPlanner.callOpenAI()
Changes:
- Track failed parameter validations
- On 2nd+ attempt: Include previous failure in prompt
- Example: "Previous attempt was missing query parameter. Ensure query is included."
```

**Fix 4: Fallback Strategy**
```
Location: actionPlanner.planNextAction()
Changes:
- If LLM fails to provide valid parameters after 2 attempts
- Automatically plan alternative action (evaluate_progress or fetch_page)
- Log the fallback for analysis
```

**Complete Implementation Checklist**:
- [ ] Add 3+ JSON examples to system prompt
- [ ] Implement parameter validation function
- [ ] Add retry logic with error feedback
- [ ] Implement fallback action selection
- [ ] Test: Verify all web_search actions include query parameter
- [ ] Test: Verify fetch_page actions include url parameter
- [ ] Test: Verify spawn_specialist actions include role, objective, goalId

---

## BUG #2: Database Foreign Key Constraint Violation

### Severity: CRITICAL (Prevents evidence/claims creation)

### Current Behavior
```
Error (Loop 2):
"insert or update on table "autonomy_evidence" violates foreign key constraint "fk_action""
"insert or update on table "autonomy_searches" violates foreign key constraint "fk_action""
```

### Root Cause Analysis

**File**: `backend/src/db/migrations/050_autonomy_action_loop.sql`

**Issue**: Two action tables with ID mismatch

```
autonomy_goal_actions:
  ├─ id: UUID (primary key)
  └─ action_id: VARCHAR(36) (unique)

autonomy_actions:
  └─ id: UUID (primary key, from migration 023)

autonomy_evidence:
  └─ action_id: UUID (FK references autonomy_actions.id)

autonomy_searches:
  └─ action_id: UUID (FK references autonomy_actions.id)

PROBLEM:
  ActionExecutor stores action in autonomy_goal_actions (gets UUID id)
  But autonomy_evidence/searches expect autonomy_actions.id
  Mismatch → FK constraint violation
```

### Complete Fix Required

**Option A: Unify to autonomy_goal_actions (RECOMMENDED)**
```
1. Rename autonomy_goal_actions → autonomy_actions (or consolidate schema)
2. Update autonomy_evidence.fk_action → references autonomy_goal_actions.id
3. Update autonomy_searches.fk_action → references autonomy_goal_actions.id
4. Update ActionExecutor to use correct table
5. Update all queries that reference old structure

Files to modify:
  - backend/src/db/migrations/050_autonomy_action_loop.sql
  - backend/src/db/migrations/023_autonomy_episodes.sql (if needed)
  - backend/src/services/action-executor.service.ts
  - backend/src/services/autonomy-orchestrator.service.ts
  - Any queries referencing autonomy_actions
```

**Option B: Keep both tables but fix references**
```
1. Keep autonomy_goal_actions and autonomy_actions separate
2. Ensure autonomy_evidence stores action_id from autonomy_goal_actions
3. Update ActionExecutor to store reference correctly
4. Update all FK constraints to match

Files to modify:
  - backend/src/services/action-executor.service.ts
  - backend/src/db/migrations/050_autonomy_action_loop.sql
  - Any insert statements for autonomy_evidence
```

**Complete Implementation Checklist**:
- [ ] Decide: Unify (A) or Fix References (B)
- [ ] Update migration file with correct FK constraints
- [ ] Update ActionExecutor insert logic
- [ ] Update all queries that reference these tables
- [ ] Run migrations fresh (drop/recreate tables)
- [ ] Test: Insert evidence without FK error
- [ ] Test: Create claims with evidence backing
- [ ] Test: Full autonomy loop with real web_search data

---

## BUG #3: Reflection Not Persistent Across Loops

### Severity: CRITICAL (No learning between loops)

### Current Behavior
```
Loop 1: web_search blocked → generates reflection
  "failurePattern": "LLM planning web_search without required query parameter"
  
Loop 2: web_search blocked → SAME PATTERN REPEATS
  (Reflection not used)
  
Loop 3-11: Same pattern repeats
  (Each loop starts fresh, no memory)
```

### Root Cause Analysis

**File**: `backend/src/services/reflection.service.ts` and `backend/scripts/autonomy-real-world-5min-unconstrained.ts`

**Issue**: Reflection stored in DB but not retrieved/passed to planner

```
Current flow:
1. Orchestrator calls executeAutonomyActionLoop()
2. Loop detects pattern → generates reflection
3. Reflection stored in autonomy_memory table
4. Loop terminates
5. Test starts NEW orchestrator instance
6. New instance has NO context from previous loop
7. Planner doesn't retrieve previous reflections
8. Pattern repeats identically

BROKEN CHAIN:
  Generate Reflection → Store in DB → [RETRIEVE?] → Pass to Planner
                                        ↑
                                   MISSING STEP
```

### Complete Fix Required

**Fix 1: Retrieve Previous Reflections in Planner**
```
Location: autonomy-action-planner.service.ts -> planNextAction()

Changes:
a) Query autonomy_memory for recent reflections:
   SELECT * FROM autonomy_memory 
   WHERE goal_id = $1 
   AND content->>'type' = 'reflection'
   ORDER BY created_at DESC 
   LIMIT 5

b) Format reflections for context:
   "Recent failures: [reflection1, reflection2, ...]
    What different action could work?"

c) Include in prompt as reflectionContext
```

**Fix 2: Pass Goal Context to Test Loop**
```
Location: backend/scripts/autonomy-real-world-5min-unconstrained.ts

Changes:
a) Reuse same goalId across all orchestrator loops
   (Currently creates new goal for each loop)
   
b) Pass goalId to orchestrator.executeAutonomyActionLoop()

c) Orchestrator retrieves previous reflections via DB
```

**Fix 3: Stateful Orchestrator**
```
Location: autonomy-orchestrator.service.ts

Changes:
a) Store goalId as instance variable
b) Retrieve previous loop's reflections before planning
c) Pass reflection context through to planner
d) Log reflection retrieval for debugging
```

**Fix 4: Reflection Quality Improvement**
```
Location: reflection.service.ts

Changes:
a) Generate more specific failure patterns:
   BEFORE: "LLM planning web_search without required query"
   AFTER: "web_search missing query. Suggest: try fetch_page with specific URL or evaluate_progress"

b) Include alternative actions in reflection
c) Rate confidence of suggestion (0-1)
```

**Complete Implementation Checklist**:
- [ ] Add reflection retrieval in ActionPlanner
- [ ] Modify test loop to reuse same goalId
- [ ] Update orchestrator to pass goalId through loop
- [ ] Test: Verify reflections retrieved from previous loop
- [ ] Test: Verify planner receives reflection context
- [ ] Test: Verify planner uses reflection (different action chosen)
- [ ] Test: Verify pattern NOT repeated in subsequent loop
- [ ] Log reflection usage for debugging

---

## BUG #4: Zero Claims Generated (No Goal Progress)

### Severity: CRITICAL (System can't succeed)

### Current Behavior
```
After 191 actions across 11 loops:
  Claims Generated: 0
  Evidence Collected: 0
  Goal Progress: 0%
  
Why: No web_search with valid query executed
     No fetch_page with valid url executed
     No evidence created
     No claims backed by evidence
```

### Root Cause Analysis

**Root Cause**: Combination of Bug #1 and Bug #2
- Bug #1: web_search never generates query parameter
- Bug #2: Even when it does, DB constraint blocks it
- Result: No evidence → No claims possible

### Complete Fix Required

**Fix**: Combination of Bug #1 + Bug #2 fixes

Once Bug #1 and Bug #2 are fixed:
- web_search will include query parameter
- Evidence will be stored successfully
- Claims can reference evidence
- Goal progress will be measurable

**Validation Checklist**:
- [ ] web_search with query executes successfully
- [ ] Evidence created in autonomy_evidence table
- [ ] Claims created with support_source_ids
- [ ] Claims count increments
- [ ] evaluate_progress shows goal progress
- [ ] NO_progress_streak detection uses actual progress (not always triggers)

---

## BUG #5: LLM Not Learning From Feedback

### Severity: HIGH (Reduces adaptability)

### Current Behavior
```
Iteration 1: LLM gets reflection context saying "try different action"
Iteration 2: LLM tries different action (evaluate_progress)
Iteration 3-5: Loop detected on evaluate_progress
Iteration 6: LLM receives NEW reflection context
Iteration 7: LLM tries web_search AGAIN (repeats bug #1)

Pattern: LLM doesn't retain learning across prompts
```

### Root Cause Analysis

**Root Cause**: Stateless LLM calls

```
Each LLM call:
- Receives current state
- Receives reflection context
- Returns action
- [CONTEXT LOST FOR NEXT CALL]

LLM has no memory of what it tried before
Reflection context is generic, not specific enough
```

### Complete Fix Required

**Fix 1: Enhanced Reflection Context**
```
Location: reflection.service.ts -> formatForContext()

Changes:
a) Include what was tried:
   "Previous attempt: web_search without query (failed)
    Reflection: Query parameter is required
    Next: Provide query in format: {query: 'your search term'}"

b) Include success criteria:
   "To succeed: web_search must have 'query' key in args"

c) Include example successful action:
   "Example that works:
    {action_type: 'web_search', args: {query: 'AI safety trends'}}"
```

**Fix 2: Constraint List in Prompt**
```
Location: actionPlanner.buildDecisionPrompt()

Changes:
a) Add "Constraints to follow" section:
   - web_search MUST have args.query
   - fetch_page MUST have args.url
   - spawn_specialist MUST have role, objective, goalId

b) Add "Recent failures" section:
   - What failed in previous iterations
   - Why it failed
   - What to try instead
```

**Fix 3: Action History in Context**
```
Location: actionPlanner.planNextAction()

Changes:
a) Include last 5 action attempts:
   "Previous actions: web_search (failed - no query), 
    evaluate_progress (completed), replan (completed)"

b) Include success/failure count:
   "Success rate: 2/5 (40%)"
```

**Complete Implementation Checklist**:
- [ ] Enhance reflection context with examples
- [ ] Add constraint list to system prompt
- [ ] Include action history in user prompt
- [ ] Test: Verify LLM generates different action after failure
- [ ] Test: Verify no repeated identical actions within loop
- [ ] Test: Verify parameter quality improves across attempts

---

## Summary: Complete Fix Dependencies

```
Fix Order (with dependencies):

1. BUG #1: LLM Parameter Generation [INDEPENDENT]
   └─ Fix: System prompt, validation, retry, fallback
   └─ Impact: Reduces blocked actions from 26% to <5%

2. BUG #2: Database FK Constraint [INDEPENDENT]
   └─ Fix: Unify or fix schema references
   └─ Impact: Enables evidence/claim creation

3. BUG #3: Reflection Persistence [DEPENDS on 1,2]
   └─ Fix: Retrieve, pass, use reflections
   └─ Impact: Enables learning across loops

4. BUG #4: Zero Claims [DEPENDS on 1,2]
   └─ Fix: Combination of 1+2 fixes
   └─ Impact: Goal progress becomes measurable

5. BUG #5: LLM Learning [DEPENDS on 1,3]
   └─ Fix: Enhanced context, constraints, history
   └─ Impact: Adaptive behavior improves
```

---

## Full Implementation Scope

### Files to Modify (Complete List)
```
backend/src/services/autonomy-action-planner.service.ts
  - buildSystemPrompt() - Add examples
  - buildDecisionPrompt() - Add constraints/history
  - planNextAction() - Add validation/retry
  - callOpenAI() - Error feedback
  - parseLLMDecision() - Validate parameters

backend/src/services/action-executor.service.ts
  - Verify correct table references
  - Ensure FK consistency

backend/src/services/autonomy-orchestrator.service.ts
  - Pass goalId consistently
  - Retrieve reflections before planning

backend/src/services/reflection.service.ts
  - formatForContext() - Enhanced context
  - generateReflection() - More specific patterns
  - storeReflection() - Preserve examples

backend/src/db/migrations/050_autonomy_action_loop.sql
  - Fix FK constraints
  - Unify or clarify table structure

backend/scripts/autonomy-real-world-5min-unconstrained.ts
  - Reuse goalId across loops
  - Pass context properly
```

### Testing Required (Complete)
```
Unit Tests:
- Parameter validation for each action type
- Reflection retrieval and formatting
- FK constraint compliance
- LLM response parsing

Integration Tests:
- Full loop with parameter generation
- Evidence creation and querying
- Claim creation with evidence backing
- Reflection retrieval and usage
- Goal progress tracking

End-to-End Tests:
- 5-minute test with goal completion
- Multiple loops with learning
- No repeated patterns
- Measurable progress
- Claims generated and valid
```

---

## Verification Criteria (All Must Pass)

✅ **After ALL fixes implemented, test must show**:
- `web_search` actions: 0 blocked (all include query)
- `fetch_page` actions: 0 blocked (all include url)
- `Evidence collected`: > 0
- `Claims generated`: > 0
- `Goal progress`: Measured and increasing
- `Reflection usage`: Verified in logs
- `Pattern repetition`: NO identical actions in same loop
- `System health`: > 95/100

---

## Timeline (No Partial Implementation)

**BEFORE starting any fix**:
1. ✅ Complete this analysis
2. ✅ Get approval for all fixes
3. ✅ Plan implementation order

**THEN implement in order**:
1. BUG #1 (Parameter generation) - Complete
2. BUG #2 (DB constraints) - Complete
3. BUG #3 (Reflection persistence) - Complete
4. BUG #4 (Zero claims) - Verified by fixes 1+2
5. BUG #5 (LLM learning) - Complete

**FINALLY**:
1. Run full 5-minute test
2. Verify all criteria
3. Commit only when ALL bugs fixed
