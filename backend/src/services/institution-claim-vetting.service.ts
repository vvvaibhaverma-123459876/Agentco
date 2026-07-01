import crypto from 'crypto';
import { db } from '../db/client';

export type RigorTier = 'lite' | 'full';
export type FindingType = 'EXTERNALLY_VERIFIED' | 'DERIVED' | 'CONJECTURE';
export type VettingStatus = 'finding' | 'rejected';

export interface AdversarialReview {
  attempted_break: boolean;
  counter_hypothesis?: string;
  counter_evidence_ids?: string[];
  severity?: 'low' | 'medium' | 'high';
}

export interface VetClaimInput {
  workRequestId: string;
  claimId: string;
  rigorTier: RigorTier;
  findingType: FindingType;
  adversarialReview?: AdversarialReview;
}

export interface VettingStageResult {
  stage: 'Production' | 'Verification' | 'Adversarial' | 'Audit';
  status: 'passed' | 'failed' | 'skipped';
  department_id: string;
  reason: string;
}

export interface VettingResult {
  work_request_id: string;
  claim_id: string;
  rigor_tier: RigorTier;
  finding_type: FindingType;
  status: VettingStatus;
  stages: VettingStageResult[];
  reputation_adjustments_required: Array<{
    department_id: string;
    reason: string;
    delta: number;
  }>;
}

const DEPARTMENT_FLOW: VettingStageResult['stage'][] = ['Production', 'Verification', 'Adversarial', 'Audit'];

export class InstitutionClaimVettingService {
  async vetClaim(input: VetClaimInput): Promise<VettingResult> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const workRequest = await this.requireWorkRequest(client, input.workRequestId);
      const claim = await this.requireClaim(client, input.claimId);
      const departments = await this.requireDepartments(client, workRequest.institution_id);

      const stages: VettingStageResult[] = [];
      stages.push(this.pass('Production', departments.Production, 'claim drafted by institution production flow'));

      const verification = this.verifyClaimGrounding(claim, input.findingType);
      stages.push({
        stage: 'Verification',
        status: verification.ok ? 'passed' : 'failed',
        department_id: departments.Verification,
        reason: verification.reason,
      });

      if (!verification.ok) {
        return await this.finish(client, input, stages, 'rejected', 'unsupported');
      }

      if (input.rigorTier === 'full') {
        const adversarial = this.verifyAdversarialReview(input.adversarialReview);
        stages.push({
          stage: 'Adversarial',
          status: adversarial.ok ? 'passed' : 'failed',
          department_id: departments.Adversarial,
          reason: adversarial.reason,
        });
        if (!adversarial.ok) {
          return await this.finish(client, input, stages, 'rejected', 'contradicted', [
            {
              department_id: departments.Adversarial,
              reason: 'adversarial department failed to provide a substantive break attempt',
              delta: -0.03,
            },
          ]);
        }
      } else {
        stages.push({
          stage: 'Adversarial',
          status: 'skipped',
          department_id: departments.Adversarial,
          reason: 'lite rigor uses Production and Verification only',
        });
      }

      stages.push(this.pass('Audit', departments.Audit, 'provenance and department flow recorded'));
      return await this.finish(client, input, stages, 'finding', 'supported');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  private async requireWorkRequest(client: any, workRequestId: string): Promise<{ id: string; institution_id: string }> {
    const result = await client.query(
      `SELECT id, institution_id
         FROM institution_work_requests
        WHERE id = $1
        LIMIT 1`,
      [workRequestId]
    );
    if ((result.rowCount ?? 0) !== 1) throw new Error(`work request not found: ${workRequestId}`);
    return result.rows[0];
  }

  private async requireClaim(client: any, claimId: string): Promise<{
    claim_id: string;
    status: string | null;
    support_source_ids: unknown;
    support_snippets: unknown;
    derived_from_action_ids: unknown;
  }> {
    const result = await client.query(
      `SELECT claim_id, status, support_source_ids, support_snippets, derived_from_action_ids
         FROM autonomy_claims
        WHERE claim_id = $1
        LIMIT 1`,
      [claimId]
    );
    if ((result.rowCount ?? 0) !== 1) throw new Error(`claim not found: ${claimId}`);
    return result.rows[0];
  }

  private async requireDepartments(client: any, institutionId: string): Promise<Record<VettingStageResult['stage'], string>> {
    const result = await client.query(
      `SELECT id, name
         FROM departments
        WHERE institution_id = $1
          AND status = 'active'
          AND name = ANY($2::text[])`,
      [institutionId, DEPARTMENT_FLOW]
    );
    const byName = Object.fromEntries(result.rows.map((row: { id: string; name: string }) => [row.name, row.id]));
    for (const name of DEPARTMENT_FLOW) {
      if (!byName[name]) throw new Error(`institution missing active ${name} department`);
    }
    return byName as Record<VettingStageResult['stage'], string>;
  }

  private verifyClaimGrounding(
    claim: { support_source_ids: unknown; support_snippets: unknown; derived_from_action_ids: unknown },
    findingType: FindingType
  ): { ok: boolean; reason: string } {
    const sourceIds = Array.isArray(claim.support_source_ids) ? claim.support_source_ids : [];
    const snippets = Array.isArray(claim.support_snippets) ? claim.support_snippets : [];
    const derivedFrom = Array.isArray(claim.derived_from_action_ids) ? claim.derived_from_action_ids : [];
    if (sourceIds.length === 0) return { ok: false, reason: 'claim has no support_source_ids' };
    if (findingType === 'EXTERNALLY_VERIFIED' && snippets.length === 0) {
      return { ok: false, reason: 'externally verified finding requires support snippets' };
    }
    if (findingType === 'DERIVED' && derivedFrom.length === 0) {
      return { ok: false, reason: 'derived finding requires derived_from_action_ids' };
    }
    return { ok: true, reason: `${findingType} grounding checks passed` };
  }

  private verifyAdversarialReview(review?: AdversarialReview): { ok: boolean; reason: string } {
    if (!review?.attempted_break) return { ok: false, reason: 'full rigor requires an attempted adversarial break' };
    const counter = review.counter_hypothesis?.trim() ?? '';
    if (counter.length < 20) return { ok: false, reason: 'adversarial review must provide a substantive counter hypothesis' };
    return { ok: true, reason: 'adversarial break attempt recorded' };
  }

  private pass(stage: VettingStageResult['stage'], departmentId: string, reason: string): VettingStageResult {
    return { stage, status: 'passed', department_id: departmentId, reason };
  }

  private async finish(
    client: any,
    input: VetClaimInput,
    stages: VettingStageResult[],
    status: VettingStatus,
    claimStatus: 'supported' | 'unsupported' | 'contradicted',
    reputationAdjustmentsRequired: VettingResult['reputation_adjustments_required'] = []
  ): Promise<VettingResult> {
    const result: VettingResult = {
      work_request_id: input.workRequestId,
      claim_id: input.claimId,
      rigor_tier: input.rigorTier,
      finding_type: input.findingType,
      status,
      stages,
      reputation_adjustments_required: reputationAdjustmentsRequired,
    };
    for (const stage of stages) {
      await this.recordCycleEvent(client, input.workRequestId, stage);
    }
    await client.query(
      `UPDATE autonomy_claims
          SET status = $1
        WHERE claim_id = $2`,
      [claimStatus, input.claimId]
    );
    await client.query(
      `UPDATE institution_work_requests
          SET status = $1::varchar,
              result_summary = $2::jsonb,
              completed_at = CASE WHEN $1::varchar = 'completed' THEN now() ELSE completed_at END
        WHERE id = $3`,
      [status === 'finding' ? 'completed' : 'failed', JSON.stringify({ vetting: result }), input.workRequestId]
    );
    await client.query('COMMIT');
    return result;
  }

  private async recordCycleEvent(client: any, workRequestId: string, stage: VettingStageResult): Promise<void> {
    await client.query(
      `INSERT INTO work_cycle_events
        (id, work_request_id, cycle_phase, event_type, details, timestamp)
       VALUES ($1,$2,$3,$4,$5::jsonb,now())`,
      [
        crypto.randomUUID(),
        workRequestId,
        'claim_vetting',
        `department_${stage.status}`,
        JSON.stringify(stage),
      ]
    );
  }

}

export const institutionClaimVettingService = new InstitutionClaimVettingService();
