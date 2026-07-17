# Volume 22 — Hypothesis Generation Framework

## 1. Header

| Field | Value |
|---|---|
| Volume | 22 |
| Name | Hypothesis Generation Framework |
| Tier | charter |
| Epistemic status | aspirational |
| Doc status | written |
| Related volumes | V20 (Knowledge Discovery Framework), V21 (Reality Models), V12 (Governance), V15 (Capability Expansion) |

## 2. Purpose

The Hypothesis Generation Framework is how AgentCo will generate possibilities to explore —
counterfactuals, alternative futures, architecture proposals, institution proposals,
capability proposals, research questions, optimization opportunities, and uncertainty
exploration. The Domain Neutrality correction renamed this from "Imagination Engine"
(`GENERALIZATION_REPORT.md` §5): imagination is one mechanism within hypothesis generation,
not the whole of it. The load-bearing rule is that **hypotheses are proposals into existing
governed pipelines, never direct state changes**: a generated architecture proposal becomes
a structural-evolution candidate (V19), an institution proposal enters governance (V12), a
capability proposal enters the expansion gate (V15), a research question enters discovery
(V20). Generation is cheap and unconstrained; *acting* on a hypothesis is always governed.

**Scope (one paragraph).** A generator contract (produce candidate hypotheses of a typed
kind), routing that turns each hypothesis into the appropriate governed proposal, and a
scoring step (which hypotheses are worth pursuing, using V11 calibration and V23
constraints to prune the impossible). No hypothesis takes effect directly; every one is a
proposal that the relevant governed pipeline evaluates.

**This framework is not yet designed in detail.** It is a charter. No hypothesis generator
exists today; proposals are authored by services and operators directly rather than
generated and routed by a framework.

**Detailed design may begin when:** (a) the governed proposal pipelines it would feed are
stable (governance V12, expansion V15, structural evolution V19 — V12/V15 are written and
enforced, V19 is written); (b) V16's autonomous loops (especially Improvement and
Research) need a source of candidate hypotheses to pursue; and (c) V23's Constraint Engine
can prune infeasible hypotheses before they consume evaluation budget. Until then this
stays a one-page charter and proposals are authored directly.

## 3. Definitions

_Deferred until detailed design begins (charter)._

## 4. Invariants

_None yet — charter volume. The fixed rule: a hypothesis is a proposal into a governed
pipeline (V12/V15/V19/V20), never a direct state change._

## 5. Interfaces

_Deferred (charter). Intended: a typed generator contract and routing into governed
proposal pipelines._

## 6. State

_Deferred (charter). Today: proposals are authored directly by services/operators; no
generator state exists._

## 7. Failure modes and responses

_Deferred (charter). Rule fixed now: generation is cheap and unconstrained, but acting on
a hypothesis is always governed — no hypothesis mutates state directly._

## 8. Verification obligations

_Deferred (charter)._

## 9. Implementation mapping

_No hypothesis generator exists. Proposals today are authored directly into governance
(`governance.service.ts`), expansion (`capability-expansion.service.ts`), and
safe-evolution (`safe-evolution.service.ts`)._

## 10. Open questions

_Deferred until detailed design begins (charter)._

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Charter written (renamed from Imagination Engine per GENERALIZATION_REPORT §5). | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 34) | Reframe imagination as one mechanism within hypothesis generation, with the fixed rule that hypotheses are governed proposals never direct changes, as a one-page charter until the pipelines it feeds and a consumer (V16) are ready. |
