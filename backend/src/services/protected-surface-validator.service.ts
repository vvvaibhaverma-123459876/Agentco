import { db } from '../db/client';

/**
 * Protected Surface Validator Service
 *
 * Enforces protection of critical system surfaces that should NEVER be modified by autonomy:
 * - Calibration system (affects trust scoring)
 * - Resolution service (affects ground truth)
 * - Audit logs (affects compliance)
 * - RBAC system (affects access control)
 * - Governance policies (affects decision making)
 * - Safety constraints (affects safety)
 * - Policy evaluation logic (affects all decisions)
 */

export interface ProtectedSurface {
  name: string;
  description: string;
  criticalityLevel: 'critical' | 'high' | 'medium';
  examples: string[];
}

const PROTECTED_SURFACES: Record<string, ProtectedSurface> = {
  calibration: {
    name: 'Calibration System',
    description: 'Metrics and logic that measure prediction accuracy',
    criticalityLevel: 'critical',
    examples: ['calibration_scores', 'calibration_models', 'calibration_thresholds', 'ece_values'],
  },
  resolution: {
    name: 'Resolution Service',
    description: 'Ground truth determination for claims',
    criticalityLevel: 'critical',
    examples: ['resolution_logic', 'ground_truth_registry', 'claim_resolver', 'truth_determiner'],
  },
  audit_log: {
    name: 'Audit Trail',
    description: 'Immutable record of all system actions',
    criticalityLevel: 'critical',
    examples: ['audit_events', 'event_history', 'decision_log', 'action_attestations'],
  },
  rbac: {
    name: 'RBAC System',
    description: 'Role-based access control and permissions',
    criticalityLevel: 'critical',
    examples: ['role_definitions', 'permission_matrix', 'user_roles', 'capability_grants'],
  },
  governance: {
    name: 'Governance Policy',
    description: 'Constitutional rules and policy enforcement',
    criticalityLevel: 'critical',
    examples: ['constitutions', 'policies', 'rules', 'constraints', 'override_queue'],
  },
  safety: {
    name: 'Safety Constraints',
    description: 'Hard constraints that prevent unsafe behavior',
    criticalityLevel: 'critical',
    examples: ['safety_constraints', 'forbidden_actions', 'resource_limits', 'rate_limits'],
  },
  policy: {
    name: 'Policy Engine',
    description: 'Logic for evaluating and enforcing policies',
    criticalityLevel: 'high',
    examples: ['policy_evaluator', 'constraint_checker', 'policy_rules', 'policy_engine'],
  },
};

export interface ValidationResult {
  valid: boolean;
  touchedSurfaces: string[];
  violations: Array<{
    surface: string;
    criticalityLevel: string;
    field: string;
    reason: string;
  }>;
  reason?: string;
}

/**
 * Validate a candidate artifact against protected surfaces
 */
async function validateCandidate(artifact: Record<string, any>): Promise<ValidationResult> {
  const touchedSurfaces: string[] = [];
  const violations: ValidationResult['violations'] = [];

  if (!artifact || !artifact.changes) {
    return { valid: true, touchedSurfaces: [], violations: [] };
  }

  // Check each change in the candidate
  for (const change of artifact.changes) {
    const field = (change.field || '').toLowerCase();
    const action = change.action || '';

    // Check against each protected surface
    for (const [surfaceKey, surface] of Object.entries(PROTECTED_SURFACES)) {
      // Check field examples
      for (const example of surface.examples) {
        if (field.includes(example.toLowerCase()) || action.includes(example.toLowerCase())) {
          touchedSurfaces.push(surfaceKey);

          violations.push({
            surface: surface.name,
            criticalityLevel: surface.criticalityLevel,
            field: change.field,
            reason: `Attempted modification of ${surface.name} (${surface.description})`,
          });

          // For critical surfaces, immediately block
          if (surface.criticalityLevel === 'critical') {
            return {
              valid: false,
              touchedSurfaces,
              violations,
              reason: `CRITICAL VIOLATION: Cannot modify protected surface "${surface.name}"`,
            };
          }
        }
      }
    }
  }

  // If any high-level violations and we're touching them, block
  const highCriticalViolations = violations.filter((v) => v.criticalityLevel === 'high');
  if (highCriticalViolations.length > 0) {
    return {
      valid: false,
      touchedSurfaces,
      violations,
      reason: `HIGH-SEVERITY VIOLATIONS: Cannot modify protected surface(s)`,
    };
  }

  return {
    valid: violations.length === 0,
    touchedSurfaces,
    violations,
  };
}

/**
 * Log a protected surface violation
 */
async function logViolation(
  candidateId: string,
  touchedSurfaces: string[],
  violations: any[]
): Promise<void> {
  try {
    await db.query(
      `INSERT INTO autonomy_task_events (
        event_type, previous_status, new_status, actor_type, reason
      ) VALUES ($1, $2, $3, $4, $5)`,
      [
        'escalated',
        'evaluating',
        'blocked',
        'system',
        `Protected surface violation: ${touchedSurfaces.join(', ')}`,
      ]
    );
  } catch (error) {
    console.error('Failed to log protected surface violation:', error);
  }
}

/**
 * Validate and enforce protected surfaces
 */
export async function validateProtectedSurfaces(candidateId: string, artifact: Record<string, any>) {
  const result = await validateCandidate(artifact);

  if (!result.valid) {
    await logViolation(candidateId, result.touchedSurfaces, result.violations);

    console.log(`[PROTECTED_SURFACE] VIOLATION BLOCKED:`, {
      candidate: candidateId,
      surfaces: result.touchedSurfaces,
      violations: result.violations.length,
      reason: result.reason,
    });

    throw new Error(result.reason || 'Protected surface violation');
  }

  if (result.touchedSurfaces.length > 0) {
    console.log(`[PROTECTED_SURFACE] WARNING: Candidate touches protected surfaces:`, {
      candidate: candidateId,
      surfaces: result.touchedSurfaces,
    });
  }

  return result;
}

/**
 * Get protected surface definitions (for documentation)
 */
export function getProtectedSurfaceDefinitions(): Record<string, ProtectedSurface> {
  return PROTECTED_SURFACES;
}

/**
 * Check if a specific field is protected
 */
export function isProtected(field: string): boolean {
  const lowerField = field.toLowerCase();

  for (const surface of Object.values(PROTECTED_SURFACES)) {
    for (const example of surface.examples) {
      if (lowerField.includes(example.toLowerCase())) {
        return true;
      }
    }
  }

  return false;
}
