import { db } from '../db/client';
import { v4 as uuidv4 } from 'uuid';

export interface SpecialistReputationSnapshot {
  specialist_role: string;
  total_count: number;
  avg_reputation: number;
  min_reputation: number;
  max_reputation: number;
  median_reputation: number;
  stddev_reputation: number;
}

export interface ReputationDistribution {
  institution_id: string;
  specialist_distribution: SpecialistReputationSnapshot[];
  total_specialists: number;
  avg_institution_reputation: number;
}

class ReputationScaleService {
  /**
   * Batch update specialist reputations efficiently
   * Optimized for 1000+ specialists
   */
  async batchUpdateReputations(
    updates: Array<{
      specialist_id: string;
      new_reputation: number;
      change_reason: string;
    }>
  ): Promise<{ updated: number; failed: number }> {
    try {
      let updated = 0;
      let failed = 0;

      // Process in batches of 100 to avoid memory issues
      const batchSize = 100;
      for (let i = 0; i < updates.length; i += batchSize) {
        const batch = updates.slice(i, Math.min(i + batchSize, updates.length));

        try {
          // Build single statement with multiple values
          const values: any[] = [];
          let paramIndex = 1;
          const valueClauses: string[] = [];

          for (const update of batch) {
            valueClauses.push(
              `($${paramIndex}, $${paramIndex + 1}, $${paramIndex + 2}, $${paramIndex + 3}, $${paramIndex + 4}, $${paramIndex + 5}, $${paramIndex + 6}, $${paramIndex + 7}, $${paramIndex + 8}, $${paramIndex + 9})`
            );
            const eventId = uuidv4();
            values.push(
              eventId,
              update.specialist_id,
              'reputation_update',
              Math.abs(update.new_reputation - 0.5),
              eventId,
              'specialist',
              0.5,
              update.new_reputation,
              update.change_reason,
              new Date()
            );
            paramIndex += 10;
          }

          // Batch insert into reputation audit log
          for (const update of batch) {
            await db.query(
              `INSERT INTO reputation_scores
                 (entity_id, entity_type, current_score, reliability, speed, innovation,
                  collaboration, performance_history, specialization, last_updated, created_at)
               VALUES ($1, 'specialist', $2, $3, 0.5, 0.5, 0.5, '[]', '[]', $4, $4)
               ON CONFLICT (entity_id) DO UPDATE
               SET current_score = EXCLUDED.current_score,
                   reliability = EXCLUDED.reliability,
                   last_updated = EXCLUDED.last_updated`,
              [
                update.specialist_id,
                update.new_reputation * 100,
                update.new_reputation,
                new Date(),
              ]
            );
          }

          await db.query(
            `INSERT INTO reputation_audit_log
              (event_id, entity_id, event_type, magnitude, id, entity_type,
               previous_reputation, new_reputation, change_reason, audit_timestamp)
             VALUES ${valueClauses.map((vc, idx) => vc).join(',')}`,
            values
          );

          updated += batch.length;
        } catch (e) {
          console.error(`Batch update failed for batch ${i / batchSize}:`, e);
          failed += batch.length;
        }
      }

      return { updated, failed };
    } catch (e) {
      throw new Error(`Failed to batch update reputations: ${e}`);
    }
  }

  /**
   * Get reputation distribution across institution
   */
  async getReputationDistribution(
    institutionId: string
  ): Promise<ReputationDistribution> {
    try {
      // Get specialist distribution
      const specResult = await db.query(
        `SELECT
          specialist_role,
          COUNT(*) as total_count,
          AVG(reputation_score) as avg_reputation,
          MIN(reputation_score) as min_reputation,
          MAX(reputation_score) as max_reputation,
          PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY reputation_score) as median_reputation,
          STDDEV_POP(reputation_score) as stddev_reputation
         FROM institution_specialist_assignments
         WHERE institution_id = $1 AND active = TRUE
         GROUP BY specialist_role
         ORDER BY avg_reputation DESC`,
        [institutionId]
      );

      const specialists = specResult.rows.map((row) => ({
        specialist_role: row.specialist_role,
        total_count: parseInt(row.total_count),
        avg_reputation: Math.round(row.avg_reputation * 100) / 100,
        min_reputation: Math.round(row.min_reputation * 100) / 100,
        max_reputation: Math.round(row.max_reputation * 100) / 100,
        median_reputation: Math.round((row.median_reputation || 0) * 100) / 100,
        stddev_reputation: Math.round((row.stddev_reputation || 0) * 100) / 100,
      }));

      // Get institution-level reputation
      const instResult = await db.query(
        `SELECT reputation_score FROM institutions WHERE id = $1`,
        [institutionId]
      );

      const totalSpecialists = specialists.reduce(
        (sum, s) => sum + s.total_count,
        0
      );
      const avgReputation =
        instResult.rows[0]?.reputation_score || 0.5;

      return {
        institution_id: institutionId,
        specialist_distribution: specialists,
        total_specialists: totalSpecialists,
        avg_institution_reputation: avgReputation,
      };
    } catch (e) {
      throw new Error(`Failed to get reputation distribution: ${e}`);
    }
  }

  /**
   * Find poorly performing specialists (bottom 10%)
   */
  async getUnderperformingSpecialists(
    institutionId: string,
    percentile: number = 10
  ): Promise<any[]> {
    try {
      const result = await db.query(
        `SELECT
          specialist_role,
          reputation_score,
          active,
          created_at,
          updated_at
         FROM institution_specialist_assignments
         WHERE institution_id = $1
           AND reputation_score < (
             SELECT PERCENTILE_CONT(${percentile / 100}) WITHIN GROUP (ORDER BY reputation_score)
             FROM institution_specialist_assignments
             WHERE institution_id = $1
           )
         ORDER BY reputation_score ASC`,
        [institutionId]
      );

      return result.rows;
    } catch (e) {
      throw new Error(`Failed to find underperforming specialists: ${e}`);
    }
  }

  /**
   * Find top performing specialists (top 10%)
   */
  async getTopPerformers(
    institutionId: string,
    percentile: number = 90
  ): Promise<any[]> {
    try {
      const result = await db.query(
        `SELECT
          specialist_role,
          reputation_score,
          COUNT(*) OVER (PARTITION BY specialist_role) as role_count
         FROM institution_specialist_assignments
         WHERE institution_id = $1
           AND reputation_score >= (
             SELECT PERCENTILE_CONT(${percentile / 100}) WITHIN GROUP (ORDER BY reputation_score)
             FROM institution_specialist_assignments
             WHERE institution_id = $1
           )
         ORDER BY reputation_score DESC`,
        [institutionId]
      );

      return result.rows;
    } catch (e) {
      throw new Error(`Failed to find top performers: ${e}`);
    }
  }

  /**
   * Calculate reputation percentile for specialist
   */
  async getReputationPercentile(
    institutionId: string,
    specialistRole: string,
    reputation: number
  ): Promise<number> {
    try {
      const result = await db.query(
        `SELECT
          ROUND(
            100.0 * COUNT(CASE WHEN reputation_score <= $3 THEN 1 END) /
            COUNT(*)
          ) as percentile
         FROM institution_specialist_assignments
         WHERE institution_id = $1 AND specialist_role = $2`,
        [institutionId, specialistRole, reputation]
      );

      return Number(result.rows[0]?.percentile || 0);
    } catch (e) {
      throw new Error(`Failed to calculate percentile: ${e}`);
    }
  }

  /**
   * Detect reputation anomalies (sudden large changes)
   */
  async detectReputationAnomalies(institutionId: string): Promise<any[]> {
    try {
      const result = await db.query(
        `SELECT
          ral.entity_id,
          ral.entity_type,
          ral.previous_reputation,
          ral.new_reputation,
          ABS(ral.new_reputation - ral.previous_reputation) as change_magnitude,
          ral.audit_timestamp
         FROM reputation_audit_log ral
         WHERE ral.entity_id IN (
           SELECT id FROM institutions WHERE id = $1
           UNION
           SELECT id FROM departments WHERE parent_id = $1
         )
         AND ABS(ral.new_reputation - ral.previous_reputation) > 0.3
         ORDER BY ral.audit_timestamp DESC
         LIMIT 50`,
        [institutionId]
      );

      return result.rows;
    } catch (e) {
      throw new Error(`Failed to detect anomalies: ${e}`);
    }
  }

  /**
   * Compute reputation trend over time window
   */
  async getReputationTrend(
    entityId: string,
    entityType: string,
    windowDays: number = 30
  ): Promise<any[]> {
    try {
      const result = await db.query(
        `SELECT
          DATE_TRUNC('day', audit_timestamp) as day,
          entity_id,
          entity_type,
          AVG(new_reputation) as avg_reputation,
          MIN(new_reputation) as min_reputation,
          MAX(new_reputation) as max_reputation,
          COUNT(*) as update_count
         FROM reputation_audit_log
         WHERE entity_id = $1
           AND entity_type = $2
           AND audit_timestamp >= NOW() - INTERVAL '${windowDays} days'
         GROUP BY DATE_TRUNC('day', audit_timestamp), entity_id, entity_type
         ORDER BY day ASC`,
        [entityId, entityType]
      );

      return result.rows.map((row) => ({
        day: row.day,
        avg_reputation: Math.round(row.avg_reputation * 100) / 100,
        min_reputation: Math.round(row.min_reputation * 100) / 100,
        max_reputation: Math.round(row.max_reputation * 100) / 100,
        update_count: parseInt(row.update_count),
      }));
    } catch (e) {
      throw new Error(`Failed to get reputation trend: ${e}`);
    }
  }

  /**
   * Aggregate specialist reputation to department
   */
  async aggregateSpecialistReputationToDept(
    departmentId: string
  ): Promise<number> {
    try {
      const result = await db.query(
        `SELECT AVG(reputation_score) as avg_reputation
         FROM institution_specialist_assignments
         WHERE department_id = $1 AND active = TRUE`,
        [departmentId]
      );

      const avgRep = result.rows[0]?.avg_reputation || 0.5;
      const roundedRep = Math.round(avgRep * 100) / 100;

      const client = await db.connect();
      try {
        await client.query('BEGIN');
        await client.query("SELECT set_config('civilization.reputation_update_authorized', 'true', true)");
        await client.query(
          `UPDATE departments
           SET reputation_score = $1, updated_at = $2
           WHERE id = $3`,
          [roundedRep, new Date(), departmentId]
        );
        await client.query('COMMIT');
      } catch (error) {
        await client.query('ROLLBACK');
        throw error;
      } finally {
        client.release();
      }

      return roundedRep;
    } catch (e) {
      throw new Error(`Failed to aggregate reputation: ${e}`);
    }
  }

  /**
   * Cascade reputation updates from specialist → dept → institution
   */
  async cascadeReputationUpdate(specialistId: string): Promise<void> {
    try {
      // Get specialist's department
      const specResult = await db.query(
        `SELECT department_id FROM institution_specialist_assignments WHERE id = $1`,
        [specialistId]
      );

      if (specResult.rows.length === 0) {
        return;
      }

      const departmentId = specResult.rows[0].department_id;

      // Update department reputation
      const deptAvg = await this.aggregateSpecialistReputationToDept(departmentId);

      // Get institution from department
      const deptResult = await db.query(
        `SELECT parent_id FROM departments WHERE id = $1`,
        [departmentId]
      );

      if (deptResult.rows.length === 0) {
        return;
      }

      const institutionId = deptResult.rows[0].parent_id;

      // Update institution reputation (aggregate all departments)
      const instResult = await db.query(
        `SELECT AVG(reputation_score) as avg_reputation
         FROM departments
         WHERE parent_id = $1 AND status = 'active'`,
        [institutionId]
      );

      const instAvg = Math.round((instResult.rows[0]?.avg_reputation || 0.5) * 100) / 100;

      const client = await db.connect();
      try {
        await client.query('BEGIN');
        await client.query("SELECT set_config('civilization.reputation_update_authorized', 'true', true)");
        await client.query(
          `UPDATE institutions
           SET reputation_score = $1, updated_at = $2
           WHERE id = $3`,
          [instAvg, new Date(), institutionId]
        );
        await client.query('COMMIT');
      } catch (error) {
        await client.query('ROLLBACK');
        throw error;
      } finally {
        client.release();
      }
    } catch (e) {
      throw new Error(`Failed to cascade reputation update: ${e}`);
    }
  }
}

export const reputationScaleService = new ReputationScaleService();
