import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { selfModValidator } from '../src/services/self-modification-validator.service';
import { isProtected, validateProtectedSurfaces } from '../src/services/protected-surface-validator.service';

async function applyCompatibilityMigration() {
  const migration = fs.readFileSync(
    path.resolve(__dirname, '../src/db/migrations/097_self_modification_validation_compatibility.sql'),
    'utf8'
  );
  await db.query(migration);
}

async function createCandidate(artifact: Record<string, unknown>): Promise<string> {
  const replayBatchId = crypto.randomUUID();
  const learnerRunId = crypto.randomUUID();
  const artifactId = crypto.randomUUID();
  const candidateId = crypto.randomUUID();
  const suffix = `${Date.now()}-${Math.random()}`;

  await db.query(
    `INSERT INTO replay_batches (id, source_filter_json, trajectory_ids, batch_hash, batch_size, created_by, tags)
     VALUES ($1, '{}'::jsonb, ARRAY[]::UUID[], $2, 0, 'protected-surface-test', ARRAY[]::TEXT[])`,
    [replayBatchId, `protected-surface-${suffix}`]
  );
  await db.query(
    `INSERT INTO learner_runs (id, replay_batch_id, policy_version_before, baseline_metrics_json)
     VALUES ($1, $2, 'test-policy', '{}'::jsonb)`,
    [learnerRunId, replayBatchId]
  );
  await db.query(
    `INSERT INTO artifacts (id, artifact_type, artifact_hash, artifact_json)
     VALUES ($1, 'config_update', $2, $3::jsonb)`,
    [artifactId, `artifact-${suffix}`, JSON.stringify(artifact)]
  );
  await db.query(
    `INSERT INTO learner_candidates
       (id, learner_run_id, candidate_type, artifact_id, artifact_hash, artifact_json, metrics_before_json, metrics_after_json)
     VALUES ($1, $2, 'config_update', $3, $4, $5::jsonb, '{}'::jsonb, '{}'::jsonb)`,
    [candidateId, learnerRunId, artifactId, `candidate-${suffix}`, JSON.stringify(artifact)]
  );

  return candidateId;
}

describe('protected surface enforcer', () => {
  beforeAll(async () => {
    await applyCompatibilityMigration();
  });

  test('blocks self-modification candidates that touch critical protected surfaces', async () => {
    const candidateId = await createCandidate({
      changes: [
        { field: 'backend/src/services/audit-log.service.ts', action: 'update', value: 'disable AuditLogService' },
      ],
    });

    const validation = await selfModValidator.validateCandidate(candidateId);
    const stored = await selfModValidator.getValidation(validation.id);
    const audit = await db.query(
      `SELECT event_type, status, severity FROM audit_events WHERE entity_id = $1`,
      [candidateId]
    );

    expect(validation.blocked).toBe(true);
    expect(validation.touchedSurfaces).toContain('Audit Log Immutability');
    expect(validation.blockedReasons.join('\n')).toMatch(/CRITICAL/);
    expect(stored.blockedReasons).toEqual(validation.blockedReasons);
    expect(audit.rows).toEqual(expect.arrayContaining([
      expect.objectContaining({ event_type: 'self_modification_blocked', status: 'blocked', severity: 'high' }),
    ]));
  });

  test('passes candidates that do not touch protected surfaces', async () => {
    const candidateId = await createCandidate({
      changes: [
        { field: 'backend/src/config/display-preferences.json', action: 'update', value: { density: 'compact' } },
      ],
    });

    const validation = await selfModValidator.validateCandidate(candidateId);

    expect(validation.blocked).toBe(false);
    expect(validation.touchedSurfaces).toEqual([]);
  });

  test('standalone protected-surface helper rejects critical and high-risk surfaces', async () => {
    const candidateId = `candidate-helper-${Date.now()}`;
    expect(isProtected('decision_log')).toBe(true);
    await expect(validateProtectedSurfaces(candidateId, {
      changes: [{ field: 'policy_engine.threshold', action: 'update' }],
    })).rejects.toThrow(/Policy Engine|protected surface/);

    const audit = await db.query(
      `SELECT event_type, status, severity FROM audit_events WHERE entity_id = $1`,
      [candidateId]
    );
    expect(audit.rows).toEqual(expect.arrayContaining([
      expect.objectContaining({ event_type: 'protected_surface_violation', status: 'blocked', severity: 'high' }),
    ]));
  });
});
