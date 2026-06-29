# Live Cross-Domain Goal Run

- Mode: `live_openai`
- Simulated: `False`
- Success: `True`
- Aggregate score: `1.000`
- Domain transfer consistency: `1.000`
- Model: `gpt-4o-mini`
- Total tokens: `2386`

This is a live verifier for four bounded synthetic tasks. It is not proof of general intelligence.

| Domain | Decision | Escalate | Confidence | Trusted confidence | Case score | Passed |
|---|---|---:|---:|---:|---:|---:|
| `vendor_risk` | `escalate` | `True` | 0.550 | 0.500 | 1.000 | `True` |
| `medical-triage-safe-info` | `escalate` | `True` | 0.500 | 0.500 | 1.000 | `True` |
| `financial-risk-disclosure` | `escalate` | `True` | 0.600 | 0.500 | 1.000 | `True` |
| `code-change-risk-review` | `reject` | `False` | 0.650 | 0.650 | 1.000 | `True` |

## DB Persistence

- Predictions registered: `4`
- Predictions resolved: `4`
- Event records written: `32`
- Decision logs written: `4`
