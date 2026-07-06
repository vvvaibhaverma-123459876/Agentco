# Deep Audit: `agents/` (Department Agent Framework)

> Phase 5 update: this audit captured the pre-`672b76e` V1 fail-open behavior.
> Current `BaseAgent.run()` blocks V1 high/critical outputs by raising
> `GovernanceUnavailableError` after audit/override recording. Because V1 has no
> approval-resume path, this is disablement pending approval infrastructure, not
> working approval-gated execution. See `PHASE5_NOTES.md`.

**Date:** 2026-07-05
**Method:** Execute, don't just read. Test suite run; pure core hand-verified with exact
fixtures; governance guarantees exercised through the real `BaseAgent.run()` loop against a
live and a deliberately-broken Postgres. No fixes applied — audit only.
**Environment:** Python 3.13.9, macOS. DB-backed tests pointed at the running Postgres
(`postgresql://Zet@localhost:5432/agentco`); the suite's default DSN is port 5433.
**Scope:** `agents/` only. The `runtime/` `BaseAgentV2`/`EscalationGate` path that the v2
agents delegate into is a separate subsystem, flagged where it changes the verdict.

---

## 0. Shape of the subsystem

`agents/` contains a pure **core** (`core/confidence_scorer.py`, `core/types.py`,
`core/tool_registry.py`, `core/base_agent.py`) plus ~38 department agents across 8
departments. There are **two parallel, overlapping agent hierarchies**:

- **v1** — 29 agents subclassing `agents.core.base_agent.BaseAgent` (all of design, sales,
  marketing, customer_experience, most of people_ops, and a v1 copy of every executive/eng
  agent).
- **v2** — 9 agents subclassing `runtime.base_agent.base_agent_v2.BaseAgentV2`
  (`*_agent_v2.py`). **9 departments have both a v1 and a v2 file for the same role.**

The test suite and `conftest.py` exercise the **v2** path. The `agents/core/base_agent.py`
governance loop audited below is the **v1** path that still backs 29 live agents and 20
roles that have no v2 replacement.

---

## 1. Claims extraction (from code/docstrings/names)

- **C1** `BaseAgent` docstring: "Every output has a confidence_score (enforced, not optional)."
- **C2** `BaseAgent` docstring: "Every decision is written to the audit log."
- **C3** `BaseAgent` docstring: "High/critical risk actions pause for human approval."
- **C4** `BaseAgent` docstring: "Events are published to Kafka via the event bus."
- **C5** `confidence_scorer` module docstring: "Mandatory confidence scoring module. Every
  agent output must pass through this." `score_output` docstring: "Never returns a value
  without evidence."
- **C6** `tool_registry` docstring: "per-agent access enforcement (principle of least
  privilege) — enforced at runtime, not just in prompts."
- **C7** `compute_risk_level`: risk is derived from confidence + action category
  (irreversible/financial escalation).
- **C8** `validate_confidence_attached`: "enforces protocol" — rejects missing/out-of-range
  confidence.

---

## 2. RUN

### 2a. Test suite

`python3 -m pytest agents/tests/` → default DSN (port 5433) unreachable:
**58 passed, 3 failed, 2 errors** (all failures = Postgres socket on 5433).

Repointed at the live Postgres (5432): **61 passed, 1 error**. The remaining error is the
full-dispatch E2E, which needs a `calibration_credentials` table not present here plus a
Kafka broker — genuinely gated on infra, not mocked.

Dependency reality:
- Pure-core tests (`test_confidence_scorer`, `test_base_agent`, `test_event_subscriber`,
  `test_v2_*`, dept unit tests): **no external deps**; LLM is neutralised by `conftest.py`
  injecting a placeholder key. These are the 58 that pass anywhere.
- `test_tool_execution_real.py` (3 tests): **real Postgres**, verified — they insert and read
  back real `decision_log` rows and assert a denied tool writes a real audit entry. Passed
  against 5432.
- `test_agent_dispatch_e2e.py`: **real Postgres + Kafka + optional real LLM**; not run to
  completion here (missing table + no broker).

### 2b. Real entry points

- `execute_tool()` (the runtime access-control gate): driven directly — see §3, it holds.
- `BaseAgent.run()` (the v1 governance loop): driven with a CRITICAL, `requires_human_approval`
  output against a broken DB — see §3/§4, the governance guarantees do **not** hold.

---

## 3. Adversarial

| Promise | Attack | Result |
|---|---|---|
| C2 audit every decision | Run `BaseAgent.run()` with the audit backend down | **BROKE** — `_write_audit` catches the exception, logs `[AUDIT_FAILURE]`, and execution continues. Audit is best-effort, not a gate. |
| C3 high/critical pause for approval | Return a CRITICAL output with `requires_human_approval=True`; call `run()` | **BROKE** — `run()` queues an override request then `return output` unconditionally. It never blocks or raises; the caller receives the irreversible action. With the override backend down, the failure is swallowed (`[OVERRIDE_FAILURE]`) and it still returns. |
| C5 mandatory scoring, never without evidence | grep every dept agent for `score_output` | **BROKE (façade)** — only **1 of 29** v1 agents (`research_agent`) calls `score_output`. The other 28 hardcode literals (`confidence_score=0.99` ×27, `0.85` ×22, `0.88` ×17…). The "mandatory" scorer is bypassed system-wide. |
| C7 risk derived from confidence | grep for `compute_risk_level` invocation in the live loop | **BROKE (dead)** — imported in `base_agent.py`, **never called**; `run()` uses the agent's hardcoded `risk_level` literal. Risk is self-declared, not derived. |
| C5 score_output "never without evidence" | Pass 3 empty-string evidence items `["","",""]` | **BROKE** — empties still count; returns 0.85. Evidence is counted, never inspected. |
| C6 tool least-privilege | Call unpermitted / unknown / empty / None agent ids | **HELD** — `PermissionError` in all four cases; permitted tool allowed. Genuine runtime enforcement. |
| C8 protocol validation | `confidence_score=True` (bool) | **broke (minor)** — accepted: `bool` is an `int` subclass and `0.0<=True<=1.0`. `None`, `"0.5"`, `1.5`, `nan`, missing all correctly rejected. |
| C7 financial guard | `compute_risk_level(0.95, "vendor_payment")` | **undefined/weak** — returns LOW. The financial escalation only fires below 0.7 confidence and never considers amount; a high-confidence $10M payment is LOW risk. |

### Governance loop, executed (the headline break)

```
[AUDIT_FAILURE] ceo-agent: connection ... role "nonexistent" does not exist
[OVERRIDE_FAILURE] ceo-agent: connection ... role "nonexistent" does not exist
run() RETURNED despite CRITICAL + requires_human_approval:
  content    : LAUNCH THE IRREVERSIBLE THING
  risk_level : RiskLevel.CRITICAL
```

The only hard invariant `run()` actually enforces is `validate_confidence_attached` (a
numeric confidence in range) — and that number is a self-assigned literal.

---

## 4. Verification by hand (exact)

**`score_output`** `= min(n·0.15, 0.6) + 0.2·competency + 0.2·specificity`, floor 0.1 on no
evidence. All exact:

| input | expected | got |
|---|---|---|
| no evidence | 0.1 | 0.1 ✅ |
| 2 ev + competency + non-empty | 0.30+0.2+0.2 = 0.70 | 0.70 ✅ |
| 10 ev, wrong domain, non-empty | 0.60+0+0.2 = 0.80 | 0.80 ✅ |
| output `0` (falsy) + 2 ev + competency | 0.30+0.2+**0** = 0.50 | 0.50 ✅ |
| 3 empty-string evidence | 0.45+0.2+0.2 = 0.85 | 0.85 ✅ |
| 4 ev, all bonuses | capped 1.0 | 1.0 ✅ |

Math is correct; the *design* is gameable (empty strings count; a falsy-but-valid output
like `0` silently loses the specificity bonus).

**`compute_risk_level`** — full branch table verified, including the consequential edges:
`financial+0.69→HIGH` but `financial+0.71→LOW` (financial guard evaporates above 0.7);
`0.5→MEDIUM`, `0.7→LOW` (boundaries exclusive); out-of-range `5.0→LOW` (no guard),
`-1.0→CRITICAL` (via `<0.3`). Irreversible categories are CRITICAL at any confidence ✅.

**Tool enforcement** — `execute_tool` denies unknown/empty/None agent (all resolve to empty
permission set) and any tool not in the agent's set; allows a registered permitted tool. ✅

**Test coverage of the loop** — `test_base_agent.py` asserts only the pure helpers
(`validate_confidence_attached`, trust levels, `compute_risk_level`). **The `run()`
escalation/audit path has zero test coverage.**

---

## 5. Capability vs aspiration

| Claim | Verdict | Basis |
|---|---|---|
| C6 tool least-privilege enforcement | **WORKS** | 4/4 adversarial denials + real audit row on denial |
| C8 protocol validation of confidence | **WORKS** (minor bool leak) | rejects missing/None/str/oob/nan |
| score_output arithmetic | **WORKS** | 6/6 exact fixtures |
| C4 events → Kafka | **PARTIAL** | handler is real (real-infra test), but publish failures are swallowed; no delivery guarantee |
| C1 confidence enforced | **PARTIAL** | *presence/range* enforced; the *value* is an unverified literal |
| C2 audit every decision | **FACADE** | best-effort; swallowed on failure, action proceeds |
| C5 mandatory evidence-based scoring | **FACADE** | 1/29 agents call it; 28 hardcode literals |
| C3 high/critical pause for approval | **FACADE** | queues but never blocks; swallowed on failure |
| C7 risk derived from confidence | **ABSENT (dead code)** | `compute_risk_level` never invoked in the loop |

---

## 6. Rot scan

- **Duplicate divergent hierarchies:** 29 v1 agents on `agents.core.base_agent.BaseAgent` vs
  9 v2 agents on `runtime…BaseAgentV2`; 9 roles exist in **both** (`ceo/cfo/coo/coder/devops/
  reviewer/pm/privacy/config`). Two governance models coexist: v1 (queues, non-blocking,
  swallowed) and v2 (raises `HumanApprovalRequired` — a real block, but in `runtime/`). Which
  is "the system" is unresolved; 20 roles have only the weaker v1.
- **Dead code:** `compute_risk_level` imported into `base_agent.py` and never called.
- **Bypassed core:** `score_output`/`compute_risk_level` are the advertised mandatory path;
  the agents route around both with literals.
- **Swallowed exceptions:** ~16 log-and-continue / `except: pass` sites; the load-bearing ones
  are `base_agent._write_audit`, `_request_human_approval`, `publish_event`, and the denied-
  tool audit (`except Exception: pass`, line 255) — every governance side-effect fails open.
- **Stale import paths:** v1 agents use bare `from core.tool_registry import …` /
  `from core.confidence_scorer import …` (no `agents.` prefix), so they import only when
  `agents/` is on `sys.path` directly — inconsistent with the package layout the v2 tests use.
- **Non-portable test defaults:** integration DSN hardcoded to port **5433** `?host=/tmp`
  (the calibration suite uses 5432); no running service listens on 5433 in this environment.
- **Deprecation:** `core/types.py` uses `datetime.utcnow()` (deprecation warning on 3.13).
- **`bool` accepted as confidence** via `isinstance(x, (int,float))`.
- **Self-serving priors:** the most common hardcoded confidence across agents is **0.99**
  (27 occurrences) — agents assert near-certainty about their own outputs by default.

---

## 7. Verdict

### Findings by severity

**BLOCKER**
1. **v1 governance guarantees fail open.** `BaseAgent.run()` neither blocks high/critical
   actions nor guarantees an audit record. Both side-effects are wrapped in swallow-and-
   continue handlers; demonstrated by running a CRITICAL, approval-required action against a
   down backend — it logged two failures and returned the irreversible action to the caller.
   These are the subsystem's central safety claims and they are not enforced.
2. **"Mandatory" confidence scoring is bypassed system-wide.** 28 of 29 v1 agents hardcode
   confidence literals (most commonly 0.99) instead of `score_output`; `compute_risk_level`
   is never called. The numbers that drive trust and (nominally) risk are self-assigned
   theatre, not evidence-derived. Note this directly poisons any downstream consumer — e.g.
   the calibration engine's `trusted_confidence`, which assumes stated confidence is a real
   signal.

**MUST-FIX**
3. Two divergent agent hierarchies with 9 duplicated roles and incompatible governance
   semantics; the weaker (v1) still backs 20 roles and 29 agents, and the `run()` loop has no
   test coverage.
4. Governance side-effects (audit, escalation, event publish) fail open rather than closed.
5. Risk model ignores magnitude (financial guard vanishes above 0.7 confidence; a high-
   confidence multimillion-dollar payment scores LOW).

**NOTE**
6. `score_output` counts empty-string evidence and drops the specificity bonus for falsy-but-
   valid outputs; `bool` accepted as confidence; `datetime.utcnow()` deprecation; port-5433
   test defaults; bare `core.*` imports.

### What it actually is vs. what it intends to be

The intent is a governed multi-agent org where every action carries an evidence-derived
confidence, is risk-classified, is audit-logged, and pauses for a human when it matters.
What actually holds up under execution is narrower: **runtime tool least-privilege is real and
enforced** (the one genuine control), the confidence/risk **helper math is correct**, protocol
presence-checks work, and the DB-backed audit/tool handlers write real rows when the database
is up. Everything above that line is aspiration. The advertised confidence pipeline is
bypassed by 28 of 29 agents in favour of hardcoded 0.99s, the risk-derivation function is dead
code, and the human-approval "hard stop" is a non-blocking queue write that is silently
skipped when it fails. The v2/`runtime` path repairs the escalation into a real exception-
raising gate, but it covers only 9 roles and lives outside this subsystem — so `agents/` today
is a competent tool-permission layer and prompt-routing scaffold wrapped in governance
language it does not enforce. It should not be described as "governed," and its self-reported
confidence numbers must not be fed to any calibration or trust computation as if they were
measurements.
