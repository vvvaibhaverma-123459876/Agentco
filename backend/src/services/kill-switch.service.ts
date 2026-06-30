import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';

export interface KillSwitchRecord {
  id: string;
  scope: string;
  active: boolean;
  reason: string;
  activated_by_actor_id: string;
  deactivated_by_actor_id: string | null;
  activated_event_log_id: string;
  deactivated_event_log_id: string | null;
  activated_at: string;
  deactivated_at: string | null;
  metadata_json: Record<string, unknown>;
}

function validateScope(scope: string): void {
  if (!/^[a-z0-9_.:-]{3,120}$/i.test(scope)) {
    throw new Error('kill switch scope must be 3-120 safe characters');
  }
}

export class KillSwitchService {
  async activate(
    scope: string,
    actorId: string,
    reason: string,
    metadata: Record<string, unknown> = {}
  ): Promise<KillSwitchRecord> {
    validateScope(scope);
    if (!reason.trim()) throw new Error('kill switch reason is required');
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const existing = await this.getActiveWithClient(client, scope);
      if (existing) {
        await client.query('COMMIT');
        return existing;
      }
      const event = await eventLog.appendWithClient(client, {
        event_type: 'kill_switch.activated',
        actor_id: actorId,
        object_type: 'governance_kill_switch',
        payload: { scope, reason, metadata },
      });
      const result = await client.query<KillSwitchRecord>(
        `INSERT INTO governance_kill_switches
           (scope, reason, activated_by_actor_id, activated_event_log_id, metadata_json)
         VALUES ($1, $2, $3, $4, $5::jsonb)
         RETURNING id, scope, active, reason, activated_by_actor_id, deactivated_by_actor_id,
                   activated_event_log_id, deactivated_event_log_id, activated_at, deactivated_at, metadata_json`,
        [scope, reason, actorId, event.id, JSON.stringify(metadata)]
      );
      await client.query('COMMIT');
      return result.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async deactivate(scope: string, actorId: string, reason: string): Promise<KillSwitchRecord> {
    validateScope(scope);
    if (!reason.trim()) throw new Error('kill switch deactivation reason is required');
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const existing = await this.getActiveWithClient(client, scope);
      if (!existing) throw new Error(`No active kill switch for scope ${scope}`);
      const event = await eventLog.appendWithClient(client, {
        event_type: 'kill_switch.deactivated',
        actor_id: actorId,
        object_type: 'governance_kill_switch',
        payload: { scope, reason, kill_switch_id: existing.id },
      });
      const result = await client.query<KillSwitchRecord>(
        `UPDATE governance_kill_switches
            SET active = false,
                deactivated_by_actor_id = $1,
                deactivated_event_log_id = $2,
                deactivated_at = now()
          WHERE id = $3
          RETURNING id, scope, active, reason, activated_by_actor_id, deactivated_by_actor_id,
                    activated_event_log_id, deactivated_event_log_id, activated_at, deactivated_at, metadata_json`,
        [actorId, event.id, existing.id]
      );
      await client.query('COMMIT');
      return result.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async getActive(scope: string): Promise<KillSwitchRecord | null> {
    validateScope(scope);
    const result = await db.query<KillSwitchRecord>(
      `SELECT id, scope, active, reason, activated_by_actor_id, deactivated_by_actor_id,
              activated_event_log_id, deactivated_event_log_id, activated_at, deactivated_at, metadata_json
         FROM governance_kill_switches
        WHERE scope = $1 AND active = true
        ORDER BY activated_at DESC
        LIMIT 1`,
      [scope]
    );
    return result.rows[0] ?? null;
  }

  async assertNotKilled(scope: string): Promise<void> {
    const active = await this.getActive(scope);
    if (active) {
      throw new Error(`Kill switch active for ${scope}: ${active.reason}`);
    }
  }

  private async getActiveWithClient(client: PoolClient, scope: string): Promise<KillSwitchRecord | null> {
    const result = await client.query<KillSwitchRecord>(
      `SELECT id, scope, active, reason, activated_by_actor_id, deactivated_by_actor_id,
              activated_event_log_id, deactivated_event_log_id, activated_at, deactivated_at, metadata_json
         FROM governance_kill_switches
        WHERE scope = $1 AND active = true
        ORDER BY activated_at DESC
        LIMIT 1
        FOR UPDATE`,
      [scope]
    );
    return result.rows[0] ?? null;
  }
}

export const killSwitchService = new KillSwitchService();
