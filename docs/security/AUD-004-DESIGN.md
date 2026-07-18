# AUD-004 Remediation Design — Authenticated Principal Boundaries

**Branch:** `audit/remediation-02-authenticated-principal-boundaries` · **Baseline:** `1a98381`
**Findings addressed:** AUD-004 (direct predicate challenge, conditions **16** & **25**).
**Rule kept:** machine-verifier truth stays separate from substantive truth; this branch does
**not** flip the substantive predicate. Conditions 16/25 remain NOT SATISFIED until an
independent re-audit confirms them on the post-remediation commit.

---

## 1. The gap (precise)

The HTTP boundary authenticates **one shared `AGENTCO_API_KEY`** (`server.ts:90`). After that
check, every governed action's actor identity is read from **caller-supplied** fields
(`body.actor_id`, `x-actor-id`). Independence checks (V13 judge≠complainant, V14
evaluator≠proposer) and governance RBAC therefore compare **labels a single key-holder chooses**
— defeated by presenting two labels for one principal.

**Not "no identity system."** The repo already has a rich one (see §2). AUD-004 is that this
machinery is **never invoked at the boundary** and is **not mandatory**. The fix is to **bind the
authenticated credential to a principal and make the existing machinery the mandatory gate** — not
to build a parallel auth stack (which would recreate the AUD-009 duplication).

## 2. Existing surface to REUSE (do not rebuild)

From `identity-authority.service.ts` + migrations `079/084/086/040`:

- **`actors`** (typed, `status` active/suspended/revoked, unique active name+type).
- **`actor_key_ring`** — per-actor **Ed25519** public keys by purpose (`identity`, …), with
  fingerprints, rotation, revocation. **`verifySignature(actor_id,'identity',payload,sig)`** already
  verifies an Ed25519 signature against the actor's registered key. ← the credential primitive.
- **RBAC**: `roles`(6 seeded)/`permissions`(6 seeded)/`role_assignments`/`actor_permissions`/
  `authority_delegation_grants`; **`verifyAuthority(actorId,permission,scope)`** resolves
  direct/role/delegation, fail-closed. ← the authorization primitive.
- `authority_decision_chains` — authority-decision audit.

`JWT_SECRET` exists only in the startup guard (`security.ts:26`) and is **never used to verify
anything**. It is symmetric (shared-secret) and weaker than the asymmetric key-ring. **Decision:
use Ed25519 request-signing over the existing key-ring, not JWT** — reuses built machinery, gives
per-actor asymmetric credentials, and avoids a second parallel system.

## 3. Mechanism — Ed25519 request-signing → authenticated principal

A governed request must **prove control of an actor's `identity` private key**:

- Canonical signing string: `METHOD` `\n` `PATH` `\n` `sha256(body)` `\n` `x-agentco-timestamp`
  `\n` `x-agentco-nonce`.
- Headers: `x-agentco-actor-id`, `x-agentco-timestamp`, `x-agentco-nonce`, `x-agentco-signature`
  (base64 Ed25519 over the canonical string).
- Server verifies via `identityAuthorityService.verifySignature(actorId,'identity',canonical,sig)`.
- **Anti-replay:** reject `|now − timestamp| > 300s`; reject a reused `(actorId,nonce)` within the
  window (in-memory TTL store now; a `used_request_nonces` table if multi-instance).
- **Fail closed** on missing/invalid/expired/ambiguous identity, unknown actor, or non-active actor.

The shared `AGENTCO_API_KEY` is retained only as a coarse **transport gate** (rate-limit/DoS), and
**must not** qualify as a governed principal. Root/admin credentials do **not** count as multiple
independent principals.

## 4. Canonical request principal

```
RequestPrincipal {
  actorId: string           // immutable, from the VERIFIED signature — never from body
  actorType: string         // actors.actor_type
  credentialFingerprint: string  // actor_key_ring.fingerprint_sha256 of the verifying key
  roles: string[]           // resolved from role_assignments
  authMethod: 'ed25519_request_signature'
  requestId: string         // correlation id
}
```
Attached as `request.principal`. **Caller-supplied `actor_id`/`x-actor-id` become descriptive
metadata only and are never the security principal.** A governed handler that needs an actor uses
`request.principal.actorId`.

## 5. Authorization (bind permissions to principals + routes)

Each privileged route declares a required permission; the preHandler calls
`verifyAuthority(request.principal.actorId, permission, scope)` and fails closed if not allowed.
New permissions to seed (additive migration): `judiciary.case.open`, `judiciary.appeal.decide`,
`evolution.evaluate`, `evolution.approve`, `treasury.penalty.impose`, `capability.expand`,
`governance.vote`. Existing `governance.approve`, `prediction.resolve` reused.

## 6. Conditions 16 & 25 — enforced on authenticated principals + DB backstops

- **16 (appeals by independent authority):** persist `complainant_actor_id` (from principal at
  open) and `original_decision_maker_actor_id`; the appeal handler derives the appellate authority
  from `request.principal.actorId` and requires `judiciary.appeal.decide`. Application check +
  **DB backstop** (guarded transition / CHECK): appellate authority `≠` complainant `≠` original
  decision-maker. Where the brief requires organizational independence, bind and compare
  `trust_domain`/institution, not just the actor id.
- **25 (independent evaluation):** `evaluator_actor_id = request.principal.actorId`; **DB
  backstop** so `evaluator ≠ proposer`, `evaluator ≠ artifact_creator`, and (where the constitution
  separates them) `evaluator ≠ approver`. Root/service/admin cannot satisfy this by relabelling —
  the compared ids are authenticated principals.

## 7. Persistence, alternate paths, and DB enforcement

- Persist `authenticated_principal_id` + `credential_fingerprint` with governed records (judiciary
  cases/rulings, evaluations, treasury penalties, governance votes).
- **Every** governed writer must carry a verified principal or be an explicitly-provisioned
  **machine principal** (a `service` actor with a key-ring identity + narrowly-scoped permissions):
  HTTP routes, workers, scheduler, event consumers, CLI/admin scripts, migration-time writers. The
  orchestrator/outbox workers run as a named service actor, not "no actor".
- DB backstops evaluated for: complainant↔appellate, proposer↔evaluator, evaluator↔approver,
  creator↔self-approver, role-qualified transitions. **No mutable display name in a security
  constraint** — only actor ids / fingerprints.

## 8. The 880-test + release-gate coupling (deliberate, not silent)

Changing the model breaks tests that assume single-key + body actor, and the completion verifier
(`generate_civilization_completion.py`, release-gate step 11b) reflects the old 16/25.

- **Test harness:** add a signing helper (`tests/helpers/sign-request.ts`) that registers an actor,
  its Ed25519 key, and signs requests. Governed-route tests migrate to it. A `test`/dev mode may
  accept a signed **test principal**, but the enforcement path is identical — no bypass.
- **Verifier hardening (16/25):** the verifier must require evidence of credential-bound resolution
  + negative impersonation tests + DB enforcement, **not** `assertIndependent` existence or
  label-inequality. **This lands only when the implementation passes it.** Until then the branch
  **honestly reports the gate red with 16/25 NOT SATISFIED** — never a silently-green half-migration.

## 9. Required negative/adversarial tests (§Phase-2 spec, all 14)

impersonation via `actor_id`/headers/body ignored; one credential cannot submit+judge its own
appeal; cannot propose+evaluate; cannot evaluate+approve; forged headers rejected; unsigned/invalid
signature fails; wrong actor/expired/replayed nonce fails; principal without role fails; privileged
route without permission fails; worker/event/script paths cannot bypass; direct-SQL cannot defeat
the DB backstops; valid independent credentials succeed; rotation does not merge principals;
root/admin cannot satisfy independence by relabelling. **Plus control-removal (mutation) tests**:
each negative test must fail if its control is deleted.

## 10. Sequenced implementation plan (each milestone independently testable)

1. **M1 principal resolver** — `request-principal.ts` (canonical string, `verifySignature`, replay
   guard, fail-closed) + `RequestPrincipal` type + unit tests (no DB: pure sign/verify). ← start here
2. **M2 server wiring** — attach `request.principal` for governed routes; keep coarse API-key
   transport gate; test-signing helper; migrate route-auth-contract test.
3. **M3 authorization** — per-route permission requirement via `verifyAuthority`; seed new
   permissions (additive migration); privileged-route tests.
4. **M4 conditions 16/25** — principal-derived complainant/judge/proposer/evaluator + DB-backstop
   migration; the impersonation/self-review negative tests.
5. **M5 alternate paths** — machine principals for workers/scheduler/outbox/scripts.
6. **M6 verifier hardening** — land the 16/25 verifier evidence requirements; run clean-room; only
   now can the gate pass, and only if it genuinely does.

Milestones commit incrementally on this branch. The substantive predicate is **not** flipped here;
that is the independent re-audit's call on the post-remediation commit.
