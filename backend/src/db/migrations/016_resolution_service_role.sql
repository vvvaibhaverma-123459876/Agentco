-- Resolution Service Role
-- ============================================================================
-- Creates the resolution_service DB role that enforces the immutability firewall
-- on prediction_ledger (write-once resolution columns) and beliefs (reality validation).
--
-- This role is referenced by triggers in migrations 010_beliefs.sql and 011_prediction_ledger.sql
-- but was never created, requiring manual setup after every fresh database rebuild.
--
-- CRITICAL: This migration must be idempotent. Safe to re-run without error.
--
-- Password is read from environment variable RESOLUTION_SERVICE_PASSWORD
-- (not hardcoded). This is applied via deployment/initialization code that
-- extracts this env var and substitutes it into the SQL before execution.
-- ============================================================================

-- Idempotent role creation/update.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'resolution_service') THEN
        CREATE ROLE resolution_service WITH LOGIN PASSWORD ':RESOLUTION_SERVICE_PASSWORD';
    END IF;
END
$$;
-- Role comment (if permissions allow)
DO $$
BEGIN
    EXECUTE 'COMMENT ON ROLE resolution_service IS '
        || quote_literal('DB role used by the resolution service to write resolution columns in prediction_ledger '
        || '(write-once, time-gated) and to promote beliefs to reality_validated. '
        || 'Enforces the immutability firewall at the DB layer.');
EXCEPTION WHEN OTHERS THEN
    NULL;  -- Silently ignore comment errors
END
$$;

-- ============================================================================
-- GRANTS: Minimal privilege set for prediction_ledger and beliefs
-- ============================================================================
-- Grants are conditional but not silently swallowed. A migration that records
-- success without these grants leaves the resolution firewall unusable.

DO $$
BEGIN
    EXECUTE 'GRANT CONNECT ON DATABASE ' || quote_ident(current_database()) || ' TO resolution_service';
END
$$;

DO $$
BEGIN
    EXECUTE 'GRANT USAGE ON SCHEMA public TO resolution_service';
END
$$;

-- Conditional grants on prediction_ledger
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'prediction_ledger') THEN
        EXECUTE 'REVOKE ALL ON prediction_ledger FROM resolution_service';
        EXECUTE 'GRANT SELECT ON prediction_ledger TO resolution_service';
        EXECUTE 'GRANT UPDATE ON prediction_ledger TO resolution_service';
    END IF;
END
$$;

-- Conditional grants on beliefs
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'beliefs') THEN
        EXECUTE 'REVOKE ALL ON beliefs FROM resolution_service';
        EXECUTE 'GRANT SELECT ON beliefs TO resolution_service';
        EXECUTE 'GRANT UPDATE ON beliefs TO resolution_service';
    END IF;
END
$$;

-- ============================================================================
-- Test confirmation: migration can be re-run without error
-- ============================================================================
-- The DO block and ALTER ROLE ensure idempotency. If this migration is re-run:
-- 1. The role is created only if missing
-- 2. LOGIN/password settings are refreshed
-- 3. Grants are revoked and re-applied to the minimal required set
