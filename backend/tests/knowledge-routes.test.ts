/**
 * Knowledge & reasoning integration tests.
 * - symbolic / kb-expansion / knowledge-persistence tested against the REAL functions.
 * - Routes proven wired into server.ts build(); network-backed RAG mocked at boundary.
 */
jest.mock('../src/services/rag.service', () => ({
  ragService: { augmentAnswer: jest.fn() },
}));

import { build } from '../src/server';
import { symbolicService } from '../src/services/symbolic.service';
import { kbExpansionService } from '../src/services/kb-expansion.service';
import { knowledgePersistenceService } from '../src/services/knowledge-persistence.service';
import { ragService } from '../src/services/rag.service';

const reader = { 'x-agentco-api-key': 'dev-api-key', 'x-agentco-role': 'auditor' };  // trust:read
const claimer = { 'x-agentco-api-key': 'dev-api-key', 'x-agentco-role': 'service' }; // claims:register

describe('symbolic / knowledge (real functions)', () => {
  it('symbolic.classifyProblem detects a sequence/pattern problem', () => {
    const p = symbolicService.classifyProblem('what is the next number in the sequence 2 4 8');
    expect(p.type).not.toBe('unknown');
  });

  it('kbExpansion.executeFullExpansion returns expansion counts', () => {
    const r = kbExpansionService.executeFullExpansion();
    expect(r).toBeTruthy();
    expect(typeof r).toBe('object');
  });

  it('knowledge.addKnowledgeNode returns a node with an id and defaults', () => {
    const node = knowledgePersistenceService.addKnowledgeNode({
      field: 'Mathematics', level: 'Graduate', topic: 'Primes', subtopics: [],
      content: 'There are infinitely many primes.', confidence: 0.9, correctness_rate: 1, prerequisites: [],
    } as unknown as Parameters<typeof knowledgePersistenceService.addKnowledgeNode>[0]);
    expect(node.id).toBeTruthy();
    expect(node.times_used).toBe(0);
  });
});

describe('knowledge routes wired into the deployable app', () => {
  beforeEach(() => {
    (ragService.augmentAnswer as jest.Mock).mockReset();
  });

  it('POST /api/symbolic/classify classifies a problem', async () => {
    const app = await build();
    const res = await app.inject({ method: 'POST', url: '/api/symbolic/classify', headers: reader, payload: { question: 'next in series 1 1 2 3 5' } });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload)).toHaveProperty('type');
    await app.close();
  });

  it('POST /api/symbolic/classify rejects empty input', async () => {
    const app = await build();
    const res = await app.inject({ method: 'POST', url: '/api/symbolic/classify', headers: reader, payload: {} });
    expect(res.statusCode).toBe(400);
    await app.close();
  });

  it('POST /api/knowledge/nodes creates a node', async () => {
    const app = await build();
    const res = await app.inject({
      method: 'POST', url: '/api/knowledge/nodes', headers: claimer,
      payload: { field: 'Physics', topic: 'Gravity', content: 'Mass attracts mass.' },
    });
    expect(res.statusCode).toBe(201);
    expect(JSON.parse(res.payload)).toHaveProperty('id');
    await app.close();
  });

  it('POST /api/rag/augment delegates to the RAG service', async () => {
    (ragService.augmentAnswer as jest.Mock).mockResolvedValueOnce({ augmented_answer: 'x', support: [] });
    const app = await build();
    const res = await app.inject({
      method: 'POST', url: '/api/rag/augment', headers: reader,
      payload: { question: 'q', model_answer: 'a', model_confidence: 0.6 },
    });
    expect(res.statusCode).toBe(200);
    expect(ragService.augmentAnswer).toHaveBeenCalledWith('q', 'a', 0.6);
    await app.close();
  });
});
