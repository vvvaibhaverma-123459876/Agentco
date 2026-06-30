import crypto from 'crypto';
import { calibrationConstitutionService } from '../src/services/calibration-constitution.service';
import { riskTierClassifier } from '../src/services/risk-tier-classifier.service';

async function installRiskTestConstitution() {
  const version = await calibrationConstitutionService.createVersion(
    { name: `Risk Classifier Constitution ${Date.now()}` },
    crypto.randomUUID(),
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
  await calibrationConstitutionService.addAllowedChangeType({
    change_type_name: 'update_display_copy',
    description: 'Change non-runtime UI copy',
    category: 'interface',
    max_scope: 'institution',
    requires_eval: false,
    can_be_canaried: true,
  });
  await calibrationConstitutionService.addProhibitedChangeType(
    'delete_audit_events',
    'audit records are append-only'
  );
  await calibrationConstitutionService.addProtectedSurface({
    surface_name: 'Event Log',
    surface_type: 'table',
    description: 'Canonical event log',
    table_names: ['event_log'],
    column_patterns: ['.*_hash$'],
    function_patterns: [],
    is_immutable: true,
    requires_constitution_vote: true,
  });
}

describe('risk tier classifier', () => {
  beforeAll(async () => {
    await installRiskTestConstitution();
  });

  test('classifies allowed evaluated governance changes as medium', async () => {
    const result = await riskTierClassifier.classify({
      changeType: 'raise_evidence_standard',
      affectedTables: ['trust_policy_versions'],
      affectedColumns: ['minimum_evidence_tier'],
      requiresEval: true,
    });

    expect(result.riskTier).toBe('medium');
    expect(result.requiresHumanReview).toBe(false);
    expect(result.requiresConstitutionOverride).toBe(false);
    expect(result.reasons).toContain('evaluation required');
  });

  test('classifies sensitive production path changes as high even when allowed', async () => {
    const result = await riskTierClassifier.classify({
      changeType: 'update_display_copy',
      affectedPaths: ['backend/src/db/migrations/098_copy.sql'],
      touchesProductionRuntime: true,
    });

    expect(result.riskTier).toBe('high');
    expect(result.requiresHumanReview).toBe(true);
    expect(result.requiresConstitutionOverride).toBe(false);
  });

  test('classifies prohibited protected changes as critical and requiring override', async () => {
    const result = await riskTierClassifier.classify({
      changeType: 'delete_audit_events',
      affectedTables: ['event_log'],
      affectedColumns: ['event_hash'],
      operation: 'delete',
    });

    expect(result.riskTier).toBe('critical');
    expect(result.requiresHumanReview).toBe(true);
    expect(result.requiresConstitutionOverride).toBe(true);
    expect(result.reasons.join('\n')).toMatch(/prohibited|Protected surface/);
  });
});
