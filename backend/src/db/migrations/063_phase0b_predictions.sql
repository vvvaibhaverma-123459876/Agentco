-- Phase 0b: Calibration Pre-Registration
-- Track predictions with confidences, then resolve against actual outcomes
-- Used to compute Brier score and calibration curves

CREATE TABLE IF NOT EXISTS predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prediction_id VARCHAR(100) UNIQUE NOT NULL,
  category VARCHAR(100) NOT NULL,  -- e.g., "autonomy_completion", "evidence_quality"
  description TEXT NOT NULL,        -- human-readable prediction statement
  confidence NUMERIC(3,2) NOT NULL, -- 0.00 to 1.00
  expected_resolution_by TIMESTAMP NOT NULL,
  hypothesis VARCHAR(500),          -- optional: reasoning behind confidence
  created_at TIMESTAMP DEFAULT NOW(),
  created_by VARCHAR(100)           -- who/what registered this prediction
);

CREATE TABLE IF NOT EXISTS prediction_resolutions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prediction_id VARCHAR(100) NOT NULL,
  outcome BOOLEAN NOT NULL,         -- true if prediction was correct
  actual_value VARCHAR(500),        -- what the actual measured value was
  measurement_method TEXT,          -- how was it measured (query, test, manual)
  resolved_at TIMESTAMP NOT NULL,
  brier_component NUMERIC(5,4),     -- (confidence - outcome)^2, computed on resolution
  created_at TIMESTAMP DEFAULT NOW(),

  CONSTRAINT fk_prediction FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id)
);

-- Index for queries
CREATE INDEX IF NOT EXISTS idx_predictions_category ON predictions(category);
CREATE INDEX IF NOT EXISTS idx_predictions_created ON predictions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_prediction_resolutions_prediction ON prediction_resolutions(prediction_id);
CREATE INDEX IF NOT EXISTS idx_prediction_resolutions_resolved ON prediction_resolutions(resolved_at DESC);

-- View for Brier score computation
CREATE OR REPLACE VIEW prediction_calibration_stats AS
SELECT
  COUNT(DISTINCT pr.prediction_id) as total_predictions,
  COUNT(CASE WHEN pr.outcome = true THEN 1 END) as correct,
  ROUND((COUNT(CASE WHEN pr.outcome = true THEN 1 END)::NUMERIC / COUNT(*))::NUMERIC, 3) as accuracy,
  ROUND(AVG(pr.brier_component)::NUMERIC, 4) as avg_brier_score,
  ROUND(AVG(p.confidence)::NUMERIC, 3) as avg_confidence
FROM predictions p
LEFT JOIN prediction_resolutions pr ON p.prediction_id = pr.prediction_id
WHERE pr.resolved_at IS NOT NULL;
