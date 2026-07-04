/**
 * Persistent Agents (B6 / GA6)
 * ============================
 * A role's agent identity, memory, and trust survive process death and
 * reattach on re-spawn.
 */

import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { describe, expect, test, beforeAll } from '@jest/globals';
import { db } from '../src/db/client';
import { persistentAgentRegistry, PersistentAgentRegistryService } from '../src/services/persistent-agent-registry.service';

async function applyMigrations() {
  for (const name of ['009_trust_scores.sql', '015_agent_memories.sql', '017_agent_memories_lifecycle.sql', '116_persistent_agents.sql']) {
    await db.query(fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8'));
  }
}

describe('persistent agents (B6)', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('a role re-spawned after process death reattaches to the same id, memory, and trust', async () => {
    const role = `researcher_${crypto.randomUUID().slice(0, 8)}`;
    const domain = `pa_${Date.now()}`;
    const marker = `finding_${Date.now()}`;

    // --- Run 1: spawn the role, it writes a memory. ---
    const run1Registry = new PersistentAgentRegistryService();
    const a1 = await run1Registry.ensureAgent(role);
    expect(a1.reattached).toBe(false);
    await run1Registry.recordSpawn(role);
    await run1Registry.writeAgentMemory(role, domain, `${marker}: the specialist learned X.`);

    // Seed a trust window for this agent from a prior resolved outcome.
    await db.query(
      `INSERT INTO trust_scores (subject_id, subject_type, domain, claim_type, horizon_class, window_start, window_end, n_predictions, n_resolved, brier_mean, log_mean, ece, trust_factor, force_downgrade)
       VALUES ($1,'agent',$2,'general','short',NOW() - INTERVAL '1 day', NOW(), 8, 8, 0.1, 0.2, 0.05, 0.82, false)`,
      [a1.agentId, domain]
    );

    // --- Process death: a brand-new registry instance (no in-memory state). ---
    const run2Registry = new PersistentAgentRegistryService();
    const ctx = await run2Registry.loadContext(role, `${marker} recall`);

    // Same stable identity, reattached.
    expect(ctx.agentId).toBe(a1.agentId);
    expect(ctx.reattached).toBe(true);
    // Its own memory came back.
    expect(ctx.memories.some(m => m.summary.includes(marker))).toBe(true);
    // Its accumulated trust loaded.
    expect(ctx.trustFactor).toBeCloseTo(0.82, 2);
    expect(ctx.nResolved).toBe(8);
  });

  test('different roles get distinct stable identities; same role is idempotent', async () => {
    const roleA = `analyst_${crypto.randomUUID().slice(0, 8)}`;
    const roleB = `auditor_${crypto.randomUUID().slice(0, 8)}`;
    const a = await persistentAgentRegistry.ensureAgent(roleA);
    const b = await persistentAgentRegistry.ensureAgent(roleB);
    const aAgain = await persistentAgentRegistry.ensureAgent(roleA);
    expect(a.agentId).not.toBe(b.agentId);
    expect(aAgain.agentId).toBe(a.agentId);
  });
});
