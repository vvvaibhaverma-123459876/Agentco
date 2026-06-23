import { createHash } from 'crypto';
import { randomUUID } from 'crypto';
import { db } from '../db/client';

export interface ConstitutionVersion {
  id: string;
  version_number: number;
  content_json: Record<string, any>;
  content_hash: string;
  signature: string;
  signer_entity_id?: string;
  created_at: Date;
  retired_at?: Date;
}

export interface ProtectedSurface {
  id: string;
  surface_name: string;
  surface_type: string;
  description?: string;
  table_names: string[];
  column_patterns: string[];
  function_patterns: string[];
  is_immutable: boolean;
  requires_constitution_vote: boolean;
}

export interface AllowedChangeType {
  id: string;
  change_type_name: string;
  description?: string;
  category: string;
  max_scope: string;
  requires_eval: boolean;
  can_be_canaried: boolean;
}

export interface VerificationResult {
  is_compliant: boolean;
  violations: string[];
  protected_surfaces_touched: ProtectedSurface[];
  requires_override: boolean;
}

export class CalibrationConstitutionService {
  /**
   * Create a new constitution version
   */
  async createVersion(
    versionContent: Record<string, any>,
    signerEntityId: string,
    signature: string,
    traceId?: string
  ): Promise<ConstitutionVersion> {
    const contentJson = versionContent;
    const contentHash = this.hashContent(contentJson);

    const result = await db.query(
      `INSERT INTO calibration_constitution_versions (
        version_number, content_json, content_hash, signature, signer_entity_id
      ) VALUES (
        (SELECT COALESCE(MAX(version_number), 0) + 1 FROM calibration_constitution_versions),
        $1, $2, $3, $4
      ) RETURNING *`,
      [JSON.stringify(contentJson), contentHash, signature, signerEntityId]
    );

    if (result.rows.length === 0) {
      throw new Error('Failed to create constitution version');
    }
    return result.rows[0];
  }

  /**
   * Activate a constitution version
   */
  async activateVersion(versionId: string, traceId?: string): Promise<ConstitutionVersion> {
    // Verify version exists
    const versionResult = await db.query(
      `SELECT * FROM calibration_constitution_versions WHERE id = $1`,
      [versionId]
    );

    if (versionResult.rows.length === 0) {
      throw new Error(`Constitution version ${versionId} not found`);
    }

    // Insert new active constitution entry (immutable history)
    await db.query(
      `INSERT INTO active_constitution (constitution_version_id) VALUES ($1)`,
      [versionId]
    );

    return versionResult.rows[0];
  }

  /**
   * Retire a constitution version
   */
  async retireVersion(versionId: string, traceId?: string): Promise<ConstitutionVersion> {
    const result = await db.query(
      `UPDATE calibration_constitution_versions
       SET retired_at = NOW()
       WHERE id = $1 AND is_active = false
       RETURNING *`,
      [versionId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Cannot retire active constitution version`);
    }

    return result.rows[0];
  }

  /**
   * Get the currently active constitution
   */
  async getActive(): Promise<ConstitutionVersion | null> {
    const result = await db.query(
      `SELECT ccv.* FROM calibration_constitution_versions ccv
       INNER JOIN active_constitution ac ON ac.constitution_version_id = ccv.id
       ORDER BY ac.activated_at DESC
       LIMIT 1`
    );

    return result.rows[0] || null;
  }

  /**
   * Get constitution by ID
   */
  async getById(versionId: string): Promise<ConstitutionVersion | null> {
    const result = await db.query(
      `SELECT * FROM calibration_constitution_versions WHERE id = $1`,
      [versionId]
    );

    return result.rows[0] || null;
  }

  /**
   * List all constitution versions
   */
  async listVersions(limit: number = 20, offset: number = 0): Promise<ConstitutionVersion[]> {
    const result = await db.query(
      `SELECT * FROM calibration_constitution_versions
       ORDER BY created_at DESC
       LIMIT $1 OFFSET $2`,
      [limit, offset]
    );

    return result.rows;
  }

  /**
   * Verify integrity of a constitution version
   */
  async verifyIntegrity(versionId: string): Promise<boolean> {
    const version = await this.getById(versionId);
    if (!version) {
      throw new Error(`Constitution version ${versionId} not found`);
    }

    const computedHash = this.hashContent(version.content_json);
    return computedHash === version.content_hash;
  }

  /**
   * Add a protected surface definition to the active constitution
   */
  async addProtectedSurface(
    surface: Omit<ProtectedSurface, 'id'>
  ): Promise<ProtectedSurface> {
    const activeConstitution = await this.getActive();
    if (!activeConstitution) {
      throw new Error('No active constitution found');
    }

    const result = await db.query(
      `INSERT INTO protected_surfaces (
        constitution_id, surface_name, surface_type, description,
        table_names, column_patterns, function_patterns,
        is_immutable, requires_constitution_vote
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
      RETURNING *`,
      [
        activeConstitution.id,
        surface.surface_name,
        surface.surface_type,
        surface.description || null,
        surface.table_names,
        surface.column_patterns,
        surface.function_patterns,
        surface.is_immutable,
        surface.requires_constitution_vote
      ]
    );

    if (result.rows.length === 0) {
      throw new Error('Failed to add protected surface');
    }
    return result.rows[0];
  }

  /**
   * Get all protected surfaces for active constitution
   */
  async getProtectedSurfaces(): Promise<ProtectedSurface[]> {
    const activeConstitution = await this.getActive();
    if (!activeConstitution) {
      throw new Error('No active constitution found');
    }

    const result = await db.query(
      `SELECT * FROM protected_surfaces WHERE constitution_id = $1 AND is_immutable = true`,
      [activeConstitution.id]
    );

    return result.rows;
  }

  /**
   * Add an allowed change type
   */
  async addAllowedChangeType(
    changeType: Omit<AllowedChangeType, 'id'>
  ): Promise<AllowedChangeType> {
    const activeConstitution = await this.getActive();
    if (!activeConstitution) {
      throw new Error('No active constitution found');
    }

    const result = await db.query(
      `INSERT INTO allowed_change_types (
        constitution_id, change_type_name, description, category,
        max_scope, requires_eval, can_be_canaried
      ) VALUES ($1, $2, $3, $4, $5, $6, $7)
      RETURNING *`,
      [
        activeConstitution.id,
        changeType.change_type_name,
        changeType.description || null,
        changeType.category,
        changeType.max_scope,
        changeType.requires_eval,
        changeType.can_be_canaried
      ]
    );

    if (result.rows.length === 0) {
      throw new Error('Failed to add allowed change type');
    }
    return result.rows[0];
  }

  /**
   * Add a prohibited change type
   */
  async addProhibitedChangeType(
    changeTypeName: string,
    reason: string
  ): Promise<{ id: string; change_type_name: string; reason: string }> {
    const activeConstitution = await this.getActive();
    if (!activeConstitution) {
      throw new Error('No active constitution found');
    }

    const result = await db.query(
      `INSERT INTO prohibited_change_types (
        constitution_id, change_type_name, reason
      ) VALUES ($1, $2, $3)
      RETURNING *`,
      [activeConstitution.id, changeTypeName, reason]
    );

    if (result.rows.length === 0) {
      throw new Error('Failed to add prohibited change type');
    }
    return result.rows[0];
  }

  /**
   * Validate a proposed change against the active constitution
   */
  async validateChange(
    changeType: string,
    affectedTables: string[],
    affectedColumns: string[],
    traceId?: string
  ): Promise<VerificationResult> {
    const activeConstitution = await this.getActive();
    if (!activeConstitution) {
      throw new Error('No active constitution found');
    }

    const violations: string[] = [];
    const protectedSurfacesTouched: ProtectedSurface[] = [];

    // 1. Check if change type is prohibited
    const prohibitedResult = await db.query(
      `SELECT * FROM prohibited_change_types
       WHERE constitution_id = $1 AND change_type_name = $2`,
      [activeConstitution.id, changeType]
    );

    if (prohibitedResult.rows.length > 0) {
      violations.push(
        `Change type '${changeType}' is prohibited: ${prohibitedResult.rows[0].reason}`
      );
    }

    // 2. Check if change type is allowed
    const allowedResult = await db.query(
      `SELECT * FROM allowed_change_types
       WHERE constitution_id = $1 AND change_type_name = $2`,
      [activeConstitution.id, changeType]
    );

    if (allowedResult.rows.length === 0 && prohibitedResult.rows.length === 0) {
      violations.push(`Change type '${changeType}' is not in the constitution`);
    }

    // 3. Check protected surfaces
    const surfaceResult = await db.query(
      `SELECT * FROM protected_surfaces
       WHERE constitution_id = $1 AND is_immutable = true`,
      [activeConstitution.id]
    );

    for (const surface of surfaceResult.rows) {
      let touched = false;

      // Check tables
      for (const table of surface.table_names || []) {
        if (affectedTables.includes(table)) {
          touched = true;
          break;
        }
      }

      // Check columns
      if (!touched) {
        for (const pattern of surface.column_patterns || []) {
          for (const col of affectedColumns) {
            const regex = new RegExp(pattern);
            if (regex.test(col)) {
              touched = true;
              break;
            }
          }
          if (touched) break;
        }
      }

      if (touched) {
        protectedSurfacesTouched.push(surface);
        violations.push(
          `Protected surface '${surface.surface_name}' would be modified (immutable)`
        );
      }
    }

    // Record verification
    await db.query(
      `INSERT INTO constitution_verifications (
        constitution_id, verification_result, violations, is_compliant, trace_id
      ) VALUES ($1, $2, $3, $4, $5)`,
      [
        activeConstitution.id,
        violations.length === 0 ? 'COMPLIANT' : 'VIOLATIONS',
        violations,
        violations.length === 0,
        traceId || null
      ]
    );

    return {
      is_compliant: violations.length === 0,
      violations,
      protected_surfaces_touched: protectedSurfacesTouched,
      requires_override: protectedSurfacesTouched.length > 0
    };
  }

  /**
   * Initialize the default constitution with standard definitions
   */
  async initializeDefaultConstitution(signerEntityId: string): Promise<ConstitutionVersion> {
    const defaultContent = {
      name: 'Default Calibration Constitution',
      version: 1,
      effective_date: new Date().toISOString(),
      principles: [
        'Civilization can propose trust-policy changes',
        'Civilization cannot directly modify calibration scoring code',
        'Civilization cannot modify resolver internals',
        'Civilization cannot modify sealed ground-truth data',
        'Civilization cannot modify audit logs',
        'Civilization cannot bypass evaluation gates',
        'Civilization cannot bypass RBAC enforcement'
      ],
      protected_surfaces_count: 7,
      allowed_change_types_count: 12,
      prohibited_change_types_count: 7
    };

    const version = await this.createVersion(
      defaultContent,
      signerEntityId,
      this.signContent(defaultContent)
    );

    // Immediately activate it
    await this.activateVersion(version.id);

    // Add default protected surfaces
    const protectedSurfaces: Omit<ProtectedSurface, 'id'>[] = [
      {
        surface_name: 'Calibration Scoring Code',
        surface_type: 'function',
        description: 'Core calibration score computation functions',
        table_names: [],
        column_patterns: [],
        function_patterns: ['calibrate_.*', 'compute_score_.*'],
        is_immutable: true,
        requires_constitution_vote: true
      },
      {
        surface_name: 'Resolver Internals',
        surface_type: 'function',
        description: 'Resolution engine implementation',
        table_names: ['resolution_engine_state'],
        column_patterns: [],
        function_patterns: ['resolve_.*', 'dispatch_.*'],
        is_immutable: true,
        requires_constitution_vote: true
      },
      {
        surface_name: 'Ground Truth Data',
        surface_type: 'table',
        description: 'Sealed reference data for evaluations',
        table_names: ['eval_ground_truth'],
        column_patterns: [],
        function_patterns: [],
        is_immutable: true,
        requires_constitution_vote: true
      },
      {
        surface_name: 'Audit Logs',
        surface_type: 'table',
        description: 'Immutable audit trail',
        table_names: ['trace_audit_events'],
        column_patterns: [],
        function_patterns: [],
        is_immutable: true,
        requires_constitution_vote: true
      },
      {
        surface_name: 'RBAC Enforcement',
        surface_type: 'function',
        description: 'Role-based access control logic',
        table_names: ['roles', 'permission_grants'],
        column_patterns: [],
        function_patterns: ['check_permission_.*', 'enforce_rbac'],
        is_immutable: true,
        requires_constitution_vote: true
      },
      {
        surface_name: 'Evaluation Thresholds',
        surface_type: 'table',
        description: 'Gate thresholds for promotions',
        table_names: ['eval_gate_thresholds'],
        column_patterns: [],
        function_patterns: [],
        is_immutable: true,
        requires_constitution_vote: true
      },
      {
        surface_name: 'Migration Integrity',
        surface_type: 'function',
        description: 'Database schema integrity',
        table_names: ['schema_migrations'],
        column_patterns: [],
        function_patterns: ['apply_migration', 'validate_schema'],
        is_immutable: true,
        requires_constitution_vote: true
      }
    ];

    for (const surface of protectedSurfaces) {
      await db.query(
        `INSERT INTO protected_surfaces (
          constitution_id, surface_name, surface_type, description,
          table_names, column_patterns, function_patterns,
          is_immutable, requires_constitution_vote
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
        [
          version.id,
          surface.surface_name,
          surface.surface_type,
          surface.description || null,
          surface.table_names,
          surface.column_patterns,
          surface.function_patterns,
          surface.is_immutable,
          surface.requires_constitution_vote
        ]
      );
    }

    // Add default allowed change types
    const allowedChangeTypes: Omit<AllowedChangeType, 'id'>[] = [
      {
        change_type_name: 'adjust_confidence_discount',
        description: 'Adjust calibration confidence discount factor',
        category: 'calibration',
        max_scope: 'civilization',
        requires_eval: true,
        can_be_canaried: true
      },
      {
        change_type_name: 'raise_evidence_standard',
        description: 'Increase minimum evidence quality required',
        category: 'calibration',
        max_scope: 'civilization',
        requires_eval: true,
        can_be_canaried: true
      },
      {
        change_type_name: 'lower_evidence_standard',
        description: 'Decrease minimum evidence quality required',
        category: 'calibration',
        max_scope: 'civilization',
        requires_eval: true,
        can_be_canaried: true
      },
      {
        change_type_name: 'adjust_reputation_weight',
        description: 'Adjust how much reputation affects trust scores',
        category: 'calibration',
        max_scope: 'civilization',
        requires_eval: true,
        can_be_canaried: true
      },
      {
        change_type_name: 'update_thresholds',
        description: 'Update decision thresholds',
        category: 'governance',
        max_scope: 'civilization',
        requires_eval: true,
        can_be_canaried: true
      },
      {
        change_type_name: 'update_dispute_rules',
        description: 'Update society-level dispute resolution rules',
        category: 'governance',
        max_scope: 'society',
        requires_eval: true,
        can_be_canaried: false
      },
      {
        change_type_name: 'add_eval_case',
        description: 'Add new evaluation test case',
        category: 'evaluation',
        max_scope: 'institution',
        requires_eval: false,
        can_be_canaried: true
      },
      {
        change_type_name: 'retire_bad_policy',
        description: 'Retire a trust policy that failed',
        category: 'governance',
        max_scope: 'civilization',
        requires_eval: false,
        can_be_canaried: false
      },
      {
        change_type_name: 'emergency_freeze',
        description: 'Activate emergency trust freeze',
        category: 'emergency',
        max_scope: 'civilization',
        requires_eval: false,
        can_be_canaried: false
      },
      {
        change_type_name: 'update_trust_decay_rate',
        description: 'Adjust how quickly trust reputation decays',
        category: 'calibration',
        max_scope: 'civilization',
        requires_eval: true,
        can_be_canaried: true
      },
      {
        change_type_name: 'update_simulation_discount',
        description: 'Adjust discount applied to simulation-derived trust',
        category: 'calibration',
        max_scope: 'civilization',
        requires_eval: true,
        can_be_canaried: true
      },
      {
        change_type_name: 'update_dispute_escalation_threshold',
        description: 'Update when disputes escalate to civilization',
        category: 'governance',
        max_scope: 'society',
        requires_eval: true,
        can_be_canaried: false
      }
    ];

    for (const changeType of allowedChangeTypes) {
      await db.query(
        `INSERT INTO allowed_change_types (
          constitution_id, change_type_name, description, category,
          max_scope, requires_eval, can_be_canaried
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)`,
        [
          version.id,
          changeType.change_type_name,
          changeType.description || null,
          changeType.category,
          changeType.max_scope,
          changeType.requires_eval,
          changeType.can_be_canaried
        ]
      );
    }

    // Add prohibited change types
    const prohibitedChangeTypes = [
      ['modify_ground_truth', 'Ground truth data is sealed and immutable'],
      ['modify_resolver_logic', 'Resolver internals are protected from modification'],
      ['modify_calibration_score_code', 'Core calibration scoring functions are immutable'],
      ['edit_calibration_history', 'Historical calibration decisions cannot be rewritten'],
      ['delete_audit_events', 'Audit events are immutable and cannot be deleted'],
      ['bypass_eval_gate', 'Evaluation gates cannot be bypassed'],
      ['bypass_rbac', 'RBAC enforcement cannot be bypassed']
    ];

    for (const [typeName, reason] of prohibitedChangeTypes) {
      await db.query(
        `INSERT INTO prohibited_change_types (
          constitution_id, change_type_name, reason
        ) VALUES ($1, $2, $3)`,
        [version.id, typeName, reason]
      );
    }

    return version;
  }

  /**
   * Hash content for integrity verification
   */
  private hashContent(content: Record<string, any>): string {
    const jsonString = JSON.stringify(content);
    return createHash('sha256').update(jsonString).digest('hex');
  }

  /**
   * Sign content (simple signature for now, would be PKI in production)
   */
  private signContent(content: Record<string, any>): string {
    const hash = this.hashContent(content);
    return `sig_${hash.substring(0, 32)}`;
  }
}

export const calibrationConstitutionService = new CalibrationConstitutionService();
