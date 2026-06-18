# Memory Audit — AgentCo (2026-06-18)

## What Exists

### agents/core/memory_client.py — STUB (no real storage)
All methods (`read`, `write`, `read_shared`, `write_shared`, `get_agent_state`, `update_heartbeat`) are 
no-ops that only call `logger.debug`. No real Postgres or Pinecone connection. Exported from 
`agents/core/__init__.py` but **never imported in `runtime/base_agent/base_agent_v2.py`**.

### runtime/base_agent/base_agent_v2.py — No memory hooks
The base agent has: `__init__`, `run()` (abstract), `act()`, `execute_action()`, `pre_register_claim()`.
**No pre-task memory retrieval, no post-task episodic capture, no prediction-lesson extraction.**
The lifecycle has no hooks for memory at any point.

### agent_memory table — EXISTS, key-value only
Simple `(agent_id, namespace, key, value, ttl_seconds)` KV store. Used by 
`agents/core/tools/handlers.py` (memory_read / memory_write tool handlers) but NOT by any agent 
autonomously. Does not support episodic, semantic, or lesson memory types.

### agent_memories table — DOES NOT EXIST
No migration for structured agent memory. Migration 015 needs to be written.

### pgvector — NOT INSTALLED
`pg_extension` shows no `vector` extension. Embedding-based similarity search must fall back to 
FLOAT[] storage + Python-side cosine similarity. The ivfflat index from the spec cannot be created.

### learning/ directory — SPECIFIED, partially stubbed
- `IntelligenceAgent`: Real implementation (reads calibration state).
- `MemoryAgent`: Uses in-memory Python list (`_memory_store: list[MemoryEntry]`). NOT connected to Postgres.
- `TrainerAgent`: Backtests hypotheses, produces proposals requiring human approval.
- `ScenarioAgent`: Generates hypotheses from learning signal.
- `LearningLoop`: Orchestrates the cycle correctly (Intelligence → Scenario → Trainer → Human gate → Memory),
  but the Memory step writes to in-memory list, not Postgres.

### backend/src/services/memory-store.service.ts — PROVEN (TypeScript)
Real Postgres reads/writes against `agent_memory` table. Has TTL, namespace isolation. Proven by 6 
integration tests mentioned in the task. This is a TypeScript service; the Python layer has a stub client.

## What Is Missing (to be built)

1. **`backend/src/db/migrations/015_agent_memories.sql`** — the `agent_memories` table with 
   immutability trigger (no `vector` type, use `FLOAT[]` for embeddings instead).
2. **`agents/core/memory/memory_writer.py`** — real Postgres writes for episodic, semantic, 
   and prediction_lesson memory types.
3. **`agents/core/memory/memory_reader.py`** — real Postgres reads with recency + domain + 
   full-text retrieval; formats context for system prompt injection.
4. **`agents/core/memory/learning_loop.py`** — lesson extraction from episodes and predictions, 
   semantic consolidation, cross-agent sharing.
5. **Memory hooks in `runtime/base_agent/base_agent_v2.py`** — `execute()` wrapper method adds 
   pre-task retrieval and post-task episodic capture without changing `run()` or breaking tests.
6. **`tests/e2e/test_memory_lifecycle.py`** — full lifecycle proof (amnesia → episodic → lessons → 
   semantic → cross-agent sharing).

## Invariants Preserved

- `agent_memory` (key-value) table untouched — existing tool handlers continue to work.
- Prediction ledger immutability: unchanged.
- All 224 existing tests pass before and after.
- Memory writes are append-only: `summary` and `content` are immutable once written (trigger enforced).
- Corrections create new rows with `superseded_by` pointing at the old row.
- Memory retrieval never blocks the agent: 500ms budget enforced via Python timeout.

## pgvector Workaround

Since pgvector is not installed, embeddings are stored as `FLOAT[]` in Postgres. Cosine similarity 
is computed in Python when needed (write_semantic duplicate detection, semantic retrieve). For datasets 
up to ~1000 memories this is adequate; at scale, installing pgvector + the ivfflat index would 
replace Python-side similarity. This limitation is documented as an outstanding item.

## Outstanding (under-claim, never over-claim)

- Embeddings require a live OpenAI API call (text-embedding-3-small); if the key is absent or the 
  call fails, memories are written WITHOUT embedding (retrieval falls back to recency + full-text).
- MemoryAgent in `learning/` still uses in-memory storage; wiring it to `agent_memories` is out of 
  scope for this task but the table schema supports it.
- Cross-agent lesson sharing requires the sharing agent's trust score; trust scores are per 
  (agent, domain, horizon) so sharing a cross-domain lesson uses a conservative default importance.
