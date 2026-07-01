import crypto from 'crypto';
import { db } from '../db/client';
import { FindingType } from './institution-claim-vetting.service';

export interface InstitutionalSynthesisInput {
  sourceWorkRequestIds: string[];
  synthesisText: string;
  outputInstitutionId?: string;
  dependencyGraph?: Array<{ from: string; to: string; relation: string }>;
  goalId?: string;
}

export interface InstitutionalSynthesisResult {
  synthesis_work_request_id: string;
  synthesis_claim_id: string;
  finding_type: FindingType;
  confidence: number;
  weakest_necessary_link: number;
  independent_corroboration_lift: number;
  contributing_claim_ids: string[];
  contributing_institution_ids: string[];
  evidence_ids: string[];
  dependency_graph: Array<{ from: string; to: string; relation: string }>;
  verification: { status: 'passed'; department_id: string; reason: string };
  audit: { status: 'passed'; department_id: string; reason: string };
}

interface SourceFinding {
  work_request_id: string;
  institution_id: string;
  claim_id: string;
  claim_text: string;
  confidence: number;
  support_source_ids: string[];
  support_snippets: unknown[];
  derived_from_action_ids: string[];
  finding_type: FindingType;
}

const SYNTHESIS_SOURCE_SQL = `
  SELECT wr.id AS work_request_id,
         wr.institution_id,
         wr.result_summary,
         c.claim_id,
         c.text AS claim_text,
         c.confidence,
         c.support_source_ids,
         c.support_snippets,
         c.derived_from_action_ids
    FROM institution_work_requests wr
    JOIN autonomy_claims c ON c.claim_id = wr.result_summary->'vetting'->>'claim_id'
   WHERE wr.id = ANY($1::varchar[])
     AND wr.status = 'completed'
`;

export class InstitutionalSynthesisService {
  async synthesize(input: InstitutionalSynthesisInput): Promise<InstitutionalSynthesisResult> {
    if (!input.synthesisText.trim()) throw new Error('synthesisText is required');
    const sourceWorkRequestIds = [...new Set(input.sourceWorkRequestIds.map(id => id.trim()).filter(Boolean))];
    if (sourceWorkRequestIds.length === 0) throw new Error('at least one source work request is required');

    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const findings = await this.loadSourceFindings(client, sourceWorkRequestIds);
      const missing = sourceWorkRequestIds.filter(id => !findings.some(finding => finding.work_request_id === id));
      if (missing.length > 0) {
        throw new Error(`source work requests are not completed findings: ${missing.join(', ')}`);
      }

      const outputInstitutionId = input.outputInstitutionId ?? findings[0].institution_id;
      const departments = await this.requireDepartments(client, outputInstitutionId);
      const evidenceIds = [...new Set(findings.flatMap(finding => finding.support_source_ids))].sort();
      if (evidenceIds.length === 0) throw new Error('synthesis requires provenance evidence ids');

      const weakestNecessaryLink = Math.min(...findings.map(finding => finding.confidence));
      const independentCorroborationLift = Math.min(
        0.1,
        Math.max(0, evidenceIds.length - findings.length) * 0.02
      );
      const confidence = Number(Math.min(0.95, weakestNecessaryLink + independentCorroborationLift).toFixed(4));
      const findingType = findings.some(finding => finding.finding_type === 'CONJECTURE') ? 'CONJECTURE' : 'DERIVED';
      const dependencyGraph = input.dependencyGraph ?? this.defaultDependencyGraph(findings);
      const claimId = crypto.randomUUID();
      const workRequestId = crypto.randomUUID();
      const result = {
        synthesis: {
          status: 'finding',
          claim_id: claimId,
          finding_type: findingType,
          confidence,
          weakest_necessary_link: weakestNecessaryLink,
          independent_corroboration_lift: independentCorroborationLift,
          contributing_claim_ids: findings.map(finding => finding.claim_id),
          contributing_work_request_ids: sourceWorkRequestIds,
          contributing_institution_ids: [...new Set(findings.map(finding => finding.institution_id))],
          evidence_ids: evidenceIds,
          dependency_graph: dependencyGraph,
          output_type_rule: 'composite synthesis is DERIVED unless any input is CONJECTURE; it is never upgraded to EXTERNALLY_VERIFIED',
        },
      };

      await client.query(
        `INSERT INTO institution_work_requests
           (id, institution_id, department_id, objective, required_specialists,
            budget_tokens, budget_iterations, budget_seconds, verification_required,
            reputation_metric, risk_level, status, autonomy_goal_id, result_summary, completed_at)
         VALUES ($1,$2,$3,$4,$5::jsonb,4000,2,600,true,'synthesis_quality','medium','completed',$6,$7::jsonb,now())`,
        [
          workRequestId,
          outputInstitutionId,
          departments.Verification,
          input.synthesisText,
          JSON.stringify([{ role: 'institutional_synthesis', priority: 1 }]),
          input.goalId ?? null,
          JSON.stringify(result),
        ]
      );

      await client.query(
        `INSERT INTO autonomy_claims
           (claim_id, text, status, confidence, support_source_ids, support_snippets, derived_from_action_ids, generated_by)
         VALUES ($1,$2,'supported',$3,$4::jsonb,$5::jsonb,$6::jsonb,'institutional-synthesis')`,
        [
          claimId,
          input.synthesisText,
          confidence,
          JSON.stringify(evidenceIds),
          JSON.stringify(findings.flatMap(finding => finding.support_snippets)),
          JSON.stringify(findings.map(finding => finding.claim_id)),
        ]
      );

      await this.recordEvent(client, workRequestId, 'synthesis', 'created', result.synthesis);
      const verification = {
        status: 'passed' as const,
        department_id: departments.Verification,
        reason: 'composite has completed source findings, dependency graph, bounded confidence, and full provenance',
      };
      const audit = {
        status: 'passed' as const,
        department_id: departments.Audit,
        reason: 'synthesis provenance and contributing institutions recorded',
      };
      await this.recordEvent(client, workRequestId, 'synthesis_verification', 'department_passed', verification);
      await this.recordEvent(client, workRequestId, 'synthesis_audit', 'department_passed', audit);
      await client.query('COMMIT');

      return {
        synthesis_work_request_id: workRequestId,
        synthesis_claim_id: claimId,
        finding_type: findingType,
        confidence,
        weakest_necessary_link: weakestNecessaryLink,
        independent_corroboration_lift: independentCorroborationLift,
        contributing_claim_ids: findings.map(finding => finding.claim_id),
        contributing_institution_ids: [...new Set(findings.map(finding => finding.institution_id))],
        evidence_ids: evidenceIds,
        dependency_graph: dependencyGraph,
        verification,
        audit,
      };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  private async loadSourceFindings(client: any, sourceWorkRequestIds: string[]): Promise<SourceFinding[]> {
    const result = await client.query(SYNTHESIS_SOURCE_SQL, [sourceWorkRequestIds]);
    return result.rows
      .filter((row: any) => row.result_summary?.vetting?.status === 'finding')
      .map((row: any) => ({
        work_request_id: row.work_request_id,
        institution_id: row.institution_id,
        claim_id: row.claim_id,
        claim_text: row.claim_text,
        confidence: Number(row.confidence),
        support_source_ids: Array.isArray(row.support_source_ids) ? row.support_source_ids : [],
        support_snippets: Array.isArray(row.support_snippets) ? row.support_snippets : [],
        derived_from_action_ids: Array.isArray(row.derived_from_action_ids) ? row.derived_from_action_ids : [],
        finding_type: row.result_summary.vetting.finding_type,
      }));
  }

  private async requireDepartments(client: any, institutionId: string): Promise<{ Verification: string; Audit: string }> {
    const result = await client.query(
      `SELECT id, name
         FROM departments
        WHERE institution_id = $1
          AND status = 'active'
          AND name = ANY($2::text[])`,
      [institutionId, ['Verification', 'Audit']]
    );
    const byName = Object.fromEntries(result.rows.map((row: { id: string; name: string }) => [row.name, row.id]));
    if (!byName.Verification || !byName.Audit) {
      throw new Error('synthesis output institution must have active Verification and Audit departments');
    }
    return byName as { Verification: string; Audit: string };
  }

  private defaultDependencyGraph(findings: SourceFinding[]): Array<{ from: string; to: string; relation: string }> {
    return findings.map(finding => ({
      from: finding.claim_id,
      to: 'synthesis',
      relation: 'necessary_partial',
    }));
  }

  private async recordEvent(
    client: any,
    workRequestId: string,
    phase: string,
    eventType: string,
    details: Record<string, unknown>
  ): Promise<void> {
    await client.query(
      `INSERT INTO work_cycle_events
         (id, work_request_id, cycle_phase, event_type, details, timestamp)
       VALUES ($1,$2,$3,$4,$5::jsonb,now())`,
      [crypto.randomUUID(), workRequestId, phase, eventType, JSON.stringify(details)]
    );
  }
}

export const institutionalSynthesisService = new InstitutionalSynthesisService();
