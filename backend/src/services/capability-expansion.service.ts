import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { auditLog } from './audit-log.service';
import { civilizationKernel } from './civilization-kernel.service';
import { PublicHttpError } from '../http-errors';

/**
 * Capability and domain expansion (build phase C11).
 *
 * A domain or capability is admitted only through the complete gate:
 * proposed -> risk_review -> benchmark_design -> limited_trial ->
 * calibration_review -> governance_review -> approved. Approval requires every
 * stage passed, a competence proof, and an approver independent of the
 * proposer. Capability grants are versioned and scoped; restriction changes
 * routing immediately; revocation blocks new work.
 */

export type ExpansionStatus =
  | 'proposed' | 'risk_review' | 'benchmark_design' | 'limited_trial' | 'calibration_review'
  | 'governance_review' | 'approved' | 'restricted' | 'rejected' | 'monitored' | 'expanded' | 'revoked';

const STAGE_ORDER = ['risk_review', 'benchmark_design', 'limited_trial', 'calibration_review', 'governance_review'] as const;
type Stage = typeof STAGE_ORDER[number];

const TRANSITIONS: Record<ExpansionStatus, ExpansionStatus[]> = {
  proposed: ['risk_review', 'rejected'],
  risk_review: ['benchmark_design', 'rejected'],
  benchmark_design: ['limited_trial', 'rejected'],
  limited_trial: ['calibration_review', 'rejected'],
  calibration_review: ['governance_review', 'rejected'],
  governance_review: ['approved', 'restricted', 'rejected'],
  approved: ['monitored', 'revoked'],
  restricted: ['monitored', 'revoked', 'approved'],
  monitored: ['expanded', 'revoked'],
  rejected: [],
  expanded: ['revoked'],
  revoked: [],
};

export interface ProposalRecord {
  id: string; civilization_id: string; expansion_type: 'domain_onboarding' | 'capability_expansion';
  domain_key: string; capability_key: string | null; title: string; proposer_actor_id: string;
  competence_proof_id: string | null; status: ExpansionStatus;
}

const PROPOSAL_COLUMNS =
  'id, civilization_id, expansion_type, domain_key, capability_key, title, proposer_actor_id, competence_proof_id, status';

export class CapabilityExpansionService {
  async propose(input: {
    expansion_type: 'domain_onboarding' | 'capability_expansion'; domain_key: string; capability_key?: string;
    title: string; proposer_actor_id: string; competence_proof_id?: string; civilization_id?: string;
  }): Promise<ProposalRecord> {
    if (!input.title || !input.domain_key) throw new PublicHttpError(400, 'title and domain_key are required');
    if (input.expansion_type === 'capability_expansion' && !input.capability_key) {
      throw new PublicHttpError(400, 'capability_key is required for capability_expansion');
    }
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const civilizationId = input.civilization_id ?? (await this.rootId());
      const proposalId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'expansion.proposed',
        actor_id: input.proposer_actor_id,
        object_type: 'expansion_proposal',
        object_id: proposalId,
        correlation_id: crypto.randomUUID(),
        payload: { expansion_type: input.expansion_type, domain_key: input.domain_key, capability_key: input.capability_key ?? null },
      });
      const inserted = await client.query<ProposalRecord>(
        `INSERT INTO expansion_proposals
           (id, civilization_id, expansion_type, domain_key, capability_key, title, proposer_actor_id, competence_proof_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
         RETURNING ${PROPOSAL_COLUMNS}`,
        [proposalId, civilizationId, input.expansion_type, input.domain_key, input.capability_key ?? null,
         input.title, input.proposer_actor_id, input.competence_proof_id ?? null, event.id]
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

  /** Record a gate stage. Stages must be completed in order and each must pass to advance. */
  async recordStage(input: {
    proposal_id: string; stage: Stage; passed: boolean; summary: string; detail?: Record<string, unknown>; actor_id: string;
  }): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const p = await this.lock(client, input.proposal_id);
      const stageIndex = STAGE_ORDER.indexOf(input.stage);
      const expectedStatus: ExpansionStatus = stageIndex === 0 ? 'proposed' : STAGE_ORDER[stageIndex - 1] as ExpansionStatus;
      if (p.status !== expectedStatus && p.status !== input.stage) {
        throw new PublicHttpError(409, `stage ${input.stage} requires status ${expectedStatus} (is ${p.status})`);
      }
      const event = await eventLog.appendWithClient(client, {
        event_type: 'expansion.stage_recorded',
        actor_id: input.actor_id,
        object_type: 'expansion_stage_record',
        object_id: crypto.randomUUID(),
        correlation_id: crypto.randomUUID(),
        payload: { proposal_id: input.proposal_id, stage: input.stage, passed: input.passed },
      });
      await client.query(
        `INSERT INTO expansion_stage_records (proposal_id, stage, passed, summary, detail_json, recorded_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5::jsonb,$6,$7) ON CONFLICT (proposal_id, stage) DO NOTHING`,
        [input.proposal_id, input.stage, input.passed, input.summary, JSON.stringify(input.detail ?? {}), input.actor_id, event.id]
      );
      if (!input.passed) {
        await this.setStatus(client, input.proposal_id, 'rejected', input.actor_id, `stage ${input.stage} failed`);
      } else {
        await this.setStatus(client, input.proposal_id, input.stage as ExpansionStatus, input.actor_id, `stage ${input.stage} passed`);
      }
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Approve an expansion after governance review. Requires every gate stage
   * passed, a competence proof, and an approver independent of the proposer.
   */
  async approve(input: { proposal_id: string; approver_actor_id: string; restricted?: boolean }): Promise<ProposalRecord> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const updated = await this.approveWithClient(client, input);
      await client.query('COMMIT');
      return updated;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async approveWithClient(client: PoolClient, input: { proposal_id: string; approver_actor_id: string; restricted?: boolean }): Promise<ProposalRecord> {
    const p = await this.lock(client, input.proposal_id);
    if (p.status !== 'governance_review') {
      throw new PublicHttpError(409, `approval requires a governance-reviewed proposal (is ${p.status})`);
    }
    if (p.proposer_actor_id === input.approver_actor_id) {
      throw new PublicHttpError(409, 'the proposer cannot approve their own expansion');
    }
    if (!p.competence_proof_id) {
      throw new PublicHttpError(409, 'expansion approval requires a competence proof');
    }
    const stages = await client.query<{ count: string }>(
      `SELECT COUNT(*)::int AS count FROM expansion_stage_records WHERE proposal_id = $1 AND passed = true AND stage = ANY($2::text[])`,
      [input.proposal_id, [...STAGE_ORDER]]
    );
    if (Number(stages.rows[0].count) !== STAGE_ORDER.length) {
      throw new PublicHttpError(409, 'every gate stage must pass before approval');
    }
    const to: ExpansionStatus = input.restricted ? 'restricted' : 'approved';
    await this.setStatus(client, input.proposal_id, to, input.approver_actor_id, `governance ${to}`);
    const updated = await client.query<ProposalRecord>(`SELECT ${PROPOSAL_COLUMNS} FROM expansion_proposals WHERE id = $1`, [input.proposal_id]);
    await auditLog.appendWithClient(client, {
      agent_id: input.approver_actor_id,
      action_type: 'decision',
      input_summary: `expansion ${input.proposal_id} governance decision`,
      output_summary: `expansion ${to} (proof ${p.competence_proof_id})`,
      confidence_score: 1, risk_level: 'high', human_approved: true,
      downstream_events: [],
    }, { timestamp: new Date().toISOString() });
    return updated.rows[0];
  }

  // -------------------------------------------------------------------------
  // Capability grants, restrictions, revocations
  // -------------------------------------------------------------------------

  async grantCapability(input: {
    proposal_id: string; capability_key: string; domain_key: string;
    grantee_scope_type: 'institution' | 'citizen' | 'society'; grantee_scope_id: string; actor_id: string;
  }): Promise<{ grant_id: string; capability_id: string; version: number }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const p = await this.lock(client, input.proposal_id);
      if (p.status !== 'approved' && p.status !== 'restricted' && p.status !== 'monitored' && p.status !== 'expanded') {
        throw new PublicHttpError(409, `capability may only be granted from an approved expansion (is ${p.status})`);
      }
      // Ensure the capability exists (versioned).
      const cap = await client.query<{ id: string; current_version: number }>(
        `INSERT INTO capabilities (civilization_id, capability_key, domain_key, created_by_actor_id)
         VALUES ($1,$2,$3,$4)
         ON CONFLICT (civilization_id, capability_key, domain_key)
         DO UPDATE SET updated_at = now()
         RETURNING id, current_version`,
        [p.civilization_id, input.capability_key, input.domain_key, input.actor_id]
      );
      const capabilityId = cap.rows[0].id;
      const version = cap.rows[0].current_version;

      const grantId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'expansion.capability_granted',
        actor_id: input.actor_id,
        object_type: 'capability_grant',
        object_id: grantId,
        correlation_id: crypto.randomUUID(),
        payload: { capability_key: input.capability_key, grantee: `${input.grantee_scope_type}:${input.grantee_scope_id}`, version },
      });
      await client.query(
        `INSERT INTO capability_grants
           (id, capability_id, proposal_id, grantee_scope_type, grantee_scope_id, domain_key, version, granted_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)`,
        [grantId, capabilityId, input.proposal_id, input.grantee_scope_type, input.grantee_scope_id,
         input.domain_key, version, input.actor_id, event.id]
      );
      // Approved -> monitored on first grant.
      if (p.status === 'approved' || p.status === 'restricted') {
        await this.setStatus(client, input.proposal_id, 'monitored', input.actor_id, 'capability granted; monitoring');
      }
      await client.query('COMMIT');
      return { grant_id: grantId, capability_id: capabilityId, version };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async restrictCapability(input: { grant_id: string; actor_id: string; restriction: Record<string, unknown>; reason: string }): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const event = await eventLog.appendWithClient(client, {
        event_type: 'expansion.capability_restricted',
        actor_id: input.actor_id,
        object_type: 'capability_grant',
        object_id: input.grant_id,
        correlation_id: crypto.randomUUID(),
        payload: { reason: input.reason },
      });
      const updated = await client.query(
        `UPDATE capability_grants
            SET status = 'restricted', restriction_json = $2::jsonb, restricted_by_actor_id = $3, restricted_at = now()
          WHERE id = $1 AND status = 'active'`,
        [input.grant_id, JSON.stringify(input.restriction), input.actor_id]
      );
      if ((updated.rowCount ?? 0) !== 1) throw new PublicHttpError(409, 'grant not found or not active');
      void event;
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async revokeCapability(input: { grant_id: string; actor_id: string; reason: string }): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const event = await eventLog.appendWithClient(client, {
        event_type: 'expansion.capability_revoked',
        actor_id: input.actor_id,
        object_type: 'capability_grant',
        object_id: input.grant_id,
        correlation_id: crypto.randomUUID(),
        payload: { reason: input.reason },
      });
      const updated = await client.query(
        `UPDATE capability_grants
            SET status = 'revoked', revoked_by_actor_id = $2, revoked_at = now()
          WHERE id = $1 AND status IN ('active','restricted')`,
        [input.grant_id, input.actor_id]
      );
      if ((updated.rowCount ?? 0) !== 1) throw new PublicHttpError(409, 'grant not found or already revoked');
      await auditLog.appendWithClient(client, {
        agent_id: input.actor_id,
        action_type: 'decision',
        input_summary: `revoke capability grant ${input.grant_id}: ${input.reason}`,
        output_summary: 'capability revoked; new work blocked',
        confidence_score: 1, risk_level: 'high', human_approved: false,
        downstream_events: [event.id],
      }, { timestamp: new Date().toISOString() });
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * The routing check: is a capability actively granted to a scope for a domain?
   * `restricted` grants are NOT active for unrestricted work; `revoked` grants
   * are never active. This is what makes restriction/revocation change routing.
   */
  async isCapabilityActive(input: {
    capability_key: string; domain_key: string; grantee_scope_type: string; grantee_scope_id: string;
  }): Promise<{ active: boolean; status: string | null; version: number | null }> {
    const result = await db.query<{ status: string; version: number }>(
      `SELECT g.status, g.version
         FROM capability_grants g JOIN capabilities c ON c.id = g.capability_id
        WHERE c.capability_key = $1 AND g.domain_key = $2
          AND g.grantee_scope_type = $3 AND g.grantee_scope_id = $4
          AND g.status <> 'revoked'
        ORDER BY g.created_at DESC LIMIT 1`,
      [input.capability_key, input.domain_key, input.grantee_scope_type, input.grantee_scope_id]
    );
    if ((result.rowCount ?? 0) === 0) return { active: false, status: null, version: null };
    return { active: result.rows[0].status === 'active', status: result.rows[0].status, version: result.rows[0].version };
  }

  /** Fail-closed routing assertion for new work. */
  async assertCapabilityGranted(input: {
    capability_key: string; domain_key: string; grantee_scope_type: string; grantee_scope_id: string;
  }): Promise<void> {
    const check = await this.isCapabilityActive(input);
    if (!check.active) {
      throw new PublicHttpError(403, `capability '${input.capability_key}' is ${check.status ?? 'not granted'} for ${input.grantee_scope_type}:${input.grantee_scope_id} in ${input.domain_key}; new work blocked`);
    }
  }

  async getProposal(proposalId: string): Promise<(ProposalRecord & { stages_passed: number; grants: number }) | null> {
    const p = await db.query<ProposalRecord>(`SELECT ${PROPOSAL_COLUMNS} FROM expansion_proposals WHERE id = $1`, [proposalId]);
    if ((p.rowCount ?? 0) !== 1) return null;
    const [stages, grants] = await Promise.all([
      db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM expansion_stage_records WHERE proposal_id = $1 AND passed = true`, [proposalId]),
      db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM capability_grants WHERE proposal_id = $1`, [proposalId]),
    ]);
    return { ...p.rows[0], stages_passed: Number(stages.rows[0].count), grants: Number(grants.rows[0].count) };
  }

  // -------------------------------------------------------------------------

  private async setStatus(client: PoolClient, proposalId: string, to: ExpansionStatus, actorId: string, reason: string): Promise<void> {
    const current = await client.query<{ status: ExpansionStatus }>(`SELECT status FROM expansion_proposals WHERE id = $1`, [proposalId]);
    const from = current.rows[0].status;
    if (from !== to && !TRANSITIONS[from]?.includes(to)) {
      throw new PublicHttpError(409, `illegal expansion transition ${from} -> ${to}`);
    }
    const event = await eventLog.appendWithClient(client, {
      event_type: 'expansion.status_changed',
      actor_id: actorId,
      object_type: 'expansion_proposal',
      object_id: proposalId,
      correlation_id: crypto.randomUUID(),
      payload: { from_status: from, to_status: to, reason },
    });
    await client.query(`SELECT set_config('civilization.expansion_authorized', 'true', true)`);
    await client.query(
      `UPDATE expansion_proposals SET status = $2, reject_reason = $3 WHERE id = $1`,
      [proposalId, to, to === 'rejected' ? reason : null]
    );
    await client.query(`SELECT set_config('civilization.expansion_authorized', 'false', true)`);
    await client.query(
      `INSERT INTO expansion_proposal_transitions (proposal_id, from_status, to_status, reason, actor_id, event_log_id)
       VALUES ($1,$2,$3,$4,$5,$6)`,
      [proposalId, from, to, reason, actorId, event.id]
    );
  }

  private async lock(client: PoolClient, proposalId: string): Promise<ProposalRecord> {
    const result = await client.query<ProposalRecord>(`SELECT ${PROPOSAL_COLUMNS} FROM expansion_proposals WHERE id = $1 FOR UPDATE`, [proposalId]);
    if ((result.rowCount ?? 0) !== 1) throw new PublicHttpError(404, `proposal not found: ${proposalId}`);
    return result.rows[0];
  }

  private async rootId(): Promise<string> {
    const root = await civilizationKernel.ensureCivilizationRoot();
    return root.id;
  }
}

export const capabilityExpansion = new CapabilityExpansionService();
