-- Migration 052: Add HTTP Endpoint Support for Specialist Agents
-- Tracks HTTP server endpoints, process IDs, and ports for specialist agents

ALTER TABLE autonomy_team_activations
ADD COLUMN http_endpoint VARCHAR(100),
ADD COLUMN process_pid INT,
ADD COLUMN port_number INT;

CREATE INDEX idx_team_activations_http_endpoint ON autonomy_team_activations(http_endpoint);
CREATE INDEX idx_team_activations_process_pid ON autonomy_team_activations(process_pid);
