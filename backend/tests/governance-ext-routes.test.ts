/**
 * Governance & safety integration tests.
 * - safety scorer tested directly against the REAL functions (pure).
 * - Routes proven wired into server.ts build(); DB-backed rbac mocked at boundary.
 */
jest.mock('../src/services/governance-rbac.service', () => ({
  governanceRBACService: { hasPermission: jest.fn() },
}));

import { build } from '../src/server';
import { safetyService } from '../src/services/safety.service';
import { governanceRBACService } from '../src/services/governance-rbac.service';

const gov = { 'x-agentco-api-key': 'dev-api-key', 'x-agentco-role': 'operator' };   // governance:mutate
const reader = { 'x-agentco-api-key': 'dev-api-key', 'x-agentco-role': 'auditor' }; // trust:read
const claimer = { 'x-agentco-api-key': 'dev-api-key', 'x-agentco-role': 'service' }; // claims:register

describe('safety response (pure, real functions)', () => {
  it('createSafeResponse + auditResponse: uncited low-confidence answer is flagged', () => {
    const safe = safetyService.createSafeResponse('maybe', 0.2, []);
    const audit = safetyService.auditResponse(safe);
    expect(audit.cited).toBe(false);          // no sources
    expect(audit.flagged).toBe(true);         // low confidence ⇒ flags/risk
    expect(audit.compliance_score).toBeGreaterThanOrEqual(0);
    expect(audit.compliance_score).toBeLessThanOrEqual(1);
  });
});

describe('governance/safety routes wired into the deployable app', () => {
  beforeEach(() => {
    (governanceRBACService.hasPermission as jest.Mock).mockReset();
  });

  it('POST /api/governance/rbac/check returns the permission decision', async () => {
    (governanceRBACService.hasPermission as jest.Mock).mockResolvedValueOnce(true);
    const app = await build();
    const res = await app.inject({
      method: 'POST', url: '/api/governance/rbac/check', headers: gov,
      payload: { entityId: 'agent-1', permission: 'goals:approve' },
    });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload).allowed).toBe(true);
    expect(governanceRBACService.hasPermission).toHaveBeenCalledWith('agent-1', 'goals:approve');
    await app.close();
  });

  it('POST /api/governance/invariant/claim flags a claim with no evidence sources', async () => {
    const app = await build();
    const res = await app.inject({
      method: 'POST', url: '/api/governance/invariant/claim', headers: claimer,
      payload: { text: 'unbacked claim', support_source_ids: [] },
    });
    expect(res.statusCode).toBe(200);
    const body = JSON.parse(res.payload);
    expect(body.valid).toBe(false);
    expect(body.errors.join(' ')).toMatch(/evidence source/i);
    await app.close();
  });

  it('POST /api/safety/response returns a safety-wrapped response + audit', async () => {
    const app = await build();
    const res = await app.inject({
      method: 'POST', url: '/api/safety/response', headers: reader,
      payload: { answer: 'the sky is blue', confidence: 0.3, sourceFactIds: [] },
    });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload)).toHaveProperty('audit');
    await app.close();
  });

  it('POST /api/provenance/verify returns false for a non-matching signature', async () => {
    const app = await build();
    const res = await app.inject({
      method: 'POST', url: '/api/provenance/verify', headers: reader,
      payload: { payload: { a: 1 }, signatureHex: '00'.repeat(64) }, // 64-byte zero sig
    });
    expect(res.statusCode).toBe(200);
    expect(JSON.parse(res.payload).valid).toBe(false);
    await app.close();
  });
});
