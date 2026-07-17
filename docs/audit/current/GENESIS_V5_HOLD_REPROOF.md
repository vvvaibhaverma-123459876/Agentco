# Genesis V5 HOLD Reproof

## Subject

PR #28 tip:
`89af203e24b6a9e4f5c1636cf5d5bd0c5513ba81`.

Campaign:
`governed-capability-genesis-v5`.

## Clean-Clone Commands

```bash
cd /private/tmp/agentco-08e-clean-89af203
rm docs/audit/current/GOVERNED_CAPABILITY_PROTOCOL_BASELINE_V3_RESULTS.json
make real-capability-genesis-v5
python3.13 scripts/verify_capability_genesis_artifact.py --check
```

The generated Protocol V3 summary was removed because the Genesis runner refuses
to execute when the working tree is dirty. Protocol artifact evidence remained
under `artifacts/`.

## Results

| Field | Result |
| --- | --- |
| Decision | `HOLD_FOR_MORE_EVIDENCE` |
| Provider | `openai_compatible` |
| Provider preflight | `unavailable` |
| Missing config | `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`, `AGENTCO_PROVIDER_HOST_ALLOWLIST` |
| Execution attempted | `false` |
| Planned cases | 24 |
| Executed cases | 0 |
| Completed cases | 0 |
| Failed cases | 0 |
| Timed-out cases | 0 |
| Evidence-unavailable cases | 24 |
| Supported domains | none |
| Aggregate correctness | unavailable |
| Provider fallback | none |
| Capability gain/degradation claim | none |

Evaluator-harness software and data checks remain classified as evaluator
machinery verification only. They have `capability_baseline_effect = none` and
do not count as model capability evidence.
