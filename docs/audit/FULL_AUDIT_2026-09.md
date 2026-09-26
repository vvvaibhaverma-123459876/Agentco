# AgentCo Full Audit — 2026-09-26

Scope: the whole repository at `b5f8a29` (after PRs #31–#34): backend (Fastify/TS), frontend (Next.js), Python agents/runtime, SQL migrations, CI/CD, Docker/Helm, dependencies, and the autonomy invariants in `AGENTS.md`.

Method: fresh clone → install → typecheck → migrate a fresh Postgres 16 from version zero → full Jest and pytest suites → targeted code review of the auth boundary, outbound fetch, multi-agent spawning, and deploy surface → live probes for each suspected issue. Every finding marked **Confirmed** was reproduced, either with a live probe or with a regression test that fails on the old code.

## 1. Baseline health

| Check | Result |
|---|---|
| Backend `tsc --noEmit` | clean |
| Frontend `tsc --noEmit`, `lint`, `build` | clean |
| Migrations 000→144 on an empty DB | apply cleanly |
| Backend Jest (before fixes) | 121/125 suites passed; the 4 failures were environmental (see L8) and pass once the Python 3.13 deps are installed |
| Backend Jest (after fixes) | 126 suites / 954 tests passed, 0 failed (8 skipped, 5 todo) |
| pytest | 908 passed, 14 skipped, 4 environmental failures (see L8) |
| Fast release-gate checks (`gate-integrity`, `verify-advertised-targets`, protocol/eval/learning/self-improvement report checks, score validation, migration naming) | pass |
| `status-check` | fails in a shallow clone only (see L9) |
| `npm audit` (before) | backend 3 prod advisories (2 high); frontend 6 (1 **critical** — `next`) |
| `npm audit` (after) | 0 in both |

Prior audit (2026-07-06) top risks, re-checked: repo-wide pytest collection now works (911 collected). GET routes are now protected by default. CI requirement paths exist. The README status block is generated. The staging compose file requires real passwords. **Still open:** dev compose file credentials (L6), `.disabled` route files, and no evidence yet from a hosted production run.

## 2. Findings

Severity: **C** critical, **H** high, **M** medium, **L** low. Status: **Fixed** (in this PR, with a regression test where feasible) or **Open** (needs a decision or a larger change).

### Critical / High

| ID | Sev | Status | Finding |
|---|---|---|---|
| C1 | C | **Partly fixed** | **The dashboard proxy is an unauthenticated relay that holds the service API key.** `frontend/src/app/api/[...path]/route.ts` attaches `AGENTCO_API_KEY` to every proxied request. The dashboard itself has no user authentication, and the CSRF check only needs an `Origin` header, which any non-browser client can set. Anyone who can reach the frontend therefore gets API-key-level backend access. It was worse than that: decoded route params let the proxy escape the `/api` prefix. A live probe showed `GET /api/..%2fidentity/actors` reaching backend `/identity/actors` with the key attached (`/metrics`, `/health/runtime`, `/v1/*` were reachable the same way). **Fixed:** dot segments and embedded separators are rejected, and the upstream path must stay under `/api/`. **Open:** the proxy still needs real operator authentication (SSO/OIDC at the ingress, or a session layer in Next). Until then the frontend must not be exposed beyond a trusted network. |
| H1 | H | **Fixed** | **SSRF guard bypass via IPv4-mapped IPv6.** WHATWG URL parsing normalizes `http://[::ffff:169.254.169.254]/` to host `[::ffff:a9fe:a9fe]`. The old `isPrivateIp` sliced off `::ffff:` and tested `a9fe:a9fe` as IPv4, so the check failed open. Cloud metadata and loopback services were reachable through `FETCH_PAGE`. NAT64 (`64:ff9b::/96`), 6to4, v4-compatible, multicast, site-local and the reserved IPv4 ranges were also unblocked. The check now decodes the IPv6 groups and fails closed on anything it cannot parse. |
| H2 | H | **Fixed** | **Redirect hops were requested before validation.** `RealWebAdapter.fetch` used `redirect: 'follow'` and only re-validated the *final* URL, so a public page could 302 the fetch onto an internal service. The request was sent, and only the response was discarded (blind SSRF, e.g. a GET that has side effects). Redirects are now followed manually (max 3), and each hop is validated before it is requested. |
| H3 | H | **Fixed** | **Specialist HMAC was optional, and the main caller never signed.** The Python `/execute` handler verified a signature only if the headers were present. `ActionExecutor.handleSpawnSpecialist` posted unsigned. So any local process, or an SSRF hop onto `127.0.0.1:<port>`, could drive a specialist. Signatures are now mandatory, and the executor signs through `TeamActivationService.signedExecuteHeaders`. The TS side also resolved the dev fallback secret differently from Python when `SPECIALIST_SHARED_SECRET=default-insecure-secret`; both sides now agree. |
| H4 | H | **Fixed** | **Known-vulnerable dependencies.** Frontend `next@16.2.9` had a critical advisory set (middleware bypass, SSRF, RCE in image optimization); backend had `fastify@5.8.5`, `fast-uri`, and `find-my-way` advisories (SSRF/host confusion, HTTP/2 DoS). Fixed with in-range lockfile updates (`next` 16.3.6, `fastify` 5.12.5); `npm audit` is now 0/0. |

### Medium

| ID | Status | Finding |
|---|---|---|
| M1 | **Fixed** | **Learning capture and the civilization validator ran before auth.** preHandler hooks run in registration order, and both were registered ahead of the API-key hook. Unauthenticated callers could (a) inject learning signals with attacker-chosen `agent_id`/body, which went into in-memory stores that were never evicted (memory DoS), and (b) burn another entity's per-`entityId` civilization rate limit (100 requests locks that entity out for a minute). The auth and rate-limit hook is now registered first; 401/429 responses no longer produce outcome signals; the stores are bounded. |
| M2 | **Fixed** | **Rate limiting keyed on the unverified API key.** The bucket id was `key:<whatever the caller sent>`, so rotating bogus keys minted a fresh 100-request bucket per request and grew the map without bound. Only a verified key now earns its own bucket; everything else shares the per-IP bucket. The map is capped at 10k with idle-first eviction. UUID path validation now also runs when no key is configured. |
| M3 | **Fixed** | **Multi-agent boundary gaps (AGENTS.md invariant 4).** (a) *Race on the 3-worker cap:* the DB count was read, then the spawn awaited for up to 5 s before inserting, so concurrent activations all passed. Now an in-process reservation is taken with no `await` between the check and the reserve; a new test fires 5 concurrent activations and gets exactly 3. (b) *Dead SIGKILL escalation:* `ChildProcess.killed` is true once a signal has been *sent*, so a process that ignored SIGTERM was never SIGKILLed, both in `terminateSpecialist` and in graceful shutdown. Liveness now comes from the exit status. (c) *No hard wall-clock interrupt:* the seconds budget was only checked on request. There is now a kill timer per specialist. (d) A failed `INSERT` left the spawned child orphaned; it is now killed. The executor's fixed 25 s timeout is replaced by the specialist's own budget. |
| M4 | Open | **Specialists inherit the backend's entire environment** (`spawn(..., { env: { ...process.env } })`): `DATABASE_URL` with owner/superuser credentials, `AGENTCO_API_KEY`, LLM keys, `JWT_SECRET`, `VAULT_TOKEN`. This conflicts with "specialists are stateless within their scope". Recommendation: pass an allowlisted env and a least-privilege DB role scoped to the tables specialists write. |
| M5 | Open (frozen) | **Capability `calculator` DoS.** `agentco_capability/tools.py` allowlists AST nodes but permits `**` and string constants, so `9**9**9**9` or `'a'*10**9` exhausts CPU/memory. A fix was written and verified (numeric constants only; bounded exponent, result size, and input length) but **withheld**, because this file is SHA-pinned in `GOVERNED_CAPABILITY_GENESIS_V5_FREEZE_MANIFEST.json`. Changing it invalidates the frozen candidate evidence, so it needs an owner decision and a freeze refresh. |
| M6 | Open | **Capability attempts: no ownership, mutable terminal state, in-memory only.** `/v1/capabilities/attempts/:id/cancel` lets any principal holding `capability.cancel` cancel *anyone's* attempt. It also overwrites `failed`/`denied` outcomes with `cancelled`, which loses the observable outcome that invariant 1 requires. Attempts live in an unbounded module-level `Map` and are lost on restart. |
| M7 | Open | **Monitoring cannot scrape `/metrics`.** The route requires the API key, but `infrastructure/prometheus/prometheus.yml` and the Helm `prometheus.io/*` annotations scrape without one. Every keyed deployment gets 401s and no metrics. Options: a separate metrics port or listener bound to the pod network, or a scrape bearer token. |
| M8 | Open | **The shipped backend image cannot spawn specialists.** `backend/Dockerfile` is `node:20-alpine` with build context `./backend`: there is no Python and no `agents/` package. `SPAWN_SPECIALIST` always fails in container deployments, so multi-agent capability exists only in local runs. |
| M9 | Open | **Helm ingress bypasses the dashboard proxy.** The ingress sends `/api` straight to the backend service, so browser calls from the dashboard hit the backend without a key and get 401 whenever a key is set. This contradicts the README's "browser dashboard API calls use the frontend server-side proxy". (It also means C1 is currently masked in Helm deployments but not in docker-compose or direct pod exposure.) |
| M10 | **Fixed** | `AGENTCO_ALLOW_LOOPBACK_FETCH=1` (the SSRF test escape hatch) was not refused in production-like envs. `assertProductionSecrets` now refuses it. |

### Low

| ID | Status | Finding |
|---|---|---|
| L1 | Open | `RealWebAdapter.fetch` reads the whole body (`response.text()`) before truncating to 500 KB. Only the 8 s timeout bounds memory. Stream with a byte cap instead. |
| L2 | Open | DNS TOCTOU: `assertPublicHttpUrl` resolves, then `fetch` resolves again (rebinding window). Pin the vetted address with a custom undici dispatcher `connect.lookup`. |
| L3 | Open | API key comparison uses `!==` (not constant-time). Use `crypto.timingSafeEqual` on equal-length digests. |
| L4 | Open | `LoopDetectorService` compares args with `JSON.stringify`, which is key-order sensitive, so `{a,b}` and `{b,a}` evade the identical-action check. |
| L5 | Open | `ActionExecutor.executeAction` marks any handler that returns while still `EXECUTING` as `COMPLETED`. A handler that silently does nothing therefore reports success, which is the exact failure invariant 1 forbids. Default to `FAILED` with a reason instead. |
| L6 | Open | The dev `docker-compose.yml` publishes Postgres (`password`), Redis, Kafka UI (no auth) and Vault **dev mode with root token `root`** on `0.0.0.0`. Bind them to `127.0.0.1:`. |
| L7 | Open | `deploy.yml` is not gated on CI, interpolates `${{ secrets.KUBECONFIG }}` inline in `run:` (pass it via `env:` instead), and pins third-party actions by tag rather than SHA. |
| L8 | Open | Test hygiene: 4 Jest suites *fail* rather than skip when Python 3.13 and its deps are absent. `test_pg_ledger_immutability.py` assumes the `resolution_service` role has password `test`, which breaks once migration 016 has created it. `test_cli_executes_request_file` hardcodes `python3.13` instead of `sys.executable`. Running pytest rewrites 14 tracked files under `docs/audit/current/`. |
| L9 | Open | `make status-check` derives the ledger commit from `git log`, so it fails in shallow clones. |
| L10 | Open | Every `TeamActivationService` instance adds process-wide SIGTERM/SIGINT listeners (a leak across instances). They race `server.ts`'s shutdown, which calls `process.exit(0)` before the specialists' SIGKILL phase finishes. |
| L11 | **Fixed** | `getReputationTrend` interpolated `windowDays` into `INTERVAL '… days'`. It was not injectable (the value is `parseInt`'d upstream), but it is now parameterized with `make_interval`. |
| L12 | Open | The Python specialist checks its rate limit before the signature, so unsigned requests consume tokens. |

## 3. AGENTS.md invariant checklist

| Invariant | Verdict |
|---|---|
| 1. Decision → Execution | All `ActionType`s route. Unknown types are `BLOCKED` with a reason. `VALIDATE_CLAIM`/`COORDINATE_TEAM` fall to that default. Gaps: L5 (implicit COMPLETED) and M6 (cancel overwrites terminal outcomes). |
| 2. Evidence → Claim | Holds. Non-empty `supportSourceIds`, grounding validation, and the DB constraint are all present. |
| 3. Loop detection | Thresholds 3/5 are implemented and tested. Minor evasion: L4. |
| 4. Multi-agent boundaries | Role whitelist, depth ≤ 2, and budgets exist. The race, missing hard interrupt, and dead escalation are **fixed** (M3). Remaining: env/credential isolation (M4); the image cannot spawn at all (M8). |

## 4. Recommended next steps (priority order)

1. Put operator authentication in front of the dashboard (C1), and make Helm routing consistent with the proxy design (M9).
2. Least-privilege env and DB role for specialists (M4); add Python and `agents/` to the backend image, or run specialists as a separate deployment (M8).
3. Decide on the frozen-capability calculator fix and refresh the freeze (M5); add ownership checks and immutable terminal states to capability attempts (M6).
4. Make `/metrics` scrapeable without the write key (M7).
5. Clean up tests (L8) so a clean environment produces skips rather than failures, and pytest stops mutating tracked files.
