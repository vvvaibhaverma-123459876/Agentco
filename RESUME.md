# AgentCo — Resume & Implementation Guide

**Last updated:** 2026-06-25 (rev 14 — active artifact rollback schema)
**Audience:** any AI coding agent (or human) picking up this work.
**Read first:** `CIVILIZATION_AUDIT.md` (the honest inventory this work is based on).

---

## 1. Where we are (ground truth)

The civilization layer has been integrated component-by-component into the deployable app,
proven end-to-end against real Postgres + real OpenAI (`gpt-4o-mini`).

- **Reachability from `backend/src/server.ts`: 65 / 78 services** (was 5).
- **Orphans: 13** — all infra/leaf utilities (see §4), intentionally not REST-exposed.
- **Tests:**
  - Default `jest` (no infra): **154 pass, 0 fail**, 26 gated-skip.
  - Targeted free-run Postgres e2e (`RUN_LIVE_SMOKE=1` + real PG): **12 pass, 0 fail**.
  - Targeted rollback Postgres e2e (`RUN_LIVE_SMOKE=1` + real PG): **1 pass, 0 fail**.
  - Kafka publish still needs Kafka and runs under `RUN_KAFKA_SMOKE=1`.
- **`tsc --noEmit`: 0 errors.**
- Each integration step has a real test (pure logic tested against the REAL function, never a
  copy) + route-level wiring via `build()`. Commits tagged B.1–B.7d, then the fixes below.

### What was proven end-to-end (real LLM + real DB)
- **Grounded claim generation works** (commit `6fcc39f`): the autonomy loop now produces claims
  each carrying a `supportSnippet` that is a verbatim substring of its cited source. Re-ran the
  number-theory e2e 3× with real OpenAI → 7/7/4 grounded claims, 0 rejected (was 0 claims).
  The planner was rewritten to quote source text; grounding also catches numeric-prefixed
  fabrications ("6m theorem"). See memory `e2e_openai_run_2026_06_25`.
- **Civilization endpoints work live** (commit `9d52290`): booting the real app vs real Postgres
  surfaced + fixed 3 defects that mocked tests hid — `civilization.solve` was a SIMULATION (now
  dispatches to real symbolic/ensemble/rag); `POST /api/goals` NOT-NULL violation (now defaults
  autonomy level to safest `L0`); reputation column drift (now derives from specialist scores).
  Guarded by `tests/integration/civilization-smoke.test.ts`. See memory `civilization_live_boot_findings`.

### Known remaining gaps (honest)
- ✅ **Evidence quality — FIXED** (commit `1b55e43`): `src/services/html-extract.ts` now extracts
  the arXiv abstract (`<blockquote class="abstract">`) / clean body text; the executor stores that
  instead of raw HTML[:2000]. Proven by a live integration test (`evidence-extraction.test.ts`,
  gated `RUN_LIVE_SMOKE`) that fetches a real `/abs/` page and asserts a clean abstract is stored.
  NOTE: full autonomy-loop re-validation is currently blocked by **arXiv search-API rate-limiting**
  (transient — falls back to listing pages, producing clean-but-useless nav text → 0 claims). Re-run
  the number-theory e2e once the API recovers to see grounded abstract-based claims flow.
- **Source-quality scoring (NEXT, highest-leverage):** grounding ≠ credibility. The loop will cite a
  junk/vanity preprint (e.g. arXiv 1810.02188 "6m theorem") as long as the words match. Add a
  source-quality / credibility signal (citation count, venue, author reputation, peer-review status)
  so evidence-governance means *trustworthy* evidence, not just *traceable* evidence.
- ✅ **Free-run agenda-driven execution — DONE** (post-`fc65461`): the goal-less free-run slice now
  makes society agenda routing affect bounded task behavior. Agenda records include `societyId`,
  `institutionId`, `taskType`, and `executionDomain`; fixture execution consumes that route and
  produces calibration-promotion work for calibration agendas and research-ingestion work for
  scientific agendas. Reports now write real `claims.jsonl` and `events.jsonl` artifacts. Covered by
  `tests/integration/civilization-free-run.test.ts` with real Postgres assertions.
- ✅ **Free-run contradiction detection — DONE** (post-`f0d523e`): the free-run pass now actively
  checks newly produced claims against recent stored claims for direct polarity conflicts before
  promotion. Detected conflicts persist `contradicted_by` / `contradicts` links on real
  `autonomy_claims` rows, mark the new claim `contradicted`, block promotion, and write
  `contradictions.jsonl` plus a `contradiction_detection` event. Covered by a real Postgres test.
- ✅ **Free-run agent-spawn proposals — DONE** (post-`0479ed2`): the free-run pass now maps agenda
  and contradiction needs to registered specialist roles, copies bounded budgets from
  `SPECIALIST_ROLES`, persists `agent_spawn_proposal` records in `autonomy_memory`, writes
  `agent_spawn_proposals.jsonl`, and explicitly does **not** activate subprocess specialists or
  create `autonomy_team_activations`. Covered by a real Postgres test.
- ✅ **Free-run self-improvement proposals — DONE** (post-`27ea31e`): the free-run pass now records
  structured `self_improvement_proposal` records in `autonomy_memory` with affected files, expected
  improvement, tests to pass, rollback plan, risk level, and protected-surface scan output from
  `ProtectedSurfaceEnforcerService`. It writes `self_improvement_proposals.jsonl` and does **not**
  edit code, create deployable candidates, or promote changes. Covered by a real Postgres test.
- ✅ **Free-run deep self-assessment — DONE** (post-`b8668ff`): the free-run pass now builds a
  `CivilizationHealthSnapshot` from real Postgres state before choosing an internal goal. The
  snapshot covers claim/evidence totals, supported/promoted backlog, unresolved contradiction links,
  overdue unresolved Phase 0b predictions, and weak domains with multiple claims but no promoted
  knowledge. Reports persist the snapshot in `civilization_report.md`, `events.jsonl`, and
  `report.json`. Covered by a real Postgres test that seeds contradictions, stale predictions, and a
  weak domain against the deployed schema.
- ✅ **Free-run governance queue escalation — DONE** (post-`8296f30`): agent-spawn and
  self-improvement proposals now enqueue real pending rows in the existing `override_queue`.
  Agent-spawn proposals use `agent_upgrade`; self-improvement proposals use `config_change`.
  Queue context includes proposal ids, goal id, budgets/files/tests/rollback details, and
  `blocked_until_approved = true`. The rows remain `pending` with no `approval_token`; the free-run
  does **not** activate specialists, generate candidates, or apply changes. Reports now write
  `governance_queue_requests.jsonl` plus a queue event. Covered by a real Postgres test that asserts
  pending queue rows and no `autonomy_team_activations` side effect.
- ✅ **Free-run approval-token/eval preflight — DONE** (post-`27327db`): approved governance queue
  requests can now be checked by `assessGovernanceApprovalReadiness()`. The gate requires the real
  `override_queue` row to be `approved`, the supplied approval token to match, and a completed
  `eval_scorecards` row with `promotion_eligible = true`. Every check writes a
  `governance_approval_preflight` audit record in `autonomy_memory` and returns either `ready` or a
  structured blocked reason. It deliberately does **not** activate specialists, generate candidates,
  consume a ready decision into execution, or promote self-modifications. Covered by a real Postgres
  test for pending override, approved-without-eval, failed eval, passing eval, and no activation side
  effect.
- ✅ **Approved free-run agent-spawn execution — DONE** (post-`3d8a6d5`): a `ready`
  approval/eval preflight can now be consumed by `executeApprovedAgentSpawn()`. The method verifies
  the approved override/eval gate again, starts a real Python specialist subprocess via
  `TeamActivationService`, sends one signed `evaluate_progress` action to `/execute`, terminates the
  process, updates the real `autonomy_team_activations` row to `completed`, and writes an
  `approved_agent_spawn_execution` audit record in `autonomy_memory`. Added stdlib specialist
  runtimes under `backend/agents/autonomy/` for the free-run roles (`claim_validator`, `researcher`,
  `contradiction_hunter`). Covered by a real Postgres + subprocess test.
- ✅ **Approved free-run self-improvement candidates — DONE** (post-`f30da16`): a `ready`
  self-improvement approval/eval preflight can now be consumed by
  `executeApprovedSelfImprovementCandidate()`. The method verifies the approved override/eval gate
  again, creates a real `artifacts` row, immutable `autonomy_episodes` + `trajectory_store`
  evidence, `replay_batches`, a completed `learner_runs` row, an evaluated `learner_candidates` row,
  a sandbox `eval_runs`/`eval_scorecards` record, and an
  `approved_self_improvement_candidate_execution` audit record in `autonomy_memory`. It deliberately
  does **not** edit code or promote the candidate: `promoted_at` stays null, sandbox feedback has
  `promotion_allowed = false`, and the sandbox scorecard has `promotion_eligible = false`. Covered
  by a real Postgres test against all affected tables.
- ✅ **Human-governed self-improvement candidate promotion — DONE** (post-`468e682`): sandbox
  candidates now have a separate second gate. `enqueueSelfImprovementPromotionRequest()` creates a
  new pending `override_queue` row only for an evaluated candidate whose artifact is tested,
  non-simulation-derived, and backed by passed sandbox feedback. `executeApprovedSelfImprovementPromotion()`
  then requires that separate approval token plus a completed promotion-eligible eval before it
  marks the real `learner_candidates` row `promoted`, sets `promoted_at`, marks the `artifacts` row
  `promoted`, and writes `approved_self_improvement_promotion_execution` to `autonomy_memory`.
  A failed promotion eval leaves the candidate `evaluated` and artifact `tested`. This is still not
  deployment or source modification because the active DB has no `active_artifacts`/rollback tables.
  Covered by a real Postgres test for pending queue, failed-eval non-promotion, and successful
  second-gate promotion.
- ✅ **Self-improvement replay/regression evaluator — DONE** (post-`17157b5`): candidate creation
  now performs explicit validation beyond the generic `promotion_eligible` bit. A scorecard marked
  promotion-eligible still blocks if it misses self-improvement floors: safety/planning 1.0,
  calibration 0.99, regression 0.95, and autonomy/memory/tool/reward 0.75. The sandbox also
  re-queries the real `replay_batches` + `trajectory_store` rows and requires non-empty batch size,
  full trajectory coverage, terminal trajectories, and non-negative rewards. Passed
  `replay_validation` and `regression_validation` records are persisted in
  `learner_candidates.eval_feedback_json`; promotion request enqueueing refuses candidates missing
  those passed records. Covered by a real Postgres test that first uses a weak-regression scorecard
  with `promotion_eligible = true` and proves candidate creation blocks, then creates and promotes a
  candidate with passed replay/regression validation.
- ✅ **Active artifact rollback schema — DONE** (post-`383c4d3`): migration
  `064_active_artifact_rollback.sql` now creates real `deployment_snapshots`, `active_artifacts`,
  and immutable `canary_rollback_events` tables against the deployed `artifacts` table. Repaired
  `RollbackService` so active pointer updates run inside transactions, deployment snapshots record
  candidate-vs-previous artifact ids correctly, rollback atomically restores the previous artifact
  pointer, and rollback audit events are append-only. Covered by a real Postgres test that creates
  artifact rows, activates a candidate artifact, snapshots, rolls back, verifies the active pointer,
  reads rollback history, and proves rollback events cannot be updated. This is still pointer-level
  rollback infrastructure only; no autonomous deployment or source-file modification is wired.
- **Claim diversity:** near-duplicate claims; add dedup + prompt for distinct claims across sources.
- **Web search dead:** DuckDuckGo scraper returns nothing; arXiv-only works. Add a search API key
  or replace the backend.
- **Learning loop not proven closed end-to-end** (see §5).
- **Next free-run boundary:** connect promoted self-improvement artifacts to an explicit
  human-governed canary/deployment request that uses `active_artifacts`, or broaden replay
  validation to compare against larger historical trajectory batches. Do not let the free-run
  auto-approve or modify source files.

### Integration method that works (repeat it for any remaining work)
1. Pick an orphaned capability service (`CIVILIZATION_AUDIT.md` lists them).
2. Expose its key methods via a `backend/src/routes/<cluster>.routes.ts` module.
3. Register the module in `backend/src/server.ts`.
4. Add `backend/tests/<cluster>-routes.test.ts`: test pure logic against the real function,
   mock DB/network services at their boundary (`jest.mock`), assert via `app.inject`.
5. Verify reachability went up (BFS script in §6), `tsc` clean, suite green. Commit.

---

## 2. Test tiers & infrastructure (RESOLVED — the 2 old failures are gone)

The previous "2 failures" were **not infra failures**:
- `protected-surfaces.test.ts` was a `console.log` **script with no `it()` blocks** → jest "must
  contain at least one test". **Converted to real assertions** (commit `9d52290`).
- `event-bus.test.ts` mixed pure signature/envelope tests with Kafka-dependent `publish()`. **Split**:
  pure tests always run; Kafka tests gated behind `RUN_KAFKA_SMOKE=1`.

### Three test tiers
| Tier | Command | Needs | Result |
|---|---|---|---|
| Unit/wiring (default) | `cd backend && npx jest` | nothing | **132 pass, 0 fail**, 12 gated-skip |
| Postgres e2e | `RUN_LIVE_SMOKE=1 DATABASE_URL=… npx jest` | Postgres + (LLM key for solve) | **142 pass, 0 fail**, 2 Kafka-skip |
| Kafka e2e | `RUN_KAFKA_SMOKE=1 DATABASE_URL=… npx jest event-bus` | Kafka + Postgres | runs `publish()` |

### Bring up infra (all defined in `docker-compose.yml`)
```bash
docker compose --profile dev up -d            # Postgres, Redis, Kafka, Zookeeper, ...
cd backend && python3 src/db/run_migrations.py
# Postgres e2e (also needs the OpenAI key for /civilization/solve):
set -a; source .codex.env; set +a; export DATABASE_URL="$AGENTCO_TEST_DATABASE_URL"
RUN_LIVE_SMOKE=1 npx jest --forceExit
# Kafka e2e (only when Kafka is up):
RUN_KAFKA_SMOKE=1 npx jest integration/event-bus --forceExit
```
Env: `DATABASE_URL`, `KAFKA_BROKERS`, `EVENT_BUS_SIGNING_KEY`, `LLM_API_KEY`/`LLM_BASE_URL`/
`LLM_MODEL_DEFAULT` (in `.codex.env`). Live boot only enforces production secrets when
`NODE_ENV=production`; dev boot uses `dev-api-key`.

### NOTE: this machine has no Docker
Postgres is running natively (5432) so the Postgres e2e tier passes here. **Kafka is unavailable
(Docker absent)** so the 2 `publish()` tests skip — they are wired/gated correctly and will run
wherever Kafka is up. That is the only unproven-here surface.

### Known minor issue: `--forceExit`
The Jest suite needs `--forceExit`: a constructed calibration service (`dynamic-calibration` /
`phase0b` / `autonomy-forecasting`) holds a **timer handle open** (a `setInterval`, e.g. the
"Auto-calibration started (every 60 minutes)" log on boot). Fix: `.unref()` the returned timer,
or lazy-init it. Also matters for graceful production shutdown.

---

## 3. Single entrypoint (`agentco`) — phased startup (TO BUILD)

**Goal:** one command boots the whole system in dependency order with health gating, instead of
`server.ts` (HTTP) and the autonomy loop (a one-off script) being separate.

**Design — `backend/src/main.ts` (new), invoked by an `agentco` npm script:**

```
Phase 0  PRECHECK    env + secrets present; assertProductionSecrets()
Phase 1  DATA        connect Postgres (db/client), run/verify migrations; connect Redis
Phase 2  MESSAGING   connect Kafka (db/kafka); ensure topics
Phase 3  GOVERNANCE  ProtectedSurfaceEnforcer.verifyProtectedSurfacesExist() — FAIL CLOSED
                     (refuse to start if the 4 policy.py surfaces are missing/changed)
Phase 4  HTTP        build() + listen  (all civilization routes register here)
Phase 5  RUNTIME     start the autonomy loop as a supervised background worker
                     (autonomyOrchestrator) + the task-worker (backend/src/workers/task-worker.ts)
Phase 6  READY       expose /health = ok only after phases 0-5 succeed
```

**Implementation notes**
- Each phase: `async function phaseN(): Promise<void>` that logs start/ok/fail; abort boot on
  failure of phases 0–4 (5 may degrade gracefully).
- Reuse existing pieces: `build()` (server.ts), `autonomyOrchestrator.executeControlledAutonomyLoop`,
  `task-worker.ts`, `ProtectedSurfaceEnforcerService`.
- Add npm scripts in `backend/package.json`:
  `"agentco": "ts-node src/main.ts"`, `"agentco:prod": "node dist/main.js"`.
- Phase 3 makes the constitution a **boot gate** (stronger than the per-change runtime check
  already wired in B.3).
- Suggested: a top-level `Procfile`/compose service `agentco` that runs `npm run agentco` after
  `postgres`+`kafka` are healthy (depends_on with condition: service_healthy).

**Acceptance test:** a new `tests/boot.test.ts` that calls each phase function with infra mocked
and asserts: boot aborts when a protected surface is missing (phase 3 fail-closed), and `/health`
returns ok only after all phases resolve.

---

## 4. The 13 remaining orphans (infra/leaf — DO NOT add REST routes)

These are libraries/workers, not request-handlers. "Integrated" for them means being **called by
a runtime service or the phased bootstrap**, not given an HTTP endpoint:

`event-bus` (used by §2 once Kafka is up), `metrics`, `rate-limiter`, `deadlock-detector`,
`durable-execution`, `input-validator`, `integration`, `load-test-harness`, `simulator`,
`orchestrator` (legacy — verify vs `autonomy-orchestrator`; likely deletable), `reward-calculator`,
`bounded-learning-run`, `trust-policy-canary`.

**To "integrate" them honestly:** wire them where they belong in the §3 bootstrap / runtime
services (e.g. `metrics` + `rate-limiter` as Fastify hooks in `build()`; `event-bus` started in
Phase 2; `reward-calculator`/`bounded-learning-run` called by the learning loop). Confirm `orchestrator`
is dead before deleting.

---

## 5. The comprehensive learning mechanism — status: INTEGRATED (verify end-to-end)

The learning subsystem **is wired** (reachable from server.ts and/or the autonomy orchestrator):

| Service | Reachable from | Role |
|---|---|---|
| `learning.service` | server | exports its own `learningRoutes` (now registered): `/api/learning/stats|signal|insights`, agent learning |
| `learner.service` | server + orch | candidate generation / replay batches |
| `reputation-learning.service` | server + orch | 4-dimensional reputation learning |
| `adaptive-strategy.service` | server + orch | strategy optimization from outcomes |
| `reflection.service` | server + orch | loop-failure reflection fed back to the planner |
| `trajectory-store.service` | server + orch | trajectory persistence for replay |
| `dynamic-calibration.service` | server | per-domain calibration feedback (`/api/calibration/dynamic/*`) |

**Still orphaned (learning-adjacent):** `reward-calculator`, `bounded-learning-run` — wire these
into the learning loop in §4, not as routes.

**What is NOT yet proven (the real gap):** integration ≠ a closed end-to-end learning loop.
Reachability says the modules are connected; it does **not** prove that an autonomy run’s outcomes
flow: outcome → reflection/reputation/adaptive-strategy update → measurably different next decision.
**Next task:** an integration test (needs Postgres) that runs the autonomy loop twice and asserts
the second run’s planner decision changes given stored reflections/reputation — i.e. the loop
actually learns. This is the same discipline as B.1: prove the behavior, don’t trust the wiring.

---

## 6. Tooling — reachability BFS (use to verify every change)

```python
# scratchpad/reach.py — BFS the import graph from an entrypoint
import os, re, glob
SRC="backend/src"
files={os.path.abspath(p):open(p,encoding="utf-8",errors="ignore").read()
       for p in glob.glob(os.path.join(SRC,"**/*.ts"),recursive=True)}
IMPORT=re.compile(r"""(?:import|export)\s+(?:[\s\S]*?\s+from\s+)?['"]([^'"]+)['"]""")
def resolve(i,s):
    if not s.startswith("."): return None
    b=os.path.normpath(os.path.join(os.path.dirname(i),s))
    for c in (b+".ts",os.path.join(b,"index.ts")):
        if os.path.abspath(c) in files: return os.path.abspath(c)
def reach(e):
    seen=set(); st=[os.path.abspath(e)]
    while st:
        c=st.pop()
        if c in seen or c not in files: continue
        seen.add(c)
        for s in IMPORT.findall(files[c]):
            r=resolve(c,s)
            if r and r not in seen: st.append(r)
    return seen
allsv={os.path.abspath(p) for p in glob.glob(os.path.join(SRC,"services/*.ts"))}
server=reach(os.path.join(SRC,"server.ts"))
print("server.ts reaches:", len(server&allsv), "/", len(allsv))
```

---

## 7. Suggested resume order (updated)

0. ✅ **Clean-abstract extraction — DONE** (commit `1b55e43`). Re-run the number-theory e2e once
   arXiv's search API stops rate-limiting to watch grounded abstract-based claims flow.
1. **Source-quality scoring** (HIGHEST leverage now, §1 gaps): grounding ≠ credibility. Add a
   credibility signal so the loop won't cite vanity/junk preprints just because the words match.
   This is what makes "evidence-governed" mean trustworthy, not merely traceable.
2. ✅ **Learning loop CLOSED** (commit `39c2c44`). Proven with a control: a reused goal carrying a
   lesson executed the flagged action 0× (overridden) vs the control's 1×. Diagnosis was that the
   LLM ignores reflectionContext; fix is deterministic enforcement (forbid flagged action types).
   Narrow honest claim: "stops repeating an action prior learning flagged as failing, across runs
   of the same goal." NEXT increment if wanted: retrieve reflections by DOMAIN for fresh runs
   (currently per-goalId via reuse); general learning beyond loop-avoidance is unproven.
3. **Single `agentco` entrypoint** (§3) with the constitution boot-gate + `boot.test.ts`, and an
   env-gated Phase -1 that brings up infra (`AGENTCO_MANAGE_INFRA=1`) for dev convenience.
4. **Fix the timer `.unref()`** so `--forceExit` is no longer needed (§2).
5. **Repair web search** (DuckDuckGo dead) or add a search API key; **claim dedup/diversity**.
6. **Wire the infra/leaf services** where they belong in the bootstrap (§4); delete `orchestrator`
   if confirmed dead. Run the Kafka e2e tier where Kafka is available.
7. Keep the discipline: real test (real function, not a copy) + reachability + green suite, and
   **boot against real infra** before claiming a DB/LLM-backed service works (mocks hide schema
   drift + simulation stubs — that's how the §1 defects were caught).

---

## 8. Commit / branch state

All work on `main`, in order:
- `fface77` de-stub correction · `56b4287` audit (`CIVILIZATION_AUDIT.md`)
- `6b7eef4` B.1 grounding · `ab112e9` credential model B
- `945b6c9` B.2 bridge · `8ef9fe8` B.3 constitution · `661f544` B.4 institutions
- `ae7c7c6` B.5 trust · `5014590` B.6 calibration
- `4f6f931`/`2d01a81`/`e6dcc63`/`d9efc1a` B.7a–d remaining capability services
- `7f24fb2` RESUME.md · `6fcc39f` snippet-quoting grounded claims (e2e proven)
- `9d52290` de-simulate civilization.solve + 2 schema fixes + live e2e smoke suite

Memory (`~/.claude/projects/-Users-Zet-Agentco/memory/`):
`civilization_audit_phase_a.md`, `e2e_openai_run_2026_06_25.md`, `civilization_live_boot_findings.md`.
