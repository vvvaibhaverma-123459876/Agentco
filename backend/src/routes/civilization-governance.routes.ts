import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { calibrationConstitutionService } from '../services/calibration-constitution.service';
import { trustPolicyService } from '../services/trust-policy.service';
import { calibrationChangeGovernanceService } from '../services/calibration-change-governance.service';
import { trustImpactAssessmentService } from '../services/trust-impact-assessment.service';
import { trustReputationService } from '../services/trust-reputation.service';
import { calibrationDriftMonitorService } from '../services/calibration-drift-monitor.service';
import { trustPolicyCanaryService } from '../services/trust-policy-canary.service';
import { civilizationRuntimeService } from '../services/civilization-runtime.service';
import { civilizationSchedulerService } from '../services/civilization-scheduler.service';

export async function civilizationGovernanceRoutes(fastify: FastifyInstance) {
  // ============================================================
  // CONSTITUTION ENDPOINTS (5)
  // ============================================================

  // POST /api/civilization/constitution/versions - Create new constitution version
  fastify.post('/api/civilization/constitution/versions', async (req: FastifyRequest, reply: FastifyReply) => {
    const { content, signerEntityId, signature } = req.body as any;
    try {
      const version = await calibrationConstitutionService.createVersion(content, signerEntityId, signature);
      return reply.status(201).send(version);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // POST /api/civilization/constitution/activate - Activate a constitution version
  fastify.post('/api/civilization/constitution/activate', async (req: FastifyRequest, reply: FastifyReply) => {
    const { versionId } = req.body as any;
    try {
      await calibrationConstitutionService.activateVersion(versionId);
      return reply.send({ status: 'activated', versionId });
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // GET /api/civilization/constitution/active - Get active constitution
  fastify.get('/api/civilization/constitution/active', async (_req: FastifyRequest, reply: FastifyReply) => {
    try {
      const constitution = await calibrationConstitutionService.getActive();
      return reply.send(constitution);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // POST /api/civilization/constitution/validate-change - Validate change against constitution
  fastify.post('/api/civilization/constitution/validate-change', async (req: FastifyRequest, reply: FastifyReply) => {
    const { changeType, affectedTables, affectedColumns } = req.body as any;
    try {
      const result = await calibrationConstitutionService.validateChange(changeType, affectedTables, affectedColumns);
      return reply.send(result);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // GET /api/civilization/constitution/protected-surfaces - List protected surfaces
  fastify.get('/api/civilization/constitution/protected-surfaces', async (_req: FastifyRequest, reply: FastifyReply) => {
    try {
      const surfaces = await calibrationConstitutionService.getProtectedSurfaces();
      return reply.send(surfaces);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // ============================================================
  // TRUST POLICY ENDPOINTS (6)
  // ============================================================

  // POST /api/civilization/policies - Create new policy draft
  fastify.post('/api/civilization/policies', async (req: FastifyRequest, reply: FastifyReply) => {
    const { policyType, promotionScope, content, creatorEntityId } = req.body as any;
    try {
      const policy = await trustPolicyService.createDraft(policyType, promotionScope, content, creatorEntityId);
      return reply.status(201).send(policy);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // GET /api/civilization/policies/:policyId - Get policy by ID
  fastify.get('/api/civilization/policies/:policyId', async (req: FastifyRequest, reply: FastifyReply) => {
    const { policyId } = req.params as { policyId: string };
    try {
      const policy = await trustPolicyService.getById(policyId);
      if (!policy) return reply.status(404).send({ error: 'policy not found' });
      return reply.send(policy);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // POST /api/civilization/policies/:policyId/review - Submit policy for review
  fastify.post('/api/civilization/policies/:policyId/review', async (req: FastifyRequest, reply: FastifyReply) => {
    const { policyId } = req.params as { policyId: string };
    const { reviewerEntityId } = req.body as any;
    try {
      await trustPolicyService.submitForReview(policyId, reviewerEntityId);
      return reply.send({ status: 'submitted_for_review' });
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // POST /api/civilization/policies/:policyId/approve - Approve policy
  fastify.post('/api/civilization/policies/:policyId/approve', async (req: FastifyRequest, reply: FastifyReply) => {
    const { policyId } = req.params as { policyId: string };
    const { approverEntityId, reason } = req.body as any;
    try {
      await trustPolicyService.approve(policyId, approverEntityId, reason);
      return reply.send({ status: 'approved' });
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // GET /api/civilization/policies/active - List active policies
  fastify.get('/api/civilization/policies/active', async (_req: FastifyRequest, reply: FastifyReply) => {
    try {
      const policies = await trustPolicyService.listActivePolicies();
      return reply.send(policies);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // GET /api/civilization/policies/by-type/:policyType - Get policy by type
  fastify.get('/api/civilization/policies/by-type/:policyType', async (req: FastifyRequest, reply: FastifyReply) => {
    const { policyType } = req.params as { policyType: string };
    try {
      const policies = await trustPolicyService.getByType(policyType);
      return reply.send(policies);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // ============================================================
  // CHANGE GOVERNANCE ENDPOINTS (5)
  // ============================================================

  // POST /api/civilization/changes/request - Create change request
  fastify.post('/api/civilization/changes/request', async (req: FastifyRequest, reply: FastifyReply) => {
    const { requesterEntityId, changeType, description, context } = req.body as any;
    try {
      const request = await calibrationChangeGovernanceService.createRequest(
        requesterEntityId,
        changeType,
        description,
        context
      );
      return reply.status(201).send(request);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // GET /api/civilization/changes/:requestId - Get change request
  fastify.get('/api/civilization/changes/:requestId', async (req: FastifyRequest, reply: FastifyReply) => {
    const { requestId } = req.params as { requestId: string };
    try {
      const request = await calibrationChangeGovernanceService.getById(requestId);
      if (!request) return reply.status(404).send({ error: 'request not found' });
      return reply.send(request);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // POST /api/civilization/changes/:requestId/review - Submit for review
  fastify.post('/api/civilization/changes/:requestId/review', async (req: FastifyRequest, reply: FastifyReply) => {
    const { requestId } = req.params as { requestId: string };
    try {
      await calibrationChangeGovernanceService.submitForReview(requestId);
      return reply.send({ status: 'submitted_for_review' });
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // POST /api/civilization/changes/:requestId/approve - Approve change
  fastify.post('/api/civilization/changes/:requestId/approve', async (req: FastifyRequest, reply: FastifyReply) => {
    const { requestId } = req.params as { requestId: string };
    const { approverEntityId, approverRole, reason } = req.body as any;
    try {
      await calibrationChangeGovernanceService.recordApproval(
        requestId,
        approverEntityId,
        'approved',
        approverRole,
        reason
      );
      return reply.send({ status: 'approved' });
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // GET /api/civilization/changes/pending - List pending changes
  fastify.get('/api/civilization/changes/pending', async (_req: FastifyRequest, reply: FastifyReply) => {
    try {
      const changes = await calibrationChangeGovernanceService.listPending();
      return reply.send(changes);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // ============================================================
  // IMPACT ASSESSMENT ENDPOINTS (3)
  // ============================================================

  // POST /api/civilization/assessments - Create impact assessment
  fastify.post('/api/civilization/assessments', async (req: FastifyRequest, reply: FastifyReply) => {
    const {
      changeRequestId,
      calibrationRegression,
      confidenceShift,
      falsePositiveImpact,
      falseNegativeImpact,
      reputationImpact,
      disputeImpact,
      simulationLeakageRisk,
      safetyThresholdCompliance,
      rollbackFeasibility,
      auditCompleteness,
    } = req.body as any;
    try {
      const assessment = await trustImpactAssessmentService.createAssessment(
        changeRequestId,
        'change_request',
        {
          calibration_regression: calibrationRegression,
          confidence_shift: confidenceShift,
          false_positive_impact: falsePositiveImpact,
          false_negative_impact: falseNegativeImpact,
          reputation_impact: reputationImpact,
          dispute_impact: disputeImpact,
          simulation_leakage_risk: simulationLeakageRisk,
          safety_threshold_compliance: safetyThresholdCompliance,
          rollback_feasibility: rollbackFeasibility,
          audit_completeness: auditCompleteness,
        }
      );
      return reply.status(201).send(assessment);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // GET /api/civilization/assessments/:assessmentId - Get assessment
  fastify.get('/api/civilization/assessments/:assessmentId', async (req: FastifyRequest, reply: FastifyReply) => {
    const { assessmentId } = req.params as { assessmentId: string };
    try {
      const assessment = await trustImpactAssessmentService.getById(assessmentId);
      if (!assessment) return reply.status(404).send({ error: 'assessment not found' });
      return reply.send(assessment);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // GET /api/civilization/assessments/:assessmentId/recommendation - Get recommendation
  fastify.get('/api/civilization/assessments/:assessmentId/recommendation', async (req: FastifyRequest, reply: FastifyReply) => {
    const { assessmentId } = req.params as { assessmentId: string };
    try {
      const assessment = await trustImpactAssessmentService.getById(assessmentId);
      if (!assessment) return reply.status(404).send({ error: 'assessment not found' });
      return reply.send({ recommendation: assessment.recommendation, blocked: assessment.blocking_issues });
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // ============================================================
  // REPUTATION ENDPOINTS (4)
  // ============================================================

  // POST /api/civilization/reputation/events - Record reputation event
  fastify.post('/api/civilization/reputation/events', async (req: FastifyRequest, reply: FastifyReply) => {
    const { entityType, entityId, eventType, context, impactValue, impactConfidence, evidenceJson } = req.body as any;
    try {
      const event = await trustReputationService.recordEvent(
        entityType,
        entityId,
        eventType,
        context,
        impactValue,
        impactConfidence,
        evidenceJson
      );
      return reply.status(201).send(event);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // GET /api/civilization/reputation/:entityType/:entityId - Get reputation for entity
  fastify.get('/api/civilization/reputation/:entityType/:entityId', async (req: FastifyRequest, reply: FastifyReply) => {
    const { entityType, entityId } = req.params as { entityType: string; entityId: string };
    try {
      const events = await trustReputationService.listEvents(entityType, entityId);
      const reputation = await trustReputationService.computeReputation(entityType, entityId);
      return reply.send({ reputation, events });
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // GET /api/civilization/reputation/:entityType/:entityId/trust-weight - Get trust weight
  fastify.get('/api/civilization/reputation/:entityType/:entityId/trust-weight', async (req: FastifyRequest, reply: FastifyReply) => {
    const { entityType, entityId } = req.params as { entityType: string; entityId: string };
    try {
      const weight = await trustReputationService.getTrustWeight(entityType, entityId);
      return reply.send({ trust_weight: weight });
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // GET /api/civilization/reputation/snapshots/:entityType/:entityId - Get reputation snapshots
  fastify.get('/api/civilization/reputation/snapshots/:entityType/:entityId', async (req: FastifyRequest, reply: FastifyReply) => {
    const { entityType, entityId } = req.params as { entityType: string; entityId: string };
    try {
      const snapshots = await trustReputationService.listSnapshots(entityType, entityId);
      return reply.send(snapshots);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // ============================================================
  // DRIFT MONITOR ENDPOINTS (4)
  // ============================================================

  // POST /api/civilization/drift/detect - Detect drift
  fastify.post('/api/civilization/drift/detect', async (req: FastifyRequest, reply: FastifyReply) => {
    const {
      driftType,
      baselineValue,
      observedValue,
      detectionMethod,
      affectedEntityType,
      affectedEntityId,
      evidence,
      traceId,
    } = req.body as any;
    try {
      const event = await calibrationDriftMonitorService.detectDrift(
        driftType,
        baselineValue,
        observedValue,
        detectionMethod,
        affectedEntityType,
        affectedEntityId,
        evidence,
        traceId
      );
      return reply.status(201).send(event);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // GET /api/civilization/drift/unresolved - List unresolved drifts
  fastify.get('/api/civilization/drift/unresolved', async (req: FastifyRequest, reply: FastifyReply) => {
    const { limit = 50, offset = 0 } = req.query as { limit?: number; offset?: number };
    try {
      const drifts = await calibrationDriftMonitorService.listUnresolved(limit, offset);
      return reply.send(drifts);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // GET /api/civilization/drift/critical - List critical drifts
  fastify.get('/api/civilization/drift/critical', async (_req: FastifyRequest, reply: FastifyReply) => {
    try {
      const drifts = await calibrationDriftMonitorService.getCriticalDrifts();
      return reply.send(drifts);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // POST /api/civilization/drift/:driftId/resolve - Resolve drift
  fastify.post('/api/civilization/drift/:driftId/resolve', async (req: FastifyRequest, reply: FastifyReply) => {
    const { driftId } = req.params as { driftId: string };
    const { resolutionType, reason } = req.body as any;
    try {
      await calibrationDriftMonitorService.resolveDrift(driftId, resolutionType, undefined, 'system', reason);
      return reply.send({ status: 'resolved' });
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // ============================================================
  // CANARY & ROLLBACK ENDPOINTS (4)
  // ============================================================

  // POST /api/civilization/canary/start - Start canary deployment
  fastify.post('/api/civilization/canary/start', async (req: FastifyRequest, reply: FastifyReply) => {
    const { policyId, canaryScope, targetAgents, targetPercentage, traceId } = req.body as any;
    try {
      const canary = await trustPolicyCanaryService.createCanary(
        policyId,
        canaryScope,
        targetAgents,
        targetPercentage,
        traceId
      );
      return reply.status(201).send(canary);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // POST /api/civilization/canary/:canaryId/metric - Record canary metric
  fastify.post('/api/civilization/canary/:canaryId/metric', async (req: FastifyRequest, reply: FastifyReply) => {
    const { canaryId } = req.params as { canaryId: string };
    const { metricName, metricValue, status = 'normal' } = req.body as any;
    try {
      await trustPolicyCanaryService.recordMetric(canaryId, metricName, metricValue, status);
      return reply.send({ status: 'recorded' });
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // POST /api/civilization/canary/:canaryId/promote - Promote canary to full rollout
  fastify.post('/api/civilization/canary/:canaryId/promote', async (req: FastifyRequest, reply: FastifyReply) => {
    const { canaryId } = req.params as { canaryId: string };
    const { traceId } = req.body as any;
    try {
      await trustPolicyCanaryService.promoteCanary(canaryId, traceId);
      return reply.send({ status: 'promoted' });
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // POST /api/civilization/canary/:canaryId/rollback - Rollback canary
  fastify.post('/api/civilization/canary/:canaryId/rollback', async (req: FastifyRequest, reply: FastifyReply) => {
    const { canaryId } = req.params as { canaryId: string };
    const { reason, traceId } = req.body as any;
    try {
      await trustPolicyCanaryService.rollback(canaryId, reason, traceId);
      return reply.send({ status: 'rolled_back' });
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // ============================================================
  // STATUS & HEALTH ENDPOINTS (3)
  // ============================================================

  // GET /api/civilization/status - Get civilization governance status
  fastify.get('/api/civilization/status', async (_req: FastifyRequest, reply: FastifyReply) => {
    try {
      const constitution = await calibrationConstitutionService.getActive();
      const activePolicies = await trustPolicyService.listActivePolicies();
      const unresolved = await calibrationDriftMonitorService.listUnresolved(10);
      const emergencyFreeze = await calibrationDriftMonitorService.isEmergencyFreezeActive();

      return reply.send({
        constitution: { active: !!constitution },
        policies: { active_count: activePolicies.length },
        drift: { unresolved_count: unresolved.length, emergency_freeze: emergencyFreeze },
      });
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // GET /api/civilization/health - Health check
  fastify.get('/api/civilization/health', async (_req: FastifyRequest, reply: FastifyReply) => {
    return reply.send({ status: 'ok', timestamp: new Date().toISOString() });
  });

  // GET /api/civilization/runtime/graph - L14 runtime graph
  fastify.get('/api/civilization/runtime/graph', async (_req: FastifyRequest, reply: FastifyReply) => {
    return reply.send({
      graph: civilizationRuntimeService.runtimeGraph(),
      scope: 'core_l14_runtime_graph',
    });
  });

  // POST /api/civilization/runtime/reachability-tick - Persist L14 coordinator reachability tick
  fastify.post('/api/civilization/runtime/reachability-tick', async (req: FastifyRequest, reply: FastifyReply) => {
    const { runtimeMode } = (req.body as { runtimeMode?: string } | undefined) ?? {};
    try {
      const tick = await civilizationRuntimeService.runReachabilityTick(runtimeMode ?? 'api_l14_runtime');
      return reply.status(tick.status === 'passed' ? 201 : 503).send(tick);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // POST /api/civilization/runtime/dispatch-tick - Route a goal through L14 coordinator to institutions
  fastify.post('/api/civilization/runtime/dispatch-tick', async (req: FastifyRequest, reply: FastifyReply) => {
    const body = (req.body as {
      goalId?: string;
      objective?: string;
      domains?: string[];
      rigorTier?: 'lite' | 'full';
      riskLevel?: 'low' | 'medium' | 'high';
      budget?: { tokens?: number; iterations?: number; seconds?: number };
      runtimeMode?: string;
    } | undefined) ?? {};
    try {
      const tick = await civilizationRuntimeService.runDispatchTick({
        goalId: body.goalId,
        objective: body.objective ?? '',
        domains: body.domains ?? [],
        rigorTier: body.rigorTier,
        riskLevel: body.riskLevel,
        budget: body.budget,
        runtimeMode: body.runtimeMode ?? 'api_l14_dispatch',
      });
      return reply.status(tick.status === 'dispatched' ? 201 : 409).send(tick);
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  // GET /api/civilization/runtime/scheduler - L14 scheduler status
  fastify.get('/api/civilization/runtime/scheduler', async (_req: FastifyRequest, reply: FastifyReply) => {
    return reply.send(civilizationSchedulerService.status());
  });

  // POST /api/civilization/runtime/scheduler/run-once - Execute one bounded scheduler tick
  fastify.post('/api/civilization/runtime/scheduler/run-once', async (req: FastifyRequest, reply: FastifyReply) => {
    const { runtimeMode } = (req.body as { runtimeMode?: string } | undefined) ?? {};
    try {
      const tick = await civilizationSchedulerService.runOnce(runtimeMode ?? 'api_scheduler_l14_runtime');
      return reply.status(tick.status === 'passed' ? 201 : 503).send({
        scheduler: civilizationSchedulerService.status(),
        tick,
      });
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request', scheduler: civilizationSchedulerService.status() });
    }
  });

  // POST /api/civilization/runtime/scheduler/start - Start bounded periodic L14 ticks
  fastify.post('/api/civilization/runtime/scheduler/start', async (req: FastifyRequest, reply: FastifyReply) => {
    const { intervalMs } = (req.body as { intervalMs?: number } | undefined) ?? {};
    try {
      return reply.send(civilizationSchedulerService.start(intervalMs ?? 60_000));
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request', scheduler: civilizationSchedulerService.status() });
    }
  });

  // POST /api/civilization/runtime/scheduler/stop - Stop periodic L14 ticks
  fastify.post('/api/civilization/runtime/scheduler/stop', async (_req: FastifyRequest, reply: FastifyReply) => {
    return reply.send(civilizationSchedulerService.stop());
  });

  // GET /api/civilization/governance/summary - Governance summary
  fastify.get('/api/civilization/governance/summary', async (_req: FastifyRequest, reply: FastifyReply) => {
    try {
      const unresolved = await calibrationDriftMonitorService.listUnresolved(50);
      const critical = await calibrationDriftMonitorService.getCriticalDrifts();
      const emergencyFreeze = await calibrationDriftMonitorService.isEmergencyFreezeActive();

      return reply.send({
        drift_monitoring: {
          total_unresolved: unresolved.length,
          critical_count: critical.length,
          emergency_freeze_active: emergencyFreeze,
        },
        governance_status: 'active',
      });
    } catch (e) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });
}
