-- Migration 075: Canonical agent task compatibility views
--
-- The deployable agent dispatch path stores tasks in workflow_tasks. Expose
-- that path as agent_tasks so external executors and verification tools do
-- not drift to a non-existent durable_tasks table.

CREATE OR REPLACE VIEW agent_tasks AS
SELECT
    task_id,
    agent_id,
    task_type,
    payload,
    queued_at,
    started_at,
    completed_at,
    status,
    result,
    error,
    audit_log_id,
    event_id,
    action_attestation_id,
    claimed_by,
    retry_count
FROM workflow_tasks;
