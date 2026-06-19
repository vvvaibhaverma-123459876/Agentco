# AgentCo Launch Readiness Audit

Generated: 2026-06-19

## Headline Finding

AgentCo has real calibration infrastructure, but the current launch surface still over-claims. The most important correctness gap is present in the internet prediction path: `scripts/autonomous_prediction_loop.py` extracts a claim from `source_url` and instructs the LLM that `resolution_url MUST be: {source_url}`. `scripts/check_resolutions.py` then resolves by fetching `pred.ground_truth_source` with no independent-source check. That means a claim can be checked against the same article it came from.

## 1. Clean Migration Path

Partially fixed, but not canonical everywhere.

- Working path: `backend/src/db/run_migrations.py` discovers and applies both `backend/src/db/migrations/*.sql` and `reserve/migrations/*.sql`.
- Broken/legacy path: `backend/package.json` has `db:migrate` as `node -e "require('./dist/db/migrate.js')"`, which requires a built `dist` tree and only applies backend migrations.
- Risk: a clean clone that follows `npm run db:migrate` can fail before build or miss reserve migrations.

Required launch fix: make the Makefile and backend package script point at the Python combined runner.

## 2. Frontend Data

The frontend is not purely static scaffolding, but it is also not currently build-complete.

- Real backend calls exist in `frontend/src/app/dashboard/page.tsx`, `frontend/src/app/audit/page.tsx`, and `frontend/src/app/override/page.tsx` through `@/lib/api`.
- The file `frontend/src/lib/api.ts` is missing, so those imports fail in a clean checkout.
- The events page uses a real websocket URL default, `ws://localhost:3001/ws/events`.

Required launch fix: add the missing API client and verify the frontend can compile or at least type-check.

## 3. API Auth/RBAC

No API-layer auth or RBAC is currently enforced.

- `backend/src/server.ts` registers all routes directly.
- `backend/src/routes/override.routes.ts` exposes write endpoints:
  - `POST /api/overrides/:request_id/resolve`
  - `POST /api/overrides`
- `backend/src/routes/agents.routes.ts` exposes write/dispatch behavior:
  - `GET /api/agents/:id/heartbeat` mutates heartbeat state despite being a GET.
  - `POST /api/agents/:id/dispatch`
- No route checks an API key, session, role, or token.

Required launch fix: add minimal API-key auth for write endpoints. Full RBAC remains roadmap.

## 4. Dev-Default Secrets Found

Literal defaults found in committed config/code:

- `docker-compose.yml`: `POSTGRES_PASSWORD=password`
- `docker-compose.yml`: `VAULT_DEV_ROOT_TOKEN_ID=root`
- `docker-compose.yml`: `GF_SECURITY_ADMIN_USER=admin`
- `docker-compose.yml`: `GF_SECURITY_ADMIN_PASSWORD=agentco`
- `.env.example`: `DATABASE_URL=postgres://agentco:password@localhost:5432/agentco`
- `.env.example`: `AGENTCO_TEST_DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco`
- `.env.example`: `VAULT_TOKEN=root`
- `.env.example`: `JWT_SECRET=change-me-generate-with-openssl-rand-hex-64`
- `runtime/base_agent/base_agent_v2.py`: `EVENT_BUS_HMAC_KEY` default `dev-insecure-key`
- `backend/src/services/event-bus.service.ts`: `EVENT_BUS_SIGNING_KEY` default `dev-key-replace-in-production`
- `reserve/credentials/proof_of_calibration.py`: `RESERVE_SIGNING_KEY` default `dev-insecure-key`
- Multiple local/test DSNs in scripts/tests use `agentco:password`.

Required launch fix: when `AGENTCO_ENV=production`, startup must fail closed if these defaults are active or required secrets are unset. Development mode should keep working.

## 5. Circular Resolution Check

Bug confirmed.

Evidence:

- In `scripts/autonomous_prediction_loop.py`, the extraction prompt says `resolution_url MUST be: {source_url}`.
- The registration record stores `confidence_basis.source = source_url` and `ground_truth_source = resolution_url`, so the source and resolution URL are intentionally identical.
- In `scripts/check_resolutions.py`, the checker fetches `pred.ground_truth_source` and asks an LLM whether that page confirms the claim. There is no comparison against the original extraction source.

Required launch fix: source independence must be enforced before registration and before resolution. Same-origin is not automatically invalid, but exact same canonical URL is invalid for a verification claim.
