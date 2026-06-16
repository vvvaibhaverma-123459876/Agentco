# AgentCo V2 — Architecture Decision Log

## ADR-001: sim_support_count excluded from promotion gate

**Date:** 2026-06-16
**Status:** Accepted

**Context:** The Reality/Simulation Firewall needed a clear rule for when simulation volume
could contribute to belief promotion. Early designs considered a hybrid gate
(simulation threshold + reality predictions).

**Decision:** `sim_support_count` is intentionally excluded from the promotion gate.
The only path to `reality_validated` is ≥3 pre-registered, non-post-hoc predictions
resolved TRUE via external ground truth. Simulation count is stored for transparency only.

**Consequences:** Simulation cannot "sneak in" via high volume. The seeded-false-belief
acceptance test (F-07) demonstrates this property holds.

---

## ADR-002: Mechanical downgrade propagation, not soft warnings

**Date:** 2026-06-16
**Status:** Accepted

**Context:** When a trust score degrades (e.g., ECE > 0.10), downstream consumers
needed to know. Options: (1) warn and let consumers decide, (2) automatically reduce
the trusted_confidence they read.

**Decision:** Mechanical downgrade propagation via callbacks. When TrustController
detects ECE > 0.10 or a forced downgrade, it fires all registered callbacks immediately.
Downstream consumers always read the latest multiplier — they cannot use stale trust.

**Consequences:** Tightly coupled but ensures no consumer can accidentally use
an invalidated trust score by reading a cached value.

---

## ADR-003: post_hoc excluded from ALL calibration math

**Date:** 2026-06-16
**Status:** Accepted

**Context:** Post-hoc prediction registration (claiming you predicted something after
you could already know the answer) is the primary calibration gaming vector.

**Decision:** The DB schema includes `post_hoc BOOLEAN NOT NULL DEFAULT false`.
PredictionLedger sets `post_hoc=True` if `earliest_knowable_at < now()` at registration time.
Resolution Service and ScoringModule both skip post_hoc records entirely.

**Consequences:** Agents cannot inflate their calibration scores by registering
known outcomes as predictions.

---

## ADR-004: No timeout auto-approve in EscalationGate

**Date:** 2026-06-16
**Status:** Accepted

**Context:** The spec's invariant #6: "Human-approval gates block execution (no auto-approve on timeout)."
A timeout auto-approve would create a DoS-style attack surface
(flood the approval queue → everything auto-approves).

**Decision:** `HumanApprovalRequired` is raised and the agent must halt.
There is no polling loop, no retry with backoff, no fallback execution path.
The action does not proceed until a human explicitly calls `approve_action()`.

**Consequences:** System may appear "stuck" awaiting approval for critical actions.
This is the intended behavior — it is the governance model.

---

## ADR-005: BaseAgentV2 uses trusted_confidence(), never stated

**Date:** 2026-06-16
**Status:** Accepted

**Context:** The spec's invariant #5: decisions must run on trusted confidence, not stated confidence.
Stated confidence is what an agent claims; trusted confidence is what the track record justifies.

**Decision:** `ConfidenceV2.get_trusted()` is called on every action in `execute_action()`.
Agents cannot bypass this — they pass an `AgentActionV2` object with `stated_confidence`
and the framework converts it to trusted via TrustController. No agent receives
its stated confidence back without the trust multiplier applied.

**Consequences:** New agents with no track record receive `trusted = stated * 0.5`
(conservative 50% discount). They must earn calibration through resolved predictions.

---

## ADR-006: Learning Loop proposals require human approval before memory writes

**Date:** 2026-06-16
**Status:** Accepted

**Context:** The learning loop produces TrainingProposals. The question was whether
to apply approved changes immediately or gate on an additional human review step.

**Decision:** `MemoryAgent.run()` checks `human_approved=True` before writing.
`LearningLoop.apply_approved_proposal()` is the only public write path and requires
explicit `approved_by` parameter. Unapproved proposals cannot update memory.

**Consequences:** Learning is slower (each 6-hour cycle requires human review)
but the system cannot modify its own beliefs without oversight.
