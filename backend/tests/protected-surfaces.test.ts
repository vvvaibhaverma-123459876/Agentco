/**
 * Protected-surface enforcer — DB-backed verification + audit trail.
 * File-derivation/existence checks run always (no I/O beyond the filesystem).
 * The audit-trail record/retrieve (autonomy_memory) needs Postgres, so it is gated behind
 * RUN_LIVE_SMOKE=1 (same convention as the civilization smoke suite).
 *
 * NOTE: this file was previously a console.log script with no it() blocks, so it always
 * failed jest with "must contain at least one test". Converted to real assertions.
 */
import { describe, it, expect } from '@jest/globals';
import { ProtectedSurfaceEnforcerService } from '../src/services/protected-surface-enforcer.service';

describe('protected surface enforcer (filesystem-derived)', () => {
  const enforcer = new ProtectedSurfaceEnforcerService();

  it('auto-derives the 4 protected surfaces from policy.py and all exist', async () => {
    const surfaces = enforcer.getProtectedSurfaces();
    expect(surfaces.length).toBe(4);
    const state = await enforcer.verifyProtectedSurfacesExist();
    expect(state.surfaces.length).toBe(4);
    expect(state.all_exist).toBe(true);
    for (const s of state.surfaces) {
      expect(s.exists).toBe(true);
      expect(s.content_hash).toBeTruthy();
    }
  });

  it('requires human approval for a critical modification of a protected surface', async () => {
    const result = await enforcer.evaluateModificationAttempt(
      'calibration/evidence/evidence_kernel.py',
      'attempt to modify protected surface',
      'critical',
    );
    expect(result.requires_human_approval).toBe(true);
  });
});

const RUN_DB = process.env.RUN_LIVE_SMOKE === '1';
(RUN_DB ? describe : describe.skip)('protected surface audit trail (real Postgres)', () => {
  const enforcer = new ProtectedSurfaceEnforcerService();

  it('records a verification and reads it back from autonomy_memory', async () => {
    const state = await enforcer.verifyProtectedSurfacesExist();
    await enforcer.recordSurfaceVerification(state);
    const latest = await enforcer.getLatestSurfaceState();
    expect(latest).not.toBeNull();
    expect(latest!.surfaces.length).toBe(4);
    expect(latest!.all_exist).toBe(true);
  });
});
