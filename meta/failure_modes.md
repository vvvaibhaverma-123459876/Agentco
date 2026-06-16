# AgentCo V2 — Known Failure Modes & Mitigations

## F-01: Calibration Gaming (Goodhart's Law)

**Risk:** An agent pre-registers predictions it knows will resolve TRUE,
inflating its trust score without genuine uncertainty.

**Detection:** Post-hoc detector flags `earliest_knowable_at < registered_at`.
Resolution Service rejects internal ground truth sources.
Self-Audit Module tracks prediction resolution patterns.

**Mitigation (engineered):**
- `DISQUALIFIED_SOURCES` list in PredictionLedger (hardcoded, 7 entries)
- Pre-registration columns immutable at DB layer
- `post_hoc=True` predictions excluded from ALL calibration math
- External ground truth required for resolution

**Residual risk:** An agent with access to external sources could still select
only easy-to-predict events. Monitor via Surprise Register — low surprise rate
at high stated confidence is a signal of cherry-picking.

---

## F-02: Simulation Bleed (Firewall Bypass)

**Risk:** Simulation volume gradually shifts a belief toward
`reality_validated` without real-world evidence.

**Detection:** `test_simulation_support_CANNOT_reach_reality_validated` (1000 sim supports, 26 tests)
Firewall DB trigger blocks `reality_validated` updates from non-`resolution_service` roles.

**Mitigation (engineered):**
- `sim_support_count` is **intentionally excluded** from the promotion gate
- DB trigger `enforce_reality_firewall()` raises exception on bypass attempt
- `promote_to_reality_validated()` has 5 explicit gates, all must pass

**Residual risk:** Database admin-level access could bypass the trigger.
Mitigation: DB role separation (`resolution_service` role is audited separately).

---

## F-03: Trust Score Stagnation

**Risk:** An agent with a high early trust score stops being recalibrated
because it stops making predictions.

**Detection:** `n_resolved` field in TrustScore. Decay Tracker runs hourly.

**Mitigation (engineered):**
- `MIN_SAMPLES_FOR_TRUST = 5` — below this, trust defaults to 0.5
- DecayTracker demotes `reality_validated` beliefs without fresh reality contact
- Governor Dashboard shows agents with low n_resolved

**Residual risk:** An agent could make many predictions but never have them resolved
(resolution date far in the future). Monitor via Prediction Ledger pending count.

---

## F-04: Surprise Register Saturation

**Risk:** Too many surprise events overwhelm the investigation queue, causing
genuine surprises to be missed.

**Detection:** `list_uninvestigated()` length. Governor Dashboard panel 4.

**Mitigation (engineered):**
- Surprise events trigger Trust Controller downgrade immediately (before investigation)
- `surprise_score` ranks by severity — governors can triage by score
- SurpriseRegister stores full event context for async investigation

**Residual risk:** The surprise score formula (`p^2` for misses) could rank
moderate-probability events lower than critical-domain events deserve.
Domain-weighted surprise scoring is a future improvement.

---

## F-05: Learning Loop Proposal Accumulation

**Risk:** Human governors are overwhelmed with TrainingProposals and
rubber-stamp approvals without genuine review.

**Detection:** Cycle log tracks `approved_by` and time between submission and approval.
If approval latency is <60 seconds consistently, flag for review.

**Mitigation (engineered):**
- Proposals require explicit approval (no auto-approve)
- Governor Dashboard shows proposal content with backtest evidence
- Proposals include `backtest_note` explicitly stating simulation uncertainty

**Residual risk:** Governor fatigue is a social/organizational risk, not an
engineering one. Mitigation: escalation training and minimum review-time SLAs.

---

## F-06: Config-Agent Prompt Injection

**Risk:** A malicious input causes Config-Agent to treat a user-provided
string as a system command and modify agent prompts.

**Detection:** `EVERY_ACTION_REQUIRES_HUMAN_APPROVAL = True` means no prompt
modification runs without human approval token. Audit log captures full payload.

**Mitigation (engineered):**
- Every action produces an override request — human must explicitly approve
- Self-modification blocked by `target_agent_id == AGENT_ID` check in code
- ROLLOUT_STAGES = [0.05, 0.25, 1.00] — changes are staged with monitoring

**Residual risk:** If a human governor is itself social-engineered, the staged
rollout provides a detection window at 5% before 100% rollout.

---

## F-07: Seeded False Belief Acceptance

**Risk (spec §7):** A false belief enters the system, is supported by
simulations, and graduates to `reality_validated` — causing the system to
act on false information at full confidence.

**Detection:** This is THE primary architecture safety test.
`TestSeededFalseBeliefAcceptance::test_seeded_false_belief_caught_by_reality`

**Mitigation (proven by test):**
1. Inject false belief → enters as `provisional`
2. 20 simulation supports → advances only to `simulation_supported`
3. 3 predictions at p=0.88 resolve FALSE → Surprise fires, Trust downgrades
4. Promotion gate checks: all must resolve TRUE → gate returns False
5. Belief quarantined as `simulation_supported`, never reaches `reality_validated`

**Residual risk:** A sufficiently long chain of TRUE-resolving predictions on
a domain adjacent to the false belief could inflate trust in that domain.
Mitigation: domain-specific trust scores (not global).

---

## Anti-Pattern Checklist (engineered against)

| Anti-pattern | Where blocked |
|---|---|
| Self-validating reasoning | Resolution Service rejects internal ground truth sources |
| Stated confidence as decision input | ConfidenceV2 always calls trusted_confidence() |
| Auto-approve on timeout | EscalationGate: no timeout path exists |
| Simulation volume promoting beliefs | Firewall: sim_support_count excluded from gate |
| Post-hoc prediction scoring | PredictionLedger: post_hoc=True excluded from calibration |
| Config-Agent self-modification | CoderAgent: target_agent_id check hardcoded |
| Memory writes without approval | MemoryAgent: human_approved=False → blocked |
| Synthesis output as ground truth | TheoryEngine: all outputs provisional, firewalled |
