import { spawnSync } from 'child_process';
import crypto from 'crypto';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import {
  acceptedDecisionLogChainHashes,
  auditLog,
  canonicalDecisionLogContent,
  CURRENT_DECISION_LOG_SERIALIZATION_VERSION,
} from '../src/services/audit-log.service';

const DSN = process.env.DATABASE_URL || 'postgresql://agentco:password@localhost:5433/agentco?host=/tmp';

async function decisionLogAvailable(): Promise<{ available: boolean; reason?: string }> {
  try {
    await db.query('SELECT log_id, chain_hash, prev_hash FROM decision_log LIMIT 1');
    return { available: true };
  } catch (error) {
    return { available: false, reason: error instanceof Error ? error.message : String(error) };
  }
}

afterAll(async () => {
  await db.end().catch(() => undefined);
});

async function withDecisionLogUpdateTriggersDisabled(fn: () => Promise<void>): Promise<void> {
  await migrationDb.query('ALTER TABLE decision_log DISABLE TRIGGER trg_decision_log_no_update');
  try {
    await fn();
  } finally {
    await migrationDb.query('ALTER TABLE decision_log ENABLE TRIGGER trg_decision_log_no_update');
  }
}

describe('decision_log cross-writer hash chain', () => {
  test('verifier accepts legacy Python insertion-order rows across the canonicalization seam', () => {
    const prevHash = 'a'.repeat(64);
    const fields = {
      log_id: '11111111-1111-4111-8111-111111111111',
      timestamp: '2026-07-06T12:34:56.123456+00:00',
      prev_hash: prevHash,
      agent_id: 'legacy-python-writer',
      action_type: 'decision',
      input_summary: 'python legacy input',
      output_summary: '{"action_type":"decision","outcome":"executed","override_id":null,"prediction_id":null}',
      confidence_score: 0.843,
      risk_level: 'medium',
      human_approved: false,
      human_approver_id: null,
      downstream_events: [],
      session_id: '22222222-2222-4222-8222-222222222222',
    };
    const chainHash = crypto.createHash('sha256').update(prevHash + JSON.stringify(fields)).digest('hex');

    const candidates = acceptedDecisionLogChainHashes({
      ...fields,
      timestamp: '2026-07-06T12:34:56.123Z',
      timestamp_text: '2026-07-06 12:34:56.123456+00',
      chain_hash: chainHash,
    });

    expect(candidates).toContainEqual({ version: 'v1.python-insertion-json', hash: chainHash });
  });

  test('verifier preserves legacy Python local timestamptz microseconds', () => {
    const row = {
      log_id: 'bd5ac052-3c68-496c-9058-349e07b5b458',
      timestamp: '2026-07-07T04:39:54.485Z',
      timestamp_text: '2026-07-07 10:09:54.485053+05:30',
      prev_hash: 'e884dab10f06f5908ce287293e342fce210eadfbbcd6294f96b60980c06d5807',
      chain_hash: '34ef65a78be4ed82e2ccc1b1904f1f8d88ca8e65617dd0f46db4e8787924dff3',
      agent_id: 'durable-audit-agent',
      action_type: 'escalation',
      input_summary: 'Durable audit round-trip',
      output_summary:
        '{"action_type": "analysis", "outcome": "blocked", "override_id": "a47a6e35-4838-4505-84a4-c1a4caba30ca", "prediction_id": null}',
      confidence_score: '0.490',
      risk_level: 'low',
      human_approved: false,
      human_approver_id: null,
      downstream_events: [],
      session_id: '89e53c45-dbbc-4718-84c0-6a6de89bf956',
    };

    expect(acceptedDecisionLogChainHashes(row)).toContainEqual({
      version: 'v1.python-insertion-json',
      hash: row.chain_hash,
    });
  });

  test('TS -> Python -> TS entries verify as one chain', async () => {
    const availability = await decisionLogAvailable();
    if (!availability.available) {
      console.warn(`SKIP: decision_log live-service test requires Postgres/migrations: ${availability.reason}`);
      return;
    }
    await migrationDb.query('TRUNCATE decision_log RESTART IDENTITY CASCADE');

    const repoRoot = path.resolve(__dirname, '../..');
    const sessionId = crypto.randomUUID();
    const agentId = `cross-writer-${crypto.randomBytes(4).toString('hex')}`;

    await auditLog.append({
      agent_id: agentId,
      action_type: 'decision',
      input_summary: 'ts entry 1',
      output_summary: 'ts output 1',
      confidence_score: 0.7314,
      risk_level: 'low',
      session_id: sessionId,
    });

    const pythonCode = [
      'from runtime.base_agent.audit_writer import DurableAuditWriter',
      'import os',
      'writer = DurableAuditWriter(os.environ["DATABASE_URL"])',
      'writer.write({',
      `  "agent_id": ${JSON.stringify(agentId)},`,
      '  "action_type": "decision",',
      '  "description": "python entry 2",',
      '  "trusted_confidence": 0.8426,',
      '  "risk_level": "medium",',
      '  "outcome": "executed",',
      `  "trace_id": ${JSON.stringify(sessionId)},`,
      '  "override_id": None,',
      '  "prediction_id": None,',
      '})',
    ].join('\n');

    const python = spawnSync(process.env.AGENTCO_PYTHON || 'python3.13', ['-c', pythonCode], {
      cwd: repoRoot,
      env: {
        ...process.env,
        DATABASE_URL: DSN,
        PYTHONPATH: process.env.PYTHONPATH ? `${repoRoot}:${process.env.PYTHONPATH}` : repoRoot,
      },
      encoding: 'utf8',
    });
    expect(python.status).toBe(0);
    expect(python.stderr).toBe('');

    await auditLog.append({
      agent_id: agentId,
      action_type: 'decision',
      input_summary: 'ts entry 3',
      output_summary: 'ts output 3',
      confidence_score: 0.9234,
      risk_level: 'low',
      session_id: sessionId,
    });

    const rows = await db.query(
      `SELECT COUNT(*)::int AS count
         FROM decision_log
        WHERE agent_id = $1
          AND session_id = $2`,
      [agentId, sessionId]
    );
    expect(Number(rows.rows[0].count)).toBe(3);

    const chainRows = await db.query(
      `SELECT log_id, agent_id, action_type, input_summary, output_summary,
              confidence_score, risk_level, human_approved, human_approver_id,
              downstream_events, session_id, timestamp, timestamp::text AS timestamp_text,
              chain_hash, prev_hash, serialization_version, attempt_id
         FROM decision_log
        WHERE agent_id = $1
          AND session_id = $2
        ORDER BY timestamp ASC, log_id ASC`,
      [agentId, sessionId]
    );
    for (const row of chainRows.rows) {
      expect(row.serialization_version).toBe(CURRENT_DECISION_LOG_SERIALIZATION_VERSION);
      expect(row.attempt_id).toEqual(expect.stringMatching(/^[0-9a-f-]{36}$/));
      expect(acceptedDecisionLogChainHashes(row)).toEqual([
        { version: CURRENT_DECISION_LOG_SERIALIZATION_VERSION, hash: row.chain_hash },
      ]);
    }

    const verification = await auditLog.verifyChainIntegrity();
    expect(verification).toEqual({ valid: true });
  });

  test('new row with version field but legacy hash fails verification', async () => {
    const availability = await decisionLogAvailable();
    if (!availability.available) {
      console.warn(`SKIP: decision_log live-service test requires Postgres/migrations: ${availability.reason}`);
      return;
    }
    await migrationDb.query('TRUNCATE decision_log RESTART IDENTITY CASCADE');

    const logId = await auditLog.append({
      agent_id: `version-negative-${crypto.randomBytes(4).toString('hex')}`,
      action_type: 'decision',
      input_summary: 'valid versioned row',
      output_summary: 'legacy hash tamper target',
      confidence_score: 0.5,
      risk_level: 'low',
      session_id: crypto.randomUUID(),
    });

    const { rows } = await db.query(
      `SELECT log_id, agent_id, action_type, input_summary, output_summary,
              confidence_score, risk_level, human_approved, human_approver_id,
              downstream_events, session_id, timestamp, timestamp::text AS timestamp_text,
              chain_hash, prev_hash, serialization_version, attempt_id
         FROM decision_log
        WHERE log_id = $1`,
      [logId]
    );
    const row = rows[0];
    const legacyContent = canonicalDecisionLogContent({
      log_id: row.log_id,
      timestamp: new Date(row.timestamp).toISOString(),
      prev_hash: row.prev_hash,
      agent_id: row.agent_id,
      action_type: row.action_type,
      input_summary: row.input_summary,
      output_summary: row.output_summary,
      confidence_score: Number(row.confidence_score),
      risk_level: row.risk_level,
      human_approved: row.human_approved,
      human_approver_id: row.human_approver_id,
      downstream_events: row.downstream_events ?? [],
      session_id: row.session_id,
    });
    const legacyHash = crypto.createHash('sha256').update(row.prev_hash + legacyContent).digest('hex');

    await withDecisionLogUpdateTriggersDisabled(async () => {
      await migrationDb.query('UPDATE decision_log SET chain_hash = $1 WHERE log_id = $2', [legacyHash, logId]);
    });

    expect(await auditLog.verifyChainIntegrity()).toEqual({ valid: false, broken_at: logId });
  });

  test('post-cutoff row missing serialization_version fails verification', async () => {
    const availability = await decisionLogAvailable();
    if (!availability.available) {
      console.warn(`SKIP: decision_log live-service test requires Postgres/migrations: ${availability.reason}`);
      return;
    }
    await migrationDb.query('TRUNCATE decision_log RESTART IDENTITY CASCADE');

    const logId = await auditLog.append({
      agent_id: `missing-version-${crypto.randomBytes(4).toString('hex')}`,
      action_type: 'decision',
      input_summary: 'missing version row',
      output_summary: 'must fail verification',
      confidence_score: 0.6,
      risk_level: 'low',
      session_id: crypto.randomUUID(),
    });

    await withDecisionLogUpdateTriggersDisabled(async () => {
      await migrationDb.query('UPDATE decision_log SET serialization_version = NULL WHERE log_id = $1', [logId]);
    });

    expect(await auditLog.verifyChainIntegrity()).toEqual({ valid: false, broken_at: logId });
  });

  test('tampering with serialization_version fails verification', async () => {
    const availability = await decisionLogAvailable();
    if (!availability.available) {
      console.warn(`SKIP: decision_log live-service test requires Postgres/migrations: ${availability.reason}`);
      return;
    }
    await migrationDb.query('TRUNCATE decision_log RESTART IDENTITY CASCADE');

    const logId = await auditLog.append({
      agent_id: `tampered-version-${crypto.randomBytes(4).toString('hex')}`,
      action_type: 'decision',
      input_summary: 'version tamper row',
      output_summary: 'must fail verification',
      confidence_score: 0.7,
      risk_level: 'low',
      session_id: crypto.randomUUID(),
    });

    await withDecisionLogUpdateTriggersDisabled(async () => {
      await migrationDb.query('UPDATE decision_log SET serialization_version = $1 WHERE log_id = $2', [
        'v3.tampered',
        logId,
      ]);
    });

    expect(await auditLog.verifyChainIntegrity()).toEqual({ valid: false, broken_at: logId });
  });

  test('duplicate TS attempt_id returns existing row without appending', async () => {
    const availability = await decisionLogAvailable();
    if (!availability.available) {
      console.warn(`SKIP: decision_log live-service test requires Postgres/migrations: ${availability.reason}`);
      return;
    }
    await migrationDb.query('TRUNCATE decision_log RESTART IDENTITY CASCADE');

    const attemptId = crypto.randomUUID();
    const agentId = `duplicate-attempt-${crypto.randomBytes(4).toString('hex')}`;
    const first = await auditLog.append({
      agent_id: agentId,
      action_type: 'decision',
      input_summary: 'first attempt body',
      output_summary: 'first attempt output',
      confidence_score: 0.5,
      risk_level: 'low',
      session_id: crypto.randomUUID(),
      attempt_id: attemptId,
    });
    const second = await auditLog.append({
      agent_id: agentId,
      action_type: 'decision',
      input_summary: 'conflicting retry body',
      output_summary: 'conflicting retry output',
      confidence_score: 0.9,
      risk_level: 'medium',
      session_id: crypto.randomUUID(),
      attempt_id: attemptId,
    });

    expect(second).toBe(first);
    const rows = await db.query(
      `SELECT COUNT(*)::int AS count, MIN(input_summary) AS input_summary
         FROM decision_log
        WHERE attempt_id = $1`,
      [attemptId]
    );
    expect(Number(rows.rows[0].count)).toBe(1);
    expect(rows.rows[0].input_summary).toBe('first attempt body');
    expect(await auditLog.verifyChainIntegrity()).toEqual({ valid: true });
  });
});
