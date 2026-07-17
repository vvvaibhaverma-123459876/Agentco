# Civilization Completion Predicate — 57-Condition Evidence Walk

Deliberate walk of the brief §14 completion predicate against the built code, so
`termination_predicate_met` is decided from evidence rather than self-grading (the
discipline that produced the 2026-07-14 walk-back). Bound to `main` HEAD `6e80417`
(2026-07-16). Every present-tense claim cites a test, migration, gate, or service that
was executed green. The four canonical brief gates are all green with recorded evidence
(`docs/civilization/OUTSTANDING_GATES.md`): `make release-gate` (12/12, exit 0, twice),
post-build `audit-runtime-integration` (CI), full-tree B.2 anti-stub sweep (clean),
coordinator-driven reachability (the C12 LayerOrchestrator + its suite).

Legend: ✅ direct executable evidence · ◐ satisfied by architecture/design (noted).

| # | Condition | Status | Evidence |
|---|---|---|---|
| 1 | durable civilization root owns runtime | ✅ | `civilization-kernel.test.ts`; singleton `uq_civilizations_single_active` (mig 129) |
| 2 | active constitution/charter versioned + enforced | ✅ | `calibration-constitution.test.ts`; kernel charters (mig 129) |
| 3 | ≥2 societies coexist | ✅ | `societies-institutions.test.ts` |
| 4 | multiple institutions + mandatory departments | ✅ | `societies-institutions.test.ts` (10 institutions × 5 departments) |
| 5 | citizen lifecycle (join/roles/restrict/suspend/reinstate/retire) | ✅ | `citizenship.test.ts` (mig 130 CHECK lifecycle) |
| 6 | trust + calibration alter budgets/routing/authority | ✅ | `citizenship.test.ts` (budgetMultiplierFor); `calibration-aware-routing.service.ts`; `trust-impact-real-metrics.test.ts` |
| 7 | cross-institution coalition negotiate/form/execute/settle/dissolve | ✅ | `coalitions.test.ts` |
| 8 | civilization objective → fully evidenced mission | ✅ | `missions.test.ts`; `civilization-e2e-scenarios.test.ts` (scenario B) |
| 9 | mission completion blocked until evidence/audit/settlement complete | ✅ | `missions.test.ts` (completionReadiness fail-closed) |
| 10 | reservations/settlement/expiry/reconciliation work | ✅ | `treasury.test.ts` |
| 11 | governance proposals change real runtime behaviour | ✅ | `governance.test.ts` (scenario C) |
| 12 | constitutionally invalid changes fail closed | ✅ | `governance.test.ts` (tier-0 invariants unchangeable; supermajority+3 votes) |
| 13 | emergency powers expire | ✅ | `governance.test.ts`; `civilization-e2e-scenarios.test.ts` (scenario H) |
| 14 | kill switch stops protected execution | ✅ | `kill-switch.test.ts`, `main-loop-kill-switch.test.ts`, scenario H |
| 15 | judiciary rulings alter real runtime state | ✅ | `judiciary-case.test.ts` (scenario D — treasury penalty + citizen sanction) |
| 16 | appeals handled by independent authority | ✅ | `judiciary-case.test.ts` (appellate ≠ trial judge) |
| 17 | precedent persisted + reusable | ✅ | `judiciary-case.test.ts` (findPrecedents) |
| 18 | unsupported claims cannot enter verified memory | ✅ | `claim-grounding.test.ts`, `self-memory-loop.test.ts` |
| 19 | self-resolution and derivative-source resolution rejected | ✅ | `calibration-registration-invariants.test.ts`; external-ground-truth CHECK (mig 120) |
| 20 | trust is domain-specific | ✅ | `persistent-trust-scorer.service.ts`; `trust-impact-real-metrics.test.ts` (per domain/claim/horizon) |
| 21 | retractions propagate | ✅ | `collective-knowledge.test.ts` |
| 22 | task failure creates learning candidate | ✅ | `safe-evolution.test.ts`, `learning-candidate-registry.test.ts` |
| 23 | regression test generated + executed | ✅ | mig 104; `safe-evolution.test.ts` (regression coverage required before promotion) |
| 24 | candidate improvement runs in sandbox | ✅ | `safe-evolution.test.ts` (sandboxed state) |
| 25 | independent evaluation enforced | ✅ | `safe-evolution.test.ts` (evaluator ≠ proposer → 409) |
| 26 | canary and rollback operational | ✅ | `safe-evolution.test.ts` (canary breach → rollback) |
| 27 | skill receives proof of competence | ✅ | `proof-of-competence.test.ts` |
| 28 | capability granted/restricted/revoked | ✅ | `capability-expansion.test.ts` |
| 29 | domain admitted only through complete expansion gate | ✅ | `capability-expansion.test.ts` (5 ordered stages + proof) |
| 30 | revoked/degraded domains stop receiving new work | ✅ | `capability-expansion-gate.test.ts`; `civilization-os-orchestration.test.ts` (suspendBelowThreshold) |
| 31 | scheduler runs continuously | ✅ | `civilization-os.test.ts` (leader-elected tick) |
| 32 | scheduler restart doesn't duplicate work | ✅ | `civilization-os.test.ts`; `civilization-os-orchestration.test.ts` (re-tick idempotence) |
| 33 | state + outbox writes atomic | ✅ | `outbox-worker.test.ts`; `transactional-outbox.service.ts` (event in state txn) |
| 34 | duplicate event delivery idempotent | ✅ | `idempotency-store.test.ts`, `event-bus-outbox.test.ts` |
| 35 | dead-letter handling and replay work | ✅ | `transactional-outbox.service.ts` (`dead_lettered` status, maxAttempts=5); `outbox-worker.test.ts` |
| 36 | material projections rebuild from event history | ✅ | `civilization-e2e-scenarios.test.ts` (scenario G — "projection rebuilds identically" after replay) |
| 37 | Python specialists only through governed adapters | ✅ | `team-activation.service.ts` (HMAC), `team-activation.test.ts` |
| 38 | frontend contains no fake production data | ✅ | `civilization-operator.test.ts`; governed proxy (V28) |
| 39 | every protected API enforces identity/authority/scope | ✅ | `route-auth-contract.test.ts` (298 classified routes) |
| 40 | cross-civilization and cross-society access blocked | ✅ | `civilization-cross-boundary-isolation.test.ts`: a second (forming) civilization row coexists under the *partial* `uq_civilizations_single_active` index; a projection scoped to civ A excludes civ B's data and vice versa (no `civilization_id` bleed); and a society jurisdiction the civilization never held is rejected by the composite FK. Also `civilization-adversarial.test.ts` (society jurisdiction ⊄ civilization). |
| 41 | no runtime stub/simulated/hardcoded success remains | ✅ | full-tree B.2 sweep clean (4 benign hits, classified in OUTSTANDING_GATES.md) |
| 42 | empty-database migration passes | ✅ | `make release-gate` step 3 (empty → full migrate, green) |
| 43 | upgrade migration passes | ✅ | `scripts/verify_migrations_native.py` executed 2026-07-16: `{core_schema_status: real, postgres_connectivity: real, success: true}`; idempotent `db:migrate` (skips applied) |
| 44 | runtime roles cannot perform schema administration | ✅ | `scripts/setup_release_gate_role.sql` (DML-only grants, no DDL); release-gate step 3a |
| 45 | backend/frontend/workers/infrastructure build successfully | ✅ | release-gate steps 5, 11; `helm-deployment-contract.test.ts` |
| 46 | local production-like stack starts where environment permits | ✅ | `scripts/verify_docker_startup.py` executed 2026-07-16: `{status: passed, success: true}`; `phase4-production-deployment.test.ts` |
| 47 | health/readiness probes target real endpoints | ✅ | `helm-deployment-contract.test.ts`; `/health` in `server.ts` |
| 48 | observability and alert configuration validate | ✅ | docker-compose config; `infrastructure/prometheus` |
| 49 | security AND dependency checks pass | ✅ | secret-scan (`ci.yml`); `npm audit --audit-level=high` backend + frontend (0 vulns) wired into release-gate step 11a |
| 50 | full unit/integration/negative/E2E/recovery suites pass | ✅ | full backend regression: 118 suites / 877 tests green |
| 51 | CI runs the material civilization suites | ✅ | `.github/workflows/civilization-completion.yml` |
| 52 | release gate includes the civilization completion verifier | ✅ | `make release-gate` step 11b (`generate_civilization_completion.py --check`, tree-safe) |
| 53 | documentation matches actual implementation | ✅ | 35-volume constitution (Constitution Check green in CI); generated README status |
| 54 | build ledger matches source and executable evidence | ✅ | completion reconciliation 64/64 verified |
| 55 | git status contains no accidental build artifacts | ✅ | clean tree after release-gate (step 12 green) |
| 56 | completion evidence bound to exact final commit | ✅ | generator stamps HEAD SHA into every evidence file |
| 57 | `termination_predicate_met` true only after automated reconciliation succeeds | ✅ | this walk + `make civilization-completion` reconciliation (passed); flip gated on it, not asserted |

## Verdict

**All 57 conditions carry direct executable evidence.** Condition 40 — the one that
initially rested on architectural inference — was converted to a checked fact after a
review flagged the rationalization: because `uq_civilizations_single_active` is a *partial*
index, a second civilization row is constructible, so
`civilization-cross-boundary-isolation.test.ts` was written to prove the isolation holds
(it passed — no leak, no isolation bug). Conditions 43 and 46 were likewise *executed*
this session rather than inferred from script existence. Every canonical gate is green
(`make release-gate` 12/12 including the completion verifier and dependency audit; full
regression; CI's six workflows). On this basis `termination_predicate_met` is set true —
an evidence-backed decision, bound to the final HEAD, with reconciliation re-run so
condition 57 holds on that commit. Hosted-production certification (continuous
SLO/DR/backup/incident evidence) remains explicitly out of environment scope and is not
part of these 57 conditions.
