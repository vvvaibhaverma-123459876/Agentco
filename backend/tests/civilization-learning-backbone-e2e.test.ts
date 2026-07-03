/**
 * Civilization Learning Backbone E2E
 * ==================================
 * Proves the civilization is a PRODUCER of learning, not only a governor:
 *
 *   completed institutional findings (Production/Verification/Audit)
 *   -> institutional synthesis (composite DERIVED claim in autonomy_claims)
 *   -> InstitutionalKnowledgeBridge promotes it into durable agent_memories
 *   -> memory-retrieval surfaces it to the planner (same path the planner uses)
 *   -> a later planner prompt in the SAME domain carries the knowledge
 *   -> cross-society: a goal in a DIFFERENT domain whose text overlaps also
 *      retrieves it (shared memory substrate)
 *
 * Fail-closed guards are proven too: ungrounded / low-confidence / non-
 * institutional claims are blocked and recorded, never silently promoted.
 * Clean-room: no LLM, no web.
 */

import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { describe, expect, test, beforeAll } from '@jest/globals';
import { db } from '../src/db/client';
import { institutionsService } from '../src/services/institutions.service';
import { FindingType } from '../src/services/institution-claim-vetting.service';
import { civilizationLiveFlow } from '../src/services/civilization-live-flow.service';
import { institutionalKnowledgeBridge } from '../src/services/institutional-knowledge-bridge.service';
import { memoryRetrieval } from '../src/services/memory-retrieval.service';
import { AutonomyActionPlannerService } from '../src/services/autonomy-action-planner.service';

async function applyMigrations() {
  for (const name of [
    '004_decision_log.sql',
    '012_decision_log_chain.sql',
    '014_decision_log_immutability_triggers.sql',
    '015_agent_memories.sql',
    '017_agent_memories_lifecycle.sql',
    '050_autonomy_action_loop.sql',
    '052b_institutions.sql',
    '053_work_assignment_schema.sql',
    '062_runtime_schema_compatibility.sql',
    '079_identity_authority.sql',
    '080_event_log.sql',
    '083_transactional_outbox.sql',
    '113_institutional_knowledge_promotions.sql',
  ]) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await db.query(migration);
  }
}

async function sourceFinding(input: {
  institutionId: string;
  departmentId: string;
  claimId: string;
  workRequestId: string;
  text: string;
  confidence: number;
  sourceIds: string[];
  findingType: FindingType;
}): Promise<void> {
  await db.query(
    `INSERT INTO autonomy_claims
       (claim_id, text, status, confidence, support_source_ids, support_snippets, generated_by)
     VALUES ($1,$2,'supported',$3,$4::jsonb,$5::jsonb,'synthesis-test')`,
    [
      input.claimId,
      input.text,
      input.confidence,
      JSON.stringify(input.sourceIds),
      JSON.stringify(input.sourceIds.map(sourceId => ({ source_id: sourceId, snippet: input.text }))),
    ]
  );
  await db.query(
    `INSERT INTO institution_work_requests
       (id, institution_id, department_id, objective, required_specialists,
        budget_tokens, budget_iterations, budget_seconds, verification_required,
        reputation_metric, risk_level, status, result_summary, completed_at)
     VALUES ($1,$2,$3,$4,'[]'::jsonb,1000,1,300,true,'evidence_quality','medium','completed',$5::jsonb,now())`,
    [
      input.workRequestId,
      input.institutionId,
      input.departmentId,
      input.text,
      JSON.stringify({
        vetting: {
          work_request_id: input.workRequestId,
          claim_id: input.claimId,
          rigor_tier: 'full',
          finding_type: input.findingType,
          status: 'finding',
          stages: [],
          reputation_adjustments_required: [],
        },
      }),
    ]
  );
}

async function buildInstitutionWithFindings(domain: string, texts: string[]): Promise<{
  institutionId: string;
  workRequestIds: string[];
}> {
  const suffix = crypto.randomUUID().slice(0, 8);
  const institution = await institutionsService.createCanonicalInstitution({
    name: `backbone_${domain}_${suffix}`,
    domain,
    purpose: 'Civilization learning backbone society',
    authorityScope: ['institutional_synthesis'],
  });
  const production = institution.departments.find(d => d.name === 'Production')!;
  const workRequestIds: string[] = [];
  let i = 0;
  for (const text of texts) {
    const workRequestId = `wr-${domain}-${suffix}-${i}`;
    await sourceFinding({
      institutionId: institution.institutionId,
      departmentId: production.id,
      claimId: `cl-${domain}-${suffix}-${i}`,
      workRequestId,
      text,
      confidence: 0.85,
      sourceIds: [`ev-${domain}-${suffix}-${i}-a`, `ev-${domain}-${suffix}-${i}-b`],
      findingType: 'EXTERNALLY_VERIFIED',
    });
    workRequestIds.push(workRequestId);
    i += 1;
  }
  return { institutionId: institution.institutionId, workRequestIds };
}

describe('civilization learning backbone', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('institution-produced knowledge becomes durable memory the planner reuses', async () => {
    const domain = `backbone_${Date.now()}`;
    const marker = `photonic_${Date.now()}`;
    const { workRequestIds } = await buildInstitutionWithFindings(domain, [
      `Finding A: ${marker} lattice cooling holds below 4 kelvin under load.`,
      `Finding B: ${marker} lattice cooling depends on two independent shielding sources.`,
    ]);

    // Civilization synthesizes the findings and promotes the composite into
    // durable memory in one call.
    const synthText = `Institutional consensus: ${marker} lattice cooling is reliable below 4 kelvin when double-shielded.`;
    const outcome = await civilizationLiveFlow.synthesizeAndPromoteKnowledge({
      sourceWorkRequestIds: workRequestIds,
      synthesisText: synthText,
      domain,
    });
    expect(outcome.promotion.promoted).toBe(true);
    expect(outcome.promotion.memoryId).toMatch(/^[0-9a-f-]{36}$/);

    // The promotion is recorded with event lineage.
    const promoRow = await db.query<{ promoted: boolean; memory_id: string; event_log_id: string }>(
      `SELECT promoted, memory_id, event_log_id FROM institutional_knowledge_promotions WHERE institutional_claim_id = $1`,
      [outcome.synthesisClaimId]
    );
    expect(promoRow.rows[0].promoted).toBe(true);
    const event = await db.query(
      `SELECT id FROM event_log WHERE id = $1 AND event_type = 'institution.knowledge_promoted'`,
      [promoRow.rows[0].event_log_id]
    );
    expect(event.rowCount).toBe(1);

    // The knowledge is retrievable via the SAME path the planner uses...
    const memories = await memoryRetrieval.retrieveForPlanning({
      goalText: `Research ${marker} lattice cooling reliability`,
      domain,
    });
    expect(memories.map(m => m.id)).toContain(outcome.promotion.memoryId);
    const retrieved = memories.find(m => m.id === outcome.promotion.memoryId)!;
    expect(retrieved.memoryType).toBe('semantic');
    expect(retrieved.namespace).toBe('institutional_knowledge');
    expect(retrieved.summary).toBe(synthText);

    // ...and it lands in the planner's decision prompt.
    const planner = new AutonomyActionPlannerService();
    const prompt = planner.buildDecisionPrompt({
      goalText: `Research ${marker} lattice cooling reliability`,
      claimsGenerated: 0,
      evidenceCount: 0,
      loopDetection: { isLooping: false } as any,
      memoryContext: memoryRetrieval.formatForPrompt(memories),
      previousActions: [],
    });
    expect(prompt).toContain(synthText);

    // Idempotency: promoting the same institutional claim again is a no-op.
    const again = await institutionalKnowledgeBridge.promoteInstitutionalClaim({
      institutionalClaimId: outcome.synthesisClaimId,
      domain,
    });
    expect(again.memoryId).toBe(outcome.promotion.memoryId);
    const count = await db.query(
      `SELECT count(*) n FROM institutional_knowledge_promotions WHERE institutional_claim_id = $1`,
      [outcome.synthesisClaimId]
    );
    expect(Number((count.rows[0] as any).n)).toBe(1);
  }, 30000);

  test('cross-society: one society\'s knowledge influences another domain\'s planning', async () => {
    const domainA = `soc_a_${Date.now()}`;
    const domainB = `soc_b_${Date.now()}`;
    const marker = `graphene_${Date.now()}`;
    const { workRequestIds } = await buildInstitutionWithFindings(domainA, [
      `Finding A: ${marker} membranes filter desalination brine at high flux.`,
      `Finding B: ${marker} membranes resist fouling across two independent trials.`,
    ]);
    const synthText = `Institutional consensus from society A: ${marker} membranes are effective for desalination.`;
    const outcome = await civilizationLiveFlow.synthesizeAndPromoteKnowledge({
      sourceWorkRequestIds: workRequestIds,
      synthesisText: synthText,
      domain: domainA,
    });
    expect(outcome.promotion.promoted).toBe(true);

    // A planning run in a DIFFERENT domain, working on the same TOPIC, still
    // retrieves society A's knowledge via the shared memory substrate
    // (full-text branch). Retrieval ANDs the goal terms, so the goal must
    // genuinely concern the same subject — which is exactly when cross-society
    // transfer should fire.
    const crossDomain = await memoryRetrieval.retrieveForPlanning({
      goalText: `${marker} membranes desalination effectiveness`,
      domain: domainB,
    });
    expect(crossDomain.map(m => m.id)).toContain(outcome.promotion.memoryId);
  }, 30000);

  test('fail-closed: unknown / low-confidence / non-institutional claims are blocked', async () => {
    // A claim id that does not exist is refused.
    await expect(
      institutionalKnowledgeBridge.promoteInstitutionalClaim({
        institutionalClaimId: `missing-${crypto.randomUUID()}`,
        domain: 'blocktest',
      })
    ).rejects.toThrow(/not found/);

    // Note: empty evidence is already rejected by the DB CHECK constraint
    // `claim_must_have_evidence`, so an ungrounded claim cannot even be
    // inserted; the bridge's evidence guard is defense-in-depth.

    // Low-confidence institutional claim.
    const weakId = crypto.randomUUID();
    await db.query(
      `INSERT INTO autonomy_claims (claim_id, text, status, confidence, support_source_ids, generated_by)
       VALUES ($1,'Weak institutional conjecture.','supported',0.3,'["ev-1"]'::jsonb,'institutional-synthesis')`,
      [weakId]
    );
    const weak = await institutionalKnowledgeBridge.promoteInstitutionalClaim({
      institutionalClaimId: weakId,
      domain: 'blocktest',
    });
    expect(weak.promoted).toBe(false);
    expect(weak.blockReason).toContain('below promotion threshold');

    // Non-institutional claim (produced by an ordinary agent) is refused.
    const outsiderId = crypto.randomUUID();
    await db.query(
      `INSERT INTO autonomy_claims (claim_id, text, status, confidence, support_source_ids, generated_by)
       VALUES ($1,'A regular agent claim.','supported',0.9,'["ev-1"]'::jsonb,'autonomy_action_planner')`,
      [outsiderId]
    );
    const outsider = await institutionalKnowledgeBridge.promoteInstitutionalClaim({
      institutionalClaimId: outsiderId,
      domain: 'blocktest',
    });
    expect(outsider.promoted).toBe(false);
    expect(outsider.blockReason).toContain('not an institutional producer');

    // The two insertable blocked claims produced no memory.
    const memories = await db.query(
      `SELECT count(*) n FROM institutional_knowledge_promotions WHERE promoted = false AND institutional_claim_id = ANY($1)`,
      [[weakId, outsiderId]]
    );
    expect(Number((memories.rows[0] as any).n)).toBe(2);
  }, 30000);
});
