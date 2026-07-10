-- Phase 8 Task 1: bind decision_log serialization version into new hashes.
--
-- Historical rows may have NULL serialization_version. The cutoff below records
-- the chain head at migration time; any later row without a version is invalid.
ALTER TABLE decision_log
  ADD COLUMN IF NOT EXISTS serialization_version TEXT;

CREATE TABLE IF NOT EXISTS decision_log_protocol_cutoff (
  id TEXT PRIMARY KEY,
  cutoff_timestamp TIMESTAMPTZ,
  cutoff_log_id UUID REFERENCES decision_log(log_id) ON DELETE RESTRICT,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO decision_log_protocol_cutoff (id, cutoff_timestamp, cutoff_log_id)
SELECT
  'serialization_version_v3',
  head.timestamp,
  head.log_id
FROM (
  SELECT timestamp, log_id
    FROM decision_log
   WHERE chain_hash ~ '^[0-9a-f]{64}$'
     AND prev_hash ~ '^[0-9a-f]{64}$'
   ORDER BY timestamp DESC, log_id DESC
   LIMIT 1
) AS head
ON CONFLICT (id) DO NOTHING;

INSERT INTO decision_log_protocol_cutoff (id, cutoff_timestamp, cutoff_log_id)
SELECT 'serialization_version_v3', NULL, NULL
WHERE NOT EXISTS (
  SELECT 1 FROM decision_log_protocol_cutoff WHERE id = 'serialization_version_v3'
);

CREATE INDEX IF NOT EXISTS idx_decision_log_serialization_version
  ON decision_log(serialization_version);
