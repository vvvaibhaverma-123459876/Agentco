/**
 * Live civilization smoke tests — boots the REAL app against REAL Postgres (no mocks).
 *
 * This is the test class that catches what reachability + boundary-mocked unit tests can't:
 * schema drift, NOT-NULL violations, and simulation stubs. It surfaced (and now guards):
 *   - POST /api/goals NOT-NULL on autonomy_level_allowed
 *   - GET reputation referencing a non-existent column
 *   - civilization.solve returning method:"simulated"
 *
 * Gated behind RUN_LIVE_SMOKE=1 so the default `jest` run (no infra) stays green.
 * Run with:
 *   docker compose --profile dev up -d && (cd backend && python3 src/db/run_migrations.py)
 *   RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco npx jest civilization-smoke
 */
import { build } from '../../src/server';
import type { FastifyInstance } from 'fastify';

const RUN = process.env.RUN_LIVE_SMOKE === '1';
const d = RUN ? describe : describe.skip;

const op = { 'x-agentco-api-key': 'dev-api-key', 'x-agentco-role': 'operator' };
const aud = { 'x-agentco-api-key': 'dev-api-key', 'x-agentco-role': 'auditor' };
const svc = { 'x-agentco-api-key': 'dev-api-key', 'x-agentco-role': 'service' };

d('civilization live smoke (real Postgres)', () => {
  let app: FastifyInstance;

  beforeAll(async () => {
    process.env.NODE_ENV = process.env.NODE_ENV ?? 'development';
    app = await build();
    await app.ready();
  });

  afterAll(async () => {
    if (app) await app.close();
  });

  it('health is ok', async () => {
    const res = await app.inject({ method: 'GET', url: '/health' });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload).status).toBe('ok');
  });

  // ---- pure ----
  it('POST /api/trust/score (pure) returns a score', async () => {
    const res = await app.inject({ method: 'POST', url: '/api/trust/score', headers: aud,
      payload: { accuracy: 0.9, calibrationError: 0.05, consistency: 0.8, explainability: 0.8, uncertaintyQuality: 0.8, conformalCoverage: 0.9 } });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload)).toHaveProperty('overall_trust');
  });

  it('POST /api/calibration/metrics (pure) returns Brier', async () => {
    const res = await app.inject({ method: 'POST', url: '/api/calibration/metrics', headers: aud,
      payload: { predictions: [{ confidence: 0.8, correct: true }] } });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload)).toHaveProperty('brier_score');
  });

  // ---- DB-backed (these regressed before) ----
  it('POST /api/institutions creates an institution', async () => {
    const res = await app.inject({ method: 'POST', url: '/api/institutions', headers: op, payload: { domain: 'mathematics' } });
    expect(res.statusCode).toBe(201);
    expect(JSON.parse(res.payload)).toHaveProperty('id');
  });

  it('POST /api/goals inserts a goal (NOT-NULL autonomy_level_allowed regression)', async () => {
    const res = await app.inject({ method: 'POST', url: '/api/goals', headers: op,
      payload: { title: 'Smoke goal', domain: 'math.NT', proposedBy: 'agent-1', source: 'agent_proposed',
        riskLevel: 'low', successCriteria: { x: 1 }, stopConditions: { y: 1 } } });
    expect(res.statusCode).toBe(201);
    expect(JSON.parse(res.payload).status).toBe('proposed');
  });

  it('GET /api/institutions/:id/reputation does not 500 (column-drift regression)', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/institutions/inst-smoke/reputation', headers: aud });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload)).toHaveProperty('institution_id');
  });

  it('POST /api/governance/invariant/claim validates against real DB', async () => {
    const res = await app.inject({ method: 'POST', url: '/api/governance/invariant/claim', headers: svc,
      payload: { text: 'unbacked', support_source_ids: [] } });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload).valid).toBe(false);
  });

  it('GET /api/calibration/claim-accuracy returns a real report', async () => {
    const res = await app.inject({ method: 'GET', url: '/api/calibration/claim-accuracy', headers: aud });
    expect(res.statusCode).toBe(200);
  });

  // ---- de-simulation guard ----
  it('POST /api/civilization/solve is NOT simulated (real solver dispatch)', async () => {
    const res = await app.inject({ method: 'POST', url: '/api/civilization/solve', headers: aud,
      payload: { question: 'Is 17 a prime number?' } });
    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.payload);
    // The fix: must dispatch to a real service (symbolic/ensemble/rag) or fail honestly — never 'simulated'.
    expect(body.method).not.toBe('simulated');
    expect(['symbolic', 'ensemble', 'rag']).toContain(body.service);
  });
});
