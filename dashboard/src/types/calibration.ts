/**
 * TypeScript types for the Governor Calibration Dashboard (Phase 5).
 * 7 panels: Prediction Ledger, Trust Scores, Firewall Status, Surprise Register,
 * Decay Status, Self-Audit, Spot-Audit Interface.
 */

export type ValidationStatus = "provisional" | "simulation_supported" | "reality_validated" | "retired";
export type HorizonClass = "short" | "medium" | "long";
export type RiskLevel = "low" | "medium" | "high" | "critical";

// Panel 1 — Prediction Ledger
export interface PredictionRecord {
  prediction_id: string;
  claim: string;
  probability: number;
  producing_agent_id: string;
  producing_prompt_version: string;
  domain: string;
  claim_type: string;
  horizon_class: HorizonClass;
  ground_truth_source: string;
  resolution_date: string;
  created_at: string;
  resolved: boolean;
  resolved_outcome: boolean | null;
  resolved_at: string | null;
  brier_score: number | null;
  log_score: number | null;
  was_surprise: boolean;
  post_hoc: boolean;
}

// Panel 2 — Trust Scores
export interface TrustScore {
  subject_id: string;
  subject_type: string;
  domain: string;
  claim_type: string;
  horizon_class: HorizonClass;
  n_resolved: number;
  brier_mean: number | null;
  ece: number | null;
  trust_factor: number;         // 0–1; this multiplies stated confidence
  force_downgrade: boolean;
  computed_at: string;
}

// Panel 3 — Firewall Status
export interface BeliefStatus {
  belief_id: string;
  statement: string;
  origin: string;
  validation_status: ValidationStatus;
  sim_support_count: number;    // displayed for transparency; not a promotion gate
  reality_validated_predictions: string[];
  promoted_at: string | null;
  created_at: string;
}

// Panel 4 — Surprise Register
export interface SurpriseEvent {
  surprise_id: string;
  prediction_id: string;
  producing_agent_id: string;
  stated_probability: number;
  actual_outcome: boolean;
  surprise_score: number;
  domain: string;
  claim_type: string;
  horizon_class: HorizonClass;
  registered_at: string;
  investigated: boolean;
  investigation_notes: string;
}

// Panel 5 — Decay Status
export interface DecayStatus {
  belief_id: string;
  statement: string;
  domain: string;
  validation_status: ValidationStatus;
  promoted_at: string | null;
  days_until_expiry: number;
  half_life_days: number;
  warning: boolean;   // True when days_until_expiry < 7
}

// Panel 6 — Self-Audit Report
export interface SelfAuditReport {
  generated_at: string;
  self_prediction_count: number;
  self_predictions_resolved: number;
  self_ece: number | null;
  stated_blind_spot_limit: string;
  recent_surprises: Array<{
    id: string;
    agent: string;
    domain: string;
    score: number;
    at: string;
    investigated: boolean;
  }>;
  trust_score_trend: "improving" | "stable" | "degrading";
  spot_audit_ready: boolean;   // always true
  human_spot_audit_log: SpotAuditRecord[];
}

// Panel 7 — Spot-Audit Interface
export interface SpotAuditRecord {
  audit_id: string;
  auditor_id: string;
  conducted_at: string;
  passed: boolean;
  findings: string;
  prediction_sample_ids: string[];
}

export interface SpotAuditRequest {
  auditor_id: string;
  prediction_sample_ids: string[];  // randomly sampled by system; governor cannot pre-select
  findings: string;
  passed: boolean;
}

// Calibration Dashboard state
export interface CalibrationDashboardState {
  ledger_summary: {
    total: number;
    resolved: number;
    pending: number;
    post_hoc_flagged: number;
    surprises: number;
  };
  trust_summary: {
    agents_tracked: number;
    agents_degraded: number;      // trust_factor < 0.5
    agents_force_downgraded: number;
    overall_brier_mean: number | null;
    overall_ece: number | null;
  };
  firewall_summary: {
    total_beliefs: number;
    provisional: number;
    simulation_supported: number;
    reality_validated: number;
    quarantined: number;
  };
  surprise_summary: {
    total: number;
    uninvestigated: number;
  };
  last_updated: string;
}
