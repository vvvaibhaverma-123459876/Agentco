import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { auditLog } from '../src/services/audit-log.service';
import { eventLog } from '../src/services/event-log.service';
import { hashChainAnchor } from '../src/services/hash-chain-anchor.service';
import { identityAuthorityService } from '../src/services/identity-authority.service';

async function applyMigrations() {
  for (const name of [
    '004_decision_log.sql',
    '012_decision_log_chain.sql',
    '014_decision_log_immutability_triggers.sql',
    '079_identity_authority.sql',
    '080_event_log.sql',
    '083_transactional_outbox.sql',
    '087_hash_chain_anchors.sql',
  ]) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await db.query(migration);
  }
}

async function createActor(prefix: string) {
  return identityAuthorityService.registerActor({
    actor_type: 'service',
    name: `${prefix}-${Date.now()}-${Math.random()}`,
    service_identity: {
      service_name: `${prefix}-${Date.now()}-${Math.random()}`,
      scopes: ['audit.anchor'],
    },
  });
}

describe('hash chain anchor', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('creates and verifies an internal Postgres anchor for event and audit chain heads', async () => {
    const actor = await createActor('anchor-service');
    await eventLog.append({
      event_type: 'test.anchor_event',
      actor_id: actor.id,
      payload: { anchor: true },
    });
    await auditLog.append({
      agent_id: actor.id,
      action_type: 'decision',
      input_summary: 'anchor test',
      output_summary: 'anchor ready',
      confidence_score: 0.9,
      risk_level: 'low',
    });

    const anchor = await hashChainAnchor.createAnchor({ test: 'hash-chain-anchor' });
    expect(anchor.combined_root_hash).toMatch(/^[0-9a-f]{64}$/);
    expect(Number(anchor.event_count)).toBeGreaterThan(0);
    expect(Number(anchor.decision_count)).toBeGreaterThan(0);

    const verified = await hashChainAnchor.verifyAnchor(anchor.id);
    expect(verified).toMatchObject({ valid: true, reason: 'anchor_valid', anchor_id: anchor.id });
  });

  test('detects when the event chain has advanced after the anchor', async () => {
    const actor = await createActor('anchor-moved-event-service');
    const anchor = await hashChainAnchor.createAnchor({ test: 'event-head-move' });

    await eventLog.append({
      event_type: 'test.after_anchor',
      actor_id: actor.id,
      payload: { moved: true },
    });

    const verified = await hashChainAnchor.verifyAnchor(anchor.id);
    expect(verified.valid).toBe(false);
    expect(verified.reason).toBe('event_head_moved');
  });

  test('detects stored root tampering even when current heads match', async () => {
    const anchor = await hashChainAnchor.createAnchor({ test: 'root-tamper' });
    await db.query(
      `UPDATE hash_chain_anchors
          SET combined_root_hash = $2
        WHERE id = $1`,
      [anchor.id, 'f'.repeat(64)]
    );

    const verified = await hashChainAnchor.verifyAnchor(anchor.id);
    expect(verified.valid).toBe(false);
    expect(verified.reason).toBe('root_mismatch');
  });
});
