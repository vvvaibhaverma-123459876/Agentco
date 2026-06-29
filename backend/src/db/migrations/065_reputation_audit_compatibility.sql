-- Migration 065: Reputation audit compatibility for scale services

ALTER TABLE institutions ADD COLUMN IF NOT EXISTS reputation_score NUMERIC(5, 2) DEFAULT 0.5;

ALTER TABLE reputation_audit_log ADD COLUMN IF NOT EXISTS id VARCHAR(255);
ALTER TABLE reputation_audit_log ADD COLUMN IF NOT EXISTS entity_type VARCHAR(100);
ALTER TABLE reputation_audit_log ADD COLUMN IF NOT EXISTS previous_reputation NUMERIC(5, 2) DEFAULT 0.5;
ALTER TABLE reputation_audit_log ADD COLUMN IF NOT EXISTS new_reputation NUMERIC(5, 2);
ALTER TABLE reputation_audit_log ADD COLUMN IF NOT EXISTS change_reason TEXT;
ALTER TABLE reputation_audit_log ADD COLUMN IF NOT EXISTS audit_timestamp TIMESTAMP DEFAULT NOW();
