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
