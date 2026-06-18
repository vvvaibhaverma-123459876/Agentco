# AgentCo — Complete Project Guide

**For any AI tool working on this project. Read this fully before making changes.**

**Repo:** github.com/vvvaibhaverma-123459876/Agentco
**Codebase:** ~16,400 lines (Python ~12,600 | TypeScript ~2,800 | SQL ~940)
**Tests:** 224+ passing, 0 failures
**Last verified:** 2026-06-18

---

## PART 1 — What This Project Is

AgentCo is an AI-operated company whose real invention is an **epistemic
governance layer** — a system that forces AI agents to earn the right to be
believed by predicting before they know the answer and letting reality score
them.

The core rule governing EVERYTHING: **"Only reality promotes."**

No belief, claim, or recommendation reaches trusted status without a
pre-registered, externally-scored, out-of-sample prediction that reality
validated. Confidence, eloquence, simulation agreement, and internal
consensus cannot substitute for being right about the actual world.

The 29-agent company (strategy, engineering, sales, legal, finance, etc.)
is the DEMONSTRATION of this governance layer. The governance layer itself —
the prediction ledger, trust controller, reality firewall, and Epistemic
Reserve — is the actual differentiator. Five independent external analyses
confirmed this is the only part of the architecture not commoditized by
existing frameworks (LangGraph, CrewAI, OpenAI Agents SDK, Microsoft Agent
Framework).

---

## PART 2 — Architecture (layer by layer, top down)

```
┌─────────────────────────────────────────────────┐
│              Epistemic Reserve                   │
│  Proof-of-Calibration credentials, staking,     │
│  publicly recomputable scoring, oracle layer    │
├─────────────────────────────────────────────────┤
│            Calibration Engine                    │
│  Prediction Ledger, Resolution Service,         │
│  Trust Controller, Reality Firewall,            │
│  Surprise Register, Decay Tracker               │
├─────────────────────────────────────────────────┤
│          Civilization Substrate                  │
│  Institutions, Departments, Cross-Review,       │
│  Reputation Propagation, Governance             │
├─────────────────────────────────────────────────┤
│              Agent Layer                         │
│  29 department agents, BaseAgentV2,             │
│  EscalationGate, Confidence scoring             │
├─────────────────────────────────────────────────┤
│            Infrastructure                        │
│  PostgreSQL+pgvector, Kafka, Redis,             │
│  Docker Compose, OpenAI-compatible LLM          │
└─────────────────────────────────────────────────┘
```

### The 10 Non-Negotiable Invariants (NEVER weaken these)

1. Only reality promotes — beliefs reach reality_validated ONLY via
   externally-scored, pre-registered, out-of-sample predictions
2. Prediction ledger is immutable — write-once, DB-enforced, no edit/delete
3. Pre-registration enforced at DB layer — post-hoc excluded from calibration
4. Reality/simulation firewall is a hard gate — sim_support excluded
5. Decisions use trusted_confidence(), not stated confidence
6. Human-approval gates block execution — no timeout auto-approve
7. Outputs carry confidence + producer_prompt_version + HMAC signature
8. Audit log is 100% immutable, hash-chained
9. Config-Agent cannot modify its own prompt
10. Ground truth must originate OUTSIDE the reasoning system

---

## PART 3 — Directory Structure and Key Files

```
Agentco/
├── agents/                    # All 29 department agents
│   ├── core/
│   │   ├── base_agent.py      # V1 base agent
│   │   ├── tool_registry.py   # Tool permissions per agent
│   │   ├── tools/
│   │   │   ├── handlers.py    # Real tool handler implementations
│   │   │   └── web_scraper.py # Internet fetch + claim extraction
│   │   └── memory_client.py   # Memory store client
│   ├── executive/             # CEO, CFO, COO agents
│   ├── engineering/           # Architect, Coder, Reviewer, DevOps
│   ├── product/               # PM, Research, Prioritizer
│   ├── sales/                 # SDR, AE, RevOps
│   ├── marketing/             # Content, SEO, Ads, Analytics
│   ├── customer_experience/   # Support, Success, Voice
│   ├── people_ops/            # Performance, Recruiter, Config
│   ├── legal/                 # Contract, Risk, Privacy
│   ├── design/                # UX, Brand, A/B
│   └── tests/                 # Agent-level tests
│
├── runtime/
│   └── base_agent/
│       ├── base_agent_v2.py   # V2 base agent (all agents extend this)
│       ├── model_tiers.py     # Config-driven provider/model resolution
│       ├── llm_client.py      # LLM client with per-tier provider support
│       └── providers.py       # Provider registry + Anthropic adapter
│
├── calibration/               # The epistemic governance layer
│   ├── ledger/
│   │   └── prediction_ledger.py   # Immutable prediction store (real PG)
│   ├── trust/
│   │   └── trust_controller.py    # Per-agent trust scores by domain
│   ├── firewall/
│   │   └── reality_firewall.py    # Reality/simulation hard gate
│   ├── resolution/
│   │   └── resolution_service.py  # External ground truth scoring
│   ├── scoring/                   # Brier + log scoring
│   ├── surprise/                  # Surprise detection
│   ├── decay/                     # Time-based trust decay
│   └── self_audit/                # Self-audit module
│
├── reserve/                   # The Epistemic Reserve
│   ├── scoring/
│   │   └── scoring_function.py        # Deterministic, recomputable scoring
│   ├── credentials/
│   │   └── proof_of_calibration.py    # Ed25519-signed credentials
│   ├── staking/
│   │   └── staking.py                 # Calibration-weighted staking
│   ├── decisions/
│   │   └── weighted_decision.py       # Belief market decisions
│   ├── oracle/
│   │   └── oracle_layer.py            # Recursive resolution hierarchy
│   ├── chain/
│   │   └── commitment_chain.py        # Tamper-evident commitment chain
│   ├── tools/
│   │   └── recompute_credential.py    # Independent recomputation (no secret)
│   ├── keys/                          # Ed25519 key management
│   ├── migrations/
│   │   ├── 001_reserve_extension.sql  # Hardness + consequence columns
│   │   ├── 002_staking.sql            # Belief questions + stakes
│   │   ├── 003_oracle_layer.sql       # Oracle resolutions
│   │   ├── 004_ed25519_signature.sql  # Ed25519 signature support
│   │   ├── 005_prediction_chain.sql   # Prediction commitment chain
│   │   └── 006_civilization.sql       # Civilization substrate tables
│   └── tests/                         # 14+ Reserve integration tests
│
├── civilization/              # Multi-institution layer
│   ├── domain/                # Institution, Department models
│   ├── services/              # Review, Reputation, Governance, Memory
│   ├── contracts/             # Per-institution YAML contracts
│   ├── controls.yaml          # Anti-chaos controls
│   └── reputation_weights.yaml
│
├── learning/                  # Learning loop (specified, partially wired)
│   ├── intelligence_agent/
│   ├── scenario_agent/
│   ├── trainer_agent/
│   └── memory_agent/
│
├── synthesis/                 # Cross-domain synthesis
│   ├── principle_library/
│   ├── theory_engine/
│   └── synthesis_agent/
│
├── backend/                   # Node.js + Fastify API
│   └── src/
│       ├── server.ts
│       ├── routes/            # agents, audit, override routes
│       ├── services/          # audit-log, event-bus, memory-store,
│       │                      # override-queue (all real PG/Kafka)
│       └── db/
│           ├── migrate.ts     # Migration runner
│           └── migrations/    # 001-014 backend migrations
│
├── frontend/                  # Next.js 14 dashboard (structure only)
├── infrastructure/            # Kubernetes, Vault, Kafka, OTel configs
├── scripts/
│   ├── smoke_one_task.py      # Single-task end-to-end proof
│   └── run_local_agent.py     # Run an individual agent
│
├── evals/
│   ├── acceptance/            # Proof artifacts (traces)
│   └── regression/            # Ledger immutability + persistence tests
│
├── tests/
│   ├── civilization/          # Civilization integration tests
│   └── e2e/                   # End-to-end tests
│
├── docs/
│   ├── runnability_audit.md
│   └── civilization_migration_map.md
│
├── docker-compose.yml         # Full local dev stack
├── .env.example               # Complete config template
├── SYSTEM.md                  # Architecture + invariants
├── SYSTEM_CIVILIZATION.md     # Civilization layer docs
└── README.md
```

---

## PART 4 — Tech Stack

| Component       | Technology                                |
|-----------------|-------------------------------------------|
| Agent runtime   | Python 3.12+ with LangGraph               |
| API layer       | Node.js 20 + Fastify                      |
| Database        | PostgreSQL 16 + pgvector                   |
| Event bus       | Apache Kafka (Confluent 7.6.1)             |
| Cache/queue     | Redis 7                                    |
| Frontend        | Next.js 14 + TypeScript + Tailwind         |
| LLM (default)   | OpenAI gpt-4o / gpt-4o-mini               |
| LLM (local)     | Ollama: phi4, qwen2.5:7b, qwen2.5-coder   |
| Observability   | OpenTelemetry + Prometheus + Grafana       |
| Secrets         | HashiCorp Vault                            |
| Infrastructure  | Docker Compose (dev), K8s + Helm (prod)    |

---

## PART 5 — How to Run (step by step)

### Prerequisites
- Docker Desktop running
- Node.js 18+ installed
- Python 3.12+ installed
- An LLM API key (OpenAI or any OpenAI-compatible provider)

### Step 1 — Clone and enter the repo
```bash
git clone https://github.com/vvvaibhaverma-123459876/Agentco.git
cd Agentco
```

### Step 2 — Start all infrastructure
```bash
docker compose up -d
```
Wait 60-90 seconds for all services to become healthy. Verify:
```bash
docker compose ps
```
You need all of these healthy before proceeding:
- agentco-postgres (port 5432)
- agentco-redis (port 6379)
- agentco-zookeeper (port 2181)
- agentco-kafka (port 9092)
- agentco-vault (port 8200)

**Apple Silicon (M1/M2/M3) note:** If zookeeper stays unhealthy, run:
```bash
sed -i '' 's/echo ruok | nc localhost 2181 | grep imok/nc -z localhost 2181/' docker-compose.yml
docker compose restart zookeeper
```

### Step 3 — Install dependencies
```bash
cd backend && npm install && cd ..
pip3 install -r agents/requirements.txt
```

### Step 4 — Apply database migrations
```bash
npm run db:migrate --prefix backend
```
This applies all 14 backend migrations + you may need to apply Reserve
migrations separately:
```bash
for f in reserve/migrations/0*.sql; do
  psql "postgresql://agentco:password@localhost:5432/agentco" -f "$f" 2>&1
done
```

### Step 5 — Set environment variables
Set these in your terminal BEFORE running any agent or launching Claude Code.
Replace the API key with your real key:
```bash
# LLM Provider (all tiers default to these)
export LLM_PROVIDER=openai
export LLM_BASE_URL=https://api.openai.com/v1
export LLM_API_KEY=sk-your-key-here          # NEVER commit this
export LLM_MODEL_DEFAULT=gpt-4o-mini

# Optional per-tier overrides
export LLM_MODEL_FRONTIER=gpt-4o
export LLM_MODEL_STANDARD=gpt-4o-mini
export LLM_MODEL_MONITOR=gpt-4o-mini
export LLM_MODEL_CODER=gpt-4o-mini

# Database URL for tests and scripts
export AGENTCO_TEST_DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco
export DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco
```

To verify (without printing the key):
```bash
echo "Provider=$LLM_PROVIDER Model=$LLM_MODEL_DEFAULT Key=${LLM_API_KEY:+SET}"
```

### Step 6 — Verify everything works
```bash
# Run the full test suite
python3 -m pytest --tb=short -q
# Expected: 224+ passed, 0 failed

# Run a single-task smoke test (costs ~$0.001)
python3 scripts/smoke_one_task.py
# Expected: 3 IDs printed (audit_log_id, prediction_id, kafka_event_id)
```

---

## PART 6 — What You Can Do With It (run commands)

### A. Single-Task Smoke Test (safest — costs ~$0.001)
```bash
python3 scripts/smoke_one_task.py
```
Dispatches ONE task through the full real path: agent → LLM → audit →
ledger → Kafka. Prints audit_row_id, prediction_id, kafka_event_id.

### B. Internet Prediction Loop (costs ~$0.001)
```bash
python3 scripts/autonomous_prediction_loop.py
```
Scrapes HackerNews, extracts 5 resolvable claims, registers them as
pre-registered predictions in the real PostgreSQL ledger. Then:
```bash
python3 scripts/check_resolutions.py
```
Re-fetches each prediction's resolution URL, LLM-evaluates TRUE/FALSE,
resolves if confidence ≥ 0.80, correctly refuses to guess below that.

### C. Run a Specific Agent
```bash
python3 scripts/run_local_agent.py --agent ceo-agent --task "Analyze Q3 strategy"
```

### D. Full Test Suite
```bash
python3 -m pytest --tb=short -q
```

### E. Real-Infrastructure Tests Only
```bash
python3 -m pytest agents/tests/integration/ reserve/tests/ tests/ evals/regression/ --tb=short -q
```

### F. Backend API
```bash
cd backend && npm run dev
```
API at http://localhost:3001 — endpoints: /agents, /audit, /overrides, /health

---

## PART 7 — LLM Provider Configuration (switching and mixing)

The system is fully config-driven. Switching providers or models is an env
var change, never a code change.

### All-OpenAI (simplest)
```bash
export LLM_PROVIDER=openai
export LLM_BASE_URL=https://api.openai.com/v1
export LLM_API_KEY=sk-...
export LLM_MODEL_DEFAULT=gpt-4o-mini
```

### All-Local (free, no API key)
```bash
export LLM_PROVIDER=ollama
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_API_KEY=ollama
export LLM_MODEL_DEFAULT=qwen2.5:7b
```

### Mixed (Anthropic frontier + OpenAI everything else)
```bash
export LLM_PROVIDER=openai
export LLM_API_KEY=sk-openai-...
export LLM_MODEL_DEFAULT=gpt-4o-mini
export LLM_PROVIDER_FRONTIER=anthropic
export LLM_API_KEY_FRONTIER=sk-ant-...
export LLM_MODEL_FRONTIER=claude-haiku-4-5-20251001
```

### OpenAI-compatible providers (no adapter needed)
OpenAI, Ollama, Together, Fireworks, Groq, DeepSeek, OpenRouter, Mistral.
Just set LLM_BASE_URL to the provider's endpoint.

### Native adapter required
Anthropic (built-in adapter exists).

### Tier map
| Tier     | Agents                        | Default model  |
|----------|-------------------------------|----------------|
| frontier | ceo-agent, cfo-agent, coo-agent | gpt-4o       |
| standard | pm-agent, research-agent, etc.  | gpt-4o-mini  |
| monitor  | support-agent, etc.             | gpt-4o-mini  |
| coder    | coder-agent                     | gpt-4o-mini  |

---

## PART 8 — Proven Capabilities (what's real)

Each capability below has been verified on real infrastructure with real
tests. Proof artifacts are in evals/acceptance/.

| Capability | Proof artifact |
|---|---|
| Immutable prediction ledger (DB-enforced) | evals/regression/test_pg_ledger_immutability.py |
| Reality/simulation firewall | evals/acceptance/seeded_false_belief_trace.md |
| Trust controller updates on evidence | evals/acceptance/first_real_prediction_trace.md |
| Publicly recomputable credentials | evals/acceptance/recomputation_trace.md |
| Ed25519 signed credentials | evals/acceptance/proof_of_calibration_trace.md |
| Tamper-evident commitment chain | evals/acceptance/tamper_evidence_trace.md |
| Calibration-weighted staking (Sybil-resistant) | evals/acceptance/staking_and_decisions_trace.md |
| Oracle self-correction | evals/acceptance/oracle_layer_trace.md |
| Internet prediction loop (3/5 resolved) | evals/acceptance/internet_predictions.md |
| Hash-chained audit log with tamper detection | backend/tests/integration/ |
| Real Kafka event bus with HMAC | backend/tests/integration/ |
| Self-cert ban at DB layer | tests/civilization/ |
| Cross-institution review | tests/e2e/test_institution_operating_loop.py |
| Spend guardrail (refuses, not throttles) | reserve/tests/ |
| Config-driven provider switching | runtime/tests/ |

---

## PART 9 — What Is NOT Built Yet (be honest about these)

- **Agent memory between runs:** agents have no episodic/semantic memory.
  The memory store service exists but automatic capture/retrieval at task
  start/end is not wired into the lifecycle yet. (Work in progress.)
- **Full autonomous multi-agent loop:** individual agents work; the
  agent-triggers-agent event loop has not been run unattended.
- **29 agents fully operational:** definitions exist; execution depends on
  a live LLM and has been proven for a subset only.
- **Frontend:** dashboard structure exists, not exercised against real infra.
- **Production deployment:** runs on Docker Compose (single-node). K8s
  path exists but untested against a real cluster.
- **Full Reserve decentralization:** credentials are signed by a central
  operator (Ed25519). Recomputation is public; the system is operator-run
  but verifiable, not fully decentralized.

---

## PART 10 — Rules for Any AI Working on This Project

### NEVER do these
1. Never weaken any of the 10 invariants for any reason.
2. Never mock a core integration to make a test pass — if a real test
   fails because a feature is incomplete, report it as incomplete.
3. Never claim a capability is "done" unless a real-infra test proves it.
4. Never write a README/SYSTEM.md claim ahead of its proof.
5. Never let a prediction resolve against internal agent output — ground
   truth must come from OUTSIDE the system.
6. Never auto-approve on timeout — human gates block until resolved.
7. Never allow an entity to self-certify its own critical output.
8. Never put API keys in committed files.
9. Never skip a phase gate — if a precondition isn't met, STOP and report.
10. Never over-claim. "5 proven, 3 remaining" is correct. "All done" when
    3 are stubbed is the exact failure this project exists to prevent.

### ALWAYS do these
1. Real infrastructure for tests (Postgres, Kafka) — no mocks for
   integrations.
2. Documentation tracks proof: update docs only when a test passes, in the
   same commit as the code change.
3. Small, separately-committed PRs. Diagnose before editing.
4. If a change requires touching a constraint-protected file, STOP and ask.
5. Run the full test suite after changes: python3 -m pytest --tb=short -q
6. Under-claim, never over-claim. Partial is fine; dishonest is not.

### When you encounter a problem
1. Check if infrastructure is running: docker compose ps
2. Check DATABASE_URL is set: echo $DATABASE_URL
3. Check LLM config: echo $LLM_PROVIDER $LLM_MODEL_DEFAULT
4. Run the specific test in isolation with -v flag for details
5. Read the actual error — don't guess at fixes
6. If the error is "column not found" — a migration probably needs applying
7. If a test passes as mock but fails against real infra — the real failure
   is the truth; the mock was hiding it

### Spend safety (when using paid LLM APIs)
- Set the spend cap LOW for first runs (single-digit dollars)
- Set a monthly budget limit in your LLM provider's dashboard as a backstop
- Run scripts/smoke_one_task.py FIRST (one task, ~$0.001) before anything
  larger
- Never run the autonomous loop unattended without confirming the spend
  guardrail halts calls when exceeded
- The SpendGuardrail REFUSES new calls (does not throttle) — this is
  verified by test

---

## PART 11 — Database Reference

### Connection
```
Host: localhost
Port: 5432
User: agentco
Password: password
Database: agentco
DSN: postgresql://agentco:password@localhost:5432/agentco
```

### Backend migrations (backend/src/db/migrations/)
Applied in order 001-014:
001_agent_state, 002_agent_memory, 003_shared_knowledge, 004_decision_log,
005_event_history, 006_prompt_registry, 007_performance_metrics,
008_customer_data, 009_trust_scores, 010_beliefs, 011_prediction_ledger,
012_decision_log_chain, 013_override_queue, 014_decision_log_immutability

### Reserve migrations (reserve/migrations/)
Applied after backend migrations, in order 001-006:
001_reserve_extension (hardness + consequence on ledger),
002_staking (belief_questions + belief_stakes),
003_oracle_layer (oracle_resolutions + oracle_standing),
004_ed25519_signature (Ed25519 signature support),
005_prediction_chain (commitment chain),
006_civilization (institutions + departments + reviews + governance)

### Key tables and their guards
| Table | Guard | Enforcement |
|---|---|---|
| prediction_ledger | No UPDATE/DELETE | DB trigger |
| decision_log | No UPDATE/DELETE + hash chain | DB trigger |
| institution_output_reviews | reviewer ≠ producer | CHECK constraint |
| institutions.reputation_score | Write requires memory event | DB trigger |
| departments.reputation_score | Write requires memory event | DB trigger |
| belief_stakes | Write-once | DB trigger |

---

## PART 12 — Proof Artifacts Reference

These files in evals/acceptance/ contain real traces — actual database rows,
event IDs, and audit entries from real runs on real infrastructure.

| File | What it proves |
|---|---|
| seeded_false_belief_trace.md | A false belief injected into the system is caught by the reality firewall and quarantined before driving any decision |
| first_real_prediction_trace.md | Complete prediction→resolution→scoring→trust-update cycle with real Postgres, real scoring, real trust change |
| proof_of_calibration_trace.md | A signed credential correctly reflecting an agent's track record |
| recomputation_trace.md | An independent recomputation from raw ledger rows matches the stored credential |
| tamper_evidence_trace.md | Tampering with a resolved prediction is detected by the commitment chain |
| staking_and_decisions_trace.md | Calibration-weighted staking with Sybil-zero-weight property |
| oracle_layer_trace.md | An oracle contradicted by harder reality loses standing automatically |
| internet_predictions.md | 5 real predictions from HackerNews: 3 resolved same-day, 2 correctly held pending |

---

## PART 13 — The One-Sentence Summary

AgentCo is an AI-operated company whose real invention is a system that
makes AI earn the right to be believed — by predicting before it knows,
letting reality be the judge, and building an unforgeable track record of
demonstrated contact with truth.
