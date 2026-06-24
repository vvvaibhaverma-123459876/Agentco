import { db } from '../db/client';

export interface ImpactAssessment {
  id: string;
  change_request_id?: string;
  policy_id?: string;
  assessment_type: string;
  baseline_policy_id?: string;
  calibration_regression: number;
  confidence_shift: number;
  false_positive_impact: number;
  false_negative_impact: number;
  reputation_impact: number;
  dispute_impact: number;
  simulation_leakage_risk: number;
  safety_threshold_compliance: number;
  rollback_feasibility: number;
  audit_completeness: number;
  recommendation: string;
  recommendation_confidence: number;
  supporting_evidence_json: Record<string, any>;
  blocking_issues: string[];
  warnings: string[];
  created_at: Date;
}

export interface AssessmentMetrics {
  calibration_regression: number;
  confidence_shift: number;
  false_positive_impact: number;
  false_negative_impact: number;
  reputation_impact: number;
  dispute_impact: number;
  simulation_leakage_risk: number;
  safety_threshold_compliance: number;
  rollback_feasibility: number;
  audit_completeness: number;
}

export class TrustImpactAssessmentService {
  /**
   * Create a new impact assessment
   */
  async createAssessment(
    policyIdOrChangeRequestId: string,
    assessmentType: string,
    metrics: AssessmentMetrics,
    baselinePolicyId?: string,
    supportingEvidence?: Record<string, any>
  ): Promise<ImpactAssessment> {
    // Determine if this is a policy or change request assessment
    const isPolicy = assessmentType.includes('policy');
    const policyId = isPolicy ? policyIdOrChangeRequestId : null;
    const changeRequestId = !isPolicy ? policyIdOrChangeRequestId : null;

    // Produce recommendation based on metrics
    const recommendation = await this.produceRecommendation(metrics);

    // Calculate recommendation confidence (0-1)
    const confidence = this.calculateRecommendationConfidence(metrics);

    // Detect blocking issues
    const blockingIssues = this.detectBlockingIssues(metrics);

    // Detect warnings
    const warnings = this.detectWarnings(metrics);

    const result = await db.query(
      `INSERT INTO trust_impact_assessments (
        change_request_id, policy_id, assessment_type, baseline_policy_id,
        calibration_regression, confidence_shift, false_positive_impact,
        false_negative_impact, reputation_impact, dispute_impact,
        simulation_leakage_risk, safety_threshold_compliance,
        rollback_feasibility, audit_completeness,
        recommendation, recommendation_confidence, supporting_evidence_json,
        blocking_issues, warnings
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
      RETURNING *`,
      [
        changeRequestId,
        policyId,
        assessmentType,
        baselinePolicyId || null,
        metrics.calibration_regression,
        metrics.confidence_shift,
        metrics.false_positive_impact,
        metrics.false_negative_impact,
        metrics.reputation_impact,
        metrics.dispute_impact,
        metrics.simulation_leakage_risk,
        metrics.safety_threshold_compliance,
        metrics.rollback_feasibility,
        metrics.audit_completeness,
        recommendation,
        confidence,
        JSON.stringify(supportingEvidence || {}),
        blockingIssues,
        warnings
      ]
    );

    return result.rows[0];
  }

  /**
   * Compare change against baseline policy
   */
  async compareAgainstBaseline(
    policyId: string,
    baselinePolicyId: string
  ): Promise<Partial<AssessmentMetrics>> {
    // Query baseline metrics for the baseline policy
    const baselineResult = await db.query(
      `SELECT metric_name, metric_value FROM baseline_metrics
       WHERE policy_id = $1
       ORDER BY measurement_timestamp DESC`,
      [baselinePolicyId]
    );

    const baselineMetrics: Record<string, number> = {};
    for (const row of baselineResult.rows) {
      baselineMetrics[row.metric_name] = row.metric_value;
    }

    // For now, return default comparison (in production, would evaluate new policy)
    return {
      calibration_regression: 0.0, // No regression (best case)
      confidence_shift: 0.0,
      false_positive_impact: 0.0,
      false_negative_impact: 0.0,
      reputation_impact: 0.0,
      dispute_impact: 0.0,
      simulation_leakage_risk: 0.0,
      safety_threshold_compliance: 1.0,
      rollback_feasibility: 1.0,
      audit_completeness: 1.0
    };
  }

  /**
   * Run calibration regression evaluation
   */
  async runCalibrationRegressionEval(policyId: string): Promise<number> {
    // Query recent eval results for policy
    const result = await db.query(
      `SELECT calibration_regression FROM trust_impact_assessments
       WHERE policy_id = $1 AND assessment_type = 'calibration_eval'
       ORDER BY created_at DESC
       LIMIT 1`,
      [policyId]
    );

    if (result.rows.length > 0) {
      return result.rows[0].calibration_regression;
    }

    // No prior assessments, assume no regression
    return 0.0;
  }

  /**
   * Assess reputation impact of proposed change
   */
  async assessReputationImpact(policyId: string): Promise<number> {
    // Query trust reputation ledger (if it exists) for expected impact
    // For now, return neutral impact
    return 0.0;
  }

  /**
   * Assess dispute impact
   */
  async assessDisputeImpact(policyId: string): Promise<number> {
    // Query society disputes to assess if change would reduce/increase disputes
    // For now, return neutral impact
    return 0.0;
  }

  /**
   * Assess simulation leakage risk
   */
  async assessSimulationLeakageRisk(policyId: string): Promise<number> {
    // Check if policy would allow simulation-derived claims to affect real-world
    // For now, return low risk (0.0 = no leakage)
    return 0.0;
  }

  /**
   * Produce recommendation based on metrics
   */
  async produceRecommendation(metrics: AssessmentMetrics): Promise<string> {
    // Calculate composite score
    const score =
      (1.0 - Math.abs(metrics.calibration_regression)) * 0.20 +
      (1.0 - Math.abs(metrics.confidence_shift)) * 0.15 +
      (1.0 - metrics.false_positive_impact) * 0.10 +
      (1.0 - metrics.false_negative_impact) * 0.10 +
      (1.0 - Math.abs(metrics.reputation_impact)) * 0.10 +
      (1.0 - Math.abs(metrics.dispute_impact)) * 0.10 +
      (1.0 - metrics.simulation_leakage_risk) * 0.05 +
      metrics.safety_threshold_compliance * 0.10 +
      metrics.rollback_feasibility * 0.05 +
      metrics.audit_completeness * 0.05;

    // Detect blocking issues
    const blockingCount = this.detectBlockingIssues(metrics).length;

    // Produce recommendation
    if (blockingCount > 0) {
      return 'block';
    } else if (score < 0.70) {
      return 'require_human_review';
    } else if (score < 0.85) {
      return 'require_revision';
    } else if (metrics.simulation_leakage_risk > 0.05) {
      return 'sandbox_only';
    } else {
      return 'approve_for_canary';
    }
  }

  /**
   * Get assessment by ID
   */
  async getById(assessmentId: string): Promise<ImpactAssessment | null> {
    const result = await db.query(
      `SELECT * FROM trust_impact_assessments WHERE id = $1`,
      [assessmentId]
    );

    return result.rows[0] || null;
  }

  /**
   * Get assessments for a policy
   */
  async getAssessmentsForPolicy(policyId: string): Promise<ImpactAssessment[]> {
    const result = await db.query(
      `SELECT * FROM trust_impact_assessments
       WHERE policy_id = $1
       ORDER BY created_at DESC`,
      [policyId]
    );

    return result.rows;
  }

  /**
   * Get assessments for a change request
   */
  async getAssessmentsForChangeRequest(changeRequestId: string): Promise<ImpactAssessment[]> {
    const result = await db.query(
      `SELECT * FROM trust_impact_assessments
       WHERE change_request_id = $1
       ORDER BY created_at DESC`,
      [changeRequestId]
    );

    return result.rows;
  }

  /**
   * Record baseline metrics for a policy
   */
  async recordBaselineMetrics(
    policyId: string,
    metrics: Record<string, number>,
    timestamp?: Date
  ): Promise<void> {
    const measurementTime = timestamp || new Date();

    for (const [metricName, metricValue] of Object.entries(metrics)) {
      await db.query(
        `INSERT INTO baseline_metrics (policy_id, metric_name, metric_value, measurement_timestamp)
         VALUES ($1, $2, $3, $4)`,
        [policyId, metricName, metricValue, measurementTime]
      );
    }
  }

  /**
   * Get latest baseline metrics for a policy
   */
  async getLatestBaselineMetrics(policyId: string): Promise<Record<string, number>> {
    const result = await db.query(
      `SELECT metric_name, metric_value FROM baseline_metrics
       WHERE policy_id = $1
       ORDER BY measurement_timestamp DESC`,
      [policyId]
    );

    const metrics: Record<string, number> = {};
    for (const row of result.rows) {
      metrics[row.metric_name] = row.metric_value;
    }

    return metrics;
  }

  /**
   * Assess whether a policy can be promoted to canary
   */
  async canPromoteToCanary(assessmentId: string): Promise<boolean> {
    const assessment = await this.getById(assessmentId);
    if (!assessment) {
      return false;
    }

    // Can promote if recommendation is approve_for_canary or sandbox_only
    return assessment.recommendation === 'approve_for_canary' || assessment.recommendation === 'sandbox_only';
  }

  /**
   * Calculate recommendation confidence (0-1)
   */
  private calculateRecommendationConfidence(metrics: AssessmentMetrics): number {
    // Confidence is higher when metrics are extreme (all good or all bad)
    // Lower when metrics are mixed

    const values = [
      1.0 - Math.abs(metrics.calibration_regression),
      1.0 - Math.abs(metrics.confidence_shift),
      1.0 - metrics.false_positive_impact,
      1.0 - metrics.false_negative_impact,
      1.0 - Math.abs(metrics.reputation_impact),
      1.0 - Math.abs(metrics.dispute_impact),
      1.0 - metrics.simulation_leakage_risk,
      metrics.safety_threshold_compliance,
      metrics.rollback_feasibility,
      metrics.audit_completeness
    ];

    // Calculate standard deviation to measure consistency
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const variance = values.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / values.length;
    const stdDev = Math.sqrt(variance);

    // Confidence: high consistency = high confidence
    return 1.0 - stdDev;
  }

  /**
   * Detect blocking issues
   */
  private detectBlockingIssues(metrics: AssessmentMetrics): string[] {
    const issues: string[] = [];

    if (metrics.calibration_regression > 0.05) {
      issues.push('Calibration regression exceeds 5% threshold');
    }

    if (metrics.safety_threshold_compliance < 0.95) {
      issues.push('Safety threshold compliance below 95%');
    }

    if (metrics.rollback_feasibility < 0.80) {
      issues.push('Rollback feasibility below 80%');
    }

    if (metrics.simulation_leakage_risk > 0.10) {
      issues.push('Simulation leakage risk exceeds 10%');
    }

    if (metrics.false_positive_impact > 0.20) {
      issues.push('False positive impact exceeds 20%');
    }

    if (metrics.false_negative_impact > 0.20) {
      issues.push('False negative impact exceeds 20%');
    }

    return issues;
  }

  /**
   * Detect warnings
   */
  private detectWarnings(metrics: AssessmentMetrics): string[] {
    const warnings: string[] = [];

    if (metrics.calibration_regression > 0.02) {
      warnings.push('Calibration regression detected (>2%)');
    }

    if (Math.abs(metrics.confidence_shift) > 0.05) {
      warnings.push('Significant confidence shift detected (>5%)');
    }

    if (metrics.simulation_leakage_risk > 0.05) {
      warnings.push('Simulation leakage risk present (>5%)');
    }

    if (metrics.reputation_impact < -0.10) {
      warnings.push('Potential reputation decrease (>10%)');
    }

    if (metrics.dispute_impact > 0.10) {
      warnings.push('Potential dispute increase (>10%)');
    }

    if (metrics.audit_completeness < 0.95) {
      warnings.push('Audit completeness below 95%');
    }

    return warnings;
  }
}

export const trustImpactAssessmentService = new TrustImpactAssessmentService();
