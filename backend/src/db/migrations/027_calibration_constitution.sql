-- Migration 027: Calibration Constitution
--
-- The root enforcement mechanism for the civilization calibration & trust governance layer.
-- Constitution defines what changes are allowed and protected surfaces that cannot be modified.
-- All versions are immutable, signed, and hashed for integrity verification.

-- ============================================================
-- CALIBRATION CONSTITUTION TABLES
-- ============================================================

-- Clean slate: drop all tables that may exist from previous migrations
DROP TABLE IF EXISTS constitution_verifications CASCADE;
DROP TABLE IF EXISTS prohibited_change_types CASCADE;
DROP TABLE IF EXISTS allowed_change_types CASCADE;
DROP TABLE IF EXISTS protected_surfaces CASCADE;
DROP TABLE IF EXISTS active_constitution CASCADE;
DROP TABLE IF EXISTS calibration_constitution_versions CASCADE;

CREATE TABLE IF NOT EXISTS calibration_constitution_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_number INT NOT NULL,
    content_json JSONB NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    signature VARCHAR(256) NOT NULL,
    signer_entity_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    retired_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_calibration_constitution_version ON calibration_constitution_versions(version_number);
CREATE INDEX IF NOT EXISTS idx_calibration_constitution_created_at ON calibration_constitution_versions(created_at);

-- Separate table for active constitution to avoid mutation issues
CREATE TABLE IF NOT EXISTS active_constitution (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    constitution_version_id UUID NOT NULL REFERENCES calibration_constitution_versions(id),
    activated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT only_one_active CHECK (id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_active_constitution_version ON active_constitution(constitution_version_id);

-- ============================================================
-- PROTECTED SURFACES TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS protected_surfaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    constitution_id UUID NOT NULL REFERENCES calibration_constitution_versions(id),
    surface_name TEXT NOT NULL,
    surface_type TEXT NOT NULL,
    description TEXT,
    table_names TEXT[],
    column_patterns TEXT[],
    function_patterns TEXT[],
    is_immutable BOOLEAN NOT NULL DEFAULT true,
    requires_constitution_vote BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_protected_surfaces_constitution ON protected_surfaces(constitution_id);
CREATE INDEX IF NOT EXISTS idx_protected_surfaces_type ON protected_surfaces(surface_type);

-- ============================================================
-- ALLOWED CHANGE TYPES TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS allowed_change_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    constitution_id UUID NOT NULL REFERENCES calibration_constitution_versions(id),
    change_type_name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    max_scope entity_type NOT NULL,
    requires_eval BOOLEAN NOT NULL DEFAULT true,
    can_be_canaried BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (constitution_id, change_type_name)
);

CREATE INDEX IF NOT EXISTS idx_allowed_change_types_constitution ON allowed_change_types(constitution_id);

-- ============================================================
-- PROHIBITED CHANGE TYPES TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS prohibited_change_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    constitution_id UUID NOT NULL REFERENCES calibration_constitution_versions(id),
    change_type_name TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (constitution_id, change_type_name)
);

CREATE INDEX IF NOT EXISTS idx_prohibited_change_types_constitution ON prohibited_change_types(constitution_id);

-- ============================================================
-- CONSTITUTION VERIFICATION TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS constitution_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    constitution_id UUID NOT NULL REFERENCES calibration_constitution_versions(id),
    change_request_id UUID,
    verification_result TEXT NOT NULL,
    violations TEXT[],
    is_compliant BOOLEAN NOT NULL,
    verified_by_entity_id UUID,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_constitution_verifications_constitution ON constitution_verifications(constitution_id);
CREATE INDEX IF NOT EXISTS idx_constitution_verifications_result ON constitution_verifications(verification_result);

-- ============================================================
-- IMMUTABILITY TRIGGERS
-- ============================================================

DROP TRIGGER IF EXISTS calibration_constitution_immutable ON calibration_constitution_versions;
CREATE TRIGGER calibration_constitution_immutable
    BEFORE UPDATE ON calibration_constitution_versions
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('calibration_constitution_versions');

DROP TRIGGER IF EXISTS protected_surfaces_immutable ON protected_surfaces;
CREATE TRIGGER protected_surfaces_immutable
    BEFORE UPDATE ON protected_surfaces
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('protected_surfaces');

DROP TRIGGER IF EXISTS allowed_change_types_immutable ON allowed_change_types;
CREATE TRIGGER allowed_change_types_immutable
    BEFORE UPDATE ON allowed_change_types
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('allowed_change_types');

DROP TRIGGER IF EXISTS prohibited_change_types_immutable ON prohibited_change_types;
CREATE TRIGGER prohibited_change_types_immutable
    BEFORE UPDATE ON prohibited_change_types
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('prohibited_change_types');

DROP TRIGGER IF EXISTS constitution_verifications_immutable ON constitution_verifications;
CREATE TRIGGER constitution_verifications_immutable
    BEFORE UPDATE ON constitution_verifications
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('constitution_verifications');

-- Active constitution can be updated (to switch versions) but previous entries remain immutable
DROP TRIGGER IF EXISTS active_constitution_immutable ON active_constitution;
CREATE TRIGGER active_constitution_immutable
    BEFORE DELETE ON active_constitution
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('active_constitution history is immutable');

-- ============================================================
-- CONSTITUTION ENFORCEMENT FUNCTIONS
-- ============================================================

CREATE OR REPLACE FUNCTION get_active_constitution()
RETURNS UUID AS $$
DECLARE
    v_constitution_id UUID;
BEGIN
    SELECT constitution_version_id INTO v_constitution_id
    FROM active_constitution
    ORDER BY activated_at DESC
    LIMIT 1;

    RETURN v_constitution_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION check_change_allowed(
    p_constitution_id UUID,
    p_change_type TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    v_is_prohibited BOOLEAN;
    v_is_allowed BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM prohibited_change_types
        WHERE constitution_id = p_constitution_id
        AND change_type_name = p_change_type
    ) INTO v_is_prohibited;

    IF v_is_prohibited THEN
        RETURN false;
    END IF;

    SELECT EXISTS(
        SELECT 1 FROM allowed_change_types
        WHERE constitution_id = p_constitution_id
        AND change_type_name = p_change_type
    ) INTO v_is_allowed;

    RETURN v_is_allowed;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION check_protected_surface_touched(
    p_constitution_id UUID,
    p_table_name TEXT,
    p_column_name TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    v_touched BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM protected_surfaces ps
        WHERE ps.constitution_id = p_constitution_id
        AND ps.is_immutable = true
        AND (
            p_table_name = ANY(ps.table_names)
            OR (p_column_name IS NOT NULL AND p_column_name ~ ANY(ps.column_patterns))
        )
    ) INTO v_touched;

    RETURN v_touched;
END;
$$ LANGUAGE plpgsql;
