-- Migration 052: Add HTTP Endpoint Support for Specialist Agents
-- Tracks HTTP server endpoints, process IDs, and ports for specialist agents

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'autonomy_team_activations' AND column_name = 'http_endpoint'
  ) THEN
    ALTER TABLE autonomy_team_activations ADD COLUMN http_endpoint VARCHAR(100);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'autonomy_team_activations' AND column_name = 'process_pid'
  ) THEN
    ALTER TABLE autonomy_team_activations ADD COLUMN process_pid INT;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'autonomy_team_activations' AND column_name = 'port_number'
  ) THEN
    ALTER TABLE autonomy_team_activations ADD COLUMN port_number INT;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_team_activations_http_endpoint ON autonomy_team_activations(http_endpoint);
CREATE INDEX IF NOT EXISTS idx_team_activations_process_pid ON autonomy_team_activations(process_pid);
