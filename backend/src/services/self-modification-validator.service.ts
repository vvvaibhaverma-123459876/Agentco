import { db } from '../db/client';
import { v4 as uuidv4 } from 'uuid';
import { ProtectedSurfaceEnforcerService } from './protected-surface-enforcer.service';

export interface ProtectedSurface {
  id: string;
  name: string;
  description: string;
  paths: string[];
  symbols: string[];
  protectionLevel: 'critical' | 'high' | 'medium';
  status: 'active' | 'inactive';
}

export interface SelfModValidation {
  id: string;
  candidateId: string;
  status: 'passed' | 'blocked';
  blocked: boolean;
  blockedReasons: string[];
  touchedSurfaces: string[];
  auditEventId?: string;
  createdAt: Date;
}

export class SelfModificationValidator {
  /**
   * Authoritative enforcer: derives protected surfaces from governance/policy.py and
   * fails closed. Consulted per change so enforcement is unified on the policy-derived
   * surfaces rather than only the in-class manifest below.
   */
  private enforcer = new ProtectedSurfaceEnforcerService();

  /**
   * Get protected surfaces manifest
   */
  private getProtectedSurfaces(): ProtectedSurface[] {
    return [
      {
        id: 'ps_calibration',
        name: 'Calibration Scoring',
        description: 'Core calibration system that ranks sources and claims',
        paths: [
          'calibration',
          'calibration/',
          'src/services/calibration',
          'src/services/confidence',
          'backend/src/services/calibration',
          'backend/src/services/confidence',
        ],
        symbols: [
          'CalibrationService',
          'ConfidenceService',
          'compute_calibration',
          'score_confidence',
          'rank_sources',
        ],
        protectionLevel: 'critical',
        status: 'active',
      },
      {
        id: 'ps_resolver',
        name: 'Sealed Resolver',
        description: 'Resolution independence engine that prevents source bias',
        paths: [
          'resolver',
          'resolver/',
          'src/sealed_resolver',
          'backend/src/services/integration.service.ts',
        ],
        symbols: [
          'SealedResolver',
          'IntegrationService',
          'resolve_independently',
          'check_resolution_bias',
        ],
        protectionLevel: 'critical',
        status: 'active',
      },
      {
        id: 'ps_audit_log',
        name: 'Audit Log Immutability',
        description: 'Immutable audit trail of all claims and resolutions',
        paths: [
          'audit',
          'audit/',
          'src/services/audit',
          'backend/src/services/audit-log.service.ts',
        ],
        symbols: [
          'AuditLogService',
          'write_audit_event',
          'audit_immutable',
          'mark_immutable',
        ],
        protectionLevel: 'critical',
        status: 'active',
      },
      {
        id: 'ps_ground_truth',
        name: 'Ground Truth Data',
        description: 'Verified ground truth data and baseline assumptions',
        paths: [
          'ground_truth',
          'ground_truth/',
          'data/ground_truth',
          'backend/data/ground_truth',
        ],
        symbols: [
          'GroundTruthStore',
          'write_ground_truth',
          'freeze_ground_truth',
        ],
        protectionLevel: 'critical',
        status: 'active',
      },
      {
        id: 'ps_rbac',
        name: 'RBAC Enforcement',
        description: 'Role-based access control that enforces authorization',
        paths: [
          'rbac',
          'rbac/',
          'src/services/rbac',
          'backend/src/db/migrations/033_rbac.sql',
        ],
        symbols: [
          'RBAC',
          'check_permission',
          'enforce_role',
          'verify_authorization',
        ],
        protectionLevel: 'critical',
        status: 'active',
      },
      {
        id: 'ps_governance',
        name: 'Governance Approval Checks',
        description: 'Governance gates that require human approval for critical changes',
        paths: [
          'governance',
          'governance/',
          'src/services/governance',
          'backend/src/db/migrations/034_policy_control.sql',
        ],
        symbols: [
          'GovernanceService',
          'require_approval',
          'check_governance',
          'is_approved',
        ],
        protectionLevel: 'high',
        status: 'active',
      },
      {
        id: 'ps_eval_gate',
        name: 'Evaluation Gate Logic',
        description: 'Logic that decides whether candidates can be promoted',
        paths: [
          'eval',
          'eval/',
          'src/services/eval',
          'backend/src/services/eval-harness.service.ts',
        ],
        symbols: [
          'EvalHarnessService',
          'runFullEvaluation',
          'promotionEligible',
          'safetyScore',
        ],
        protectionLevel: 'high',
        status: 'active',
      },
      {
        id: 'ps_migration',
        name: 'Migration Integrity',
        description: 'Database migrations that define the core schema',
        paths: [
          'migrations',
          'migrations/',
          'backend/src/db/migrations',
          'backend/src/db/migrations/*.sql',
        ],
        symbols: [
          'CREATE TABLE',
          'ALTER TABLE',
          'migration_version',
        ],
        protectionLevel: 'high',
        status: 'active',
      },
      {
        id: 'ps_reward_function',
        name: 'Reward Function History',
        description: 'Reward function definitions that shape autonomous behavior',
        paths: [
          'reward',
          'reward/',
          'src/services/reward',
          'backend/src/db/migrations/027_reward_system.sql',
        ],
        symbols: [
          'RewardService',
          'reward_function',
          'calculate_reward',
          'reward_formula',
        ],
        protectionLevel: 'high',
        status: 'active',
      },
      {
        id: 'ps_secret_check',
        name: 'Production Secret Enforcement',
        description: 'Logic that ensures secrets are not exposed in non-production',
        paths: [
          'secret',
          'secret/',
          'env_guard',
          'production_check',
        ],
        symbols: [
          'check_environment',
          'is_production',
          'secret_safe',
          'block_if_production',
        ],
        protectionLevel: 'high',
        status: 'active',
      },
    ];
  }

  /**
   * Scan candidate artifact for protected surface modifications
   */
  async validateCandidate(candidateId: string): Promise<SelfModValidation> {
    const validationId = uuidv4();

    // Get candidate
    const candResult = await db.query(
      `SELECT artifact_id, artifact_json FROM learner_candidates WHERE id = $1`,
      [candidateId]
    );

    if (candResult.rows.length === 0) {
      throw new Error(`Candidate not found: ${candidateId}`);
    }

    const candidate = candResult.rows[0];
    const artifact = JSON.parse(candidate.artifact_json);

    // Get protected surfaces
    const protectedSurfaces = this.getProtectedSurfaces();

    // Scan artifact for protected surface modifications
    const blockedReasons: string[] = [];
    const touchedSurfaces: string[] = [];

    if (artifact.changes && Array.isArray(artifact.changes)) {
      for (const change of artifact.changes) {
        const field = change.field || '';
        const action = change.action || '';

        // Check against all protected surfaces
        for (const surface of protectedSurfaces) {
          // Check path matches
          for (const path of surface.paths) {
            if (this.pathMatches(field, path)) {
              if (!touchedSurfaces.includes(surface.name)) {
                touchedSurfaces.push(surface.name);
              }

              if (surface.protectionLevel === 'critical') {
                blockedReasons.push(
                  `CRITICAL: Attempted modification of ${surface.name} (field: ${field})`
                );
              }
            }
          }

          // Check symbol matches
          for (const symbol of surface.symbols) {
            if (field.includes(symbol) || (change.value && JSON.stringify(change.value).includes(symbol))) {
              if (!touchedSurfaces.includes(surface.name)) {
                touchedSurfaces.push(surface.name);
              }

              if (surface.protectionLevel === 'critical') {
                blockedReasons.push(
                  `CRITICAL: Attempted modification of ${surface.name} (symbol: ${symbol})`
                );
              }
            }
          }
        }

        // Additional heuristic checks
        if (action === 'delete' || action === 'remove') {
          // Deleting anything suspicious
          if (field.toLowerCase().includes('check') || field.toLowerCase().includes('verify')) {
            blockedReasons.push(`BLOCKED: Suspicious deletion of ${field}`);
          }
        }

        if (action === 'override' || action === 'bypass') {
          blockedReasons.push(`BLOCKED: Attempt to override/bypass ${field}`);
        }

        // Authoritative check: consult the policy.py-derived enforcer (fail-closed).
        // This is the source of truth for protected surfaces; the in-class manifest above
        // is a fast pre-filter. A destructive action raises the risk to 'critical'.
        const enforcerRisk: 'low' | 'high' | 'critical' =
          action === 'delete' || action === 'remove' || action === 'override' || action === 'bypass'
            ? 'critical'
            : 'high';
        const verdict = await this.enforcer.evaluateModificationAttempt(
          field,
          change.value !== undefined ? JSON.stringify(change.value) : '',
          enforcerRisk,
        );
        if (verdict.requires_human_approval) {
          if (!touchedSurfaces.includes(verdict.surface_path)) {
            touchedSurfaces.push(verdict.surface_path);
          }
          blockedReasons.push(
            `BLOCKED by protected-surface enforcer: ${field} requires human approval (risk: ${enforcerRisk})`,
          );
        }
      }
    }

    const passed = blockedReasons.length === 0;
    const status = passed ? 'passed' : 'blocked';

    // Create validation record
    const now = new Date();
    const result = await db.query(
      `INSERT INTO self_modification_validations (
        id, candidate_id, status, blocked_reasons_json, touched_surfaces_json, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING id, created_at`,
      [
        validationId,
        candidateId,
        status,
        JSON.stringify(blockedReasons),
        JSON.stringify(touchedSurfaces),
        now,
      ]
    );

    // Write audit event if blocked
    let auditEventId: string | undefined;
    if (!passed) {
      const eventId = uuidv4();
      await db.query(
        `INSERT INTO audit_events (
          id, event_type, entity_type, entity_id, status, details_json, severity
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)`,
        [
          eventId,
          'self_modification_blocked',
          'candidate',
          candidateId,
          'blocked',
          JSON.stringify({
            reason: 'Protected surface violation',
            blocked_reasons: blockedReasons,
            touched_surfaces: touchedSurfaces,
            validation_id: validationId,
          }),
          'high',
        ]
      );
      auditEventId = eventId;
    }

    return {
      id: result.rows[0].id,
      candidateId,
      status,
      blocked: !passed,
      blockedReasons,
      touchedSurfaces,
      auditEventId,
      createdAt: result.rows[0].created_at,
    };
  }

  /**
   * Helper: Check if field path matches protected surface path
   */
  private pathMatches(fieldPath: string, protectedPath: string): boolean {
    // Normalize paths
    const normalized = (p: string) => p.toLowerCase().replace(/\/+/g, '/').trim();

    const field = normalized(fieldPath);
    const protectedSurface = normalized(protectedPath);

    // Exact match
    if (field === protectedSurface) return true;

    // Wildcard match (e.g., migrations/*.sql)
    if (protectedSurface.includes('*')) {
      const regex = new RegExp('^' + protectedSurface.replace(/\*/g, '.*') + '$');
      return regex.test(field);
    }

    // Contains match (for shorter paths)
    if (protectedSurface.length > 0 && field.includes(protectedSurface)) return true;

    return false;
  }

  /**
   * Get validation details
   */
  async getValidation(validationId: string): Promise<SelfModValidation> {
    const result = await db.query(
      `SELECT id, candidate_id, status, blocked_reasons_json, touched_surfaces_json, created_at
       FROM self_modification_validations WHERE id = $1`,
      [validationId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Validation not found: ${validationId}`);
    }

    const row = result.rows[0];
    return {
      id: row.id,
      candidateId: row.candidate_id,
      status: row.status,
      blocked: row.status === 'blocked',
      blockedReasons: JSON.parse(row.blocked_reasons_json || '[]'),
      touchedSurfaces: JSON.parse(row.touched_surfaces_json || '[]'),
      createdAt: row.created_at,
    };
  }
}

// Export singleton instance
export const selfModValidator = new SelfModificationValidator();
