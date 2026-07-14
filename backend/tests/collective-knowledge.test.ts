import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { collectiveKnowledge } from '../src/services/collective-knowledge.service';

async function applyMigrations() {
  for (const file of [
    '129_civilization_kernel.sql', '130_citizenship.sql',
    '131_societies_and_institution_charters.sql', '132_institution_coalitions.sql',
    '133_missions.sql', '134_civilization_economy.sql', '135_governance.sql', '136_judiciary.sql',
    '137_collective_epistemics.sql',
  ]) {
    await migrationDb.query(fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${file}`), 'utf8'));
  }
}

async function actor(prefix: string): Promise<string> {
  const a = await identityAuthorityService.registerActor({
    actor_type: 'human', name: `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}`,
  });
  return a.id;
}

/** Insert a supported claim directly (bypasses the executor; C9 tests the retraction engine). */
async function insertClaim(claimId: string, sourceIds: string[], producer: string): Promise<void> {
  await db.query(
    `INSERT INTO autonomy_claims (claim_id, text, status, confidence, support_source_ids, generated_by)
     VALUES ($1,$2,'supported',0.8,$3::jsonb,$4)`,
    [claimId, `claim ${claimId}`, JSON.stringify(sourceIds), producer]
  );
}

async function insertMemory(agentId: string, domain: string, summary: string): Promise<string> {
  const r = await db.query<{ id: string }>(
    `INSERT INTO agent_memories (agent_id, memory_type, namespace, domain, summary, content, importance)
     VALUES ($1,'semantic','shared',$2,$3,'{}'::jsonb,0.5) RETURNING id`,
    [agentId, domain, summary]
  );
  return r.rows[0].id;
}

describe('collective epistemics (C9)', () => {
  beforeAll(async () => {
    await applyMigrations();
    await civilizationKernel.ensureCivilizationRoot();
  });

  test('retraction propagates transitively to dependent claims and memories', async () => {
    const producer = `agent-${Date.now()}`;
    const op = await actor('know-retract');
    const evidenceId = `ev-${crypto.randomUUID()}`;
    const claimA = crypto.randomUUID(); // claim_id is varchar(36)
    const claimB = crypto.randomUUID();

    // claimA is supported by the evidence; claimB derives from claimA.
    await insertClaim(claimA, [evidenceId], producer);
    await insertClaim(claimB, [claimA], producer);

    // A memory derives from claimA (explicit provenance edge).
    const memoryId = await insertMemory(producer, 'research', 'derived from claimA');
    await collectiveKnowledge.linkProvenance({
      from_type: 'claim', from_id: claimA, to_type: 'memory', to_id: memoryId, actor_id: op,
    });
    // A decision derives from claimB.
    const decisionId = `dec-${crypto.randomUUID()}`;
    await collectiveKnowledge.linkProvenance({
      from_type: 'claim', from_id: claimB, to_type: 'decision', to_id: decisionId, actor_id: op,
    });

    // Retract the evidence → everything downstream is affected.
    const result = await collectiveKnowledge.retract({
      subject_type: 'evidence', subject_id: evidenceId, reason: 'source discredited', actor_id: op,
    });

    // claimA (auto-discovered via support_source_ids), claimB (via support + edge),
    // memory (via edge), decision (via edge) all propagated.
    const affectedKeys = result.affected.map(a => `${a.type}:${a.id}`);
    expect(affectedKeys).toContain(`claim:${claimA}`);
    expect(affectedKeys).toContain(`claim:${claimB}`);
    expect(affectedKeys).toContain(`memory:${memoryId}`);
    expect(affectedKeys).toContain(`decision:${decisionId}`);

    expect(await collectiveKnowledge.isRetracted('claim', claimA)).toBe(true);
    expect(await collectiveKnowledge.isRetracted('claim', claimB)).toBe(true);
    expect(await collectiveKnowledge.isRetracted('memory', memoryId)).toBe(true);

    const memDemoted = await db.query(`SELECT COUNT(*)::int AS c FROM memory_demotions WHERE memory_id = $1`, [memoryId]);
    expect(Number(memDemoted.rows[0].c)).toBe(1);
    const decFlag = await db.query(`SELECT COUNT(*)::int AS c FROM decision_retraction_flags WHERE decision_id = $1`, [decisionId]);
    expect(Number(decFlag.rows[0].c)).toBe(1);

    const detail = await collectiveKnowledge.getRetraction(result.retraction_id);
    expect(detail!.propagations.length).toBe(result.affected.length);
  });

  test('retraction records are append-only and immutable', async () => {
    const op = await actor('know-immutable');
    const result = await collectiveKnowledge.retract({
      subject_type: 'prediction', subject_id: `pred-${crypto.randomUUID()}`, reason: 'resolution reversed', actor_id: op,
    });
    await expect(
      db.query(`UPDATE knowledge_retractions SET reason = 'changed' WHERE id = $1`, [result.retraction_id])
    ).rejects.toThrow(/EPISTEMICS GUARD/);
    await expect(
      db.query(`DELETE FROM knowledge_retractions WHERE id = $1`, [result.retraction_id])
    ).rejects.toThrow(/may not be deleted/);
    await expect(
      db.query(`UPDATE retraction_propagations SET depth = 9 WHERE retraction_id = $1`, [result.retraction_id])
    ).rejects.toThrow(/append-only/);
  });

  test('civilization knowledge view returns supported claims and non-demoted memories with domain trust context', async () => {
    const producer = `trusted-agent-${Date.now()}`;
    const op = await actor('know-view');
    // Seed a domain trust window for the producer.
    await db.query(
      `INSERT INTO trust_scores (subject_id, subject_type, domain, horizon_class, window_start, window_end, trust_factor, force_downgrade)
       VALUES ($1,'agent','physics','short', now() - interval '7 days', now(), 0.82, false)`,
      [producer]
    );
    const claimId = crypto.randomUUID(); // claim_id is varchar(36)
    await insertClaim(claimId, [`ev-${crypto.randomUUID()}`], producer);
    const memoryId = await insertMemory(producer, 'physics', 'stable finding');

    const view = await collectiveKnowledge.civilizationKnowledge({ domain: 'physics' });
    const claim = view.claims.find(c => c.claim_id === claimId);
    expect(claim).toBeDefined();
    expect(claim!.domain_trust).toBeCloseTo(0.82, 2);
    const mem = view.memories.find(m => m.memory_id === memoryId);
    expect(mem).toBeDefined();
    expect(mem!.domain_trust).toBeCloseTo(0.82, 2);
    expect(mem!.demoted).toBe(false);

    // Once demoted, the memory drops out of the civilization knowledge view.
    await collectiveKnowledge.retract({ subject_type: 'memory', subject_id: memoryId, reason: 'stale', actor_id: op });
    const afterView = await collectiveKnowledge.civilizationKnowledge({ domain: 'physics' });
    expect(afterView.memories.find(m => m.memory_id === memoryId)).toBeUndefined();
  });

  test('self-referential provenance edge is rejected', async () => {
    const op = await actor('know-selfedge');
    const id = `node-${crypto.randomUUID()}`;
    await expect(collectiveKnowledge.linkProvenance({
      from_type: 'claim', from_id: id, to_type: 'claim', to_id: id, actor_id: op,
    })).rejects.toThrow(/cannot derive from itself/);
  });
});
