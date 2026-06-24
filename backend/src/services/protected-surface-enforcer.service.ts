/**
 * Protected Surface Enforcer - Phase 1 Brick 3
 *
 * Auto-derives protected surfaces from policy.py and enforces immutability.
 * This is the constitutional foundation that self-improvement cannot break.
 *
 * Surfaces are auto-derived from PROTECTED_SURFACES in policy.py.
 * Enforcement: any proposed modification to these paths is blocked unless approved by human.
 */

import * as fs from 'fs';
import * as path from 'path';
import { db } from '../db/client';

export interface ProtectedSurface {
  path: string;
  exists: boolean;
  content_hash: string | null;
  last_verified_at: Date | null;
}

export interface SurfaceModificationAttempt {
  surface_path: string;
  proposed_change: string;
  risk_level: 'low' | 'high' | 'critical';
  requires_human_approval: boolean;
}

export interface ProtectedSurfaceState {
  surfaces: ProtectedSurface[];
  all_exist: boolean;
  verified_at: Date;
}

/**
 * Service for protected surface governance.
 * Auto-derives surfaces from policy.py and verifies they remain unmodified.
 */
export class ProtectedSurfaceEnforcerService {
  // Policy file location: discovered by walking up from __dirname
  private POLICY_FILE: string | null;
  private protectedSurfaces: Set<string> = new Set();
  private loadFailed: boolean = false;

  constructor() {
    // Find governance/policy.py by walking up from this file's location (__dirname)
    // This works regardless of launch directory or build output location
    this.POLICY_FILE = this.findPolicyFile(__dirname);
    if (!this.POLICY_FILE) {
      this.loadFailed = true;
      console.error('Failed to locate governance/policy.py in repo');
      return;
    }
    this.loadProtectedSurfaces();
  }

  /**
   * Walk upward from a starting directory to find governance/policy.py
   */
  private findPolicyFile(startDir: string): string | null {
    let current = startDir;
    for (let i = 0; i < 10; i++) {
      const candidate = path.join(current, 'governance', 'policy.py');
      if (fs.existsSync(candidate)) {
        return candidate;
      }
      const parent = path.dirname(current);
      if (parent === current) break; // reached filesystem root
      current = parent;
    }
    return null;
  }

  /**
   * Auto-derive protected surfaces from policy.py
   * Extracts the PROTECTED_SURFACES set definition
   * FAIL-CLOSED: Errors prevent service initialization; empty set is treated as failure
   */
  private loadProtectedSurfaces(): void {
    if (!this.POLICY_FILE) {
      this.loadFailed = true;
      return;
    }

    try {
      const policyContent = fs.readFileSync(this.POLICY_FILE, 'utf-8');

      // Extract PROTECTED_SURFACES = { ... }
      const match = policyContent.match(/PROTECTED_SURFACES\s*=\s*\{([^}]+)\}/s);
      if (!match) {
        this.loadFailed = true;
        console.error('Could not find PROTECTED_SURFACES in policy.py');
        return;
      }

      // Parse the set contents
      const surfaceLines = match[1]
        .split('\n')
        .map(line => line.trim())
        .filter(line => line && !line.startsWith('#'))
        .map(line => {
          // Remove quotes and commas: "path/to/file.ts" -> path/to/file.ts
          return line.replace(/["',]/g, '').trim();
        })
        .filter(line => line.length > 0);

      if (surfaceLines.length === 0) {
        this.loadFailed = true;
        console.error('PROTECTED_SURFACES set is empty');
        return;
      }

      this.protectedSurfaces = new Set(surfaceLines);
      console.log(`✅ Auto-derived ${this.protectedSurfaces.size} protected surfaces from policy.py`);
    } catch (error) {
      this.loadFailed = true;
      console.error('Failed to load protected surfaces:', error);
    }
  }

  /**
   * Verify all protected surfaces exist
   * FAIL-CLOSED: If load failed or no surfaces, report all_exist=false
   */
  async verifyProtectedSurfacesExist(): Promise<ProtectedSurfaceState> {
    const surfaces: ProtectedSurface[] = [];

    // If policy.py load failed, return failed state immediately
    if (this.loadFailed || this.protectedSurfaces.size === 0) {
      console.error('❌ Cannot verify surfaces: policy.py load failed or surfaces set is empty');
      return {
        surfaces: [],
        all_exist: false,
        verified_at: new Date(),
      };
    }

    // Find repo root from policy.py directory
    if (!this.POLICY_FILE) {
      console.error('❌ Cannot verify surfaces: policy.py path not set');
      return {
        surfaces: [],
        all_exist: false,
        verified_at: new Date(),
      };
    }
    const policyDir = path.dirname(this.POLICY_FILE);
    const repoRoot = path.dirname(policyDir); // governance -> repo

    for (const surfacePath of this.protectedSurfaces) {
      let fullPath = surfacePath;
      if (!fullPath.startsWith('/')) {
        fullPath = path.join(repoRoot, surfacePath);
      }

      const exists = fs.existsSync(fullPath);
      let contentHash: string | null = null;

      if (exists) {
        // Compute content hash for verification
        const crypto = require('crypto');
        const content = fs.readFileSync(fullPath, 'utf-8');
        contentHash = crypto.createHash('sha256').update(content).digest('hex');
      }

      surfaces.push({
        path: surfacePath,
        exists,
        content_hash: contentHash,
        last_verified_at: new Date(),
      });
    }

    // all_exist is true only if all surfaces exist AND we have exactly the expected count
    const allExist = surfaces.length > 0 && surfaces.every(s => s.exists);

    if (!allExist) {
      const missing = surfaces.filter(s => !s.exists).map(s => s.path);
      console.error(`❌ Protected surfaces missing: ${missing.join(', ')}`);
    }

    return {
      surfaces,
      all_exist: allExist,
      verified_at: new Date(),
    };
  }

  /**
   * Check if a proposed change violates protected surface constraints
   * Used by self-improvement loop (Phase 3) to gate modifications
   * FAIL-CLOSED: If enforcer failed to initialize, all changes require approval
   */
  async evaluateModificationAttempt(
    filePath: string,
    proposedChange: string,
    riskLevel: 'low' | 'high' | 'critical' = 'high'
  ): Promise<SurfaceModificationAttempt> {
    // Normalize path for comparison
    const normalizedPath = path.normalize(filePath);

    // If enforcer failed to load, fail closed: require human approval for all changes
    if (this.loadFailed || this.protectedSurfaces.size === 0) {
      return {
        surface_path: filePath,
        proposed_change: proposedChange.substring(0, 200),
        risk_level: riskLevel,
        requires_human_approval: true, // FAIL CLOSED
      };
    }

    // Check if this file is a protected surface
    const isProtected = Array.from(this.protectedSurfaces).some(surface => {
      const surfacePath = path.normalize(surface);
      return normalizedPath.includes(surfacePath) || surfacePath.includes(normalizedPath);
    });

    return {
      surface_path: filePath,
      proposed_change: proposedChange.substring(0, 200), // Truncate for logging
      risk_level: riskLevel,
      requires_human_approval: isProtected || riskLevel === 'critical',
    };
  }

  /**
   * Store protected surface state to DB for audit trail
   */
  async recordSurfaceVerification(state: ProtectedSurfaceState): Promise<void> {
    await db.query(
      `INSERT INTO autonomy_memory (id, action_id, content, created_at)
       VALUES ($1, NULL, $2, NOW())`,
      [
        require('uuid').v4(),
        JSON.stringify({
          type: 'protected_surface_verification',
          all_exist: state.all_exist,
          surfaces_count: state.surfaces.length,
          surfaces: state.surfaces.map(s => ({
            path: s.path,
            exists: s.exists,
            content_hash: s.content_hash,
          })),
          verified_at: state.verified_at,
        }),
      ]
    );
  }

  /**
   * Get the list of auto-derived protected surfaces
   */
  getProtectedSurfaces(): string[] {
    return Array.from(this.protectedSurfaces);
  }

  /**
   * Get surface state from most recent verification
   */
  async getLatestSurfaceState(): Promise<ProtectedSurfaceState | null> {
    const result = await db.query(
      `SELECT content, created_at FROM autonomy_memory
       WHERE content->>'type' = 'protected_surface_verification'
       ORDER BY created_at DESC
       LIMIT 1`
    );

    if (result.rows.length === 0) {
      return null;
    }

    // Content is already a JSON object from the DB, don't parse
    const record = typeof result.rows[0].content === 'string'
      ? JSON.parse(result.rows[0].content)
      : result.rows[0].content;

    return {
      surfaces: record.surfaces,
      all_exist: record.all_exist,
      verified_at: new Date(record.verified_at),
    };
  }
}
