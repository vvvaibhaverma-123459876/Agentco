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
  Experiential Memory Hooks           agents/core/memory/

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
  Commitment Chain (tamper-evident)     reserve/chain/
  Staking + Weighted Decision           reserve/staking/ + reserve/decisions/
  Recursive Resolution (oracles)        reserve/oracle/
  Schema migrations                     reserve/migrations/
  Published public key                  reserve/keys/agentco_reserve_public.pem
```

## Epistemic Reserve — Trust Model (honest statement)

AgentCo **operates** the Reserve. This is an operator-run system, not a
decentralised protocol. There is a single issuer. Full trustlessness (no single
operator) is **future work** and is not claimed.

What IS true and tested as of this version:

### 1. Any score is independently recomputable (no secret, no operator trust)

Any party with read access to the public `prediction_ledger` can run:

```
python3 reserve/tools/recompute_credential.py <agent_id>
```

and obtain the identical score embedded in any stored credential. The scoring
function is published in `reserve/scoring/scoring_function.py` and is a pure,
deterministic function of resolved ledger rows. If the recomputed score
differs from the stored credential, the operator embedded a false score.

**Proven by:** `reserve/tests/test_independent_recomputation.py`

### 2. Credential authorship is publicly verifiable (public key, no secret)

Credentials are signed with Ed25519. The operator holds the private key
(`RESERVE_PRIVATE_KEY` env var, never committed). The public key is published at:

```
reserve/keys/agentco_reserve_public.pem
```

Anyone can verify a credential's authorship using only the public key:

```python
from reserve.credentials.proof_of_calibration import verify_credential
assert verify_credential(cred)   # uses public key from reserve/keys/ — no secret
```

Key rotation: when the private key changes, a new public key file is added
(never deleted), so older credentials remain verifiable with their issuing key.

**Proven by:** `reserve/tests/test_ed25519_signing.py`

### 3. Correctness is verifiable without the signature

The two guarantees above are independent:
- **Authorship** (Ed25519): "AgentCo attests this snapshot was issued by us"
- **Correctness** (recomputation): "the scores are what the ledger rows dictate"

Correctness requires no key at all. If you strip the signature entirely, you
can still verify correctness by recomputing from ledger rows. A credential
whose signature fails but whose scores match the recomputed values means the
credential was re-signed with a different key (key rotation), not that the
scores were rigged.

### 4. The operator cannot rig a score undetected (tamper-evident chain)

All resolved predictions that feed scores are committed to an append-only
hash chain (`prediction_chain_log`). The chain design mirrors
Certificate Transparency:

```
row_hash = SHA-256(prev_hash || prediction_id || agent_id ||
                   probability || resolved_outcome || resolved_at ||
                   domain || horizon_class || consequence)
```

Any third party can recompute the chain head from raw ledger rows and compare
to the published head. Alteration of any committed prediction field changes
every subsequent hash — the divergence is detectable without any secret.

```python
from reserve.chain.commitment_chain import verify_chain, recompute_chain_head
assert verify_chain(db)   # True = chain intact; False = tampering detected
```

**Proven by:** `reserve/tests/test_tamper_evidence.py`

### What is NOT yet true (explicit under-claim)

- **Not decentralised.** A single operator controls the private key and the DB.
  A malicious operator could shut down the system; they cannot silently rig
  scores without detection, but they could refuse to issue credentials.
- **Chain is operator-hosted.** Third parties must have read access to the DB
  or a published snapshot to audit the chain. External log shipping (e.g. to
  a transparency log server) is future work.
- **No on-chain settlement.** Staking and weighted decisions are recorded
  on-DB, not on a public blockchain. Finality depends on operator uptime.
- **Single issuer.** There is no multi-party credential issuance or threshold
  signing. Future work: federated reserve with multiple independent signers.

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

**Experiential memory lifecycle (proven append-only path):**
```
BaseAgentV2.prepare_memory_context(task, domain)
  → MemoryReader.retrieve_relevant()  [best-effort, 500ms budget]
  → MemoryReader.get_agent_track_record_summary()
  → inject concise memory context into act() messages

BaseAgentV2.complete_task_memory(...)
  → MemoryWriter.write_episodic()     [append-only agent_memories row]

BaseAgentV2.remember_prediction_lesson(...)
  → MemoryWriter.write_prediction_lesson()

LearningLoop.extract_lessons_from_recent()
  → MemoryWriter.write_semantic()
  → consolidate/share through superseded_by and shared namespace
```

`agent_memories` rows are immutable once written: summary/content and identity
columns cannot be updated, and deletes are rejected by trigger. Corrections and
consolidations write new rows and link old rows through `superseded_by`.

**Proven by:** `tests/e2e/test_memory_lifecycle.py`

## Epistemic Reserve Data Flows

**Proof-of-Calibration issuance:**
```
score_agent(ledger.list_by_agent(agent_id))
  → ReserveScore per (domain × horizon) cell
  → issue_credential(score, last_contacts)   [Ed25519-signed, non-transferable]
  → persist_credential(cred, db)             [append-only calibration_credentials]
  → commit_prediction(pid, db) per row       [append-only hash chain]
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

---

## LLM Provider Model (Config-Driven)

Every agent tier resolves its provider and model **entirely from environment
variables** — no code change is required to switch providers or models.

### Tier → Agent mapping

| Tier       | Agents                      | Env prefix          |
|------------|-----------------------------|---------------------|
| `frontier` | ceo-agent                   | `LLM_*_FRONTIER`    |
| `standard` | pm-agent, research-agent, … | `LLM_*_STANDARD`    |
| `monitor`  | support-agent               | `LLM_*_MONITOR`     |
| `coder`    | coder-agent                 | `LLM_*_CODER`       |

### Resolution order (per tier T)

```
LLM_PROVIDER_T  →  LLM_PROVIDER       →  "openai"
LLM_BASE_URL_T  →  LLM_BASE_URL       →  provider default
LLM_API_KEY_T   →  LLM_API_KEY        →  "" (fails validation for non-ollama)
LLM_MODEL_T     →  LLM_MODEL_DEFAULT  →  provider tier default
```

### Supported providers

**OpenAI-compatible** (OpenAI SDK with `base_url`): `openai`, `ollama`,
`groq`, `together`, `fireworks`, `openrouter`, `deepseek`, `mistral`,
`anyscale`.

**Native adapter**: `anthropic` — thin wrapper around `anthropic.Anthropic`;
requires `pip install anthropic>=0.40`.

**Unsupported**: `google` — raises `ConfigurationError` at startup.

### Spend guardrail

`SpendGuardrail` is checked **before** every LLM call in `act()`.

- `LLM_MAX_TOKENS_PER_RUN` (default 100 000): token cap per agent run.
- `LLM_RATE_LIMIT_RPM` (default 60): call-rate cap per minute per run.

When exceeded: `escalation.route(reason="spend_cap_exceeded", risk_level="critical")`
fires **first**, then `SpendCapExceeded` is raised. The LLM call is never made.
No silent throttling — the agent stops and escalates.

### Startup validation

`validate_all_tiers()` raises `ConfigurationError` naming the missing variable
and tier if any non-ollama tier has no api_key. Call at process start.

### Smoke test

`scripts/smoke_one_task.py` — verifies config, calibration engine, LLM call,
Postgres audit log, and Kafka event bus in one run. Kafka is optional (dev);
calibration + LLM + DB are required (exit 1 if any fail).
