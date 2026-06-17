/**
 * Audit Log Integration Tests — real Postgres, no mocks.
 *
 * Requires: Postgres on port 5433, agentco DB, migrations 004 + 012 applied.
 *
 * Tests:
 *   1. append() writes N real rows; query() returns them
 *   2. Hash chain integrity passes on unmodified data
 *   3. Tampering one row's output_summary is detected by verifyChainIntegrity()
 *   4. UPDATE on decision_log is rejected by trigger (append-only)
 *   5. DELETE on decision_log is rejected by trigger (append-only)
 */

import crypto from 'crypto';
import { Pool } from 'pg';
import { AuditLogService, AuditEntry } from '../../src/services/audit-log.service';

const DSN =
  process.env.DATABASE_URL ||
  'postgresql://agentco:password@localhost:5433/agentco?host=/tmp';

const SUPER_DSN =
  process.env.SUPERUSER_DATABASE_URL ||
  'postgresql://postgres:password@localhost:5433/agentco?host=/tmp';

// agentco-role pool used by the service under test
const agentcoDb = new Pool({ connectionString: DSN });
// postgres superuser pool used for setup/teardown/tamper
const superDb = new Pool({ connectionString: SUPER_DSN });

const svc = new AuditLogService();

const TEST_AGENT = `test-audit-${crypto.randomBytes(4).toString('hex')}`;
const TEST_SESSION = crypto.randomUUID();

const BASE_ENTRY: AuditEntry = {
  agent_id: TEST_AGENT,
  action_type: 'decision',
  input_summary: 'test input',
  output_summary: 'test output',
  confidence_score: 0.85,
  risk_level: 'low',
  session_id: TEST_SESSION,
};

beforeAll(async () => {
  // The hash chain spans ALL decision_log rows, so any partial delete would break it.
  // For a deterministic test we reset the whole chain to a clean slate.
  // Superuser + triggers disabled is required because decision_log is append-only.
  await superDb.query('ALTER TABLE decision_log DISABLE TRIGGER trg_decision_log_no_delete');
  try {
    await superDb.query('DELETE FROM decision_log');
  } finally {
    await superDb.query('ALTER TABLE decision_log ENABLE TRIGGER trg_decision_log_no_delete');
  }
});

afterAll(async () => {
  await agentcoDb.end();
  await superDb.end();
});

describe('Audit Log — real Postgres', () => {
  const logIds: string[] = [];

  test('append() writes N real rows', async () => {
    for (let i = 0; i < 5; i++) {
      const id = await svc.append({
        ...BASE_ENTRY,
        input_summary: `input ${i}`,
        output_summary: `output ${i}`,
      });
      expect(id).toMatch(/^[0-9a-f-]{36}$/);
      logIds.push(id);
    }
    expect(logIds).toHaveLength(5);
  });

  test('query() returns appended rows filtered by agent_id', async () => {
    const rows = await svc.query({ agent_id: TEST_AGENT, limit: 10 });
    expect(rows.length).toBe(5);
    for (const row of rows) {
      expect(row.agent_id).toBe(TEST_AGENT);
      expect(row.chain_hash).toMatch(/^[0-9a-f]{64}$/);
      expect(row.prev_hash).toMatch(/^[0-9a-f]{64}$/);
    }
  });

  test('verifyChainIntegrity() returns valid on unmodified rows', async () => {
    const result = await svc.verifyChainIntegrity();
    expect(result.valid).toBe(true);
    expect(result.broken_at).toBeUndefined();
  });

  test('verifyChainIntegrity() detects tampered output_summary', async () => {
    const tamperTarget = logIds[2];
    // Disable trigger temporarily (superuser only) to inject the tamper
    await superDb.query('ALTER TABLE decision_log DISABLE TRIGGER trg_decision_log_no_update');
    try {
      await superDb.query(
        `UPDATE decision_log SET output_summary = 'TAMPERED' WHERE log_id = $1`,
        [tamperTarget]
      );
    } finally {
      await superDb.query('ALTER TABLE decision_log ENABLE TRIGGER trg_decision_log_no_update');
    }

    const result = await svc.verifyChainIntegrity();
    expect(result.valid).toBe(false);
    expect(result.broken_at).toBeDefined();

    // Restore — disable trigger again for cleanup
    await superDb.query('ALTER TABLE decision_log DISABLE TRIGGER trg_decision_log_no_update');
    try {
      await superDb.query(
        `UPDATE decision_log SET output_summary = 'output 2' WHERE log_id = $1`,
        [tamperTarget]
      );
    } finally {
      await superDb.query('ALTER TABLE decision_log ENABLE TRIGGER trg_decision_log_no_update');
    }
  });

  test('trigger rejects UPDATE (append-only enforcement)', async () => {
    const targetId = logIds[0];
    await expect(
      agentcoDb.query(
        `UPDATE decision_log SET output_summary = 'hacked' WHERE log_id = $1`,
        [targetId]
      )
    ).rejects.toThrow(/append-only/i);
  });

  test('trigger rejects DELETE (append-only enforcement)', async () => {
    const targetId = logIds[0];
    await expect(
      agentcoDb.query(`DELETE FROM decision_log WHERE log_id = $1`, [targetId])
    ).rejects.toThrow(/append-only/i);
  });

  test('validateEntry() rejects invalid confidence_score', () => {
    expect(() =>
      // @ts-expect-error accessing private for test
      svc.validateEntry({ ...BASE_ENTRY, confidence_score: 1.5 })
    ).toThrow(/invalid confidence_score/);
  });

  test('validateEntry() rejects missing agent_id', () => {
    expect(() =>
      // @ts-expect-error accessing private for test
      svc.validateEntry({ ...BASE_ENTRY, agent_id: '' })
    ).toThrow(/missing agent_id/);
  });
});
