# Conditions 16 & 25 — Evidence Map (AUD-004 remediation, supersedes the corresponding rows in COMPLETION_PREDICATE_WALK.md)

`COMPLETION_PREDICATE_WALK.md` rows 16 and 25 (bound to `main` HEAD `6e80417`, 2026-07-16) cite
label-inequality test evidence only:

```
| 16 | appeals handled by independent authority | ✅ | judiciary-case.test.ts (appellate ≠ trial judge) |
| 25 | independent evaluation enforced           | ✅ | safe-evolution.test.ts (evaluator ≠ proposer → 409) |
```

This is exactly the evidence class AUD-004 found insufficient: a single credential holder can
satisfy string inequality between two caller-chosen actor_id values. Those rows are **superseded
by this document** for any commit on or after the AUD-004 remediation branch
(`audit/remediation-02-authenticated-principal-boundaries`). The historical walk's other 55
rows are untouched — this document does not rewrite audit history, it documents what changed.

## Machine-verifier truth vs. independent-substantive truth (kept separate, never collapsed)

```text
Repository verifier result (generate_civilization_completion.py --check): see reconciliation_passed
  -> requires scripts/verify_aud004_conditions_16_25.py to report locally_verified=True for BOTH
     conditions (structural + behavioral, credential-bound, DB-backed, tests actually executed).
termination_predicate_met (CIVILIZATION_BUILD_LEDGER.yaml): UNCHANGED by this remediation --
  still read verbatim from the ledger; this document does not flip it.
Independent substantive completion for conditions 16/25: PENDING INDEPENDENT RE-AUDIT.
  A True result from the local verifier is NOT that determination. It is evidence FOR an
  independent auditor to examine, not a substitute for their examination.
```

## Condition 16 — appeals handled by an independent authority

| Requirement | Evidence | Verified by |
|---|---|---|
| Complainant identity is credential-bound | `judiciary-case.routes.ts` case-open route: `complainant_actor_id: req.principal!.actorId` (never a body field) | `scripts/verify_aud004_conditions_16_25.py` (structural) |
| Original decision-maker identity is credential-bound | `judiciary-case.routes.ts` ruling route: `ruling_actor_id: req.principal!.actorId` | same |
| Appeal authority identity is credential-bound | `judiciary-case.routes.ts` appeal-ruling route: `appellate_actor_id: req.principal!.actorId`, gated by `requirePrincipal('judiciary.appeal.decide')` | same |
| Appeal authority ≠ complainant (enforced, not just tested) | Migration `142_aud004_independence_backstops.sql`, `judiciary_appellate_independence_guard` trigger: `BEFORE INSERT ON judiciary_rulings`, `RAISE EXCEPTION` if `NEW.ruling_actor_id = complainant_actor_id` on an appellate ruling | same (structural: IF-condition immediately enclosing a real RAISE EXCEPTION, not just co-located text — see Verifier Hardening below) |
| Appeal authority ≠ original decision-maker (trial judge) | Same trigger, second branch: `RAISE EXCEPTION` if `NEW.ruling_actor_id = trial_judge` | same |
| Caller-supplied labels cannot alter the comparison | Route never reads `appellate_actor_id`/`complainant_actor_id` from `req.body` for these slots (grep-verified: the destructured body validation excludes them) | same + `aud004-conditions-16-25.test.ts` ("body evaluator ignored" pattern applied to judiciary) |
| Root/admin relabeling cannot satisfy independence | The DB trigger contains no `actor_type` branch — a `service`-type actor is bound by the exact same comparison as a `human`-type one | `aud004-m5-machine-principals.test.ts` |
| Direct-SQL bypass is rejected | Migration-142 trigger runs `BEFORE INSERT` regardless of writer | `aud004-conditions-16-25.test.ts` ("cond 16 DB backstop: DIRECT-SQL appellate ruling ... rejected") |
| Runtime route AND alternate paths enforce the rule | HTTP route gated; `ruleOnAppeal` has no caller outside the route + tests (alternate-writer scan) | `verify_aud004_conditions_16_25.py` |
| Negative/adversarial tests are reachable and passing | `aud004-conditions-16-25.test.ts`, `aud004-m5-machine-principals.test.ts`, `principal-boundary.test.ts` | executed by `--run-tests`, not just checked for existence |

## Condition 25 — independent evaluation enforced

| Requirement | Evidence |
|---|---|
| Proposer identity is credential-bound | `createCandidate` route: `proposer_actor_id: req.principal!.actorId` |
| Evaluator identity is credential-bound | `/evaluate` route: `evaluator_actor_id: req.principal!.actorId`, gated by `requirePrincipal('evolution.evaluate')` |
| Approver identity is credential-bound (where separate) | `/promote` route: `actor_id: req.principal!.actorId`, gated by `requirePrincipal('evolution.approve')` |
| Proposer cannot evaluate their own work (enforced, not just tested) | Migration 142 `civ_evaluation_independence_guard`: `BEFORE INSERT ON civ_evaluations`, `RAISE EXCEPTION` if `evaluator_actor_id = candidate.proposer_actor_id` |
| Arbitrary actor strings cannot satisfy separation | Comparison is against the DB-resident `civ_learning_candidates.proposer_actor_id`, not a caller-supplied string |
| Root/admin relabeling cannot satisfy independence | No `actor_type` branch in the trigger; verified identical treatment of `service` vs `human` actors |
| Alternate worker/event/service paths enforce the same rule | `retireMonitoredCandidates` (a genuinely autonomous path) only calls `safeEvolution.retain`, never `.evaluate` — the evaluation gate has exactly one caller (the HTTP route) |
| Direct-SQL bypass is rejected | Verified directly against `civ_evaluations` |
| Negative tests reachable and passing | Same three test files, executed |

## Verifier hardening — proven adversarially, not just written

`scripts/verify_aud004_conditions_16_25.py` was itself tested via **deliberate control-removal**
during development (kept as a documented methodology, not just a claim):

1. A first version of the DB-backstop check (string co-occurrence in a 2000-char window) was
   proven to give a **false PASS** when one `RAISE EXCEPTION` branch was replaced with `NULL`
   — caught by removing the control and observing the verifier didn't notice.
2. A second version (character-distance from first mention) also gave a **false FAIL** on the
   clean, correct code — because the first mention of e.g. `complainant` is its `DECLARE`, not
   its `IF` use.
3. A third version (forward `IF...THEN...END IF` block regex) mis-parsed **nested** IF blocks —
   the outer wrapping `IF NEW.is_appellate = true THEN` swallowed the inner blocks' spans.
4. The final version anchors on each `RAISE EXCEPTION` (the rarer, more distinctive token) and
   walks backward to its nearest enclosing `IF...THEN`, which is robust to nesting. Verified
   against all three failure modes above (each guard branch broken independently → verifier
   correctly flags only the broken one; both branches intact → verifier passes; the sibling
   condition's guard is provably unaffected by breaking the other).

This is the concrete meaning of "the hardened verifier's value is that it FAILS, not that it
passes" — it was exercised against known-broken states before being trusted against the real,
correct code.

## What this document does NOT claim

- It does not claim conditions 16/25 are independently, substantively SATISFIED. That is the
  independent re-audit's determination, against a fresh clone at the post-remediation commit.
- It does not claim the machine-checkable evidence above is exhaustive of everything an
  independent auditor might examine (e.g. organizational/institutional independence beyond
  actor-id inequality, which the brief may require in some interpretations, is not modeled).
- It does not flip `termination_predicate_met` or any other ledger-recorded machine flag.
