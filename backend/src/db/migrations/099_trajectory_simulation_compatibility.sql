ALTER TABLE trajectory_store
  ADD COLUMN IF NOT EXISTS is_simulation BOOLEAN NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_trajectory_store_is_simulation
  ON trajectory_store(is_simulation);
