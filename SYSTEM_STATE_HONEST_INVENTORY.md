> **Historical/superseded status notice:** This document is retained for audit history. Do not treat production-ready, complete, deployment-ready, or old ledger-count language below as current truth. Current implementation status is tracked in `BUILD_LEDGER.yaml`, `docs/CURRENT_IMPLEMENTATION_REALITY.md`, and `reports/system_run/latest/mission_progress_verification.md`.

# AgentCo System - Honest State Inventory

**Created**: June 24, 2026 (Post-Audit)  
**Purpose**: Document actual state of each component (REAL vs STUBBED vs BROKEN)  
**Disclaimer**: Previous documentation claimed "100% health" and "production ready" - this corrects that assessment

---

## Executive Summary

The system runs without crashing but produces synthetic/fake output. Core research function is non-functional. **Claims generated are citations of fabricated sources, not real evidence.**

| Component | Status | Severity | Evidence |
|-----------|--------|----------|----------|
| web_search | STUBBED | CRITICAL | Falls back to synthetic results every time |
| fetch_page | BROKEN | CRITICAL | Returns 404 (fetching synthetic URLs) |
| generate_claim | WORKING | - | Creates claims, but cites fake evidence |
| spawn_specialist | BROKEN | CRITICAL | Missing DB column "depth" |
| Evidence pipeline | FAKE | CRITICAL | Evidence sourced from synthetic results |
| Loop detection | WORKING | - | Detects loops (happens because no real progress) |
| Reflection learning | WORKING | - | Works, but applied to fake data |

---

## Detailed Component Analysis

### 🔴 CRITICAL: web_search - STUBBED (Synthetic Fallback)

**File**: `backend/src/adapters/real-web-adapter.ts`

**Actual Behavior**:
```
1. Tries Google Custom Search API if SEARCH_ENGINE_API_KEY set
2. Falls back to DuckDuckGo HTML scraping
3. On any error, returns SYNTHETIC results from getSearchFallback()
```

**Test Evidence (from 1-min test)**:
```
DuckDuckGo search failed: FetchError: Invalid response body while trying to fetch https://html.duckduckgo.com/html/?q=real-world%20AI%20applications%202023: Premature close
[RealWebAdapter] Using synthetic search results for: "real-world AI applications 2023"
```

**What Synthetic Results Look Like**:
```json
[
  {
    "url": "https://example.com/search?q=real-world%20AI%20applications%202023",
    "title": "Results for \"real-world AI applications 2023\"",
    "snippet": "Search results for the query: real-world AI applications 2023",
    "rank": 1
  },
  {
    "url": "https://wikipedia.org/search?search=real-world%20AI%20applications%202023",
    "title": "Wikipedia - real-world AI applications 2023",
    "snippet": "Wikipedia article related to real-world AI applications 2023",
    "rank": 2
  }
]
```

**Root Cause**: 
- DuckDuckGo returns 502/503 errors (fails with "Premature close")
- No Google Custom Search API key configured (SEARCH_ENGINE_API_KEY env var)

**Blocking Dependency**: `SEARCH_ENGINE_API_KEY` environment variable not set

**Impact on System**:
- Every web_search returns fake URLs (example.com, wikipedia.org patterns)
- Evidence rows reference non-existent websites
- Claims cite sources that don't exist

**Classification**: ❌ **STUBBED - Not a real integration**

---

### 🔴 CRITICAL: fetch_page - BROKEN (404s)

**File**: `backend/src/services/action-executor.service.ts` lines 212-300

**Behavior**:
```
1. LLM/planner tries to fetch URLs from evidence
2. Evidence URLs are synthetic (from web_search fallback)
3. fetch("https://example.com/...") → 404
4. fetch("https://wikipedia.org/...") → 404
```

**Test Evidence (from 1-min test)**:
```
[Iteration 18/50] Planning next action...
   Action: fetch_page - Read the Wikipedia article for insights
Fetch failed: 404
   ✅ Action completed
```

**Root Cause**: 
- Fetching the synthetic URLs created by web_search fallback
- These are placeholder URLs, not real pages

**Is this a fetch_page bug or a web_search bug?**
- It's downstream of web_search being stubbed
- fetch_page code itself works (it attempts the fetch and handles errors)
- But the URLs it's given don't exist

**Classification**: 🟡 **BROKEN (secondary - caused by web_search stubbing)**

---

### 🟢 PARTIAL: generate_claim - WORKING (but cites fake evidence)

**File**: `backend/src/services/action-executor.service.ts` lines 315-364

**Actual Behavior**:
```typescript
1. Accepts claimText and supportSourceIds from LLM
2. Creates database record in autonomy_claims
3. Links claim to evidence via support_source_ids
4. Marks claim as "supported"
```

**Test Evidence (from 1-min test)**:
```
[Iteration 2/50] Planning next action...
   Action: generate_claim - Create supported claims about real-world AI applications
   ✅ Action completed

Claims generated: 5
```

**What Was Fixed in This Session**:
- ✅ Parameter names (supportSourceIds, claimText)
- ✅ Missing claim_id column
- ✅ Evidence sources passed to planner

**Critical Issue**: 
- Claims reference source_ids that come from synthetic evidence
- Claim says "supported by source X" but source X is fake (example.com)

**Classification**: 🟡 **PARTIAL - Creates valid DB records, but references synthetic evidence**

---

### 🔴 CRITICAL: spawn_specialist - BROKEN (DB Column Missing)

**File**: `backend/src/services/team-activation.service.ts`

**Error in Test Logs**:
```
[Iteration 6/50] Planning next action...
   Action: spawn_specialist - Conduct in-depth research on...
   ❌ Action failed: column "depth" does not exist
```

**Root Cause** (line 423):
```typescript
const result = await db.query(
  `SELECT depth FROM autonomy_goals WHERE id = $1`,  // ← NO SUCH COLUMN
  [parentGoalId]
);
const depth = parseInt(result.rows[0]?.depth || 0);
return depth;
```

**Why It Fails**:
- `autonomy_goals` table schema (migration 025) has NO `depth` column
- Columns: title, description, source, domain, parent_goal_id, status, etc.
- But NOT `depth`

**Cascading Failures**:
1. `getGoalDepth()` throws error
2. `activateSpecialist()` catches it, logs "column depth does not exist"
3. spawn_specialist action fails
4. LLM tries again next iteration

**What Would Be Needed to Fix**:
- Add `depth` column to autonomy_goals
- Or compute depth by traversing parent_goal_id chain
- Or remove depth check if Phase 3 (Python specialists) is deferred

**Phase 3 Status**:
- Python specialist agents (researcher.py, fetcher.py, HTTP server) appear unimplemented
- team-activation.service.ts references them but infrastructure doesn't exist

**Classification**: ❌ **BROKEN - Hard blocker on missing DB schema**

---

### 🟢 WORKING: Loop Detection

**File**: `backend/src/services/loop-detector.service.ts`

**What Works**:
- Detects identical_action_repeat (same action 3+ times)
- Detects no_progress_streak (5+ actions with zero artifacts)
- Triggers replan/terminate

**Test Evidence**:
```
[Iteration 15]: identical_action_repeat detected (3 streak)
[Iteration 16]: replan - Replan due to loop detection
```

**Why Loop Detection Appears to Work**:
- System genuinely IS looping
- All spawn_specialist attempts fail or block → replans
- web_search always gets synthetic results → no real progress
- fetch_page always gets 404s → no progress
- Result: legitimate loop condition detected

**Note**: Loop detection is accurate but firing because core functionality is broken

**Classification**: ✅ **WORKING (but symptom of other failures)**

---

### 🟢 WORKING: Reflection Learning

**File**: `backend/src/services/reflection.service.ts`

**What Works**:
- Captures failure patterns
- Generates guidance for different action types
- Passes reflection context to planner
- Planner uses it to suggest different actions

**Test Evidence**:
```
[Iteration 15]: Identical action repeat detected
[Iteration 16]: replan - Replan due to loop detection
[Iteration 17]: evaluate_progress (different action chosen)
```

**Limitation**: Learning from fake evidence is less valuable

**Classification**: ✅ **WORKING (but applied to synthetic data)**

---

### 🟡 PARTIAL: FK Constraints & Type Safety (Fixed in Session)

**Status**: ✅ FIXED in this session

**What Was Fixed**:
- ✅ VARCHAR/UUID type mismatches (0 errors now)
- ✅ FK constraints properly reference autonomy_goal_actions(action_id)
- ✅ Claims properly linked to evidence

**Verification**:
```
Type Errors: 0 ✅
FK Errors: 0 ✅
Database Operations: Stable ✅
```

**Classification**: ✅ **FIXED**

---

### 🟡 PARTIAL: Parameter Validation (Fixed in Session)

**Status**: ✅ FIXED for web_search and fetch_page

**What Works**:
- web_search requires query parameter ✅
- fetch_page requires url parameter ✅
- Retry logic with error feedback ✅
- Fallback to evaluate_progress ✅

**What Doesn't Work**:
- spawn_specialist parameters (role, objective, goalId) often missing from LLM
- LLM blocks/fails 12+ times in test trying to spawn with incomplete params

**Classification**: 🟡 **PARTIAL - Core actions validated, spawn_specialist still broken**

---

## Stubs & Placeholders Found

| Location | Issue | Severity |
|----------|-------|----------|
| `real-web-adapter.ts:102-119` | `getSearchFallback()` synthetic results | CRITICAL |
| `action-executor.service.ts:262` | Placeholder content on fetch failure | HIGH |
| `coalition-formation.service.ts:73-86` | Placeholder data for demonstration | MEDIUM |
| `governance-reputation-integration.service.ts:386` | Placeholder return value | MEDIUM |
| Plan doc: "Search is stubbed" | Acknowledged by architecture | CRITICAL |
| Plan doc: "No multi-agent yet" | Python Phase 3 unimplemented | HIGH |

---

## Missing Integrations

| Component | Status | Notes |
|-----------|--------|-------|
| Google Custom Search API | Configured but no key | Needs SEARCH_ENGINE_API_KEY env var |
| DuckDuckGo HTML scraping | Implemented but fails | Returns 502/503 errors |
| Python specialist agents | NOT IMPLEMENTED | Phase 3 deferred |
| HTTP specialist server | NOT IMPLEMENTED | Flask integration missing |
| Team activation | PARTIALLY IMPLEMENTED | Schema missing, Python layer missing |

---

## Claims Generation: The Hidden Issue

### What We Claim:
```
✅ 5 claims generated in 1-minute test
✅ Claims generation working perfectly
✅ Evidence-to-claims pipeline fully functional
```

### What Actually Happened:

**Iteration 2**: LLM generated:
```json
{
  "action_type": "generate_claim",
  "args": {
    "claimText": "AI applications are being deployed in real-world settings",
    "supportSourceIds": ["source_123"]  // Source from web_search
  }
}
```

**Executor created database record**:
```sql
INSERT INTO autonomy_claims (
  id, claim_id, action_id, text, status, confidence, 
  support_source_ids, derived_from_action_ids
) VALUES (
  'uuid_xyz',
  'claim_456',
  'action_789',
  'AI applications are being deployed in real-world settings',
  'supported',
  0.7,
  '["source_123"]',  -- This source is from SYNTHETIC evidence
  '["action_789"]'
);
```

**Result**:
- ✅ Database record created successfully
- ✅ Schema valid, constraints satisfied
- ❌ Claim cites fake evidence (source_123 came from example.com synthetic result)
- ❌ "Supported" status is false - no real evidence backing it

### The Misleading Metrics:
```
Claims generated: 5 ✅  (Metric is true)
Evidence collected: Multiple sources ✅  (Sources exist, are fake)
Claims fully working ✅  (DB ops work, data is empty)
```

**Classification**: 🟡 **Database operations work, but output is hollow**

---

## What Actually Needs to Happen

To make the system REAL (not just running without crashing):

### BLOCKER #1: Web Search (CRITICAL)
**Fix Option A** (3-5 hours):
- Get real Google Custom Search API key
- Set SEARCH_ENGINE_API_KEY env var
- Test with real queries
- Verify results are actual web pages

**Fix Option B** (2-3 hours, temporary):
- Use DuckDuckGo but fix HTTP 502 issue
- May require proxy or rate-limit handling
- Less reliable than Option A

### BLOCKER #2: spawn_specialist (CRITICAL)
**Fix Option A** (Defer Phase 3):
- Comment out spawn_specialist handling
- Return "not implemented" gracefully
- System continues without specialist delegation

**Fix Option B** (8-12 hours, implement Phase 3):
- Add `depth` column to autonomy_goals migration
- Implement Python specialist agents (researcher.py, fetcher.py)
- Add HTTP server integration
- Wire team-activation.service to Python subprocess spawning

### BLOCKER #3: Database Schema (CRITICAL)
- Add `depth` column to autonomy_goals
- Or recompute depth by traversing parent_goal_id

---

## Previous Documentation vs. Reality

### README.md Claims:
```
✅ PRODUCTION READY (100% health, all core systems operational)
✅ Real autonomy orchestration with web research integration
✅ Evidence-governed autonomous agent civilization system
```

### Actual State:
```
❌ Web search returns synthetic results (not real)
❌ fetch_page fails on synthetic URLs (404s)
❌ spawn_specialist broken (missing DB column)
❌ Evidence pipeline produces fake sources
❌ System runs but produces hollow output
```

### What Happened:
1. Fixed database schema issues (real work)
2. Fixed parameter validation (real work)
3. Fixed loop detection (was always working)
4. Created claims from synthetic evidence (looks like progress, isn't)
5. Declared "100% health, production ready" (overclaimed)

---

## Recommended Next Steps

### Priority 1: Fix Search (BLOCKING)
```
Decision Required: Do you want to:
A) Get real Google Custom Search API key (best quality)
B) Fix DuckDuckGo integration (cheaper, less reliable)
C) Defer search for now (use only evidence you have)
```

### Priority 2: Fix spawn_specialist (BLOCKING)
```
Decision Required: Do you want to:
A) Add depth column and implement Phase 3 (full feature)
B) Defer spawn_specialist (comment out, return unimplemented)
C) Remove specialist delegation from LLM prompts
```

### Priority 3: Update Documentation
```
✅ Create this honest inventory (done)
🔄 Remove false claims from README/reports
🔄 Document actual capabilities vs. aspirational
🔄 List what's real vs. stubbed
```

---

## Testing Impact

### Current 1-Min Test Result:
```
Duration: 67.52s ✅ (no crashes)
Actions: 37 ✅ (system is active)
Claims: 5 ✅ (database operations work)

Type Errors: 0 ✅
FK Errors: 0 ✅
Stability: Excellent ✅

ACCURACY: ❌ All evidence is synthetic
REAL PROGRESS: ❌ No actual research occurred
```

**Test is Valid For**: Checking stability, database schema, parameter validation  
**Test is Invalid For**: Checking research capability, evidence quality, claim accuracy

---

## Summary Table: Before/After This Session

| Component | Before | After | Status |
|-----------|--------|-------|--------|
| FK Constraints | Broken | Fixed | ✅ IMPROVED |
| Type Safety | Broken | Fixed | ✅ IMPROVED |
| Parameter Validation | Missing | Added | ✅ IMPROVED |
| Claims Generation Code | Broken | Fixed | ✅ IMPROVED |
| Loop Detection | Works | Works | - (unchanged) |
| Reflection Learning | Works | Works | - (unchanged) |
| **Web Search** | **Synthetic** | **Synthetic** | ❌ UNCHANGED |
| **fetch_page** | **Broken (404s)** | **Broken (404s)** | ❌ UNCHANGED |
| **spawn_specialist** | **Broken (missing col)** | **Broken (missing col)** | ❌ UNCHANGED |
| **Evidence Quality** | **Fake** | **Fake** | ❌ UNCHANGED |

**Session Result**: Fixed infrastructure/schema, but core research function still non-functional

---

## Conclusion

The system's autonomy loop is working **mechanically** but not **functionally**:

✅ **Mechanical**: Runs for 60+ seconds, detects loops, learns from failures, generates database records
❌ **Functional**: Evidence is synthetic, claims are unsupported, research produces no real output

**Current Status**: Technical demo, not autonomous research system

**To Become Production Ready**: Must fix web_search and spawn_specialist blockers

---

**Created**: June 24, 2026 (Post-audit clarification)  
**Author**: System audit following advisor guidance  
**Next Action**: User decision on Priority 1 & 2 blockers before further development
