import { DurableExecutionService, WorkflowTask } from '../src/services/durable-execution.service';

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
});
