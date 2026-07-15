# Volume 1 — Constitutional Core

## 1. Header

| Field | Value |
|---|---|
| Volume | 1 |
| Name | Constitutional Core |
| Tier | constitutional |
| Epistemic status | mixed |
| Doc status | written |
| Related volumes | V0 (Vision), V4 (Identity & Authority), V12 (Governance), V13 (Judiciary), V27 (Operator Control Plane), V31 (Civilization Evolution) |

## 2. Purpose

The Constitutional Core defines the civilization's immutable foundations: what the
civilization *is* (identity), what it may never quietly change about itself (protected
invariants and surfaces), the hierarchy that ranks every norm in the system, how
legitimate change happens (amendment rules and meta-governance), and the safety
principles that sit beneath every other volume. Everything else in this constitution is
amendable machinery; this volume states what amendment itself must respect.

### The constitutional hierarchy

Every norm in AgentCo belongs to exactly one level. A lower level can never amend a
higher one, and every act is bound by all levels above it:

```text
H0  Human root authority      — outside the system; cannot be voted away
      enforced today by: kill switch, override queue, operator console
H1  Protected invariants      — testable sentences no process may violate
      today: civilization_protected_invariants, protected surfaces,
      constitution/invariants.yaml
H2  Constitutional documents  — this constitution; versioned runtime constitution
      today: constitution/ volumes, constitution_versions, civilization_charters
H3  Statutes                  — enacted, enforceable runtime policy
      today: runtime_policies via governance proposals (V12)
H4  Institutional charters    — mandates, powers, limits of institutions (V6)
H5  Decisions and acts        — every recorded decision and state change
      today: decision_log (hash-chained), event_log
```

### Safety principles

1. **Fail closed at the base.** Tamper-evidence and append-only enforcement live at the
   database layer (triggers), not in application code that could be bypassed.
2. **Power is time-bounded.** Emergency powers carry expiries by schema constraint;
   nothing extraordinary is permanent.
3. **No self-judging.** The machinery that validates change is not the machinery being
   changed (checker vs volumes; evaluator ≠ proposer in V14/V19).
4. **Human authority is root (H0).** No design in any volume may remove the kill switch
   or place H0 inside the system's own amendment power (V0-INV-004, V1-INV-008).

## 3. Definitions

- **Constitution (runtime)** — a versioned, content-hashed, signed document row
  (`constitution_versions`) with activation/retirement lifecycle
  (`backend/src/services/calibration-constitution.service.ts`, migration
  `027_calibration_constitution.sql`).
- **Constitution (architecture)** — this document series (`constitution/`), drift-checked
  in CI (V0-INV-001).
- **Civilization charter** — the kernel-level identity document of a civilization
  instance (`civilization_charters`, migration `129_civilization_kernel.sql`).
- **Protected invariant** — a registered rule no process may violate
  (`civilization_protected_invariants`; doc-level: `constitution/invariants.yaml`).
- **Protected surface** — a declared set of tables/columns/functions that is immutable
  or requires a constitution-level vote to touch (`protected_surfaces` machinery in
  `calibration-constitution.service.ts`; `backend/tests/protected-surface-enforcer.test.ts`).
- **Amendment** — a recorded, human-authorized change to an H1/H2 artifact.
- **Emergency power** — a time-bounded extraordinary authority
  (`governance_emergency_powers`, migration `135_governance.sql`).
- **Kill switch** — the human-scope stop mechanism
  (`backend/src/services/kill-switch.service.ts`).
- **Meta-governance** — the rules about changing the rules (quorum, ratification,
  cooling-off) — design territory of V12/V31, bounded by this volume.
- **Civilization identity** — the singleton civilization row, its version lineage and
  jurisdictions (`civilizations`, `civilization_versions`,
  `civilization_jurisdictions`, migration `129_civilization_kernel.sql`).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V1-INV-001 | Every decision is recorded in an append-only, hash-chained decision log whose rows reject UPDATE and DELETE at the database layer. | enforced | `backend/src/db/migrations/012_decision_log_chain.sql`, `backend/src/db/migrations/014_decision_log_immutability_triggers.sql` |
| V1-INV-002 | Civilization identity and lifecycle state change only through explicit transaction-scoped authorization, and every transition appends to kernel history. | enforced | `backend/src/db/migrations/129_civilization_kernel.sql`, `backend/src/services/civilization-kernel.service.ts`, `backend/tests/civilization-kernel.test.ts` |
| V1-INV-003 | The runtime constitution is versioned, content-hashed, and signed; its integrity is verifiable; and declared protected surfaces subject changes to immutability or vote requirements. | enforced | `backend/src/db/migrations/027_calibration_constitution.sql`, `backend/src/services/calibration-constitution.service.ts`, `backend/tests/calibration-constitution.test.ts`, `backend/tests/protected-surface-enforcer.test.ts` |
| V1-INV-004 | Emergency powers are time-bounded by schema constraint, their activation and revocation are governed recorded acts, and an activated kill switch stops governed run loops. | enforced | `backend/src/db/migrations/135_governance.sql`, `backend/src/services/kill-switch.service.ts`, `backend/src/services/run-guard.service.ts`, `backend/tests/civilization-e2e-scenarios.test.ts` |
| V1-INV-005 | An enacted statute changes runtime behaviour: policy enforcement is checked at execution time, not merely recorded. | enforced | `backend/src/services/policy-enforcement.service.ts`, `backend/tests/governance.test.ts` |
| V1-INV-006 | A change to a constitutional-tier volume without a recorded authorizing human fails CI (mechanical amendment gate). | planned | — |
| V1-INV-007 | A statute that contradicts a protected invariant fails enactment, fail-closed (constitutionality validation at enactment time). | planned | — |
| V1-INV-008 | Meta-governance may evolve the civilization's own constitutional processes, but human root authority and the protected-invariant mechanism remain outside the system's own amendment power. | aspirational | — |

## 5. Interfaces

- **Kernel APIs** — bootstrap, lifecycle transitions, jurisdictions, objectives, and
  emergency state (`backend/src/routes/civilization-kernel.routes.ts`); guarded
  transitions require transaction-scoped `set_config('civilization.*_transition_authorized', …)`
  gates set only by the kernel service (`backend/src/services/civilization-kernel.service.ts`).
- **Runtime constitution APIs** — constitution versions, protected surfaces, and change
  validation are exposed through governance routes
  (`backend/src/routes/governance.routes.ts`,
  `backend/src/routes/civilization-governance.routes.ts`) and consumed by risk
  classification (`backend/src/services/risk-tier-classifier.service.ts`), change
  governance (`backend/src/services/calibration-change-governance.service.ts`), and the
  autonomy orchestrator (`backend/src/services/autonomy-orchestrator.service.ts`).
- **Emergency and stop** — governed emergency powers and kill-switch activation
  (`backend/src/services/governance.service.ts`), surfaced to humans in the operator
  console (`frontend/src/app/civilization/page.tsx`), which requires a typed reason.
- **Drift checking** — `scripts/constitution/check_constitution.py` in CI
  (`.github/workflows/constitution.yml`).

## 6. State

- **Kernel (migration `129_civilization_kernel.sql`):** `civilizations` (singleton
  identity), `civilization_versions`, `civilization_charters`,
  `civilization_jurisdictions`, `civilization_protected_invariants`,
  `civilization_emergency_states`, `civilization_state_transitions` (append-only
  history), `civilization_objectives`.
- **Governance (migration `135_governance.sql`):** `governance_proposals`,
  `proposal_sponsors`, `impact_assessments`, `deliberations`, `governance_votes`,
  `governance_decisions`, `runtime_policies`, `policy_activations`,
  `governance_emergency_powers` (expiry-constrained).
- **Runtime constitution (migrations `027`–`029`):** constitution versions, protected
  surfaces, allowed/prohibited change types, change requests.
- **Decision record (migrations `004`, `012`, `014`, `125`, `126`):** `decision_log`
  with `chain_hash`/`prev_hash` (SHA-256 chain, all-zeros genesis) and unconditional
  BEFORE UPDATE/DELETE triggers.
- **Documents:** `constitution/` (volumes, `invariants.yaml`, `INDEX.md`).

## 7. Failure modes and responses

- **Tampering with history** — UPDATE/DELETE on `decision_log` raises at the DB layer
  (migration `014`); the hash chain makes silent edits detectable even by superusers
  who disable triggers (chain verification in the audit-log service, migration `012`).
- **Silent constitutional drift** — the CI checker fails on header/INDEX disagreement,
  dead enforcement paths, and domain-lexicon violations (V0-INV-001/002/009).
- **Ungoverned emergency** — emergency powers cannot be created without expiry
  (schema CHECK, migration `135`); kill-switch state is honored by the run loops
  (`run-guard.service.ts`, `civilization-scheduler.service.ts`,
  `supervised-free-run.service.ts`, `civilization-os.service.ts`) and its activation is
  itself an audited event; end-to-end emergency behaviour is proven by scenario H
  (`backend/tests/civilization-e2e-scenarios.test.ts`).
- **Self-amendment capture** — H0 sits outside the system (operator console + override
  queue); the mechanical amendment gate for H2 documents does not exist yet
  (V1-INV-006, planned) — today it is procedural (CONVENTIONS.md change-log rule).
- **Unconstitutional statutes** — nothing today validates a new `runtime_policies` row
  against protected invariants at enactment (V1-INV-007, planned). Gap stated honestly:
  a governance majority could currently enact a statute contradicting H1 and it would
  bind until judicially struck (V13).
- **Constitutional fragmentation** — three constitutional artifacts coexist (see §10).

## 8. Verification obligations

Existing and green today: `backend/tests/civilization-kernel.test.ts` (identity,
transitions, protected invariants), `backend/tests/governance.test.ts` (scenario C —
governance changes behaviour), `backend/tests/civilization-e2e-scenarios.test.ts`
(scenario H — emergency state), `backend/tests/calibration-constitution.test.ts`,
`backend/tests/protected-surface-enforcer.test.ts`, and the constitution drift checker
in CI (`.github/workflows/constitution.yml`).

Must exist before the planned invariants flip to enforced: a CI amendment gate that
diffs `constitution/volumes/` for constitutional-tier changes and requires a change-log
row naming the authorizing human (V1-INV-006); enactment-time constitutionality
validation with fail-closed tests (V1-INV-007).

## 9. Implementation mapping

- Hash-chained decision record: `backend/src/db/migrations/004_decision_log.sql`,
  `012_decision_log_chain.sql`, `014_decision_log_immutability_triggers.sql`,
  `125_decision_log_protocol_version.sql`, `126_decision_log_attempt_id.sql`.
- Civilization identity and kernel: `backend/src/services/civilization-kernel.service.ts`
  (seeds and counts protected invariants; guards lifecycle transitions),
  `backend/src/routes/civilization-kernel.routes.ts`, migration `129`.
- Runtime constitution: `backend/src/services/calibration-constitution.service.ts`
  (versions with content hash + signature, `verifyIntegrity`, protected surfaces,
  allowed/prohibited change types, `validateChange` → compliance verdict with
  override-requirement flag), migrations `027`–`029`. Note: "calibration" in the name
  is legacy — the machinery is generic (§10.2).
- Statute enforcement: `backend/src/services/governance.service.ts` (proposals, votes,
  enactment, emergency powers), `backend/src/services/policy-enforcement.service.ts`
  (`assertAllowed` consulted at execution time, e.g. mission creation in
  `backend/src/services/mission.service.ts`).
- Human root authority: `backend/src/services/kill-switch.service.ts` (activation with
  scope + reason + audit event), `backend/src/services/override-queue.service.ts`
  (human approval of protected actions), protected-execution gating for citizens
  (`backend/src/services/citizenship.service.ts`), operator console kill switch with
  mandatory reason (`frontend/src/app/civilization/page.tsx`).

To be built (prescriptive): the mechanical amendment gate (V1-INV-006), enactment-time
constitutionality validation (V1-INV-007), and the unification plan of §10.1.

## 10. Open questions

1. **Three constitutional artifacts, no declared supremacy.** The architecture
   constitution (`constitution/`), the runtime constitution (`constitution_versions`),
   and the kernel charter (`civilization_charters`) coexist without a binding rule for
   which prevails on conflict. Proposed resolution for V12 to ratify: H2 supreme text =
   this document series; `constitution_versions` = its machine-enacted excerpt; kernel
   charters = per-civilization-instance identity documents subordinate to both.
2. **Legacy naming.** `calibration-constitution.service.ts` and migrations `027`–`029`
   implement *generic* constitutional machinery under a calibration-era name. Renaming
   is a Structural Evolution (V19) migration item; until then this volume is the naming
   bridge.
3. **Three protected-invariant registries** (`civilization_protected_invariants`,
   protected surfaces, `constitution/invariants.yaml`) with no cross-reconciliation —
   nothing verifies they agree. Candidate mechanism: extend the constitution checker or
   Self Inspection (V17) to reconcile doc-level and runtime registries.
4. **Amendment gating is procedural, not mechanical** (V1-INV-006) — the change-log
   rule exists in `constitution/CONVENTIONS.md` but nothing fails CI when it is skipped.
5. **No statute-constitutionality check at enactment** (V1-INV-007) — enforcement
   exists at execution time (V1-INV-005) but legality review happens only after the
   fact, via the judiciary (V13).

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 2) | Bind the existing tamper-evidence, kernel-identity, runtime-constitution, emergency, and enforcement machinery into one constitutional hierarchy before any dependent volume is written. |
