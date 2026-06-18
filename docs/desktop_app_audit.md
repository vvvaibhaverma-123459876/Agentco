# AgentCo Desktop App — Pre-Build Audit

## Existing Frontend (Next.js 14.2.5, `frontend/`)

### Pages (src/app/)
| Route | File | What It Does | Backend-Connected |
|-------|------|-------------|-------------------|
| / | page.tsx | Redirect to /dashboard | - |
| /dashboard | dashboard/page.tsx | Agent status grid, 29 agents across 9 departments, polls /api/agents every 10s | YES - /api/agents |
| /audit | audit/page.tsx | Audit log viewer with chain integrity check | YES - /api/audit, /api/audit/integrity |
| /override | override/page.tsx | Human override queue (approve/reject) | YES - /api/overrides |
| /config | config/page.tsx | Configuration page | Partial |
| /events | events/page.tsx | Real-time event stream via WebSocket (/ws/events) | YES - WebSocket |
| /finance | finance/page.tsx | Finance metrics | Unknown - may be static |
| /incidents | incidents/page.tsx | Incidents view | Unknown - may be static |
| /performance | performance/page.tsx | Performance metrics | Unknown - may be static |

### Shared Components
- `src/components/Sidebar.tsx` — navigation sidebar
- `src/lib/api.ts` — typed API client (agents.list, agents.get, overrides.list/resolve, audit.list/verifyIntegrity)
- `src/types/index.ts` — Agent, Department, status types

### Frontend Config
- Next.js `output: 'standalone'` — already set up for single-binary bundling
- API base: `NEXT_PUBLIC_API_URL ?? 'http://localhost:3001'`
- No Tauri integration yet

## Existing Backend (Fastify + TypeScript, `backend/src/`)

### API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| GET | /api/agents | List all 29 agents with state |
| GET | /api/agents/:id | Single agent detail |
| GET | /api/agents/:id/heartbeat | Update heartbeat |
| POST | /api/agents/:id/dispatch | Dispatch task (async) |
| GET | /api/agents/tasks/:task_id | Poll task result |
| GET | /api/agents/tasks | List all tasks |
| GET | /api/audit | Query audit log (filterable) |
| GET | /api/audit/integrity | Verify hash-chain integrity |
| GET | /api/overrides | List pending override requests |
| GET | /api/overrides/overdue | SLA-overdue items |
| POST | /api/overrides/:id/resolve | Approve or reject override |
| POST | /api/overrides | Enqueue new override request |
| WS | /ws/events | Real-time event stream |

### Missing Endpoints (needed for new screens)
| Screen | Missing Endpoints |
|--------|------------------|
| Home / Live Overview | GET /api/stats (prediction counts, agent active count) |
| Prediction Ledger | GET /api/predictions (searchable, filterable), GET /api/predictions/:id |
| Trust & Calibration | GET /api/trust-scores (per-agent, per-domain) |
| Epistemic Reserve | GET /api/reserve/credentials, POST /api/reserve/verify/:agent_id |
| Agent Memory | GET /api/memory/:agent_id/episodes, GET /api/memory/:agent_id/semantic |
| Civilization | GET /api/civilization/institutions, GET /api/civilization/reviews, GET /api/civilization/reputation |
| Kafka event feed | GET /api/events/recent (last N events from event_history table) |

## Existing Database Schema (PostgreSQL, `backend/src/db/migrations/`)

| Migration | Table | Purpose |
|-----------|-------|---------|
| 001 | agent_state | Agent lifecycle, heartbeat, active task |
| 002 | agent_memory | Episodic + semantic memory entries |
| 003 | shared_knowledge | Cross-agent knowledge store |
| 004 | decision_log | Immutable, hash-chained audit entries |
| 005 | event_history | Kafka event persistence |
| 006 | prompt_registry | Versioned agent prompts |
| 007 | performance_metrics | Agent performance timeseries |
| 008 | customer_data | Customer data (RLS-protected) |
| 009 | trust_scores | Calibration windows, immutable rows |
| 010 | beliefs | Agent beliefs with validation state |
| 011 | prediction_ledger | Immutable prediction pre-registration |
| 012 | decision_log_chain | Hash chain integrity columns |
| 013 | override_queue | Human approval queue with SLA |
| 014 | — | Immutability triggers on decision_log |

Civilization tables (`reserve/migrations/006_civilization.sql`):
- `institutions`, `departments`, `agent_membership_edges`
- `institution_output_reviews` (self-cert ban CHECK constraint)
- `institution_reputation_scores` (reputation guard trigger)
- `governance_decisions`

## Docker Compose Services (`docker-compose.yml`)
- `postgres` (port 5432), `redis` (6379), `zookeeper`, `kafka` (9092), `kafka-ui` (8080)
- `vault` (8200), `otel-collector` (4317/4318), `prometheus` (9090), `grafana` (3002)

## What Exists vs What Needs Building

### Already Exists
- Next.js frontend shell with navigation
- Dashboard (agent status grid)
- Audit log viewer with real integrity check
- Human override queue (approve/reject)
- Events WebSocket stream
- Fastify backend with 13 REST endpoints + WebSocket
- All 14 DB migrations including prediction_ledger, trust_scores
- docker-compose.yml with full infrastructure stack
- Backend `output: 'standalone'` mode

### Needs Building
**Tauri Shell**
- `desktop/` directory with Tauri 2.0 project (Rust + config)
- Sidecar management (Docker Compose, Node backend)
- System tray with health indicators
- First-run wizard (Docker/Ollama detection)
- App lifecycle (launch → infra up → backend up → show window)

**New Backend Endpoints** (7 modules)
- `/api/stats` — live counters for Home screen
- `/api/predictions` — prediction ledger with search/filter
- `/api/trust-scores` — calibration data per agent/domain
- `/api/reserve/*` — epistemic reserve credentials + verification
- `/api/memory/:agent_id/*` — episodic + semantic memory
- `/api/civilization/*` — institutions, reviews, reputation
- `/api/events/recent` — last N events from event_history

**New Frontend Pages** (mapping to spec screens)
- Screen 1: `/` — Home / Live Overview (replaces redirect)
- Screen 2: `/run` — Live Run scoreboard
- Screen 3: `/ledger` — Prediction Ledger (extends existing)
- Screen 4: `/calibration` — Trust Scores & Calibration curves
- Screen 5: `/reserve` — Epistemic Reserve credentials
- Screen 6: `/memory` — Agent Memory timeline
- Screen 7: `/civilization` — Multi-institution governance
- Screen 8: `/audit` — Audit Log (extend existing)
- Screen 9: `/override` — Human Override Queue (extend existing)
- Screen 10: `/settings` — Full settings (extend /config)

**Build Pipeline**
- `.github/workflows/release.yml` — Mac/Windows/Linux parallel builds
- Tauri bundle config (sidecar binaries, updater, icons)
- PyInstaller spec for Python agent runtime
- README download section

## Gaps: What Data Is In Postgres But Has No Frontend Representation
1. `prediction_ledger` — no frontend table at all (most critical gap)
2. `trust_scores` — no calibration curve UI
3. `agent_memory` — no memory timeline
4. `event_history` — WebSocket shows live events but no history browser
5. `beliefs` — no belief state visualization
6. `performance_metrics` — /performance page may be static
7. Civilization tables — no UI at all

## Honest Status
What can be built completely: Tauri shell, all 10 screen layouts wired to real APIs, release pipeline.
What requires a running Ollama/Docker to smoke-test: first-run wizard, sidecar lifecycle, credential verification.
What cannot be delivered as fully functional in this session: the PyInstaller binary (Python runtime bundling requires a working build environment with all agent deps installed); the actual .dmg/.exe/.AppImage artifacts (require platform-specific build runners in CI).
