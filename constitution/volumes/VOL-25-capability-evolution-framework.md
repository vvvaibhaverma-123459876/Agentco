# Volume 25 — Capability Evolution Framework

## 1. Header

| Field | Value |
|---|---|
| Volume | 25 |
| Name | Capability Evolution Framework |
| Tier | statute |
| Epistemic status | prescriptive |
| Doc status | written |
| Related volumes | V15 (Capability Expansion), V14 (Learning Engine), V11 (Trust & Calibration), V6 (Institutions), V20 (Knowledge Discovery Framework) |

## 2. Purpose

The Capability Evolution Framework is the **universal lifecycle every capability follows** —
the mechanism that makes coding just one capability among many. The Domain Neutrality
correction renamed this from "Coder Civilization" (`GENERALIZATION_REPORT.md` §1): there is
no privileged coding architecture; the coder in `selfcoding/` is one *instance* of a
capability being developed, and the same lifecycle governs any capability. This volume
defines that one lifecycle and binds the pieces that already implement parts of it (V14
learning, V15 expansion gates) into a single named contract. Prescriptive tier: the unified
framework as one artifact does not yet exist; §9 cites the distributed substrate honestly.

```text
THE ONE LIFECYCLE (every capability, no exceptions):
   capability gap        (generality tracker, V15 mig 103)
      ▼ verification      does the gap justify a new capability?
      ▼ research          (V20 Knowledge Discovery)          ── no first-class record (M4)
      ▼ knowledge acquisition                                 ── no first-class record (M4)
      ▼ experimentation   (falsifiable predictions, V11)
      ▼ implementation    (skill-library versions, V14 mig 105)
      ▼ evaluation        (proof of competence, V15 mig 106)
      ▼ independent verification  (evaluator ≠ proposer, V14)
      ▼ promotion         (skill promotion loop, V14 mig 108)
      ▼ monitoring        (canary, V14)
      ▼ restriction OR retirement  (capability grants revoke/restrict, V15)
   ── coding is ONE instance of this lifecycle (selfcoding/), not the architecture
```

## 3. Definitions

- **Capability** — anything AgentCo can do, developed through the one lifecycle (coding,
  and any future skill). No capability is architecturally privileged (V0-INV-009).
- **Capability lifecycle** — the eleven-stage path above, applied to every capability.
- **Instance** — a specific capability being developed; `selfcoding/` is the coding
  instance (a quarantined Python sandbox per `docs/civilization/CANONICAL_RUNTIME_MAP.md`).
- **Skill** — an implemented, versioned capability artifact
  (`skill_library_versions`, migration `105`; `backend/src/services/skill-library.service.ts`).
- **Research / knowledge-acquisition stages** — the "how do we learn to do this?" stages
  (V20); not yet first-class records (`GENERALIZATION_REPORT.md` M4).

## 4. Invariants

Prescriptive: the unified framework is planned; enforced entries are the real lifecycle
stages that already exist, named as distributed pieces.

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V25-INV-001 | An implemented capability is a versioned skill with regression coverage required before promotion. | enforced | `backend/src/services/skill-library.service.ts`, `backend/src/db/migrations/105_skill_library.sql` |
| V25-INV-002 | A capability is admitted only through the five-stage expansion gate with an independent competence proof (the evaluation/verification stages). | enforced | `backend/src/services/capability-expansion.service.ts`, `backend/src/services/proof-of-competence.service.ts` |
| V25-INV-003 | Promotion and rollback of a capability follow the learning engine's independent-evaluation and canary gates. | enforced | `backend/src/services/safe-evolution.service.ts`, `backend/tests/safe-evolution.test.ts` |
| V25-INV-004 | Coding is treated as one capability instance, not privileged architecture — no service, route, or table is named for coding. | enforced | `scripts/constitution/check_constitution.py` |
| V25-INV-005 | The eleven-stage capability lifecycle is a single named contract that every capability provably traverses. | planned | — |
| V25-INV-006 | The research and knowledge-acquisition stages have first-class records, so a capability's "how we learned it" is auditable. | planned | — |
| V25-INV-007 | Any capability can be developed through the framework without new architecture (a new capability = registry + lifecycle, not new code paths). | planned | — |
| V25-INV-008 | Capability monitoring after promotion feeds automatic restriction or retirement on degradation. | planned | — |
| V25-INV-009 | The coding instance (selfcoding/) is either promoted to a canonical capability under this framework or retired, resolving its quarantined status. | planned | — |

## 5. Interfaces

Prescriptive — the intended contract binds existing services:

- **Gap** — generality tracker (V15, migration `103`).
- **Verification/evaluation** — proof of competence (V15, migration `106`), safe
  evolution independent evaluation (V14).
- **Implementation** — `skill-library.service.ts` (versioned skills).
- **Promotion/rollback** — skill promotion loop (V14, migration `108`), canary (V14).
- **Restriction/retirement** — capability grants revoke/restrict (V15).
- **Instance** — `selfcoding/` (coding), a quarantined sandbox to be resolved.

## 6. State

- **Substrate today:** `skill_library_entries`/`skill_library_versions` (migration `105`),
  `proof_of_competence` (migration `106`), expansion tables (migration `139`), safe
  evolution tables (migration `138`), generality runs (migration `103`).
- **To be built:** a single capability-lifecycle record spanning all eleven stages
  (today the stages live in separate tables), and first-class research/knowledge-
  acquisition records (M4).

## 7. Failure modes and responses

- **Privileged capability** — the Domain Neutrality checker fails CI on a coding-named
  architectural volume, and no service/table is coding-named (V25-INV-004); coding is an
  instance, not the architecture.
- **Capability without proof** — admission requires the five-stage gate and an
  independent competence proof (V25-INV-002), and promotion requires regression coverage
  and independent evaluation (V25-INV-001, V25-INV-003) — the same no-self-judging rule.
- **Fragmented lifecycle** — the eleven stages exist but across separate subsystems; there
  is no single named lifecycle a capability provably traverses (V25-INV-005 planned) —
  the core unification gap.
- **Missing research record** — the research and knowledge-acquisition stages have no
  first-class records (V25-INV-006 planned; M4), so "how we learned to do this" is not
  auditable.
- **Quarantined coder** — `selfcoding/` is a sealed Python sandbox, neither promoted to a
  canonical capability nor retired (V25-INV-009 planned).

## 8. Verification obligations

Existing and green today: skill-library versioning + regression coverage
(`backend/tests/skill-library.test.ts`), expansion gate + competence proof
(`backend/tests/capability-expansion.test.ts`, `proof-of-competence.test.ts`), safe
evolution (`backend/tests/safe-evolution.test.ts`), the Domain Neutrality checker.

Must exist to satisfy the volume: a single capability-lifecycle record + a test proving
every capability traverses it (V25-INV-005), first-class research/knowledge-acquisition
records (V25-INV-006), and a new-capability-without-new-architecture demonstration
(V25-INV-007).

## 9. Implementation mapping

- **Enforced stages (distributed today):** `skill-library.service.ts` (implementation),
  `capability-expansion.service.ts` + `proof-of-competence.service.ts` (admission/
  evaluation), `safe-evolution.service.ts` (promotion/rollback), generality tracker (gap).
- **Coding instance:** `selfcoding/` (coder/planner/resolver/sandbox), quarantined per
  `docs/civilization/CANONICAL_RUNTIME_MAP.md`.
- **Not yet built:** the single named eleven-stage lifecycle contract, first-class
  research/knowledge-acquisition records (M4), and the new-capability-without-new-code
  demonstration.

## 10. Open questions

1. **Unify the lifecycle record.** The eleven stages exist across V14/V15 tables; a single
   capability-lifecycle record (or a view over them) keyed by capability would let
   V25-INV-005 be proven and make "every capability follows the same path, no exceptions"
   real rather than aspirational.
2. **Research/acquisition stages (M4).** These are the two stages with no home; they
   belong to the Knowledge Discovery Framework (V20) but must record into the capability
   lifecycle so a capability's provenance is complete.
3. **Resolve the coder instance.** `selfcoding/` proves the framework can develop the
   coding capability, but it is quarantined; promoting it to a canonical capability under
   this framework (or retiring it) would validate the framework on its founding example
   (V25-INV-009).

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written (renamed from Coder Civilization per GENERALIZATION_REPORT §1). | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 29) | Define the one universal capability lifecycle that makes coding one capability among many, bind the distributed stages that already implement parts of it, and mark the unified lifecycle record and research stages as to-be-built. |
