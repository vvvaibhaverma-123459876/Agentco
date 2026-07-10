import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { institutionWorkAssignmentService } from '../services/institution-work-assignment.service';

export async function institutionWorkAssignmentRoutes(
  fastify: FastifyInstance
): Promise<void> {
  /**
   * POST /api/autonomy/work-requests
   * Submit a work request from institution to autonomy system
   */
  fastify.post('/api/autonomy/work-requests', async (
    req: FastifyRequest,
    reply: FastifyReply
  ) => {
    try {
      const {
        institution_id,
        department_id,
        objective,
        required_specialists,
        budget,
        verification_required,
        external_reviewer_id,
        reputation_metric,
        risk_level,
      } = req.body as any;

      // Validate required fields
      if (!institution_id) {
        return reply.status(400).send({ error: 'institution_id is required' });
      }
      if (!department_id) {
        return reply.status(400).send({ error: 'department_id is required' });
      }
      if (!objective) {
        return reply.status(400).send({ error: 'objective is required' });
      }
      if (!Array.isArray(required_specialists) || required_specialists.length === 0) {
        return reply.status(400).send({ error: 'required_specialists must be non-empty array' });
      }
      if (!budget || typeof budget.tokens !== 'number' || typeof budget.iterations !== 'number' || typeof budget.seconds !== 'number') {
        return reply.status(400).send({ error: 'budget must have tokens, iterations, seconds' });
      }

      // Submit work request
      const workRequest = await institutionWorkAssignmentService.submitWorkRequest({
        institution_id,
        department_id,
        objective,
        required_specialists,
        budget,
        verification_required: verification_required || false,
        external_reviewer_id,
        reputation_metric,
        risk_level: risk_level || 'low',
      });

      return reply.status(201).send(workRequest);
    } catch (e: any) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  /**
   * GET /api/autonomy/work-requests/:requestId
   * Get work request details
   */
  fastify.get('/api/autonomy/work-requests/:requestId', async (
    req: FastifyRequest,
    reply: FastifyReply
  ) => {
    try {
      const { requestId } = req.params as { requestId: string };

      const workRequest = await institutionWorkAssignmentService.getWorkRequest(requestId);

      if (!workRequest) {
        return reply.status(404).send({ error: 'work request not found' });
      }

      return reply.send(workRequest);
    } catch (e: any) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  /**
   * GET /api/civilization/institutions/:institutionId/work-requests
   * List work requests for institution
   */
  fastify.get(
    '/api/civilization/institutions/:institutionId/work-requests',
    async (req: FastifyRequest, reply: FastifyReply) => {
      try {
        const { institutionId } = req.params as { institutionId: string };
        const { status } = req.query as { status?: string };

        const workRequests = await institutionWorkAssignmentService.getInstitutionWorkRequests(
          institutionId,
          status
        );

        return reply.send({
          institution_id: institutionId,
          work_requests: workRequests,
          total: workRequests.length,
        });
      } catch (e: any) {
        return reply.status(400).send({ error: 'Invalid request' });
      }
    }
  );

  /**
   * POST /api/civilization/institutions/:institutionId/specialist-assignments
   * Assign specialist to department
   */
  fastify.post(
    '/api/civilization/institutions/:institutionId/specialist-assignments',
    async (req: FastifyRequest, reply: FastifyReply) => {
      try {
        const { institutionId } = req.params as { institutionId: string };
        const { department_id, specialist_role, reputation_score } = req.body as any;

        if (!department_id) {
          return reply.status(400).send({ error: 'department_id is required' });
        }
        if (!specialist_role) {
          return reply.status(400).send({ error: 'specialist_role is required' });
        }

        const result = await institutionWorkAssignmentService.assignSpecialistToDepartment(
          institutionId,
          department_id,
          specialist_role,
          reputation_score || 0.0
        );

        return reply.status(201).send(result);
      } catch (e: any) {
        return reply.status(400).send({ error: 'Invalid request' });
      }
    }
  );

  /**
   * GET /api/civilization/departments/:departmentId/specialists
   * Get specialists assigned to department
   */
  fastify.get(
    '/api/civilization/departments/:departmentId/specialists',
    async (req: FastifyRequest, reply: FastifyReply) => {
      try {
        const { departmentId } = req.params as { departmentId: string };

        const specialists = await institutionWorkAssignmentService.getDepartmentSpecialists(
          departmentId
        );

        return reply.send({
          department_id: departmentId,
          specialists: specialists,
          total: specialists.length,
        });
      } catch (e: any) {
        return reply.status(400).send({ error: 'Invalid request' });
      }
    }
  );
}
