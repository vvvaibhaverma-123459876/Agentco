# Architecture Constitution — Index and Build Plan

This is the master plan for the AgentCo Architecture Constitution: ~34 governing volumes
that together define the entire system, written **in the Order column's sequence** (not
numerically). Conventions and tiers: [`CONVENTIONS.md`](CONVENTIONS.md). Section layout:
[`TEMPLATE.md`](TEMPLATE.md). Automated drift checker:
`scripts/constitution/check_constitution.py` (CI: `.github/workflows/constitution.yml`).

**Why this order:** volumes about working code can be verified against reality
immediately; constitutional and security volumes bind everything after them; dream-stage
volumes stay one-page charters until there is something real to govern.

Volumes 32 (Security & Threat Model) and 33 (Model Governance) were added to the
original 0–31 plan: security machinery already exists in code and deserves
constitutional status, and the system's single LLM call site
(`backend/src/services/llm-provider.service.ts`) needs replacement/upgrade rules now.

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
| 18 | 6 | Institutions | statute | mixed | not written | institution services + migrations (L9) |
| 19 | 5 | Civilization Society | statute | prescriptive | not written | citizen/role services (L7) |
| 20 | 17 | Self Inspection | statute | mixed | not written | scripts/generate_status.py, doctor/audit scripts, BUILD_LEDGER.yaml |
| 21 | 18 | Self Model | statute | prescriptive | not written | BUILD_LEDGER.yaml, backend/src/services/ inventory |
| 22 | 30 | Verification | statute | descriptive | not written | backend/tests/, evals/, .github/workflows/ |
| 23 | 29 | Infrastructure | regulation | mixed | not written | docker-compose*.yml, infrastructure/, helm chart |
| 24 | 27 | Superuser Control Plane | statute | mixed | not written | override-queue.service.ts, kill-switch, frontend override page |
| 25 | 28 | Operator Experience | regulation | mixed | not written | frontend/ pages |
| 26 | 24 | Response Intelligence | regulation | prescriptive | not written | backend routes, autonomy-action-planner.service.ts |
| 27 | 26 | Multi-Agent Civilization | statute | prescriptive | not written | team-activation.service.ts, specialist agents |
| 28 | 25 | Coder Civilization | statute | prescriptive | not written | selfcoding/ |
| 29 | 16 | Autonomous Evolution | statute | prescriptive | not written | goal-formation tick in supervised runtime |
| 30 | 19 | Architecture Evolution | statute | prescriptive | not written | skill-canary.service.ts (promotion pattern to reuse) |
| 31 | 20 | Scientific Research | charter | aspirational | not written | evals/ |
| 32 | 21 | World Models | charter | aspirational | not written | (none) |
| 33 | 22 | Imagination Engine | charter | aspirational | not written | (none) |
| 34 | 31 | Civilization Evolution | charter | aspirational | not written | BUILD_LEDGER.yaml |

## Working agreement

- One volume per working session, in Order-column sequence.
- When starting a volume: read its "primary code to read" first, **draw its architecture
  and capabilities, and present them to the operator** before/while writing.
- Origin `main` is kept continuously updated: each written volume is committed to `main`
  and pushed (operator directive, 2026-07-15).
- A volume is "written" only when `scripts/constitution/check_constitution.py` passes.
