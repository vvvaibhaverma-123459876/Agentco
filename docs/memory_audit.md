# Memory Lifecycle Audit

Date: 2026-06-18

## Scope

This audit checks the current repository wiring before adding experiential memory. It follows the requested gate: diagnose first, then build.

## Precondition Check

- Local repository is synced to `origin/main` at `9df6fd3`.
- `AGENTCO_TEST_DATABASE_URL` is not exported in this Codex shell.
- Read-only schema check was run against `postgresql://agentco:password@localhost:5432/agentco`.
- Live Postgres is reachable at that URL.
- Kafka reachability was not rechecked during this audit.

## Existing Memory Store

### Backend service

`backend/src/services/memory-store.service.ts` is a real Postgres-backed TypeScript service for the existing `agent_memory` table and `shared_knowledge` table.

Observed capabilities:

- Reads `agent_memory` by `(agent_id, namespace, key)`.
- Writes `agent_memory` with `INSERT ... ON CONFLICT DO UPDATE`.
- Supports TTL expiry through the `expires_at` column.
- Reads and writes `shared_knowledge`.
- Tries pgvector semantic search for shared knowledge, with full-text fallback if embedding service is unavailable.
- Enforces shared-knowledge writer permissions at the app layer.

Important gap:

- `writeAgentMemory()` overwrites existing memory on key conflict. That is incompatible with the requested append-only experiential memory invariant.

### Python memory client

`agents/core/memory_client.py` exists, but it is a stub.

Observed methods:

- `read(key)`
- `write(key, value, ttl_seconds=None)`
- `read_shared(query, top_k=5)`
- `write_shared(key, content, metadata)`
- `get_agent_state()`
- `update_heartbeat()`

Important gaps:

- It does not connect to Postgres.
- Reads always return `None` or `[]`.
- Writes only log and do not persist.
- It is not imported or used by `runtime/base_agent/base_agent_v2.py`.

## Base Agent Lifecycle

`runtime/base_agent/base_agent_v2.py` is the current V2 base agent.

Observed lifecycle points:

- Agent entrypoint: subclasses implement `run(task)`.
- LLM call path: subclasses can call `act(messages, schema=None)`, which delegates to `get_validated_output()`.
- Action path: subclasses call `execute_action(action, prediction_id=None, pre_approved_token=None)`.
- Prediction preregistration: `pre_register_claim(...)`.
- Audit capture: `_write_audit(...)` appends in-memory `AuditEntryV2` objects.

Memory injection points:

- Task start: no common pre-run hook currently exists in `BaseAgentV2`; subclasses call `run()` directly.
- Prompt context: `act()` receives already-assembled `messages`; there is no base prompt builder.
- Task completion: no common post-run hook currently exists.
- Prediction resolution: no hook in `BaseAgentV2` currently writes lessons when predictions resolve.

Important gap:

- There is no automatic memory retrieval or episodic capture in the base lifecycle. Any integration must add a shared wrapper/hook without breaking existing subclass `run()` behavior.

## Current Agent Memory Usage

Search results show:

- `agents/core/memory_client.py` exports `MemoryClient`.
- `agents/core/__init__.py` re-exports `MemoryClient`.
- `agents/core/base_agent.py` mentions statefulness via `memory_client`.
- `agents/core/tools/handlers.py` has direct SQL handlers for the old `agent_memory` key/value table.
- `runtime/base_agent/base_agent_v2.py` does not use memory.

Conclusion:

- Some older agent/tool code can interact with key/value memory manually.
- V2 runtime agents do not automatically read or write memory during task execution.

## Learning Directory

`learning/` exists and implements a specified calibration-improvement loop:

- `learning/intelligence_agent/intelligence_agent.py`
- `learning/scenario_agent/scenario_agent.py`
- `learning/trainer_agent/trainer_agent.py`
- `learning/memory_agent/memory_agent.py`
- `learning/learning_loop.py`

Observed behavior:

- Intelligence-Agent scans calibration state and surprise signals.
- Scenario-Agent generates hypotheses and preregisters them.
- Trainer-Agent evaluates hypotheses through simulation and produces proposals.
- Memory-Agent stores approved cycle outcomes in an in-memory Python list.
- Human approval remains required before memory cycle writes.

Important gaps:

- This is not the requested experiential memory loop.
- `MemoryAgent` does not write to Postgres.
- The loop does not automatically capture every task as episodic memory.
- It does not retrieve prior experience into agent prompts.
- It does not extract prediction lessons into persistent memory.

## Live Postgres Schema

Read-only schema check:

```text
Table "public.agent_memory"
Column       Type                     Nullable  Default
id           uuid                     not null  gen_random_uuid()
agent_id     character varying(64)    not null
namespace    character varying(128)   not null
key          character varying(256)   not null
value        jsonb                    not null
ttl_seconds  integer
expires_at   timestamp with time zone
created_at   timestamp with time zone not null  now()
updated_at   timestamp with time zone not null  now()
```

Indexes:

- Primary key on `id`.
- Unique constraint on `(agent_id, namespace, key)`.
- Index on `agent_id`.
- Index on `(namespace, key)`.
- Partial index on `expires_at`.

Constraints and triggers:

- Foreign key from `agent_id` to `agent_state(agent_id)`.
- Row-level security is enabled, but no policies are visible.
- TTL trigger `trg_agent_memory_expires_at` exists.

Important gaps:

- No `memory_type`, `task_id`, `prediction_id`, `domain`, `summary`, `content`, `embedding`, `importance`, `access_count`, `last_accessed_at`, or `superseded_by` columns.
- No append-only guard for summary/content.
- No delete prevention trigger.
- Current unique key encourages overwrites by `(agent_id, namespace, key)`.

## Summary

Wired:

- Real backend Postgres key/value memory service exists.
- Real `agent_memory` table exists.
- Shared knowledge service supports pgvector when embeddings are available.
- Learning loop agents exist for calibration proposal workflows.

Stubbed:

- Python `MemoryClient`.
- Learning `MemoryAgent` persistence.

Missing:

- Append-only experiential memory schema.
- Automatic pre-task memory retrieval.
- Automatic post-task episodic capture.
- Prediction-resolution lesson memory.
- Semantic memory distillation.
- Cross-agent sharing through persistent memory.
- End-to-end proof that run 2 is informed by run 1.

## Recommendation

Add a new append-only `agent_memories` table instead of destructively reshaping the existing `agent_memory` key/value table. This preserves the proven backend memory-store contract while adding the requested episodic, semantic, and prediction-lesson lifecycle.
