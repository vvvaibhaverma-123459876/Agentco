import { db } from '../db/client';

export interface ReputationEvent {
  id: string;
  entity_type: string;
  entity_id: string;
  event_type: string;
  context: 'real_world' | 'simulation' | 'both';
  impact_value: number;
  impact_confidence: number;
  source_ref?: string;
  source_type?: string;
  evidence_json: Record<string, any>;
  corrects_event_id?: string;
  trace_id?: string;
  created_at: Date;
}

export interface ReputationSnapshot {
  id: string;
  entity_type: string;
  entity_id: string;
  context: 'real_world' | 'simulation' | 'both';
  reputation_score: number;
  event_count: number;
  positive_events: number;
  negative_events: number;
  confidence: number;
  snapshot_timestamp: Date;
  created_at: Date;
}

export class TrustReputationService {
  /**
   * Record a reputation event
   */
  async recordEvent(
    entityType: string,
    entityId: string,
    eventType: string,
    impactValue: number,
    context: 'real_world' | 'simulation' | 'both' = 'real_world',
    sourceRef?: string,
    sourceType?: string,
    evidence?: Record<string, any>,
    traceId?: string
  ): Promise<ReputationEvent> {
    // Clamp impact to -1.0 to 1.0
    const clampedImpact = Math.max(-1.0, Math.min(1.0, impactValue));
    const canonicalEventType = this.toCanonicalEventType(eventType);
    const canonicalSourceRef = this.isUuid(sourceRef) ? sourceRef : undefined;
    const evidenceJson = {
      ...(evidence || {}),
      ...(canonicalEventType !== eventType ? { original_event_type: eventType } : {}),
      ...(sourceRef && !canonicalSourceRef ? { original_source_ref: sourceRef } : {}),
    };

    // Impact confidence is 0.0 to 1.0
    const confidence = Math.max(0.0, Math.min(1.0, Math.abs(clampedImpact)));

    const result = await db.query(
      `INSERT INTO trust_reputation_ledger (
        entity_type, entity_id, event_type, context,
        impact_value, impact_confidence, source_ref, source_type,
        evidence_json, trace_id
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
      RETURNING *`,
      [
        entityType,
        entityId,
        canonicalEventType,
        context,
        clampedImpact,
        confidence,
        canonicalSourceRef || null,
        sourceType || null,
        JSON.stringify(evidenceJson),
        traceId || null
      ]
    );

    return result.rows[0];
  }

  private toCanonicalEventType(eventType: string): string {
    const governanceEventMap: Record<string, string> = {
      promotion_approved_by_governance: 'governance_review_quality',
      promotion_blocked_by_emergency_freeze: 'unsafe_action_blocked',
      promotion_blocked_by_protected_surface: 'protected_surface_violation',
      promotion_blocked_by_trust_policy: 'governance_review_quality',
    };

    return governanceEventMap[eventType] ?? eventType;
  }

  private isUuid(value?: string): boolean {
    return Boolean(
      value &&
        /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)
    );
  }

  /**
   * Record a correction event (never overwrites, only adds)
   */
  async createCorrectionEvent(
    entityType: string,
    entityId: string,
    correctsEventId: string,
    correctionImpactValue: number,
    context: 'real_world' | 'simulation' | 'both' = 'real_world',
    reason?: string,
    traceId?: string
  ): Promise<ReputationEvent> {
    // Create a new event that references the previous event
    const result = await db.query(
      `INSERT INTO trust_reputation_ledger (
        entity_type, entity_id, event_type, context,
        impact_value, impact_confidence, corrects_event_id,
        evidence_json, trace_id
      ) VALUES ($1, $2, 'correction_event', $3, $4, $5, $6, $7, $8)
      RETURNING *`,
      [
        entityType,
        entityId,
        context,
        correctionImpactValue,
        Math.max(0.0, Math.min(1.0, Math.abs(correctionImpactValue))),
        correctsEventId,
        JSON.stringify({ reason: reason || 'Correction event' }),
        traceId || null
      ]
    );

    return result.rows[0];
  }

  /**
   * Compute reputation score for an entity
   */
  async computeReputation(
    entityType: string,
    entityId: string,
    context: 'real_world' | 'simulation' | 'both' = 'real_world'
  ): Promise<number> {
    // Query all events for this entity
    const result = await db.query(
      `SELECT impact_value, (
        SELECT COALESCE(base_weight, 1.0)
        FROM reputation_impact_weights riw
        WHERE riw.event_type = trl.event_type
       ) as weight
       FROM trust_reputation_ledger trl
       WHERE entity_type = $1
       AND entity_id = $2
       AND (context = $3 OR context = 'both')
       AND corrects_event_id IS NULL
       ORDER BY created_at DESC`,
      [entityType, entityId, context]
    );

    if (result.rows.length === 0) {
      return 0.5; // Neutral default
    }

    let totalWeight = 0.0;
    let totalImpact = 0.0;

    for (const row of result.rows) {
      const weight = row.weight || 1.0;
      totalWeight += weight;
      totalImpact += row.impact_value * weight;
    }

    // Normalize to 0-1 range
    const normalizedScore = (totalImpact / totalWeight + 1.0) / 2.0;
    return Math.max(0.0, Math.min(1.0, normalizedScore));
  }

  /**
   * Apply reputation to trust policy weight
   */
  async applyToWeight(
    entityType: string,
    entityId: string,
    baseWeight: number,
    context: 'real_world' | 'simulation' | 'both' = 'real_world'
  ): Promise<number> {
    const reputation = await this.computeReputation(entityType, entityId, context);

    // Weight adjustment: reputation 0.5 = 1.0x, 1.0 = 1.5x, 0.0 = 0.5x
    const weightMultiplier = 0.5 + reputation;

    return baseWeight * weightMultiplier;
  }

  /**
   * Get all events for an entity
   */
  async listEvents(
    entityType: string,
    entityId: string,
    context?: 'real_world' | 'simulation' | 'both',
    limit: number = 50,
    offset: number = 0
  ): Promise<ReputationEvent[]> {
    let query = `
      SELECT * FROM trust_reputation_ledger
      WHERE entity_type = $1 AND entity_id = $2
    `;
    const params: any[] = [entityType, entityId];

    if (context) {
      query += ` AND (context = $3 OR context = 'both')`;
      params.push(context);
    }

    query += ` ORDER BY created_at DESC LIMIT $${params.length + 1} OFFSET $${params.length + 2}`;
    params.push(limit, offset);

    const result = await db.query(query, params);
    return result.rows;
  }

  /**
   * Get reputation snapshot for an entity
   */
  async getLatestSnapshot(
    entityType: string,
    entityId: string,
    context: 'real_world' | 'simulation' | 'both' = 'real_world'
  ): Promise<ReputationSnapshot | null> {
    const result = await db.query(
      `SELECT * FROM reputation_snapshots
       WHERE entity_type = $1 AND entity_id = $2 AND context = $3
       ORDER BY snapshot_timestamp DESC
       LIMIT 1`,
      [entityType, entityId, context]
    );

    return result.rows[0] || null;
  }

  /**
   * Create a new reputation snapshot
   */
  async createSnapshot(
    entityType: string,
    entityId: string,
    context: 'real_world' | 'simulation' | 'both' = 'real_world'
  ): Promise<ReputationSnapshot> {
    // Compute fresh reputation
    const reputation = await this.computeReputation(entityType, entityId, context);

    // Count events
    const countResult = await db.query(
      `SELECT COUNT(*) as total,
              SUM(CASE WHEN impact_value > 0 THEN 1 ELSE 0 END) as positive
       FROM trust_reputation_ledger
       WHERE entity_type = $1 AND entity_id = $2
       AND (context = $3 OR context = 'both')
       AND corrects_event_id IS NULL`,
      [entityType, entityId, context]
    );

    const eventCount = countResult.rows[0].total || 0;
    const positiveCount = countResult.rows[0].positive || 0;
    const negativeCount = eventCount - positiveCount;

    // Calculate confidence (higher with more events)
    const confidence = Math.max(0.5, 1.0 - 1.0 / (eventCount + 1.0));

    // Insert snapshot
    const result = await db.query(
      `INSERT INTO reputation_snapshots (
        entity_type, entity_id, context, reputation_score,
        event_count, positive_events, negative_events, confidence,
        snapshot_timestamp
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
      RETURNING *`,
      [entityType, entityId, context, reputation, eventCount, positiveCount, negativeCount, confidence]
    );

    return result.rows[0];
  }

  /**
   * Get event by ID
   */
  async getEventById(eventId: string): Promise<ReputationEvent | null> {
    const result = await db.query(
      `SELECT * FROM trust_reputation_ledger WHERE id = $1`,
      [eventId]
    );

    return result.rows[0] || null;
  }

  /**
   * Set impact weight for an event type
   */
  async setEventTypeWeight(
    eventType: string,
    baseWeight: number,
    context: 'real_world' | 'simulation' | 'both' = 'both',
    description?: string
  ): Promise<void> {
    await db.query(
      `INSERT INTO reputation_impact_weights (event_type, base_weight, context, description)
       VALUES ($1, $2, $3, $4)
       ON CONFLICT (event_type) DO UPDATE SET base_weight = EXCLUDED.base_weight`,
      [eventType, baseWeight, context, description || null]
    );
  }

  /**
   * Initialize default event type weights
   */
  async initializeDefaultWeights(): Promise<void> {
    const weights = [
      ['accurate_prediction', 0.2, 'real_world', 'Correct predictions increase trust'],
      ['failed_prediction', -0.3, 'real_world', 'Failed predictions decrease trust significantly'],
      ['overconfident_claim', -0.25, 'both', 'Overconfidence damages trust'],
      ['underconfident_correct', 0.1, 'both', 'Conservative correctness is modest positive'],
      ['unsafe_action_blocked', 0.15, 'both', 'Blocking unsafe actions increases trust'],
      ['dispute_resolution_quality', 0.2, 'real_world', 'Good dispute resolution increases trust'],
      ['calibration_improvement', 0.25, 'real_world', 'Calibration improvement is highly trusted'],
      ['calibration_regression', -0.35, 'real_world', 'Calibration regression is highly negative'],
      ['rollback_triggered', -0.2, 'real_world', 'Rollback indicates poor judgment'],
      ['protected_surface_violation', -0.4, 'both', 'Violations severely damage trust'],
      ['governance_review_quality', 0.15, 'real_world', 'Good reviews increase trust'],
      ['memory_quality_improvement', 0.1, 'real_world', 'Memory quality improvement is modest positive'],
      ['memory_quality_decline', -0.15, 'real_world', 'Memory degradation decreases trust'],
      ['evidence_quality_good', 0.1, 'real_world', 'Good evidence quality increases trust'],
      ['evidence_quality_poor', -0.15, 'real_world', 'Poor evidence quality decreases trust'],
      ['correction_event', 0.05, 'both', 'Correction events are slightly positive']
    ];

    for (const item of weights) {
      const eventType = item[0] as string;
      const weight = item[1] as number;
      const context = item[2] as any;
      const description = item[3] as string;
      await this.setEventTypeWeight(eventType, weight, context, description);
    }
  }

  /**
   * Get trust weight for applying to policies
   */
  async getTrustWeight(
    entityType: string,
    entityId: string,
    context: 'real_world' | 'simulation' | 'both' = 'real_world'
  ): Promise<number> {
    const reputation = await this.computeReputation(entityType, entityId, context);

    // Trust weight: 0.5 (low trust) to 1.5 (high trust)
    return 0.5 + reputation;
  }

  // Duplicate listEvents removed - use the more complete version at line 175 instead

  /**
   * List reputation snapshots for an entity
   */
  async listSnapshots(entityType: string, entityId: string): Promise<ReputationSnapshot[]> {
    const result = await db.query(
      `SELECT * FROM reputation_snapshots
       WHERE entity_type = $1 AND entity_id = $2
       ORDER BY snapshot_timestamp DESC`,
      [entityType, entityId]
    );

    return result.rows;
  }
}

export const trustReputationService = new TrustReputationService();
