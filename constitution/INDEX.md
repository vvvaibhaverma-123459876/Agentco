# Architecture Constitution — Index and Build Plan

This is the master plan for the AgentCo Architecture Constitution: 35 governing volumes
(0–34) that together define the entire system, written **in the Order column's sequence**
(not numerically). Conventions and tiers: [`CONVENTIONS.md`](CONVENTIONS.md). Section
layout: [`TEMPLATE.md`](TEMPLATE.md). Automated drift checker:
`scripts/constitution/check_constitution.py` (CI: `.github/workflows/constitution.yml`).

**Why this order:** volumes about working code can be verified against reality
immediately; constitutional and security volumes bind everything after them; dream-stage
volumes stay one-page charters until there is something real to govern.

Volumes 32 (Security & Threat Model) and 33 (Model Governance) were added to the
original 0–31 plan: security machinery already exists in code and deserves
constitutional status, and the system's single LLM call site
(`backend/src/services/llm-provider.service.ts`) needs replacement/upgrade rules now.

**Domain Neutrality (2026-07-15, operator-directed):** no volume — and no permanent
architectural component — may exist solely for a specific knowledge domain or
profession (V0-INV-009, enforced by the checker's domain lexicon). The generalization
pass renamed volumes 18/19/20/21/22/24/25/27, split Self Model into Civilization Self
Model (V18) + Civilization Memory (V34, new), and mandated the six-loop decomposition of
Autonomous Evolution (V16) and the emergent-institution lifecycle (V6). Full rationale,
audit table, and migration impacts: [`GENERALIZATION_REPORT.md`](GENERALIZATION_REPORT.md).

Note: backend migrations live at `backend/src/db/migrations/` (there is no
`backend/migrations/`); migration numbers below refer to files there.

| Order | Vol | Name | Tier | Epistemic status | Doc status | Primary code to read |
|---|---|---|---|---|---|---|
| 1 | 0 | Vision | constitutional | mixed | written | README.md, BUILD_LEDGER.yaml |
| 2 | 1 | Constitutional Core | constitutional | mixed | not written | decision_log migrations (hash chain), governance + judiciary services, backend/src (search "security") |
| 3 | 32 | Security & Threat Model | constitutional | descriptive | not written | backend/src (search "url-safety", SSRF), autonomy-action-planner.service.ts (injection guard), team-activation.service.ts (HMAC), agentco_security/env_guard.py |
| 4 | 9 | Knowledge System | statute | descriptive | not written | claim-grounding.service.ts, evidence registry services, memory-promotion + memory-retrieval services, autonomy_evidence/claims/agent_memories migrations |
| 5 | 11 | Trust & Calibration | statute | descriptive | not written | persistent-trust-scorer.service.ts, falsifiable-prediction services, independent-resolver.service.ts, prediction_ledger migrations, reserve/ |
| 6 | 8 | Missions | statute | descriptive | not written | goal-manager.service.ts, autonomy-orchestrator, autonomy-run, action-executor services |
| 7 | 14 | Learning Engine | statute | descriptive | not written | skill-library.service.ts, skill-canary.service.ts, migrations 105/108, memory promotion pipeline |
| 8 | 15 | Capability Expansion | statute | descriptive | not written | capability-expansion-gate.service.ts, generality-metric-tracker, proof-of-competence, migrations 102/103/106/107 |
| 9 | 13 | Judiciary | statute | descriptive | not written | judiciary*.service.ts, migrations 109/136 |
| 10 | 4 | Identity & Authority | constitutional | mixed | not written | backend/src (search "security"), credential.service.ts, reserve/, migration 052 |
| 11 | 7 | Civilization Economy | statute | mixed | not written | resource ledger + budget services, treasury routes, token budget in llm-provider.service.ts |
| 12 | 12 | Governance | constitutional | mixed | not written | governance/constitution services + migrations |
| 13 | 33 | Model Governance | statute | mixed | not written | llm-provider.service.ts, runtime/base_agent/provider_config.py |
| 14 | 3 | Runtime Operating System | statute | mixed | not written | supervised-runtime + free-run CLIs, outbox-worker, kill-switch services |
| 15 | 2 | Civilization Kernel | constitutional | mixed | not written | backend/src/server.ts, migrate.ts, event_log/outbox, civilization-runtime.service.ts (migration 129) |
| 16 | 10 | Reasoning Engine | article | prescriptive | not written | decision_log migrations, autonomy-action-planner.service.ts |
| 17 | 23 | Constraint Engine | article | prescriptive | not written | budget services, url-safety, fail-closed guards |
| 18 | 6 | Institutions | statute | mixed | not written | institution services + migrations (L9); emergent-institution lifecycle per GENERALIZATION_REPORT.md §11 |
| 19 | 5 | Civilization Society | statute | prescriptive | not written | citizen/role services (L7) |
| 20 | 17 | Self Inspection | statute | mixed | not written | scripts/generate_status.py, doctor/audit scripts, BUILD_LEDGER.yaml |
| 21 | 18 | Civilization Self Model | statute | prescriptive | not written | BUILD_LEDGER.yaml, backend/src/services/ inventory |
| 22 | 34 | Civilization Memory | statute | mixed | not written | memory-promotion-pipeline.service.ts, memory-retrieval.service.ts, event_log + agent_memories migrations |
| 23 | 30 | Verification | statute | descriptive | not written | backend/tests/, evals/, .github/workflows/ |
| 24 | 29 | Infrastructure | regulation | mixed | not written | docker-compose*.yml, infrastructure/, helm chart |
| 25 | 27 | Operator Control Plane | statute | mixed | not written | override-queue.service.ts, kill-switch, frontend override page |
| 26 | 28 | Operator Experience | regulation | mixed | not written | frontend/ pages |
| 27 | 24 | Interaction Intelligence | regulation | prescriptive | not written | backend routes, autonomy-action-planner.service.ts |
| 28 | 26 | Multi-Agent Civilization | statute | prescriptive | not written | team-activation.service.ts, specialist role registry (backend/src/types/specialist-roles.ts) |
| 29 | 25 | Capability Evolution Framework | statute | prescriptive | not written | selfcoding/ (existing single-capability instance to generalize from), skill-library.service.ts |
| 30 | 16 | Autonomous Evolution | statute | prescriptive | not written | goal-formation tick in supervised runtime; six-loop decomposition per GENERALIZATION_REPORT.md §8 |
| 31 | 19 | Structural Evolution Framework | statute | prescriptive | not written | skill-canary.service.ts (promotion pattern to reuse) |
| 32 | 20 | Knowledge Discovery Framework | charter | aspirational | not written | evals/ |
| 33 | 21 | Reality Models | charter | aspirational | not written | (none) |
| 34 | 22 | Hypothesis Generation Framework | charter | aspirational | not written | (none) |
| 35 | 31 | Civilization Evolution | charter | aspirational | not written | BUILD_LEDGER.yaml |

## Working agreement

- One volume per working session, in Order-column sequence.
- When starting a volume: read its "primary code to read" first, **draw its architecture
  and capabilities, and present them to the operator** before/while writing.
- Origin `main` is kept continuously updated: each written volume is committed to `main`
  and pushed (operator directive, 2026-07-15).
- A volume is "written" only when `scripts/constitution/check_constitution.py` passes.
- Domain Neutrality (V0-INV-009) applies to every future volume and revision: domain
  expertise enters through the Capability Evolution Framework (V25), the dynamic domain
  registry (V15), emergent institutions (V6), and the Knowledge Discovery Framework
  (V20) — never as new top-level architecture.
