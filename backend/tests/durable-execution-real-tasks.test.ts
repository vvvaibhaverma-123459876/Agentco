import { DurableExecutionService, WorkflowTask } from '../src/services/durable-execution.service';
import { db } from '../src/db/client';
import { disconnectProducer } from '../src/db/kafka';

function task(task_type: string, payload: Record<string, unknown>): WorkflowTask {
  return {
    task_id: 'task-1',
    agent_id: 'reviewer-agent',
    task_type,
    payload,
    queued_at: new Date().toISOString(),
    status: 'running',
  };
}

describe('DurableExecutionService real review/decision handlers', () => {
  const originalFetch = global.fetch;
  const originalEnv = { ...process.env };

  afterAll(async () => {
    await disconnectProducer();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    process.env = { ...originalEnv };
  });

  test('review uses LLM JSON and does not return placeholder summary', async () => {
    process.env.LLM_API_KEY = 'test-key';
    process.env.LLM_BASE_URL = 'https://llm.example.test/v1';
    process.env.LLM_MODEL_DEFAULT = 'test-model';
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        choices: [{
          message: {
            content: JSON.stringify({
              decision: 'changes_requested',
              findings: ['missing test evidence'],
              required_changes: ['add integration test'],
              confidence: 0.74,
              evidence_ids_used: ['ev1'],
            }),
          },
        }],
      }),
    }) as unknown as typeof fetch;

    const service = new DurableExecutionService();
    const result = await (service as any).dispatch(task('review', {
      subject: 'Pull request 12',
      criteria: ['tests', 'security'],
      evidence: [{ id: 'ev1', text: 'No integration test attached' }],
    }));

    expect(result).toEqual(expect.objectContaining({
      kind: 'review_result',
      decision: 'changes_requested',
      confidence: 0.74,
    }));
    expect(result.findings).toEqual(['missing test evidence']);
  });

  test('decision rejects LLM-selected option not present in payload', async () => {
    process.env.LLM_API_KEY = 'test-key';
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        choices: [{
          message: {
            content: JSON.stringify({
              selected_option: 'ship_anyway',
              rationale: 'bad output',
              confidence: 0.91,
              evidence_ids_used: [],
              escalation_required: false,
            }),
          },
        }],
      }),
    }) as unknown as typeof fetch;

    const service = new DurableExecutionService();

    await expect((service as any).dispatch(task('decision', {
      options: ['approve', 'reject'],
      criteria: ['security'],
    }))).rejects.toThrow(/option not present/);
  });

  test('decision requires LLM key rather than selecting first option', async () => {
    delete process.env.LLM_API_KEY;
    delete process.env.OPENAI_API_KEY;
    const service = new DurableExecutionService();

    await expect((service as any).dispatch(task('decision', {
      options: ['approve', 'reject'],
      criteria: ['security'],
    }))).rejects.toThrow(/LLM_API_KEY/);
  });

  test('enqueue rejects agents that are not in the canonical registry', async () => {
    const service = new DurableExecutionService();

    await expect(
      service.enqueue('unregistered-agent', 'health_check', {})
    ).rejects.toThrow(/not registered/);
  });

  test('runs a registered durable task and records provenance pointers', async () => {
    const service = new DurableExecutionService();
    const queued = await service.enqueue('reviewer-agent', 'health_check', {
      probe: 'durable-execution-registry-test',
    });

    const completed = await service.run(queued.task_id);

    expect(completed.status).toBe('done');
    expect(completed.audit_log_id).toEqual(expect.stringMatching(/^[0-9a-f-]{36}$/));
    expect(completed.action_attestation_id).toEqual(expect.stringMatching(/^[0-9a-f-]{36}$/));
    expect(completed.result).toEqual(expect.objectContaining({
      kind: 'health_check_result',
      agent_id: 'reviewer-agent',
      executed_by: 'durable-execution-service',
    }));

    const stored = await db.query(
      `SELECT status, claimed_by, audit_log_id, action_attestation_id
         FROM workflow_tasks
        WHERE task_id = $1`,
      [queued.task_id]
    );
    expect(stored.rows).toEqual([
      expect.objectContaining({
        status: 'done',
        claimed_by: 'backend-dispatcher',
        audit_log_id: completed.audit_log_id,
        action_attestation_id: completed.action_attestation_id,
      }),
    ]);
  });
});
