/**
 * Invariant Validator Service
 *
 * Hand-authored invariant checks for data-row guarantees.
 * Enforces system invariants that are non-negotiable for evidence-governed operation.
 *
 * Invariants checked:
 * 1. Evidence-backed claims: Every claim must reference existing evidence sources
 * 2. Confidence bounds: All confidences in [0, 1]
 * 3. Model decisions: All model calls must be logged with outcome
 * 4. Source integrity: All sources must have content_hash and source_type
 * 5. (UNIMPLEMENTED) No circular evidence: Evidence chains must be acyclic
 * 6. (UNIMPLEMENTED) Goal acyclicity: Goal hierarchies cannot have cycles
 */

import { db } from '../db/client';

export interface InvariantViolation {
  invariant: string;
  severity: 'fatal' | 'warning';
  entity_type: string;
  entity_id: string;
  violation_description: string;
  suggested_fix: string;
}

export interface ValidationResult {
  passed: boolean;
  violations: InvariantViolation[];
  timestamp: Date;
  checked_tables: string[];
}

/**
 * Validates system invariants continuously
 * Acts as a gatekeeper before data is persisted
 */
export class InvariantValidatorService {
  /**
   * Validate a claim before it's persisted
   * Invariant: Claims must have at least one evidence source
   */
  async validateClaimBeforePersist(claimData: {
    text: string;
    support_source_ids: string[];
    confidence?: number;
  }): Promise<{ valid: boolean; errors: string[] }> {
    const errors: string[] = [];

    // Invariant 1: Evidence-backed claims
    if (!claimData.support_source_ids || claimData.support_source_ids.length === 0) {
      errors.push('Invariant violation: Claims must reference at least one evidence source');
    } else {
      // Verify that all referenced sources exist
      const sourceIds = claimData.support_source_ids;
      const result = await db.query(
        `SELECT COUNT(*) as count FROM autonomy_evidence WHERE id = ANY($1)`,
        [sourceIds]
      );

      const foundCount = result.rows[0].count;
      if (foundCount !== sourceIds.length) {
        errors.push(
          `Invariant violation: ${sourceIds.length - foundCount} referenced sources do not exist in autonomy_evidence`
        );
      }
    }

    // Invariant 3: Confidence bounds
    if (claimData.confidence !== undefined) {
      if (claimData.confidence < 0 || claimData.confidence > 1) {
        errors.push(`Invariant violation: Confidence must be in [0, 1], got ${claimData.confidence}`);
      }
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Validate evidence source before persistence
   * Invariant: All sources must have content_hash and source_type
   */
  async validateEvidenceBeforePersist(evidenceData: {
    url: string;
    content_hash?: string;
    source_type?: string;
    is_public_access?: boolean;
  }): Promise<{ valid: boolean; errors: string[] }> {
    const errors: string[] = [];

    // Invariant 6: Source integrity
    if (!evidenceData.content_hash) {
      errors.push('Invariant violation: Evidence must have content_hash');
    }

    if (!evidenceData.source_type) {
      errors.push('Invariant violation: Evidence must have source_type (e.g., "web", "pdf", "api")');
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Validate model decision before logging
   * Invariant: All model calls must eventually have outcome recorded
   */
  async validateModelDecisionBeforePersist(decisionData: {
    decision_id: string;
    model_code: string;
    provider: string;
  }): Promise<{ valid: boolean; errors: string[] }> {
    const errors: string[] = [];

    // Invariant 4: Confidence bounds
    // (Model code and provider are simple strings; validate format)
    if (!decisionData.model_code || decisionData.model_code.trim().length === 0) {
      errors.push('Invariant violation: Model decision must have model_code');
    }

    if (!decisionData.provider || decisionData.provider.trim().length === 0) {
      errors.push('Invariant violation: Model decision must have provider');
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * TODO: Check for circular evidence dependencies (UNIMPLEMENTED)
   * Invariant: Evidence chains must be acyclic
   *
   * Current implementation was flawed (detects depth > 4, not actual cycles).
   * Proper implementation deferred — requires full graph traversal and confirmation
   * that derived_from_claim_ids column exists and is populated correctly.
   */
  async checkForEvidenceCircles(): Promise<{ valid: boolean; cycles: string[][] }> {
    // NOT IMPLEMENTED - placeholder returns no cycles
    // Proper cycle detection deferred to Phase 3 (when self-improvement needs it)
    return {
      valid: true,
      cycles: [],
    };
  }

  /**
   * Full system validation
   * Check all critical invariants across the system
   */
  async validateSystemInvariants(): Promise<ValidationResult> {
    const violations: InvariantViolation[] = [];
    const checkedTables: string[] = [];

    // Check 1: Claims without evidence
    const claimsWithoutEvidence = await db.query(
      `SELECT id, text FROM autonomy_claims
       WHERE support_source_ids IS NULL OR support_source_ids::text = '[]'`
    );

    for (const row of claimsWithoutEvidence.rows) {
      violations.push({
        invariant: 'evidence_backed_claims',
        severity: 'fatal',
        entity_type: 'autonomy_claims',
        entity_id: row.id,
        violation_description: `Claim "${row.text.substring(0, 50)}..." has no evidence sources`,
        suggested_fix: 'Add support_source_ids before persisting claim',
      });
    }

    checkedTables.push('autonomy_claims');

    // Check 2: Confidence bounds
    const badConfidences = await db.query(
      `SELECT id FROM autonomy_claims
       WHERE confidence IS NOT NULL AND (confidence < 0 OR confidence > 1)`
    );

    for (const row of badConfidences.rows) {
      violations.push({
        invariant: 'confidence_bounds',
        severity: 'fatal',
        entity_type: 'autonomy_claims',
        entity_id: row.id,
        violation_description: 'Confidence value outside [0, 1]',
        suggested_fix: 'Clamp confidence to [0, 1]',
      });
    }

    // Check 3: Evidence integrity
    const badEvidence = await db.query(
      `SELECT id, url FROM autonomy_evidence
       WHERE content_hash IS NULL OR source_type IS NULL`
    );

    for (const row of badEvidence.rows) {
      violations.push({
        invariant: 'source_integrity',
        severity: 'warning',
        entity_type: 'autonomy_evidence',
        entity_id: row.id,
        violation_description: `Evidence ${row.url} missing content_hash or source_type`,
        suggested_fix: 'Populate content_hash and source_type before referencing',
      });
    }

    checkedTables.push('autonomy_evidence');

    // Check 4: Model decisions with outcomes
    const incompleteDecisions = await db.query(
      `SELECT decision_id FROM model_decision_ledger
       WHERE success IS NULL AND created_at < NOW() - INTERVAL '1 hour'`
    );

    for (const row of incompleteDecisions.rows) {
      violations.push({
        invariant: 'model_decision_outcome',
        severity: 'warning',
        entity_type: 'model_decision_ledger',
        entity_id: row.decision_id,
        violation_description: 'Model decision unresolved after 1 hour',
        suggested_fix: 'Ensure updateDecisionOutcome() is called after API response',
      });
    }

    checkedTables.push('model_decision_ledger');

    return {
      passed: violations.length === 0,
      violations,
      timestamp: new Date(),
      checked_tables: checkedTables,
    };
  }

  /**
   * Log an invariant violation for audit trail
   */
  async logViolation(violation: InvariantViolation): Promise<void> {
    await db.query(
      `INSERT INTO autonomy_memory (id, action_id, content, created_at)
       VALUES ($1, NULL, $2, NOW())`,
      [
        require('uuid').v4(),
        JSON.stringify({
          type: 'invariant_violation',
          invariant: violation.invariant,
          severity: violation.severity,
          entity: `${violation.entity_type}:${violation.entity_id}`,
          description: violation.violation_description,
          suggested_fix: violation.suggested_fix,
        }),
      ]
    );
  }

  /**
   * Get all logged invariant violations
   */
  async getViolationHistory(limit: number = 100): Promise<any[]> {
    const result = await db.query(
      `SELECT content, created_at FROM autonomy_memory
       WHERE content->>'type' = 'invariant_violation'
       ORDER BY created_at DESC
       LIMIT $1`,
      [limit]
    );

    return result.rows.map(r => ({ ...JSON.parse(r.content), logged_at: r.created_at }));
  }
}
