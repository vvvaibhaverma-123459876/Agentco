/**
 * Knowledge & reasoning routes
 * ============================
 * Integrates symbolic reasoning, knowledge persistence, KB expansion and RAG into the
 * deployable app. All were orphaned (see CIVILIZATION_AUDIT.md).
 */
import type { FastifyInstance, FastifyRequest } from 'fastify';
import { requireScope } from '../security';
import { symbolicService } from '../services/symbolic.service';
import { knowledgePersistenceService } from '../services/knowledge-persistence.service';
import { kbExpansionService } from '../services/kb-expansion.service';
import { ragService } from '../services/rag.service';

function bodyOf(req: FastifyRequest): Record<string, unknown> {
  return (req.body ?? {}) as Record<string, unknown>;
}

export async function knowledgeRoutes(fastify: FastifyInstance) {
  // Symbolic problem classification (pure).
  fastify.post('/api/symbolic/classify', { preHandler: requireScope('trust:read') }, async (req, reply) => {
    const { question } = bodyOf(req);
    if (typeof question !== 'string' || !question.trim()) {
      return reply.status(400).send({ error: 'question is required' });
    }
    return reply.send(symbolicService.classifyProblem(question));
  });

  // Symbolic solve (deterministic, in-memory).
  fastify.post('/api/symbolic/solve', { preHandler: requireScope('trust:read') }, async (req, reply) => {
    const { question } = bodyOf(req);
    if (typeof question !== 'string' || !question.trim()) {
      return reply.status(400).send({ error: 'question is required' });
    }
    return reply.send(await symbolicService.solve(question));
  });

  // Add a knowledge node to the graph (in-memory persistence layer).
  fastify.post('/api/knowledge/nodes', { preHandler: requireScope('claims:register') }, async (req, reply) => {
    const b = bodyOf(req);
    if (typeof b.field !== 'string' || typeof b.topic !== 'string' || typeof b.content !== 'string') {
      return reply.status(400).send({ error: 'field, topic and content are required' });
    }
    const node = knowledgePersistenceService.addKnowledgeNode({
      field: b.field,
      level: String(b.level ?? 'Undergraduate'),
      topic: b.topic,
      subtopics: Array.isArray(b.subtopics) ? b.subtopics.map(String) : [],
      content: b.content,
      confidence: Number(b.confidence ?? 0.7),
      correctness_rate: Number(b.correctness_rate ?? 1),
      prerequisites: Array.isArray(b.prerequisites) ? b.prerequisites.map(String) : [],
    } as Parameters<typeof knowledgePersistenceService.addKnowledgeNode>[0]);
    return reply.status(201).send(node);
  });

  // Execute the full KB expansion (deterministic, in-memory).
  fastify.post('/api/knowledge/expand', { preHandler: requireScope('claims:register') }, async (_req, reply) => {
    return reply.send(kbExpansionService.executeFullExpansion());
  });

  // RAG: augment a model answer with retrieved evidence.
  fastify.post('/api/rag/augment', { preHandler: requireScope('trust:read') }, async (req, reply) => {
    const b = bodyOf(req);
    if (typeof b.question !== 'string' || typeof b.model_answer !== 'string') {
      return reply.status(400).send({ error: 'question and model_answer are required' });
    }
    const result = await ragService.augmentAnswer(b.question, b.model_answer, Number(b.model_confidence ?? 0.5));
    return reply.send(result);
  });
}
