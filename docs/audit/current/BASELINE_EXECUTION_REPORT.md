# Baseline Execution Report

Baseline tag: `audit-baseline-2026-07`
Baseline commit: `b3e6fa44a6075c44062374c0ce9be5edaa23483f`
Branch at capture: `audit/remediation-01-gate-integrity`
Tracked files at capture: `1614`

This baseline was captured before the gate-integrity remediation in this
branch. It records the active false-success and bypass paths found in the
starting tree so later reports do not erase the original defects.

## Tool Versions

| Tool | Result |
|---|---|
| `python3.13 --version` | `Python 3.13.9` |
| `node --version` | `v24.17.0` |
| `npm --version` | `11.13.0` |
| `docker --version` | `Docker version 29.5.3, build d1c06ef` |
| `docker compose version` | `Docker Compose version v5.1.4` |
| `helm version` | `UNVERIFIED_EXTERNAL_DEPENDENCY: helm not installed` |
| `kubectl version --client` | `Client Version: v1.34.1; Kustomize Version: v5.7.1` |
| `psql --version` | `psql (PostgreSQL) 16.14 (Homebrew)` |

## Baseline Findings

| ID | Severity | Finding | Evidence |
|---|---|---|---|
| GATE-001 | S2 | `production-release-gate` printed production-ready status and exited 0 while masking test and smoke failures. | `Makefile:407-449` at baseline |
| GATE-002 | S2 | `autonomy-learner-test` was print-only and did not execute a test runner. | `Makefile:369-373` at baseline |
| GATE-003 | S2 | `autonomy-simulator-test` was print-only and did not execute a test runner. | `Makefile:375-379` at baseline |
| GATE-004 | S2 | `scripts/verify_release_gates.py` used Jest `--forceExit` in an active release-gate verifier. | `scripts/verify_release_gates.py:116-127` at baseline |
| GATE-005 | S3 | Documentation advertised Make targets that were not defined. | `python3.13 scripts/verify_make_targets.py` initially reported 20 missing targets |
| GATE-006 | S3 | Score validation presented a structural estimate without a separate verified-behaviour score field. | `backend/src/cli/score-validation.ts` at baseline |

## Baseline Release-Gate Context

The pre-remediation `make release-gate` had passed on `main` before this branch,
but that did not cover the alternate `production-release-gate`, print-only
learner/simulator targets, advertised target drift, or stale-report semantics.
Those gaps are the scope of remediation batch 01.
