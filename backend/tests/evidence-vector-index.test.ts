import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { evidenceRegistry } from '../src/services/evidence-registry.service';
import { evidenceVectorIndex } from '../src/services/evidence-vector-index.service';
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
    '101_evidence_vector_index.sql',
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
      scopes: ['evidence.register', 'evidence.vector_index'],
    },
  });
}

describe('evidence vector index', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('indexes registered evidence and retrieves nearest evidence with event/outbox provenance', async () => {
    const actor = await createActor('evidence-vector-index');
    const embeddingModel = `test-embedding-model-${Date.now()}-${Math.random()}`;
    const first = await evidenceRegistry.register({
      actor_id: actor.id,
      source_id: `vec-${Date.now()}-security`,
      url: 'https://example.com/security-audit',
      title: 'Security audit',
      snippet: 'External audit found runtime controls and event provenance.',
      content_hash: `sha256:security-${Date.now()}`,
      source_type: 'web',
    });
    const second = await evidenceRegistry.register({
      actor_id: actor.id,
      source_id: `vec-${Date.now()}-finance`,
      url: 'https://example.com/finance-review',
      title: 'Finance review',
      snippet: 'Revenue forecast focused on subscription expansion.',
      content_hash: `sha256:finance-${Date.now()}`,
      source_type: 'web',
    });

    const indexedFirst = await evidenceVectorIndex.indexEvidence({
      actor_id: actor.id,
      source_id: first.source_id,
      content_text: first.snippet ?? '',
      embedding_model: embeddingModel,
      embedding: [0.95, 0.05, 0.01],
      metadata: { test: true },
    });
    await evidenceVectorIndex.indexEvidence({
      actor_id: actor.id,
      source_id: second.source_id,
      content_text: second.snippet ?? '',
      embedding_model: embeddingModel,
      embedding: [0.01, 0.94, 0.05],
    });

    const results = await evidenceVectorIndex.search({
      embedding_model: embeddingModel,
      embedding: [0.99, 0.02, 0.01],
      top_k: 2,
    });

    expect(results).toHaveLength(2);
    expect(results[0].source_id).toBe(first.source_id);
    expect(results[0].similarity).toBeGreaterThan(results[1].similarity);
    expect(results[0].similarity).toBeGreaterThan(0.99);
    expect(indexedFirst.embedding_hash).toMatch(/^[0-9a-f]{64}$/);

    const event = await db.query(
      `SELECT id, event_type, payload
         FROM event_log
        WHERE id = $1`,
      [indexedFirst.event_log_id]
    );
    expect(event.rowCount).toBe(1);
    expect(event.rows[0].event_type).toBe('evidence.vector_indexed');
    expect(event.rows[0].payload.source_id).toBe(first.source_id);

    const outbox = await db.query('SELECT id FROM event_outbox WHERE event_log_id = $1', [indexedFirst.event_log_id]);
    expect(outbox.rowCount).toBe(1);
  });

  test('rejects vectors for unregistered evidence sources', async () => {
    await expect(
      evidenceVectorIndex.indexEvidence({
        source_id: `missing-${Date.now()}`,
        content_text: 'not registered',
        embedding_model: 'test-embedding-model',
        embedding: [1, 0, 0],
      })
    ).rejects.toThrow(/registered evidence not found/);
  });
});
