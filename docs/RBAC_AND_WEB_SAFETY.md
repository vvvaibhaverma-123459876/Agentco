# RBAC and Web Safety

## RBAC / API auth (canonical, active)

The backend runtime is **Fastify** (`backend/src/server.ts`). Authentication and
governance authorization are enforced two ways:

1. **Write-path API key** — `server.ts` `preHandler` hook requires
   `x-api-key: $AGENTCO_API_KEY` for every non-GET request and applies a
   per-key rate limit. GET/HEAD/OPTIONS are read-only and unauthenticated.
2. **Governance RBAC** — `governance.routes.ts` calls
   `governanceRBACService.hasPermission` / `checkPermissionLevel` per protected
   operation, and every check is written to `governance_rbac_audit`. Roles and
   permissions live in migration `040_governance_rbac.sql`.

### Removed: Express RBAC middleware

`src/middleware/governance-rbac.middleware.ts.disabled` and
`src/middleware/rbac.middleware.ts.disabled` were **Express** middleware for an
earlier server that no longer exists. They were dead code (never imported,
`.disabled`, and written against `express.Request`). They have been deleted.
The canonical RBAC path is the Fastify per-route check above, which is exercised
by `tests/safety-hardening.test.ts` (allow + deny + audit) and
`tests/governance-*` suites.

## Web fetch safety (SSRF + prompt injection)

`backend/src/adapters/url-safety.ts` is the single guard for outbound fetches,
used by `RealWebAdapter.fetch`:

- Only `http:` / `https:` schemes.
- Blocks `localhost`, `*.internal` / `*.local`, and any host that **resolves**
  to a loopback / link-local / RFC1918 / CGNAT / IPv6-private address (defends
  against DNS-based SSRF to cloud metadata at `169.254.169.254`, etc.).
- Bounded redirects (`MAX_REDIRECTS = 3`), each hop re-validated.
- Response size cap and timeout.
- Loopback is permitted **only** when `AGENTCO_ALLOW_LOOPBACK_FETCH=1`
  (test fixtures), never by default.

Fetched content is treated as **untrusted evidence**:
`wrapUntrustedContent` fences it with a per-call random token and a banner
telling the planner never to follow instructions inside it. The planner injects
web snippets exclusively through this wrapper, and the planner system prompt
carries the matching rule. Covered by `tests/safety-hardening.test.ts`.

## Autonomy bounds

The supervised free-run (`supervised-free-run.service.ts`) checks the
`autonomy.supervised_free_run` kill switch before every goal, is bounded by
wall-clock and goal count, and only auto-approves low-risk internal goals in
local/test mode. Live-service goals are held for human review. Covered by
`tests/goal-formation-supervised-free-run.test.ts`.
