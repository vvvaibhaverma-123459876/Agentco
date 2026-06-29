-- Migration 092: Canonical agent task event compatibility view
--
-- Durable execution exposes agent_tasks as the canonical task read path while
-- the autonomy runtime stores lifecycle events in autonomy_task_events. Expose
-- a matching agent_task_events view so verification and tooling can depend on
-- one canonical name without duplicating event rows.

CREATE OR REPLACE VIEW agent_task_events AS
SELECT
    id,
    task_id,
    event_type,
    previous_status,
    new_status,
    actor_type,
    actor_id,
    reason,
    payload_json,
    trace_id,
    created_at
FROM autonomy_task_events;
