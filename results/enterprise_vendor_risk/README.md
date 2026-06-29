> **Historical/superseded status notice (2026-06-29):** This document is retained for audit history. Do not treat production-ready, complete, or deployment-ready language below as current truth. Current implementation status is tracked in `BUILD_LEDGER.yaml` and summarized in `docs/CURRENT_IMPLEMENTATION_REALITY.md`. As of 2026-06-29, AgentCo is local-native runnable, not production certified, with 18/67 ledger items verified.

# Enterprise Vendor Risk Triage Benchmark - Results

**Latest Run:** `/latest.json` and `/latest.md`

## Important Notice

Committed results in this directory may include smoke-test runs using the deterministic fake model. These results demonstrate that the benchmark framework is working correctly but **do not represent actual model performance**.

Real external provider results must include:
- ✅ Model ID (e.g., `openai:gpt-4.1`)
- ✅ Timestamp (ISO 8601 format)
- ✅ Dataset hash (SHA256 of cases.jsonl)
- ✅ Commit SHA (for reproducibility)
- ✅ Status: "completed" (not "not_run")
- ✅ No skip_reason (or skip_reason is null for completed trials)

If you see a result with:
- `status: "not_run"`
- `skip_reason: "missing_credentials"`

Then that model was not actually run due to missing API credentials.

## Running the Benchmark

### Smoke Test (No Credentials Required)
```bash
make vendor-risk-smoke
```

### Full Benchmark (With Credentials)
```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_API_KEY=...

python -m evals.enterprise_vendor_risk.run_benchmark \
  --models "fake:deterministic,agentco,openai:gpt-4.1,anthropic:claude-3-7-sonnet,google:gemini-2.5-pro" \
  --output results/enterprise_vendor_risk/runs/benchmark_$(date +%s).json

python -m evals.enterprise_vendor_risk.leaderboard \
  --input results/enterprise_vendor_risk/runs/benchmark_<timestamp>.json \
  --output-json results/enterprise_vendor_risk/latest.json \
  --output-md results/enterprise_vendor_risk/latest.md
```

## Result Files

- `latest.json` — Latest leaderboard in JSON format (structured data)
- `latest.md` — Latest leaderboard in Markdown format (human-readable table)
- `runs/` — All historical runs stored by timestamp

## Interpreting Results

See `/docs/agentco_vs_llms_vendor_risk_benchmark.md` for detailed:
- Metric definitions
- Target performance levels
- How to interpret gaps between models
- Known limitations

## Troubleshooting

**Model shows `status: "not_run"` with `skip_reason: "missing_credentials"`**
- The API key for that provider is not set or is invalid
- Set the required environment variable (see "Running the Benchmark" above)
- Re-run the benchmark

**Hallucination rate appears high (>20%)**
- Model is fabricating evidence, certifications, or policy compliance
- Check the raw output in the JSON for specific false claims
- This is expected behavior for LLMs without fine-tuning on this task

**Evidence F1 is low (<0.6)**
- Model is not citing required evidence or is citing evidence that doesn't exist
- Look for model citations that don't match the `evidence_id` field in the task

**All models show low decision_accuracy**
- The cases may be ambiguous or the grading may be too strict
- Review specific failed cases in the raw JSON output
- Consider adding more test cases to increase statistical reliability
