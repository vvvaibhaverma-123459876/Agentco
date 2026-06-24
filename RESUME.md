# AgentCo — Resume & Implementation Guide

**Last updated:** 2026-06-25
**Audience:** any AI coding agent (or human) picking up this work.
**Read first:** `CIVILIZATION_AUDIT.md` (the honest inventory this work is based on).

---

## 1. Where we are (ground truth)

The civilization layer has been integrated component-by-component into the deployable app.

- **Reachability from `backend/src/server.ts`: 65 / 78 services** (was 5).
- **Orphans: 13** — all infra/leaf utilities (see §4), intentionally not REST-exposed.
- **Tests: 129 pass, 2 fail** — both *infrastructure-only* (need Postgres + Kafka, see §2).
- **`tsc --noEmit`: 0 errors.**
- Each integration step has a real test (pure logic tested against the REAL function, never a
  copy) plus route-level wiring tests via `build()`. Commits are tagged B.1–B.7d.

### Integration method that works (repeat it for any remaining work)
1. Pick an orphaned capability service (`CIVILIZATION_AUDIT.md` lists them).
2. Expose its key methods via a `backend/src/routes/<cluster>.routes.ts` module.
3. Register the module in `backend/src/server.ts`.
4. Add `backend/tests/<cluster>-routes.test.ts`: test pure logic against the real function,
   mock DB/network services at their boundary (`jest.mock`), assert via `app.inject`.
5. Verify reachability went up (BFS script in §6), `tsc` clean, suite green. Commit.

---

## 2. Resolving the 2 infrastructure test failures

The failures are **not logic bugs** — the services are real, they just need their backing infra.

| Failing test | Needs | Why |
|---|---|---|
| `tests/integration/event-bus.test.ts` | **Kafka** at `localhost:9092` | `EventBusService.publish` produces to Kafka (`backend/src/db/kafka.ts`, `KAFKA_BROKERS`). |
| `tests/protected-surfaces.test.ts` | **Postgres** at `localhost:5432` | enforcer writes/reads verification rows in `autonomy_memory`. |

### Steps to make them pass (everything already exists in `docker-compose.yml`)
```bash
# 1. Bring up infra (Postgres, Redis, Kafka, Zookeeper, ...). Profiles: minimal|dev|full|demo
docker compose --profile dev up -d

# 2. Wait for healthchecks, then run DB migrations
#    DSN default already matches compose: postgresql://agentco:password@localhost:5432/agentco
cd backend && python3 src/db/run_migrations.py

# 3. (Kafka) topics auto-create on first publish; if disabled, create agentco.events* topics.

# 4. Run the full suite WITHOUT --forceExit (handles should close once infra is real)
cd backend && npx jest
# Expect: event-bus + protected-surfaces now green.
```
Env vars consumed (defaults work with compose): `DATABASE_URL`, `KAFKA_BROKERS`,
`EVENT_BUS_SIGNING_KEY`, `LLM_API_KEY` (only needed when the planner actually calls an LLM).

### Known minor issue to fix while here
The Jest suite currently needs `--forceExit`: a constructed calibration service
(`dynamic-calibration` / `phase0b` / `autonomy-forecasting`) holds a **timer handle open**.
Fix: find the `setInterval` in those constructors and call `.unref()` on the returned timer
(or guard construction behind a lazy getter, as was done for the planner's `LLM_API_KEY` check
in `autonomy-action-planner.service.ts`). This also matters for graceful production shutdown.

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

## 7. Suggested resume order

1. **Infra green** (§2): `docker compose --profile dev up -d`, migrate, run suite → 131/131.
2. **Fix the timer `.unref()`** so `--forceExit` is no longer needed (§2).
3. **Single `agentco` entrypoint** (§3) with the constitution boot-gate + `boot.test.ts`.
4. **Close the learning loop** with the end-to-end test (§5) — the real unproven gap.
5. **Wire the infra/leaf services** where they belong in the bootstrap (§4); delete `orchestrator`
   if confirmed dead.
6. Keep the discipline: real test (real function, not a copy) + reachability + green suite per commit.

---

## 8. Commit / branch state

All work is on `main`, committed in order: `fface77` (de-stub correction), `56b4287` (audit),
`6b7eef4` (B.1), `ab112e9` (credential model B), `945b6c9` (B.2), `8ef9fe8` (B.3), `661f544` (B.4),
`ae7c7c6` (B.5), `5014590` (B.6), `4f6f931`/`2d01a81`/`e6dcc63`/`d9efc1a` (B.7a–d).
Memory index: `~/.claude/projects/-Users-Zet-Agentco/memory/civilization_audit_phase_a.md`.
