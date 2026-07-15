# Volume 11 — Trust & Calibration

## 1. Header

| Field | Value |
|---|---|
| Volume | 11 |
| Name | Trust & Calibration |
| Tier | statute |
| Epistemic status | descriptive |
| Doc status | written |
| Related volumes | V9 (Knowledge System), V8 (Missions), V14 (Learning Engine), V15 (Capability Expansion), V33 (Model Governance) |

## 2. Purpose

Trust in AgentCo is **earned by resolved outcomes, never asserted**. This volume defines
how confidence is measured: predictions are pre-registered before their outcome is
knowable, resolved against *independent, external* ground truth, scored with proper
scoring rules (Brier / log score), and only then do those scores move a subject's trust —
per domain, claim type, and time horizon. Trust is the currency Knowledge (V9) spends to
promote memory and that Capability Expansion (V15) requires before granting new powers.
Descriptive tier: every normative sentence cites the enforcing file or test.

The calibration loop:

```text
CLAIM ──► register a falsifiable PREDICTION before the outcome is knowable
             (falsifiable-prediction.service.ts → prediction_ledger)
             DB constraints: resolution_date > created_at; post_hoc consistent
             with earliest_knowable_at; ground truth must be EXTERNAL
                     │
                     ▼
        RESOLVE from independent evidence, under a separate DB role
             (independent-resolver.service.ts; resolution_service role, mig 016)
                     │
                     ▼
        SCORE with proper scoring rules  (Brier, log score) → prediction_ledger
                     │
                     ▼
        TRUST WINDOW per (subject, domain, claim_type, horizon_class)
             (persistent-trust-scorer.service.ts → trust_scores)
             force-downgrade if n_resolved < 5 or brier_mean > 0.25
                     │
                     ▼
        SPENT BY:  memory promotion (V9) · capability grants (V15) · routing
```

## 3. Definitions

- **Falsifiable prediction** — a pre-registered claim about whether independent
  corroboration will exist by a resolution date; instant self-resolution is disallowed
  (`backend/src/services/falsifiable-prediction.service.ts`).
- **Pre-registration** — recording the prediction before its outcome is knowable;
  `post_hoc = (created_at > earliest_knowable_at)` is enforced at the database
  (`backend/src/db/migrations/120_prediction_ledger_registration_invariants.sql`).
- **Independent resolution** — resolving a prediction from external evidence not produced
  by the predicting agent, executed under the dedicated `resolution_service` DB role
  (`backend/src/services/independent-resolver.service.ts`,
  `backend/src/db/migrations/016_resolution_service_role.sql`).
- **Proper scoring** — Brier score and log score stored per resolved prediction
  (`prediction_ledger`; used in `persistent-trust-scorer.service.ts`).
- **ECE** — expected calibration error, computed per subject key
  (`computeEce` in `persistent-trust-scorer.service.ts`).
- **Trust window** — a `trust_scores` row keyed by
  `(subject, domain, claim_type, horizon_class)` carrying `trust_factor`,
  `force_downgrade`, and `downgrade_reason`.
- **Force-downgrade** — a hard trust cap applied when evidence is too thin
  (`n_resolved < 5`) or accuracy too poor (`brier_mean > 0.25`).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V11-INV-001 | A prediction's resolution date must be after its registration, and its post-hoc flag must match whether it was created after the outcome became knowable — enforced at the database. | enforced | `backend/src/db/migrations/120_prediction_ledger_registration_invariants.sql`, `backend/tests/calibration-registration-invariants.test.ts` |
| V11-INV-002 | Ground truth for a resolution must be external — a prediction cannot be resolved from the system's own internal tokens. | enforced | `backend/src/db/migrations/120_prediction_ledger_registration_invariants.sql`, `backend/src/services/independent-resolver.service.ts` |
| V11-INV-003 | Resolution of the write-once prediction columns is firewalled to the dedicated resolution_service database role, not the producing service. | enforced | `backend/src/db/migrations/016_resolution_service_role.sql`, `backend/src/db/migrations/011_prediction_ledger.sql` |
| V11-INV-004 | Trust is computed only from resolved, non-post-hoc predictions using proper scoring rules (Brier / log score). | enforced | `backend/src/services/persistent-trust-scorer.service.ts`, `backend/tests/trust-impact-real-metrics.test.ts` |
| V11-INV-005 | Trust is force-downgraded when the resolved sample is below five or the mean Brier score exceeds 0.25. | enforced | `backend/src/services/persistent-trust-scorer.service.ts`, `backend/tests/trust-impact-real-metrics.test.ts` |
| V11-INV-006 | Trust is scoped per subject, domain, claim type, and time horizon — not a single global scalar. | enforced | `backend/src/services/persistent-trust-scorer.service.ts`, `backend/src/db/migrations/009_trust_scores.sql` |
| V11-INV-007 | A prediction's registered probability is derived from the subject's prior calibration history, not chosen freely at resolution time. | enforced | `backend/src/services/falsifiable-prediction.service.ts`, `backend/tests/falsifiable-calibration-e2e.test.ts` |
| V11-INV-008 | Trust-policy changes are themselves canaried and governed before taking effect (calibration governs its own changes). | planned | — |
| V11-INV-009 | Calibration drift is monitored continuously and raises a governed alert when a subject's ECE degrades beyond threshold. | planned | — |

## 5. Interfaces

- **Prediction registration** — `falsifiable-prediction.service.ts`
  (`registerForClaim`, `deriveProbability` from `trust_scores` history).
- **Resolution** — `independent-resolver.service.ts` (`attemptResolution`,
  `resolveDuePredictions`) reads candidate external evidence and writes resolution under
  the `resolution_service` role; `grounded-resolver.service.ts` for grounded checks.
- **Trust scoring** — `persistent-trust-scorer.service.ts` (`computeForPrediction`)
  aggregates the ledger and writes a `trust_scores` window, emitting
  `accurate_prediction` / `failed_prediction` events.
- **Consumers** — memory promotion (`memory-promotion-pipeline.service.ts`, V9),
  capability grants (V15), and calibration-aware routing
  (`calibration-aware-routing.service.ts`).
- **Governance of calibration** — `trust-policy.service.ts`,
  `trust-policy-canary.service.ts`, `calibration-change-governance.service.ts`,
  `calibration-drift-monitor.service.ts`.

## 6. State

- **Predictions:** `prediction_ledger` (migration `011`; registration invariants `120`;
  hardness/reserve compatibility `094`/`095`).
- **Trust:** `trust_scores` (migration `009`), `trust_reputation_ledger` (`031`),
  `trust_impact_assessment` (`030`).
- **Calibration policy:** `trust_policy_versions` (`028`), `calibration_change_requests`
  (`029`), `calibration_framework` (`059`), `calibration_drift_monitor` (`032`).
- **Resolution firewall:** `resolution_service` role (migration `016`; grant repair
  `093`).
- **Reserve:** `reserve/` (Python) holds signing/proof-of-calibration material consumed
  at credentialing time.

## 7. Failure modes and responses

- **Grading your own homework** — blocked three ways: the external-ground-truth CHECK
  constraint (V11-INV-002), the separate `resolution_service` role that owns the
  write-once resolution columns (V11-INV-003), and the resolver's requirement of
  independent evidence (`independent-resolver.service.ts`).
- **Backdating a prediction** — the `post_hoc`/`earliest_knowable_at` consistency
  constraint makes a claim registered after the outcome was knowable record itself as
  post-hoc, and post-hoc predictions do not feed trust (V11-INV-001, V11-INV-004).
- **Thin-sample overconfidence** — force-downgrade caps trust below five resolved
  samples or above 0.25 mean Brier (V11-INV-005), so a lucky streak cannot mint trust.
- **Global-reputation laundering** — trust is keyed per domain/claim-type/horizon
  (V11-INV-006), so competence in one area does not transfer unearned to another.
- **Silent calibration decay** — a drift monitor exists
  (`calibration-drift-monitor.service.ts`, migration `032`) but the governed-alert
  obligation is not yet an enforced invariant (V11-INV-009 planned; open question 2).

## 8. Verification obligations

Existing and green today: `backend/tests/calibration-registration-invariants.test.ts`,
`backend/tests/falsifiable-calibration-e2e.test.ts`, `backend/tests/grounded-resolver.test.ts`,
`backend/tests/trust-impact-real-metrics.test.ts`,
`backend/tests/calibration-driven-planning.test.ts`,
`backend/tests/phase5-calibration-groundwork.test.ts`.

Must exist before the planned invariants flip: a test proving trust-policy changes are
canaried and governed before activation (V11-INV-008), and a drift-monitor test proving
a governed alert fires on ECE degradation (V11-INV-009).

## 9. Implementation mapping

- `backend/src/services/falsifiable-prediction.service.ts` — registration,
  probability derivation from history.
- `backend/src/services/independent-resolver.service.ts`,
  `backend/src/services/grounded-resolver.service.ts` — independent resolution.
- `backend/src/services/persistent-trust-scorer.service.ts` — Brier/log aggregation,
  ECE, force-downgrade, `trust_scores` window.
- `backend/src/services/trust-policy.service.ts`,
  `backend/src/services/trust-policy-canary.service.ts`,
  `backend/src/services/trust-reputation.service.ts`,
  `backend/src/services/trust-impact-assessment.service.ts` — policy and reputation.
- `backend/src/services/calibration-aware-routing.service.ts`,
  `backend/src/services/calibration-drift-monitor.service.ts`,
  `backend/src/services/dynamic-calibration.service.ts` — routing and drift.
- Migrations: `009`, `011`, `016`, `028`–`032`, `059`, `093`–`095`, `120`.
- `reserve/` — proof-of-calibration credential material.

## 10. Open questions

1. **Two overlapping trust services.** `persistent-trust-scorer.service.ts` (the
   ledger-backed window scorer) and the older `trust-scoring.service.ts` /
   `trust-scoring` path coexist; which is canonical for new consumers should be frozen
   (a Volume 2 canonical-runtime concern) so routing and grants read one source.
2. **Drift monitoring is not yet a governed alert.** `calibration-drift-monitor.service.ts`
   computes drift, but nothing obliges a governed response when ECE degrades
   (V11-INV-009 planned).
3. **Trust-policy self-governance is partial.** Canary and change-governance services
   exist (`trust-policy-canary`, `calibration-change-governance`) but no invariant yet
   proves a policy change cannot take effect un-canaried (V11-INV-008).
4. **Horizon-class taxonomy is implicit.** `horizon_class` keys trust windows but its
   allowed values are not centrally declared; a registry would prevent silent
   fragmentation of trust keys.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 5) | Bind the pre-registration, independent-resolution, proper-scoring, and per-key trust machinery into one citable calibration loop, since Knowledge (V9), Missions (V8), and Capability Expansion (V15) all spend the trust it produces. |
