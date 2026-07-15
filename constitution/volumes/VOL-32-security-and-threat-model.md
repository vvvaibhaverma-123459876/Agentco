# Volume 32 — Security & Threat Model

## 1. Header

| Field | Value |
|---|---|
| Volume | 32 |
| Name | Security & Threat Model |
| Tier | constitutional |
| Epistemic status | descriptive |
| Doc status | written |
| Related volumes | V1 (Constitutional Core), V4 (Identity & Authority), V27 (Operator Control Plane), V30 (Verification) |

## 2. Purpose

This volume states the threat model the running system defends against **today** and
where each defense is enforced. It is descriptive: every normative sentence cites the
enforcing file or test. It is constitutional because these boundaries are preconditions
for every other volume — weakening any defense below is an amendment to H1/H2
(see Volume 1), not a refactor.

### Threat model

| # | Threat | Defense today | Enforced by |
|---|---|---|---|
| T1 | Unauthenticated or under-authenticated API access | Every HTTP route is classified PUBLIC / AUTH-READ / AUTH-WRITE in a sensitivity matrix; a contract test fails on unclassified or misclassified routes; write access requires the API key | `docs/audit/ROUTE_SENSITIVITY_MATRIX.md`, `backend/tests/route-auth-contract.test.ts`, `backend/src/security.ts` ("minimal API key auth" in `backend/tests/security.test.ts`) |
| T2 | Production start with dev-default or missing secrets | Fail-closed startup assertions in both runtimes | TS: `assertProductionSecrets` / `assertAuthPosture` in `backend/src/security.ts` ("production secret guard" in `backend/tests/security.test.ts`). Python: `agentco_security/env_guard.py`, called from `runtime/base_agent/base_agent_v2.py`, `backend/src/db/run_migrations.py`, `reserve/credentials/proof_of_calibration.py` |
| T3 | SSRF via outbound fetches | Only http/https; blocks loopback, RFC1918, CGNAT 100.64/10, link-local (incl. cloud metadata 169.254/16 and `metadata.google.internal`), IPv6 ULA/link-local/v4-mapped, `.local`/`.internal` suffixes — for literals **and** hostnames that DNS-resolve to private addresses; bounded redirects with every hop re-validated | `backend/src/adapters/url-safety.ts`; consumed by `backend/src/adapters/real-web-adapter.ts`, `backend/src/services/action-executor.service.ts`, `backend/src/services/input-validator.service.ts`; exercised by `backend/tests/red-team-corpus.test.ts` |
| T4 | Prompt injection from fetched web content | Fetched content enters model prompts only inside UNTRUSTED fences with an explicit planner rule: quoted web evidence, never instructions | `wrapUntrustedContent` in `backend/src/adapters/url-safety.ts`; planner rule + fencing in `backend/src/services/autonomy-action-planner.service.ts`; `backend/tests/prompt-injection-e2e.test.ts` (B6), `backend/tests/red-team-corpus.test.ts` (D5/D6) |
| T5 | Forged specialist / team activation calls | HMAC-SHA256 over `payload:timestamp` with `SPECIALIST_SHARED_SECRET`; production/staging refuse unset or default secret | `signRequest` in `backend/src/services/team-activation.service.ts`; `backend/tests/team-activation.test.ts` |
| T6 | Forged or tampered inter-service events | Signed event-bus envelopes; the signing/HMAC keys are among the startup-guarded secrets | `backend/src/services/event-bus.service.ts`, migration `backend/src/db/migrations/128_event_bus_outbox.sql`, key guards in `backend/src/security.ts` and `agentco_security/env_guard.py` |
| T7 | Secrets committed to the repository | CI secret-scan job on every push | `secret-scan` job in `.github/workflows/ci.yml` |
| T8 | Network exposure without auth | The server refuses to bind a non-loopback host without a real API key | `assertAuthPosture` in `backend/src/security.ts` |
| T9 | Tampered history or protected state | Constitutional layer: append-only triggers, hash chain, protected surfaces | Volume 1 (V1-INV-001, V1-INV-003) |
| T10 | Runaway or hostile execution | Kill switch honored by run loops; budgets and policy enforcement | Volume 1 (V1-INV-004), Volume 7, `backend/src/services/run-guard.service.ts` |

## 3. Definitions

- **SSRF** — server-side request forgery: inducing the runtime to fetch internal or
  metadata endpoints. Guarded per T3.
- **Untrusted content fencing** — wrapping fetched text in a banner block the planner is
  instructed never to obey (`UNTRUSTED_CONTENT_BANNER`, `wrapUntrustedContent` in
  `backend/src/adapters/url-safety.ts`).
- **Route sensitivity classification** — the PUBLIC / AUTH-READ / AUTH-WRITE label every
  route carries in `docs/audit/ROUTE_SENSITIVITY_MATRIX.md`.
- **Auth posture** — the startup decision of whether binding and key configuration are
  safe (`assertAuthPosture`, `backend/src/security.ts`).
- **Dev-default secret** — a placeholder value acceptable only in local development;
  enumerated in `DEV_DEFAULTS` (`agentco_security/env_guard.py`) and in
  `backend/src/security.ts`.
- **Fail-closed** — refusing to start or proceed when a guard cannot positively verify
  safety.

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V32-INV-001 | Every HTTP route is classified in the sensitivity matrix, and a contract test fails the build on unclassified or misclassified routes. | enforced | `backend/tests/route-auth-contract.test.ts`, `docs/audit/ROUTE_SENSITIVITY_MATRIX.md` |
| V32-INV-002 | A production-like start fails closed on missing or dev-default secrets in both the TypeScript and Python runtimes. | enforced | `backend/src/security.ts`, `backend/tests/security.test.ts`, `agentco_security/env_guard.py` |
| V32-INV-003 | Every outbound web fetch validates scheme and target against private and metadata ranges — including hostnames that resolve to private addresses — and re-validates every redirect hop. | enforced | `backend/src/adapters/url-safety.ts`, `backend/tests/red-team-corpus.test.ts` |
| V32-INV-004 | Fetched web content enters model prompts only inside untrusted fences accompanied by a rule that fenced content is evidence, never instructions. | enforced | `backend/src/adapters/url-safety.ts`, `backend/src/services/autonomy-action-planner.service.ts`, `backend/tests/prompt-injection-e2e.test.ts` |
| V32-INV-005 | Specialist HTTP activation is HMAC-authenticated, and production or staging refuses to sign with an unset or default shared secret. | enforced | `backend/src/services/team-activation.service.ts`, `backend/tests/team-activation.test.ts` |
| V32-INV-006 | Inter-service event envelopes are signed, and the signing keys are among the startup-guarded secrets. | enforced | `backend/src/services/event-bus.service.ts`, `backend/src/db/migrations/128_event_bus_outbox.sql`, `agentco_security/env_guard.py` |
| V32-INV-007 | Continuous integration scans every push for committed secrets. | enforced | `.github/workflows/ci.yml` |
| V32-INV-008 | Dependency vulnerability audits run as a wired, fail-closed release gate rather than ad-hoc commands. | planned | — |
| V32-INV-009 | The URL-safety adapter has a dedicated unit suite covering literal, DNS-resolved, redirect, and v4-mapped bypass attempts. | planned | — |

## 5. Interfaces

- **Startup guards** — `assertProductionSecrets` and `assertAuthPosture` are invoked at
  server start (`backend/src/server.ts` imports from `backend/src/security.ts`);
  `getProvidedApiKey` backs the route auth hook.
- **Fetch path** — all web-facing callers (`real-web-adapter`, `action-executor`,
  `input-validator`) validate through `backend/src/adapters/url-safety.ts` before
  fetching and fence results via `wrapUntrustedContent` before prompting.
- **Specialist calls** — `team-activation.service.ts` signs each HTTP activation
  (HMAC-SHA256, timestamped) toward specialist endpoints (migration
  `052_specialist_http_endpoint.sql`).
- **Event bus** — producers sign envelopes via `backend/src/services/event-bus.service.ts`
  into `event_bus_outbox` (migration `128`), relayed by
  `backend/src/workers/outbox-worker.ts`.
- **CI** — `secret-scan` job in `.github/workflows/ci.yml`.

## 6. State

Security here is mostly stateless guards plus configuration:

- **Guarded secret set** (must never be dev-default in production):
  `EVENT_BUS_HMAC_KEY`, `EVENT_BUS_SIGNING_KEY`, `RESERVE_SIGNING_KEY`,
  `RESOLUTION_SERVICE_PASSWORD`, `VAULT_TOKEN`, `JWT_SECRET`, `AGENTCO_API_KEY`
  (`agentco_security/env_guard.py`), plus password-bearing `DATABASE_URL` /
  `AGENTCO_TEST_DATABASE_URL` DSNs; TypeScript side additionally guards
  `SPECIALIST_SHARED_SECRET` at signing time
  (`backend/src/services/team-activation.service.ts`).
- **Tables:** `event_bus_outbox` (migration `128`); specialist endpoint registration
  (migration `052`).
- **Documents:** `docs/audit/ROUTE_SENSITIVITY_MATRIX.md` (298 classified routes as of
  2026-07-15).

## 7. Failure modes and responses

- **Dev fallbacks outside production** — signing falls back to
  `development-only-specialist-secret` and auth accepts the dev key **only** when the
  environment is not production-like; production paths throw
  (`backend/src/services/team-activation.service.ts`, `backend/src/security.ts`).
  Accepted for local development; the boundary is the `isProductionEnv` check.
- **DNS rebinding (TOCTOU)** — `url-safety.ts` validates what a hostname resolves to at
  check time; a hostile resolver could answer differently at fetch time. Not currently
  mitigated (no pinned-IP fetch). Recorded as open question 2.
- **Redirect laundering** — bounded redirects with per-hop re-validation
  (`backend/src/adapters/url-safety.ts`).
- **New secret introduced without guard registration** — nothing forces a new env secret
  into `DEV_DEFAULTS`/`security.ts`; the two runtimes' lists are maintained by hand and
  already differ (open question 3).
- **Unclassified new route** — `route-auth-contract.test.ts` fails the suite until the
  route is classified.

## 8. Verification obligations

Existing and green today: `backend/tests/security.test.ts`,
`backend/tests/route-auth-contract.test.ts`, `backend/tests/prompt-injection-e2e.test.ts`,
`backend/tests/red-team-corpus.test.ts`, `backend/tests/team-activation.test.ts`, and the
CI `secret-scan` job (`.github/workflows/ci.yml`).

Must exist before the planned invariants flip: a wired `npm audit` (or equivalent SCA)
gate failing the release path on known-vulnerable dependencies (V32-INV-008); a
dedicated `url-safety` unit suite including DNS-rebinding and v4-mapped cases
(V32-INV-009).

## 9. Implementation mapping

- `backend/src/security.ts` — production env detection, secret assertions, auth
  posture, API-key extraction.
- `backend/src/adapters/url-safety.ts` — `isPrivateIp`, URL validation with DNS
  resolution, redirect re-validation, untrusted-content fencing.
- `backend/src/services/autonomy-action-planner.service.ts` — fenced snippets +
  explicit non-instruction rule in the planner prompt.
- `backend/src/services/team-activation.service.ts` — HMAC-SHA256 request signing with
  production fail-closed secret check.
- `backend/src/services/event-bus.service.ts` + migration `128_event_bus_outbox.sql` —
  signed envelopes through the transactional outbox.
- `agentco_security/env_guard.py` — Python-side fail-closed production secret guard
  (three call sites listed in T2).
- `.github/workflows/ci.yml` — `secret-scan` job.
- Route authorization: `docs/audit/ROUTE_SENSITIVITY_MATRIX.md` +
  `backend/tests/route-auth-contract.test.ts`.

## 10. Open questions

1. **No wired dependency-vulnerability gate.** `npm audit` appears in no Makefile target
   and no CI workflow; audits have been run ad-hoc only (V32-INV-008 planned).
2. **DNS rebinding TOCTOU** in `url-safety.ts` — validate-time resolution is not pinned
   for fetch-time use. Mitigation (resolve-then-fetch-by-IP with Host header, or
   re-resolve comparison) belongs to this volume's implementation backlog.
3. **Two hand-maintained secret registries.** `agentco_security/env_guard.py`
   `DEV_DEFAULTS` and the TypeScript-side guards overlap but differ
   (`SPECIALIST_SHARED_SECRET` is TS-only). A single machine-readable secret registry,
   checked by both runtimes and by Self Inspection (V17), would close the drift channel.
4. **`allowLoopback` escape hatch** in `UrlSafetyOptions`
   (`backend/src/adapters/url-safety.ts`) is documented "test fixtures only"; nothing
   mechanically prevents a production caller from passing it. Candidate: assert
   non-production when the flag is set.
5. **Red-team corpus growth discipline** — `red-team-corpus.test.ts` exists (D5/D6),
   but no obligation states when new attack classes must be added; tie to incident
   learnings via V14 (Learning Engine).

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 3) | Bind the existing SSRF, injection, HMAC, signing, secret-guard, and route-auth machinery into one citable threat model before the descriptive volumes that depend on it. |
