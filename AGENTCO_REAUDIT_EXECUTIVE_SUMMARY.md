# AgentCo Re-Audit Executive Summary — 2026-07-07

## Verdict

AgentCo improved materially after Phases 1-6.5, but it is still not production-ready. The re-audit verdict is **PARTIAL REMEDIATION VERIFIED**: route auth, V1 governance fail-closed behavior, V1 retirement, Python locking, staging secret requirements, and decision-log chain compatibility are demonstrably better. The clean-clone default Python suite still fails, generated artifacts still dirty the tree, and hosted production evidence is still absent.

## Classification

Current classification: **local production-posture research/runtime system, not hosted-production ready**.

Scores changed from the 2026-07-06 baseline:

| dimension | old | new |
|---|---:|---:|
| Overall | 5.7 | 6.2 |
| Production | 4.2 | 4.8 |
| Security | 4.8 | 6.1 |
| Architecture | 5.5 | 6.3 |
| Testing | 6.0 | 6.0 |
| Documentation | 4.5 | 5.4 |
| Deployment | 3.8 | 4.6 |

## What Changed In 30 Days

The repository moved from broad capability drift and unauthenticated surface area toward a much more honest local runtime: sensitive routes now default protected, V1 high/critical actions no longer execute without governance infrastructure, dead V1 department agents are archived, Python dependencies are locked, staging compose fails loudly when secrets are absent, and cross-language decision-log chain verification is tested. The remaining gap is credibility at the release boundary: a fresh clone still cannot run the default Python suite cleanly, some generated artifacts are still checked-in/stateful, and no evidence shows the system operating safely in a real hosted environment.

## Top 10 Risks

1. Clean-clone `python3.13 -m pytest -q` fails with 5 failures and 1 error.
2. Verification commands dirty README, eval acceptance files, and reports.
3. No hosted staging/production operations evidence.
4. Raw backend error messages are still returned to clients.
5. Jest still uses `forceExit` because open handles remain.
6. Decision-log legacy serialization compatibility is advisory, not version-bound in the row.
7. V2 audit fail-closed path has a committed-row/lost-ACK ambiguity.
8. LIVE V1 specialists remain, even though Phase 6.5 found no severity landmine.
9. Secret scanning excludes docs, reports, markdown, and tests.
10. Local/dev credential defaults remain outside staging compose.

## Top 10 Missing

1. A green, side-effect-free clean-clone default test run.
2. Browser-executed frontend auth/dashboard smoke.
3. Hosted staging deployment proof.
4. Hosted backup/restore and rollback proof.
5. Explicit decision-log serialization version field bound into the hash.
6. Idempotent audit write/ACK protocol.
7. Removal of backend Jest open handles.
8. V2 migration for the 18 LIVE autonomy specialist agents.
9. Sanitized production error responses.
10. CI check that README/status generation is current without rewriting files.

## Top 10 Fastest Fixes

1. Mark Kafka-dependent Python tests as opt-in live-service tests unless Kafka is configured.
2. Fix invalid UUID/path handling to return 400 without raw database errors.
3. Make `make status` check-only in CI or commit regenerated README status.
4. Add a no-diff assertion after verification commands.
5. Remove or quarantine generated eval/report outputs from default tests.
6. Add route-auth cases for HEAD, trailing slash, and case variants.
7. Add explicit `serialization_version` for new decision-log rows.
8. Isolate the remaining Jest open handle and remove `forceExit`.
9. Narrow CI secret-scan exclusions or add a second scanner for docs/reports.
10. Convert remaining `/Users/Zet/Agentco` scripts to repo-relative paths.

## Next Milestone

Next milestone: **Release Credibility Gate**. It should pass from a clean clone with no generated diffs: Python default suite, backend install/build/Jest without force exit, frontend install/typecheck/browser smoke, route-auth contract, decision-log chain verification, and `make status` in check mode.
