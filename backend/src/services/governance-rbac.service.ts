import { db } from '../db/client';
import { v4 as uuidv4 } from 'uuid';

export interface GovernanceRole {
  id: string;
  role_name: string;
  display_name: string;
  description?: string;
  permission_level: number;
  created_at: Date;
}

export interface GovernancePermission {
  id: string;
  permission_name: string;
  description?: string;
  resource: string;
  action: string;
  created_at: Date;
}

export interface EntityRoleAssignment {
  id: string;
  entity_id: string;
  entity_type: string;
  role_id: string;
  assigned_by?: string;
  assigned_at: Date;
  revoked_at?: Date;
}

export class GovernanceRBACService {
  /**
   * Check if an entity has a specific permission
   */
  async hasPermission(entityId: string, permissionName: string): Promise<boolean> {
    try {
      const result = await db.query(
        `SELECT has_permission($1::TEXT, $2::TEXT) as has_perm`,
        [entityId, permissionName]
      );
      return result.rows[0]?.has_perm || false;
    } catch (error) {
      console.error(`Error checking permission: ${error}`);
      return false;
    }
  }

  /**
   * Get all roles assigned to an entity
   */
  async getEntityRoles(entityId: string): Promise<GovernanceRole[]> {
    try {
      const result = await db.query(
        `SELECT * FROM get_entity_roles($1::TEXT) ORDER BY permission_level DESC`,
        [entityId]
      );
      return result.rows;
    } catch (error) {
      console.error(`Error getting entity roles: ${error}`);
      return [];
    }
  }

  /**
   * Assign a role to an entity
   */
  async assignRole(
    entityId: string,
    entityType: string,
    roleName: string,
    assignedBy?: string,
    traceId?: string
  ): Promise<EntityRoleAssignment> {
    try {
      // Get role by name
      const roleResult = await db.query(
        `SELECT id FROM governance_roles WHERE role_name = $1`,
        [roleName]
      );

      if (roleResult.rows.length === 0) {
        throw new Error(`Role not found: ${roleName}`);
      }

      const roleId = roleResult.rows[0].id;

      // Assign role
      const result = await db.query(
        `INSERT INTO governance_entity_roles (entity_id, entity_type, role_id, assigned_by)
         VALUES ($1, $2, $3, $4)
         ON CONFLICT (entity_id, role_id) DO UPDATE
         SET revoked_at = NULL, assigned_by = $4
         RETURNING *`,
        [entityId, entityType, roleId, assignedBy || null]
      );

      // Audit the assignment
      await db.query(
        `INSERT INTO governance_rbac_audit (
          actor_entity_id, action, resource, permission_granted,
          required_permission, trace_id
        ) VALUES ($1, $2, $3, $4, $5, $6)`,
        [
          assignedBy || 'system',
          'ASSIGN_ROLE',
          entityId,
          true,
          'governance.assign_roles',
          traceId || null,
        ]
      );

      return result.rows[0];
    } catch (error: any) {
      throw new Error(`Failed to assign role: ${error.message}`);
    }
  }

  /**
   * Revoke a role from an entity
   */
  async revokeRole(entityId: string, roleName: string, revokedBy?: string, traceId?: string): Promise<void> {
    try {
      // Get role by name
      const roleResult = await db.query(
        `SELECT id FROM governance_roles WHERE role_name = $1`,
        [roleName]
      );

      if (roleResult.rows.length === 0) {
        throw new Error(`Role not found: ${roleName}`);
      }

      const roleId = roleResult.rows[0].id;

      // Revoke role (soft delete with revoked_at timestamp)
      await db.query(
        `UPDATE governance_entity_roles
         SET revoked_at = NOW()
         WHERE entity_id = $1 AND role_id = $2 AND revoked_at IS NULL`,
        [entityId, roleId]
      );

      // Audit the revocation
      await db.query(
        `INSERT INTO governance_rbac_audit (
          actor_entity_id, action, resource, permission_granted,
          required_permission, trace_id
        ) VALUES ($1, $2, $3, $4, $5, $6)`,
        [
          revokedBy || 'system',
          'REVOKE_ROLE',
          entityId,
          true,
          'governance.assign_roles',
          traceId || null,
        ]
      );
    } catch (error: any) {
      throw new Error(`Failed to revoke role: ${error.message}`);
    }
  }

  /**
   * Check if entity has minimum permission level (1-5)
   * Higher number = more permissions
   */
  async checkPermissionLevel(entityId: string, minimumLevel: number): Promise<boolean> {
    try {
      const result = await db.query(
        `SELECT MAX(r.permission_level) as max_level
         FROM governance_entity_roles er
         JOIN governance_roles r ON er.role_id = r.id
         WHERE er.entity_id = $1 AND er.revoked_at IS NULL`,
        [entityId]
      );

      const maxLevel = result.rows[0]?.max_level || 0;
      return maxLevel >= minimumLevel;
    } catch (error) {
      console.error(`Error checking permission level: ${error}`);
      return false;
    }
  }

  /**
   * Audit an RBAC check (for logging who tried what)
   */
  async auditRBACCheck(
    actorEntityId: string,
    action: string,
    resource: string,
    permissionGranted: boolean,
    requiredPermission?: string,
    reasonDenied?: string,
    traceId?: string
  ): Promise<string> {
    try {
      const result = await db.query(
        `SELECT audit_rbac_check($1, $2, $3, $4, $5, $6, $7) as audit_id`,
        [actorEntityId, action, resource, permissionGranted, requiredPermission || null, reasonDenied || null, traceId || null]
      );

      return result.rows[0]?.audit_id || '';
    } catch (error: any) {
      console.error(`Error auditing RBAC check: ${error.message}`);
      return '';
    }
  }

  /**
   * Get RBAC audit trail
   */
  async getAuditTrail(
    actorEntityId?: string,
    action?: string,
    limit: number = 100,
    offset: number = 0
  ): Promise<any[]> {
    try {
      let query = `SELECT * FROM governance_rbac_audit WHERE 1=1`;
      const params: any[] = [];

      if (actorEntityId) {
        query += ` AND actor_entity_id = $${params.length + 1}`;
        params.push(actorEntityId);
      }

      if (action) {
        query += ` AND action = $${params.length + 1}`;
        params.push(action);
      }

      query += ` ORDER BY created_at DESC LIMIT $${params.length + 1} OFFSET $${params.length + 2}`;
      params.push(limit, offset);

      const result = await db.query(query, params);
      return result.rows;
    } catch (error: any) {
      console.error(`Error getting audit trail: ${error.message}`);
      return [];
    }
  }

  /**
   * Get all roles in the system
   */
  async getAllRoles(): Promise<GovernanceRole[]> {
    try {
      const result = await db.query(
        `SELECT * FROM governance_roles ORDER BY permission_level ASC`
      );
      return result.rows;
    } catch (error) {
      console.error(`Error getting roles: ${error}`);
      return [];
    }
  }

  /**
   * Get all permissions in the system
   */
  async getAllPermissions(): Promise<GovernancePermission[]> {
    try {
      const result = await db.query(
        `SELECT * FROM governance_permissions ORDER BY resource, action`
      );
      return result.rows;
    } catch (error) {
      console.error(`Error getting permissions: ${error}`);
      return [];
    }
  }

  /**
   * Bootstrap default role assignments (for testing/setup)
   */
  async bootstrapDefaultRoles(): Promise<void> {
    try {
      // Assign system entities to appropriate roles
      const systemRoles = [
        { entity: 'autonomy_orchestrator', role: 'governance_operator' },
        { entity: 'eval_harness', role: 'governance_reviewer' },
        { entity: 'self_mod_validator', role: 'governance_approver' },
        { entity: 'system_admin', role: 'governance_admin' },
      ];

      for (const { entity, role } of systemRoles) {
        await this.assignRole(entity, 'service', role, 'system_bootstrap');
      }

      console.log('[RBAC] Bootstrap: default role assignments created');
    } catch (error: any) {
      console.error(`Error bootstrapping roles: ${error.message}`);
    }
  }
}

export const governanceRBACService = new GovernanceRBACService();
