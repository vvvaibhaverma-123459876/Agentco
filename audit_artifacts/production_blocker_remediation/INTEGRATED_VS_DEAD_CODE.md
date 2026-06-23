# Integrated vs. Dead Code Analysis

**Date:** 2026-06-23  
**Finding:** System has unregistered route files causing compilation errors but never executed

---

## Registered Routes (Actually Used)

These 7 route files are imported and registered in `server.ts`:

✅ `agents.routes.ts` — Registered line 57  
✅ `audit.routes.ts` — Registered line 59  
✅ `credential.routes.ts` — Registered line 60  
✅ `autonomy-tasks.routes.ts` — Registered line 62  
✅ `autonomy-orchestrator.routes.ts` — Registered line 63  
✅ `civilization-governance.routes.ts` — Registered line 64  
✅ `override.routes.ts` — Registered line 58  

---

## Unregistered Routes (Dead Code)

These 4 route files are defined but NEVER imported or registered:

❌ `goal.routes.ts` — NOT imported, NOT registered  
❌ `governance.routes.ts` — NOT imported, NOT registered  
❌ `phases-6-8.routes.ts` — NOT imported, NOT registered  
❌ `phases-9-13.routes.ts` — NOT imported, NOT registered  

**Error count from dead code:**
- `goal.routes.ts` — 7 errors
- `governance.routes.ts` — 0 errors (fixed by escape fixes)
- `phases-6-8.routes.ts` — 27 errors
- `phases-9-13.routes.ts` — 19 errors

**Total errors from dead code: ~53 errors (66% of remaining 80)**

---

## Implication

### The 80 Remaining Errors Split:

- **~27 errors in actually-integrated files** (real blockers)
- **~53 errors in dead-code files** (not execution blockers, but compilation blockers)

### Decision Points

**Option A: Fix dead code**
- Include dead code in build
- Fixes ~53 errors with type casting
- Effort: ~2 hours
- Benefit: Complete build with unused code

**Option B: Exclude dead code**
- Document unintegrated routes
- Compilation succeeds with integrated code only
- Effort: <5 minutes
- Benefit: Cleaner build, focuses on real issues
- Risk: May want these routes later

**Option C: Register and fix dead code**
- Import and register unused routes
- Fix all errors
- Effort: ~3-4 hours  
- Benefit: All code is live and tested
- Risk: May activate buggy code

---

## Recommendation

**Option B (exclude dead code) is most honest for this audit:**

The production readiness assessment should focus on what's actually running. Dead unregistered code is a finding that should be documented, not silently fixed.

**Action:** Exclude `goal`, `governance`, `phases-6-8`, `phases-9-13` routes from compilation.

This leaves ~27 real errors in integrated code to fix.

---

## Files to Update

To exclude dead code, either:

1. Move them out of src/routes/
2. Add `tsconfig.json` exclude rule
3. Comment out the export functions

**Recommendation:** Move to `src/routes.disabled/` or mark with `.disabled` suffix

This makes the status clear and reversible.
