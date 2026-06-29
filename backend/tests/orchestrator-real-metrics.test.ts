import { OrchestratorService } from '../src/services/orchestrator.service';

describe('OrchestratorService evidence-derived metrics', () => {
  it('computes evidence and trust inputs from retrieved source metadata', () => {
    const service = new OrchestratorService();
    const sources = [
      {
        source: 'Wikipedia',
        relevance: 0.9,
        snippet: 'Paris is the capital of France.',
        url: 'https://en.wikipedia.org/wiki/Paris',
      },
      {
        source: 'ArXiv',
        relevance: 0.8,
        snippet: 'Evidence-grounded systems cite sources.',
        url: 'https://arxiv.org/abs/1234.5678',
      },
    ];

    expect(service.computeEvidenceQuality(sources)).toBeGreaterThan(0.8);
    expect(service.computeSourceReliability(sources)).toBeGreaterThan(0.8);
    expect(service.estimateCalibrationError(0.7, 0.55)).toBeCloseTo(0.15);
    expect(service.computeAgreement('Paris', 'Paris is the capital of France', 0.75)).toBeGreaterThan(0.8);
    expect(service.computeExplainability(['Symbolic reasoning', 'Evidence supports model answer.'])).toBeGreaterThan(0.6);
  });

  it('degrades metrics when no retrieved evidence exists', () => {
    const service = new OrchestratorService();

    expect(service.computeEvidenceQuality([])).toBe(0.2);
    expect(service.computeSourceReliability([])).toBe(0.2);
    expect(service.computeAgreement('model answer', '', 0)).toBe(0.5);
    expect(service.computeExplainability([])).toBe(0.3);
  });
});
