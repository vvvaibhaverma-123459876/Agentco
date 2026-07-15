# Volume 20 — Knowledge Discovery Framework

## 1. Header

| Field | Value |
|---|---|
| Volume | 20 |
| Name | Knowledge Discovery Framework |
| Tier | charter |
| Epistemic status | aspirational |
| Doc status | written |
| Related volumes | V9 (Knowledge System), V11 (Trust & Calibration), V25 (Capability Evolution Framework), V16 (Autonomous Evolution) |

## 2. Purpose

The Knowledge Discovery Framework is how AgentCo will discover new knowledge through
**many methodologies, of which science is only one**. The Domain Neutrality correction
renamed this from "Scientific Research" (`GENERALIZATION_REPORT.md` §2): scientific
experimentation is one method among simulation, formal proof, optimization, observation,
benchmarking, adversarial evaluation, human instruction, evidence synthesis, and future
methodologies. Whatever the method, a discovery must emit **evidence** into the existing
knowledge system (claims, provenance, contradictions — V9) rather than owning a private
store of truth, and its confidence must be calibrated through pre-registered predictions
(V11).

**Scope (one paragraph).** A methodology registry (discovery methods as data, not a fixed
enum), a common discovery contract (question → method → observation → evidence →
calibrated claim), and adapters for each method that all write into V9's evidence graph.
No method is privileged; adding a new methodology is a registry entry, not new
architecture (the Domain Neutrality spirit applied to discovery).

**This framework is not yet designed in detail.** It is a charter. Today the substrate
exists only as instances: benchmarking (`evals/`), adversarial evaluation
(`backend/tests/red-team-corpus.test.ts`), and experimentation with pre-registration and
independent resolution (`backend/src/services/falsifiable-prediction.service.ts`,
`independent-resolver.service.ts`, V11). There is no unifying discovery framework.

**Detailed design may begin when:** (a) V9 (Knowledge System) and V11 (Trust &
Calibration) are stable enough to serve as the shared evidence + calibration substrate
(both are written and enforced); (b) V16's Autonomous Research loop
(V16-INV-007) has a home to call discovery from; and (c) at least two distinct
methodologies (e.g. benchmarking and experimentation) are ready to be expressed through a
common discovery contract, proving the abstraction against more than one method. Until
then this stays a one-page charter, and discovery happens through the existing instances.

## 3. Definitions

_Deferred until detailed design begins (charter)._

## 4. Invariants

_None yet — charter volume. Discovery invariants will be defined when the framework is
designed; any discovery method will inherit V9's grounding and V11's calibration
obligations._

## 5. Interfaces

_Deferred (charter). Intended: a methodology registry and a common discovery contract
writing into V9._

## 6. State

_Deferred (charter). Substrate today: `evals/`, the adversarial corpus, and the
falsifiable-prediction machinery (V11)._

## 7. Failure modes and responses

_Deferred (charter). The key rule already fixed: no discovery method owns a private truth
store; all emit evidence into V9._

## 8. Verification obligations

_Deferred (charter)._

## 9. Implementation mapping

_Instances only today: `evals/` (benchmarking), `backend/tests/red-team-corpus.test.ts`
(adversarial), `backend/src/services/falsifiable-prediction.service.ts` (experimentation).
No unifying framework exists._

## 10. Open questions

_Deferred until detailed design begins (charter)._

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Charter written (renamed from Scientific Research per GENERALIZATION_REPORT §2). | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 32) | Reframe discovery as method-agnostic — science one methodology among many — as a one-page charter until the shared evidence/calibration substrate and a second methodology are ready. |
