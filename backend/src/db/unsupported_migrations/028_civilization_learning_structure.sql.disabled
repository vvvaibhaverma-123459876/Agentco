-- Migration 028: Civilization-Structured Learning Layer
--
-- Transforms Phases 9-13 from agent-only to multi-level learning:
-- Agent → Team → Institution → Society → Civilization
--
-- Every trajectory, candidate, and artifact is attributed to a level.
-- Promotion is gated: agents cannot promote to institutional; teams cannot
-- promote to society-wide without institution+society review; etc.

-- ============================================================
-- CIVILIZATION ENTITY HIERARCHY
-- ============================================================

CREATE TYPE entity_type AS ENUM (
    'agent',
    'team',
    'institution',
    'society',
    'civilization'
);

CREATE TYPE knowledge_type AS ENUM (
    'prompt_template',
    'tool_selection_policy',
    'escalation_threshold',
    'coordination_pattern',
    'procedure',
    'standard',
    'review_rule',
    'research_agenda',
    'dispute_resolution_policy',
    'governance_rule',
    'safety_doctrine',
    'constitutional_constraint'
);

CREATE TYPE learning_level AS ENUM (
    'agent',
    'team',
    'institution',
    'society',
    'civilization'
);

CREATE TYPE dispute_status AS ENUM (
    'raised',
    'under_investigation',
    'awaiting_evidence',
    'in_consensus_formation',
    'resolved',
    'escalated_to_civilization'
);

-- Civilization entities (agents, teams, institutions, etc.)
CREATE TABLE IF NOT EXISTS civilization_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type entity_type NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    parent_entity_id UUID REFERENCES civilization_entities(id),
    domain TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_civilization_entities_type ON civilization_entities(entity_type);
CREATE INDEX idx_civilization_entities_parent ON civilization_entities(parent_entity_id);
CREATE INDEX idx_civilization_entities_domain ON civilization_entities(domain);

-- Membership hierarchy
CREATE TABLE IF NOT EXISTS civilization_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_entity_id UUID NOT NULL REFERENCES civilization_entities(id),
    parent_entity_id UUID NOT NULL REFERENCES civilization_entities(id),
    role TEXT,
    authority_scope_json JSONB DEFAULT '{}'::jsonb,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_civilization_memberships_child ON civilization_memberships(child_entity_id);
CREATE INDEX idx_civilization_memberships_parent ON civilization_memberships(parent_entity_id);

-- ============================================================
-- CIVILIZATION LEARNING EVENTS
-- ============================================================

-- Master learning event log (all levels)
CREATE TABLE IF NOT EXISTS civilization_learning_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    learning_level learning_level NOT NULL,
    agent_id UUID REFERENCES civilization_entities(id),
    team_id UUID REFERENCES civilization_entities(id),
    institution_id UUID REFERENCES civilization_entities(id),
    society_id UUID REFERENCES civilization_entities(id),
    civilization_id UUID REFERENCES civilization_entities(id),
    source_type TEXT NOT NULL, -- replay_batch|simulator|self_modification
    source_id UUID,
    event_type TEXT NOT NULL,
    summary TEXT,
    evidence_refs_json JSONB DEFAULT '[]'::jsonb,
    confidence_reported FLOAT,
    confidence_trusted FLOAT,
    simulation_derived BOOLEAN DEFAULT false,
    requires_review BOOLEAN DEFAULT false,
    review_required_by_entity_type entity_type,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_civilization_learning_events_level ON civilization_learning_events(learning_level);
CREATE INDEX idx_civilization_learning_events_entity ON civilization_learning_events(agent_id, team_id, institution_id, society_id);
CREATE INDEX idx_civilization_learning_events_source ON civilization_learning_events(source_type, source_id);

-- ============================================================
-- INSTITUTIONAL KNOWLEDGE
-- ============================================================

-- Institutional knowledge items (procedures, standards, rules)
CREATE TABLE IF NOT EXISTS institutional_knowledge_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_type knowledge_type NOT NULL,
    institution_id UUID REFERENCES civilization_entities(id),
    society_id UUID REFERENCES civilization_entities(id),
    civilization_id UUID REFERENCES civilization_entities(id),
    title TEXT NOT NULL,
    content_json JSONB NOT NULL,
    evidence_refs_json JSONB DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'draft',
    confidence_trusted FLOAT,
    promoted_from_event_id UUID REFERENCES civilization_learning_events(id),
    simulation_derived BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    promoted_at TIMESTAMPTZ,
    demoted_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ
);

CREATE INDEX idx_institutional_knowledge_type ON institutional_knowledge_items(knowledge_type);
CREATE INDEX idx_institutional_knowledge_institution ON institutional_knowledge_items(institution_id);
CREATE INDEX idx_institutional_knowledge_society ON institutional_knowledge_items(society_id);
CREATE INDEX idx_institutional_knowledge_status ON institutional_knowledge_items(status);

-- ============================================================
-- SOCIETY-LEVEL DISPUTES
-- ============================================================

-- Disputes: when claims/knowledge items conflict at society level
CREATE TABLE IF NOT EXISTS society_disputes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    society_id UUID NOT NULL REFERENCES civilization_entities(id),
    claim_or_knowledge_id UUID,
    conflicting_knowledge_id UUID,
    dispute_type TEXT NOT NULL,
    parties_json JSONB DEFAULT '[]'::jsonb, -- which entities are party to dispute
    evidence_for_json JSONB DEFAULT '[]'::jsonb,
    evidence_against_json JSONB DEFAULT '[]'::jsonb,
    status dispute_status NOT NULL DEFAULT 'raised',
    resolution_summary TEXT,
    simulation_derived BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raised_at TIMESTAMPTZ,
    investigation_started_at TIMESTAMPTZ,
    investigation_completed_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    escalated_to_civilization_at TIMESTAMPTZ
);

CREATE INDEX idx_society_disputes_society ON society_disputes(society_id);
CREATE INDEX idx_society_disputes_status ON society_disputes(status);

-- ============================================================
-- CIVILIZATION GOVERNANCE REVIEWS
-- ============================================================

-- Reviews at each level for promotion/demotion decisions
CREATE TABLE IF NOT EXISTS civilization_governance_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    civilization_id UUID REFERENCES civilization_entities(id),
    target_entity_type entity_type,
    target_entity_id UUID REFERENCES civilization_entities(id),
    target_type TEXT, -- knowledge_item|learning_event|artifact|promotion_decision
    target_id UUID,
    review_type TEXT,
    decision TEXT NOT NULL,
    reviewer_entity_id UUID REFERENCES civilization_entities(id),
    reason TEXT,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_civilization_governance_reviews_target ON civilization_governance_reviews(target_entity_type, target_entity_id);

-- ============================================================
-- EXTENDED TABLES FOR CIVILIZATION SCOPE
-- ============================================================

-- Add civilization columns to replay_batches
ALTER TABLE IF EXISTS replay_batches ADD COLUMN IF NOT EXISTS learning_level learning_level DEFAULT 'agent';
ALTER TABLE IF EXISTS replay_batches ADD COLUMN IF NOT EXISTS agent_id UUID REFERENCES civilization_entities(id);
ALTER TABLE IF EXISTS replay_batches ADD COLUMN IF NOT EXISTS team_id UUID REFERENCES civilization_entities(id);
ALTER TABLE IF EXISTS replay_batches ADD COLUMN IF NOT EXISTS institution_id UUID REFERENCES civilization_entities(id);
ALTER TABLE IF EXISTS replay_batches ADD COLUMN IF NOT EXISTS society_id UUID REFERENCES civilization_entities(id);
ALTER TABLE IF EXISTS replay_batches ADD COLUMN IF NOT EXISTS civilization_id UUID REFERENCES civilization_entities(id);
ALTER TABLE IF EXISTS replay_batches ADD COLUMN IF NOT EXISTS governance_required BOOLEAN DEFAULT false;
ALTER TABLE IF EXISTS replay_batches ADD COLUMN IF NOT EXISTS promotion_scope learning_level;

CREATE INDEX IF NOT EXISTS idx_replay_batches_learning_level ON replay_batches(learning_level);
CREATE INDEX IF NOT EXISTS idx_replay_batches_entity ON replay_batches(agent_id, team_id, institution_id, society_id);

-- Add civilization columns to learner_runs
ALTER TABLE IF EXISTS learner_runs ADD COLUMN IF NOT EXISTS learning_level learning_level DEFAULT 'agent';
ALTER TABLE IF EXISTS learner_runs ADD COLUMN IF NOT EXISTS target_entity_id UUID REFERENCES civilization_entities(id);
ALTER TABLE IF EXISTS learner_runs ADD COLUMN IF NOT EXISTS target_entity_type entity_type;
ALTER TABLE IF EXISTS learner_runs ADD COLUMN IF NOT EXISTS institutional_review_required BOOLEAN DEFAULT false;
ALTER TABLE IF EXISTS learner_runs ADD COLUMN IF NOT EXISTS society_review_required BOOLEAN DEFAULT false;
ALTER TABLE IF EXISTS learner_runs ADD COLUMN IF NOT EXISTS civilization_review_required BOOLEAN DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_learner_runs_learning_level ON learner_runs(learning_level);

-- Add civilization columns to learner_candidates
ALTER TABLE IF EXISTS learner_candidates ADD COLUMN IF NOT EXISTS learning_level learning_level DEFAULT 'agent';
ALTER TABLE IF EXISTS learner_candidates ADD COLUMN IF NOT EXISTS target_entity_type entity_type;
ALTER TABLE IF EXISTS learner_candidates ADD COLUMN IF NOT EXISTS target_entity_id UUID REFERENCES civilization_entities(id);
ALTER TABLE IF EXISTS learner_candidates ADD COLUMN IF NOT EXISTS promotion_scope learning_level;
ALTER TABLE IF EXISTS learner_candidates ADD COLUMN IF NOT EXISTS review_required_by_entity_type entity_type;

CREATE INDEX IF NOT EXISTS idx_learner_candidates_learning_level ON learner_candidates(learning_level);

-- Add civilization columns to simulator_runs
ALTER TABLE IF EXISTS simulator_runs ADD COLUMN IF NOT EXISTS learning_level learning_level DEFAULT 'agent';
ALTER TABLE IF EXISTS simulator_runs ADD COLUMN IF NOT EXISTS emitting_entity_type entity_type;
ALTER TABLE IF EXISTS simulator_runs ADD COLUMN IF NOT EXISTS emitting_entity_id UUID REFERENCES civilization_entities(id);

-- Add civilization columns to self_modification_requests
ALTER TABLE IF EXISTS self_modification_requests ADD COLUMN IF NOT EXISTS requester_entity_type entity_type;
ALTER TABLE IF EXISTS self_modification_requests ADD COLUMN IF NOT EXISTS requester_entity_id UUID REFERENCES civilization_entities(id);
ALTER TABLE IF EXISTS self_modification_requests ADD COLUMN IF NOT EXISTS target_entity_type entity_type;
ALTER TABLE IF EXISTS self_modification_requests ADD COLUMN IF NOT EXISTS target_entity_id UUID REFERENCES civilization_entities(id);
ALTER TABLE IF EXISTS self_modification_requests ADD COLUMN IF NOT EXISTS learning_level learning_level;
ALTER TABLE IF EXISTS self_modification_requests ADD COLUMN IF NOT EXISTS promotion_scope learning_level;

-- Add civilization columns to artifact_registry
ALTER TABLE IF EXISTS artifact_registry ADD COLUMN IF NOT EXISTS learning_level learning_level DEFAULT 'agent';
ALTER TABLE IF EXISTS artifact_registry ADD COLUMN IF NOT EXISTS owner_entity_type entity_type;
ALTER TABLE IF EXISTS artifact_registry ADD COLUMN IF NOT EXISTS owner_entity_id UUID REFERENCES civilization_entities(id);
ALTER TABLE IF EXISTS artifact_registry ADD COLUMN IF NOT EXISTS promotion_scope learning_level;
ALTER TABLE IF EXISTS artifact_registry ADD COLUMN IF NOT EXISTS governance_decision_id UUID REFERENCES civilization_governance_reviews(id);

CREATE INDEX IF NOT EXISTS idx_artifact_registry_learning_level ON artifact_registry(learning_level);

-- Add civilization columns to canary_plans
ALTER TABLE IF EXISTS canary_plans ADD COLUMN IF NOT EXISTS learning_level learning_level DEFAULT 'agent';
ALTER TABLE IF EXISTS canary_plans ADD COLUMN IF NOT EXISTS governance_scope entity_type;
ALTER TABLE IF EXISTS canary_plans ADD COLUMN IF NOT EXISTS governance_entity_id UUID REFERENCES civilization_entities(id);

-- Add civilization columns to rollback_events
ALTER TABLE IF EXISTS rollback_events ADD COLUMN IF NOT EXISTS learning_level learning_level DEFAULT 'agent';
ALTER TABLE IF EXISTS rollback_events ADD COLUMN IF NOT EXISTS governance_scope entity_type;

-- ============================================================
-- VIEWS AND LINEAGE
-- ============================================================

-- View: complete learning lineage from agent to civilization
CREATE VIEW civilization_learning_lineage AS
    SELECT
        cle.id as learning_event_id,
        cle.learning_level,
        ce_agent.name as agent_name,
        ce_team.name as team_name,
        ce_institution.name as institution_name,
        ce_society.name as society_name,
        ce_civilization.name as civilization_name,
        cle.source_type,
        cle.event_type,
        cle.simulation_derived,
        cle.requires_review,
        cle.review_required_by_entity_type,
        cle.trace_id,
        cle.created_at
    FROM civilization_learning_events cle
    LEFT JOIN civilization_entities ce_agent ON cle.agent_id = ce_agent.id
    LEFT JOIN civilization_entities ce_team ON cle.team_id = ce_team.id
    LEFT JOIN civilization_entities ce_institution ON cle.institution_id = ce_institution.id
    LEFT JOIN civilization_entities ce_society ON cle.society_id = ce_society.id
    LEFT JOIN civilization_entities ce_civilization ON cle.civilization_id = ce_civilization.id;

-- View: promotion gates by entity level
CREATE VIEW promotion_gates AS
    SELECT
        'agent' as source_level,
        'team' as target_level,
        true as can_self_promote,
        false as requires_parent_review
    UNION ALL
    SELECT 'team', 'institution', false, true
    UNION ALL
    SELECT 'institution', 'society', false, true
    UNION ALL
    SELECT 'society', 'civilization', false, true
    UNION ALL
    SELECT 'agent', 'institution', false, true
    UNION ALL
    SELECT 'team', 'society', false, true
    UNION ALL
    SELECT 'institution', 'civilization', false, true;

-- ============================================================
-- IMMUTABILITY AND AUDIT
-- ============================================================

DROP TRIGGER IF EXISTS civilization_learning_events_immutable ON civilization_learning_events;
CREATE TRIGGER civilization_learning_events_immutable
    BEFORE UPDATE ON civilization_learning_events
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('civilization_learning_events');

DROP TRIGGER IF EXISTS institutional_knowledge_items_immutable_on_promotion ON institutional_knowledge_items;
CREATE TRIGGER institutional_knowledge_items_immutable_on_promotion
    BEFORE UPDATE ON institutional_knowledge_items
    FOR EACH ROW
    WHEN (OLD.status = 'promoted' OR NEW.status = 'promoted')
    EXECUTE FUNCTION raise_immutability_violation('institutional_knowledge_items promoted state');

DROP TRIGGER IF EXISTS society_disputes_immutable_when_resolved ON society_disputes;
CREATE TRIGGER society_disputes_immutable_when_resolved
    BEFORE UPDATE ON society_disputes
    FOR EACH ROW
    WHEN (OLD.status = 'resolved' OR NEW.status = 'resolved')
    EXECUTE FUNCTION raise_immutability_violation('society_disputes resolved state');

DROP TRIGGER IF EXISTS civilization_governance_reviews_immutable ON civilization_governance_reviews;
CREATE TRIGGER civilization_governance_reviews_immutable
    BEFORE UPDATE ON civilization_governance_reviews
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('civilization_governance_reviews');
