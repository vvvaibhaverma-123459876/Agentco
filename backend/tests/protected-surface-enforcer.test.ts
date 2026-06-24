/**
 * Protected-surface enforcer — evaluateModificationAttempt logic (no DB).
 * Tests the authoritative, policy.py-derived enforcement that B.3 wired into the
 * self-modification validator. The method reads surfaces from governance/policy.py at
 * construction (filesystem) and performs no DB I/O, so it is directly unit-testable.
 */
import { describe, it, expect } from '@jest/globals';
import { ProtectedSurfaceEnforcerService } from '../src/services/protected-surface-enforcer.service';

describe('ProtectedSurfaceEnforcerService.evaluateModificationAttempt', () => {
  const enforcer = new ProtectedSurfaceEnforcerService();

  it('REQUIRES human approval for a protected surface (provenance.service)', async () => {
    const v = await enforcer.evaluateModificationAttempt(
      'backend/src/services/provenance.service.ts',
      'rewrite provenance hashing',
      'high',
    );
    expect(v.requires_human_approval).toBe(true);
  });

  it('REQUIRES human approval for the evidence kernel (path substring match)', async () => {
    const v = await enforcer.evaluateModificationAttempt(
      '/repo/calibration/evidence/evidence_kernel.py',
      'change scoring',
      'high',
    );
    expect(v.requires_human_approval).toBe(true);
  });

  it('REQUIRES human approval for ANY change at critical risk (even benign paths)', async () => {
    const v = await enforcer.evaluateModificationAttempt(
      'backend/src/services/some-benign-file.ts',
      'delete a helper',
      'critical',
    );
    expect(v.requires_human_approval).toBe(true);
  });

  it('ALLOWS a benign, non-critical change without human approval', async () => {
    const v = await enforcer.evaluateModificationAttempt(
      'backend/src/services/some-benign-file.ts',
      'rename a local variable',
      'high',
    );
    expect(v.requires_human_approval).toBe(false);
  });

  it('FAILS CLOSED: an enforcer that loaded no surfaces requires approval for everything', async () => {
    // Force the load-failed branch by constructing against a directory with no policy.py.
    const broken = new ProtectedSurfaceEnforcerService();
    // @ts-expect-error — exercise fail-closed by emptying the surface set.
    broken.protectedSurfaces = new Set();
    // @ts-expect-error
    broken.loadFailed = true;
    const v = await broken.evaluateModificationAttempt('any/benign/path.ts', 'noop', 'low');
    expect(v.requires_human_approval).toBe(true);
  });
});
