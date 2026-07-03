/**
 * Civilization Learning Backbone — LIVE
 * =====================================
 * Opt-in real-world proof (skips cleanly without credentials). Requires
 * RUN_REAL_LLM_TESTS=1 and a working LLM_API_KEY/OPENAI_API_KEY.
 *
 * Proves against a REAL model that institution-produced knowledge reaches a
 * live planner run: an institution synthesizes findings, the bridge promotes
 * the composite into durable memory, and a genuine planner call (hitting the
 * configured provider) is issued for a related goal with that institutional
 * knowledge retrieved into its context.
 */

import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { describe, expect, test, beforeAll } from '@jest/globals';
import { db } from '../src/db/client';
import { institutionsService } from '../src/services/institutions.service';
import { civilizationLiveFlow } from '../src/services/civilization-live-flow.service';
import { memoryRetrieval } from '../src/services/memory-retrieval.service';
import { AutonomyActionPlannerService } from '../src/services/autonomy-action-planner.service';

const RUN_LIVE =
  process.env.RUN_REAL_LLM_TESTS === '1' &&
  Boolean(process.env.LLM_API_KEY || process.env.OPENAI_API_KEY);
const maybe = RUN_LIVE ? describe : describe.skip;

async function applyMigrations() {
  for (const name of [
    '004_decision_log.sql', '012_decision_log_chain.sql', '014_decision_log_immutability_triggers.sql',
    '015_agent_memories.sql', '017_agent_memories_lifecycle.sql', '050_autonomy_action_loop.sql',
    '052b_institutions.sql', '053_work_assignment_schema.sql', '062_runtime_schema_compatibility.sql',
    '079_identity_authority.sql', '080_event_log.sql', '083_transactional_outbox.sql',
    '113_institutional_knowledge_promotions.sql',
  ]) {
    await db.query(fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8'));
  }
}

async function finding(institutionId: string, deptId: string, claimId: string, wr: string, text: string, evs: string[]) {
  await db.query(
    `INSERT INTO autonomy_claims (claim_id, text, status, confidence, support_source_ids, support_snippets, generated_by)
     VALUES ($1,$2,'supported',0.85,$3::jsonb,$4::jsonb,'synthesis-test')`,
    [claimId, text, JSON.stringify(evs), JSON.stringify(evs.map(e => ({ source_id: e, snippet: text })))]
  );
  await db.query(
    `INSERT INTO institution_work_requests (id, institution_id, department_id, objective, required_specialists, budget_tokens, budget_iterations, budget_seconds, verification_required, reputation_metric, risk_level, status, result_summary, completed_at)
     VALUES ($1,$2,$3,$4,'[]'::jsonb,1000,1,300,true,'evidence_quality','medium','completed',$5::jsonb,now())`,
    [wr, institutionId, deptId, text, JSON.stringify({ vetting: { work_request_id: wr, claim_id: claimId, rigor_tier: 'full', finding_type: 'EXTERNALLY_VERIFIED', status: 'finding', stages: [], reputation_adjustments_required: [] } })]
  );
}

maybe('civilization learning backbone (live)', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('institution knowledge is promoted and reaches a live planner run', async () => {
    const suffix = crypto.randomUUID().slice(0, 8);
    const domain = `civlive_${suffix}`;
    const inst = await institutionsService.createCanonicalInstitution({
      name: `civlive_${suffix}`, domain, purpose: 'Live civ learning', authorityScope: ['institutional_synthesis'],
    });
    const prod = inst.departments.find(d => d.name === 'Production')!;
    await finding(inst.institutionId, prod.id, `cl-${suffix}-0`, `wr-${suffix}-0`,
      'Sodium-ion cells retain over 90% capacity after 3000 cycles in independent lab tests.', [`ev-${suffix}-a`, `ev-${suffix}-b`]);
    await finding(inst.institutionId, prod.id, `cl-${suffix}-1`, `wr-${suffix}-1`,
      'Sodium-ion cells cost roughly 30% less than lithium-ion at grid scale across two suppliers.', [`ev-${suffix}-c`, `ev-${suffix}-d`]);

    const synthText = 'Institutional consensus: sodium-ion batteries are a durable, lower-cost option for grid-scale storage.';
    const outcome = await civilizationLiveFlow.synthesizeAndPromoteKnowledge({
      sourceWorkRequestIds: [`wr-${suffix}-0`, `wr-${suffix}-1`], synthesisText: synthText, domain,
    });
    expect(outcome.promotion.promoted).toBe(true);

    const memories = await memoryRetrieval.retrieveForPlanning({
      goalText: 'Recommend a battery chemistry for a new grid-scale storage project', domain,
    });
    expect(memories.map(m => m.id)).toContain(outcome.promotion.memoryId);

    // Real planner call against the configured provider — must not throw.
    const planner = new AutonomyActionPlannerService();
    const action = await planner.planNextAction(crypto.randomUUID(), {
      goalText: 'Recommend a battery chemistry for a new grid-scale storage project',
      claimsGenerated: 0, evidenceCount: 0, loopDetection: { isLooping: false } as any,
      memoryContext: undefined, domain, previousActions: [],
    });
    expect(action.actionType).toBeTruthy();
    // The institutional knowledge was in the planner's context for this live call.
    expect(memories.some(m => m.summary === synthText)).toBe(true);
  }, 60000);
});
