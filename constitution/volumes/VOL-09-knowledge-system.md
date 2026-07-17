# Volume 9 — Knowledge System

## 1. Header

| Field | Value |
|---|---|
| Volume | 9 |
| Name | Knowledge System |
| Tier | statute |
| Epistemic status | descriptive |
| Doc status | written |
| Related volumes | V1 (Constitutional Core), V11 (Trust & Calibration), V13 (Judiciary), V14 (Learning Engine), V34 (Civilization Memory) |

## 2. Purpose

The Knowledge System is how AgentCo distinguishes *what it has grounds to believe* from
*what was merely asserted*. It defines the lifecycle of a belief: evidence is registered,
claims must be grounded in that evidence, knowledge is promoted only from scored
outcomes, provenance is tracked as a graph, and when a foundation is retracted the
retraction propagates transitively so nothing keeps standing on removed ground. This
volume is descriptive: every normative sentence cites the enforcing file or test.

The pipeline, end to end:

```text
observation
   │  register (with content hash + event provenance)
   ▼
EVIDENCE  autonomy_evidence  (evidence-registry.service.ts)
   │  ground: a claim must cite ≥1 registered evidence source,
   │  and every support snippet must be a token-subsequence of it
   ▼
CLAIM  (claim-grounding.service.ts — fabrication is rejected, not scored)
   │  predictions resolve; only RESOLVED, non-post-hoc ones promote
   ▼
MEMORY  agent_memory / shared_knowledge  (memory-promotion-pipeline.service.ts)
   │  provenance recorded as a directed graph
   ▼
PROVENANCE GRAPH  knowledge_provenance_edges  (collective-knowledge.service.ts)
   │  retract a node → transitive propagation that only ever WEAKENS
   ▼
RETRACTION / DEMOTION / CONTRADICTION  (knowledge_retractions, memory_demotions,
                                        contradictions)
```

## 3. Definitions

- **Evidence** — a registered, content-hashed, attributable observation row in
  `autonomy_evidence`, with canonical event provenance (`event_log_id`,
  `registered_by_actor_id`) added by migration `088`
  (`backend/src/services/evidence-registry.service.ts`).
- **Claim** — an assertion that, if it claims support, must cite at least one registered
  evidence source id and whose support snippets must be token-subsequences of that
  evidence (`backend/src/services/claim-grounding.service.ts`).
- **Grounding** — the validation that a claim's cited evidence exists and textually
  contains the quoted support (same file).
- **Memory** — knowledge promoted from a resolved, scored prediction into
  `agent_memory` / `shared_knowledge`
  (`backend/src/services/memory-promotion-pipeline.service.ts`).
- **Provenance edge** — a directed dependency between knowledge nodes
  (`knowledge_provenance_edges`, migration `137`;
  `backend/src/services/collective-knowledge.service.ts`).
- **Retraction** — removal of a knowledge node that propagates transitively to every
  dependent, only ever weakening (retract claim / demote memory), never strengthening
  (`knowledge_retractions`, `retraction_propagations`, migration `137`).
- **Contradiction / demotion** — recorded conflict and the resulting weakening of a
  memory (`contradictions`, `memory_demotions`, migration `118`).
- **Vector index** — embedding-based retrieval over evidence
  (`evidence_vector_index`, migration `101`;
  `backend/src/services/evidence-vector-index.service.ts`).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V9-INV-001 | A claim asserting support is rejected unless every cited source id is registered evidence. | enforced | `backend/src/services/claim-grounding.service.ts`, `backend/tests/claim-grounding.test.ts` |
| V9-INV-002 | A support snippet is rejected unless it is a token-subsequence of the registered evidence it cites (quoted support cannot be fabricated). | enforced | `backend/src/services/claim-grounding.service.ts`, `backend/tests/claim-grounding.test.ts` |
| V9-INV-003 | Registered evidence carries a content hash and canonical event provenance linking it to the event log and the registering actor. | enforced | `backend/src/services/evidence-registry.service.ts`, `backend/src/db/migrations/088_evidence_registry_events.sql` |
| V9-INV-004 | Knowledge is promoted to memory only from a resolved, non-post-hoc prediction that has a trust score — never from an unscored assertion. | enforced | `backend/src/services/memory-promotion-pipeline.service.ts`, `backend/tests/self-memory-loop.test.ts` |
| V9-INV-005 | Retracting a knowledge node propagates transitively to every dependent through the provenance graph, and every propagation effect only weakens knowledge (retract or demote). | enforced | `backend/src/services/collective-knowledge.service.ts`, `backend/src/db/migrations/137_collective_epistemics.sql`, `backend/tests/collective-knowledge.test.ts` |
| V9-INV-006 | A recorded contradiction demotes the affected memory rather than silently overwriting it. | enforced | `backend/src/db/migrations/118_contradictions_and_demotions.sql`, `backend/src/services/collective-knowledge.service.ts` |
| V9-INV-007 | Planners cite grounded claims rather than ungrounded assertions when producing evidence-bearing actions. | enforced | `backend/tests/planner-claim-bias.test.ts` |
| V9-INV-008 | The three protected-invariant-style knowledge registries (doc-level provenance, runtime provenance edges, contradiction records) are periodically reconciled so no dangling or orphaned provenance survives. | planned | — |
| V9-INV-009 | Memory has a bounded forgetting policy so unbounded low-value knowledge does not accumulate. | planned | — |

## 5. Interfaces

- **Evidence registration** — `evidence-registry.service.ts`
  (`register`, `getBySourceIds`) writes `autonomy_evidence` with a content hash and event
  provenance; consumed by the action executor and claim grounding.
- **Claim grounding** — `claim-grounding.service.ts` `validate(input)` returns
  `{ valid, evidenceRows, errors }`; called on evidence-bearing actions.
- **Memory promotion** — `memory-promotion-pipeline.service.ts`
  `promoteResolvedPrediction(predictionId)` reads `prediction_ledger` + `trust_scores`
  and writes memory; the bridge from Volume 11 (Trust & Calibration).
- **Provenance and retraction** — `collective-knowledge.service.ts`
  (`linkProvenance`, `retract`, `isRetracted`, `getRetraction`, `civilizationKnowledge`).
- **Retrieval** — `memory-retrieval.service.ts`, `memory-store.service.ts`, and vector
  search via `evidence-vector-index.service.ts` (migration `101`).
- **Institutional vetting** — `institution-claim-vetting.service.ts` and
  `institutional-knowledge-bridge.service.ts` gate promotion into institutional memory
  (migration `113`).

## 6. State

- **Evidence:** `autonomy_evidence` (migration `050`; provenance columns migration `088`),
  `evidence_artifacts` (migration `018`), `evidence_vector_documents` /
  `evidence_vector_index` (migration `101`).
- **Memory:** `agent_memory` (migration `002`), `shared_knowledge` (migration `003`),
  self-memory retrievability (migration `114`), institutional promotions (migration
  `113`).
- **Provenance & retraction:** `knowledge_provenance_edges`, `knowledge_retractions`,
  `retraction_propagations`, `decision_retraction_flags` (migration `137`);
  `contradictions`, `memory_demotions` (migration `118`).
- **Predictions (source of promotion):** `prediction_ledger` (Volume 11).

## 7. Failure modes and responses

- **Fabricated support** — a claim quoting text not present in its cited evidence is
  rejected at grounding time (V9-INV-002), not scored down later. This is fail-closed:
  the claim is invalid, not merely low-trust.
- **Promotion of unscored belief** — `promoteResolvedPrediction` throws if the
  prediction is unresolved, post-hoc, or lacks a trust score
  (`memory-promotion-pipeline.service.ts`), so nothing enters memory on assertion alone.
- **Knowledge standing on retracted ground** — transitive retraction propagates through
  `knowledge_provenance_edges`; because propagation only ever weakens
  (`collective-knowledge.service.ts`), a bug in the graph can fail to weaken but can
  never *strengthen* on retraction.
- **Contradiction** — recorded in `contradictions` and resolved by demotion, not
  overwrite (migration `118`), preserving the losing memory for audit.
- **Orphaned provenance** — nothing today reconciles the doc-level and runtime provenance
  records (V9-INV-008 planned; open question 1).
- **Unbounded accumulation** — there is no forgetting policy yet (V9-INV-009 planned;
  open question 2). The Vision names "forgetting" as part of this system; it is not built.

## 8. Verification obligations

Existing and green today: `backend/tests/claim-grounding.test.ts`,
`backend/tests/evidence-registry.test.ts`, `backend/tests/evidence-vector-index.test.ts`,
`backend/tests/memory-retrieval.test.ts`, `backend/tests/self-memory-loop.test.ts`,
`backend/tests/collective-knowledge.test.ts`,
`backend/tests/institution-claim-vetting.test.ts`,
`backend/tests/planner-claim-bias.test.ts`.

Must exist before the planned invariants flip: a reconciliation check across the
provenance registries (V9-INV-008) and a forgetting/retention policy with a test proving
bounded growth (V9-INV-009).

## 9. Implementation mapping

- `backend/src/services/evidence-registry.service.ts` — evidence registration with
  content hash + event provenance (`autonomy_evidence`).
- `backend/src/services/claim-grounding.service.ts` — grounding validation
  (registered-source + token-subsequence checks).
- `backend/src/services/memory-promotion-pipeline.service.ts` — promotion from resolved
  predictions with trust lookup.
- `backend/src/services/collective-knowledge.service.ts` — provenance graph, transitive
  retraction, contradiction effects, civilization knowledge view.
- `backend/src/services/memory-retrieval.service.ts`,
  `backend/src/services/memory-store.service.ts`,
  `backend/src/services/evidence-vector-index.service.ts` — storage and retrieval.
- `backend/src/services/provenance.service.ts` — action attestation (Ed25519) linking
  acts to evidence.
- `backend/src/services/institution-claim-vetting.service.ts`,
  `backend/src/services/institutional-knowledge-bridge.service.ts` — institutional
  promotion gates.
- Migrations: `002`, `003`, `018`, `050`, `073`, `088`, `101`, `113`, `114`, `118`,
  `137`.

## 10. Open questions

1. **Provenance registries are not reconciled.** Doc-level provenance intent, runtime
   `knowledge_provenance_edges`, and `contradictions` are separate; nothing verifies they
   agree or that no edge dangles after a retraction (V9-INV-008 planned). Candidate owner:
   Self Inspection (V17).
2. **No forgetting policy.** The Vision lists forgetting; there is no retention/eviction
   mechanism, so memory grows monotonically (V9-INV-009 planned). Needs a value/age
   policy and a bounded-growth test.
3. **Grounding is lexical, not semantic.** Token-subsequence matching
   (`claim-grounding.service.ts`) catches fabricated quotes but not paraphrase that
   distorts meaning; semantic grounding would need the vector index (`101`) in the
   grounding path. Trade-off: lexical grounding is deterministic and testable; semantic
   grounding is stronger but harder to make fail-closed.
4. **Two evidence lineages.** `evidence_artifacts` (migration `018`) predates the
   canonical `autonomy_evidence` path; which is authoritative for new code should be
   frozen (a Volume 2 / canonical-runtime concern).

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 4) | Bind the existing evidence/claim/memory/provenance machinery into one citable belief lifecycle before Trust (V11) and Learning (V14), which build on it. |
