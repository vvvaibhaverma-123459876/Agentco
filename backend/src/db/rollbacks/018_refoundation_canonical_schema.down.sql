-- Rollback for 018_refoundation_canonical_schema.sql.
-- Drops only additive refoundation tables, in dependency order.

DROP TABLE IF EXISTS benchmark_eval_runs;
DROP TABLE IF EXISTS memory_events;
DROP TABLE IF EXISTS override_cases;
DROP TABLE IF EXISTS action_attestations;
DROP TABLE IF EXISTS calibration_cells;
DROP TABLE IF EXISTS resolutions;
DROP TABLE IF EXISTS sources;
DROP TABLE IF EXISTS evidence_artifacts;

-- claims may pre-exist in older local databases. Do not drop it here.
ALTER TABLE IF EXISTS claims DROP COLUMN IF EXISTS promotion_status;
ALTER TABLE IF EXISTS claims DROP COLUMN IF EXISTS contradiction_set;
ALTER TABLE IF EXISTS claims DROP COLUMN IF EXISTS derived_claims;
ALTER TABLE IF EXISTS claims DROP COLUMN IF EXISTS parent_claims;
ALTER TABLE IF EXISTS claims DROP COLUMN IF EXISTS verification_requirements;
ALTER TABLE IF EXISTS claims DROP COLUMN IF EXISTS expires_at;
ALTER TABLE IF EXISTS claims DROP COLUMN IF EXISTS independence_class;
ALTER TABLE IF EXISTS claims DROP COLUMN IF EXISTS evidence_status;
ALTER TABLE IF EXISTS claims DROP COLUMN IF EXISTS originating_institution;
ALTER TABLE IF EXISTS claims DROP COLUMN IF EXISTS originating_agent;
ALTER TABLE IF EXISTS claims DROP COLUMN IF EXISTS source_uri;
ALTER TABLE IF EXISTS claims DROP COLUMN IF EXISTS source_type;
ALTER TABLE IF EXISTS claims DROP COLUMN IF EXISTS time_horizon;
ALTER TABLE IF EXISTS claims DROP COLUMN IF EXISTS scope;
ALTER TABLE IF EXISTS claims DROP COLUMN IF EXISTS normalized_claim;
ALTER TABLE IF EXISTS claims DROP COLUMN IF EXISTS intent_id;

DROP TABLE IF EXISTS workflow_intents;
DROP TABLE IF EXISTS policies;
DROP TABLE IF EXISTS constitutions;
DROP TABLE IF EXISTS principals;
