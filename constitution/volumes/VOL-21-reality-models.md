# Volume 21 — Reality Models

## 1. Header

| Field | Value |
|---|---|
| Volume | 21 |
| Name | Reality Models |
| Tier | charter |
| Epistemic status | aspirational |
| Doc status | written |
| Related volumes | V20 (Knowledge Discovery Framework), V22 (Hypothesis Generation Framework), V9 (Knowledge System), V23 (Constraint Engine) |

## 2. Purpose

Reality Models is how AgentCo will represent and reason about domains of reality —
physical, biological, social, political, legal, economic, computational, software,
infrastructure, organizational, agent, civilization, and **future model classes not yet
imagined**. The Domain Neutrality correction renamed this from "World Models"
(`GENERALIZATION_REPORT.md` §4) precisely so the set of model classes is an **open
registry, not a fixed taxonomy**: the architecture must admit unlimited future model
classes without redesign.

**Scope (one paragraph).** A model-class registry (model classes as data), a common model
contract (a model makes falsifiable predictions about its domain that resolve against
observation, feeding V11), and the boundary that a model is a *representation used for
reasoning*, never a source of ungrounded truth — its predictions are calibrated like any
other (V11) and its assertions grounded like any other (V9). Reality Models feed the
Constraint Engine (V23, physical/economic/legal constraints come from models) and the
Hypothesis Generation Framework (V22, counterfactuals run against models).

**This framework is not yet designed in detail.** It is a charter. No model-class registry
or model contract exists today; domain reasoning happens implicitly inside individual
services (e.g. the economy models scarcity, the calibration layer models predictive
accuracy) rather than through an explicit Reality Models layer.

**Detailed design may begin when:** (a) there is a concrete need for at least two distinct
model classes to be represented explicitly and reasoned over (rather than embedded in a
service); (b) V11's calibration substrate is used to score model predictions (V11 is
written and enforced, so this is available); and (c) the Constraint Engine (V23) or
Hypothesis Generation (V22) has a concrete consumer that needs a model to reason against.
Until then this stays a one-page charter and domain reasoning stays implicit in services.

## 3. Definitions

_Deferred until detailed design begins (charter)._

## 4. Invariants

_None yet — charter volume. Any model will inherit V9 grounding and V11 calibration
obligations; model classes must be an open registry, not an enum._

## 5. Interfaces

_Deferred (charter). Intended: a model-class registry and a common model contract._

## 6. State

_Deferred (charter). Today: domain reasoning is implicit inside services (economy,
calibration), with no explicit model layer._

## 7. Failure modes and responses

_Deferred (charter). Rule fixed now: a model is a representation for reasoning, never a
source of ungrounded truth._

## 8. Verification obligations

_Deferred (charter)._

## 9. Implementation mapping

_No explicit Reality Models layer exists. Implicit domain models live inside services
(e.g. `treasury.service.ts` models scarcity; the calibration layer models predictive
accuracy)._

## 10. Open questions

_Deferred until detailed design begins (charter)._

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Charter written (renamed from World Models per GENERALIZATION_REPORT §4). | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 33) | Keep the set of reality-model classes an open registry admitting unlimited future classes, as a one-page charter until two explicit model classes and a concrete consumer exist. |
