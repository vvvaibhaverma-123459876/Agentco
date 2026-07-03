# Civilization Learning Backbone

## What it is

The seam that makes AgentCo's civilization a **producer** of learning, not
only a governor of it. Before this, institutional claims (from vetting and
synthesis) dead-ended in `autonomy_claims`; nothing turned them into durable
knowledge the planner reuses.

Flow:

```
completed institutional findings (Production / Verification / Audit)
  -> institutional synthesis   (composite DERIVED claim, bounded confidence)
  -> InstitutionalKnowledgeBridge.promoteInstitutionalClaim
       (fail-closed guards, transactional, idempotent, event-logged)
  -> agent_memories (semantic, namespace 'institutional_knowledge')
  -> memory-retrieval surfaces it to the planner (the same path the planner
     already uses for prediction lessons)
  -> a later planner run — same domain, or a DIFFERENT domain on the same
     topic (cross-society) — carries the institution's knowledge in context
```

Entry points: `civilizationLiveFlow.synthesizeAndPromoteKnowledge(...)` (one
call: synthesize + promote) or `institutionalKnowledgeBridge.promoteFromSynthesis(...)`.

## Fail-closed guards (production behavior)

A surviving institutional claim is promoted **only if** it exists, is
`supported`, was produced by an institutional producer (`institutional-synthesis`
/ `institution-claim-vetting`), carries registered evidence ids, and clears
`MIN_PROMOTION_CONFIDENCE` (0.6). Otherwise the bridge records a **blocked**
row in `institutional_knowledge_promotions` with the reason and an
`institution.knowledge_promotion_blocked` event — the civilization can refuse
to turn a weak or ungrounded belief into durable knowledge, and an auditor can
see why. Empty evidence is additionally rejected upstream by the
`claim_must_have_evidence` DB constraint.

Promotion is **idempotent** (one memory per institutional claim, enforced by a
`UNIQUE` constraint and a `FOR UPDATE` check) and **transactional** (memory,
promotion record, and event are one commit or none).

## Verification

- Clean-room (no LLM/web): `tests/civilization-learning-backbone-e2e.test.ts`
  — synthesis -> promotion -> retrieval -> planner prompt, cross-society
  transfer, and the three fail-closed cases.
- Live (opt-in, `RUN_REAL_LLM_TESTS=1`):
  `tests/civilization-learning-backbone-live.test.ts` — institution knowledge
  is promoted and reaches a real planner call against the configured provider;
  skips cleanly without credentials.

## Honest limits

- This makes institutional knowledge **available** to the planner; whether the
  live model acts on it in a given step is the model's evidence-governed choice
  (in a live run it may sensibly gather more evidence first).
- Cross-society retrieval uses full-text matching (`plainto_tsquery` ANDs
  terms), so transfer fires when another society works on a genuinely related
  topic — not for arbitrary unrelated goals. A semantic/embedding retrieval
  upgrade would broaden this.
- Promotion currently targets durable **memory**. Institutional claims that
  encode a reusable *strategy* still go through the existing
  learner→skill pipeline; the bridge does not attempt to infer strategies from
  free-text claims (that would be unreliable).
- This is a runtime capability with tests and event lineage. It is **not** a
  hosted-production certification (SLOs, DR, deployment) — see
  `docs/CURRENT_IMPLEMENTATION_REALITY.md`.
