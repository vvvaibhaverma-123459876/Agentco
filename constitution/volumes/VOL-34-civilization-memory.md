# Volume 34 — Civilization Memory

## 1. Header

| Field | Value |
|---|---|
| Volume | 34 |
| Name | Civilization Memory |
| Tier | statute |
| Epistemic status | mixed |
| Doc status | written |
| Related volumes | V9 (Knowledge System), V18 (Civilization Self Model), V14 (Learning Engine), V1 (Constitutional Core), V17 (Self Inspection) |

## 2. Purpose

Civilization Memory is the durable record of **what happened** — the ordered, hash-chained
event history, promoted agent and shared memory, and the lineage of artifacts and
improvements. It is deliberately separated from the Self Model (V18, *what currently is*)
and from the Knowledge System (V9, the *belief-grounding mechanics*): where V9 defines how
a claim becomes trusted memory, V34 defines the durable, tamper-evident store that memory
and history live in and how it is retrieved and, eventually, forgotten. This split was
mandated by the Domain Neutrality correction (`GENERALIZATION_REPORT.md` §7). Mixed status;
every present-tense claim cites its file.

```text
EVENT SPINE  event_log (mig 080)   ordered, hash-chained (prev_hash, event_hash UNIQUE),
   │         REVOKE UPDATE/DELETE — the immutable "what happened"
   ├─ AGENT MEMORY     agent_memory (mig 002)          per-agent durable state
   ├─ SHARED KNOWLEDGE shared_knowledge (mig 003)       cross-agent memory
   ├─ SELF MEMORY      (mig 114) retrievable self-memory
   ├─ PROMOTED MEMORY  ← from resolved predictions (V9 promotion pipeline)
   ├─ ARTIFACT LINEAGE artifacts_hash_lineage (mig 117) dedup within lineage class
   └─ IMPROVEMENT LINEAGE civ_improvement_lineage (mig 138, V14)
   ▼
RETRIEVE  memory-retrieval.service.ts (retrieveForPlanning, demotionWarnings)
FORGET    (to build) bounded retention / eviction — V9-INV-009 lives here
```

## 3. Definitions

- **Event log** — the ordered, hash-chained, append-only event spine
  (`event_log`, migration `080`; `backend/src/services/event-log.service.ts`).
- **Agent memory** — per-agent durable key/value state
  (`agent_memory`, migration `002`; `backend/src/services/memory-store.service.ts`).
- **Shared knowledge** — cross-agent memory (`shared_knowledge`, migration `003`).
- **Self memory** — an agent's own retrievable memory (migration `114`).
- **Promoted memory** — knowledge admitted from a resolved prediction (V9 pipeline).
- **Lineage** — the recorded ancestry of an artifact or improvement
  (`artifacts_hash_lineage` migration `117`; `civ_improvement_lineage` migration `138`).
- **Retrieval** — surfacing relevant memory for planning
  (`backend/src/services/memory-retrieval.service.ts`).
- **Forgetting** — bounded retention/eviction of low-value memory (to be built; the same
  gap as V9-INV-009).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V34-INV-001 | The event history is an ordered, hash-chained spine whose rows reject UPDATE and DELETE at the database layer. | enforced | `backend/src/db/migrations/080_event_log.sql`, `backend/src/services/event-log.service.ts` |
| V34-INV-002 | Every event carries an actor, a correlation id, and a hash linking it to the prior event, so history is attributable and tamper-evident. | enforced | `backend/src/db/migrations/080_event_log.sql` |
| V34-INV-003 | Agent memory and shared knowledge are durable stores readable and writable through a memory service, not ad hoc. | enforced | `backend/src/services/memory-store.service.ts`, `backend/src/db/migrations/002_agent_memory.sql`, `backend/src/db/migrations/003_shared_knowledge.sql` |
| V34-INV-004 | Memory is retrievable for planning, and retrieval surfaces demotion warnings so weakened memory is flagged. | enforced | `backend/src/services/memory-retrieval.service.ts`, `backend/tests/memory-retrieval.test.ts` |
| V34-INV-005 | An agent's own self-memory is retrievable without dropping or mutating existing memory. | enforced | `backend/src/db/migrations/114_self_memory_retrievable.sql`, `backend/tests/self-memory-loop.test.ts` |
| V34-INV-006 | Artifact lineage is part of artifact identity — content dedup applies within a lineage class, not across, so real lineage is preserved. | enforced | `backend/src/db/migrations/117_artifact_lineage_identity.sql` |
| V34-INV-007 | Improvement lineage links a promoted improvement to its originating failure and candidate. | enforced | `backend/src/db/migrations/138_safe_evolution.sql`, `backend/tests/civilization-learning-e2e.test.ts` |
| V34-INV-008 | Memory has a bounded forgetting/retention policy so low-value memory does not accumulate without limit. | planned | — |
| V34-INV-009 | Long-term lineage is queryable end to end — any promoted memory can be traced to the events and evidence that produced it. | planned | — |

## 5. Interfaces

- **Event spine** — `event-log.service.ts` (`append`, `appendWithClient`), the audit
  substrate every service writes through; `audit-log.service.ts` (hash-chain verify).
- **Memory store** — `memory-store.service.ts` (`readAgentMemory`, `writeAgentMemory`,
  `readSharedKnowledge`, `writeSharedKnowledge`, `getAgentState`).
- **Retrieval** — `memory-retrieval.service.ts` (`retrieveForPlanning`,
  `demotionWarnings`).
- **Promotion seam** — `memory-promotion-pipeline.service.ts` (V9) writes promoted
  memory.
- **Lineage** — artifact lineage (migration `117`), improvement lineage (migration
  `138`, V14).

## 6. State

- **Event history:** `event_log` (migration `080`, hash-chained, append-only), plus the
  decision log (V1, migration `004`).
- **Memory:** `agent_memory` (migration `002`), `shared_knowledge` (migration `003`),
  self-memory retrievability (migration `114`).
- **Lineage:** `artifacts_hash_lineage` (migration `117`), `civ_improvement_lineage`
  (migration `138`).
- **Retrieval index:** the evidence vector index (V9, migration `101`) supports semantic
  recall.

## 7. Failure modes and responses

- **Rewriting history** — `event_log` REVOKEs UPDATE/DELETE and chains each event by hash
  (V34-INV-001, V34-INV-002), so the historical record is tamper-evident even to
  privileged roles (the same principle as the decision log, V1).
- **Lost lineage** — artifact dedup is scoped within a lineage class, so a real
  descendant is not collapsed into its ancestor by a hash collision (V34-INV-006, the bug
  migration `117` fixed).
- **Retrieving stale belief** — retrieval surfaces demotion warnings (V34-INV-004), so
  weakened memory (from V9 retraction/contradiction) is flagged rather than served as
  fact.
- **Unbounded growth** — no forgetting policy exists; memory accumulates monotonically
  (V34-INV-008 planned) — the same gap as V9-INV-009, and this volume is its home.
- **Untraceable provenance** — end-to-end lineage query (memory → events → evidence) is
  not yet a single traversal (V34-INV-009 planned).

## 8. Verification obligations

Existing and green today: `backend/tests/memory-retrieval.test.ts`,
`backend/tests/self-memory-loop.test.ts`, event-log immutability/chaining tests, and the
learning-lineage e2e (`backend/tests/civilization-learning-e2e.test.ts`).

Must exist before the planned invariants flip: a forgetting/retention policy with a
bounded-growth test (V34-INV-008), and an end-to-end lineage query test tracing promoted
memory to its events and evidence (V34-INV-009).

## 9. Implementation mapping

- `backend/src/services/event-log.service.ts`, `audit-log.service.ts` — the hash-chained
  event spine and its verification.
- `backend/src/services/memory-store.service.ts`,
  `backend/src/services/memory-retrieval.service.ts` — durable memory and retrieval.
- `backend/src/services/memory-promotion-pipeline.service.ts` — the V9 promotion seam.
- Migrations: `002` (agent memory), `003` (shared knowledge), `080` (event log), `114`
  (self memory), `117` (artifact lineage), `138` (improvement lineage).

## 10. Open questions

1. **Forgetting has no home until now.** V9 named the missing forgetting policy; this
   volume owns it (V34-INV-008). A value/age retention policy with a bounded-growth test
   is the concrete next step — the single most-cited gap across V9 and V34.
2. **Lineage is fragmented.** Artifact lineage (migration `117`), improvement lineage
   (migration `138`), event correlation ids, and evidence provenance (V9, migration
   `137`) are separate traversals; a unified lineage query (V34-INV-009) would let any
   memory be traced to its origin in one path.
3. **Boundary with V9.** V9 owns the belief *mechanics* (grounding, promotion rules,
   retraction); V34 owns the *store and history*. The promotion pipeline sits on the seam;
   which volume's invariants govern a given behaviour should be read as: V9 = "may this
   become memory?", V34 = "how is it stored, retrieved, and forgotten?".

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written (new volume, split from Self Model per GENERALIZATION_REPORT §7). | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 22) | Bind the hash-chained event spine, durable memory stores, retrieval, and lineage into one citable history layer — the "what happened" store separated from structure (V18) and belief mechanics (V9) — and give the missing forgetting policy a home. |
