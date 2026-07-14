import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { auditLog } from './audit-log.service';
import { civilizationKernel } from './civilization-kernel.service';
import { PublicHttpError } from '../http-errors';

/**
 * Societies (build phase C3).
 *
 * Societies sit between the civilization root and institutions. Society
 * jurisdiction is a DB-enforced subset of civilization jurisdiction
 * (composite FK). Suspension blocks new protected attachments and joins while
 * preserving history; dissolution is terminal and requires an empty society.
 */

export type SocietyStatus = 'forming' | 'active' | 'suspended' | 'dissolved';

const SOCIETY_TRANSITIONS: Record<SocietyStatus, SocietyStatus[]> = {
  forming: ['active', 'dissolved'],
  active: ['suspended', 'dissolved'],
  suspended: ['active', 'dissolved'],
  dissolved: [],
};

export interface SocietyRecord {
  id: string;
  civilization_id: string;
  name: string;
  status: SocietyStatus;
  description: string;
  created_by_actor_id: string;
  created_at: string;
  updated_at: string;
}

const SOCIETY_COLUMNS =
  'id, civilization_id, name, status, description, created_by_actor_id, created_at, updated_at';

/** Default societies seeded for the civilization root (predicate: >=2 active). */
export const DEFAULT_SOCIETIES: Array<{ name: string; description: string }> = [
  { name: 'Core Operations', description: 'Operates verified production workflows and institutional duties' },
  { name: 'Frontier Research', description: 'Explores new domains, capabilities, and evaluation frontiers' },
];

export class SocietyService {
  async createSociety(input: {
    name: string;
    description?: string;
    civilization_id?: string;
    created_by_actor_id?: string;
  }): Promise<SocietyRecord> {
    if (!input.name || input.name.trim().length === 0) {
      throw new PublicHttpError(400, 'name is required');
    }
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const civilizationId = input.civilization_id ?? (await this.requireRootId(client));
      const actorId = input.created_by_actor_id ?? (await this.ensureServiceActor(client));
      const existing = await client.query<SocietyRecord>(
        `SELECT ${SOCIETY_COLUMNS} FROM societies WHERE civilization_id = $1 AND name = $2 LIMIT 1`,
        [civilizationId, input.name.trim()]
      );
      if ((existing.rowCount ?? 0) > 0) {
        await client.query('COMMIT');
        return existing.rows[0];
      }
      const societyId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'society.created',
        actor_id: actorId,
        object_type: 'society',
        object_id: societyId,
        correlation_id: crypto.randomUUID(),
        payload: { civilization_id: civilizationId, name: input.name.trim() },
      });
      const inserted = await client.query<SocietyRecord>(
        `INSERT INTO societies (id, civilization_id, name, description, created_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6) RETURNING ${SOCIETY_COLUMNS}`,
        [societyId, civilizationId, input.name.trim(), input.description ?? '', actorId, event.id]
      );
      await auditLog.appendWithClient(client, {
        agent_id: actorId,
        action_type: 'decision',
        input_summary: `create society ${input.name.trim()}`,
        output_summary: `society ${societyId} forming`,
        confidence_score: 1,
        risk_level: 'medium',
        human_approved: false,
        downstream_events: [event.id],
      }, { timestamp: new Date().toISOString() });
      await client.query('COMMIT');
      return inserted.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async transitionSociety(input: {
    society_id: string;
    to_status: SocietyStatus;
    actor_id: string;
    reason: string;
  }): Promise<SocietyRecord> {
    if (!input.reason || input.reason.trim().length === 0) {
      throw new PublicHttpError(400, 'reason is required');
    }
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const current = await client.query<SocietyRecord>(
        `SELECT ${SOCIETY_COLUMNS} FROM societies WHERE id = $1 FOR UPDATE`,
        [input.society_id]
      );
      if ((current.rowCount ?? 0) !== 1) {
        throw new PublicHttpError(404, `society not found: ${input.society_id}`);
      }
      const from = current.rows[0].status;
      if (!SOCIETY_TRANSITIONS[from]?.includes(input.to_status)) {
        throw new PublicHttpError(409, `illegal society transition ${from} -> ${input.to_status}`);
      }
      if (input.to_status === 'dissolved') {
        const active = await client.query<{ citizens: number; institutions: number }>(
          `SELECT
             (SELECT COUNT(*) FROM society_memberships WHERE society_id = $1 AND status = 'active')::int AS citizens,
             (SELECT COUNT(*) FROM institution_society_memberships WHERE society_id = $1 AND status = 'active')::int AS institutions`,
          [input.society_id]
        );
        if (active.rows[0].citizens > 0 || active.rows[0].institutions > 0) {
          throw new PublicHttpError(409, 'dissolution requires ending all active citizen and institution memberships first');
        }
      }
      const event = await eventLog.appendWithClient(client, {
        event_type: 'society.status_changed',
        actor_id: input.actor_id,
        object_type: 'society',
        object_id: input.society_id,
        correlation_id: crypto.randomUUID(),
        payload: { from_status: from, to_status: input.to_status, reason: input.reason },
      });
      await client.query(`SELECT set_config('civilization.society_transition_authorized', 'true', true)`);
      const updated = await client.query<SocietyRecord>(
        `UPDATE societies SET status = $2 WHERE id = $1 RETURNING ${SOCIETY_COLUMNS}`,
        [input.society_id, input.to_status]
      );
      await client.query(`SELECT set_config('civilization.society_transition_authorized', 'false', true)`);
      await client.query(
        `INSERT INTO society_state_transitions (society_id, from_status, to_status, reason, actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6)`,
        [input.society_id, from, input.to_status, input.reason, input.actor_id, event.id]
      );
      await auditLog.appendWithClient(client, {
        agent_id: input.actor_id,
        action_type: 'decision',
        input_summary: `society ${input.society_id} ${from} -> ${input.to_status}: ${input.reason}`,
        output_summary: `society status is now ${input.to_status}`,
        confidence_score: 1,
        risk_level: input.to_status === 'dissolved' ? 'high' : 'medium',
        human_approved: false,
        downstream_events: [event.id],
      }, { timestamp: new Date().toISOString() });
      await client.query('COMMIT');
      return updated.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async getSociety(societyId: string): Promise<SocietyRecord | null> {
    const result = await db.query<SocietyRecord>(
      `SELECT ${SOCIETY_COLUMNS} FROM societies WHERE id = $1 LIMIT 1`,
      [societyId]
    );
    return result.rows[0] ?? null;
  }

  async listSocieties(civilizationId?: string): Promise<SocietyRecord[]> {
    const result = civilizationId
      ? await db.query<SocietyRecord>(
          `SELECT ${SOCIETY_COLUMNS} FROM societies WHERE civilization_id = $1 ORDER BY created_at`,
          [civilizationId]
        )
      : await db.query<SocietyRecord>(`SELECT ${SOCIETY_COLUMNS} FROM societies ORDER BY created_at`);
    return result.rows;
  }

  async assertSocietyActive(societyId: string): Promise<SocietyRecord> {
    const society = await this.getSociety(societyId);
    if (!society) throw new PublicHttpError(404, `society not found: ${societyId}`);
    if (society.status !== 'active') {
      throw new PublicHttpError(409, `society is ${society.status}; new protected work is blocked`);
    }
    return society;
  }

  // -------------------------------------------------------------------------
  // Jurisdiction (subset of civilization jurisdiction, DB-enforced)
  // -------------------------------------------------------------------------

  async addJurisdiction(input: {
    society_id: string;
    jurisdiction_key: string;
    granted_by_actor_id: string;
  }): Promise<{ id: string; jurisdiction_key: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const society = await client.query<{ civilization_id: string }>(
        `SELECT civilization_id FROM societies WHERE id = $1 LIMIT 1`,
        [input.society_id]
      );
      if ((society.rowCount ?? 0) !== 1) {
        throw new PublicHttpError(404, `society not found: ${input.society_id}`);
      }
      const grantId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'society.jurisdiction_granted',
        actor_id: input.granted_by_actor_id,
        object_type: 'society_jurisdiction',
        object_id: grantId,
        correlation_id: crypto.randomUUID(),
        payload: { society_id: input.society_id, jurisdiction_key: input.jurisdiction_key },
      });
      const inserted = await client.query<{ id: string; jurisdiction_key: string }>(
        `INSERT INTO society_jurisdictions
           (id, society_id, civilization_id, jurisdiction_key, granted_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6)
         RETURNING id, jurisdiction_key`,
        [grantId, input.society_id, society.rows[0].civilization_id,
         input.jurisdiction_key, input.granted_by_actor_id, event.id]
      );
      await client.query('COMMIT');
      return inserted.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      if ((error as { code?: string }).code === '23503') {
        throw new PublicHttpError(409,
          `jurisdiction '${input.jurisdiction_key}' is not granted at the civilization level; society powers cannot exceed civilization jurisdiction`);
      }
      throw error;
    } finally {
      client.release();
    }
  }

  // -------------------------------------------------------------------------
  // Memberships
  // -------------------------------------------------------------------------

  async joinSociety(input: {
    society_id: string;
    citizen_id: string;
    role_in_society?: string;
    actor_id: string;
  }): Promise<{ id: string }> {
    await this.assertSocietyActive(input.society_id);
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const existing = await client.query<{ id: string }>(
        `SELECT id FROM society_memberships WHERE society_id = $1 AND citizen_id = $2 AND status = 'active' LIMIT 1`,
        [input.society_id, input.citizen_id]
      );
      if ((existing.rowCount ?? 0) > 0) {
        await client.query('COMMIT');
        return existing.rows[0];
      }
      const membershipId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'society.citizen_joined',
        actor_id: input.actor_id,
        object_type: 'society_membership',
        object_id: membershipId,
        correlation_id: crypto.randomUUID(),
        payload: {
          society_id: input.society_id,
          citizen_id: input.citizen_id,
          role_in_society: input.role_in_society ?? 'member',
        },
      });
      const inserted = await client.query<{ id: string }>(
        `INSERT INTO society_memberships (id, society_id, citizen_id, role_in_society, event_log_id)
         VALUES ($1,$2,$3,$4,$5) RETURNING id`,
        [membershipId, input.society_id, input.citizen_id, input.role_in_society ?? 'member', event.id]
      );
      await client.query('COMMIT');
      return inserted.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async leaveSociety(input: { society_id: string; citizen_id: string; actor_id: string; reason: string }): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await eventLog.appendWithClient(client, {
        event_type: 'society.citizen_left',
        actor_id: input.actor_id,
        object_type: 'society_membership',
        object_id: input.citizen_id,
        correlation_id: crypto.randomUUID(),
        payload: { society_id: input.society_id, citizen_id: input.citizen_id, reason: input.reason },
      });
      const updated = await client.query(
        `UPDATE society_memberships SET status = 'ended', ended_at = now(), ended_by_actor_id = $3
          WHERE society_id = $1 AND citizen_id = $2 AND status = 'active'`,
        [input.society_id, input.citizen_id, input.actor_id]
      );
      if ((updated.rowCount ?? 0) !== 1) {
        throw new PublicHttpError(409, 'no active membership to end');
      }
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async attachInstitution(input: {
    society_id: string;
    institution_id: string;
    actor_id: string;
  }): Promise<{ id: string }> {
    await this.assertSocietyActive(input.society_id);
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const institution = await client.query<{ id: string }>(
        `SELECT id FROM institutions WHERE id = $1 AND status = 'active' LIMIT 1`,
        [input.institution_id]
      );
      if ((institution.rowCount ?? 0) !== 1) {
        throw new PublicHttpError(404, `active institution not found: ${input.institution_id}`);
      }
      const existing = await client.query<{ id: string; society_id: string }>(
        `SELECT id, society_id FROM institution_society_memberships
          WHERE institution_id = $1 AND status = 'active' LIMIT 1`,
        [input.institution_id]
      );
      if ((existing.rowCount ?? 0) > 0) {
        if (existing.rows[0].society_id === input.society_id) {
          await client.query('COMMIT');
          return { id: existing.rows[0].id };
        }
        throw new PublicHttpError(409, 'institution already belongs to another active society; detach first');
      }
      const membershipId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'society.institution_attached',
        actor_id: input.actor_id,
        object_type: 'institution_society_membership',
        object_id: membershipId,
        correlation_id: crypto.randomUUID(),
        payload: { society_id: input.society_id, institution_id: input.institution_id },
      });
      const inserted = await client.query<{ id: string }>(
        `INSERT INTO institution_society_memberships (id, institution_id, society_id, attached_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5) RETURNING id`,
        [membershipId, input.institution_id, input.society_id, input.actor_id, event.id]
      );
      await client.query('COMMIT');
      return inserted.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async grantInstitutionCivilizationJurisdiction(input: {
    institution_id: string;
    jurisdiction_key: string;
    granted_by_actor_id: string;
    civilization_id?: string;
  }): Promise<{ id: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const civilizationId = input.civilization_id ?? (await this.requireRootId(client));
      const existing = await client.query<{ id: string }>(
        `SELECT id FROM institution_jurisdiction_grants
          WHERE institution_id = $1 AND jurisdiction_key = $2 AND status = 'active' LIMIT 1`,
        [input.institution_id, input.jurisdiction_key]
      );
      if ((existing.rowCount ?? 0) > 0) {
        await client.query('COMMIT');
        return existing.rows[0];
      }
      const grantId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'institution.jurisdiction_granted',
        actor_id: input.granted_by_actor_id,
        object_type: 'institution_jurisdiction_grant',
        object_id: grantId,
        correlation_id: crypto.randomUUID(),
        payload: { institution_id: input.institution_id, jurisdiction_key: input.jurisdiction_key },
      });
      const inserted = await client.query<{ id: string }>(
        `INSERT INTO institution_jurisdiction_grants
           (id, institution_id, civilization_id, jurisdiction_key, granted_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6) RETURNING id`,
        [grantId, input.institution_id, civilizationId, input.jurisdiction_key, input.granted_by_actor_id, event.id]
      );
      await client.query('COMMIT');
      return inserted.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      if ((error as { code?: string }).code === '23503') {
        throw new PublicHttpError(409,
          `jurisdiction '${input.jurisdiction_key}' is not granted at the civilization level`);
      }
      throw error;
    } finally {
      client.release();
    }
  }

  /** Idempotent seed of the two default societies (activated, chartered, global jurisdiction). */
  async ensureDefaultSocieties(actorId?: string): Promise<SocietyRecord[]> {
    await civilizationKernel.ensureCivilizationRoot();
    const results: SocietyRecord[] = [];
    for (const spec of DEFAULT_SOCIETIES) {
      let society = await this.createSociety({
        name: spec.name,
        description: spec.description,
        created_by_actor_id: actorId,
      });
      if (society.status === 'forming') {
        const client = await db.connect();
        try {
          const serviceActor = actorId ?? (await this.ensureServiceActor(client));
          society = await this.transitionSociety({
            society_id: society.id,
            to_status: 'active',
            actor_id: serviceActor,
            reason: 'default society activation',
          });
          await this.addJurisdiction({
            society_id: society.id,
            jurisdiction_key: 'global',
            granted_by_actor_id: serviceActor,
          });
        } finally {
          client.release();
        }
      }
      results.push(society);
    }
    return results;
  }

  async getTopology(): Promise<{
    civilization_id: string | null;
    societies: Array<SocietyRecord & { citizen_members: number; institutions: number; jurisdictions: string[] }>;
    civilization_wide_institutions: Array<{ institution_id: string; jurisdiction_keys: string[] }>;
  }> {
    const root = await civilizationKernel.getActiveCivilization();
    if (!root) return { civilization_id: null, societies: [], civilization_wide_institutions: [] };
    const societies = await this.listSocieties(root.id);
    const enriched = [] as Array<SocietyRecord & { citizen_members: number; institutions: number; jurisdictions: string[] }>;
    for (const society of societies) {
      const [members, institutions, jurisdictions] = await Promise.all([
        db.query<{ count: string }>(
          `SELECT COUNT(*)::int AS count FROM society_memberships WHERE society_id = $1 AND status = 'active'`,
          [society.id]
        ),
        db.query<{ count: string }>(
          `SELECT COUNT(*)::int AS count FROM institution_society_memberships WHERE society_id = $1 AND status = 'active'`,
          [society.id]
        ),
        db.query<{ jurisdiction_key: string }>(
          `SELECT jurisdiction_key FROM society_jurisdictions WHERE society_id = $1 AND status = 'active'`,
          [society.id]
        ),
      ]);
      enriched.push({
        ...society,
        citizen_members: Number(members.rows[0].count),
        institutions: Number(institutions.rows[0].count),
        jurisdictions: jurisdictions.rows.map(r => r.jurisdiction_key),
      });
    }
    const wide = await db.query<{ institution_id: string; jurisdiction_key: string }>(
      `SELECT institution_id, jurisdiction_key FROM institution_jurisdiction_grants WHERE status = 'active'`
    );
    const wideMap = new Map<string, string[]>();
    for (const row of wide.rows) {
      wideMap.set(row.institution_id, [...(wideMap.get(row.institution_id) ?? []), row.jurisdiction_key]);
    }
    return {
      civilization_id: root.id,
      societies: enriched,
      civilization_wide_institutions: [...wideMap.entries()].map(([institution_id, jurisdiction_keys]) => ({
        institution_id, jurisdiction_keys,
      })),
    };
  }

  private async requireRootId(client: PoolClient): Promise<string> {
    const root = await client.query<{ id: string }>(
      `SELECT id FROM civilizations WHERE status = 'active' LIMIT 1`
    );
    if ((root.rowCount ?? 0) !== 1) {
      throw new PublicHttpError(409, 'no active civilization root; bootstrap the kernel first');
    }
    return root.rows[0].id;
  }

  private async ensureServiceActor(client: PoolClient): Promise<string> {
    const name = 'agentco-society-service';
    const actor = await client.query<{ id: string }>(
      `INSERT INTO actors (actor_type, name, metadata_json)
       VALUES ('service',$1,$2::jsonb)
       ON CONFLICT (actor_type, name) WHERE status = 'active'
       DO UPDATE SET updated_at = actors.updated_at
       RETURNING id`,
      [name, JSON.stringify({ created_by: 'SocietyService' })]
    );
    await client.query(
      `INSERT INTO service_identities (actor_id, service_name, scopes)
       VALUES ($1,$2,$3::jsonb)
       ON CONFLICT (actor_id) DO NOTHING`,
      [actor.rows[0].id, name, JSON.stringify(['society.manage'])]
    );
    return actor.rows[0].id;
  }
}

export const societyService = new SocietyService();
