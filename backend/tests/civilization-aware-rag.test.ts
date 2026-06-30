import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { evidenceRegistry } from '../src/services/evidence-registry.service';
import { evidenceVectorIndex } from '../src/services/evidence-vector-index.service';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { RAGService } from '../src/services/rag.service';

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

describe('civilization-aware RAG', () => {
  const originalFetch = global.fetch;

  beforeAll(async () => {
    await applyMigrations();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  test('uses canonical vector-index evidence before falling back to external retrieval', async () => {
    const actor = await createActor('civilization-aware-rag');
    const embeddingModel = `civilization-aware-rag-${Date.now()}-${Math.random()}`;
    const evidence = await evidenceRegistry.register({
      actor_id: actor.id,
      source_id: `rag-${Date.now()}-runtime-audit`,
      url: 'https://example.com/runtime-audit',
      title: 'Runtime audit',
      snippet: 'External security audit verified runtime controls and canonical event provenance.',
      content_hash: `sha256:runtime-audit-${Date.now()}`,
      source_type: 'web',
    });
    await evidenceVectorIndex.indexEvidence({
      actor_id: actor.id,
      source_id: evidence.source_id,
      content_text: evidence.snippet ?? '',
      embedding_model: embeddingModel,
      embedding: [0.99, 0.01, 0.02],
    });

    global.fetch = jest.fn().mockRejectedValue(new Error('external retrieval unavailable')) as unknown as typeof fetch;
    const service = new RAGService({
      canonicalEvidenceTopK: 1,
      embedQuestion: async () => ({
        embedding_model: embeddingModel,
        embedding: [0.98, 0.02, 0.01],
      }),
    });

    const result = await service.augmentAnswer(
      'What evidence exists for runtime controls and event provenance?',
      'No evidence is available.',
      0.25
    );

    expect(result.evidence_consensus.sources).toHaveLength(1);
    expect(result.evidence_consensus.sources[0]).toEqual(expect.objectContaining({
      source: 'EvidenceVectorIndex',
      source_id: evidence.source_id,
      url: 'https://example.com/runtime-audit',
    }));
    expect(result.final_answer).toContain('External security audit verified runtime controls');
    expect(result.final_confidence).toBeGreaterThan(0.8);
  });
});
