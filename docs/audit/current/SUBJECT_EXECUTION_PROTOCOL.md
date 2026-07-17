# Subject Execution Protocol

Batch 07B defines `subject-benchmark-v1` as the only accepted behavioral
cross-version interface.

The control harness writes a candidate-readable request JSON file with:

```json
{
  "protocol_version": "subject-benchmark-v1",
  "run_id": "...",
  "case_id": "...",
  "domain": "...",
  "prompt": "...",
  "seed": 101,
  "budget": {},
  "tool_allowlist": [],
  "timeout_seconds": 30
}
```

A subject that supports the protocol must return:

```json
{
  "protocol_version": "subject-benchmark-v1",
  "run_id": "...",
  "case_id": "...",
  "status": "completed",
  "answer": {},
  "confidence": 0.7,
  "evidence_refs": ["audit://..."],
  "tool_calls": [],
  "authorization_events": [],
  "budget_usage": {},
  "runtime_events": [],
  "audit_refs": [],
  "error": null
}
```

If an immutable subject lacks this interface, the external adapter may invoke a
real subject process and record the case as `unsupported`. It must not invent an
answer, confidence, authorization result, budget result, tool call, latency or
resource use.

Hidden expected outputs remain outside subject-readable paths. The evaluator
scores only after subject output is captured.
