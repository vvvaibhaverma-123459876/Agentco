import { db } from '../db/client';
import { calibrationChangeGovernanceService } from './calibration-change-governance.service';

export interface DriftEvent {
  id: string;
  drift_type: string;
  severity: 'normal' | 'warning' | 'severe' | 'critical';
  baseline_value: number;
  observed_value: number;
  drift_magnitude: number;
  threshold_value: number;
  detection_method: string;
  affected_entity_type?: string;
  affected_entity_id?: string;
  proposed_change_id?: string;
  triggered_emergency_freeze: boolean;
  evidence_json: Record<string, any>;
  trace_id?: string;
  created_at: Date;
  resolved_at?: Date;
}

export interface DriftThreshold {
  id: string;
  drift_type: string;
  warning_threshold: number;
  severe_threshold: number;
  critical_threshold: number;
  requires_emergency_freeze: boolean;
  auto_propose_change: boolean;
  description?: string;
}

export class CalibrationDriftMonitorService {
  /**
   * Detect drift in calibration metrics
   */
  async detectDrift(
    driftType: string,
    baselineValue: number,
    observedValue: number,
    detectionMethod: string,
    affectedEntityType?: string,
    affectedEntityId?: string,
    evidence?: Record<string, any>,
    traceId?: string
  ): Promise<DriftEvent> {
    // Get threshold for this drift type
    const thresholdResult = await db.query(
      `SELECT * FROM drift_thresholds WHERE drift_type = $1`,
      [driftType]
    );

    if (thresholdResult.rows.length === 0) {
      throw new Error(`No threshold configured for drift type: ${driftType}`);
    }

    const threshold = thresholdResult.rows[0];

    // Calculate drift magnitude
    const driftMagnitude = Math.abs(
      baselineValue === 0 ? observedValue : (observedValue - baselineValue) / baselineValue
    );

    // Determine severity
    let severity: 'normal' | 'warning' | 'severe' | 'critical';
    if (driftMagnitude >= threshold.critical_threshold) {
      severity = 'critical';
    } else if (driftMagnitude >= threshold.severe_threshold) {
      severity = 'severe';
    } else if (driftMagnitude >= threshold.warning_threshold) {
      severity = 'warning';
    } else {
      severity = 'normal';
    }

    // Record drift event
    const result = await db.query(
      `INSERT INTO calibration_drift_events (
        drift_type, severity, baseline_value, observed_value,
        drift_magnitude, threshold_value, detection_method,
        affected_entity_type, affected_entity_id, evidence_json, trace_id
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
      RETURNING *`,
      [
        driftType,
        severity,
        baselineValue,
        observedValue,
        driftMagnitude,
        threshold.severe_threshold,
        detectionMethod,
        affectedEntityType || null,
        affectedEntityId || null,
        JSON.stringify(evidence || {}),
        traceId || null
      ]
    );

    const driftEvent = result.rows[0];

    // Auto-propose change if enabled and severity warrants it
    if (threshold.auto_propose_change && (severity === 'severe' || severity === 'critical')) {
      await this.proposeChange(driftEvent.id, driftType, driftMagnitude);
    }

    // Trigger emergency freeze if critical
    if (severity === 'critical' && threshold.requires_emergency_freeze) {
      await this.triggerEmergencyFreeze(driftEvent.id);
    }

    return driftEvent;
  }

  /**
   * Propose a change to address detected drift
   */
  private async proposeChange(
    driftEventId: string,
    driftType: string,
    driftMagnitude: number
  ): Promise<void> {
    // Map drift types to change types
    const changeTypeMap: Record<string, string> = {
      overconfidence: 'lower_evidence_standard',
      underconfidence: 'raise_evidence_standard',
      resolution_delay: 'update_thresholds',
      evidence_quality_decline: 'update_evidence_standard',
      reputation_drift: 'adjust_reputation_weight',
      dispute_rate_increase: 'update_dispute_rules',
      simulation_leakage_risk: 'update_simulation_discount',
      eval_failure_rate_increase: 'add_eval_case',
      rollback_rate_increase: 'adjust_confidence_discount'
    };

    const changeType = changeTypeMap[driftType] || 'adjust_confidence_discount';

    // Create change request
    const changeRequest = await calibrationChangeGovernanceService.createRequest(
      'calibration-drift-monitor',
      changeType,
      `Auto-proposed change for drift: ${driftType}`,
      {
        drift_type: driftType,
        drift_magnitude: driftMagnitude,
        source: 'calibration_drift_monitor'
      }
    );

    // Link change to drift event
    await db.query(
      `UPDATE calibration_drift_events SET proposed_change_id = $1 WHERE id = $2`,
      [changeRequest.id, driftEventId]
    );
  }

  /**
   * Trigger emergency freeze for critical drift
   */
  private async triggerEmergencyFreeze(driftEventId: string): Promise<void> {
    // Record that this drift triggered freeze
    await db.query(
      `UPDATE calibration_drift_events SET triggered_emergency_freeze = true WHERE id = $1`,
      [driftEventId]
    );

    // In a real system, this would set a global governance flag
    // For now, just record the event
  }

  /**
   * Resolve a drift event
   */
  async resolveDrift(
    driftEventId: string,
    resolutionType: string,
    resolutionChangeId?: string,
    resolvedByEntityId?: string,
    reason?: string
  ): Promise<void> {
    // Record resolution
    await db.query(
      `INSERT INTO drift_resolutions (
        drift_event_id, resolution_type, resolution_change_id,
        resolved_by_entity_id, reason
      ) VALUES ($1, $2, $3, $4, $5)`,
      [driftEventId, resolutionType, resolutionChangeId || null, resolvedByEntityId || null, reason || null]
    );

    // Mark drift as resolved
    await db.query(
      `UPDATE calibration_drift_events SET resolved_at = NOW() WHERE id = $1`,
      [driftEventId]
    );
  }

  /**
   * Get drift event by ID
   */
  async getById(driftEventId: string): Promise<DriftEvent | null> {
    const result = await db.query(
      `SELECT * FROM calibration_drift_events WHERE id = $1`,
      [driftEventId]
    );

    return result.rows[0] || null;
  }

  /**
   * List unresolved drift events
   */
  async listUnresolved(limit: number = 50, offset: number = 0): Promise<DriftEvent[]> {
    const result = await db.query(
      `SELECT * FROM calibration_drift_events
       WHERE resolved_at IS NULL
       ORDER BY created_at DESC, severity DESC
       LIMIT $1 OFFSET $2`,
      [limit, offset]
    );

    return result.rows;
  }

  /**
   * List drift events by severity
   */
  async listBySeverity(
    severity: 'normal' | 'warning' | 'severe' | 'critical',
    limit: number = 50
  ): Promise<DriftEvent[]> {
    const result = await db.query(
      `SELECT * FROM calibration_drift_events
       WHERE severity = $1 AND resolved_at IS NULL
       ORDER BY created_at DESC
       LIMIT $2`,
      [severity, limit]
    );

    return result.rows;
  }

  /**
   * Get critical unresolved drifts from last hour
   */
  async getCriticalDrifts(): Promise<DriftEvent[]> {
    const result = await db.query(
      `SELECT * FROM calibration_drift_events
       WHERE severity = 'critical' AND resolved_at IS NULL
       AND created_at > NOW() - INTERVAL '1 hour'
       ORDER BY created_at DESC`
    );

    return result.rows;
  }

  /**
   * Set or update threshold for drift type
   */
  async setThreshold(
    driftType: string,
    warningThreshold: number,
    severeThreshold: number,
    criticalThreshold: number,
    requiresEmergencyFreeze: boolean = false,
    autoProposChange: boolean = true,
    description?: string
  ): Promise<void> {
    await db.query(
      `INSERT INTO drift_thresholds (
        drift_type, warning_threshold, severe_threshold, critical_threshold,
        requires_emergency_freeze, auto_propose_change, description
      ) VALUES ($1, $2, $3, $4, $5, $6, $7)
      ON CONFLICT (drift_type) DO UPDATE SET
        warning_threshold = EXCLUDED.warning_threshold,
        severe_threshold = EXCLUDED.severe_threshold,
        critical_threshold = EXCLUDED.critical_threshold,
        requires_emergency_freeze = EXCLUDED.requires_emergency_freeze,
        auto_propose_change = EXCLUDED.auto_propose_change,
        description = EXCLUDED.description`,
      [driftType, warningThreshold, severeThreshold, criticalThreshold, requiresEmergencyFreeze, autoProposChange, description || null]
    );
  }

  /**
   * Initialize default thresholds
   */
  async initializeDefaultThresholds(): Promise<void> {
    const thresholds = [
      ['overconfidence', 0.05, 0.10, 0.20, true, true, 'Predicted confidence > actual'],
      ['underconfidence', 0.05, 0.10, 0.20, false, true, 'Predicted confidence < actual'],
      ['resolution_delay', 0.10, 0.25, 0.50, false, true, 'Resolution time increasing'],
      ['evidence_quality_decline', 0.05, 0.15, 0.30, false, true, 'Evidence quality decreasing'],
      ['reputation_drift', 0.10, 0.20, 0.35, false, true, 'Entity reputation drifting'],
      ['dispute_rate_increase', 0.10, 0.25, 0.50, false, true, 'Disputes increasing'],
      ['simulation_leakage_risk', 0.05, 0.10, 0.25, true, true, 'Sim claims affecting reality'],
      ['eval_failure_rate_increase', 0.10, 0.25, 0.50, false, true, 'Eval failures increasing'],
      ['rollback_rate_increase', 0.05, 0.15, 0.30, true, true, 'Rollbacks increasing']
    ];

    for (const [driftType, warning, severe, critical, emergency, propose, description] of thresholds) {
      await this.setThreshold(
        driftType as string,
        warning as number,
        severe as number,
        critical as number,
        emergency as boolean,
        propose as boolean,
        description as string
      );
    }
  }

  /**
   * Get all thresholds
   */
  async getThresholds(): Promise<DriftThreshold[]> {
    const result = await db.query(
      `SELECT * FROM drift_thresholds ORDER BY drift_type`
    );

    return result.rows;
  }

  /**
   * Check if emergency freeze is active (any critical unresolved drift)
   */
  async isEmergencyFreezeActive(): Promise<boolean> {
    const result = await db.query(
      `SELECT COUNT(*) as count FROM calibration_drift_events
       WHERE severity = 'critical' AND resolved_at IS NULL
       AND created_at > NOW() - INTERVAL '1 hour'`
    );

    return result.rows[0].count > 0;
  }
}

export const calibrationDriftMonitorService = new CalibrationDriftMonitorService();
