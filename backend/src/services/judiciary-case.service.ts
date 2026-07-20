import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { auditLog } from './audit-log.service';
import { civilizationKernel } from './civilization-kernel.service';
import { treasuryService, ScopeType, EconomyResource } from './treasury.service';
import { citizenshipService } from './citizenship.service';
import { PublicHttpError } from '../http-errors';

/**
 * Civilization judiciary (build phase C8).
 *
 * Cases move opened -> jurisdiction_check -> evidence_collection -> hearing ->
 * ruling -> enforcement -> appeal -> final -> closed. The judiciary actor must
 * be independent of the disputed parties; the appellate panel must differ from
 * the trial judge. Enforcement orders mutate real runtime state (treasury
 * penalties, citizen sanctions). Duplicate final rulings are blocked by unique
 * indexes; precedent is searchable; dissent is retained.
 */

export type CaseStatus =
  | 'opened' | 'jurisdiction_check' | 'evidence_collection' | 'hearing' | 'ruling'
  | 'enforcement' | 'appeal' | 'final' | 'closed' | 'dismissed';

const CASE_TRANSITIONS: Record<CaseStatus, CaseStatus[]> = {
  opened: ['jurisdiction_check', 'dismissed'],
  jurisdiction_check: ['evidence_collection', 'dismissed'],
  evidence_collection: ['hearing', 'dismissed'],
  hearing: ['ruling'],
  ruling: ['enforcement', 'appeal', 'final'],
  enforcement: ['appeal', 'final'],
  appeal: ['final'],
  final: ['closed'],
  closed: [],
  dismissed: [],
};

export type DisputeType =
  | 'evidence_conflict' | 'claim_challenge' | 'prediction_resolution_challenge'
  | 'resource_dispute' | 'jurisdiction_conflict' | 'citizen_misconduct' | 'trust_appeal'
  | 'policy_conflict' | 'memory_retraction' | 'capability_revocation' | 'contract_breach';

export interface CaseRecord {
  id: string; civilization_id: string; dispute_type: DisputeType; title: string;
  complainant_actor_id: string; respondent_scope_type: string; respondent_scope_id: string;
  status: CaseStatus; assigned_institution_id: string | null;
}

const CASE_COLUMNS =
  'id, civilization_id, dispute_type, title, complainant_actor_id, respondent_scope_type, respondent_scope_id, status, assigned_institution_id';

const JUDICIARY_SOURCE_DISPUTE_UNIQUE_CONSTRAINT = 'uq_judiciary_cases_source_dispute_id';

export class JudiciaryCaseService {
  async openCase(input: {
    dispute_type: DisputeType; title: string; complainant_actor_id: string;
    respondent_scope_type: 'citizen' | 'institution' | 'coalition' | 'mission' | 'actor'; respondent_scope_id: string;
    source_dispute_id?: string; body?: Record<string, unknown>; civilization_id?: string;
  }): Promise<CaseRecord> {
    if (!input.title || input.title.trim().length === 0) throw new PublicHttpError(400, 'title is required');
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const civilizationId = input.civilization_id ?? (await this.rootId());
      const caseId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'judiciary.case_opened',
        actor_id: input.complainant_actor_id,
        object_type: 'judiciary_case',
        object_id: caseId,
        correlation_id: crypto.randomUUID(),
        payload: { dispute_type: input.dispute_type, respondent: `${input.respondent_scope_type}:${input.respondent_scope_id}` },
      });
      const inserted = await client.query<CaseRecord>(
        `INSERT INTO judiciary_cases
           (id, civilization_id, dispute_type, title, complainant_actor_id, respondent_scope_type, respondent_scope_id, source_dispute_id, body_json, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10)
         RETURNING ${CASE_COLUMNS}`,
        [caseId, civilizationId, input.dispute_type, input.title.trim(), input.complainant_actor_id,
         input.respondent_scope_type, input.respondent_scope_id, input.source_dispute_id ?? null,
         JSON.stringify(input.body ?? {}), event.id]
      );
      await client.query('COMMIT');
      return inserted.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      // AUD-013: migration 145's partial unique index (source_dispute_id IS NOT NULL) is the real
      // idempotency backstop -- it fires regardless of caller (retried HTTP request, a racing
      // orchestration tick, a direct-SQL writer), unlike a caller-side check-then-act guard split
      // across separate connections/transactions. On a genuine collision, return the case that
      // already exists for this dispute instead of surfacing a raw constraint-violation error.
      if (
        input.source_dispute_id &&
        (error as { code?: string; constraint?: string }).code === '23505' &&
        (error as { code?: string; constraint?: string }).constraint === JUDICIARY_SOURCE_DISPUTE_UNIQUE_CONSTRAINT
      ) {
        const existing = await db.query<CaseRecord>(
          `SELECT ${CASE_COLUMNS} FROM judiciary_cases WHERE source_dispute_id = $1`,
          [input.source_dispute_id]
        );
        if (existing.rowCount) return existing.rows[0];
      }
      throw error;
    } finally {
      client.release();
    }
  }

  async checkJurisdiction(input: { case_id: string; actor_id: string; assigned_institution_id?: string; accept: boolean }): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const c = await this.lockCase(client, input.case_id);
      if (c.status !== 'opened') throw new PublicHttpError(409, `case must be opened for jurisdiction check (is ${c.status})`);
      if (input.assigned_institution_id) {
        await client.query(`UPDATE judiciary_cases SET assigned_institution_id = $2 WHERE id = $1`, [input.case_id, input.assigned_institution_id]);
      }
      await this.setStatus(client, input.case_id, input.accept ? 'jurisdiction_check' : 'dismissed', input.actor_id,
        input.accept ? 'jurisdiction accepted' : 'jurisdiction declined');
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async openEvidenceCollection(caseId: string, actorId: string): Promise<void> {
    await this.simpleAdvance(caseId, 'jurisdiction_check', 'evidence_collection', actorId, 'evidence collection opened');
  }

  async submitEvidence(input: { case_id: string; submitted_by_actor_id: string; statement: string; evidence_id?: string }): Promise<{ id: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const c = await this.lockCase(client, input.case_id);
      if (c.status !== 'evidence_collection') throw new PublicHttpError(409, 'case is not collecting evidence');
      const subId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'judiciary.evidence_submitted',
        actor_id: input.submitted_by_actor_id,
        object_type: 'judiciary_evidence_submission',
        object_id: subId,
        correlation_id: crypto.randomUUID(),
        payload: { case_id: input.case_id },
      });
      await client.query(
        `INSERT INTO judiciary_evidence_submissions (id, case_id, submitted_by_actor_id, evidence_id, statement, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6)`,
        [subId, input.case_id, input.submitted_by_actor_id, input.evidence_id ?? null, input.statement, event.id]
      );
      await client.query('COMMIT');
      return { id: subId };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async holdHearing(input: { case_id: string; presiding_actor_id: string; summary: string }): Promise<{ id: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const c = await this.lockCase(client, input.case_id);
      if (c.status !== 'evidence_collection') throw new PublicHttpError(409, 'case is not ready for a hearing');
      await this.assertIndependent(c, input.presiding_actor_id, 'presiding judge');
      const hearingId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'judiciary.hearing_held',
        actor_id: input.presiding_actor_id,
        object_type: 'judiciary_hearing',
        object_id: hearingId,
        correlation_id: crypto.randomUUID(),
        payload: { case_id: input.case_id },
      });
      await client.query(
        `INSERT INTO judiciary_hearings (id, case_id, presiding_actor_id, summary, event_log_id)
         VALUES ($1,$2,$3,$4,$5)`,
        [hearingId, input.case_id, input.presiding_actor_id, input.summary, event.id]
      );
      await this.setStatus(client, input.case_id, 'hearing', input.presiding_actor_id, 'hearing held');
      await client.query('COMMIT');
      return { id: hearingId };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /** Issue the trial ruling. Judge must be independent of the disputed parties. */
  async issueRuling(input: {
    case_id: string; ruling_actor_id: string; outcome: 'upheld' | 'dismissed' | 'partial' | 'escalated';
    rationale: string; is_precedent?: boolean; principle?: string;
  }): Promise<{ ruling_id: string; precedent_id: string | null }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const c = await this.lockCase(client, input.case_id);
      if (c.status !== 'hearing') throw new PublicHttpError(409, `ruling requires a heard case (is ${c.status})`);
      await this.assertIndependent(c, input.ruling_actor_id, 'ruling judge');
      const rulingId = await this.insertRulingWithClient(client, {
        case_id: input.case_id, ruling_actor_id: input.ruling_actor_id, outcome: input.outcome,
        rationale: input.rationale, is_precedent: input.is_precedent ?? false, principle: input.principle,
        is_appellate: false, dispute_type: c.dispute_type, civilization_id: c.civilization_id,
      });
      await this.setStatus(client, input.case_id, 'ruling', input.ruling_actor_id, `ruling: ${input.outcome}`);
      await client.query('COMMIT');
      return rulingId;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Issue an enforcement order that mutates real runtime state. Requires a
   * ruling. Supported: resource_penalty (treasury), citizen_sanction, no_action.
   */
  async issueEnforcement(input: {
    case_id: string; issued_by_actor_id: string; order_type: 'resource_penalty' | 'citizen_sanction' | 'trust_adjustment' | 'capability_revocation' | 'policy_clarification' | 'no_action';
    target_scope_type: string; target_scope_id: string; detail?: Record<string, unknown>;
  }): Promise<{ order_id: string; applied_ref: string | null }> {
    const ruling = await db.query<{ id: string }>(
      `SELECT id FROM judiciary_rulings WHERE case_id = $1 AND is_appellate = false LIMIT 1`, [input.case_id]
    );
    if ((ruling.rowCount ?? 0) !== 1) throw new PublicHttpError(409, 'a trial ruling is required before enforcement');

    // Apply the real-world effect FIRST (its own transaction), then record the order.
    let appliedRef: string | null = null;
    const detail = input.detail ?? {};
    if (input.order_type === 'resource_penalty') {
      const penalty = await treasuryService.imposePenalty({
        target_scope: { type: input.target_scope_type as ScopeType, id: input.target_scope_id },
        resource_type: (detail.resource_type as EconomyResource) ?? 'llm_tokens',
        amount: Number(detail.amount ?? 0),
        reason: (detail.reason as string) ?? `judiciary enforcement for case ${input.case_id}`,
        authorized_decision_ref: `ruling:${ruling.rows[0].id}`,
        authority: 'judiciary',
        actor_id: input.issued_by_actor_id,
      });
      appliedRef = `penalty:${penalty.id}`;
    } else if (input.order_type === 'citizen_sanction') {
      const sanction = await citizenshipService.imposeSanction({
        citizen_id: input.target_scope_id,
        sanction_type: (detail.sanction_type as any) ?? 'restriction',
        reason: (detail.reason as string) ?? `judiciary enforcement for case ${input.case_id}`,
        imposed_by_actor_id: input.issued_by_actor_id,
        authorized_decision_ref: `ruling:${ruling.rows[0].id}`,
      });
      appliedRef = `sanction:${sanction.id}`;
    }

    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const c = await this.lockCase(client, input.case_id);
      if (c.status !== 'ruling') throw new PublicHttpError(409, `enforcement requires a ruled case (is ${c.status})`);
      const orderId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'judiciary.enforcement_issued',
        actor_id: input.issued_by_actor_id,
        object_type: 'judiciary_enforcement_order',
        object_id: orderId,
        correlation_id: crypto.randomUUID(),
        payload: { case_id: input.case_id, order_type: input.order_type, applied_ref: appliedRef },
      });
      await client.query(
        `INSERT INTO judiciary_enforcement_orders
           (id, case_id, ruling_id, order_type, target_scope_type, target_scope_id, detail_json, status, applied_ref, issued_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8,$9,$10,$11)`,
        [orderId, input.case_id, ruling.rows[0].id, input.order_type, input.target_scope_type, input.target_scope_id,
         JSON.stringify(detail), appliedRef ? 'applied' : 'issued', appliedRef, input.issued_by_actor_id, event.id]
      );
      await this.setStatus(client, input.case_id, 'enforcement', input.issued_by_actor_id, `enforcement: ${input.order_type}`);
      await auditLog.appendWithClient(client, {
        agent_id: input.issued_by_actor_id,
        action_type: 'decision',
        input_summary: `enforce ${input.order_type} on ${input.target_scope_type}:${input.target_scope_id} for case ${input.case_id}`,
        output_summary: `enforcement order ${orderId} ${appliedRef ? 'applied ' + appliedRef : 'issued'}`,
        confidence_score: 1, risk_level: 'high', human_approved: false,
        downstream_events: [event.id],
      }, { timestamp: new Date().toISOString() });
      await client.query('COMMIT');
      return { order_id: orderId, applied_ref: appliedRef };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async recordDissent(input: { ruling_id: string; actor_id: string; opinion: string }): Promise<{ id: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const dissentId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'judiciary.dissent_recorded',
        actor_id: input.actor_id,
        object_type: 'judiciary_dissent',
        object_id: dissentId,
        correlation_id: crypto.randomUUID(),
        payload: { ruling_id: input.ruling_id },
      });
      await client.query(
        `INSERT INTO judiciary_dissents (id, ruling_id, actor_id, opinion, event_log_id) VALUES ($1,$2,$3,$4,$5)`,
        [dissentId, input.ruling_id, input.actor_id, input.opinion, event.id]
      );
      await client.query('COMMIT');
      return { id: dissentId };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /** File an appeal against the trial ruling. */
  async fileAppeal(input: { case_id: string; appellant_actor_id: string; grounds: string }): Promise<{ appeal_id: string }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const c = await this.lockCase(client, input.case_id);
      if (c.status !== 'ruling' && c.status !== 'enforcement') {
        throw new PublicHttpError(409, `appeal requires a ruled/enforced case (is ${c.status})`);
      }
      const ruling = await client.query<{ id: string }>(`SELECT id FROM judiciary_rulings WHERE case_id = $1 AND is_appellate = false`, [input.case_id]);
      const appealId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'judiciary.appeal_filed',
        actor_id: input.appellant_actor_id,
        object_type: 'judiciary_appeal',
        object_id: appealId,
        correlation_id: crypto.randomUUID(),
        payload: { case_id: input.case_id },
      });
      await client.query(
        `INSERT INTO judiciary_appeals (id, case_id, ruling_id, appellant_actor_id, grounds, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6)`,
        [appealId, input.case_id, ruling.rows[0].id, input.appellant_actor_id, input.grounds, event.id]
      );
      await this.setStatus(client, input.case_id, 'appeal', input.appellant_actor_id, 'appeal filed');
      await client.query('COMMIT');
      return { appeal_id: appealId };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Rule on an appeal. The appellate judge must differ from the trial judge
   * (independent panel) and be independent of the parties. Finalizes the case.
   */
  async ruleOnAppeal(input: {
    case_id: string; appellate_actor_id: string; outcome: 'upheld' | 'dismissed' | 'partial'; rationale: string;
    is_precedent?: boolean; principle?: string;
  }): Promise<{ ruling_id: string; precedent_id: string | null }> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const c = await this.lockCase(client, input.case_id);
      if (c.status !== 'appeal') throw new PublicHttpError(409, 'no appeal pending on this case');
      await this.assertIndependent(c, input.appellate_actor_id, 'appellate judge');
      const trialRuling = await client.query<{ ruling_actor_id: string }>(
        `SELECT ruling_actor_id FROM judiciary_rulings WHERE case_id = $1 AND is_appellate = false`, [input.case_id]
      );
      if (trialRuling.rows[0].ruling_actor_id === input.appellate_actor_id) {
        throw new PublicHttpError(409, 'the appellate panel must be independent of the trial judge');
      }
      const result = await this.insertRulingWithClient(client, {
        case_id: input.case_id, ruling_actor_id: input.appellate_actor_id, outcome: input.outcome,
        rationale: input.rationale, is_precedent: input.is_precedent ?? false, principle: input.principle,
        is_appellate: true, dispute_type: c.dispute_type, civilization_id: c.civilization_id,
      });
      await client.query(`UPDATE judiciary_appeals SET status = 'ruled' WHERE case_id = $1`, [input.case_id]);
      await this.setStatus(client, input.case_id, 'final', input.appellate_actor_id, `appellate ruling: ${input.outcome}`);
      await client.query('COMMIT');
      return result;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async finalizeCase(input: { case_id: string; actor_id: string }): Promise<CaseRecord> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const c = await this.lockCase(client, input.case_id);
      let updated = c;
      if (c.status === 'ruling' || c.status === 'enforcement') {
        await this.setStatus(client, input.case_id, 'final', input.actor_id, 'case finalized (no appeal)');
      }
      await this.setStatus(client, input.case_id, 'closed', input.actor_id, 'case closed');
      updated = (await client.query<CaseRecord>(`SELECT ${CASE_COLUMNS} FROM judiciary_cases WHERE id = $1`, [input.case_id])).rows[0];
      await client.query('COMMIT');
      return updated;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async findPrecedents(input: { dispute_type: string; outcome?: string }): Promise<Array<{ principle: string; outcome: string; ruling_id: string }>> {
    const result = input.outcome
      ? await db.query(`SELECT principle, outcome, ruling_id FROM judiciary_precedents WHERE dispute_type = $1 AND outcome = $2 ORDER BY created_at DESC`, [input.dispute_type, input.outcome])
      : await db.query(`SELECT principle, outcome, ruling_id FROM judiciary_precedents WHERE dispute_type = $1 ORDER BY created_at DESC`, [input.dispute_type]);
    return result.rows as any;
  }

  async getCase(caseId: string): Promise<(CaseRecord & { rulings: number; enforcement_orders: number; appealed: boolean }) | null> {
    const c = await db.query<CaseRecord>(`SELECT ${CASE_COLUMNS} FROM judiciary_cases WHERE id = $1`, [caseId]);
    if ((c.rowCount ?? 0) !== 1) return null;
    const [rulings, orders, appeals] = await Promise.all([
      db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM judiciary_rulings WHERE case_id = $1`, [caseId]),
      db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM judiciary_enforcement_orders WHERE case_id = $1`, [caseId]),
      db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM judiciary_appeals WHERE case_id = $1`, [caseId]),
    ]);
    return {
      ...c.rows[0],
      rulings: Number(rulings.rows[0].count),
      enforcement_orders: Number(orders.rows[0].count),
      appealed: Number(appeals.rows[0].count) > 0,
    };
  }

  // -------------------------------------------------------------------------

  private async insertRulingWithClient(client: PoolClient, input: {
    case_id: string; ruling_actor_id: string; outcome: string; rationale: string;
    is_precedent: boolean; principle?: string; is_appellate: boolean; dispute_type: string; civilization_id: string;
  }): Promise<{ ruling_id: string; precedent_id: string | null }> {
    const rulingId = crypto.randomUUID();
    const signature = crypto.createHash('sha256')
      .update(`${input.case_id}|${input.ruling_actor_id}|${input.outcome}|${input.rationale}|${input.is_appellate}`)
      .digest('hex');
    const event = await eventLog.appendWithClient(client, {
      event_type: input.is_appellate ? 'judiciary.appellate_ruling_issued' : 'judiciary.ruling_issued',
      actor_id: input.ruling_actor_id,
      object_type: 'judiciary_ruling',
      object_id: rulingId,
      correlation_id: crypto.randomUUID(),
      payload: { case_id: input.case_id, outcome: input.outcome, is_appellate: input.is_appellate },
    });
    await client.query(
      `INSERT INTO judiciary_rulings
         (id, case_id, ruling_actor_id, outcome, rationale, is_precedent, principle, signature, is_appellate, event_log_id)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)`,
      [rulingId, input.case_id, input.ruling_actor_id, input.outcome, input.rationale,
       input.is_precedent, input.principle ?? null, signature, input.is_appellate, event.id]
    );
    let precedentId: string | null = null;
    if (input.is_precedent) {
      if (!input.principle || input.principle.trim().length === 0) {
        throw new PublicHttpError(400, 'a precedent ruling requires a principle');
      }
      precedentId = crypto.randomUUID();
      await client.query(
        `INSERT INTO judiciary_precedents (id, civilization_id, ruling_id, dispute_type, principle, outcome, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7) ON CONFLICT (ruling_id) DO NOTHING`,
        [precedentId, input.civilization_id, rulingId, input.dispute_type, input.principle, input.outcome, event.id]
      );
    }
    await auditLog.appendWithClient(client, {
      agent_id: input.ruling_actor_id,
      action_type: 'decision',
      input_summary: `${input.is_appellate ? 'appellate ' : ''}ruling on case ${input.case_id}: ${input.outcome}`,
      output_summary: `ruling ${rulingId} signed ${signature.slice(0, 12)}`,
      confidence_score: 1, risk_level: 'high', human_approved: false,
      downstream_events: [event.id],
    }, { timestamp: new Date().toISOString() });
    return { ruling_id: rulingId, precedent_id: precedentId };
  }

  /** The judge/panel must not be a party to the case. */
  private async assertIndependent(c: CaseRecord, judgeActorId: string, role: string): Promise<void> {
    if (c.complainant_actor_id === judgeActorId) {
      throw new PublicHttpError(409, `${role} cannot be the complainant (judiciary independence)`);
    }
    if (c.respondent_scope_type === 'actor' && c.respondent_scope_id === judgeActorId) {
      throw new PublicHttpError(409, `${role} cannot be the respondent (judiciary independence)`);
    }
    if (c.respondent_scope_type === 'citizen') {
      const citizen = await db.query<{ actor_id: string }>(`SELECT actor_id FROM citizens WHERE id = $1`, [c.respondent_scope_id]);
      if (citizen.rows[0]?.actor_id === judgeActorId) {
        throw new PublicHttpError(409, `${role} cannot be the respondent citizen (judiciary independence)`);
      }
    }
  }

  private async simpleAdvance(caseId: string, from: CaseStatus, to: CaseStatus, actorId: string, reason: string): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const c = await this.lockCase(client, caseId);
      if (c.status !== from) throw new PublicHttpError(409, `case must be ${from} (is ${c.status})`);
      await this.setStatus(client, caseId, to, actorId, reason);
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  private async setStatus(client: PoolClient, caseId: string, to: CaseStatus, actorId: string, reason: string): Promise<void> {
    const current = await client.query<{ status: CaseStatus }>(`SELECT status FROM judiciary_cases WHERE id = $1`, [caseId]);
    const from = current.rows[0].status;
    if (from !== to && !CASE_TRANSITIONS[from]?.includes(to)) {
      throw new PublicHttpError(409, `illegal case transition ${from} -> ${to}`);
    }
    const event = await eventLog.appendWithClient(client, {
      event_type: 'judiciary.case_status_changed',
      actor_id: actorId,
      object_type: 'judiciary_case',
      object_id: caseId,
      correlation_id: crypto.randomUUID(),
      payload: { from_status: from, to_status: to, reason },
    });
    await client.query(`SELECT set_config('civilization.judiciary_transition_authorized', 'true', true)`);
    await client.query(`UPDATE judiciary_cases SET status = $2 WHERE id = $1`, [caseId, to]);
    await client.query(`SELECT set_config('civilization.judiciary_transition_authorized', 'false', true)`);
    await client.query(
      `INSERT INTO judiciary_case_transitions (case_id, from_status, to_status, reason, actor_id, event_log_id)
       VALUES ($1,$2,$3,$4,$5,$6)`,
      [caseId, from, to, reason, actorId, event.id]
    );
  }

  private async lockCase(client: PoolClient, caseId: string): Promise<CaseRecord> {
    const result = await client.query<CaseRecord>(`SELECT ${CASE_COLUMNS} FROM judiciary_cases WHERE id = $1 FOR UPDATE`, [caseId]);
    if ((result.rowCount ?? 0) !== 1) throw new PublicHttpError(404, `case not found: ${caseId}`);
    return result.rows[0];
  }

  private async rootId(): Promise<string> {
    const root = await civilizationKernel.ensureCivilizationRoot();
    return root.id;
  }
}

export const judiciaryCaseService = new JudiciaryCaseService();
