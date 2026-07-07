import { spawnSync } from 'child_process';
import crypto from 'crypto';
import path from 'path';
import { db } from '../src/db/client';
import { acceptedDecisionLogChainHashes, auditLog } from '../src/services/audit-log.service';

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

  test('TS -> Python -> TS entries verify as one chain', async () => {
    const availability = await decisionLogAvailable();
    if (!availability.available) {
      console.warn(`SKIP: decision_log live-service test requires Postgres/migrations: ${availability.reason}`);
      return;
    }

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

    const verification = await auditLog.verifyChainIntegrity();
    expect(verification).toEqual({ valid: true });
  });
});
