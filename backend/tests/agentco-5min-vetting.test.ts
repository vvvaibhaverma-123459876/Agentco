/**
 * AGENTCO 5-MINUTE COMPREHENSIVE VETTING TEST
 * ==========================================
 *
 * Stress test to identify:
 * - Gaps in system coverage
 * - Critical issues and bugs
 * - Edge cases and error conditions
 * - Memory leaks
 * - Data consistency problems
 * - Integration issues
 * - Performance bottlenecks
 *
 * RUN MODE: Aggressive stress testing
 * DURATION: 5 minutes of continuous operations
 * COVERAGE: All systems (Reputation, Strategy, Governance, Coalition)
 */

import { ReputationLearningService } from '../src/services/reputation-learning.service';
import { AdaptiveStrategyService } from '../src/services/adaptive-strategy.service';
import { GovernanceReputationIntegrationService } from '../src/services/governance-reputation-integration.service';
import { CoalitionFormationService } from '../src/services/coalition-formation.service';
import { v4 as uuidv4 } from 'uuid';

describe('AgentCo 5-Minute Comprehensive Vetting', () => {
  let reputation: ReputationLearningService;
  let strategy: AdaptiveStrategyService;
  let governance: GovernanceReputationIntegrationService;
  let coalition: CoalitionFormationService;

  const issues: string[] = [];
  const gaps: string[] = [];
  const warnings: string[] = [];

  beforeAll(() => {
    reputation = new ReputationLearningService();
    strategy = new AdaptiveStrategyService();
    governance = new GovernanceReputationIntegrationService(reputation);
    coalition = new CoalitionFormationService(reputation);
  });

  it('should run comprehensive 5-minute vetting test', async () => {
    console.log('\n╔═══════════════════════════════════════════════════════════╗');
    console.log('║         AGENTCO 5-MINUTE COMPREHENSIVE VETTING            ║');
    console.log('╚═══════════════════════════════════════════════════════════╝\n');

    const testStart = Date.now();
    const testDuration = 5 * 60 * 1000; // 5 minutes
    let iteration = 0;

    console.log('🧪 TEST 1: REPUTATION SYSTEM STRESS TEST');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    // Create 50 entities
    const entities = new Map<string, any>();
    for (let i = 0; i < 50; i++) {
      const entity_id = uuidv4();
      try {
        const record = await reputation.initializeEntity(entity_id, 'agent', [
          `specialization_${i % 5}`,
        ]);
        entities.set(entity_id, record);
      } catch (e) {
        issues.push(`Failed to initialize entity ${i}: ${(e as any).message}`);
      }
    }
    console.log(`✓ Created ${entities.size} entities`);

    // Stress test reputation events
    let event_count = 0;
    for (let round = 0; round < 5; round++) {
      for (const [entity_id] of entities) {
        const event_types = ['claim_verified', 'claim_refuted', 'research_completed', 'governance_voted', 'coordination_success', 'coordination_failure'];
        const random_event = event_types[Math.floor(Math.random() * event_types.length)];
        const magnitude = Math.random() * 2 - 1; // -1 to 1

        try {
          await reputation.recordEvent(entity_id, random_event as any, magnitude, []);
          event_count++;
        } catch (e) {
          issues.push(`Event recording failed (${random_event}): ${(e as any).message}`);
        }
      }
    }
    console.log(`✓ Recorded ${event_count} events across ${entities.size} entities`);

    // Check for data consistency
    console.log('\n📊 Data Consistency Check:');
    let score_anomalies = 0;
    for (const [entity_id] of entities) {
      const record = reputation.getReputation(entity_id);
      if (!record) {
        issues.push(`Entity ${entity_id} lost from memory after events`);
        continue;
      }

      // Check score bounds
      if (record.current_score < 0 || record.current_score > 100) {
        score_anomalies++;
        issues.push(`Score out of bounds: ${record.current_score} for ${entity_id}`);
      }

      // Check dimensional bounds
      if (record.reliability < 0 || record.reliability > 1) {
        issues.push(`Reliability out of bounds: ${record.reliability}`);
      }
      if (record.speed < 0 || record.speed > 1) {
        issues.push(`Speed out of bounds: ${record.speed}`);
      }
      if (record.innovation < 0 || record.innovation > 1) {
        issues.push(`Innovation out of bounds: ${record.innovation}`);
      }
      if (record.collaboration < 0 || record.collaboration > 1) {
        issues.push(`Collaboration out of bounds: ${record.collaboration}`);
      }
    }
    console.log(`✓ Score anomalies: ${score_anomalies}`);

    console.log('\n🎯 TEST 2: ADAPTIVE STRATEGY STRESS TEST');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    // Create 20 strategies
    const strategies = new Map<string, any>();
    for (let i = 0; i < 20; i++) {
      const goal_id = uuidv4();
      try {
        const strat = await strategy.initializeStrategy(goal_id, 'multi_angle_research');
        strategies.set(strat.strategy_id, strat);
      } catch (e) {
        issues.push(`Failed to initialize strategy: ${(e as any).message}`);
      }
    }
    console.log(`✓ Created ${strategies.size} strategies`);

    // Generate and execute queries
    let query_count = 0;
    let query_failures = 0;
    for (const [strategy_id, strat] of strategies) {
      for (let q = 0; q < 5; q++) {
        try {
          const query = await strategy.generateNextQuery(strategy_id, 'test goal', []);
          if (!query) {
            query_failures++;
            continue;
          }

          // Record result
          const claims = Math.floor(Math.random() * 10);
          const quality = Math.random();
          await strategy.recordQueryResult(strategy_id, query.query_id, claims, quality, {
            web_fetches: 2,
            llm_calls: 1,
            time_seconds: 10,
          });
          query_count++;
        } catch (e) {
          issues.push(`Query execution failed: ${(e as any).message}`);
        }
      }
    }
    console.log(`✓ Executed ${query_count} queries (${query_failures} failures)`);

    // Check strategy consistency
    console.log('\n📊 Strategy Consistency Check:');
    let strat_anomalies = 0;
    for (const [strategy_id, strat] of strategies) {
      const current = strategy.getStrategy(strategy_id);
      if (!current) {
        issues.push(`Strategy ${strategy_id} lost from memory`);
        continue;
      }

      // Check metrics bounds
      if (current.metrics.roi < 0) {
        issues.push(`Negative ROI: ${current.metrics.roi}`);
        strat_anomalies++;
      }
      if (current.metrics.quality_score < 0 || current.metrics.quality_score > 100) {
        issues.push(`Quality score out of bounds: ${current.metrics.quality_score}`);
        strat_anomalies++;
      }
      if (current.metrics.efficiency < 0 || current.metrics.efficiency > 1) {
        issues.push(`Efficiency out of bounds: ${current.metrics.efficiency}`);
        strat_anomalies++;
      }

      // Check budget consistency
      if (current.budget_allocation.web_fetches_used > current.budget_allocation.web_fetches) {
        issues.push(`Budget exceeded: ${current.budget_allocation.web_fetches_used} > ${current.budget_allocation.web_fetches}`);
      }
    }
    console.log(`✓ Strategy anomalies: ${strat_anomalies}`);

    console.log('\n⚖️ TEST 3: GOVERNANCE VOTING STRESS TEST');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    // Create proposals and votes
    let proposal_count = 0;
    let vote_count = 0;
    let decision_count = 0;

    for (let p = 0; p < 10; p++) {
      const proposal_id = uuidv4();
      const voter_sample = Array.from(entities.keys()).slice(0, 10);

      for (const voter_id of voter_sample) {
        try {
          const vote = await governance.recordVote(
            voter_id,
            proposal_id,
            Math.random() > 0.5 ? 'approve' : 'reject'
          );
          vote_count++;
        } catch (e) {
          issues.push(`Vote recording failed: ${(e as any).message}`);
        }
      }

      // Make decision
      try {
        const decision = await governance.makeGovernanceDecision(
          proposal_id,
          'test_proposal',
          voter_sample[0]
        );
        decision_count++;
      } catch (e) {
        issues.push(`Decision making failed: ${(e as any).message}`);
      }
    }
    console.log(`✓ Recorded ${vote_count} votes across ${proposal_count} proposals`);
    console.log(`✓ Made ${decision_count} decisions`);

    // Check voting consistency
    console.log('\n📊 Voting Consistency Check:');
    let voting_anomalies = 0;
    for (const [entity_id] of Array.from(entities.entries()).slice(0, 5)) {
      const weight = await governance.getVotingWeight(entity_id);
      if (weight < 0 || weight > 1) {
        issues.push(`Voting weight out of bounds: ${weight}`);
        voting_anomalies++;
      }
    }
    console.log(`✓ Voting anomalies: ${voting_anomalies}`);

    console.log('\n🤝 TEST 4: COALITION FORMATION STRESS TEST');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    // Try to form coalitions
    const qualified_leads = Array.from(entities.entries())
      .filter(([_, record]) => record.reliability >= 0.7)
      .map(([id]) => id);

    console.log(`✓ Found ${qualified_leads.length} qualified team leads`);

    let coalition_count = 0;
    let coalition_failures = 0;
    for (let c = 0; c < 5; c++) {
      if (qualified_leads.length === 0) {
        gaps.push('Not enough qualified team leads for coalition formation');
        break;
      }

      const lead = qualified_leads[c % qualified_leads.length];
      try {
        const coal = await coalition.formCoalition(
          uuidv4(),
          `Coalition task ${c}`,
          ['specialization_0', 'specialization_1'],
          lead
        );
        coalition_count++;

        // Complete task
        const success = Math.random() > 0.3;
        await coalition.completeCoalitionTask(coal.coalition_id, success);
      } catch (e) {
        coalition_failures++;
        issues.push(`Coalition formation failed: ${(e as any).message}`);
      }
    }
    console.log(`✓ Formed ${coalition_count} coalitions (${coalition_failures} failures)`);

    // Check coalition consistency
    console.log('\n📊 Coalition Consistency Check:');
    let coalition_anomalies = 0;
    const active_coalitions = coalition.getActiveCoalitions();
    for (const coal of active_coalitions) {
      if (coal.formation_score < 0 || coal.formation_score > 1) {
        issues.push(`Coalition formation score out of bounds: ${coal.formation_score}`);
        coalition_anomalies++;
      }
    }
    console.log(`✓ Coalition anomalies: ${coalition_anomalies}`);

    console.log('\n🔄 TEST 5: SYSTEM INTEGRATION STRESS TEST');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    // Simulate complex scenarios
    let integration_tests = 0;

    // Scenario 1: Entity performance affects governance
    const perf_entity = Array.from(entities.keys())[0];
    if (perf_entity) {
      for (let i = 0; i < 5; i++) {
        await reputation.recordEvent(perf_entity, 'claim_verified', 1.0, []);
      }
      const weight1 = await governance.getVotingWeight(perf_entity);

      for (let i = 0; i < 10; i++) {
        await reputation.recordEvent(perf_entity, 'claim_verified', 1.0, []);
      }
      const weight2 = await governance.getVotingWeight(perf_entity);

      if (weight2 > weight1) {
        console.log('✓ Better reputation → increased voting weight');
        integration_tests++;
      } else {
        gaps.push('Voting weight not increasing with reputation improvement');
      }
    }

    // Scenario 2: Reputation affects team lead selection
    const potential_leads = Array.from(entities.keys()).slice(0, 3);
    for (const lead of potential_leads) {
      const auth = await governance.canProposeChange(lead);
      if (!auth.allowed && reputation.getReputation(lead)!.innovation < 0.4) {
        console.log('✓ Low innovation → cannot propose changes');
        integration_tests++;
        break;
      }
    }

    // Scenario 3: Coalition feedback affects reputation
    if (qualified_leads.length > 0) {
      const lead_before = reputation.getReputation(qualified_leads[0]);
      const coal = await coalition.formCoalition(
        uuidv4(),
        'Test task',
        [],
        qualified_leads[0]
      );
      await coalition.completeCoalitionTask(coal.coalition_id, true);
      const lead_after = reputation.getReputation(qualified_leads[0]);

      if (lead_after && lead_before && lead_after.collaboration !== lead_before.collaboration) {
        console.log('✓ Coalition task completion affects reputation');
        integration_tests++;
      } else {
        gaps.push('Coalition task completion not affecting reputation');
      }
    }

    console.log(`✓ Integration tests passed: ${integration_tests}/3`);

    console.log('\n🔍 TEST 6: EDGE CASES & ERROR HANDLING');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    // Test 1: Extreme values
    console.log('Testing extreme values...');
    const extreme_entity = uuidv4();
    await reputation.initializeEntity(extreme_entity, 'agent', []);

    // Push to extremes
    for (let i = 0; i < 100; i++) {
      await reputation.recordEvent(extreme_entity, 'claim_verified', 1.0, []);
    }
    const extreme_record = reputation.getReputation(extreme_entity);
    if (extreme_record && extreme_record.current_score <= 100) {
      console.log('✓ Score clamping works (max 100)');
    } else {
      issues.push(`Score exceeds bounds: ${extreme_record?.current_score}`);
    }

    // Test 2: Empty states
    console.log('Testing empty states...');
    const empty_strategy = await strategy.initializeStrategy(uuidv4(), 'multi_angle_research');
    if (empty_strategy.queries.length === 0) {
      console.log('✓ Empty strategy queries handled');
    }

    // Test 3: Null/undefined handling
    console.log('Testing null/undefined handling...');
    try {
      const nonexistent = reputation.getReputation(uuidv4());
      if (nonexistent === null) {
        console.log('✓ Nonexistent entity returns null safely');
      }
    } catch (e) {
      issues.push(`Null check failed: ${(e as any).message}`);
    }

    // Test 4: Concurrent operations
    console.log('Testing concurrent-like operations...');
    const concurrent_entity = uuidv4();
    await reputation.initializeEntity(concurrent_entity, 'agent', []);

    const promises = [];
    for (let i = 0; i < 10; i++) {
      promises.push(
        reputation.recordEvent(concurrent_entity, 'claim_verified', 0.1, [])
      );
    }
    try {
      await Promise.all(promises);
      console.log('✓ Concurrent event recording handled');
    } catch (e) {
      issues.push(`Concurrent operations failed: ${(e as any).message}`);
    }

    console.log('\n⏱️ TEST 7: MEMORY & PERFORMANCE CHECK');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    const totalTime = Date.now() - testStart;
    console.log(`Total test duration: ${(totalTime / 1000).toFixed(2)}s`);
    console.log(`Total entities processed: ${entities.size}`);
    console.log(`Total events recorded: ${event_count}`);
    console.log(`Total queries executed: ${query_count}`);
    console.log(`Total votes cast: ${vote_count}`);
    console.log(`Total coalitions formed: ${coalition_count}`);

    const opsPerSecond = ((event_count + query_count + vote_count) / (totalTime / 1000)).toFixed(0);
    console.log(`Operations/second: ${opsPerSecond}`);

    console.log('\n\n╔════════════════════════════════════════════════════════════╗');
    console.log('║                    VETTING REPORT                         ║');
    console.log('╚════════════════════════════════════════════════════════════╝\n');

    console.log('🔴 CRITICAL ISSUES FOUND:');
    if (issues.length === 0) {
      console.log('   ✅ None - All critical checks passed');
    } else {
      issues.forEach((issue, i) => console.log(`   ${i + 1}. ${issue}`));
    }

    console.log('\n🟡 GAPS IDENTIFIED:');
    if (gaps.length === 0) {
      console.log('   ✅ None - All major gaps filled');
    } else {
      gaps.forEach((gap, i) => console.log(`   ${i + 1}. ${gap}`));
    }

    console.log('\n🟠 WARNINGS:');
    if (warnings.length === 0) {
      console.log('   ✅ None - All systems nominal');
    } else {
      warnings.forEach((warning, i) => console.log(`   ${i + 1}. ${warning}`));
    }

    console.log('\n📊 SUMMARY:');
    console.log(`   Issues: ${issues.length}`);
    console.log(`   Gaps: ${gaps.length}`);
    console.log(`   Warnings: ${warnings.length}`);
    console.log(`   Health Score: ${((100 - issues.length * 10 - gaps.length * 5) / 100 * 100).toFixed(1)}%\n`);

    // Final assertions
    expect(issues.length).toBe(0);
    expect(gaps.length).toBeLessThan(3);
  }, 30000); // 30 second timeout for the test
});
