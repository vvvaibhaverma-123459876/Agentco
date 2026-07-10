\set ON_ERROR_STOP on

-- Prepare the least-privilege role used by `make release-gate`.
--
-- Required psql variables:
--   gate_role      role name to create/update
--   gate_password  login password for that role
--
-- Run this after migrations with a schema-owning/admin connection:
--   psql "$RELEASE_GATE_SETUP_DATABASE_URL" \
--     -v gate_role=agentco_gate \
--     -v gate_password=... \
--     -f scripts/setup_release_gate_role.sql

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'gate_role', :'gate_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'gate_role')
\gexec

SELECT format('ALTER ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION', :'gate_role', :'gate_password')
\gexec

SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'gate_role')
\gexec

GRANT USAGE ON SCHEMA public TO :"gate_role";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO :"gate_role";
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO :"gate_role";

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"gate_role";

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO :"gate_role";

SELECT format(
  'CREATE POLICY agent_memory_%I_gate_access ON agent_memory FOR ALL TO %I USING (true) WITH CHECK (true)',
  :'gate_role',
  :'gate_role'
)
WHERE to_regclass('public.agent_memory') IS NOT NULL
  AND NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'agent_memory'
      AND policyname = format('agent_memory_%s_gate_access', :'gate_role')
  )
\gexec
