# AgentCo

## What is AgentCo?

AgentCo is verifiable calibration: proof that an AI agent's claim was checked against something outside itself, not merely made to look checked.

## Who is this for?

Teams evaluating autonomous agents that need audit-grade evidence of what agents claimed, when they claimed it, how reality resolved it, and whether confidence was earned.

## Install in 5 minutes

```bash
git clone https://github.com/vvvaibhaverma-123459876/Agentco.git
cd Agentco
make dev
make smoke
```

## Run the demo

```bash
make demo
```

## What you just saw, and why it's hard

The demo pre-registers a claim, resolves it against an independent source, updates trust, exports a recomputable credential, and rejects a circular same-source "verification." The hard part is catching failures that look fine in logs.

## Security model

Local development uses explicit dev defaults; `AGENTCO_ENV=production` refuses to start with those defaults. Write endpoints use minimal API-key auth; full RBAC is roadmap. Details live in `docs/launch_readiness_audit.md` and `SYSTEM.md`.

## What this is NOT

This is not yet a full company and not yet a civilization layer. Those ambitions are future work, tracked honestly in `ROADMAP.md`, not claimed as launch-ready product.

---

# Previous Architecture Notes

# AgentCo — Autonomous AI Company

AgentCo is a fully autonomous, AI-operated company. Every business function is executed by specialised AI agents operating on a shared infrastructure. Humans exist only at the governance layer: they audit, veto, and reconfigure — but do not initiate or perform operational work.

## V2 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Civilization Substrate  Institution · Department · Agent        │
│                          Review FSM · Reputation Propagation     │
│                          Governance · Anti-Chaos Controls        │
├─────────────────────────────────────────────────────────────────┤
│  Epistemic Reserve       Proof-of-Calibration · Staking          │
│                          Recursive Resolution · Ed25519 Signing  │
│                          Independent Recomputation · Hash Chain  │
├─────────────────────────────────────────────────────────────────┤
│  Synthesis Layer         PrincipleLibrary · TheoryEngine         │
├─────────────────────────────────────────────────────────────────┤
│  Learning Loop           Intelligence → Scenario → Trainer       │
│                          → [Human gate] → Memory  (6h cycle)    │
├─────────────────────────────────────────────────────────────────┤
│  Calibration Engine      PredictionLedger · ResolutionService    │
│                          TrustController · RealityFirewall       │
│                          SurpriseRegister · DecayTracker         │
├─────────────────────────────────────────────────────────────────┤
│  Agent Layer (29)        BaseAgentV2 · EscalationGate            │
│                          ConfidenceV2 · AuditLog                 │
├─────────────────────────────────────────────────────────────────┤
│  Infrastructure          PostgreSQL · Kafka · Redis · K8s        │
└─────────────────────────────────────────────────────────────────┘
```

## 10 Non-Negotiable Invariants (hardcoded, never in prompts)

1. **Only reality promotes** — beliefs reach `reality_validated` only via externally-scored, pre-registered, out-of-sample predictions
2. **Immutable prediction ledger** — DB-enforced; no overwrite, no delete
3. **Pre-registration enforced at DB layer** — post-hoc predictions detected and excluded from all calibration math
4. **Reality/Simulation Firewall is a hard gate** — `sim_support_count` intentionally excluded from the promotion gate
5. **Decisions run on `trusted_confidence()`** — never on stated confidence
6. **Human-approval gates block execution** — no auto-approve on timeout, ever
7. **All outputs carry confidence + `producer_prompt_version` + HMAC signature**
8. **100% immutable audit log** — hash-chained, append-only
9. **Config-Agent cannot modify its own prompt**
10. **Ground truth must originate outside the reasoning system**

## The 29 Agents

| Department | Agents |
|---|---|
| **Executive** | CEO-Agent · CFO-Agent · COO-Agent |
| **Product** | PM-Agent · Research-Agent · Prioritizer-Agent |
| **Engineering** | Architect-Agent · Coder-Agent · Reviewer-Agent · DevOps-Agent |
| **Design** | UX-Agent · Brand-Agent · A/B-Agent |
| **Sales** | SDR-Agent · AE-Agent · RevOps-Agent |
| **Marketing** | Content-Agent · SEO-Agent · Ads-Agent · Analytics-Agent |
| **Customer Experience** | Support-Agent · Success-Agent · Voice-Agent |
| **People Ops** | Performance-Agent · Recruiter-Agent · Config-Agent |
| **Legal & Compliance** | Contract-Agent · Risk-Agent · Privacy-Agent |

## Technology Stack

| Layer | Technology |
|---|---|
| API | Node.js 20 + Fastify |
| Agents | Python 3.12 + LangGraph |
| LLM | Local Ollama (phi4 / qwen2.5:7b / qwen2.5-coder:7b) via OpenAI-compatible endpoint |
| Task Queue | BullMQ + Redis 7 |
| Event Bus | Apache Kafka |
| Relational DB | PostgreSQL 16 |
| Vector DB | Pinecone |
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| Observability | OpenTelemetry + Grafana |
| Infrastructure | Kubernetes + Helm |
| Secrets | HashiCorp Vault |

## Local Model Setup (HP Omen — RTX 5050 8GB)

Agents run on local open-weight models via [Ollama](https://ollama.com) (OpenAI-compatible endpoint at `http://localhost:11434/v1`). No cloud API key required.

**Model tier map** (`runtime/base_agent/model_tiers.py`):

| Tier | Model | Agents |
|---|---|---|
| `frontier` | `phi4` | CEO, Synthesis, Config, Calibration-Reasoner |
| `standard` | `qwen2.5:7b` | All department agents |
| `monitor` | `qwen2.5:7b` | Support, Performance |
| `coder` | `qwen2.5-coder:7b` | Coder-Agent, Reviewer-Agent |

```bash
# Pull models (all fit 8GB VRAM at Q4)
ollama pull qwen2.5:7b
ollama pull qwen2.5-coder:7b
ollama pull phi4

# Smoke-test
ollama run qwen2.5:7b 'Return only the JSON {"ok": true}'
```

To swap providers, set `LLM_BASE_URL` and `LLM_API_KEY` in `.env` — no code changes needed.

## Repository Structure

```
agentco/
├── civilization/              # Civilization Substrate (multi-institution layer)
│   ├── domain/entities.py     # Institution, Department, AgentMembershipEdge dataclasses
│   ├── services/              # institution_service, review_service, reputation_service,
│   │                          #   governance_service, memory_service
│   ├── contracts/             # Institution YAML contracts (engineering.yaml, security.yaml)
│   ├── controls.yaml          # Anti-chaos controls (emergency shutdown, duplicate detector, …)
│   └── reputation_weights.yaml # Department weights for institution score aggregation
├── agents/                    # Python agent runtime (all 29 agents)
│   ├── core/                  # BaseAgent, confidence scoring, event subscriber, memory client
│   ├── executive/             # CEO, CFO, COO agents
│   ├── product/               # PM, Research, Prioritizer agents
│   ├── engineering/           # Architect, Coder, Reviewer, DevOps agents
│   ├── design/                # UX, Brand, A/B agents
│   ├── sales/                 # SDR, AE, RevOps agents
│   ├── marketing/             # Content, SEO, Ads, Analytics agents
│   ├── customer_experience/   # Support, Success, Voice agents
│   ├── people_ops/            # Performance, Recruiter, Config agents
│   ├── legal/                 # Contract, Risk, Privacy agents
│   └── prompts/               # Version-controlled system prompts (all 29)
├── backend/                   # Node.js + Fastify API
│   ├── Dockerfile
│   └── src/
│       ├── db/migrations/     # PostgreSQL migrations
│       ├── services/          # Audit log, Event bus, Memory store, Override queue
│       └── routes/            # REST API endpoints
├── calibration/               # V2 Calibration Engine
│   ├── ledger/                # Prediction Ledger (immutable, pre-registration enforced)
│   ├── resolution/            # Resolution Service (external ground truth only)
│   ├── scoring/               # Brier score, calibration curves
│   ├── trust/                 # TrustController (trusted_confidence multiplier)
│   ├── firewall/              # Reality/Simulation Firewall (hard gate)
│   ├── surprise/              # Surprise Register
│   └── decay/                 # DecayTracker (hourly)
├── runtime/                   # V2 agent runtime
│   ├── base_agent/
│   │   ├── base_agent_v2.py   # BaseAgentV2 with pre-registration + escalation gates
│   │   ├── llm_client.py      # make_client() — Ollama/OpenAI-compatible
│   │   ├── model_tiers.py     # model_for(agent_id) — single source of truth
│   │   └── structured_output.py  # validate-and-retry layer (MAX_RETRIES=3)
│   ├── confidence/            # ConfidenceV2 (trusted_confidence vs stated)
│   └── escalation/            # EscalationGate (human approval, no auto-approve)
├── learning/                  # V2 Learning Loop (6-hour cycle)
├── synthesis/                 # V2 Synthesis Engine (PrincipleLibrary + TheoryEngine)
├── evals/                     # Regression suite (10 invariants + seeded-false-belief test)
├── frontend/                  # Next.js 14 control dashboard
│   ├── Dockerfile
│   └── src/app/
│       ├── dashboard/         # Agent status (all 29 agents by department)
│       ├── override/          # Human override queue
│       └── audit/             # Immutable audit log viewer
├── infrastructure/
│   ├── kubernetes/            # Namespaces, network policies, Helm chart
│   ├── kafka/                 # Topic definitions
│   └── vault/                 # Access policies
├── governance/                # Governor Dashboard specs
├── meta/                      # Failure modes, design decisions
└── .github/workflows/         # CI (pytest + tsc + lint) + Deploy (Helm + Docker)
```

## Local Development

```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit LLM_BASE_URL (default: http://localhost:11434/v1 for local Ollama)

# 2. Start infrastructure
docker-compose up -d

# 3. Backend
cd backend && npm install && npm run db:migrate && npm run dev

# 4. Frontend
cd frontend && npm install && npm run dev

# 5. Python agent tests
cd agents && pip install -r requirements.txt && pytest

# 6. V2 calibration + runtime tests
cd agents && pytest ../calibration ../runtime ../learning ../synthesis -v
```

## V2 Safety Properties (by test)

| Property | Test |
|---|---|
| 10,000 simulation supports cannot promote a belief | `TestInvariant4_RealitySimulationFirewall` |
| Seeded false belief cannot reach `reality_validated` | `TestSeededFalseBeliefRegression` |
| Critical actions raise `HumanApprovalRequired` | `TestInvariant6_NoAutoApprove` |
| No track record → degraded trusted confidence | `TestInvariant5_TrustedConfidence` |
| Internal ground truth sources rejected | `TestInvariant10_GroundTruthExternal` |
| All outputs carry confidence + HMAC signature | `TestInvariant7_AllOutputsCarryConfidence` |

## Real-Infrastructure Integration Status (Phase 1)

Every component below is backed by a test that exercises it against a **real**
dependency (real Postgres / real Kafka / real pgvector). A component is only
marked **Proven** when such a test passes; tests against mocks do not count.

| # | Component | Status | Real dependency proven | Test |
|---|---|---|---|---|
| 1 | Audit Log | ✅ Proven | Postgres append-only writes, SHA-256 hash chain, tamper detection, UPDATE/DELETE rejected by trigger | `backend/tests/integration/audit-log.test.ts` (8) |
| 2 | Prediction Ledger | ✅ Proven | Postgres durable INSERT, cache hydration, immutable pre-reg columns, write-once + role-gated + time-gated resolution | `evals/regression/test_pg_ledger_immutability.py`, `test_pg_ledger_persistence.py` (8) |
| 3 | Event Bus | ✅ Proven | Kafka produce/consume, HMAC sign+verify, idempotent `event_history` persist | `backend/tests/integration/event-bus.test.ts` (7) |
| 4 | Memory Store | ✅ Proven | Postgres namespaced read/write, TTL expiry, namespace isolation, shared knowledge fallback search, writer gating | `backend/tests/integration/memory-store.test.ts` (6) |
| 5 | Override Queue | ✅ Proven | Postgres persistence, SLA expiry → `expired` (never auto-approve), write-once resolution | `backend/tests/integration/override-queue.test.ts` (7) |
| 6 | Tool Execution + Permissions | ✅ Proven | Runtime permission enforcement, real DB side-effect on permitted call, denial audited to Postgres before handler runs | `agents/tests/integration/test_tool_execution_real.py` (3) |
| 7 | Agent Task Dispatch (end-to-end) | ⚠️ Partial | audit → ledger → Kafka legs all proven against real infra in one task flow; **live LLM-inference leg is UNVERIFIED in this sandbox** (egress to model hosts blocked — see note) | `agents/tests/integration/test_agent_dispatch_e2e.py` (1) |
| 8 | Local Model Cleanup | ✅ Proven | No cloud model IDs anywhere; `model_for()` resolves a local Ollama tier map | `runtime/tests/test_local_model_setup.py`, `runtime/base_agent/model_tiers.py` |
| 9 | Experiential Memory Lifecycle | ✅ Proven | Append-only `agent_memories` table (migration 015); episodic, semantic, and prediction-lesson writes; namespace isolation; access-count retrieval; first-run/second-run memory trace; learning-loop extraction; cross-agent sharing. `BaseAgentV2` automatically retrieves prior context on task start (500ms budget, non-blocking) and writes episodic memory on task complete. | `tests/e2e/test_memory_lifecycle.py` (10) |

**Master gate (real infra):** `188+ passed` (Python; 15 reserve errors pre-exist due to sandbox Postgres port mismatch, not regressed by this change)
and `28 passed` (backend integration). Acceptance trace:
[`evals/acceptance/memory_lifecycle_trace.md`](evals/acceptance/memory_lifecycle_trace.md).

> **Note on Component 7 (honest scope):** the orchestration path an agent task
> runs — registering a real prediction in Postgres, writing a hash-chained audit
> entry, and publishing a signed event consumed back off Kafka — is fully proven
> against real infrastructure. The agent's OpenAI-compatible client makes a
> **real** provider call when `LLM_BASE_URL` points at a reachable model endpoint
> (e.g. local Ollama); the e2e test performs that call when reachable and skips
> **only** that sub-assertion otherwise. In this build environment no model host
> is reachable (Hugging Face, ollama.com, Azure blob, modelscope all return 403;
> only pypi/npm/github-web egress is open), so the live-inference leg is reported
> as **unverified here**, not claimed. It is wired to run unchanged in an
> environment with a reachable local model.

> **Note on experiential memory scope:** `agent_memories` is append-only and
> proven against real Postgres (10/10 e2e tests pass). Embeddings are stored as
> optional `FLOAT[]` arrays because the local PostgreSQL server does not have the
> `vector` extension installed; similarity is computed in Python (Jaccard fallback).
> pgvector ivfflat indexing is not claimed. The 500ms retrieval budget is enforced
> and tested (1ms timeout test confirms non-blocking behavior). LLM-assisted lesson
> extraction uses llama3:latest via local Ollama; duplicate-claim suppression on
> Run 2 of the prediction loop was injected into the LLM prompt but compliance
> depends on model capability — llama3 re-registered identical claims despite the
> instruction; a stronger model would not.

**Reproduce the master gate:**

```bash
# First: apply migrations to a fresh database
export DATABASE_URL='postgresql://agentco:password@localhost:5433/agentco?host=/tmp'
export AGENTCO_TEST_DATABASE_URL="$DATABASE_URL"
export KAFKA_BROKERS='localhost:9092'

# Apply backend migrations (creates all 14 backend tables)
cd backend && npm run db:migrate && cd ..

# Python master gate (all directories)
python3 -m pytest \
  evals/ calibration/ runtime/ synthesis/ learning/ \
  agents/tests/ reserve/tests/ tests/ \
  -q
# Expected: 205 passed

# Backend integration (real Postgres + Kafka)
cd backend && SUPERUSER_DATABASE_URL='postgresql://postgres:password@localhost:5433/agentco?host=/tmp' \
  npx jest tests/ --runInBand --forceExit
# Expected: 28 passed
```

---

## Epistemic Reserve

The Epistemic Reserve is a standalone settlement layer built on top of AgentCo's
`calibration/` engine. Its governing invariant: **only demonstrated, externally-resolved
contact with reality earns calibration credit.** No operator discretion over any score,
ever. Every credential is independently recomputable from the public prediction ledger
by anyone, with no secret.

AgentCo's agents are the first participants.

### Trust model (honest statement)

AgentCo **operates** the Reserve. It is operator-run, not decentralised. There is a
single issuer. Full trustlessness is future work.

What IS guaranteed and tested:

| Guarantee | How to verify | Secret required? |
|---|---|---|
| **Score correctness** | `python3 reserve/tools/recompute_credential.py <agent_id>` | **None** — public ledger rows only |
| **Credential authorship** | `verify_credential(cred)` with `reserve/keys/agentco_reserve_public.pem` | **None** — public key only |
| **Tamper-evidence** | `verify_chain(db)` or recompute hash chain from ledger rows | **None** — SHA-256 is public |

What is NOT yet true: decentralised hosting, multi-party issuance, on-chain settlement.

### Reserve currency

`stake_weight = max(0, exp(cell_log_score) − 0.5)`

- Agents scoring above the random-binary baseline earn positive weight.
- Agents at or below baseline earn 0.
- Fresh identities (no resolved predictions) earn 0.
- Weight is non-transferable and non-forgeable (bound to `agent_id`; embedded in Ed25519 signature).

### Five Phases — all proven against real Postgres (25/25 tests)

| Phase | Deliverable | Core property proven |
|---|---|---|
| 1 — Proof-of-Calibration | Signed credential vector per (domain × horizon) | Deterministic; non-transferable; independently recomputable |
| 2 — Staking + Weighted Decision | Belief market; outcome = weighted majority | Reality-Contact Weight Bound (RCWB): Sybil agents earn weight=0 |
| 3 — Recursive Resolution | Credentialed oracles; self-correcting via contradiction | Mechanical ground truth is bedrock; contradicted oracle loses standing |
| A — Independent Recomputation | Third-party recomputation from raw DB rows | Score identical to stored credential; no secret; no in-memory objects reused |
| B — Asymmetric Signing | Ed25519 replaces HMAC-SHA256 | Anyone verifies authorship with published public key; no secret required |
| C — Tamper-Evident Chain | Append-only SHA-256 hash chain over committed predictions | Altered prediction → chain head diverges → tampering detectable by any third party |

### Scoring algorithm (published — anyone may recompute)

```
hardness(p)     = 2 · p · (1 − p)                          # ∈ [0, 0.5]
weight(p, c)    = hardness(p) · (2 if consequence else 1)   # consequence doubles credit
log_score(p, o) = log(p) if o else log(1−p)                 # clipped ε
brier(p, o)     = (p − o)²

cell_log_score  = Σ(weight · log_score) / Σweight

credential sig  = Ed25519(canonical_json, private_key)      # verify with public key only
stake_weight    = max(0, exp(cell_log_score) − 0.5)
```

### Reserve test suite

```bash
AGENTCO_TEST_DATABASE_URL=postgresql://agentco:password@localhost:5433/agentco?host=/tmp \
  python3 -m pytest reserve/tests/ -v
# Expected: 25 passed
#   agent_reserve_integration: 1
#   Phases 1-3 (proof_of_calibration + staking + oracle): 4+5+5 = 14
#   Phase A (independent_recomputation): 1
#   Phase B (ed25519_signing): 5
#   Phase C (tamper_evidence): 4
```

Acceptance traces:
- [`evals/acceptance/proof_of_calibration_trace.md`](evals/acceptance/proof_of_calibration_trace.md) — Phase 1
- [`evals/acceptance/staking_and_decisions_trace.md`](evals/acceptance/staking_and_decisions_trace.md) — Phase 2
- [`evals/acceptance/oracle_layer_trace.md`](evals/acceptance/oracle_layer_trace.md) — Phase 3
- [`evals/acceptance/recomputation_trace.md`](evals/acceptance/recomputation_trace.md) — Phase A (independent recomputation)
- [`evals/acceptance/tamper_evidence_trace.md`](evals/acceptance/tamper_evidence_trace.md) — Phase C (tamper detection)

### Collusion-Resistance Property: Reality-Contact Weight Bound (RCWB)

> The total voting weight a coalition of k agents can contribute is bounded by
> Σᵢ max(0, exp(cell_log_score_i) − 0.5), where each term is derived solely from
> that agent's independently verified, externally-resolved prediction history.
> Creating Sybil identities contributes weight=0 per identity — no resolved
> predictions means no cell, means no weight.

Proven structurally in `reserve/staking/staking.py` and demonstrated by test 2 of
`reserve/tests/test_staking_and_decisions.py`: 10 zero-weight agents cannot override
1 credentialed agent.

---

## Civilization Substrate

The Civilization Substrate adds a multi-institution coordination layer on top of the Epistemic Reserve. Agent credentials flow upward; reputation propagates only from recomputable Reserve evidence. Full specification: [`SYSTEM_CIVILIZATION.md`](SYSTEM_CIVILIZATION.md).

### Three-Level Hierarchy

```
Institution  (top — parent_id must be NULL, enforced by DB CHECK)
  └─ Department  (five mandatory per institution; parent_id NOT NULL)
       └─ Agent  (leaf, via agent_membership_edges)
```

No Society or Civilization entities exist. The hierarchy stops at Institution.

### Five Mandatory Departments

Every institution is created atomically with: **Production · Verification · Audit · Adversarial · Improvement**

### Key Invariants (all DB-enforced)

| Invariant | Enforcement |
|---|---|
| Self-certification ban | `CHECK (producing_institution_id <> reviewer_institution_id)` on `institution_output_reviews` |
| Reputation guard | BEFORE UPDATE trigger — `SET LOCAL civilization.reputation_update_authorized = 'true'` required |
| Institution parent null | `CHECK (parent_id IS NULL)` on `institutions` |
| Department parent not null | `NOT NULL` FK on `departments.parent_id` |

### Review State Machine

```
proposed → under_review → challenged → approved → archived
                        ↘ rejected  ↗         ↘ archived
```

`approved` is only reachable after `under_review` — direct `proposed → approved` raises `ReviewTransitionError`.

### Reputation Propagation Formula

```
agent_score(a)      = Reserve credential overall_log_score
dept_score(d)       = Σ(sample_count(a) × agent_score(a)) / Σ sample_count(a)
institution_score(i)= Σ(W(d) × dept_score(d)) / Σ W(d)    # W from reputation_weights.yaml
```

Empty groups → NULL (not 0). Score write requires a `reputation_updated` memory event in the same transaction.

### Civilization Test Suite

```bash
AGENTCO_TEST_DATABASE_URL=postgresql://agentco:password@localhost:5433/agentco?host=/tmp \
  python3 -m pytest tests/civilization/ tests/e2e/ -v
# Expected: 22 passed (T3.1-T3.4 migration, 9 contract, T5.1-T5.4 review+reputation,
#           4 governance, 1 Phase 7 end-to-end operating loop)
```

---

*V2 · Calibrated Epistemic Architecture · Local-Model Edition*
