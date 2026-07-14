import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { auditLog } from './audit-log.service';
import { civilizationKernel } from './civilization-kernel.service';
import { PublicHttpError } from '../http-errors';

/**
 * Institution coalitions (build phase C4).
 *
 * Temporary, explicit, durable institution-level coordination: negotiation
 * rounds with proposals/counterproposals, accepted commitments, consensus per
 * the coalition's charter rule, retained dissent, delegated authority revoked
 * on dissolution, and settlement preserved for failed coalitions.
 *
 * Lifecycle: proposed -> negotiating -> constituted -> active -> completing
 *            -> settled | dissolved | failed
 */

export type CoalitionStatus =
  | 'proposed' | 'negotiating' | 'constituted' | 'active'
  | 'completing' | 'settled' | 'dissolved' | 'failed';

const COALITION_TRANSITIONS: Record<CoalitionStatus, CoalitionStatus[]> = {
  proposed: ['negotiating', 'failed'],
  negotiating: ['constituted', 'failed'],
  constituted: ['active', 'failed'],
  active: ['completing', 'dissolved', 'failed'],
  completing: ['settled', 'failed'],
  settled: [],
  dissolved: [],
  failed: [],
};

const TERMINAL: CoalitionStatus[] = ['settled', 'dissolved', 'failed'];

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  const entries = Object.entries(value as Record<string, unknown>)
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([k, v]) => `${JSON.stringify(k)}:${stableStringify(v)}`);
  return `{${entries.join(',')}}`;
}

export interface CoalitionRecord {
  id: string;
  civilization_id: string;
  name: string;
  purpose: string;
  mission_scope: string;
  consensus_rule: 'unanimous' | 'majority' | 'weighted_majority';
  status: CoalitionStatus;
  created_by_actor_id: string;
  created_at: string;
  updated_at: string;
}

const COALITION_COLUMNS =
  'id, civilization_id, name, purpose, mission_scope, consensus_rule, status, created_by_actor_id, created_at, updated_at';

export class CoalitionService {
  async proposeCoalition(input: {
    name: string;
    purpose?: string;
    mission_scope?: string;
    consensus_rule?: 'unanimous' | 'majority' | 'weighted_majority';
    charter?: Record<string, unknown>;
    member_institution_ids: string[];
    created_by_actor_id: string;
  }): Promise<CoalitionRecord> {
    if (!input.name || input.name.trim().length === 0) throw new PublicHttpError(400, 'name is required');
    if (!Array.isArray(input.member_institution_ids) || input.member_institution_ids.length < 2) {
      throw new PublicHttpError(400, 'a coalition requires at least two member institutions');
    }
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const civilizationId = await this.requireRootId(client);
      const coalitionId = crypto.randomUUID();
      const charter = input.charter ?? { consensus_rule: input.consensus_rule ?? 'unanimous' };
      const charterHash = crypto.createHash('sha256').update(stableStringify(charter)).digest('hex');
      const event = await eventLog.appendWithClient(client, {
        event_type: 'coalition.proposed',
        actor_id: input.created_by_actor_id,
        object_type: 'institution_coalition',
        object_id: coalitionId,
        correlation_id: crypto.randomUUID(),
        payload: { name: input.name.trim(), members: input.member_institution_ids },
      });
      const inserted = await client.query<CoalitionRecord>(
        `INSERT INTO institution_coalitions
           (id, civilization_id, name, purpose, mission_scope, consensus_rule, charter_json, charter_hash, created_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8,$9,$10)
         RETURNING ${COALITION_COLUMNS}`,
        [coalitionId, civilizationId, input.name.trim(), input.purpose ?? '', input.mission_scope ?? '',
         input.consensus_rule ?? 'unanimous', JSON.stringify(charter), charterHash,
         input.created_by_actor_id, event.id]
      );
      for (const institutionId of input.member_institution_ids) {
        const institution = await client.query(
          `SELECT id FROM institutions WHERE id = $1 AND status = 'active' LIMIT 1`,
          [institutionId]
        );
        if ((institution.rowCount ?? 0) !== 1) {
          throw new PublicHttpError(404, `active institution not found: ${institutionId}`);
        }
        await client.query(
          `INSERT INTO coalition_members (coalition_id, institution_id, invited_by_actor_id, event_log_id)
           VALUES ($1,$2,$3,$4)`,
          [coalitionId, institutionId, input.created_by_actor_id, event.id]
        );
      }
      await auditLog.appendWithClient(client, {
        agent_id: input.created_by_actor_id,
        action_type: 'decision',
        input_summary: `propose coalition ${input.name.trim()} (${input.member_institution_ids.length} members)`,
        output_summary: `coalition ${coalitionId} proposed`,
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

  async openNegotiation(input: { coalition_id: string; actor_id: string }): Promise<{ round_number: number }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.transitionWithClient(client, {
        coalitionId: input.coalition_id, toStatus: 'negotiating',
        actorId: input.actor_id, reason: 'open negotiation', allowSame: true,
      });
      await client.query(
        `UPDATE coalition_members SET status = 'negotiating', updated_at = now()
          WHERE coalition_id = $1 AND status = 'invited'`,
        [input.coalition_id]
      );
      const next = await client.query<{ next: number }>(
        `SELECT COALESCE(MAX(round_number),0)+1 AS next FROM coalition_negotiation_rounds WHERE coalition_id = $1`,
        [input.coalition_id]
      );
      const roundNumber = Number(next.rows[0].next);
      const event = await eventLog.appendWithClient(client, {
        event_type: 'coalition.round_opened',
        actor_id: input.actor_id,
        object_type: 'coalition_negotiation_round',
        object_id: crypto.randomUUID(),
        correlation_id: crypto.randomUUID(),
        payload: { coalition_id: input.coalition_id, round_number: roundNumber },
      });
      await client.query(
        `INSERT INTO coalition_negotiation_rounds (coalition_id, round_number, opened_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4)`,
        [input.coalition_id, roundNumber, input.actor_id, event.id]
      );
      await client.query('COMMIT');
      return { round_number: roundNumber };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async submitProposal(input: {
    coalition_id: string;
    round_number: number;
    institution_id: string;
    actor_id: string;
    proposal: Record<string, unknown>;
    parent_proposal_id?: string;
  }): Promise<{ id: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.requireMember(client, input.coalition_id, input.institution_id);
      const round = await client.query(
        `SELECT id FROM coalition_negotiation_rounds WHERE coalition_id = $1 AND round_number = $2 AND status = 'open'`,
        [input.coalition_id, input.round_number]
      );
      if ((round.rowCount ?? 0) !== 1) throw new PublicHttpError(409, 'no open negotiation round with that number');
      const proposalId = crypto.randomUUID();
      const messageType = input.parent_proposal_id ? 'counterproposal' : 'proposal';
      if (input.parent_proposal_id) {
        await client.query(
          `UPDATE coalition_proposals SET status = 'superseded' WHERE id = $1 AND status = 'open'`,
          [input.parent_proposal_id]
        );
      }
      const event = await eventLog.appendWithClient(client, {
        event_type: `coalition.${messageType}_submitted`,
        actor_id: input.actor_id,
        object_type: 'coalition_proposal',
        object_id: proposalId,
        correlation_id: crypto.randomUUID(),
        payload: { coalition_id: input.coalition_id, round_number: input.round_number },
      });
      await client.query(
        `INSERT INTO coalition_proposals
           (id, coalition_id, round_number, proposed_by_institution_id, proposed_by_actor_id, proposal_json, parent_proposal_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7,$8)`,
        [proposalId, input.coalition_id, input.round_number, input.institution_id, input.actor_id,
         JSON.stringify(input.proposal), input.parent_proposal_id ?? null, event.id]
      );
      await this.postMessageWithClient(client, {
        coalition_id: input.coalition_id,
        institution_id: input.institution_id,
        actor_id: input.actor_id,
        message_type: messageType,
        body: `Proposal in round ${input.round_number}`,
        round_number: input.round_number,
      });
      await client.query('COMMIT');
      return { id: proposalId };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async recordDissent(input: {
    coalition_id: string; institution_id: string; actor_id: string; reason: string; round_number?: number;
  }): Promise<{ id: string }> {
    if (!input.reason || input.reason.trim().length === 0) throw new PublicHttpError(400, 'reason is required');
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.requireMember(client, input.coalition_id, input.institution_id);
      const dissentId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'coalition.dissent_recorded',
        actor_id: input.actor_id,
        object_type: 'coalition_dissent',
        object_id: dissentId,
        correlation_id: crypto.randomUUID(),
        payload: { coalition_id: input.coalition_id, institution_id: input.institution_id, reason: input.reason },
      });
      await client.query(
        `INSERT INTO coalition_dissents (id, coalition_id, institution_id, actor_id, reason, round_number, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7)`,
        [dissentId, input.coalition_id, input.institution_id, input.actor_id, input.reason, input.round_number ?? null, event.id]
      );
      await this.postMessageWithClient(client, {
        coalition_id: input.coalition_id, institution_id: input.institution_id, actor_id: input.actor_id,
        message_type: 'dissent', body: input.reason, round_number: input.round_number ?? null,
      });
      await client.query('COMMIT');
      return { id: dissentId };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Tally a round against the coalition's consensus rule using committed
   * members' acceptances. Deadlock (no approval under the rule) escalates to
   * governance rather than fabricating a winner.
   */
  async resolveConsensus(input: {
    coalition_id: string;
    round_number: number;
    actor_id: string;
    acceptances: Array<{ institution_id: string; weight?: number }>;
  }): Promise<{ outcome: 'approved' | 'rejected' | 'deadlocked'; escalation_id?: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const coalition = await client.query<{ consensus_rule: string; status: string }>(
        `SELECT consensus_rule, status FROM institution_coalitions WHERE id = $1 FOR UPDATE`,
        [input.coalition_id]
      );
      if ((coalition.rowCount ?? 0) !== 1) throw new PublicHttpError(404, 'coalition not found');
      const members = await client.query<{ institution_id: string }>(
        `SELECT institution_id FROM coalition_members
          WHERE coalition_id = $1 AND status IN ('negotiating','committed')`,
        [input.coalition_id]
      );
      const totalMembers = members.rowCount ?? 0;
      if (totalMembers === 0) throw new PublicHttpError(409, 'coalition has no active members to tally');
      const memberSet = new Set(members.rows.map(r => r.institution_id));
      const accepted = input.acceptances.filter(a => memberSet.has(a.institution_id));
      const acceptedCount = accepted.length;
      const rule = coalition.rows[0].consensus_rule;
      const totalWeight = accepted.reduce((sum, a) => sum + (a.weight ?? 1), 0);
      const weightBase = totalMembers; // 1.0 default weight per member

      let outcome: 'approved' | 'rejected' | 'deadlocked';
      if (rule === 'unanimous') {
        outcome = acceptedCount === totalMembers ? 'approved' : (acceptedCount === 0 ? 'rejected' : 'deadlocked');
      } else if (rule === 'majority') {
        outcome = acceptedCount * 2 > totalMembers ? 'approved'
          : (acceptedCount * 2 < totalMembers ? 'rejected' : 'deadlocked');
      } else {
        outcome = totalWeight * 2 > weightBase ? 'approved'
          : (totalWeight === 0 ? 'rejected' : 'deadlocked');
      }

      const event = await eventLog.appendWithClient(client, {
        event_type: 'coalition.consensus_resolved',
        actor_id: input.actor_id,
        object_type: 'coalition_consensus_result',
        object_id: crypto.randomUUID(),
        correlation_id: crypto.randomUUID(),
        payload: {
          coalition_id: input.coalition_id, round_number: input.round_number,
          rule, outcome, accepted: acceptedCount, total: totalMembers,
        },
      });
      await client.query(
        `INSERT INTO coalition_consensus_results
           (coalition_id, round_number, consensus_rule, outcome, tally_json, decided_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5::jsonb,$6,$7)`,
        [input.coalition_id, input.round_number, rule, outcome,
         JSON.stringify({ accepted: acceptedCount, total: totalMembers, total_weight: totalWeight }),
         input.actor_id, event.id]
      );
      await client.query(
        `UPDATE coalition_negotiation_rounds SET status = 'closed', closed_at = now()
          WHERE coalition_id = $1 AND round_number = $2`,
        [input.coalition_id, input.round_number]
      );

      let escalationId: string | undefined;
      if (outcome === 'deadlocked') {
        escalationId = await this.escalateWithClient(client, {
          coalition_id: input.coalition_id, actor_id: input.actor_id,
          escalation_type: 'deadlock', target: 'governance',
          reason: `consensus deadlocked in round ${input.round_number} under ${rule} rule`,
        });
      }
      await client.query('COMMIT');
      return { outcome, escalation_id: escalationId };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async commit(input: {
    coalition_id: string; institution_id: string; actor_id: string; commitment: Record<string, unknown>;
  }): Promise<{ id: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.requireMember(client, input.coalition_id, input.institution_id);
      const commitmentId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'coalition.commitment_accepted',
        actor_id: input.actor_id,
        object_type: 'coalition_commitment',
        object_id: commitmentId,
        correlation_id: crypto.randomUUID(),
        payload: { coalition_id: input.coalition_id, institution_id: input.institution_id },
      });
      await client.query(
        `INSERT INTO coalition_commitments
           (id, coalition_id, institution_id, commitment_json, status, offered_by_actor_id, accepted_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4::jsonb,'accepted',$5,$5,$6)`,
        [commitmentId, input.coalition_id, input.institution_id, JSON.stringify(input.commitment), input.actor_id, event.id]
      );
      await client.query(
        `UPDATE coalition_members SET status = 'committed', updated_at = now()
          WHERE coalition_id = $1 AND institution_id = $2`,
        [input.coalition_id, input.institution_id]
      );
      await client.query('COMMIT');
      return { id: commitmentId };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /** Constitute the coalition: every member must have an accepted commitment. */
  async constitute(input: { coalition_id: string; actor_id: string }): Promise<CoalitionRecord> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const members = await client.query<{ institution_id: string; status: string }>(
        `SELECT institution_id, status FROM coalition_members WHERE coalition_id = $1 AND status <> 'withdrawn'`,
        [input.coalition_id]
      );
      const uncommitted = members.rows.filter(m => m.status !== 'committed');
      if (uncommitted.length > 0) {
        throw new PublicHttpError(409, `membership requires accepted commitments; ${uncommitted.length} member(s) uncommitted`);
      }
      const record = await this.transitionWithClient(client, {
        coalitionId: input.coalition_id, toStatus: 'constituted',
        actorId: input.actor_id, reason: 'all members committed',
      });
      await client.query('COMMIT');
      return record;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async activate(input: { coalition_id: string; actor_id: string }): Promise<CoalitionRecord> {
    return this.simpleTransition(input.coalition_id, 'active', input.actor_id, 'coalition activated');
  }

  async grantDelegation(input: {
    coalition_id: string; from_institution_id: string; delegated_authority_key: string; granted_by_actor_id: string;
  }): Promise<{ id: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.requireMember(client, input.coalition_id, input.from_institution_id);
      const delegationId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'coalition.delegation_granted',
        actor_id: input.granted_by_actor_id,
        object_type: 'coalition_delegation',
        object_id: delegationId,
        correlation_id: crypto.randomUUID(),
        payload: {
          coalition_id: input.coalition_id, from_institution_id: input.from_institution_id,
          delegated_authority_key: input.delegated_authority_key,
        },
      });
      await client.query(
        `INSERT INTO coalition_delegations
           (id, coalition_id, from_institution_id, delegated_authority_key, granted_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6)
         ON CONFLICT (coalition_id, from_institution_id, delegated_authority_key) WHERE status = 'active'
         DO NOTHING`,
        [delegationId, input.coalition_id, input.from_institution_id, input.delegated_authority_key,
         input.granted_by_actor_id, event.id]
      );
      await client.query('COMMIT');
      return { id: delegationId };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /** Settle the coalition (records settlement, revokes delegations, moves to settled). */
  async settle(input: {
    coalition_id: string; actor_id: string; settlement: Record<string, unknown>;
  }): Promise<CoalitionRecord> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const current = await client.query<{ status: CoalitionStatus }>(
        `SELECT status FROM institution_coalitions WHERE id = $1 FOR UPDATE`,
        [input.coalition_id]
      );
      if ((current.rowCount ?? 0) !== 1) throw new PublicHttpError(404, 'coalition not found');
      if (current.rows[0].status !== 'active' && current.rows[0].status !== 'completing') {
        throw new PublicHttpError(409, `coalition must be active or completing to settle (is ${current.rows[0].status})`);
      }
      if (current.rows[0].status === 'active') {
        await this.transitionWithClient(client, {
          coalitionId: input.coalition_id, toStatus: 'completing',
          actorId: input.actor_id, reason: 'begin settlement',
        });
      }
      await this.recordSettlementWithClient(client, input.coalition_id, input.actor_id, input.settlement);
      await this.revokeDelegationsWithClient(client, input.coalition_id, input.actor_id);
      const record = await this.transitionWithClient(client, {
        coalitionId: input.coalition_id, toStatus: 'settled',
        actorId: input.actor_id, reason: 'settlement recorded',
      });
      await client.query('COMMIT');
      return record;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /** Fail or dissolve a coalition; settlement + delegation revocation still recorded. */
  async terminate(input: {
    coalition_id: string; actor_id: string; terminal_status: 'dissolved' | 'failed'; reason: string;
    settlement?: Record<string, unknown>;
  }): Promise<CoalitionRecord> {
    if (!input.reason || input.reason.trim().length === 0) throw new PublicHttpError(400, 'reason is required');
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.recordSettlementWithClient(
        client, input.coalition_id, input.actor_id,
        input.settlement ?? { terminal_status: input.terminal_status, reason: input.reason }
      );
      await this.revokeDelegationsWithClient(client, input.coalition_id, input.actor_id);
      const record = await this.transitionWithClient(client, {
        coalitionId: input.coalition_id, toStatus: input.terminal_status,
        actorId: input.actor_id, reason: input.reason, failureReason: input.terminal_status === 'failed' ? input.reason : undefined,
      });
      await client.query('COMMIT');
      return record;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async getCoalition(coalitionId: string): Promise<(CoalitionRecord & {
    members: Array<{ institution_id: string; status: string }>;
    dissents: number;
    delegations_active: number;
    settled: boolean;
  }) | null> {
    const coalition = await db.query<CoalitionRecord>(
      `SELECT ${COALITION_COLUMNS} FROM institution_coalitions WHERE id = $1 LIMIT 1`,
      [coalitionId]
    );
    if ((coalition.rowCount ?? 0) !== 1) return null;
    const [members, dissents, delegations, settlement] = await Promise.all([
      db.query(`SELECT institution_id, status FROM coalition_members WHERE coalition_id = $1`, [coalitionId]),
      db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM coalition_dissents WHERE coalition_id = $1`, [coalitionId]),
      db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM coalition_delegations WHERE coalition_id = $1 AND status = 'active'`, [coalitionId]),
      db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM coalition_settlements WHERE coalition_id = $1`, [coalitionId]),
    ]);
    return {
      ...coalition.rows[0],
      members: members.rows as any,
      dissents: Number(dissents.rows[0].count),
      delegations_active: Number(delegations.rows[0].count),
      settled: Number(settlement.rows[0].count) > 0,
    };
  }

  // -------------------------------------------------------------------------

  private async simpleTransition(coalitionId: string, toStatus: CoalitionStatus, actorId: string, reason: string): Promise<CoalitionRecord> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const record = await this.transitionWithClient(client, { coalitionId, toStatus, actorId, reason });
      await client.query('COMMIT');
      return record;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  private async transitionWithClient(client: PoolClient, input: {
    coalitionId: string; toStatus: CoalitionStatus; actorId: string; reason: string;
    allowSame?: boolean; failureReason?: string;
  }): Promise<CoalitionRecord> {
    const current = await client.query<CoalitionRecord>(
      `SELECT ${COALITION_COLUMNS} FROM institution_coalitions WHERE id = $1 FOR UPDATE`,
      [input.coalitionId]
    );
    if ((current.rowCount ?? 0) !== 1) throw new PublicHttpError(404, `coalition not found: ${input.coalitionId}`);
    const from = current.rows[0].status;
    if (from === input.toStatus && input.allowSame) return current.rows[0];
    if (TERMINAL.includes(from)) throw new PublicHttpError(409, `coalition is ${from} (terminal)`);
    if (!COALITION_TRANSITIONS[from]?.includes(input.toStatus)) {
      throw new PublicHttpError(409, `illegal coalition transition ${from} -> ${input.toStatus}`);
    }
    const terminal = TERMINAL.includes(input.toStatus);
    const event = await eventLog.appendWithClient(client, {
      event_type: 'coalition.status_changed',
      actor_id: input.actorId,
      object_type: 'institution_coalition',
      object_id: input.coalitionId,
      correlation_id: crypto.randomUUID(),
      payload: { from_status: from, to_status: input.toStatus, reason: input.reason },
    });
    await client.query(`SELECT set_config('civilization.coalition_transition_authorized', 'true', true)`);
    const updated = await client.query<CoalitionRecord>(
      `UPDATE institution_coalitions
          SET status = $2,
              failure_reason = COALESCE($3, failure_reason),
              closed_by_actor_id = CASE WHEN $4 THEN $5 ELSE closed_by_actor_id END,
              closed_at = CASE WHEN $4 THEN now() ELSE closed_at END
        WHERE id = $1
        RETURNING ${COALITION_COLUMNS}`,
      [input.coalitionId, input.toStatus, input.failureReason ?? null, terminal, input.actorId]
    );
    await client.query(`SELECT set_config('civilization.coalition_transition_authorized', 'false', true)`);
    await client.query(
      `INSERT INTO coalition_state_transitions (coalition_id, from_status, to_status, reason, actor_id, event_log_id)
       VALUES ($1,$2,$3,$4,$5,$6)`,
      [input.coalitionId, from, input.toStatus, input.reason, input.actorId, event.id]
    );
    await auditLog.appendWithClient(client, {
      agent_id: input.actorId,
      action_type: 'decision',
      input_summary: `coalition ${input.coalitionId} ${from} -> ${input.toStatus}: ${input.reason}`,
      output_summary: `coalition status is now ${input.toStatus}`,
      confidence_score: 1,
      risk_level: terminal ? 'high' : 'medium',
      human_approved: false,
      downstream_events: [event.id],
    }, { timestamp: new Date().toISOString() });
    return updated.rows[0];
  }

  private async recordSettlementWithClient(client: PoolClient, coalitionId: string, actorId: string, settlement: Record<string, unknown>): Promise<void> {
    const event = await eventLog.appendWithClient(client, {
      event_type: 'coalition.settled',
      actor_id: actorId,
      object_type: 'coalition_settlement',
      object_id: crypto.randomUUID(),
      correlation_id: crypto.randomUUID(),
      payload: { coalition_id: coalitionId },
    });
    await client.query(
      `INSERT INTO coalition_settlements (coalition_id, settlement_json, recorded_by_actor_id, event_log_id)
       VALUES ($1,$2::jsonb,$3,$4)
       ON CONFLICT (coalition_id) DO NOTHING`,
      [coalitionId, JSON.stringify(settlement), actorId, event.id]
    );
  }

  private async revokeDelegationsWithClient(client: PoolClient, coalitionId: string, actorId: string): Promise<void> {
    await client.query(
      `UPDATE coalition_delegations
          SET status = 'revoked', revoked_at = now(), revoked_by_actor_id = $2
        WHERE coalition_id = $1 AND status = 'active'`,
      [coalitionId, actorId]
    );
  }

  private async escalateWithClient(client: PoolClient, input: {
    coalition_id: string; actor_id: string;
    escalation_type: 'deadlock' | 'commitment_breach'; target: 'governance' | 'judiciary'; reason: string;
  }): Promise<string> {
    const escalationId = crypto.randomUUID();
    const event = await eventLog.appendWithClient(client, {
      event_type: 'coalition.escalated',
      actor_id: input.actor_id,
      object_type: 'coalition_escalation',
      object_id: escalationId,
      correlation_id: crypto.randomUUID(),
      payload: { coalition_id: input.coalition_id, escalation_type: input.escalation_type, target: input.target, reason: input.reason },
    });
    await client.query(
      `INSERT INTO coalition_escalations
         (id, coalition_id, escalation_type, target, reason, created_by_actor_id, event_log_id)
       VALUES ($1,$2,$3,$4,$5,$6,$7)`,
      [escalationId, input.coalition_id, input.escalation_type, input.target, input.reason, input.actor_id, event.id]
    );
    return escalationId;
  }

  private async postMessageWithClient(client: PoolClient, input: {
    coalition_id: string; institution_id: string; actor_id: string;
    message_type: string; body: string; round_number: number | null;
  }): Promise<void> {
    const thread = await client.query<{ id: string }>(
      `SELECT id FROM coalition_threads WHERE coalition_id = $1 ORDER BY created_at LIMIT 1`,
      [input.coalition_id]
    );
    let threadId = thread.rows[0]?.id;
    if (!threadId) {
      const created = await client.query<{ id: string }>(
        `INSERT INTO coalition_threads (coalition_id, topic, created_by_actor_id)
         VALUES ($1,'negotiation',$2) RETURNING id`,
        [input.coalition_id, input.actor_id]
      );
      threadId = created.rows[0].id;
    }
    await client.query(
      `INSERT INTO coalition_messages
         (thread_id, coalition_id, from_institution_id, from_actor_id, message_type, body, round_number)
       VALUES ($1,$2,$3,$4,$5,$6,$7)`,
      [threadId, input.coalition_id, input.institution_id, input.actor_id, input.message_type, input.body, input.round_number]
    );
  }

  private async requireMember(client: PoolClient, coalitionId: string, institutionId: string): Promise<void> {
    const member = await client.query(
      `SELECT id FROM coalition_members WHERE coalition_id = $1 AND institution_id = $2 AND status <> 'withdrawn'`,
      [coalitionId, institutionId]
    );
    if ((member.rowCount ?? 0) !== 1) {
      throw new PublicHttpError(409, `institution ${institutionId} is not an active member of this coalition`);
    }
  }

  private async requireRootId(client: PoolClient): Promise<string> {
    await civilizationKernel.ensureCivilizationRoot();
    const root = await client.query<{ id: string }>(`SELECT id FROM civilizations WHERE status = 'active' LIMIT 1`);
    if ((root.rowCount ?? 0) !== 1) throw new PublicHttpError(409, 'no active civilization root');
    return root.rows[0].id;
  }
}

export const coalitionService = new CoalitionService();
