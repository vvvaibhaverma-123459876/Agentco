# AgentCo — Autonomous AI Company

AgentCo is a fully autonomous, AI-operated company. Every business function is executed by specialised AI agents operating on a shared infrastructure. Humans exist only at the governance layer: they audit, veto, and reconfigure, but do not initiate or perform operational work.

## Architecture

Three-layer architecture:

```
Layer 1 — Executive Coordination     (CEO, CFO, COO)
Layer 2 — Functional Departments     (9 departments, 26 agents)
Layer 3 — Shared Infrastructure      (Memory, Event Bus, Audit Log, Override Layer)
```

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
| Agents | Python 3.12 + LangGraph + Anthropic SDK |
| LLM | Anthropic Claude (Sonnet 4.6 / Opus 4.8) |
| Task Queue | BullMQ + Redis 7 |
| Event Bus | Apache Kafka |
| Relational DB | PostgreSQL 16 |
| Vector DB | Pinecone |
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| Observability | OpenTelemetry + Grafana |
| Infrastructure | Kubernetes + Helm |
| Secrets | HashiCorp Vault |

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
│   └── src/
│       ├── db/migrations/     # PostgreSQL migrations (8 tables)
│       ├── services/          # Audit log, Event bus, Memory store, Override queue
│       └── routes/            # REST API endpoints
├── frontend/                  # Next.js 14 control dashboard
│   └── src/app/
│       ├── dashboard/         # Agent status (all 29 agents by department)
│       ├── override/          # Human override queue with approve/reject
│       ├── audit/             # Immutable audit log viewer
│       ├── events/            # Real-time event stream
│       ├── performance/       # Per-agent metrics
│       ├── config/            # Prompt version history
│       ├── finance/           # P&L dashboard (CFO-Agent feed)
│       └── incidents/         # Incident log
├── infrastructure/
│   ├── kubernetes/            # Namespaces, network policies, Helm chart
│   ├── kafka/                 # Topic definitions
│   └── vault/                 # Access policies
└── .github/workflows/         # CI (test + lint) + Deploy (Helm)
```

## Local Development

```bash
# Copy environment config
cp .env.example .env
# Edit .env with your Anthropic API key and local service configs

# Start infrastructure
docker-compose up -d

# Run database migrations
cd backend && npm install && npm run db:migrate

# Start backend API
npm run dev

# Start frontend
cd ../frontend && npm install && npm run dev

# Run Python agent tests
cd ../agents && pip install -r requirements.txt && pytest
```

## Key Design Constraints

- **Confidence scoring is mandatory** — every agent output carries a confidence score (0.0–1.0). Downstream agents treat scores below 0.7 as unverified hypotheses.
- **Human override is a hard gate** — high/critical risk actions pause and cannot proceed without a human approval token.
- **Config-Agent has zero autonomy** — every prompt or permission change requires human approval without exception, including emergencies.
- **Privacy breach response is hardcoded** — suspected data breach triggers immediate human escalation with no autonomous remediation.
- **Reviewer-Agent is the only merge authority** — Coder-Agent cannot merge its own PRs.
- **Auto-rollback thresholds** — DevOps-Agent rolls back automatically at: error rate >5%/5min, latency >3x P99, memory >90%/2min.
- **Audit log is immutable** — append-only, hash-chained, DELETE permission revoked at DB level.

## Build Phases

| Phase | Timeline | Focus |
|---|---|---|
| 1 | Weeks 1–4 | Infrastructure (DB, Kafka, Redis, Vault, K8s) |
| 2 | Weeks 5–8 | Agent runtime (BaseAgent, Config-Agent, Executive) |
| 3 | Weeks 9–16 | All 29 department agents |
| 4 | Weeks 12–16 | Control dashboard (parallel) |
| 5 | Weeks 17–20 | Hardening, evals, security audit |

---

*Version 1.0 · Full-Stack AI Architecture · End-to-End Build Specification*
