import { LlmProviderError, LlmProviderService } from '../src/services/llm-provider.service';
import { resourceLedger } from '../src/services/resource-ledger.service';

function jsonResponse(content: string, status = 200, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify({
    model: 'gpt-test',
    choices: [{ message: { content } }],
    usage: { prompt_tokens: 3, completion_tokens: 4, total_tokens: 7 },
  }), { status, headers });
}

function jsonResponseWithoutUsage(content: string) {
  return new Response(JSON.stringify({
    model: 'gpt-test',
    choices: [{ message: { content } }],
  }), { status: 200 });
}

describe('LlmProviderService', () => {
  const savedEnv = { ...process.env };
  let fetchSpy: jest.SpiedFunction<typeof fetch>;

  beforeEach(() => {
    process.env = { ...savedEnv };
    process.env.LLM_API_KEY = 'sk-test';
    process.env.LLM_BASE_URL = 'https://llm.example/v1';
    process.env.LLM_MODEL_DEFAULT = 'gpt-test';
    process.env.LLM_MAX_RETRIES = '2';
    process.env.LLM_RETRY_BASE_MS = '0';
    process.env.LLM_REQUEST_TIMEOUT_MS = '1000';
    process.env.LLM_TOTAL_DEADLINE_MS = '3000';
    fetchSpy = jest.spyOn(globalThis, 'fetch');
  });

  afterEach(() => {
    fetchSpy.mockRestore();
    jest.restoreAllMocks();
    process.env = savedEnv;
  });

  test('fails closed when provider credentials are missing', async () => {
    delete process.env.LLM_API_KEY;
    delete process.env.OPENAI_API_KEY;

    await expect(new LlmProviderService().callJson({
      operation: 'missing config test',
      system: 'system',
      user: 'user',
    })).rejects.toMatchObject({ code: 'missing_config', retryable: false });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  test('retries retryable provider failures and returns usage metadata', async () => {
    fetchSpy
      .mockResolvedValueOnce(new Response('temporary', { status: 500 }))
      .mockResolvedValueOnce(jsonResponse('{"answer":"ok"}'));

    const result = await new LlmProviderService().callJson({
      operation: 'retry test',
      system: 'system',
      user: 'user',
    });

    expect(fetchSpy).toHaveBeenCalledTimes(2);
    expect(result.json).toEqual({ answer: 'ok' });
    expect(result.usage.totalTokens).toBe(7);
    expect(result.attempts).toBe(2);
  });

  test('does not retry non-retryable 4xx errors', async () => {
    fetchSpy.mockResolvedValue(new Response('bad request', { status: 400 }));

    await expect(new LlmProviderService().callJson({
      operation: 'bad request test',
      system: 'system',
      user: 'user',
    })).rejects.toMatchObject({ code: 'non_retryable_http', retryable: false });
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  test('rejects malformed provider JSON', async () => {
    fetchSpy.mockResolvedValue(jsonResponse('not-json'));

    await expect(new LlmProviderService().callJson({
      operation: 'malformed test',
      system: 'system',
      user: 'user',
    })).rejects.toMatchObject({ code: 'malformed_response', retryable: false });
  });

  test('propagates caller cancellation without retrying', async () => {
    const controller = new AbortController();
    fetchSpy.mockImplementation((_url, init) => new Promise((_resolve, reject) => {
      (init?.signal as AbortSignal).addEventListener('abort', () => {
        reject(Object.assign(new Error('aborted'), { name: 'AbortError' }));
      });
      controller.abort();
    }));

    await expect(new LlmProviderService().callJson({
      operation: 'cancel test',
      system: 'system',
      user: 'user',
      signal: controller.signal,
    })).rejects.toMatchObject({ code: 'cancelled', retryable: false });
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  test('maps per-attempt timeout to a retryable provider error', async () => {
    process.env.LLM_MAX_RETRIES = '0';
    process.env.LLM_REQUEST_TIMEOUT_MS = '1';
    process.env.LLM_TOTAL_DEADLINE_MS = '5';
    fetchSpy.mockImplementation((_url, init) => new Promise((_resolve, reject) => {
      (init?.signal as AbortSignal).addEventListener('abort', () => {
        reject(Object.assign(new Error('aborted'), { name: 'AbortError' }));
      });
    }));

    await expect(new LlmProviderService().callJson({
      operation: 'timeout test',
      system: 'system',
      user: 'user',
    })).rejects.toBeInstanceOf(LlmProviderError);
  });

  test('production LLM calls fail closed without durable budget configuration', async () => {
    process.env.NODE_ENV = 'production';
    delete process.env.LLM_RESOURCE_ACCOUNT_ID;
    delete process.env.LLM_RESOURCE_ACTOR_ID;

    await expect(new LlmProviderService().callJson({
      operation: 'budget required test',
      system: 'system',
      user: 'user',
    })).rejects.toMatchObject({ code: 'budget_unavailable', retryable: false });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  test('reserves and settles durable budget around a successful provider call', async () => {
    const actorId = '11111111-1111-4111-8111-111111111111';
    const accountId = '22222222-2222-4222-8222-222222222222';
    process.env.LLM_BUDGET_ENFORCEMENT = 'required';
    process.env.LLM_RESOURCE_ACTOR_ID = actorId;
    process.env.LLM_RESOURCE_ACCOUNT_ID = accountId;
    process.env.LLM_MAX_OUTPUT_TOKENS = '20';
    fetchSpy.mockResolvedValue(jsonResponse('{"answer":"ok"}'));
    const reserveSpy = jest.spyOn(resourceLedger, 'reserve').mockResolvedValue({
      id: '33333333-3333-4333-8333-333333333333',
      account_id: accountId,
      actor_id: actorId,
      amount: '25',
      status: 'reserved',
      reason: 'llm',
      idempotency_key: 'llm-reserve:attempt-1',
      expires_at: new Date(Date.now() + 60_000).toISOString(),
      settled_transaction_id: null,
      event_log_id: '44444444-4444-4444-8444-444444444444',
    });
    const settleSpy = jest.spyOn(resourceLedger, 'settleReservationUsage').mockResolvedValue({} as never);
    const releaseSpy = jest.spyOn(resourceLedger, 'releaseReservation').mockResolvedValue({} as never);

    const result = await new LlmProviderService().callJson({
      operation: 'budget success test',
      system: 'system',
      user: 'user',
      attemptId: 'attempt-1',
    });

    expect(result.usage.totalTokens).toBe(7);
    expect(reserveSpy).toHaveBeenCalledWith(expect.objectContaining({
      account_id: accountId,
      actor_id: actorId,
      idempotency_key: 'llm-reserve:attempt-1',
    }));
    expect(settleSpy).toHaveBeenCalledWith('33333333-3333-4333-8333-333333333333', actorId, 'llm-settle:attempt-1', 7);
    expect(releaseSpy).not.toHaveBeenCalled();
  });

  test('settles the full reservation when provider usage is missing', async () => {
    process.env.LLM_BUDGET_ENFORCEMENT = 'required';
    process.env.LLM_RESOURCE_ACTOR_ID = '11111111-1111-4111-8111-111111111111';
    process.env.LLM_RESOURCE_ACCOUNT_ID = '22222222-2222-4222-8222-222222222222';
    process.env.LLM_MAX_OUTPUT_TOKENS = '20';
    fetchSpy.mockResolvedValue(jsonResponseWithoutUsage('{"answer":"ok"}'));
    jest.spyOn(resourceLedger, 'reserve').mockResolvedValue({
      id: '33333333-3333-4333-8333-333333333333',
      account_id: process.env.LLM_RESOURCE_ACCOUNT_ID,
      actor_id: process.env.LLM_RESOURCE_ACTOR_ID,
      amount: '25',
      status: 'reserved',
      reason: 'llm',
      idempotency_key: 'llm-reserve:attempt-2',
      expires_at: new Date(Date.now() + 60_000).toISOString(),
      settled_transaction_id: null,
      event_log_id: '44444444-4444-4444-8444-444444444444',
    });
    const settleSpy = jest.spyOn(resourceLedger, 'settleReservationUsage').mockResolvedValue({} as never);

    await new LlmProviderService().callJson({
      operation: 'unknown usage test',
      system: 'system',
      user: 'user',
      attemptId: 'attempt-2',
    });

    expect(settleSpy).toHaveBeenCalledWith(
      '33333333-3333-4333-8333-333333333333',
      process.env.LLM_RESOURCE_ACTOR_ID,
      'llm-settle:attempt-2',
      expect.any(Number),
    );
    expect((settleSpy.mock.calls[0]?.[3] as number)).toBeGreaterThan(7);
  });

  test('releases durable budget when the provider call fails', async () => {
    process.env.LLM_BUDGET_ENFORCEMENT = 'required';
    process.env.LLM_RESOURCE_ACTOR_ID = '11111111-1111-4111-8111-111111111111';
    process.env.LLM_RESOURCE_ACCOUNT_ID = '22222222-2222-4222-8222-222222222222';
    process.env.LLM_MAX_RETRIES = '0';
    fetchSpy.mockResolvedValue(new Response('bad request', { status: 400 }));
    jest.spyOn(resourceLedger, 'reserve').mockResolvedValue({
      id: '33333333-3333-4333-8333-333333333333',
      account_id: process.env.LLM_RESOURCE_ACCOUNT_ID,
      actor_id: process.env.LLM_RESOURCE_ACTOR_ID,
      amount: '25',
      status: 'reserved',
      reason: 'llm',
      idempotency_key: 'llm-reserve:attempt-3',
      expires_at: new Date(Date.now() + 60_000).toISOString(),
      settled_transaction_id: null,
      event_log_id: '44444444-4444-4444-8444-444444444444',
    });
    const releaseSpy = jest.spyOn(resourceLedger, 'releaseReservation').mockResolvedValue({} as never);

    await expect(new LlmProviderService().callJson({
      operation: 'release on failure test',
      system: 'system',
      user: 'user',
      attemptId: 'attempt-3',
    })).rejects.toMatchObject({ code: 'non_retryable_http' });

    expect(releaseSpy).toHaveBeenCalledWith('33333333-3333-4333-8333-333333333333', process.env.LLM_RESOURCE_ACTOR_ID);
  });
});
