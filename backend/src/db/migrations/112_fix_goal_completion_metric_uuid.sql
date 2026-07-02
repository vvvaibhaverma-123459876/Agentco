-- Migration 112: repair record_production_metric for databases migrated
-- before 056 was corrected. The function used uuid_generate_v4(), which
-- requires the uuid-ossp extension that is never installed, so the
-- goal-completion metrics trigger failed on every completed goal. Use the
-- built-in gen_random_uuid() like the rest of the schema.

CREATE OR REPLACE FUNCTION record_production_metric(
  p_metric_type VARCHAR(100),
  p_metric_name VARCHAR(255),
  p_metric_value NUMERIC,
  p_institution_id VARCHAR(36) DEFAULT NULL
)
RETURNS VARCHAR(36) AS $$
DECLARE
  v_metric_id VARCHAR(36);
BEGIN
  v_metric_id := gen_random_uuid()::VARCHAR(36);

  INSERT INTO production_metrics
    (id, metric_type, metric_name, metric_value, institution_id, measured_at)
  VALUES
    (v_metric_id, p_metric_type, p_metric_name, p_metric_value, p_institution_id, CURRENT_TIMESTAMP);

  RETURN v_metric_id;
END;
$$ LANGUAGE plpgsql;
