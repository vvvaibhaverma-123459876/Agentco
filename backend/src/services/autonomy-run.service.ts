/**
 * Autonomy Run (D1 / D10)
 * =======================
 * The single, first-class path that composes the full learning chain in ONE
 * uninterrupted call:
 *
 *   fetch real evidence -> mint grounded claims (orchestrator loop)
 *   -> register a prediction per grounded claim
 *   -> resolve predictions from the SAME fetched evidence (grounded resolver,
 *      through the resolution_service firewall)
 *   -> auto-promote resolved lessons (existing hook, gated + audited)
 *   -> emit a user-readable deliverable citing each claim to its sha256 row
 *
 * A second run on a related goal retrieves and uses the promoted lesson. This
 * service is what the `autonomy` CLI, the unattended long-run, and the
 * real-world deliverable probes all call — no bespoke stitching.
 */

import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { Pool } from 'pg';
import { db } from '../db/client';
import { resolutionServiceDatabaseUrl } from '../db/dsn';
import { AutonomyOrchestratorService } from './autonomy-orchestrator.service';
import { ledgerResolutionService } from './resolution-service.service';
import { groundedResolver } from './grounded-resolver.service';
import { autonomousPromotion } from './autonomous-promotion.service';

const RUN_AGENT = 'autonomy_action_planner';

export interface AutonomyRunResult {
  goalId: string;
  runId: string;
  goalText: string;
  iterations: number;
  claims: number;
  predictionsRegistered: number;
  predictionsResolved: number;
  lessonsPromoted: number;
  deliverablePath: string | null;
  evidenceUrls: string[];
}

// Firewall DSN comes from the shared resolver so prediction writes and
// resolutions can never target different databases (G1).
const serviceDatabaseUrl = resolutionServiceDatabaseUrl;

export class AutonomyRunService {
  private orchestrator = new AutonomyOrchestratorService();

  async run(options: {
    goal: string;
    maxIterations?: number;
    outputDir?: string;
    writeDeliverable?: boolean;
  }): Promise<AutonomyRunResult> {
    const maxIterations = Math.max(1, Math.min(options.maxIterations ?? 6, 60));
    const runId = `autorun_${Date.now()}_${crypto.randomUUID().slice(0, 6)}`;

    // 1) fetch -> grounded claims
    const loop = await this.orchestrator.executeAutonomyActionLoop(options.goal, maxIterations);
    const goalId = loop.goalId;

    const claims = await db.query<{ claim_id: string; text: string; support_source_ids: string[]; support_snippets: unknown[] }>(
      `SELECT claim_id, text, support_source_ids, support_snippets
         FROM autonomy_claims
        WHERE goal_id = $1 AND status = 'supported'
        ORDER BY generated_at ASC`,
      [goalId]
    );

    // 2) register a prediction per grounded claim
    const domain = 'autonomy_research';
    const predictionIds: string[] = [];
    for (const claim of claims.rows) {
      const evidenceIds = Array.isArray(claim.support_source_ids) ? claim.support_source_ids : [];
      if (evidenceIds.length === 0) continue;
      const predictionId = await ledgerResolutionService.registerPrediction({
        claim: claim.text,
        probability: 0.8,
        confidence_basis: { claim_id: claim.claim_id, evidence_source_ids: evidenceIds },
        producing_agent_id: RUN_AGENT,
        producing_prompt_version: 'autonomy-run-v1',
        resolution_criterion: 'the claim is supported by the fetched evidence it cites',
        resolution_date: new Date(Date.now() - 1000),
        ground_truth_source: `agentco://run/${runId}`,
        horizon_class: 'short',
        domain,
        claim_type: 'grounded_claim_quality',
        correlation_id: crypto.randomUUID(),
      });
      predictionIds.push(predictionId);
    }

    // 3) resolve predictions from the SAME fetched evidence (firewall path)
    let resolved = 0;
    if (predictionIds.length > 0) {
      const servicePool = new Pool({ connectionString: serviceDatabaseUrl(), max: 2 });
      try {
        const client = await servicePool.connect();
        try {
          for (let i = 0; i < predictionIds.length; i++) {
            const claim = claims.rows[i];
            const snippet = this.firstSnippet(claim.support_snippets);
            if (!snippet) continue;
            const result = await groundedResolver.resolveFromEvidence({
              predictionId: predictionIds[i],
              evidenceSourceIds: Array.isArray(claim.support_source_ids) ? claim.support_source_ids : [],
              resolvedOutcome: true, // the claim was grounded in the evidence it cites
              justification: snippet,
              serviceClient: client,
            });
            if (result.resolved) resolved++;
          }
        } finally {
          client.release();
        }
      } finally {
        await servicePool.end();
      }
    }

    // 4) auto-promote resolved lessons (gated + audited)
    const promotion = await autonomousPromotion.promoteResolvedForRun({ runId, agentId: RUN_AGENT });

    // 5) deliverable
    let deliverablePath: string | null = null;
    const evidenceUrls = await this.evidenceUrls(goalId);
    if (options.writeDeliverable !== false) {
      deliverablePath = await this.writeDeliverable(options, runId, goalId, claims.rows, evidenceUrls);
    }

    return {
      goalId,
      runId,
      goalText: options.goal,
      iterations: maxIterations,
      claims: claims.rowCount ?? 0,
      predictionsRegistered: predictionIds.length,
      predictionsResolved: resolved,
      lessonsPromoted: promotion.promoted,
      deliverablePath,
      evidenceUrls,
    };
  }

  private firstSnippet(snippets: unknown[]): string | null {
    if (!Array.isArray(snippets)) return null;
    for (const s of snippets) {
      if (typeof s === 'string' && s.trim()) return s;
      if (s && typeof s === 'object' && typeof (s as any).snippet === 'string') return (s as any).snippet;
    }
    return null;
  }

  private async evidenceUrls(goalId: string): Promise<string[]> {
    const rows = await db.query<{ url: string }>(
      `SELECT DISTINCT e.url
         FROM autonomy_evidence e
         JOIN autonomy_goal_actions a ON a.action_id = e.action_id
        WHERE a.goal_id = $1`,
      [goalId]
    );
    return rows.rows.map(r => r.url);
  }

  private async writeDeliverable(
    options: { goal: string; outputDir?: string },
    runId: string,
    goalId: string,
    claims: Array<{ claim_id: string; text: string; support_source_ids: string[] }>,
    evidenceUrls: string[]
  ): Promise<string> {
    const outDir = options.outputDir ?? path.resolve(__dirname, '../../../outputs');
    fs.mkdirSync(outDir, { recursive: true });
    const file = path.join(outDir, `${runId}.md`);

    const lines: string[] = [
      `# AgentCo Deliverable`,
      ``,
      `**Goal:** ${options.goal}`,
      `**Run:** \`${runId}\` · goal \`${goalId}\` · generated ${new Date().toISOString()}`,
      ``,
    ];

    if (claims.length === 0) {
      lines.push(
        `## Insufficient evidence`,
        ``,
        `AgentCo could not fetch enough grounded evidence to make any claim about this goal, ` +
          `so it is reporting no findings rather than fabricating them.`,
        ``,
        evidenceUrls.length ? `Sources attempted: ${evidenceUrls.join(', ')}` : `No sources were reachable.`,
        ``
      );
    } else {
      lines.push(`## Findings (each cited to a hashed evidence row)`, ``);
      for (const claim of claims) {
        const ev = await db.query<{ url: string; content_hash: string }>(
          `SELECT url, content_hash FROM autonomy_evidence WHERE source_id = ANY($1::text[]) LIMIT 1`,
          [Array.isArray(claim.support_source_ids) ? claim.support_source_ids : []]
        );
        const src = ev.rows[0];
        lines.push(
          `- ${claim.text}`,
          `  - source: ${src?.url ?? 'n/a'} (${src?.content_hash ?? 'no hash'})`,
          ``
        );
      }
      lines.push(
        `## Provenance`,
        ``,
        `Every finding above is a claim that passed the token-subsequence grounding gate ` +
          `against a fetched, sha256-hashed evidence row. Claim ids and evidence source ids are ` +
          `queryable in \`autonomy_claims\` / \`autonomy_evidence\`.`,
        ``
      );
    }
    fs.writeFileSync(file, lines.join('\n'));
    return file;
  }
}

export const autonomyRun = new AutonomyRunService();
