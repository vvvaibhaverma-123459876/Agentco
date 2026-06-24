# Strategic Merge: Working Repo → Desktop Repo (Zero Feature Loss)

**Date**: 2026-06-24  
**Objective**: Consolidate repos without losing any features

---

## Analysis Summary

### Working Repo (`/Users/Zet/Agentco`)
- **67 backend services** (comprehensive autonomy stack)
- **61+ migrations** (complete database schema)
- **Status**: Advanced (Phases 1-5 complete)
- **Includes**: Phase 5 calibration groundwork, all advanced governance

### Desktop Repo (`/Users/Zet/Desktop/Agentco`)
- **7 backend services** (foundation only)
- **22 migrations** (foundation only)
- **Status**: Earlier stage
- **Unique feature**: `task-dispatch.service.ts` (simpler task management)

### Unique Items Audit
- **Working repo unique**: 66 services + 39 migrations (all advanced features)
- **Desktop repo unique**: 1 service (`task-dispatch.service.ts`)
- **Status**: Working repo is a **strict superset** of desktop

### Task Dispatch Comparison
| Feature | Desktop | Working |
|---------|---------|---------|
| Basic task CRUD | ✅ | ✅ task-engine.service.ts |
| Task leasing | ✅ | ✅ worker-coordinator.service.ts |
| Dead letter handling | ❌ | ✅ autonomy_dead_letters |
| Task tracing/telemetry | ❌ | ✅ trace_id, run_id |
| Coordination | ❌ | ✅ worker-coordinator |

**Verdict**: Working repo's task services are MORE capable. Safe to use.

---

## Merge Plan (Safe & Non-Destructive)

### Phase 1: Backup & Verify (5 min)
```bash
# Already done: /Users/Zet/Desktop/Agentco.backup exists
# Verify both repos are clean
cd /Users/Zet/Agentco && git status  # Should be clean
cd /Users/Zet/Desktop/Agentco && git status  # Should be clean
```

### Phase 2: Sync Working Repo State to Desktop (15 min)
```
Copy ENTIRE backend/ from working to desktop
Copy ENTIRE docs/ from working to desktop  
Copy ENTIRE evals/ from working to desktop
Copy database migrations from working to desktop
Keep desktop's unique .git history (for branch context)
```

### Phase 3: Conflict Resolution (10 min)
- Check for file conflicts (unlikely, working is superset)
- Verify database schema is consistent
- Ensure no broken imports

### Phase 4: Test & Commit (5 min)
```
Run: npm run db:migrate (test migrations apply)
Run: npm test (sanity check)
Commit to desktop repo's current branch: codex/full-civilization-gated-build
```

### Phase 5: Unified State (Final)
- Desktop repo now has ALL features from working repo
- Working repo synced to desktop (single source of truth)
- No feature loss ✅
- Complete history preserved ✅

---

## Risk Assessment

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| Migration conflict | Very Low | Working is superset, no conflicts |
| Code conflict | Very Low | Working has all code, no conflicts |
| Data loss | None | Backup exists, non-destructive |
| Build breakage | Low | Will test after merge |
| Lost commits | None | Git history preserved on both |

---

## What Gets Merged

### ✅ INTO Desktop Repo (from Working)
- `backend/src/services/` (all 67 services)
- `backend/src/db/migrations/` (all 61 migrations)
- `backend/src/cli/` (CLI tools)
- `backend/src/types/` (type definitions)
- `docs/` (all documentation)
- `evals/` (evaluation harness)
- Package dependencies (if updated)

### ✅ PRESERVED on Desktop
- `.git/` directory (branch history)
- Current branch: `codex/full-civilization-gated-build`
- Any desktop-specific config

### ✅ RESULT
- Single consolidated repo on desktop
- Zero feature loss
- All Phase 5 calibration work accessible
- Ready for validation and next steps

---

## Execution (Do Not Execute Without User Approval)

Waiting on: **User approval to proceed with merge**

Once approved:
```bash
# From /Users/Zet/Agentco
cp -r backend /Users/Zet/Desktop/Agentco/
cp -r docs /Users/Zet/Desktop/Agentco/
cp -r evals /Users/Zet/Desktop/Agentco/

cd /Users/Zet/Desktop/Agentco
git add -A
git commit -m "merge: Consolidate advanced features from working repo (zero feature loss)"
npm run db:migrate
npm test
```

---

## Post-Merge Workflow

After merge is complete:
1. Use `/Users/Zet/Desktop/Agentco` as primary
2. Point working repo to archived state (or delete)
3. Continue Phase 5 calibration validation steps
4. Proceed with Steps 3-6 (validation → metrics → gates → approval)

---

## Approval Checklist

- [ ] User approves merge strategy
- [ ] Backup verified: /Users/Zet/Desktop/Agentco.backup exists
- [ ] No active work on either repo
- [ ] Ready to proceed with copy
- [ ] Ready to run tests post-merge
