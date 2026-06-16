# AgentCo — Autonomous AI Company

AgentCo is a fully autonomous, AI-operated company. Every business function is executed by specialised AI agents operating on a shared infrastructure. Humans exist only at the governance layer: they audit, veto, and reconfigure — but do not initiate or perform operational work.

## V2 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Synthesis Layer        PrincipleLibrary · TheoryEngine          │
├─────────────────────────────────────────────────────────────────┤
│  Learning Loop          Intelligence → Scenario → Trainer        │
│                         → [Human gate] → Memory  (6h cycle)     │
├─────────────────────────────────────────────────────────────────┤
│  Calibration Engine     PredictionLedger · ResolutionService     │
│                         TrustController · RealityFirewall        │
│                         SurpriseRegister · DecayTracker          │
├─────────────────────────────────────────────────────────────────┤
│  Agent Layer (29)       BaseAgentV2 · EscalationGate             │
│                         ConfidenceV2 · AuditLog                  │
├─────────────────────────────────────────────────────────────────┤
│  Infrastructure         PostgreSQL · Kafka · Redis · K8s         │
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

---

*V2 · Calibrated Epistemic Architecture · Local-Model Edition*
