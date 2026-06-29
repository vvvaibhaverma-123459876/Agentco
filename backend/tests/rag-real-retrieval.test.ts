import { RAGService } from '../src/services/rag.service';

describe('RAGService real retrieval contract', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('uses retrieved Wikipedia and arXiv evidence instead of canned knowledge', async () => {
    const service = new RAGService();
    const fetchMock = jest.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          pages: [
            {
              title: 'Paris',
              key: 'Paris',
              excerpt: 'Paris is the <span>capital</span> and most populous city of France.',
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        text: async () => `
          <feed>
            <entry>
              <id>https://arxiv.org/abs/1234.5678</id>
              <title>Evidence Grounded AI Systems</title>
              <summary>Evidence grounded systems cite external sources before claims.</summary>
            </entry>
          </feed>
        `,
      });
    global.fetch = fetchMock as unknown as typeof fetch;

    const result = await service.augmentAnswer('capital of France', 'Paris', 0.6);

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(result.evidence_consensus.sources.map((source) => source.source).sort()).toEqual(['ArXiv', 'Wikipedia']);
    expect(result.evidence_consensus.sources.some((source) => source.snippet.includes('Paris is the capital'))).toBe(true);
    expect(result.evidence_consensus.sources.some((source) => source.url === 'https://arxiv.org/abs/1234.5678')).toBe(true);
  });

  it('falls back transparently without synthetic evidence when retrieval fails', async () => {
    const service = new RAGService();
    global.fetch = jest.fn().mockRejectedValue(new Error('network unavailable')) as unknown as typeof fetch;

    const result = await service.augmentAnswer('unknown production topic', 'model answer', 0.55);

    expect(result.final_answer).toBe('model answer');
    expect(result.evidence_consensus.sources).toHaveLength(0);
    expect(result.evidence_consensus.confidence).toBe(0);
    expect(result.reasoning).toContain('Uncertain');
  });
});
