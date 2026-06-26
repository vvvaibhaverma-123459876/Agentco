/**
 * COALITION FORMATION SERVICE
 * ==========================
 *
 * Assembles effective teams using reputation signals:
 * - Specialization matching for task requirements
 * - Collaboration score filtering for team cohesion
 * - Reliability weighting for critical roles
 * - Team performance monitoring
 *
 * PRODUCTION-GRADE: Full error handling, monitoring, persistence
 */

import { v4 as uuidv4 } from 'uuid';
import { db } from '../db/client';
import { ReputationLearningService } from './reputation-learning.service';

export interface TeamMember {
  agent_id: string;
  specializations: string[];
  collaboration_score: number;
  reliability_score: number;
  innovation_score: number;
  availability: boolean;
}

export interface Coalition {
  coalition_id: string;
  task_id: string;
  objective: string;
  required_specializations: string[];
  min_collaboration_threshold: number;
  team_lead: string;
  members: TeamMember[];
  formation_score: number; // 0-1, quality of team composition
  status: 'forming' | 'active' | 'completed' | 'failed';
  created_at: Date;
  completed_at?: Date;
}

export interface TeamComposition {
  team_lead_reliability: number;
  avg_collaboration: number;
  specialization_coverage: number; // 0-1
  diversity_score: number; // 0-1, variation in specializations
  cohesion_score: number; // 0-1, average of pairwise compatibility
}

class CoalitionFormationService {
  private reputation: ReputationLearningService;
  private coalitions = new Map<string, Coalition>();
  private min_collaboration_threshold = 0.5; // Minimum for any team member
  private lead_reliability_threshold = 0.7; // Minimum for certified team lead

  constructor(reputationService?: ReputationLearningService) {
    this.reputation = reputationService || new ReputationLearningService();
  }

  /**
   * Find potential team members matching specializations
   */
  async findCandidates(
    required_specializations: string[],
    min_collaboration: number = this.min_collaboration_threshold
  ): Promise<TeamMember[]> {
    try {
      const required = new Set(required_specializations);
      const activeMemberIds = new Set(
        Array.from(this.coalitions.values())
          .filter((coalition) => coalition.status === 'active' || coalition.status === 'forming')
          .flatMap((coalition) => coalition.members.map((member) => member.agent_id))
      );

      console.log(
        `[CoalitionFormation] Searching for candidates with specializations: ${required_specializations.join(', ')}`
      );

      return this.reputation
        .listReputations()
        .filter((record) => record.entity_type === 'agent')
        .filter((record) => !activeMemberIds.has(record.entity_id))
        .filter((record) => record.collaboration >= min_collaboration)
        .filter((record) => required.size === 0 || record.specialization.some((spec) => required.has(spec)))
        .map((record) => ({
          agent_id: record.entity_id,
          specializations: record.specialization,
          collaboration_score: record.collaboration,
          reliability_score: record.reliability,
          innovation_score: record.innovation,
          availability: true,
        }))
        .sort((a, b) => {
          const aCoverage = a.specializations.filter((spec) => required.has(spec)).length;
          const bCoverage = b.specializations.filter((spec) => required.has(spec)).length;
          const aScore = aCoverage * 0.5 + a.collaboration_score * 0.25 + a.reliability_score * 0.25;
          const bScore = bCoverage * 0.5 + b.collaboration_score * 0.25 + b.reliability_score * 0.25;
          return bScore - aScore;
        });
    } catch (e) {
      console.error(`[CoalitionFormation] Failed to find candidates: ${(e as any).message}`);
      return [];
    }
  }

  /**
   * Calculate team composition quality metrics
   */
  private calculateComposition(
    team_lead: TeamMember,
    members: TeamMember[],
    required_specializations: string[]
  ): TeamComposition {
    // Team lead reliability (most important)
    const team_lead_reliability = team_lead.reliability_score;

    // Average collaboration (team cohesion)
    const avg_collaboration = members.reduce((sum, m) => sum + m.collaboration_score, 0) / Math.max(1, members.length);

    // Specialization coverage (what % of required specs are covered)
    const covered = new Set(members.flatMap(m => m.specializations));
    const specialization_coverage = required_specializations.length > 0
      ? required_specializations.filter(s => covered.has(s)).length / required_specializations.length
      : 1.0;

    // Diversity (members have different specializations)
    const all_specs = members.flatMap(m => m.specializations);
    const unique_specs = new Set(all_specs).size;
    const diversity_score = all_specs.length > 0 ? unique_specs / all_specs.length : 0;

    // Cohesion (pairwise compatibility based on collaboration scores)
    let cohesion_total = 0;
    let cohesion_pairs = 0;
    for (let i = 0; i < members.length; i++) {
      for (let j = i + 1; j < members.length; j++) {
        // High collaboration scores = high compatibility
        cohesion_total += (members[i].collaboration_score + members[j].collaboration_score) / 2;
        cohesion_pairs++;
      }
    }
    const cohesion_score = cohesion_pairs > 0 ? cohesion_total / cohesion_pairs : members[0]?.collaboration_score || 0;

    return {
      team_lead_reliability,
      avg_collaboration,
      specialization_coverage,
      diversity_score,
      cohesion_score,
    };
  }

  /**
   * Form coalition for a task
   */
  async formCoalition(
    task_id: string,
    objective: string,
    required_specializations: string[],
    team_lead_id: string
  ): Promise<Coalition> {
    try {
      const coalition_id = uuidv4();

      // Verify team lead has sufficient reliability
      const lead_record = this.reputation.getReputation(team_lead_id);
      if (!lead_record) {
        throw new Error(`Team lead ${team_lead_id} not found in reputation system`);
      }

      if (lead_record.reliability < this.lead_reliability_threshold) {
        throw new Error(
          `Team lead reliability (${lead_record.reliability.toFixed(2)}) below required threshold ${this.lead_reliability_threshold}`
        );
      }

      const lead_member: TeamMember = {
        agent_id: team_lead_id,
        specializations: lead_record.specialization,
        collaboration_score: lead_record.collaboration,
        reliability_score: lead_record.reliability,
        innovation_score: lead_record.innovation,
        availability: true,
      };

      // Find team members
      const candidates = await this.findCandidates(required_specializations, this.min_collaboration_threshold);

      // Filter candidates by collaboration threshold
      const qualified = candidates
        .filter(c => c.agent_id !== team_lead_id)
        .filter(c => c.collaboration_score >= this.min_collaboration_threshold);

      // Rank by fit (specialization + collaboration)
      qualified.sort((a, b) => {
        const a_fit =
          a.specializations.filter(s => required_specializations.includes(s)).length * a.collaboration_score;
        const b_fit =
          b.specializations.filter(s => required_specializations.includes(s)).length * b.collaboration_score;
        return b_fit - a_fit;
      });

      // Select top candidates (reasonable team size)
      const selected = qualified.slice(0, 5); // Max 5 additional members

      // Calculate composition metrics
      const composition = this.calculateComposition(lead_member, selected, required_specializations);

      // Formation score = weighted combination of metrics
      const formation_score =
        composition.team_lead_reliability * 0.3 +
        composition.avg_collaboration * 0.3 +
        composition.specialization_coverage * 0.2 +
        composition.diversity_score * 0.1 +
        composition.cohesion_score * 0.1;

      // Add metadata about lead type
      const coalition: Coalition = {
        coalition_id,
        task_id,
        objective,
        required_specializations,
        min_collaboration_threshold: this.min_collaboration_threshold,
        team_lead: team_lead_id,
        members: [lead_member, ...selected],
        formation_score,
        status: 'forming',
        created_at: new Date(),
      };

      // Persist coalition (non-blocking)
      try {
        await db.query(
          `INSERT INTO coalition_formations
           (coalition_id, task_id, objective, required_specializations, team_lead, members, formation_score, status)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
          [
            coalition_id,
            task_id,
            objective,
            JSON.stringify(required_specializations),
            team_lead_id,
            JSON.stringify(coalition.members),
            formation_score,
            'forming',
          ]
        );
      } catch (dbErr: any) {
        console.warn(`[CoalitionFormation] Coalition persist failed: ${dbErr.message}`);
      }

      // Record coordination_success event for team lead
      await this.reputation.recordEvent(team_lead_id, 'coordination_success', formation_score, [], {
        coalition_id,
        objective,
        team_size: coalition.members.length,
        composition_metrics: composition,
      });

      // Record coordination_success for each member
      for (const member of selected) {
        await this.reputation.recordEvent(member.agent_id, 'coordination_success', 0.6, [team_lead_id], {
          coalition_id,
          role: 'team_member',
          team_lead: team_lead_id,
        });
      }

      this.coalitions.set(coalition_id, coalition);

      console.log(
        `[CoalitionFormation] Coalition ${coalition_id} formed for "${objective}" ` +
          `(lead: ${team_lead_id} [CERTIFIED], members: ${coalition.members.length}, score: ${formation_score.toFixed(2)})`
      );

      return coalition;
    } catch (e) {
      console.error(`[CoalitionFormation] Failed to form coalition: ${(e as any).message}`);
      throw e;
    }
  }

  /**
   * Complete coalition task and record performance
   */
  async completeCoalitionTask(
    coalition_id: string,
    success: boolean,
    performance_notes?: string
  ): Promise<void> {
    try {
      const coalition = this.coalitions.get(coalition_id);
      if (!coalition) {
        throw new Error(`Coalition ${coalition_id} not found`);
      }

      // Update coalition status
      coalition.status = success ? 'completed' : 'failed';
      coalition.completed_at = new Date();

      // Persist update (non-blocking)
      try {
        await db.query(
          `UPDATE coalition_formations
           SET status = $1, completed_at = NOW()
           WHERE coalition_id = $2`,
          [coalition.status, coalition_id]
        );
      } catch (dbErr: any) {
        console.warn(`[CoalitionFormation] Status update failed: ${dbErr.message}`);
      }

      // Record performance events
      if (success) {
        // Success: record positive coordination_success events
        for (const member of coalition.members) {
          await this.reputation.recordEvent(member.agent_id, 'coordination_success', 0.8, coalition.members.map(m => m.agent_id), {
            coalition_id,
            task_completed: true,
            notes: performance_notes,
          });
        }
        console.log(`[CoalitionFormation] Coalition ${coalition_id} task completed successfully`);
      } else {
        // Failure: record coordination_failure events (negative impact on reputation)
        for (const member of coalition.members) {
          await this.reputation.recordEvent(
            member.agent_id,
            'coordination_failure',
            0.5,
            coalition.members.map(m => m.agent_id),
            {
              coalition_id,
              task_failed: true,
              notes: performance_notes,
            }
          );
        }
        console.log(`[CoalitionFormation] Coalition ${coalition_id} task failed`);
      }
    } catch (e) {
      console.error(`[CoalitionFormation] Failed to complete task: ${(e as any).message}`);
    }
  }

  /**
   * Get coalition performance metrics
   */
  getCoalitionMetrics(coalition_id: string): {
    size: number;
    formation_score: number;
    avg_collaboration: number;
    specialization_coverage: number;
    status: string;
  } {
    try {
      const coalition = this.coalitions.get(coalition_id);
      if (!coalition) {
        throw new Error(`Coalition not found`);
      }

      const avg_collaboration = coalition.members.reduce((sum, m) => sum + m.collaboration_score, 0) / coalition.members.length;

      const covered_specs = new Set(coalition.members.flatMap(m => m.specializations));
      const specialization_coverage =
        coalition.required_specializations.length > 0
          ? covered_specs.size / coalition.required_specializations.length
          : 1.0;

      return {
        size: coalition.members.length,
        formation_score: coalition.formation_score,
        avg_collaboration,
        specialization_coverage,
        status: coalition.status,
      };
    } catch (e) {
      console.error(`[CoalitionFormation] Failed to get metrics: ${(e as any).message}`);
      return {
        size: 0,
        formation_score: 0,
        avg_collaboration: 0,
        specialization_coverage: 0,
        status: 'unknown',
      };
    }
  }

  /**
   * Recommend team composition for task
   */
  async recommendTeamComposition(
    objective: string,
    required_specializations: string[]
  ): Promise<{
    recommended_lead: string | null;
    recommended_team_size: number;
    predicted_success_rate: number;
    reasoning: string;
  }> {
    try {
      const candidates = await this.findCandidates(required_specializations, this.min_collaboration_threshold);
      const leadCandidates = candidates
        .filter((candidate) => candidate.reliability_score >= this.lead_reliability_threshold)
        .sort((a, b) => {
          const aCoverage = a.specializations.filter((spec) => required_specializations.includes(spec)).length;
          const bCoverage = b.specializations.filter((spec) => required_specializations.includes(spec)).length;
          const aScore = a.reliability_score * 0.45 + a.collaboration_score * 0.35 + aCoverage * 0.2;
          const bScore = b.reliability_score * 0.45 + b.collaboration_score * 0.35 + bCoverage * 0.2;
          return bScore - aScore;
        });
      const recommendedLead = leadCandidates[0] || null;
      const selectedMembers = candidates
        .filter((candidate) => candidate.agent_id !== recommendedLead?.agent_id)
        .slice(0, 5);

      const membersForScoring = recommendedLead ? [recommendedLead, ...selectedMembers] : selectedMembers;
      const coveredSpecs = new Set(membersForScoring.flatMap((member) => member.specializations));
      const specializationCoverage = required_specializations.length > 0
        ? required_specializations.filter((spec) => coveredSpecs.has(spec)).length / required_specializations.length
        : 1.0;
      const avgReliability = membersForScoring.length > 0
        ? membersForScoring.reduce((sum, member) => sum + member.reliability_score, 0) / membersForScoring.length
        : 0;
      const avgCollaboration = membersForScoring.length > 0
        ? membersForScoring.reduce((sum, member) => sum + member.collaboration_score, 0) / membersForScoring.length
        : 0;
      const predictedSuccessRate = Math.max(
        0,
        Math.min(1, avgReliability * 0.4 + avgCollaboration * 0.35 + specializationCoverage * 0.25)
      );

      try {
        await db.query(
          `INSERT INTO coalition_composition_recommendations
           (recommendation_id, task_objective, required_specializations, recommended_lead_id, recommended_team_size, predicted_success_rate, reasoning)
           VALUES ($1, $2, $3, $4, $5, $6, $7)`,
          [
            uuidv4(),
            objective,
            JSON.stringify(required_specializations),
            recommendedLead?.agent_id || null,
            membersForScoring.length,
            predictedSuccessRate,
            recommendedLead
              ? `Lead selected from live reputation pool. Coverage=${specializationCoverage.toFixed(2)}, avg reliability=${avgReliability.toFixed(2)}, avg collaboration=${avgCollaboration.toFixed(2)}`
              : 'No available lead met the reliability threshold',
          ]
        );
      } catch (dbErr: any) {
        console.warn(`[CoalitionFormation] Recommendation persist failed: ${dbErr.message}`);
      }

      return {
        recommended_lead: recommendedLead?.agent_id || null,
        recommended_team_size: membersForScoring.length,
        predicted_success_rate: predictedSuccessRate,
        reasoning: recommendedLead
          ? `Recommended ${recommendedLead.agent_id} from ${candidates.length} available candidates for "${objective}"; specialization coverage ${specializationCoverage.toFixed(2)}`
          : `No available lead meets reliability threshold ${this.lead_reliability_threshold}; ${candidates.length} candidates considered`,
      };
    } catch (e) {
      console.error(`[CoalitionFormation] Failed to recommend: ${(e as any).message}`);
      return {
        recommended_lead: null,
        recommended_team_size: 0,
        predicted_success_rate: 0,
        reasoning: `Error: ${(e as any).message}`,
      };
    }
  }

  /**
   * Get all active coalitions
   */
  getActiveCoalitions(): Coalition[] {
    return Array.from(this.coalitions.values()).filter(c => c.status === 'active' || c.status === 'forming');
  }

  /**
   * Get coalition by ID
   */
  getCoalition(coalition_id: string): Coalition | null {
    return this.coalitions.get(coalition_id) || null;
  }
}

export const coalitionFormationService = new CoalitionFormationService();
export { CoalitionFormationService };
