# Memory vs Amnesia Comparison

Status: not executed.

The requested rerun depends on `scripts/autonomous_prediction_loop.py`, but that
script is not present in this synced checkout. No internet prediction loop was
rerun for this artifact, and no claim is made that duplicate external
predictions are suppressed in the live internet loop.

What is proven instead:

| Scenario | Result |
|---|---|
| First task for `research-agent` | Prompt context says `No previous experience`; task can write an episodic memory. |
| Second task for same agent/domain | Retrieval returns the prior episodic memory; prompt contains the previous finding. |
| Prediction lesson written | Next retrieval includes the lesson in prompt context. |
| Semantic extraction | Recent episodic memories produce semantic memory rows. |
| Cross-agent sharing | `ceo-agent` retrieves a shared lesson written from `research-agent` memory. |

Proof artifact:

- `evals/acceptance/memory_lifecycle_trace.md`
- `tests/e2e/test_memory_lifecycle.py`

Remaining work:

- Add or restore `scripts/autonomous_prediction_loop.py`.
- Run the first internet prediction scan with memory enabled.
- Run the second scan over the same sources.
- Assert duplicate prediction suppression and save the concrete side-by-side
  trace here.
