-- Migration 017: Advanced Calibration Layer (Phase 1)
--
-- Adds persistent storage for calibrated trust curves, metacalibration scores,
-- structural break detection, domain transfer estimates, and skill/luck analysis.
--
-- Date: 2026-06-20
-- Status: Reversible

CREATE TABLE IF NOT EXISTS calibration_curves_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    domain VARCHAR(255) NOT NULL,
    horizon VARCHAR(50) NOT NULL,
    curve_type VARCHAR(50) DEFAULT 'isotonic',
    n_samples INT DEFAULT 0,
    n_fits INT DEFAULT 0,
    last_fitted_at TIMESTAMP WITH TIME ZONE,
    structural_break_detected BOOLEAN DEFAULT FALSE,
    structural_break_date TIMESTAMP WITH TIME ZONE,
    metacalibration_ece FLOAT,
    metacalibration_interpretation VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, domain, horizon)
);

CREATE TABLE IF NOT EXISTS domain_transfer_estimates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    source_domain VARCHAR(255) NOT NULL,
    target_domain VARCHAR(255) NOT NULL,
    correlation FLOAT NOT NULL,
    point_estimate FLOAT NOT NULL,
    transfer_confidence FLOAT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS skill_luck_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    domain VARCHAR(255) NOT NULL,
    horizon VARCHAR(50) NOT NULL,
    sharpe_ratio FLOAT,
    sharpe_ci_lower FLOAT,
    sharpe_ci_upper FLOAT,
    estimated_skill_fraction FLOAT,
    skill_interpretation VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, domain, horizon)
);

CREATE INDEX IF NOT EXISTS idx_calibration_curves_v2_agent
    ON calibration_curves_v2(agent_id, domain, horizon);

CREATE INDEX IF NOT EXISTS idx_domain_transfer_estimates_agent
    ON domain_transfer_estimates(agent_id, source_domain, target_domain);

CREATE INDEX IF NOT EXISTS idx_skill_luck_analysis_agent
    ON skill_luck_analysis(agent_id, domain, horizon);

-- ============================================================================
-- ROLLBACK
-- ============================================================================
--
-- To rollback this migration:
--
-- DROP INDEX IF EXISTS idx_skill_luck_analysis_agent;
-- DROP INDEX IF EXISTS idx_domain_transfer_estimates_agent;
-- DROP INDEX IF EXISTS idx_calibration_curves_v2_agent;
-- DROP TABLE IF EXISTS skill_luck_analysis;
-- DROP TABLE IF EXISTS domain_transfer_estimates;
-- DROP TABLE IF EXISTS calibration_curves_v2;
