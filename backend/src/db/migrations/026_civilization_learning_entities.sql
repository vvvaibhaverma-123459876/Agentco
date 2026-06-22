-- Migration 026: Civilization Learning Entities and Governance
--
-- Implements the five-level civilization hierarchy for learning governance:
-- Agent → Team → Institution → Society → Civilization
--
-- This enables structured learning with promotion gates at each level.

-- ============================================================
-- CIVILIZATION ENTITY TYPES
-- ============================================================

CREATE TYPE entity_type AS ENUM (
    'agent', 'team', 'institution', 'society', 'civilization'
);

CREATE TYPE knowledge_type AS ENUM (
    'prompt_template', 'tool_selection_policy', 'escalation_threshold',
    'coordination_pattern', 'procedure', 'standard', 'review_rule',
    'research_agenda', 'dispute_resolution_policy', 'governance_rule',
    'safety_doctrine', 'constitutional_constraint'
);

CREATE TYPE learning_level AS ENUM (
    'agent', 'team', 'institution', 'society', 'civilization'
);

CREATE TYPE dispute_status AS ENUM (
    'raised', 'under_investigation', 'awaiting_evidence',
    'in_consensus_formation', 'resolved', 'escalated_to_civilization'
);

-- ============================================================
-- CIVILIZATION HIERARCHY TABLES
-- ============================================================

CREATE TABLE civilization_entities (
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
CREATE INDEX idx_civilization_entities_status ON civilization_entities(status);

CREATE TABLE civilization_memberships (
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
-- CIVILIZATION LEARNING EVENTS (IMMUTABLE)
-- ============================================================

CREATE TABLE civilization_learning_events (
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
CREATE INDEX idx_civilization_learning_events_simulation ON civilization_learning_events(simulation_derived);

-- ============================================================
-- INSTITUTIONAL KNOWLEDGE (IMMUTABLE WHEN PROMOTED)
-- ============================================================

CREATE TABLE institutional_knowledge_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_type knowledge_type NOT NULL,
    institution_id UUID REFERENCES civilization_entities(id),
    society_id UUID REFERENCES civilization_entities(id),
    civilization_id UUID REFERENCES civilization_entities(id),
    title TEXT NOT NULL,
    content_json JSONB NOT NULL,
    evidence_refs_json JSONB DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'draft', -- draft|promoted|demoted|retired
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
CREATE INDEX idx_institutional_knowledge_simulation ON institutional_knowledge_items(simulation_derived);

-- ============================================================
-- SOCIETY-LEVEL DISPUTES (IMMUTABLE WHEN RESOLVED)
-- ============================================================

CREATE TABLE society_disputes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    society_id UUID NOT NULL REFERENCES civilization_entities(id),
    claim_or_knowledge_id UUID,
    conflicting_knowledge_id UUID,
    dispute_type TEXT NOT NULL,
    parties_json JSONB DEFAULT '[]'::jsonb,
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
-- CIVILIZATION GOVERNANCE REVIEWS (IMMUTABLE)
-- ============================================================

CREATE TABLE civilization_governance_reviews (
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
CREATE INDEX idx_civilization_governance_reviews_decision ON civilization_governance_reviews(decision);

-- ============================================================
-- IMMUTABILITY TRIGGERS
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
