import crypto from 'crypto';
import { db } from '../src/db/client';
import { calibrationConstitutionService } from '../src/services/calibration-constitution.service';

async function requireConstitutionSchema() {
  const result = await db.query(
    `SELECT to_regclass('public.calibration_constitution_versions') AS versions,
            to_regclass('public.protected_surfaces') AS surfaces,
            to_regclass('public.allowed_change_types') AS allowed,
            to_regclass('public.prohibited_change_types') AS prohibited`
  );
  expect(result.rows[0]).toEqual({
    versions: 'calibration_constitution_versions',
    surfaces: 'protected_surfaces',
    allowed: 'allowed_change_types',
    prohibited: 'prohibited_change_types',
  });
}

describe('calibration constitution service', () => {
  beforeAll(async () => {
    await requireConstitutionSchema();
  });

  test('creates, activates, and verifies a canonical constitution version', async () => {
    const signer = crypto.randomUUID();
    const content = {
      rules: [{ action: 'raise_evidence_standard', requires_eval: true }],
      name: `Test Constitution ${Date.now()}`,
    };

    const version = await calibrationConstitutionService.createVersion(content, signer, 'test-signature');
    await calibrationConstitutionService.activateVersion(version.id);
    const active = await calibrationConstitutionService.getActive();

    expect(active?.id).toBe(version.id);
    await expect(calibrationConstitutionService.verifyIntegrity(version.id)).resolves.toBe(true);
  });

  test('validates allowed changes and blocks protected or prohibited changes', async () => {
    const signer = crypto.randomUUID();
    const version = await calibrationConstitutionService.createVersion(
      { name: `Validation Constitution ${Date.now()}` },
      signer,
      'test-signature'
    );
    await calibrationConstitutionService.activateVersion(version.id);
    await calibrationConstitutionService.addAllowedChangeType({
      change_type_name: 'raise_evidence_standard',
      description: 'Increase evidence requirements',
      category: 'calibration',
      max_scope: 'civilization',
      requires_eval: true,
      can_be_canaried: true,
    });
    await calibrationConstitutionService.addProhibitedChangeType(
      'delete_audit_events',
      'audit records are append-only'
    );
    await calibrationConstitutionService.addProtectedSurface({
      surface_name: 'Audit Log',
      surface_type: 'table',
      description: 'Canonical audit/event trail',
      table_names: ['event_log'],
      column_patterns: ['.*_hash$'],
      function_patterns: [],
      is_immutable: true,
      requires_constitution_vote: true,
    });

    const allowed = await calibrationConstitutionService.validateChange(
      'raise_evidence_standard',
      ['trust_policy_versions'],
      ['minimum_evidence_tier']
    );
    const blocked = await calibrationConstitutionService.validateChange(
      'delete_audit_events',
      ['event_log'],
      ['event_hash']
    );

    expect(allowed.is_compliant).toBe(true);
    expect(allowed.violations).toEqual([]);
    expect(blocked.is_compliant).toBe(false);
    expect(blocked.requires_override).toBe(true);
    expect(blocked.violations.join('\n')).toMatch(/prohibited|Protected surface/);
  });

  test('retireVersion fails explicitly because constitution records are immutable', async () => {
    await expect(calibrationConstitutionService.retireVersion(crypto.randomUUID())).rejects.toThrow(/append-only/);
  });
});
