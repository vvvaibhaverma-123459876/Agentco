import { MultiAgentEnsembleService } from '../src/services/multi-agent-ensemble.service';

describe('MultiAgentEnsembleService LLM-backed experts', () => {
  const originalFetch = global.fetch;
  const originalEnv = { ...process.env };

  afterEach(() => {
    global.fetch = originalFetch;
    process.env = { ...originalEnv };
  });

  it('calls configured LLM endpoint for selected experts', async () => {
    process.env.LLM_API_KEY = 'test-key';
    process.env.LLM_BASE_URL = 'https://llm.example.test/v1';
    process.env.LLM_MODEL_DEFAULT = 'test-model';
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        choices: [
          {
            message: {
              content: JSON.stringify({
                answer: 'A bounded answer from an expert.',
                confidence: 0.84,
                reasoning_chain: ['Identify domain constraints', 'Cite available evidence', 'State calibrated answer'],
              }),
            },
          },
        ],
      }),
    }) as unknown as typeof fetch;

    const service = new MultiAgentEnsembleService();
    const result = await service.solveComplexQuestion(
      'Explain the mathematical and physical constraints in quantum measurement for a complex synthesis task.',
      'baseline answer',
      0.5
    );

    expect(global.fetch).toHaveBeenCalled();
    expect(result.contributing_experts.length).toBeGreaterThan(0);
    expect(result.reasoning_synthesis.join(' ')).toContain('calibrated answer');
  });

  it('fails closed for complex expert routing when no LLM key is configured', async () => {
    delete process.env.LLM_API_KEY;
    delete process.env.OPENAI_API_KEY;

    const service = new MultiAgentEnsembleService();

    await expect(
      service.solveComplexQuestion(
        'Explain the mathematical and physical constraints in quantum measurement for a complex synthesis task.',
        'baseline answer',
        0.5
      )
    ).rejects.toThrow(/LLM_API_KEY/);
  });
});
