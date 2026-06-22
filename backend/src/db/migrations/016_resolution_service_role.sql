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
    ELSE
        ALTER ROLE resolution_service WITH LOGIN PASSWORD ':RESOLUTION_SERVICE_PASSWORD';
    END IF;
END
$$;
COMMENT ON ROLE resolution_service IS
    'DB role used by the resolution service to write resolution columns in prediction_ledger '
    '(write-once, time-gated) and to promote beliefs to reality_validated. '
    'Enforces the immutability firewall at the DB layer.';

-- ============================================================================
-- GRANTS: Minimal privilege set for prediction_ledger
-- ============================================================================
-- resolution_service needs:
--   SELECT: to read predictions before/after resolving
--   UPDATE: to set resolution columns (enforced write-once by trigger)
-- It explicitly does NOT need INSERT (predictions come from agents), DELETE (ledger is append-only)

REVOKE ALL ON prediction_ledger FROM resolution_service;
GRANT USAGE ON SCHEMA public TO resolution_service;
GRANT SELECT ON prediction_ledger TO resolution_service;
GRANT UPDATE ON prediction_ledger TO resolution_service;

-- ============================================================================
-- GRANTS: Minimal privilege set for beliefs
-- ============================================================================
-- resolution_service needs:
--   SELECT: to read beliefs before/after promotion
--   UPDATE: to promote beliefs to reality_validated (enforced by trigger on beliefs table)
-- It does NOT need INSERT (beliefs come from simulation) or DELETE (audit trail)

REVOKE ALL ON beliefs FROM resolution_service;
GRANT SELECT ON beliefs TO resolution_service;
GRANT UPDATE ON beliefs TO resolution_service;

-- ============================================================================
<<<<<<< HEAD
-- Test confirmation: migration can be re-run without error
-- ============================================================================
-- The DO block and ALTER ROLE ensure idempotency. If this migration is re-run:
-- 1. The role is created only if missing
-- 2. LOGIN/password settings are refreshed
-- 3. Grants are revoked and re-applied to the minimal required set
=======
-- Test confirmation: migration can be re-run without error.
>>>>>>> agentco-refoundation-codex-loop
