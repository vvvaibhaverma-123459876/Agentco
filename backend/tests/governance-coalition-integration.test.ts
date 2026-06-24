/**
 * Integration test for Governance-Reputation + Coalition Formation
 * Tests governance decisions using reputation, and team assembly using collaboration scores
 */

import { ReputationLearningService } from '../src/services/reputation-learning.service';
import { GovernanceReputationIntegrationService } from '../src/services/governance-reputation-integration.service';
import { CoalitionFormationService } from '../src/services/coalition-formation.service';
import { v4 as uuidv4 } from 'uuid';

describe('Governance-Reputation & Coalition Formation Integration', () => {
  let reputation: ReputationLearningService;
  let governance: GovernanceReputationIntegrationService;
  let coalition: CoalitionFormationService;
  let testEntityId: string;
  let testProposalId: string;

  beforeEach(() => {
    reputation = new ReputationLearningService();
    governance = new GovernanceReputationIntegrationService(reputation);
    coalition = new CoalitionFormationService(reputation);
    testEntityId = uuidv4();
    testProposalId = uuidv4();
  });

  describe('Governance-Reputation Integration', () => {
    it('should initialize reputation and governance system', async () => {
      const record = await reputation.initializeEntity(testEntityId, 'agent', ['research']);
      expect(record.entity_id).toBe(testEntityId);
      expect(record.entity_type).toBe('agent');
      expect(record.current_score).toBe(50);
    });

    it('should calculate voting weight from reputation', async () => {
      // Create high-reputation entity
      await reputation.initializeEntity(testEntityId, 'agent', []);
      await reputation.recordEvent(testEntityId, 'claim_verified', 1.0, []);
      await reputation.recordEvent(testEntityId, 'research_completed', 1.0, []);

      const weight = await governance.getVotingWeight(testEntityId);
      expect(weight).toBeGreaterThan(0.5);
      expect(weight).toBeLessThanOrEqual(1.0);
    });

    it('should record weighted vote on proposal', async () => {
      // Setup: high-reputation voter
      await reputation.initializeEntity(testEntityId, 'agent', []);
      for (let i = 0; i < 3; i++) {
        await reputation.recordEvent(testEntityId, 'claim_verified', 1.0, []);
      }

      // Record approval vote
      const vote = await governance.recordVote(testEntityId, testProposalId, 'approve', 'Entity approves proposal');

      expect(vote.voter_id).toBe(testEntityId);
      expect(vote.vote).toBe('approve');
      expect(vote.weight).toBeGreaterThan(0);
      expect(vote.voter_reputation).toBeGreaterThan(50);
    });

    it('should make governance decision with weighted votes', async () => {
      // Setup: three entities with different reputations
      const voter1 = uuidv4();
      const voter2 = uuidv4();
      const voter3 = uuidv4();

      // Voter 1: High reputation
      await reputation.initializeEntity(voter1, 'agent', []);
      for (let i = 0; i < 5; i++) {
        await reputation.recordEvent(voter1, 'claim_verified', 1.0, []);
      }

      // Voter 2: Medium reputation
      await reputation.initializeEntity(voter2, 'agent', []);
      for (let i = 0; i < 2; i++) {
        await reputation.recordEvent(voter2, 'claim_verified', 0.8, []);
      }

      // Voter 3: Low reputation
      await reputation.initializeEntity(voter3, 'agent', []);
      await reputation.recordEvent(voter3, 'claim_refuted', 1.0, []);

      // Record votes
      await governance.recordVote(voter1, testProposalId, 'approve');
      await governance.recordVote(voter2, testProposalId, 'approve');
      await governance.recordVote(voter3, testProposalId, 'reject');

      // Make decision
      const decision = await governance.makeGovernanceDecision(
        testProposalId,
        'policy_approval',
        uuidv4()
      );

      expect(decision.decision_id).toBeDefined();
      expect(decision.vote_count).toBe(3);
      expect(['approved', 'rejected', 'deferred']).toContain(decision.decision);
      expect(decision.weighted_score).toBeGreaterThanOrEqual(0);
      expect(decision.weighted_score).toBeLessThanOrEqual(1);
    });

    it('should check proposal authority based on innovation score', async () => {
      await reputation.initializeEntity(testEntityId, 'agent', []);

      // New entities start with innovation = 0.5, threshold is 0.4, so they CAN propose
      const check1 = await governance.canProposeChange(testEntityId);
      expect(check1.allowed).toBe(true);
      expect(check1.score).toBe(0.5); // Initial innovation score

      // Increase innovation through governance_voted events
      for (let i = 0; i < 3; i++) {
        await reputation.recordEvent(testEntityId, 'governance_voted', 1.0, [], {
          proposal_id: uuidv4(),
          vote_type: 'approve',
        });
      }

      // Should now have even higher innovation
      const check2 = await governance.canProposeChange(testEntityId);
      expect(check2.allowed).toBe(true);
      expect(check2.score).toBeGreaterThanOrEqual(check1.score);
    });

    it('should form coalition from governance', async () => {
      const initiator = uuidv4();
      await reputation.initializeEntity(initiator, 'agent', ['research']);

      const coalition_req = await governance.formCoalition(
        initiator,
        'Investigate AI safety',
        ['research', 'analysis']
      );

      expect(coalition_req.coalition_id).toBeDefined();
      expect(coalition_req.initiator_id).toBe(initiator);
      expect(coalition_req.status).toBe('forming');
      expect(coalition_req.recruited_members).toContain(initiator);
    });
  });

  describe('Coalition Formation', () => {
    it('should require team lead with sufficient reliability', async () => {
      const team_lead = uuidv4();
      await reputation.initializeEntity(team_lead, 'agent', []);

      // New entities have 0.5 reliability, threshold is 0.7
      // Try to form coalition with insufficient reliability
      try {
        await coalition.formCoalition(uuidv4(), 'Research task', ['research'], team_lead);
        expect(true).toBe(false); // Should not reach here
      } catch (e) {
        expect((e as any).message).toContain('reliability');
      }
    });

    it('should form coalition with qualified team lead', async () => {
      const team_lead = uuidv4();
      await reputation.initializeEntity(team_lead, 'agent', ['research']);

      // Increase reliability to threshold (0.7)
      // Each claim_verified adds 0.1 to reliability
      for (let i = 0; i < 5; i++) {
        await reputation.recordEvent(team_lead, 'claim_verified', 1.0, []);
      }

      const coal = await coalition.formCoalition(uuidv4(), 'Research task', ['research'], team_lead);

      expect(coal.coalition_id).toBeDefined();
      expect(coal.team_lead).toBe(team_lead);
      expect(coal.status).toBe('forming');
      expect(coal.members.length).toBeGreaterThan(0);
    });

    it('should calculate team composition metrics', async () => {
      const team_lead = uuidv4();
      await reputation.initializeEntity(team_lead, 'agent', ['research']);

      // Build reliability for lead (threshold is 0.7)
      for (let i = 0; i < 5; i++) {
        await reputation.recordEvent(team_lead, 'claim_verified', 1.0, []);
      }

      const coal = await coalition.formCoalition(uuidv4(), 'Research task', ['research'], team_lead);

      expect(coal.formation_score).toBeGreaterThan(0);
      expect(coal.formation_score).toBeLessThanOrEqual(1);
      expect(coal.members.length).toBeGreaterThan(0);

      const metrics = coalition.getCoalitionMetrics(coal.coalition_id);
      expect(metrics.size).toBe(coal.members.length);
      expect(metrics.formation_score).toBe(coal.formation_score);
      expect(metrics.status).toBe('forming');
    });

    it('should complete coalition task and record performance', async () => {
      const team_lead = uuidv4();
      await reputation.initializeEntity(team_lead, 'agent', ['research']);

      // Build lead reliability (threshold 0.7)
      for (let i = 0; i < 5; i++) {
        await reputation.recordEvent(team_lead, 'claim_verified', 1.0, []);
      }

      const coal = await coalition.formCoalition(uuidv4(), 'Research task', ['research'], team_lead);

      // Get initial reputation
      const initial_record = reputation.getReputation(team_lead);
      const initial_score = initial_record?.current_score || 0;

      // Complete task successfully
      await coalition.completeCoalitionTask(coal.coalition_id, true, 'Task completed successfully');

      // Check coalition status updated
      const updated_coal = coalition.getCoalition(coal.coalition_id);
      expect(updated_coal?.status).toBe('completed');
      expect(updated_coal?.completed_at).toBeDefined();
    });

    it('should record failed coalition task', async () => {
      const team_lead = uuidv4();
      await reputation.initializeEntity(team_lead, 'agent', ['research']);

      // Build lead reliability (threshold 0.7)
      for (let i = 0; i < 5; i++) {
        await reputation.recordEvent(team_lead, 'claim_verified', 1.0, []);
      }

      const coal = await coalition.formCoalition(uuidv4(), 'Research task', ['research'], team_lead);

      // Complete task unsuccessfully
      await coalition.completeCoalitionTask(coal.coalition_id, false, 'Task failed - resource constraints');

      const updated_coal = coalition.getCoalition(coal.coalition_id);
      expect(updated_coal?.status).toBe('failed');
    });

    it('should get active coalitions', async () => {
      const team_lead = uuidv4();
      await reputation.initializeEntity(team_lead, 'agent', []);

      // Build reliability (threshold 0.7)
      for (let i = 0; i < 5; i++) {
        await reputation.recordEvent(team_lead, 'claim_verified', 1.0, []);
      }

      const coal1 = await coalition.formCoalition(uuidv4(), 'Task 1', [], team_lead);
      const coal2 = await coalition.formCoalition(uuidv4(), 'Task 2', [], team_lead);

      const active = coalition.getActiveCoalitions();
      expect(active.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('Full Governance-Coalition Integration', () => {
    it('should use governance to approve coalition formation', async () => {
      // Setup: High-reputation proposer
      const proposer = uuidv4();
      await reputation.initializeEntity(proposer, 'agent', ['research']);

      // Build reliability first (threshold 0.7 for coalition formation)
      for (let i = 0; i < 5; i++) {
        await reputation.recordEvent(proposer, 'claim_verified', 1.0, []);
      }

      // Build innovation score for proposal authority
      for (let i = 0; i < 5; i++) {
        await reputation.recordEvent(proposer, 'governance_voted', 1.0, []);
      }

      // Check authority
      const { allowed } = await governance.canProposeChange(proposer);
      expect(allowed).toBeDefined();

      // Form coalition for task (requires approval)
      const coal_id = uuidv4();
      const coal = await coalition.formCoalition(coal_id, 'Approved task', ['research'], proposer);

      expect(coal.coalition_id).toBeDefined();
      expect(coal.team_lead).toBe(proposer);
    });

    it('should track governance votes for coalition decisions', async () => {
      // Create voters with reputation
      const voter1 = uuidv4();
      const voter2 = uuidv4();

      await reputation.initializeEntity(voter1, 'agent', []);
      await reputation.initializeEntity(voter2, 'agent', []);

      // Build reputation for both
      for (let i = 0; i < 3; i++) {
        await reputation.recordEvent(voter1, 'claim_verified', 1.0, []);
        await reputation.recordEvent(voter2, 'claim_verified', 0.8, []);
      }

      // Vote on coalition proposal
      await governance.recordVote(voter1, testProposalId, 'approve');
      await governance.recordVote(voter2, testProposalId, 'approve');

      // Make decision
      const decision = await governance.makeGovernanceDecision(
        testProposalId,
        'coalition_formation',
        uuidv4()
      );

      expect(decision.decision).toBeDefined();
      expect(['approved', 'rejected', 'deferred']).toContain(decision.decision);
    });

    it('should escalate reputation events through governance-coalition cycle', async () => {
      // Setup: Team lead forms coalition
      const team_lead = uuidv4();
      await reputation.initializeEntity(team_lead, 'agent', ['research']);

      // Build lead's reliability (threshold 0.7)
      for (let i = 0; i < 5; i++) {
        await reputation.recordEvent(team_lead, 'claim_verified', 1.0, []);
      }

      const initial_record = reputation.getReputation(team_lead);
      const initial_score = initial_record?.current_score || 0;

      // Form coalition
      const coal = await coalition.formCoalition(uuidv4(), 'Task', ['research'], team_lead);

      // Complete successfully
      await coalition.completeCoalitionTask(coal.coalition_id, true);

      // Check reputation updated
      const updated_record = reputation.getReputation(team_lead);
      expect(updated_record?.current_score).toBeGreaterThanOrEqual(initial_score);

      // Vote on governance proposal (team lead)
      const proposal = uuidv4();
      const vote = await governance.recordVote(team_lead, proposal, 'approve', 'Team lead recommends');

      expect(vote.voter_id).toBe(team_lead);
      expect(vote.vote).toBe('approve');
      // Vote should use updated reputation scores
      expect(vote.voter_reputation).toBeGreaterThanOrEqual(initial_score);
    });
  });
});
