/**
 * REPUTATION LEARNING SERVICE
 * ==========================
 *
 * Core reputation system:
 * - Tracks performance of agents, teams, institutions, societies
 * - Learns from claim accuracy, research quality, decision outcomes
 * - Cascades reputation through hierarchy
 * - Drives resource allocation and role assignment
 * - Persistent learning across runs
 *
 * PRODUCTION-GRADE: Full error handling, monitoring, persistence
 */

import { v4 as uuidv4 } from 'uuid';
import { db } from '../db/client';

export interface ReputationRecord {
  entity_id: string;
  entity_type: 'agent' | 'team' | 'institution' | 'society';
  current_score: number; // 0-100
  performance_history: PerformanceEvent[];
  specialization: string[]; // What this entity is good at
  reliability: number; // 0-1, based on claim accuracy
  speed: number; // 0-1, based on research pace
  innovation: number; // 0-1, based on novel insights
  collaboration: number; // 0-1, based on inter-agent coordination
  last_updated: Date;
}

export interface PerformanceEvent {
  event_id: string;
  event_type: 'claim_verified' | 'claim_refuted' | 'research_completed' | 'governance_voted' | 'coordination_success' | 'coordination_failure';
  magnitude: number; // Impact of event (-1.0 to 1.0)
  timestamp: Date;
  related_entities: string[]; // Other entities involved
  context: Record<string, any>;
}

export interface HierarchicalReputation {
  agent_scores: Map<string, number>;
  team_scores: Map<string, number>;
  institution_scores: Map<string, number>;
  society_scores: Map<string, number>;
  cascaded_at: Date;
}

class ReputationLearningService {
  private reputations = new Map<string, ReputationRecord>();
  private learning_buffer: PerformanceEvent[] = [];
  private cascade_threshold = 0.1; // Minimum change to cascade
  private decay_per_day = 0.02; // Reputation decay per day

  /**
   * Initialize or load reputation for entity
   */
  async initializeEntity(
    entity_id: string,
    entity_type: 'agent' | 'team' | 'institution' | 'society',
    specialization: string[] = []
  ): Promise<ReputationRecord> {
    // Check if exists in memory first
    if (this.reputations.has(entity_id)) {
      return this.reputations.get(entity_id)!;
    }

    try {
      // Try to check if exists in database
      try {
        const result = await db.query(
          `SELECT * FROM reputation_scores WHERE entity_id = $1 AND entity_type = $2`,
          [entity_id, entity_type]
        );

        if (result.rows.length > 0) {
          const row = result.rows[0];
          const record: ReputationRecord = {
            entity_id,
            entity_type,
            current_score: row.current_score,
            performance_history: JSON.parse(row.performance_history || '[]'),
            specialization: JSON.parse(row.specialization || '[]'),
            reliability: row.reliability,
            speed: row.speed,
            innovation: row.innovation,
            collaboration: row.collaboration,
            last_updated: new Date(row.last_updated)
          };
          this.reputations.set(entity_id, record);
          return record;
        }
      } catch (dbQueryErr: any) {
        // Database not available, will create in-memory only
        console.warn(`[ReputationLearning] Database query failed, will use in-memory: ${dbQueryErr.message}`);
      }

      // Create new reputation
      const new_record: ReputationRecord = {
        entity_id,
        entity_type,
        current_score: 50, // Start neutral
        performance_history: [],
        specialization,
        reliability: 0.5,
        speed: 0.5,
        innovation: 0.5,
        collaboration: 0.5,
        last_updated: new Date()
      };

      // Try to persist to database
      try {
        await db.query(
          `INSERT INTO reputation_scores
           (entity_id, entity_type, current_score, performance_history, specialization, reliability, speed, innovation, collaboration, last_updated)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())`,
          [
            entity_id,
            entity_type,
            new_record.current_score,
            JSON.stringify(new_record.performance_history),
            JSON.stringify(new_record.specialization),
            new_record.reliability,
            new_record.speed,
            new_record.innovation,
            new_record.collaboration
          ]
        );
      } catch (dbErr: any) {
        // If database write fails (e.g., in tests), continue with in-memory only
        console.warn(`[ReputationLearning] Database write failed, using in-memory: ${dbErr.message}`);
      }

      this.reputations.set(entity_id, new_record);
      return new_record;
    } catch (e) {
      console.error(`[ReputationLearning] Failed to initialize entity ${entity_id}:`, e);
      throw e;
    }
  }

  /**
   * Record performance event
   */
  async recordEvent(
    entity_id: string,
    event_type: PerformanceEvent['event_type'],
    magnitude: number,
    related_entities: string[] = [],
    context: Record<string, any> = {}
  ): Promise<void> {
    try {
      const record = this.reputations.get(entity_id);
      if (!record) {
        console.warn(`[ReputationLearning] Entity ${entity_id} not initialized`);
        return;
      }

      const event: PerformanceEvent = {
        event_id: uuidv4(),
        event_type,
        magnitude: Math.max(-1, Math.min(1, magnitude)), // Clamp to [-1, 1]
        timestamp: new Date(),
        related_entities,
        context
      };

      record.performance_history.push(event);
      this.learning_buffer.push(event);

      // Update reputation based on event
      await this.updateReputation(entity_id, event);

      // Persist event (non-blocking)
      try {
        await db.query(
          `INSERT INTO reputation_audit_log
           (event_id, entity_id, event_type, magnitude, related_entities, context, timestamp)
           VALUES ($1, $2, $3, $4, $5, $6, NOW())`,
          [
            event.event_id,
            entity_id,
            event_type,
            magnitude,
            JSON.stringify(related_entities),
            JSON.stringify(context)
          ]
        );
      } catch (dbErr: any) {
        console.warn(`[ReputationLearning] Event audit log write failed: ${dbErr.message}`);
      }
    } catch (e) {
      console.error(`[ReputationLearning] Failed to record event:`, e);
      throw e;
    }
  }

  /**
   * Update reputation based on event
   */
  private async updateReputation(entity_id: string, event: PerformanceEvent): Promise<void> {
    const record = this.reputations.get(entity_id);
    if (!record) return;

    const old_score = record.current_score;

    // Weight event based on type
    const event_weights: Record<PerformanceEvent['event_type'], number> = {
      claim_verified: 0.3,
      claim_refuted: -0.3,
      research_completed: 0.15,
      governance_voted: 0.2,
      coordination_success: 0.25,
      coordination_failure: -0.25
    };

    const weight = event_weights[event.event_type] || 0.1;
    const delta = weight * event.magnitude * 10; // Scale to reputation points

    // Update dimensional scores
    switch (event.event_type) {
      case 'claim_verified':
        record.reliability = Math.min(1, record.reliability + event.magnitude * 0.1);
        break;
      case 'claim_refuted':
        record.reliability = Math.max(0, record.reliability - Math.abs(event.magnitude) * 0.1);
        break;
      case 'research_completed':
        record.speed = Math.min(1, record.speed + event.magnitude * 0.05);
        break;
      case 'governance_voted':
        record.innovation = Math.min(1, record.innovation + event.magnitude * 0.08);
        break;
      case 'coordination_success':
        record.collaboration = Math.min(1, record.collaboration + event.magnitude * 0.1);
        break;
      case 'coordination_failure':
        record.collaboration = Math.max(0, record.collaboration - Math.abs(event.magnitude) * 0.1);
        break;
    }

    // Update overall score
    record.current_score = Math.max(0, Math.min(100, record.current_score + delta));

    // Learn specialization from success
    if (event.magnitude > 0.5 && event.context.topic) {
      if (!record.specialization.includes(event.context.topic)) {
        record.specialization.push(event.context.topic);
      }
    }

    record.last_updated = new Date();

    // Persist update (non-blocking)
    try {
      await db.query(
        `UPDATE reputation_scores
         SET current_score = $1, reliability = $2, speed = $3, innovation = $4, collaboration = $5,
             performance_history = $6, specialization = $7, last_updated = NOW()
         WHERE entity_id = $8`,
        [
          record.current_score,
          record.reliability,
          record.speed,
          record.innovation,
          record.collaboration,
          JSON.stringify(record.performance_history),
          JSON.stringify(record.specialization),
          entity_id
        ]
      );
    } catch (dbErr: any) {
      console.warn(`[ReputationLearning] Reputation update write failed: ${dbErr.message}`);
    }

    // Emit cascade event if significant change
    if (Math.abs(record.current_score - old_score) > this.cascade_threshold * 10) {
      await this.emitCascadeEvent(entity_id, record);
    }
  }

  /**
   * Cascade reputation up the hierarchy
   */
  private async emitCascadeEvent(entity_id: string, record: ReputationRecord): Promise<void> {
    try {
      // Find parent entity
      const parent_result = await db.query(
        `SELECT parent_id FROM entity_hierarchy WHERE child_id = $1 LIMIT 1`,
        [entity_id]
      );

      if (parent_result.rows.length === 0) return;

      const parent_id = parent_result.rows[0].parent_id;
      const parent_record = this.reputations.get(parent_id);

      if (!parent_record) {
        console.warn(`[ReputationLearning] Parent ${parent_id} not found for cascade`);
        return;
      }

      // Cascade: parent reputation shifts toward child's performance
      const child_ratio = (record.current_score - 50) / 50; // -1 to 1
      const cascade_amount = child_ratio * 3; // Up to ±3 points per child

      parent_record.current_score = Math.max(
        0,
        Math.min(100, parent_record.current_score + cascade_amount)
      );

      parent_record.last_updated = new Date();

      // Persist parent update (non-blocking)
      try {
        await db.query(
          `UPDATE reputation_scores
           SET current_score = $1, last_updated = NOW()
           WHERE entity_id = $2`,
          [parent_record.current_score, parent_id]
        );
      } catch (dbErr: any) {
        console.warn(`[ReputationLearning] Parent cascade write failed: ${dbErr.message}`);
      }

      // Recursively cascade up
      await this.emitCascadeEvent(parent_id, parent_record);
    } catch (e) {
      console.error(`[ReputationLearning] Cascade failed:`, e);
    }
  }

  /**
   * Get hierarchical reputation snapshot
   */
  async getHierarchicalReputation(root_id?: string): Promise<HierarchicalReputation> {
    const agent_scores = new Map<string, number>();
    const team_scores = new Map<string, number>();
    const institution_scores = new Map<string, number>();
    const society_scores = new Map<string, number>();

    // Gather all current scores
    for (const [entity_id, record] of this.reputations) {
      const score = record.current_score;

      switch (record.entity_type) {
        case 'agent':
          agent_scores.set(entity_id, score);
          break;
        case 'team':
          team_scores.set(entity_id, score);
          break;
        case 'institution':
          institution_scores.set(entity_id, score);
          break;
        case 'society':
          society_scores.set(entity_id, score);
          break;
      }
    }

    return {
      agent_scores,
      team_scores,
      institution_scores,
      society_scores,
      cascaded_at: new Date()
    };
  }

  /**
   * Apply decay to old reputations
   */
  async applyDecay(): Promise<void> {
    try {
      for (const [entity_id, record] of this.reputations) {
        const days_since_update = (Date.now() - record.last_updated.getTime()) / (1000 * 60 * 60 * 24);
        const decay_amount = days_since_update * this.decay_per_day * 10; // Convert to reputation points

        if (decay_amount > 0) {
          // Reputation decays toward neutral (50)
          const neutral_distance = Math.abs(record.current_score - 50);
          const decayed_amount = Math.max(0, neutral_distance - decay_amount);
          const new_score = record.current_score > 50
            ? 50 + decayed_amount
            : 50 - decayed_amount;

          record.current_score = new_score;
          record.last_updated = new Date();

          try {
            await db.query(
              `UPDATE reputation_scores SET current_score = $1, last_updated = NOW() WHERE entity_id = $2`,
              [record.current_score, entity_id]
            );
          } catch (dbErr: any) {
            console.warn(`[ReputationLearning] Decay update write failed: ${dbErr.message}`);
          }
        }
      }
    } catch (e) {
      console.error(`[ReputationLearning] Decay application failed:`, e);
    }
  }

  /**
   * Get entity reputation
   */
  getReputation(entity_id: string): ReputationRecord | null {
    return this.reputations.get(entity_id) || null;
  }

  /**
   * List current in-process reputation records.
   *
   * Services that make runtime governance/routing decisions use this as their
   * candidate pool. Database-backed entities are loaded into this map through
   * initializeEntity(), so callers do not need to invent placeholder agents.
   */
  listReputations(): ReputationRecord[] {
    return Array.from(this.reputations.values());
  }

  /**
   * Predict future performance based on reputation
   */
  predictPerformance(entity_id: string): { predicted_quality: number; confidence: number } {
    const record = this.reputations.get(entity_id);
    if (!record) {
      return { predicted_quality: 0.5, confidence: 0 };
    }

    // Use dimensions to predict quality
    const weighted_quality =
      (record.reliability * 0.4 +
        record.speed * 0.2 +
        record.innovation * 0.2 +
        record.collaboration * 0.2);

    // Confidence is higher with more history
    const history_count = record.performance_history.length;
    const confidence = Math.min(1, history_count / 50); // 50 events = 100% confidence

    return {
      predicted_quality: weighted_quality,
      confidence
    };
  }

  /**
   * Get learning insights from reputation history
   */
  getInsights(entity_id: string): {
    strengths: string[];
    weaknesses: string[];
    specializations: string[];
    recommendations: string[];
  } {
    const record = this.reputations.get(entity_id);
    if (!record) {
      return { strengths: [], weaknesses: [], specializations: [], recommendations: [] };
    }

    const strengths: string[] = [];
    const weaknesses: string[] = [];

    // Identify strengths
    if (record.reliability > 0.7) strengths.push('Reliable claims');
    if (record.speed > 0.7) strengths.push('Fast research');
    if (record.innovation > 0.7) strengths.push('Novel insights');
    if (record.collaboration > 0.7) strengths.push('Strong coordination');

    // Identify weaknesses
    if (record.reliability < 0.4) weaknesses.push('Low claim accuracy');
    if (record.speed < 0.4) weaknesses.push('Slow research pace');
    if (record.innovation < 0.4) weaknesses.push('Limited new ideas');
    if (record.collaboration < 0.4) weaknesses.push('Poor coordination');

    // Recommendations
    const recommendations: string[] = [];
    if (record.reliability < 0.5) {
      recommendations.push('Focus on evidence verification before claiming');
    }
    if (record.specialization.length === 0) {
      recommendations.push('Build specialization in a domain');
    }
    if (record.current_score < 30) {
      recommendations.push('Consider reassignment to simpler tasks');
    }

    return {
      strengths,
      weaknesses,
      specializations: record.specialization,
      recommendations
    };
  }
}

export const reputationLearningService = new ReputationLearningService();
export { ReputationLearningService };
