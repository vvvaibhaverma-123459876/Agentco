import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { evidenceRegistry } from '../src/services/evidence-registry.service';
import { identityAuthorityService } from '../src/services/identity-authority.service';

async function applyMigrations() {
  for (const name of [
    '004_decision_log.sql',
    '012_decision_log_chain.sql',
    '014_decision_log_immutability_triggers.sql',
    '050_autonomy_action_loop.sql',
    '079_identity_authority.sql',
    '080_event_log.sql',
    '083_transactional_outbox.sql',
    '088_evidence_registry_events.sql',
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
      scopes: ['evidence.register'],
    },
  });
}

describe('evidence registry', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('registers evidence with canonical event and audit provenance', async () => {
    const actor = await createActor('evidence-registry-service');
    const evidence = await evidenceRegistry.register({
      actor_id: actor.id,
      url: 'https://example.com/evidence-registry',
      title: 'Evidence Registry Test',
      snippet: 'Evidence registry records provenance.',
      content_hash: 'sha256:test-evidence-registry',
      source_type: 'web',
      is_public_access: true,
      metadata: { test: true },
    });

    expect(evidence.source_id).toMatch(/^[0-9a-f-]{36}$/);
    expect(evidence.event_log_id).toMatch(/^[0-9a-f-]{36}$/);
    expect(evidence.registered_by_actor_id).toBe(actor.id);

    const event = await db.query(
      `SELECT id, event_type, actor_id, payload
         FROM event_log
        WHERE id = $1`,
      [evidence.event_log_id]
    );
    expect(event.rowCount).toBe(1);
    expect(event.rows[0].event_type).toBe('evidence.registered');
    expect(event.rows[0].payload.source_id).toBe(evidence.source_id);

    const audit = await db.query(
      `SELECT log_id
         FROM decision_log
        WHERE downstream_events @> $1::uuid[]
          AND agent_id = $2`,
      [[evidence.event_log_id], actor.id]
    );
    expect(audit.rowCount).toBe(1);
  });

  test('rejects non-http evidence URLs without writing an artifact', async () => {
    await expect(
      evidenceRegistry.register({
        url: 'file:///tmp/local.txt',
        content_hash: 'sha256:local',
        source_type: 'document',
      })
    ).rejects.toThrow(/http\(s\)/);
  });
});
