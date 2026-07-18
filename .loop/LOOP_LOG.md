# Loop Log

## Iteration 1 — 2026-07-19

- Branch: `loop/completion`
- Starting HEAD: `b5f8a2993f869f1a1d668dc7ad36245474fa37b8`
- Canonical goal source read: `README.md`
- Delta from prompt DoD: README confirms AgentCo is not certified hosted production and remains partial for durable autonomous improvement/general capability; prompt DoD is stricter and consistent with that current non-complete status.
- Selected item: Genesis V7 real-provider runner evidence quality and authorization binding, covering DoD 3, 4 and 5.
- Claude/Duet: attempted `duet talk ... claude`; unavailable due Claude session limit resetting at `4am (Asia/Calcutta)`.
- Changed:
  - `scripts/run_openai_genesis_v7_baseline.py` now requires `AGENTCO_GENESIS_V7_AUTHORIZATION` to point at a source-bound authorization JSON for provider/model/endpoint identity. The disputed model is no longer hardcoded in the runner.
  - Future case evidence records now include redacted provider response, provider request ID hash, finish reason, parser input hash/redacted parser input, and local audit references.
  - Future clean-clone verification report now recomputes aggregate and case semantic hashes and fails hash-only provider evidence instead of writing a `not_run_*` placeholder.
  - Added focused regression tests in `tests/test_openai_genesis_v7_runner.py`.
- Evidence:
  - `python3.13 -m pytest tests/test_openai_genesis_v7_runner.py -q` -> `5 passed`
  - `python3.13 -m py_compile scripts/run_openai_genesis_v7_baseline.py` -> passed
  - `make release-gate` first attempt failed because new tracked files made forensic inventory/control ledgers stale.
  - Regenerated `docs/audit/FORENSIC_FILE_INVENTORY.*` and `docs/audit/FORENSIC_AUDIT_CONTROLS.*`.
  - `python3.13 scripts/generate_forensic_inventory.py --check` -> `forensic inventory current`
  - `python3.13 scripts/generate_forensic_audit_controls.py --check` -> `forensic audit controls current`
  - `python3.13 -m pytest tests/test_openai_genesis_v7_runner.py tests/test_forensic_inventory.py -q` -> `7 passed`
  - `npm run agentco:score-validation -- --check` initially reported a stale generated report hash after the new commit; regenerated `reports/system_run/latest/score_validation.{json,md}` for commit `07a7ac8abcb628eea98eff519dd75a2c412fe4f0`.
  - Final `make release-gate` on clean commit `e0983c56ca39f315da3e391ae2e32b07204872d4` -> passed.
- Next candidate item:
  - Run broader cheap gates, then continue with audit-runner/subsystem audit failures or strengthen V7 artifact verifier to reject historical-style hash-only case evidence for any new accepted run.

## Iteration 2 — 2026-07-19

- Branch: `loop/completion`
- Starting HEAD: `3393283c0830c61eec526e8d933a1a1be9f14f20`
- Selected item: strengthen capability genesis artifact verification for DoD 3 evidence diagnosability.
- Claude/Duet: attempted `duet talk ... claude`; still unavailable due Claude session limit resetting at `4am (Asia/Calcutta)`.
- Changed:
  - `scripts/verify_capability_genesis_artifact.py` now discovers Genesis V7 campaign manifests and verifies case-level real-provider evidence shape.
  - The verifier now rejects provider-attempted V7 cases that only preserve response hashes and lack redacted provider response content, provider request ID hash, finish reason, parser input hash/redacted parser input and audit references.
  - The verifier now continues inspecting a manifest even when `INTERNAL_PAYLOAD_MANIFEST.json` is missing, so payload-manifest failures cannot mask case-evidence failures.
  - Added focused verifier regression tests in `tests/test_capability_genesis_artifact_verifier.py`.
  - Recorded `GCR-011` as an open blocking finding for the committed Genesis V7 attempt-2 hash-only evidence.
- Evidence:
  - `python3.13 -m pytest tests/test_capability_genesis_artifact_verifier.py tests/test_openai_genesis_v7_runner.py -q` -> `9 passed`
  - `python3.13 -m py_compile scripts/verify_capability_genesis_artifact.py` -> passed
  - `python3.13 -m json.tool docs/audit/current/GOVERNED_CAPABILITY_RUNTIME_FINDINGS.json` -> passed
  - `python3.13 scripts/generate_forensic_inventory.py --check` -> `forensic inventory current`
  - `python3.13 scripts/generate_forensic_audit_controls.py --check` -> `forensic audit controls current`
  - `python3.13 scripts/verify_capability_genesis_artifact.py --check` -> expected failure, now reports stale freeze coverage for the modified verifier, missing V7 payload manifests, 24 non-diagnosable V7 provider evidence records and identical response hashes across all 24 provider-attempted cases.
- Next candidate item:
  - Continue with audit-runner/subsystem audit failures or implement a new freeze/evidence path for the strengthened verifier before any future real-provider rerun.

## Iteration 3 — 2026-07-19

- Branch: `loop/completion`
- Starting HEAD: `030527158dafd3516a467fafe4fd522106b2a9b0`
- Selected item: make the loop DoD "zero blocking findings" condition executable instead of relying on manual ledger inspection.
- Claude/Duet: attempted `duet talk ... claude`; still unavailable due Claude session limit resetting at `4am (Asia/Calcutta)`.
- Changed:
  - Added `scripts/verify_no_blocking_findings.py`, which scans `docs/audit/current/*.json` for `open_blocking` and `open_hold_for_more_evidence` findings.
  - Added `tests/test_verify_no_blocking_findings.py`.
  - Added `make no-blocking-findings` and wired it into `make release-gate` as step `0c`.
- Evidence:
  - `python3.13 -m pytest tests/test_verify_no_blocking_findings.py -q` -> `3 passed`
  - `python3.13 -m py_compile scripts/verify_no_blocking_findings.py` -> passed
  - `python3.13 scripts/verify_make_targets.py --check` -> `{"missing": 0, "success": true}`
  - `python3.13 scripts/verify_no_blocking_findings.py --check` -> expected failure reporting `GCR-008`, `GCR-010`, `GCR-011` and `HST-001`.
  - `make release-gate` after commit -> expected failure at step `0c/12` (`no-blocking-findings`) reporting `GCR-008`, `GCR-010`, `GCR-011` and `HST-001`.
- Next candidate item:
  - Continue with audit-runner/subsystem audit discovery, then work remaining non-human-blocked verifier gaps.

## Iteration 4 — 2026-07-19

- Branch: `loop/completion`
- Starting HEAD: `11e68c90370d16ec6b26aa72b6bc19445c756f43`
- Selected item: define and enforce the machine-readable 18-subsystem audit evidence contract required by the loop DoD.
- Claude/Duet: attempted `duet talk ... claude`; still unavailable due Claude session limit resetting at `4am (Asia/Calcutta)`.
- Changed:
  - Added `scripts/verify_subsystem_audit_results.py`.
  - Added `tests/test_verify_subsystem_audit_results.py`.
  - Added `make subsystem-audit-results-check` and wired it into `make release-gate` after the blocking-findings guard.
  - Regenerated forensic inventory and audit-control ledgers for the new verifier and target.
- Evidence:
  - `python3.13 -m pytest tests/test_verify_subsystem_audit_results.py -q` -> `5 passed`
  - `python3.13 -m py_compile scripts/verify_subsystem_audit_results.py` -> passed
  - `python3.13 scripts/verify_make_targets.py --check` -> `{"missing": 0, "success": true}`
  - `python3.13 scripts/generate_forensic_inventory.py --check` -> `forensic inventory current`
  - `python3.13 scripts/generate_forensic_audit_controls.py --check` -> `forensic audit controls current`
  - `python3.13 scripts/verify_subsystem_audit_results.py --check` -> expected failure: `SUBSYSTEM_AUDIT_RESULTS_MISSING`.
- Next candidate item:
  - Build the actual subsystem-audit runner/result producer, starting with small local deterministic audits rather than relying on external agent summaries.

## Iteration 5 — 2026-07-19

- Branch: `loop/completion`
- Starting HEAD: `5c7adaefc863569197e93501def783fb1c14f067`
- Selected item: produce the missing machine-readable subsystem audit artifact without relying on external agent summaries.
- Claude/Duet: attempted `duet talk ... claude`; still unavailable due Claude session limit resetting at `4am (Asia/Calcutta)`.
- Changed:
  - Added `scripts/run_subsystem_audit_results.py`.
  - Added `make subsystem-audit-results`.
  - Added `tests/test_run_subsystem_audit_results.py`.
  - Generated `docs/audit/current/SUBSYSTEM_AUDIT_RESULTS.json` and `.md`.
  - Regenerated forensic inventory and audit-control ledgers.
- Evidence:
  - `python3.13 scripts/run_subsystem_audit_results.py` -> completed and wrote subsystem results: `16 passed`, `2 failed`.
  - Failed subsystems are `capability_runtime_protocol` (`GCR-008`, `GCR-010`, `GCR-011`) and `infra_deployment` (`HST-001`).
  - `python3.13 -m pytest tests/test_run_subsystem_audit_results.py tests/test_verify_subsystem_audit_results.py -q` -> `8 passed`
  - `python3.13 -m py_compile scripts/run_subsystem_audit_results.py` -> passed
  - `python3.13 scripts/verify_make_targets.py --check` -> `{"missing": 0, "success": true}`
  - `python3.13 scripts/generate_forensic_inventory.py --check` -> `forensic inventory current`
  - `python3.13 scripts/generate_forensic_audit_controls.py --check` -> `forensic audit controls current`
  - `python3.13 scripts/verify_subsystem_audit_results.py --check` -> expected failure on the two failed subsystems and linked open findings.
- Next candidate item:
  - Work the non-provider/non-hosted parts of `capability_runtime_protocol`; leave real provider execution and hosted staging blocked until authorized evidence is available.

## Iteration 6 — 2026-07-19

- Branch: `loop/completion`
- Starting HEAD: `4ae31cfb405ea59db296f14b0956506886bb12d9`
- Selected item: improve the non-provider parts of the Genesis V7 real-provider runner that likely contributed to all 24 attempt-2 cases producing schema-invalid output.
- Claude/Duet: attempted `duet talk ... claude`; still unavailable due Claude session limit resetting at `4am (Asia/Calcutta)`.
- Changed:
  - Increased `MAX_COMPLETION_TOKENS` from `256` to `1000`; conservative hard-cap estimate remains below USD 3.00 for the frozen 24 cases plus canary.
  - Added domain-specific required JSON fields to provider-visible V7 requests.
  - Added explicit JSON-only chat body construction that derives the model from authorization and does not request private chain-of-thought.
  - Added explicit empty-content parse classification.
  - Updated `GCR-010` remediation text to describe this prepared fix without closing the finding.
  - Regenerated subsystem audit results and forensic ledgers.
- Evidence:
  - `python3.13 -m pytest tests/test_openai_genesis_v7_runner.py tests/test_capability_genesis_artifact_verifier.py tests/test_run_subsystem_audit_results.py tests/test_verify_subsystem_audit_results.py -q` -> `20 passed`
  - `python3.13 -m py_compile scripts/run_openai_genesis_v7_baseline.py` -> passed
  - Conservative cost check -> `max_completion_tokens=1000`, `conservative_campaign_max=0.789`, `hard_cap=3.0`.
  - `python3.13 scripts/run_subsystem_audit_results.py` -> completed with `16 passed`, `2 failed`.
  - `python3.13 scripts/generate_forensic_inventory.py --check` -> `forensic inventory current`
  - `python3.13 scripts/generate_forensic_audit_controls.py --check` -> `forensic audit controls current`
  - `python3.13 scripts/verify_subsystem_audit_results.py --check` -> expected failure on `capability_runtime_protocol` and `infra_deployment`.
  - `python3.13 scripts/verify_no_blocking_findings.py --check` -> expected failure on `GCR-008`, `GCR-010`, `GCR-011` and `HST-001`.
- Next candidate item:
  - Prepare a new V7 campaign identity/freeze path for a future authorized rerun, or continue closing verifier gaps that do not require provider credentials or hosted infrastructure.

## Iteration 7 — 2026-07-19

- Branch: `loop/completion`
- Starting HEAD: `6eae2130e97d86b833f67ebef4d4794454832537`
- Selected item: persist the user's loop-control instruction so restarted iterations continue while status remains `CONTINUE`.
- Claude/Duet: attempted `duet talk ... claude`; still unavailable due Claude session limit resetting at `4am (Asia/Calcutta)`.
- Changed:
  - Added a loop continuation policy to `.loop/DECISIONS.md`.
- Evidence:
  - `cat .loop/status` -> `CONTINUE`
  - `cat .loop/DECISIONS.md` -> continuation policy recorded.
- Next candidate item:
  - Continue with the highest-leverage non-human-blocked item, currently stale finding cleanup around `GCR-008` or further capability-runtime verifier strengthening.
