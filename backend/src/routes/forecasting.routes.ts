/**
 * Forecasting & calibration-governance routes
 * ===========================================
 * Integrates dynamic-calibration, autonomy-forecasting, phase0b-calibration,
 * calibration-drift-monitor and ensemble into the deployable app. All were orphaned
 * (see CIVILIZATION_AUDIT.md).
 */
import type { FastifyInstance, FastifyRequest } from 'fastify';
import { requireScope } from '../security';
import { dynamicCalibrationService } from '../services/dynamic-calibration.service';
import { calibrationDriftMonitorService } from '../services/calibration-drift-monitor.service';
import { ensembleService } from '../services/ensemble.service';
import { Phase0bCalibrationService } from '../services/phase0b-calibration.service';
import { AutonomyForecastingService } from '../services/autonomy-forecasting.service';

const phase0b = new Phase0bCalibrationService();
const forecasting = new AutonomyForecastingService();

function bodyOf(req: FastifyRequest): Record<string, unknown> {
  return (req.body ?? {}) as Record<string, unknown>;
}

export async function forecastingRoutes(fastify: FastifyInstance) {
  // Domain/difficulty-calibrated confidence (pure, learned parameters).
  fastify.post('/api/calibration/dynamic/confidence', { preHandler: requireScope('trust:read') }, async (req, reply) => {
    const b = bodyOf(req);
    const base = Number(b.baseConfidence);
    if (!Number.isFinite(base)) {
      return reply.status(400).send({ error: 'baseConfidence (number) is required' });
    }
    return reply.send(dynamicCalibrationService.getCalibratedConfidence(base, String(b.domain ?? 'general'), String(b.difficulty ?? 'medium')));
  });

  // Record performance feedback that updates the dynamic calibration model.
  fastify.post('/api/calibration/dynamic/feedback', { preHandler: requireScope('trust:read') }, async (req, reply) => {
    const b = bodyOf(req);
    if (typeof b.domain !== 'string') {
      return reply.status(400).send({ error: 'domain is required' });
    }
    dynamicCalibrationService.recordPerformanceFeedback(b as unknown as Parameters<typeof dynamicCalibrationService.recordPerformanceFeedback>[0]);
    return reply.status(202).send({ recorded: true });
  });

  // Register an external-event prediction (pre-registration for calibration).
  fastify.post('/api/predictions', { preHandler: requireScope('claims:register') }, async (req, reply) => {
    const b = bodyOf(req);
    try {
      const record = await phase0b.registerPrediction(b as unknown as Parameters<typeof phase0b.registerPrediction>[0]);
      return reply.status(201).send(record);
    } catch (error) {
      return reply.status(400).send({ error: error instanceof Error ? error.message : String(error) });
    }
  });

  // Generate a forecast for an external event.
  fastify.post('/api/forecast', { preHandler: requireScope('claims:register') }, async (req, reply) => {
    const b = bodyOf(req);
    try {
      const forecast = await forecasting.generateForecast(b as unknown as Parameters<typeof forecasting.generateForecast>[0]);
      return reply.send(forecast);
    } catch (error) {
      return reply.status(502).send({ error: error instanceof Error ? error.message : String(error) });
    }
  });

  // List unresolved calibration-drift events.
  fastify.get('/api/calibration/drift', { preHandler: requireScope('trust:read') }, async (_req, reply) => {
    const events = await calibrationDriftMonitorService.listUnresolved();
    return reply.send({ events, count: events.length });
  });

  // Ensemble vote across models for a question.
  fastify.post('/api/ensemble/vote', { preHandler: requireScope('trust:read') }, async (req, reply) => {
    const { question } = bodyOf(req);
    if (typeof question !== 'string' || !question.trim()) {
      return reply.status(400).send({ error: 'question is required' });
    }
    const result = await ensembleService.ensembleVote(question);
    return reply.send(result);
  });
}
