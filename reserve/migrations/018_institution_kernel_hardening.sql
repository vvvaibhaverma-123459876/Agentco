-- Institution kernel hardening support.

ALTER TABLE agent_membership_edges ADD COLUMN IF NOT EXISTS deactivated_at TIMESTAMPTZ NULL;
ALTER TABLE agent_membership_edges ADD COLUMN IF NOT EXISTS deactivation_reason TEXT NULL;
ALTER TABLE agent_membership_edges ADD COLUMN IF NOT EXISTS evicted_by TEXT NULL;
ALTER TABLE agent_membership_edges ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}';

ALTER TABLE civilization_memory_events
    DROP CONSTRAINT IF EXISTS civilization_memory_events_event_type_check;

ALTER TABLE civilization_memory_events
    ADD CONSTRAINT civilization_memory_events_event_type_check
    CHECK (event_type IN (
        'output_created',
        'review_completed',
        'challenge_opened',
        'challenge_resolved',
        'governance_decision',
        'reputation_updated',
        'institution_created',
        'institution_retired',
        'failure_recorded',
        'lesson_extracted',
        'membership_added',
        'membership_expired',
        'membership_evicted',
        'review_timed_out',
        'entity_suspended',
        'entity_probation_started',
        'review_archived'
    ));
