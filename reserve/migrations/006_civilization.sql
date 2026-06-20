-- Migration 006 — Civilization substrate tables.
--
-- Three hierarchy levels: Institution → Department → Agent (via membership edge).
-- Society and Civilization levels are DEFERRED and not created here.

-- ── institutions ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS institutions (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    entity_type      TEXT NOT NULL DEFAULT 'institution'
                         CHECK (entity_type = 'institution'),
    parent_id        TEXT NULL,
    status           TEXT NOT NULL DEFAULT 'active'
                         CHECK (status IN ('active','suspended','retired')),
    purpose          TEXT NOT NULL,
    authority_scope  JSONB NOT NULL DEFAULT '[]',
    reputation_score DOUBLE PRECISION NULL,   -- derived only; see trigger below
    metadata         JSONB NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT institutions_parent_null CHECK (parent_id IS NULL)
);

-- ── departments ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS departments (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    entity_type      TEXT NOT NULL DEFAULT 'department'
                         CHECK (entity_type = 'department'),
    parent_id        TEXT NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    status           TEXT NOT NULL DEFAULT 'active'
                         CHECK (status IN ('active','suspended','retired')),
    purpose          TEXT NOT NULL,
    authority_scope  JSONB NOT NULL DEFAULT '[]',
    reputation_score DOUBLE PRECISION NULL,
    metadata         JSONB NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── agent_membership_edges ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_membership_edges (
    agent_id        TEXT NOT NULL,
    department_id   TEXT NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
    role_name       TEXT NOT NULL,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at      TIMESTAMPTZ NULL,
    evicted_at      TIMESTAMPTZ NULL,
    eviction_reason TEXT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (agent_id, department_id)
);

ALTER TABLE agent_membership_edges ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ NULL;
ALTER TABLE agent_membership_edges ADD COLUMN IF NOT EXISTS evicted_at TIMESTAMPTZ NULL;
ALTER TABLE agent_membership_edges ADD COLUMN IF NOT EXISTS eviction_reason TEXT NULL;

-- ── institution_contracts ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS institution_contracts (
    institution_id  TEXT NOT NULL UNIQUE REFERENCES institutions(id) ON DELETE RESTRICT,
    contract        JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── institution_output_reviews ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS institution_output_reviews (
    id                       TEXT PRIMARY KEY,
    output_id                TEXT NOT NULL,
    producing_institution_id TEXT NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    reviewer_institution_id  TEXT NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    status                   TEXT NOT NULL DEFAULT 'proposed'
                                 CHECK (status IN (
                                     'proposed','under_review','challenged',
                                     'approved','rejected','archived')),
    review_evidence          JSONB,
    reputation_delta         DOUBLE PRECISION,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- SELF-CERTIFICATION BAN: enforced at DB level
    CONSTRAINT no_self_certification
        CHECK (producing_institution_id <> reviewer_institution_id)
);

-- ── civilization_memory_events ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS civilization_memory_events (
    id               TEXT PRIMARY KEY,
    entity_type      TEXT NOT NULL,
    entity_id        TEXT NOT NULL,
    event_type       TEXT NOT NULL CHECK (event_type IN (
                         'output_created','review_completed','challenge_opened',
                         'challenge_resolved','governance_decision','reputation_updated',
                         'institution_created','institution_retired','failure_recorded',
                         'lesson_extracted')),
    summary          TEXT,
    evidence_refs    JSONB,
    reputation_delta DOUBLE PRECISION,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── governance_decisions ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS governance_decisions (
    id                  TEXT PRIMARY KEY,
    decision_type       TEXT NOT NULL CHECK (decision_type IN (
                            'create_institution','retire_institution',
                            'approve_high_risk_output','change_reputation_weights',
                            'change_contract')),
    status              TEXT NOT NULL DEFAULT 'proposed'
                            CHECK (status IN (
                                'proposed','deliberating','approved',
                                'rejected','executed','rolled_back')),
    proposer_entity_id  TEXT,
    approver_entity_id  TEXT,
    payload             JSONB,
    audit_event_id      TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── TRIGGER: guard reputation_score writes ────────────────────────────────────
-- A direct UPDATE of reputation_score on institutions or departments is only
-- allowed if a 'reputation_updated' civilization_memory_event row is being
-- written in the SAME transaction (same txn_id checked via advisory lock /
-- session variable). We use a session-level flag set by the propagation service.
--
-- Implementation: propagation service sets a session var before UPDATE, trigger
-- checks it. Any UPDATE without the flag raises.

CREATE OR REPLACE FUNCTION check_reputation_update_authorized()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    flag TEXT;
BEGIN
    -- Only fires when reputation_score actually changes.
    IF NEW.reputation_score IS NOT DISTINCT FROM OLD.reputation_score THEN
        RETURN NEW;
    END IF;
    -- Check session-level authorization flag set by propagation service.
    BEGIN
        flag := current_setting('civilization.reputation_update_authorized');
    EXCEPTION WHEN undefined_object THEN
        flag := '';
    END;
    IF flag <> 'true' THEN
        RAISE EXCEPTION
            'REPUTATION GUARD: reputation_score may only be updated by the '
            'propagation service (civilization.reputation_update_authorized not set). '
            'Use reputation_service.propagate() which writes a memory event first.';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_institutions_reputation_guard ON institutions;
CREATE TRIGGER trg_institutions_reputation_guard
    BEFORE UPDATE ON institutions
    FOR EACH ROW EXECUTE FUNCTION check_reputation_update_authorized();

DROP TRIGGER IF EXISTS trg_departments_reputation_guard ON departments;
CREATE TRIGGER trg_departments_reputation_guard
    BEFORE UPDATE ON departments
    FOR EACH ROW EXECUTE FUNCTION check_reputation_update_authorized();

-- ── TRIGGER: institution_output_reviews append-only (status transitions only) ─
-- Reviews may change status (state machine); their core identity fields are immutable.
CREATE OR REPLACE FUNCTION trg_review_core_immutable()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.output_id <> OLD.output_id
       OR NEW.producing_institution_id <> OLD.producing_institution_id
       OR NEW.reviewer_institution_id <> OLD.reviewer_institution_id THEN
        RAISE EXCEPTION 'REVIEW IMMUTABILITY: output_id, producing_institution_id, '
            'and reviewer_institution_id are write-once.';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_review_core_immutable ON institution_output_reviews;
CREATE TRIGGER trg_review_core_immutable
    BEFORE UPDATE ON institution_output_reviews
    FOR EACH ROW EXECUTE FUNCTION trg_review_core_immutable();
