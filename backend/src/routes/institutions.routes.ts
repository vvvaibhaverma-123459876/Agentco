/**
 * Institutions / goals / coalitions routes
 * ========================================
 * Integrates the civilization "org" layer (institutions, goal lifecycle, goal hierarchy,
 * coalition formation) into the deployable app. These services were all orphaned before
 * (see CIVILIZATION_AUDIT.md) - real, substantial, wired into nothing.
 */
import type { FastifyInstance, FastifyRequest } from 'fastify';
import { requireScope } from '../security';
import { institutionsService } from '../services/institutions.service';
import { goalManager } from '../services/goal-manager.service';
import { goalHierarchyService } from '../services/goal-hierarchy.service';
import { coalitionFormationService } from '../services/coalition-formation.service';
import type { GoalInput } from '../services/goal-manager.service';

function bodyOf(req: FastifyRequest): Record<string, unknown> {
  return (req.body ?? {}) as Record<string, unknown>;
}

export async function institutionsRoutes(fastify: FastifyInstance) {
  // Create an institution for a domain.
  fastify.post(
    '/api/institutions',
    { preHandler: requireScope('institutions:mutate') },
    async (req, reply) => {
      const { domain } = bodyOf(req);
      if (typeof domain !== 'string' || !domain.trim()) {
        return reply.status(400).send({ error: 'domain (non-empty string) is required' });
      }
      const institution = institutionsService.createInstitution(domain);
      return reply.status(201).send(institution);
    },
  );

  // Propose a governed goal (agents propose; humans/governors approve downstream).
  fastify.post(
    '/api/goals',
    { preHandler: requireScope('institutions:mutate') },
    async (req, reply) => {
      const b = bodyOf(req);
      if (typeof b.title !== 'string' || typeof b.domain !== 'string' || typeof b.proposedBy !== 'string') {
        return reply.status(400).send({ error: 'title, domain and proposedBy are required' });
      }
      try {
        const { goalId } = await goalManager.proposeGoal(b as unknown as GoalInput);
        return reply.status(201).send({ goal_id: goalId, status: 'proposed' });
      } catch (error) {
        return reply.status(400).send({ error: error instanceof Error ? error.message : String(error) });
      }
    },
  );

  // Activate an approved goal.
  fastify.post<{ Params: { id: string } }>(
    '/api/goals/:id/activate',
    { preHandler: requireScope('institutions:mutate') },
    async (req, reply) => {
      try {
        await goalManager.activateGoal(req.params.id);
        return reply.send({ goal_id: req.params.id, status: 'active' });
      } catch (error) {
        return reply.status(409).send({ error: error instanceof Error ? error.message : String(error) });
      }
    },
  );

  // Read an institution's goal hierarchy.
  fastify.get<{ Params: { id: string } }>(
    '/api/institutions/:id/goals',
    { preHandler: requireScope('task:read') },
    async (req, reply) => {
      const hierarchy = await goalHierarchyService.getGoalHierarchy(req.params.id);
      return reply.send(hierarchy);
    },
  );

  // Recommend a coalition (team) for an objective.
  fastify.post(
    '/api/coalitions/recommend',
    { preHandler: requireScope('institutions:mutate') },
    async (req, reply) => {
      const b = bodyOf(req);
      if (typeof b.objective !== 'string' || !b.objective.trim()) {
        return reply.status(400).send({ error: 'objective (non-empty string) is required' });
      }
      const specs = Array.isArray(b.required_specializations) ? b.required_specializations.map(String) : [];
      const recommendation = await coalitionFormationService.recommendTeamComposition(b.objective, specs);
      return reply.send(recommendation);
    },
  );
}
