ALTER TABLE trajectory_store
  ADD COLUMN IF NOT EXISTS is_successful BOOLEAN NOT NULL DEFAULT false;
