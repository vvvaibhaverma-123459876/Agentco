-- 117: lineage is part of artifact identity (G8)
-- ================================================
-- Bug: artifacts deduplicated on artifact_hash alone. A real-lineage learner
-- candidate whose artifact content matched a previously stored
-- simulation-derived artifact silently adopted that row via
-- ON CONFLICT (artifact_hash), inheriting is_simulation_derived = true.
-- Identical bytes with different provenance are NOT the same artifact.
--
-- Fix: uniqueness becomes (artifact_hash, is_simulation_derived). This is a
-- strictly finer constraint: no previously-valid distinct pair becomes
-- invalid, and content dedup still applies within a lineage class.

ALTER TABLE artifacts
    DROP CONSTRAINT IF EXISTS artifacts_artifact_hash_key;

-- Pre-existing duplicate hashes across lineage classes are impossible under
-- the old UNIQUE(artifact_hash); within a class the old constraint also
-- guaranteed uniqueness, so this index creation cannot fail on legacy data.
CREATE UNIQUE INDEX IF NOT EXISTS artifacts_hash_lineage_key
    ON artifacts (artifact_hash, is_simulation_derived);

COMMENT ON INDEX artifacts_hash_lineage_key IS
    'Artifact identity = content hash + lineage class. Simulation-derived and real artifacts never merge (G8).';
