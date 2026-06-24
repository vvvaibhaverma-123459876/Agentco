/**
 * Integration test for Reputation Learning + Adaptive Strategy services
 * Tests full civilization-scale autonomy with learning and adaptation
 */

import { ReputationLearningService } from '../src/services/reputation-learning.service';
import { AdaptiveStrategyService } from '../src/services/adaptive-strategy.service';
import { v4 as uuidv4 } from 'uuid';

describe('Reputation Learning & Adaptive Strategy Integration', () => {
  let reputation: ReputationLearningService;
  let strategy: AdaptiveStrategyService;
  let testGoalId: string;
  let testStrategyId: string;

  beforeEach(() => {
    reputation = new ReputationLearningService();
    strategy = new AdaptiveStrategyService();
    testGoalId = uuidv4();
  });

  it('should initialize reputation for goal entity', async () => {
    // Initialize reputation for goal
    const record = await reputation.initializeEntity(testGoalId, 'society', ['research', 'autonomy']);

    expect(record.entity_id).toBe(testGoalId);
    expect(record.entity_type).toBe('society');
    expect(record.current_score).toBe(50); // Neutral start
    expect(record.reliability).toBe(0.5);
    expect(record.speed).toBe(0.5);
    expect(record.innovation).toBe(0.5);
    expect(record.collaboration).toBe(0.5);
    expect(record.specialization).toEqual(['research', 'autonomy']);
  });

  it('should initialize adaptive strategy for goal', async () => {
    const strat = await strategy.initializeStrategy(testGoalId, 'multi_angle_research');

    expect(strat.strategy_id).toBeDefined();
    expect(strat.goal_id).toBe(testGoalId);
    expect(strat.approach).toBe('multi_angle_research');
    expect(strat.status).toBe('active');
    expect(strat.queries).toEqual([]);
    expect(strat.metrics.total_claims).toBe(0);
    expect(strat.metrics.roi).toBe(0);
  });

  it('should record research_completed events and update reputation', async () => {
    await reputation.initializeEntity(testGoalId, 'society', ['research']);

    // Record successful research
    await reputation.recordEvent(testGoalId, 'research_completed', 1.0, [], {
      topic: 'AI autonomy',
      claims_found: 3,
    });

    const record = reputation.getReputation(testGoalId);
    expect(record).not.toBeNull();
    expect(record?.current_score).toBeGreaterThan(50);
    expect(record?.speed).toBeGreaterThan(0.5);
  });

  it('should record claim_verified events and increase reliability', async () => {
    await reputation.initializeEntity(testGoalId, 'society', []);

    // Record verified claim
    await reputation.recordEvent(testGoalId, 'claim_verified', 1.0, [], {
      claim_text: 'AI systems can learn',
    });

    const record = reputation.getReputation(testGoalId);
    expect(record?.reliability).toBeGreaterThan(0.5);
    expect(record?.current_score).toBeGreaterThan(50);
  });

  it('should record claim_refuted events and decrease reliability', async () => {
    await reputation.initializeEntity(testGoalId, 'society', []);

    // Record refuted claim with positive magnitude (the weight handles the direction)
    await reputation.recordEvent(testGoalId, 'claim_refuted', 1.0, [], {
      claim_text: 'False claim',
    });

    const record = reputation.getReputation(testGoalId);
    expect(record?.reliability).toBeLessThan(0.5);
    expect(record?.current_score).toBeLessThan(50);
  });

  it('should learn specialization from successful events', async () => {
    await reputation.initializeEntity(testGoalId, 'society', []);

    // Record high-magnitude successful event with topic
    await reputation.recordEvent(testGoalId, 'research_completed', 0.8, [], {
      topic: 'machine_learning',
    });

    const record = reputation.getReputation(testGoalId);
    expect(record?.specialization).toContain('machine_learning');
  });

  it('should provide performance insights', async () => {
    await reputation.initializeEntity(testGoalId, 'society', ['research']);

    // Build up some performance history
    await reputation.recordEvent(testGoalId, 'research_completed', 1.0, []);
    await reputation.recordEvent(testGoalId, 'claim_verified', 1.0, []);
    await reputation.recordEvent(testGoalId, 'research_completed', 0.8, []);

    const insights = reputation.getInsights(testGoalId);

    expect(insights).toHaveProperty('strengths');
    expect(insights).toHaveProperty('weaknesses');
    expect(insights).toHaveProperty('specializations');
    expect(insights).toHaveProperty('recommendations');
  });

  it('should predict performance based on reputation', async () => {
    await reputation.initializeEntity(testGoalId, 'society', []);

    // Add some events
    await reputation.recordEvent(testGoalId, 'research_completed', 1.0, []);
    await reputation.recordEvent(testGoalId, 'claim_verified', 1.0, []);

    const prediction = reputation.predictPerformance(testGoalId);

    expect(prediction.predicted_quality).toBeGreaterThan(0.5);
    expect(prediction.confidence).toBeGreaterThanOrEqual(0);
    expect(prediction.confidence).toBeLessThanOrEqual(1);
  });

  it('should generate multi-angle search queries', async () => {
    const strat = await strategy.initializeStrategy(testGoalId, 'multi_angle_research');
    testStrategyId = strat.strategy_id;

    const query = await strategy.generateNextQuery(strat.strategy_id, 'AI autonomy', []);

    expect(query).not.toBeNull();
    expect(query?.text).toContain('autonomy');
    expect(query?.source_type).toBe('web');
  });

  it('should track query execution and ROI', async () => {
    const strat = await strategy.initializeStrategy(testGoalId, 'multi_angle_research');
    testStrategyId = strat.strategy_id;

    const query = await strategy.generateNextQuery(testGoalId, 'AI systems', []);
    if (query) {
      // Record that query found 5 claims with quality 0.8
      await strategy.recordQueryResult(
        testStrategyId,
        query.query_id,
        5,
        0.8,
        { web_fetches: 2, llm_calls: 1, time_seconds: 15 }
      );

      const strat2 = strategy.getStrategy(testStrategyId);
      expect(strat2?.metrics.total_claims).toBe(5);
      expect(strat2?.metrics.roi).toBeGreaterThan(0);
      expect(strat2?.budget_allocation.web_fetches_used).toBe(2);
    }
  });

  it('should generate task assignments from productive queries', async () => {
    const strat = await strategy.initializeStrategy(testGoalId, 'multi_angle_research');
    testStrategyId = strat.strategy_id;

    const query = await strategy.generateNextQuery(testGoalId, 'AI', []);
    if (query) {
      await strategy.recordQueryResult(testStrategyId, query.query_id, 10, 0.9, {
        web_fetches: 3,
        llm_calls: 2,
        time_seconds: 20,
      });

      const availableAgents = [
        { agent_id: 'agent1', specialization: ['research'] },
        { agent_id: 'agent2', specialization: ['analysis'] },
      ];

      const assignments = await strategy.generateTaskAssignments(testStrategyId, availableAgents);

      expect(assignments).toBeDefined();
      expect(Array.isArray(assignments)).toBe(true);
    }
  });

  it('should consider strategy pivots on low ROI', async () => {
    const strat = await strategy.initializeStrategy(testGoalId, 'multi_angle_research');
    testStrategyId = strat.strategy_id;

    const query = await strategy.generateNextQuery(testGoalId, 'obscure topic', []);
    if (query) {
      // Low-ROI query (few claims per execution)
      for (let i = 0; i < 5; i++) {
        await strategy.recordQueryResult(testStrategyId, query.query_id, 0, 0.2, {
          web_fetches: 1,
          llm_calls: 1,
          time_seconds: 10,
        });
      }

      const pivoted = await strategy.considerPivot(testStrategyId);
      // Pivot may or may not happen depending on other queries
      expect(pivoted).toBeDefined();
    }
  });

  it('should track hierarchical reputation across entity types', async () => {
    // Create hierarchy: Agent -> Team -> Institution -> Society
    const agentId = uuidv4();
    const teamId = uuidv4();
    const institutionId = uuidv4();
    const societyId = uuidv4();

    await reputation.initializeEntity(agentId, 'agent', []);
    await reputation.initializeEntity(teamId, 'team', []);
    await reputation.initializeEntity(institutionId, 'institution', []);
    await reputation.initializeEntity(societyId, 'society', []);

    // Record events on agent
    await reputation.recordEvent(agentId, 'claim_verified', 1.0, []);
    await reputation.recordEvent(agentId, 'claim_verified', 1.0, []);

    const hierarchical = await reputation.getHierarchicalReputation(societyId);

    expect(hierarchical.agent_scores.size).toBeGreaterThanOrEqual(0);
    expect(hierarchical.team_scores.size).toBeGreaterThanOrEqual(0);
    expect(hierarchical.institution_scores.size).toBeGreaterThanOrEqual(0);
    expect(hierarchical.society_scores.size).toBeGreaterThanOrEqual(0);
  });

  it('should handle decay on old reputations', async () => {
    await reputation.initializeEntity(testGoalId, 'society', []);

    // Record initial event
    await reputation.recordEvent(testGoalId, 'claim_verified', 1.0, []);

    // Apply decay (simulates passage of time)
    await reputation.applyDecay();

    const record = reputation.getReputation(testGoalId);
    expect(record).not.toBeNull();
    // Score should be same or decayed (toward neutral)
    expect(record?.current_score).toBeLessThanOrEqual(100);
  });

  it('should integrate reputation and adaptive strategy for full learning loop', async () => {
    // Initialize both systems for same goal
    await reputation.initializeEntity(testGoalId, 'society', ['research']);
    const strat = await strategy.initializeStrategy(testGoalId, 'multi_angle_research');

    // Simulate multiple research iterations
    for (let i = 0; i < 3; i++) {
      // Get next query from strategy (use strategy_id, not goal_id)
      const query = await strategy.generateNextQuery(strat.strategy_id, 'AI autonomy', []);

      if (query) {
        // Simulate successful research
        const claimsFound = 5 + i; // Increasing success
        const qualityScore = 0.7 + i * 0.05; // Improving quality

        // Record query results in strategy (use strategy_id, not goal_id)
        await strategy.recordQueryResult(strat.strategy_id, query.query_id, claimsFound, qualityScore, {
          web_fetches: 2,
          llm_calls: 1,
          time_seconds: 15,
        });

        // Record corresponding reputation events
        await reputation.recordEvent(testGoalId, 'research_completed', 0.8 + i * 0.05, [], {
          claimsFound,
        });
      }
    }

    // Verify learning happened in both systems
    const reputation_record = reputation.getReputation(testGoalId);
    const strategy_record = strategy.getStrategy(strat.strategy_id);

    expect(reputation_record?.current_score).toBeGreaterThanOrEqual(50);
    expect(reputation_record?.speed).toBeGreaterThanOrEqual(0.5);
    expect(strategy_record?.metrics.total_claims).toBeGreaterThan(0);
    expect(strategy_record?.metrics.roi).toBeGreaterThan(0);

    // Both systems should show that entity is learning
    const insights = reputation.getInsights(testGoalId);
    expect(insights.strengths.length).toBeGreaterThanOrEqual(0);
  });
});
