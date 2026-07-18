# AUD-004 M5 — Machine Principal Registry

Every autonomous/worker component that mutates governed civilization state does so as an
explicit, narrowly-scoped `service`-type actor row in `actors` (+ `service_identities`), never
as an ambient/implicit identity. No machine principal is assigned a human-facing role
(`governor`, `auditor`, etc.) or `civilization_operator`, so none can satisfy the condition
16/25 independence checks by relabeling — they simply never appear as a candidate
evaluator/appellate authority in the first place (verified: `aud004-m5-machine-principals.test.ts`).

## Registry

| Actor name | Component | Purpose (scope) | Lifecycle | Can impersonate a human? | Can satisfy 16/25 via relabel? |
|---|---|---|---|---|---|
| `agentco-civilization-os-scheduler` | `civilization-os.service.ts` tick loop | Attributes tick/heartbeat bookkeeping events only (`civilization_os.tick.record`) | Auto-provisioned idempotently on first tick (`ON CONFLICT ... DO UPDATE`); `status='active'` while in use; no automated revocation path yet (see Residual) | No — never assigned a human role; every write requires the real `actors.id` FK | No — no `evolution.evaluate`/`judiciary.*` scope, and application code never calls evaluate/rule as this actor |
| `agentco-civilization-os-work-router` | `civilization-os.service.ts` `workSourcerAndRouter` | Attributes mission lead-institution assignment events only (`mission.lead_institution.assign`) | Same as above | No | No |
| `agentco-civilization-os-learning-retention` | `civilization-os.service.ts` `retireMonitoredCandidates` | Attributes post-promotion candidate retention only (`evolution.candidate.retain`) | Same as above | No | No — retention is a terminal monitored→retained transition, not an evaluation |
| `agentco-domain-registry` | `domain-registry.service.ts` | Domain suspension bookkeeping (`domain.register`) | Pre-existing (predates this remediation); same idempotent pattern | No | No |
| `agentco-authority-service` | `identity-authority.service.ts` | Provenance actor for authority-decision denial events only (used when the *requested* actor isn't a valid active actor, so the event needs *some* real attributable actor) | Pre-existing | No | No — `identity.*` scope only, no evaluate/rule permission |
| `resolution_service` (DB role, not an `actors` row) | `prediction_ledger` / `beliefs` resolution | Distinct **credential** boundary (DB role + password), not an application actor row — condition 19's genuine credential-enforced control | Provisioned by migration `016_resolution_service_role.sql` | N/A (a DB role, not an actor) | N/A |

## Key design decisions

1. **One principal per sub-responsibility, not one universal orchestrator actor.** Before this
   pass, `civilization-os.service.ts` had a single `agentco-civilization-os` actor used for tick
   bookkeeping, mission routing, AND learning retention — i.e. one identity holding the
   union of everything the orchestrator does. That is exactly the anti-pattern AUD-004's M5
   scope warns against ("do not create one universal system principal with every permission").
   It is now split three ways, each with its own `service_identities.scopes` entry.
2. **Registration alone grants no authority.** `actors` + `service_identities` records identity
   and a *declared* scope list for documentation/audit purposes; the actual authorization gate
   (`identityAuthorityService.verifyAuthority`, used by the HTTP-layer `requirePrincipal`) is
   driven by `role_assignments`/`actor_permissions`, and no machine principal is ever granted a
   role there. Machine principals write only through service methods that don't go through the
   HTTP `requirePrincipal` gate at all (they're in-process calls), so their "scope" list is
   documentation of intent, not an enforced RBAC boundary today — see Residual.
3. **Initiating identity is preserved, not replaced.** The one place a machine principal COULD
   have been used as a stand-in for a human decision — `routeEscalationsToJudiciary`, which
   opens a judiciary case from an autonomous tick — instead preserves the real
   `coalition_escalations.created_by_actor_id` as `complainant_actor_id`. The machine principal
   that *executes* the routing is never the complainant. Verified:
   `aud004-m5-machine-principals.test.ts` ("initiating human/agent identity is preserved").
4. **No DB-level actor_type exemption.** The migration-142 independence triggers
   (`civ_evaluation_independence_guard`, `judiciary_appellate_independence_guard`) compare actor
   *ids*, not `actor_type`. A `service` actor is exactly as capable of self-evaluating (and
   exactly as blocked from doing so) as a `human` one — verified directly against the DB in
   `aud004-m5-machine-principals.test.ts`. Machines are not banned from legitimate evaluation
   (a service CAN evaluate a human's proposal); they cannot evaluate their OWN proposal, same as
   anyone else.
5. **A governed write requires a real, registered actor — enforced by the DB, not convention.**
   Every governed table's actor/evaluator/complainant column is `NOT NULL REFERENCES actors(id)`.
   An unregistered (well-formed but never-inserted) actor id is rejected by the foreign-key
   constraint before any application logic runs — verified directly.

## Residual / follow-up (not closed by this pass)

- **Machine-principal RBAC is not yet enforced at the service-call boundary.** Unlike HTTP
  routes (gated by `requirePrincipal` + `verifyAuthority`), in-process service-to-service calls
  (workers calling `safeEvolution.retain(...)` directly) do not re-verify that the calling code
  path is *authorized* to use a given machine principal — the boundary is "this code, running
  in this process, is trusted to act as this actor," which is the same trust boundary the whole
  backend process already operates under (single deployable, single DB credential per role).
  Formalizing per-worker credentials (e.g. mTLS client certs per worker, or a signed
  service-to-service token) would close this gap but is infrastructure work beyond this
  remediation's scope.
- **No automated rotation/revocation path for machine principals yet.** They are provisioned
  idempotently and never explicitly revoked; if a worker component is deprecated, its actor row
  and permissions should be manually revoked (`UPDATE actors SET status='suspended'`) — not yet
  automated.
- **Python capability stacks (AUD-009) remain out of this registry** — they have zero DB
  connection / zero mutation authority (independently verified in the audit), so they are not
  machine principals in the governed-state sense; nothing to register.
