import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';

export interface OpenContradictionDisputeInput {
  subject_claim_id: string;
  counter_claim_id: string;
  reason: string;
  evidence?: Record<string, unknown>;
  correlation_id?: string;
}

export interface DisputeRecord {
  id: string;
  dispute_type: string;
  status: string;
  subject_claim_id: string | null;
  counter_claim_id: string | null;
  contradiction_json: Record<string, unknown>;
  event_log_id: string | null;
}

export interface IssueRulingInput {
  dispute_id: string;
  outcome: 'subject_upheld' | 'counter_upheld' | 'both_rejected' | 'insufficient_evidence' | 'settled';
  rationale: string;
  precedent_flag?: boolean;
  principle?: string;
  correlation_id?: string;
}

export interface RulingRecord {
  id: string;
  dispute_id: string;
  outcome: string;
  rationale: string;
  precedent_flag: boolean;
  event_log_id: string | null;
}

export interface PrecedentRecord {
  id: string;
  ruling_id: string;
  dispute_type: string;
  outcome: string;
  principle: string;
  event_log_id: string | null;
}

function requireClaimId(value: string, field: string): void {
  if (!value.trim() || value.length > 36) {
    throw new Error(`${field} is required and must be at most 36 chars`);
  }
}

function requireUuid(value: string, field: string): void {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)) {
    throw new Error(`${field} must be a UUID`);
  }
}

export class DisputeRegistryService {
  async openContradictionDispute(input: OpenContradictionDisputeInput): Promise<DisputeRecord> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const dispute = await this.openContradictionDisputeWithClient(client, input);
      await client.query('COMMIT');
      return dispute;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async openContradictionDisputeWithClient(client: PoolClient, input: OpenContradictionDisputeInput): Promise<DisputeRecord> {
    requireClaimId(input.subject_claim_id, 'subject_claim_id');
    requireClaimId(input.counter_claim_id, 'counter_claim_id');
    if (input.subject_claim_id === input.counter_claim_id) {
      throw new Error('contradiction dispute requires two distinct claims');
    }
    if (!input.reason.trim()) throw new Error('reason is required');

    const [subjectClaimId, counterClaimId] = [input.subject_claim_id, input.counter_claim_id].sort();
    await this.requireClaims(client, [subjectClaimId, counterClaimId]);
    const existing = await client.query<DisputeRecord>(
      `SELECT id, dispute_type, status, subject_claim_id, counter_claim_id,
              contradiction_json, event_log_id
         FROM disputes
        WHERE dispute_type = 'claim_contradiction'
          AND subject_claim_id = $1
          AND counter_claim_id = $2
        LIMIT 1`,
      [subjectClaimId, counterClaimId]
    );
    if ((existing.rowCount ?? 0) > 0) return existing.rows[0];

    await this.linkClaims(client, subjectClaimId, counterClaimId);
    const disputeId = crypto.randomUUID();
    const actorId = await this.ensureServiceActor();
    const contradiction = {
      reason: input.reason,
      evidence: input.evidence ?? {},
      claims: [subjectClaimId, counterClaimId],
    };
    const event = await eventLog.appendWithClient(client, {
      event_type: 'dispute.opened',
      actor_id: actorId,
      object_type: 'dispute',
      object_id: disputeId,
      correlation_id: input.correlation_id,
      payload: {
        dispute_type: 'claim_contradiction',
        subject_claim_id: subjectClaimId,
        counter_claim_id: counterClaimId,
        reason: input.reason,
      },
    });

    const inserted = await client.query<DisputeRecord>(
      `INSERT INTO disputes
         (id, dispute_type, status, subject_claim_id, counter_claim_id,
          plaintiff_id, defendant_id, critical, opened_by_actor_id, contradiction_json, event_log_id)
       VALUES ($1,'claim_contradiction','opened',$2,$3,$4,$5,false,$6,$7::jsonb,$8)
       RETURNING id, dispute_type, status, subject_claim_id, counter_claim_id,
                 contradiction_json, event_log_id`,
      [
        disputeId,
        subjectClaimId,
        counterClaimId,
        subjectClaimId,
        counterClaimId,
        actorId,
        JSON.stringify(contradiction),
        event.id,
      ]
    );
    return inserted.rows[0];
  }

  private async requireClaims(client: PoolClient, claimIds: string[]): Promise<void> {
    const result = await client.query<{ claim_id: string }>(
      `SELECT claim_id FROM autonomy_claims WHERE claim_id = ANY($1::varchar[])`,
      [claimIds]
    );
    const found = new Set(result.rows.map((row) => row.claim_id));
    const missing = claimIds.filter((claimId) => !found.has(claimId));
    if (missing.length > 0) {
      throw new Error(`claim not found: ${missing.join(', ')}`);
    }
  }

  private async linkClaims(client: PoolClient, subjectClaimId: string, counterClaimId: string): Promise<void> {
    await client.query(
      `UPDATE autonomy_claims
          SET contradicted_by = CASE
                WHEN contradicted_by @> to_jsonb(ARRAY[$2]::text[]) THEN contradicted_by
                ELSE contradicted_by || to_jsonb(ARRAY[$2]::text[])
              END,
              status = 'contradicted'
        WHERE claim_id = $1`,
      [subjectClaimId, counterClaimId]
    );
    await client.query(
      `UPDATE autonomy_claims
          SET contradicts = CASE
                WHEN contradicts @> to_jsonb(ARRAY[$1]::text[]) THEN contradicts
                ELSE contradicts || to_jsonb(ARRAY[$1]::text[])
              END,
              status = 'contradicted'
        WHERE claim_id = $2`,
      [subjectClaimId, counterClaimId]
    );
  }

  private async ensureServiceActor(): Promise<string> {
    return ledgerResolutionService.ensureServiceActor('agentco-dispute-registry', [
      'judiciary.dispute.open',
    ]);
  }
}

export class RulingService {
  async issueRuling(input: IssueRulingInput): Promise<{ ruling: RulingRecord; precedent: PrecedentRecord | null }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const result = await this.issueRulingWithClient(client, input);
      await client.query('COMMIT');
      return result;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async issueRulingWithClient(
    client: PoolClient,
    input: IssueRulingInput
  ): Promise<{ ruling: RulingRecord; precedent: PrecedentRecord | null }> {
    requireUuid(input.dispute_id, 'dispute_id');
    if (!input.rationale.trim()) throw new Error('rationale is required');
    const dispute = await client.query<{ id: string; dispute_type: string; status: string }>(
      `SELECT id, dispute_type, status FROM disputes WHERE id = $1 LIMIT 1`,
      [input.dispute_id]
    );
    if ((dispute.rowCount ?? 0) !== 1) throw new Error(`dispute not found: ${input.dispute_id}`);
    if (['ruled', 'closed'].includes(dispute.rows[0].status)) {
      throw new Error('dispute already ruled or closed');
    }

    const rulingId = crypto.randomUUID();
    const actorId = await this.ensureServiceActor();
    const event = await eventLog.appendWithClient(client, {
      event_type: 'ruling.issued',
      actor_id: actorId,
      object_type: 'ruling',
      object_id: rulingId,
      correlation_id: input.correlation_id,
      payload: {
        dispute_id: input.dispute_id,
        outcome: input.outcome,
        precedent_flag: input.precedent_flag ?? false,
      },
    });

    const ruling = await client.query<RulingRecord>(
      `INSERT INTO rulings
         (id, dispute_id, judge_entity_id, ruling, penalty, appeal_deadline,
          outcome, rationale, precedent_flag, ruled_by_actor_id, event_log_id)
       VALUES ($1,$2,$6,$3,'{}'::jsonb,now() + INTERVAL '14 days',$3,$4,$5,$8,$7)
       RETURNING id, dispute_id, outcome, rationale, precedent_flag, event_log_id`,
      [
        rulingId,
        input.dispute_id,
        input.outcome,
        input.rationale,
        input.precedent_flag ?? false,
        actorId,
        event.id,
        actorId,
      ]
    );

    await client.query(
      `UPDATE disputes SET status = 'ruled', updated_at = now() WHERE id = $1`,
      [input.dispute_id]
    );

    let precedent: PrecedentRecord | null = null;
    if (input.precedent_flag) {
      precedent = await precedentStore.createPrecedentWithClient(client, {
        ruling_id: rulingId,
        dispute_type: dispute.rows[0].dispute_type,
        outcome: input.outcome,
        principle: input.principle ?? input.rationale,
        correlation_id: input.correlation_id,
      });
    }

    return { ruling: ruling.rows[0], precedent };
  }

  private async ensureServiceActor(): Promise<string> {
    return ledgerResolutionService.ensureServiceActor('agentco-ruling-service', [
      'judiciary.ruling.issue',
    ]);
  }
}

export class PrecedentStoreService {
  async createPrecedentWithClient(
    client: PoolClient,
    input: { ruling_id: string; dispute_type: string; outcome: string; principle: string; correlation_id?: string }
  ): Promise<PrecedentRecord> {
    if (!input.principle.trim()) throw new Error('principle is required');
    const existing = await client.query<PrecedentRecord>(
      `SELECT id, ruling_id, dispute_type, outcome, principle, event_log_id
         FROM precedents
        WHERE ruling_id = $1
        LIMIT 1`,
      [input.ruling_id]
    );
    if ((existing.rowCount ?? 0) > 0) return existing.rows[0];

    const precedentId = crypto.randomUUID();
    const actorId = await this.ensureServiceActor();
    const event = await eventLog.appendWithClient(client, {
      event_type: 'precedent.created',
      actor_id: actorId,
      object_type: 'precedent',
      object_id: precedentId,
      correlation_id: input.correlation_id,
      payload: {
        ruling_id: input.ruling_id,
        dispute_type: input.dispute_type,
        outcome: input.outcome,
      },
    });

    const inserted = await client.query<PrecedentRecord>(
      `INSERT INTO precedents
         (id, ruling_id, dispute_type, summary, outcome, principle, event_log_id)
       VALUES ($1,$2,$3,$5,$4,$5,$6)
       RETURNING id, ruling_id, dispute_type, outcome, principle, event_log_id`,
      [precedentId, input.ruling_id, input.dispute_type, input.outcome, input.principle, event.id]
    );
    return inserted.rows[0];
  }

  async findPrecedents(input: { dispute_type: string; outcome?: string }): Promise<PrecedentRecord[]> {
    const params: unknown[] = [input.dispute_type];
    let outcomeClause = '';
    if (input.outcome) {
      params.push(input.outcome);
      outcomeClause = `AND outcome = $${params.length}`;
    }
    const result = await db.query<PrecedentRecord>(
      `SELECT id, ruling_id, dispute_type, outcome, principle, event_log_id
         FROM precedents
        WHERE dispute_type = $1
          ${outcomeClause}
        ORDER BY created_at DESC`,
      params
    );
    return result.rows;
  }

  private async ensureServiceActor(): Promise<string> {
    return ledgerResolutionService.ensureServiceActor('agentco-precedent-store', [
      'judiciary.precedent.create',
    ]);
  }
}

export const disputeRegistry = new DisputeRegistryService();
export const precedentStore = new PrecedentStoreService();
export const rulingService = new RulingService();
