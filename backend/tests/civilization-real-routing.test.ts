import { CivilizationService } from '../src/services/civilization.service';
import { ragService } from '../src/services/rag.service';
import { symbolicService } from '../src/services/symbolic.service';
import { ensembleService } from '../src/services/ensemble.service';
import { db } from '../src/db/client';

describe('CivilizationService real service routing', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('uses real service adapters for primary solving and validation', async () => {
    jest.spyOn(ragService, 'augmentAnswer').mockResolvedValue({
      model_answer: '',
      model_confidence: 0.2,
      evidence_consensus: {
        answer: 'Paris',
        confidence: 0.9,
        sources: [{ source: 'Wikipedia', title: 'Paris', snippet: 'Paris is the capital of France.', relevance: 0.9, url: 'https://en.wikipedia.org/wiki/Paris' }],
        agreement_ratio: 1,
      },
      final_answer: 'Paris',
      final_confidence: 0.9,
      reasoning: 'Evidence supports Paris.',
    } as any);
    jest.spyOn(symbolicService, 'solve').mockResolvedValue({
      solved: false,
      answer: '',
      confidence: 0.1,
      method: 'not_symbolic',
      reasoning: 'Not a symbolic question',
    } as any);
    jest.spyOn(ensembleService, 'ensembleVote').mockResolvedValue({
      final_answer: 'Paris',
      confidence: 0.8,
      abstention: false,
      disagreement_level: 0,
      model_votes: [],
      reasoning: 'LLM ensemble agrees.',
    } as any);

    const service = new CivilizationService();
    const result = await service.solveWithCivilization('What is the capital of France?');

    expect(result.service).toBe('rag');
    expect(result.route_task_id).toEqual(expect.stringMatching(/^[0-9a-f-]{36}$/));
    expect(result.answer).toBe('Paris');
    expect(result.method).toBe('retrieval_augmented');
    expect(result.reasoning).toContain('Evidence supports Paris');

    const routeTask = await db.query(
      `SELECT agent_id, task_type, status, result, audit_log_id, action_attestation_id
         FROM workflow_tasks
        WHERE task_id = $1`,
      [result.route_task_id]
    );
    expect(routeTask.rows).toEqual([
      expect.objectContaining({
        agent_id: 'research-agent',
        task_type: 'record_observation',
        status: 'done',
        audit_log_id: expect.stringMatching(/^[0-9a-f-]{36}$/),
        action_attestation_id: expect.stringMatching(/^[0-9a-f-]{36}$/),
      }),
    ]);
    expect(routeTask.rows[0].result).toEqual(expect.objectContaining({
      kind: 'observation_recorded',
      executed_by: 'durable-execution-service',
    }));
  });
});
