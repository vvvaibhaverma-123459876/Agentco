-- Repair and harden the resolution_service role after older migrations that
-- swallowed grant failures or granted broader privileges during local tests.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'resolution_service') THEN
        CREATE ROLE resolution_service WITH LOGIN PASSWORD ':RESOLUTION_SERVICE_PASSWORD';
    END IF;
END
$$;

DO $$
BEGIN
    EXECUTE 'GRANT CONNECT ON DATABASE ' || quote_ident(current_database()) || ' TO resolution_service';
END
$$;

GRANT USAGE ON SCHEMA public TO resolution_service;

DO $$
BEGIN
    IF to_regclass('public.prediction_ledger') IS NULL THEN
        RAISE EXCEPTION 'prediction_ledger is required before resolution_service grants can be repaired';
    END IF;

    REVOKE ALL ON TABLE prediction_ledger FROM resolution_service;
    GRANT SELECT, UPDATE ON TABLE prediction_ledger TO resolution_service;
END
$$;

DO $$
BEGIN
    IF to_regclass('public.beliefs') IS NULL THEN
        RAISE EXCEPTION 'beliefs is required before resolution_service grants can be repaired';
    END IF;

    REVOKE ALL ON TABLE beliefs FROM resolution_service;
    GRANT SELECT, UPDATE ON TABLE beliefs TO resolution_service;
END
$$;
