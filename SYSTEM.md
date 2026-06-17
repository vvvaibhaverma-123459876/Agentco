# AgentCo V2 — System Architecture

## Core Invariants (hardcoded, not in prompts)

1. **Only reality promotes.** Beliefs reach `reality_validated` ONLY via externally-scored, pre-registered, out-of-sample predictions resolved by an independent ground truth source. No simulation volume crosses this line.
2. **Immutable prediction ledger.** Pre-registration columns are write-once at the DB layer (UPDATE trigger + role restriction). Resolution columns may only be written by the `resolution_service` DB role, once.
3. **Pre-registration enforced.** Claims must be registered BEFORE the outcome is knowable. Post-hoc detection flags and excludes claims where `earliest_knowable_at < registered_at`.
4. **Reality/Simulation Firewall is a hard gate.** `sim_support_count` is intentionally excluded from the promotion gate. 10,000 simulation confirmations cannot promote a belief to `reality_validated`.
5. **Decisions run on trusted confidence, not stated confidence.** `TrustController.trusted_confidence()` is the only function that may produce a confidence value used in a decision. Stated confidence is an input, not an output.
6. **Human-approval gates block execution.** No auto-approve on timeout. `HumanApprovalRequired` must be resolved by a human. The action does not proceed otherwise.
7. **All outputs carry confidence scores.** Every event envelope must include `confidence_score`, `risk_level`, `producer_prompt_version`, and a valid HMAC signature. The event bus rejects envelopes missing any of these.
8. **100% immutable audit log.** `decision_log` is append-only, enforced by `BEFORE UPDATE`/`BEFORE DELETE` triggers that raise unconditionally (migration `014` — `REVOKE` alone is insufficient because the table owner/superuser bypasses it). The audit-log service chain-hashes entries with SHA-256 over a canonical row form; `verifyChainIntegrity()` re-derives the chain from the DB and detects any tampering. Proven by `backend/tests/integration/audit-log.test.ts`.
9. **Config-Agent cannot modify its own prompt.** `EVERY_ACTION_REQUIRES_HUMAN_APPROVAL = True` is hardcoded.
10. **Ground truth must originate outside the reasoning system.** Internal sources (`self`, `internal`, `simulation`, `agent`, `agentco_system`, `twin`, `sandbox`) are disqualified from backing calibration scores.

## Layer Structure

```
Layer 0 — Calibration Engine          calibration/
  Prediction Ledger                   calibration/ledger/
  Resolution Service                  calibration/resolution/
  Scoring Module (Brier, log, ECE)    calibration/scoring/
  Trust Controller                    calibration/trust/
  Reality/Simulation Firewall         calibration/firewall/
  Surprise Register                   calibration/surprise/
  Decay Tracker                       calibration/decay/
  Self-Audit Module                   calibration/self_audit/

Layer 1 — V2 Runtime                  runtime/
  BaseAgentV2                         runtime/base_agent/
  ConfidenceV2                        runtime/confidence/
  EscalationGate                      runtime/escalation/

Layer 2 — Continuous Learning Loop    learning/
  Intelligence-Agent (6h cycle)
  Scenario-Agent
  Trainer-Agent
  Memory-Agent

Layer 3 — Cross-Domain Synthesis      synthesis/
  Synthesis-Agent
  Principle Library
  Theory Engine

Layer 4 — Digital Twin + Governor UI  simulation/ + dashboard/

Layer 5 — Epistemic Reserve             reserve/
  Scoring Function (deterministic)      reserve/scoring/
  Proof-of-Calibration Credential       reserve/credentials/
  Staking + Weighted Decision           reserve/staking/ + reserve/decisions/
  Recursive Resolution (oracles)        reserve/oracle/
  Schema migrations                     reserve/migrations/
```

## Key Data Flows

**Prediction lifecycle:**
```
Agent.pre_register_claim()
  → PredictionLedger.pre_register()   [immutable write, post-hoc check]
  → [time passes, outcome becomes knowable]
  → ResolutionService.resolve()       [time gate, write-once, external source check]
  → ScoringModule.brier_score()       [stored on ledger row]
  → SurpriseRegister.check()          [fires if p≥0.80 resolved FALSE]
  → TrustController.ingest_resolution() [updates trusted_multiplier]
```

**Belief promotion (the only safe path to reality_validated):**
```
RealitySimulationFirewall.promote_to_reality_validated(belief_id, prediction_ids)
  Gate 1: ≥3 prediction_ids provided
  Gate 2: all predictions are resolved
  Gate 3: all outcomes are TRUE
  Gate 4: all ground_truth_sources are external (not in DISQUALIFIED_SOURCES)
  Gate 5: none are post_hoc
  → status = "reality_validated"
```

**Action execution (V2 contract):**
```
BaseAgentV2.execute_action(action)
  → ConfidenceV2.get_trusted()        [never use stated directly]
  → EscalationGate.check_and_gate()  [block if risk≥high or trusted_conf<0.50]
  → emit signed envelope with producer_prompt_version
  → write immutable audit entry
```

## Epistemic Reserve Data Flows

**Proof-of-Calibration issuance:**
```
score_agent(ledger.list_by_agent(agent_id))
  → ReserveScore per (domain × horizon) cell
  → issue_credential(score, last_contacts)   [HMAC-signed, non-transferable]
  → persist_credential(cred, db)             [append-only calibration_credentials]
```

**Belief market resolution:**
```
register_question()
  → place_stake(agent, credential, position)  [weight = max(0, exp(log_score) − 0.5)]
  → resolve_question(stakes)                  [weighted majority; sybil_filtered_count auditable]
  → persist_decision(decision, db)
```

**Oracle contradiction chain:**
```
resolve_as_oracle(pred, outcome, credential)  [authority = stake_weight; round=0]
  → [if stronger source contradicts]
  → resolve_as_oracle/mechanical(…, prior_resolution_id)  [round N+1]
  → _mark_contradicted(prior)
  → _record_standing_event(prior.agent, standing_delta = −PENALTY × authority)
  # Mechanical source = bedrock; cannot be contradicted
```

## Acceptance Test (§7 — must always pass)

`calibration/tests/test_ledger_immutability.py::TestSeededFalseBeliefAcceptance::test_seeded_false_belief_caught_by_reality`

Seeds a false belief → 20 simulation supports (status: `simulation_supported`) → registers 3 predictions with p=0.88 → resolves all FALSE via ResolutionService → asserts: surprises fired, trust downgraded, promotion gate returns False, belief quarantined as `simulation_supported`.

Run all Phase 0 tests:
```
python -m pytest calibration/tests/ runtime/tests/ -v
```
