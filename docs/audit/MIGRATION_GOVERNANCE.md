# Migration Naming/Ordering Governance (AUD-006)

## Finding

`backend/src/db/migrate.ts` applies every `*.sql` file in `backend/src/db/migrations/`
in plain lexical filename order (`fs.readdirSync(dir).filter(f => f.endsWith('.sql')).sort()`).
There is no other ordering signal — no dependency graph, no explicit "runs after"
declaration. Two migration files sharing the same numeric sequence prefix therefore
have their relative execution order decided by alphabetical comparison of the rest
of the filename, which is an accident of what each file happened to be named, not a
designed sequence. Nothing validated this before AUD-006: a contributor could add a
migration reusing an already-used number, or a non-conforming filename, and nothing
would catch it before it reached a shared database.

At the time of this remediation, the repository already contained five such
collisions and one non-conforming filename — evidence that this has actually
happened repeatedly, most recently from two remediation campaigns
(`audit/remediation-02-authenticated-principal-boundaries` and
`audit/remediation-08-governed-capability-runtime`) developing in parallel and
independently picking migration number `140`.

## Investigation

Each duplicate-numbered pair and the non-conforming filename were read in full and
checked for real cross-file references (shared table, column, type, function, or
role names in either direction) before being grandfathered as pre-existing,
already-applied, low-risk exceptions. None had any.

| Number | Files | Real dependency found | Risk |
|---|---|---|---|
| 051 | `051_fix_fk_constraints.sql`, `051_team_activations.sql` | No — FK/type cleanup on `autonomy_evidence`/`autonomy_claims`/`autonomy_searches`/`autonomy_memory` vs. a brand-new `autonomy_team_activations` table. Zero shared identifiers either direction. | none |
| 058 | `058_adaptive_strategy.sql`, `058_bounded_learning.sql` | No — `adaptive_strategies` schema module vs. `autonomy_routed_claims`/`autonomy_audit_events`/`autonomy_source_discovery_runs`. Bounded-learning's one external FK (`autonomy_claims`) is satisfied by migration 050, unrelated to its sibling. | none |
| 059 | `059_calibration_framework.sql`, `059_governance_reputation_integration.sql` | No — `autonomy_*` calibration/trustworthiness tables vs. `governance_reputation_*` voting/decision/audit tables. No FK, type, or role overlap. | none |
| 129 | `129_civilization_kernel.sql`, `129_longitudinal_mission_evidence.sql` | No — the civilization root aggregate (references only pre-existing `actors`/`event_log`) vs. the longitudinal evaluation-campaign schema (fully self-referential FKs). Zero mentions of `civilization` in the longitudinal file or `longitudinal` in the kernel file. | none |
| 140 | `140_civilization_os.sql`, `140_governed_capability_runtime.sql` | No — civilization-OS tick/status tracking (references pre-existing `civilizations`/`actors`/`event_log`) vs. the capability-runtime audit trail (fully self-referential FKs on `capability_attempts`). Zero cross-references either direction. | none |

`052b_institutions.sql`: a letter suffix inserted after `052_specialist_http_endpoint.sql`
and `053_work_assignment_schema.sql` were already committed, to slot a later migration
in between without renumbering everything after it (`052b_` sorts correctly between
`052_` and `053_` under plain string sort). This is a one-off anomaly, not a second
sanctioned convention — the repository already solved the same "insert between existing
migrations" problem a different, inconsistent way for the 051 pair (reusing a number,
disambiguated by name only, no letter suffix). Grandfathered as a named exception;
**not** extended into an accepted pattern for future migrations.

**Conclusion: no evidence of a live ordering bug from any of these six cases** — but the
absence of a bug so far is not a structural guarantee, and the fact that this has
already happened six times with zero prevention is the actual finding. The fix is
forward-looking: stop new collisions and non-conforming names from landing at all.

## Policy going forward

Enforced by `scripts/verify_migration_naming.py`, wired into `make release-gate` and CI
(`.github/workflows/ci.yml`):

- Every migration filename not in the grandfather lists below must match
  `^\d{3}_[a-z0-9_]+\.sql$` exactly — a 3-digit sequence number, underscore,
  lowercase snake_case description, `.sql` extension. No letter suffixes, no
  uppercase, no other punctuation.
- No two non-grandfathered files may share a sequence number. If your migration's
  intended number is already taken, take the next unused number instead — do not
  add a duplicate.
- The grandfather lists are keyed by **exact filename**, not by number or pattern.
  Renaming or deleting a grandfathered file fails the check (`GRANDFATHERED_FILE_MISSING`)
  rather than silently accepting whatever replaced it.
- Extending a grandfather list is only for verified pre-existing, already-applied
  migrations investigated the same way as the six cases above — never as a way to
  land a new collision.

Migration files are never renamed once committed, even to "fix" a pre-existing
collision: `schema_migrations.filename` is the tracking key in every already-migrated
database, and renaming a file makes an already-applied migration look unapplied there.
The five duplicate pairs and `052b_institutions.sql` stay as they are; this policy
only prevents new ones.
