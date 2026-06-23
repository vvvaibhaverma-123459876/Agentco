/**
 * Bridge service between autonomy and civilization layers
 * Handles:
 * 1. Work request routing from institution to specialists
 * 2. Performance scoring when work completes
 * 3. Reputation feedback to civilization layer
 */

import { institutionWorkAssignmentService } from './institution-work-assignment.service';

interface WorkCompletionResult {
  work_request_id: string;
  specialist_role: string;
  evidence_count: number;
  claim_count: number;
  confidence_avg: number;
  tokens_used: number;
  iterations_used: number;
  time_elapsed_seconds: number;
}

class AutonomyCivilizationBridgeService {
  /**
   * Compute specialist performance score from work result
   */
  computePerformanceScore(result: WorkCompletionResult): {
    evidence_quality: number;
    claim_accuracy: number;
    efficiency: number;
    overall: number;
  } {
    // Evidence quality: (evidence_count, relevance from work context)
    const evidence_quality = Math.min(1.0, (result.evidence_count || 1) / 10.0);

    // Claim accuracy: confidence score from autonomy layer
    const claim_accuracy = result.confidence_avg || 0.7;

    // Efficiency: token ratio (lower is better)
    // Assume 10000 tokens per hour as baseline
    const baseline_tokens = (result.time_elapsed_seconds / 3600) * 10000;
    const token_efficiency = Math.max(0.0, 1.0 - result.tokens_used / (baseline_tokens + 1));
    const iteration_efficiency = Math.max(0.0, 1.0 - result.iterations_used / 100);
    const efficiency = (token_efficiency + iteration_efficiency) / 2;

    // Overall score: weighted average
    const overall = (
      evidence_quality * 0.4 +
      claim_accuracy * 0.35 +
      efficiency * 0.25
    );

    return {
      evidence_quality: Math.round(evidence_quality * 100) / 100,
      claim_accuracy: Math.round(claim_accuracy * 100) / 100,
      efficiency: Math.round(efficiency * 100) / 100,
      overall: Math.round(overall * 100) / 100,
    };
  }

  /**
   * Report work completion to reputation system
   */
  async reportWorkCompletion(result: WorkCompletionResult): Promise<void> {
    try {
      // Get work request to find institution/department
      const workRequest = await institutionWorkAssignmentService.getWorkRequest(
        result.work_request_id
      );

      if (!workRequest) {
        console.error(`Work request not found: ${result.work_request_id}`);
        return;
      }

      // Compute performance scores
      const scores = this.computePerformanceScore(result);

      // Record specialist performance
      await institutionWorkAssignmentService.recordSpecialistPerformance(
        result.work_request_id,
        {
          work_request_id: result.work_request_id,
          specialist_role: result.specialist_role,
          evidence_quality_score: scores.evidence_quality,
          claim_accuracy_score: scores.claim_accuracy,
          efficiency_score: scores.efficiency,
          overall_score: scores.overall,
          tokens_used: result.tokens_used,
          iterations_used: result.iterations_used,
          time_elapsed_seconds: result.time_elapsed_seconds,
        }
      );

      // Update work request to completed
      await institutionWorkAssignmentService.updateWorkRequestStatus(
        result.work_request_id,
        'completed',
        {
          result_summary: {
            evidence_count: result.evidence_count,
            claim_count: result.claim_count,
            overall_score: scores.overall,
          },
        }
      );

      // Update specialist reputation assignment (in production, would call Python reputation service)
      await institutionWorkAssignmentService.assignSpecialistToDepartment(
        workRequest.institution_id,
        workRequest.department_id,
        result.specialist_role,
        scores.overall  // Use overall score as reputation
      );

      console.log(
        `✅ Work completion reported: ${result.work_request_id} for ${result.specialist_role} (score: ${scores.overall})`
      );
    } catch (e) {
      console.error(`Failed to report work completion: ${e}`);
      throw e;
    }
  }

  /**
   * Route institutional work request to autonomy system
   * Returns autonomy goal ID for the work
   */
  async routeWorkToAutonomy(
    workRequestId: string,
    objective: string,
    specialists: string[]
  ): Promise<string> {
    // In production, would create autonomy goal via orchestrator API
    // For now, return a placeholder goal ID
    const autonomyGoalId = `autonomy_goal_${workRequestId}`;

    // Update work request with autonomy goal
    await institutionWorkAssignmentService.updateWorkRequestStatus(
      workRequestId,
      'in_progress',
      { autonomy_goal_id: autonomyGoalId }
    );

    return autonomyGoalId;
  }
}

export const autonomyCivilizationBridgeService = new AutonomyCivilizationBridgeService();
