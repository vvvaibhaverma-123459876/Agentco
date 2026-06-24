/**
 * Calibration governance routes
 * =============================
 * Integrates the calibration cluster (bayesian, confidence, claim-accuracy-tracker,
 * calibration-drift-monitor) into the deployable app. All were orphaned
 * (see CIVILIZATION_AUDIT.md).
 */
import type { FastifyInstance, FastifyRequest } from 'fastify';
import { requireScope } from '../security';
import { bayesianService } from '../services/bayesian.service';
import { confidenceService } from '../services/confidence.service';
import { claimAccuracyTracker } from '../services/claim-accuracy-tracker.service';

function bodyOf(req: FastifyRequest): Record<string, unknown> {
  return (req.body ?? {}) as Record<string, unknown>;
}

export async function calibrationRoutes(fastify: FastifyInstance) {
  // ECE / Brier / calibration metrics from a batch of (confidence, correct) predictions (pure).
  fastify.post('/api/calibration/metrics', { preHandler: requireScope('trust:read') }, async (req, reply) => {
    const b = bodyOf(req);
    const raw = Array.isArray(b.predictions) ? b.predictions : [];
    const predictions = raw
      .map((p) => p as { confidence?: unknown; correct?: unknown })
      .map((p) => ({ confidence: Number(p.confidence), correct: Boolean(p.correct) }))
      .filter((p) => Number.isFinite(p.confidence));
    if (predictions.length === 0) {
      return reply.status(400).send({ error: 'predictions: non-empty array of {confidence, correct} required' });
    }
    return reply.send(bayesianService.computeCalibrationMetrics(predictions));
  });

  // Single calibration-gap classification for a stated confidence vs actual accuracy (pure).
  fastify.post('/api/calibration/metric', { preHandler: requireScope('trust:read') }, async (req, reply) => {
    const b = bodyOf(req);
    const stated = Number(b.statedConfidence);
    const actual = Number(b.actualAccuracy);
    if (!Number.isFinite(stated) || !Number.isFinite(actual)) {
      return reply.status(400).send({ error: 'statedConfidence and actualAccuracy (numbers) required' });
    }
    return reply.send(confidenceService.computeCalibrationMetric(stated, actual));
  });

  // Domain/difficulty-adjusted confidence (pure).
  fastify.post('/api/calibration/adjust', { preHandler: requireScope('trust:read') }, async (req, reply) => {
    const b = bodyOf(req);
    const base = Number(b.baseConfidence);
    if (!Number.isFinite(base)) {
      return reply.status(400).send({ error: 'baseConfidence (number) required' });
    }
    return reply.send(confidenceService.adjustConfidence(base, String(b.domain ?? 'general'), String(b.difficulty ?? 'medium')));
  });

  // Aggregate calibration status across logged metrics.
  fastify.get('/api/calibration/status', { preHandler: requireScope('trust:read') }, async (_req, reply) => {
    return reply.send(confidenceService.getCalibrationStatus());
  });

  // Claim-accuracy calibration report (DB-backed).
  fastify.get('/api/calibration/claim-accuracy', { preHandler: requireScope('trust:read') }, async (_req, reply) => {
    const report = await claimAccuracyTracker.generateCalibrationReport();
    return reply.send(report);
  });
}
