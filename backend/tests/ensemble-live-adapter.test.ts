import { EnsembleService } from '../src/services/ensemble.service';

describe('EnsembleService OpenAI-compatible adapter', () => {
  const originalFetch = global.fetch;
  const originalEnv = { ...process.env };

  afterEach(() => {
    global.fetch = originalFetch;
    process.env = { ...originalEnv };
  });

  it('calls the configured LLM endpoint for each ensemble persona', async () => {
    process.env.LLM_API_KEY = 'test-key';
    process.env.LLM_BASE_URL = 'https://llm.example.test/v1';
    process.env.LLM_MODEL_DEFAULT = 'test-model';
    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        choices: [
          {
            message: {
              content: JSON.stringify({
                answer: 'Paris',
                confidence: 0.82,
                reasoning: 'The question asks for the capital of France.',
              }),
            },
          },
        ],
      }),
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    const service = new EnsembleService();
    const result = await service.ensembleVote('What is the capital of France?');

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[0][0]).toBe('https://llm.example.test/v1/chat/completions');
    expect(result.final_answer).toBe('paris');
    expect(result.model_votes).toHaveLength(3);
    expect(result.model_votes.every((vote) => vote.reasoning.length > 0)).toBe(true);
  });

  it('fails closed when no LLM key is configured', async () => {
    delete process.env.LLM_API_KEY;
    delete process.env.OPENAI_API_KEY;

    const service = new EnsembleService();

    await expect(service.queryModels('What is the capital of France?')).rejects.toThrow(/LLM_API_KEY/);
  });
});
