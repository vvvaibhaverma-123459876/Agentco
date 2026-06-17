/**
 * Override Queue Integration Tests — real Postgres, no mocks.
 *
 * Requires: Postgres on localhost:5433, override_queue table (migration 013).
 *
 * Tests:
 *   1. enqueue() persists and returns a pending override
 *   2. Pending override blocks action (status is 'pending', not 'approved')
 *   3. resolve('approved') unblocks: status becomes 'approved' with approval_token
 *   4. resolve on already-resolved throws (DB trigger / app-layer guard)
 *   5. SLA expiry sets status to 'expired' (NOT 'approved') — action stays blocked
 *   6. listPending() returns only pending overrides
 *   7. getOverdueSla() returns expired overrides
 */

import crypto from 'crypto';
import { Pool } from 'pg';
import { OverrideQueueService } from '../../src/services/override-queue.service';

const DSN =
  process.env.DATABASE_URL ||
  'postgresql://agentco:password@localhost:5433/agentco?host=/tmp';

const db = new Pool({ connectionString: DSN });
const svc = new OverrideQueueService();

const TEST_AGENT = `test-override-${crypto.randomBytes(3).toString('hex')}`;

afterAll(async () => {
  await db.query(`DELETE FROM override_queue WHERE agent_id LIKE 'test-override-%'`);
  await db.end();
});

describe('Override Queue — real Postgres', () => {
  test('enqueue() persists with status=pending', async () => {
    const req = await svc.enqueue(TEST_AGENT, 'config_change', 'high', { rationale: 'test' });
    expect(req.request_id).toBeDefined();
    expect(req.status).toBe('pending');
    expect(Number(req.sla_hours)).toBe(4);

    const { rows } = await db.query(
      `SELECT status, risk_level, agent_id FROM override_queue WHERE request_id=$1`,
      [req.request_id]
    );
    expect(rows).toHaveLength(1);
    expect(rows[0].status).toBe('pending');
    expect(rows[0].risk_level).toBe('high');
  });

  test('pending override is NOT approved — action is blocked', async () => {
    const req = await svc.enqueue(TEST_AGENT, 'spend_approval', 'critical', { amount: 50000 });
    expect(req.status).toBe('pending');
    // Confirm there is no approval_token (action not unblocked)
    const { rows } = await db.query(
      `SELECT approval_token FROM override_queue WHERE request_id=$1`,
      [req.request_id]
    );
    expect(rows[0].approval_token).toBeNull();
  });

  test('resolve(approved) sets status=approved and issues approval_token', async () => {
    const req = await svc.enqueue(TEST_AGENT, 'config_change', 'high', {});
    const resolved = await svc.resolve(req.request_id, 'approved', 'human-approver-1', 'LGTM');
    expect(resolved.status).toBe('approved');
    expect(resolved.approval_token).toBeDefined();
    expect(typeof resolved.approval_token).toBe('string');
    expect(resolved.resolved_by).toBe('human-approver-1');
  });

  test('resolve on already-resolved request throws', async () => {
    const req = await svc.enqueue(TEST_AGENT, 'config_change', 'high', {});
    await svc.resolve(req.request_id, 'rejected', 'human-1', 'no thanks');
    await expect(
      svc.resolve(req.request_id, 'approved', 'human-2', 'override')
    ).rejects.toThrow(/already rejected/i);
  });

  test('SLA expiry sets status=expired (NOT approved) — action stays blocked', async () => {
    const req = await svc.enqueue(TEST_AGENT, 'novel_incident', 'critical', {});
    // Force expires_at into the past
    await db.query(
      `UPDATE override_queue SET expires_at = NOW() - INTERVAL '1 minute' WHERE request_id=$1`,
      [req.request_id]
    );
    // Trigger expiry by calling listPending() which calls _expireOverdue()
    await svc.listPending();

    const { rows } = await db.query(
      `SELECT status, approval_token FROM override_queue WHERE request_id=$1`,
      [req.request_id]
    );
    expect(rows[0].status).toBe('expired');
    expect(rows[0].approval_token).toBeNull();  // never approved
  });

  test('listPending() returns only pending overrides for agent', async () => {
    // Create one pending and one resolved
    const pending = await svc.enqueue(TEST_AGENT, 'config_change', 'high', {});
    const toResolve = await svc.enqueue(TEST_AGENT, 'config_change', 'high', {});
    await svc.resolve(toResolve.request_id, 'rejected', 'human-1');

    const list = await svc.listPending({ agent_id: TEST_AGENT });
    const found = list.find(r => r.request_id === pending.request_id);
    const resolved = list.find(r => r.request_id === toResolve.request_id);
    expect(found).toBeDefined();
    expect(resolved).toBeUndefined();
  });

  test('getOverdueSla() returns expired overrides', async () => {
    const req = await svc.enqueue(TEST_AGENT, 'novel_incident', 'critical', {});
    await db.query(
      `UPDATE override_queue SET expires_at = NOW() - INTERVAL '1 minute' WHERE request_id=$1`,
      [req.request_id]
    );
    const overdue = await svc.getOverdueSla();
    const found = overdue.find(r => r.request_id === req.request_id);
    expect(found).toBeDefined();
    expect(found!.status).toBe('expired');
  });
});
