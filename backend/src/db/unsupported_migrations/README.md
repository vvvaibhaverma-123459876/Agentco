# Unsupported Migration Archive

Files in this directory are historical or future schema drafts. They are not part of the active migration chain and are not applied by `npm run db:migrate`.

Rules:

- Do not import these files from the migration runner.
- Do not cite these schemas as implemented capability.
- To enable one, move it back to `backend/src/db/migrations/`, reconcile it with the current schema, and add integration tests proving the routes/services that depend on it work.

