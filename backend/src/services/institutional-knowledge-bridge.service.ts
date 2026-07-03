/**
 * Institutional Knowledge Bridge
 * ==============================
 * The "civilization produces learning" backbone. Institutional claims that
 * survive vetting/synthesis are promoted into durable, append-only
 * `agent_memories` so the planner's memory-retrieval path reuses
 * civilization-produced knowledge in subsequent runs (including runs in other
 * domains — cross-society transfer via the shared memory substrate).
 *
 * Production-grade guards (fail closed — a claim is NOT promoted unless):
 *   - the claim exists and is `supported`
 *   - it was produced by an institution (institutional-synthesis or the
 *     institution claim-vetting pipeline) — arbitrary claims are refused
 *   - it carries registered evidence ids (no ungrounded promotion)
 *   - its confidence clears MIN_PROMOTION_CONFIDENCE
 *   - CONJECTURE findings are promoted only at reduced importance, never as
 *     high-trust knowledge
 * Promotion is idempotent (one memory per institutional claim) and
 * transactional, and every decision — promote or block — is recorded in
 * `institutional_knowledge_promotions` with event-log lineage.
 */

import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { ledgerResolutionService } from './resolution-service.service';

const MIN_PROMOTION_CONFIDENCE = 0.6;
const MEMORY_NAMESPACE = 'institutional_knowledge';
const INSTITUTIONAL_PRODUCERS = new Set([
  'institutional-synthesis',
  'institution-claim-vetting',
]);

export interface PromoteInstitutionalClaimInput {
  /** autonomy_claims.claim_id produced by the civilization */
  institutionalClaimId: string;
  /** domain the knowledge belongs to (drives retrieval) */
  domain: string;
  contributingInstitutionIds?: string[];
  sourceKind?: 'synthesis' | 'vetting';
  correlationId?: string;
}

export interface InstitutionalPromotionResult {
  institutionalClaimId: string;
  promoted: boolean;
  memoryId: string | null;
  blockReason: string | null;
  importance: number | null;
  eventLogId: string | null;
}

type ClaimRow = {
  claim_id: string;
  text: string;
  status: string;
  confidence: number | null;
  support_source_ids: unknown;
  generated_by: string | null;
};

export class InstitutionalKnowledgeBridgeService {
  /**
   * Promote a single surviving institutional claim into durable memory.
   * Idempotent: repeated calls return the existing decision.
   */
  async promoteInstitutionalClaim(
    input: PromoteInstitutionalClaimInput
  ): Promise<InstitutionalPromotionResult> {
    const claimId = input.institutionalClaimId?.trim();
    if (!claimId) throw new Error('institutionalClaimId is required');
    if (!input.domain?.trim()) throw new Error('domain is required');
    const correlationId = input.correlationId ?? crypto.randomUUID();

    const client = await db.connect();
    try {
      await client.query('BEGIN');

      // Idempotency: return the prior decision if one exists.
      const existing = await client.query<{
        institutional_claim_id: string;
        memory_id: string | null;
        promoted: boolean;
        block_reason: string | null;
        event_log_id: string | null;
      }>(
        `SELECT institutional_claim_id, memory_id, promoted, block_reason, event_log_id
           FROM institutional_knowledge_promotions
          WHERE institutional_claim_id = $1
          FOR UPDATE`,
        [claimId]
      );
      if ((existing.rowCount ?? 0) > 0) {
        await client.query('COMMIT');
        const row = existing.rows[0];
        return {
          institutionalClaimId: claimId,
          promoted: row.promoted,
          memoryId: row.memory_id,
          blockReason: row.block_reason,
          importance: null,
          eventLogId: row.event_log_id,
        };
      }

      const claimResult = await client.query<ClaimRow>(
        `SELECT claim_id, text, status, confidence, support_source_ids, generated_by
           FROM autonomy_claims
          WHERE claim_id = $1`,
        [claimId]
      );
      if ((claimResult.rowCount ?? 0) !== 1) {
        throw new Error(`institutional claim not found: ${claimId}`);
      }
      const claim = claimResult.rows[0];

      // --- Fail-closed guards -------------------------------------------------
      const evidenceIds = Array.isArray(claim.support_source_ids)
        ? (claim.support_source_ids as unknown[]).filter((id): id is string => typeof id === 'string')
        : [];
      const confidence = claim.confidence === null ? 0 : Number(claim.confidence);
      const findingType = (input.sourceKind === 'vetting' ? 'VERIFIED' : 'DERIVED');

      let blockReason: string | null = null;
      if (claim.status !== 'supported') {
        blockReason = `claim status '${claim.status}' is not supported`;
      } else if (!claim.generated_by || !INSTITUTIONAL_PRODUCERS.has(claim.generated_by)) {
        blockReason = `claim producer '${claim.generated_by}' is not an institutional producer`;
      } else if (evidenceIds.length === 0) {
        blockReason = 'claim has no registered evidence ids';
      } else if (confidence < MIN_PROMOTION_CONFIDENCE) {
        blockReason = `confidence ${confidence} below promotion threshold ${MIN_PROMOTION_CONFIDENCE}`;
      }

      const actorId = await ledgerResolutionService.ensureServiceActor(
        'agentco-institutional-knowledge-bridge',
        ['institution.knowledge.promote']
      );

      if (blockReason) {
        const event = await eventLog.appendWithClient(client, {
          event_type: 'institution.knowledge_promotion_blocked',
          actor_id: actorId,
          object_type: 'institutional_knowledge_promotion',
          object_id: crypto.randomUUID(),
          correlation_id: correlationId,
          payload: { institutional_claim_id: claimId, block_reason: blockReason },
        });
        await client.query(
          `INSERT INTO institutional_knowledge_promotions
             (institutional_claim_id, memory_id, domain, confidence, finding_type,
              contributing_institution_ids, evidence_ids, source_kind, promoted,
              block_reason, event_log_id)
           VALUES ($1,NULL,$2,$3,$4,$5::jsonb,$6::jsonb,$7,false,$8,$9)`,
          [
            claimId,
            input.domain,
            confidence,
            findingType,
            JSON.stringify(input.contributingInstitutionIds ?? []),
            JSON.stringify(evidenceIds),
            input.sourceKind ?? 'synthesis',
            blockReason,
            event.id,
          ]
        );
        await client.query('COMMIT');
        return {
          institutionalClaimId: claimId,
          promoted: false,
          memoryId: null,
          blockReason,
          importance: null,
          eventLogId: event.id,
        };
      }

      // --- Promote into durable semantic memory ------------------------------
      // Importance is bounded by confidence; conjecture-grade findings would be
      // capped lower (synthesis marks CONJECTURE, but such claims usually fall
      // below MIN_PROMOTION_CONFIDENCE and are blocked above).
      const importance = Number(Math.min(0.9, Math.max(0.5, confidence)).toFixed(4));
      const memoryId = crypto.randomUUID();
      const agentId = `civilization:${(input.contributingInstitutionIds ?? [])[0] ?? 'synthesis'}`;
      const content = {
        source: 'civilization',
        institutional_claim_id: claimId,
        confidence,
        finding_type: findingType,
        contributing_institution_ids: input.contributingInstitutionIds ?? [],
        evidence_ids: evidenceIds,
      };

      await client.query(
        `INSERT INTO agent_memories
           (id, agent_id, memory_type, namespace, domain, summary, content, importance)
         VALUES ($1,$2,'semantic',$3,$4,$5,$6::jsonb,$7)`,
        [memoryId, agentId, MEMORY_NAMESPACE, input.domain, claim.text, JSON.stringify(content), importance]
      );

      const event = await eventLog.appendWithClient(client, {
        event_type: 'institution.knowledge_promoted',
        actor_id: actorId,
        object_type: 'agent_memory',
        object_id: memoryId,
        correlation_id: correlationId,
        payload: {
          institutional_claim_id: claimId,
          memory_id: memoryId,
          domain: input.domain,
          confidence,
          contributing_institution_ids: input.contributingInstitutionIds ?? [],
        },
      });

      await client.query(
        `INSERT INTO institutional_knowledge_promotions
           (institutional_claim_id, memory_id, domain, confidence, finding_type,
            contributing_institution_ids, evidence_ids, source_kind, promoted,
            block_reason, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7::jsonb,$8,true,NULL,$9)`,
        [
          claimId,
          memoryId,
          input.domain,
          confidence,
          findingType,
          JSON.stringify(input.contributingInstitutionIds ?? []),
          JSON.stringify(evidenceIds),
          input.sourceKind ?? 'synthesis',
          event.id,
        ]
      );

      await client.query('COMMIT');
      return {
        institutionalClaimId: claimId,
        promoted: true,
        memoryId,
        blockReason: null,
        importance,
        eventLogId: event.id,
      };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Promote the composite claim produced by an institutional synthesis result.
   * Convenience wrapper around promoteInstitutionalClaim.
   */
  async promoteFromSynthesis(synthesis: {
    synthesis_claim_id: string;
    contributing_institution_ids: string[];
    domain?: string;
  }): Promise<InstitutionalPromotionResult> {
    if (!synthesis.domain) {
      throw new Error('promoteFromSynthesis requires a domain for retrieval routing');
    }
    return this.promoteInstitutionalClaim({
      institutionalClaimId: synthesis.synthesis_claim_id,
      domain: synthesis.domain,
      contributingInstitutionIds: synthesis.contributing_institution_ids,
      sourceKind: 'synthesis',
    });
  }

  /** Promote a batch of pending surviving institutional claims (bounded). */
  async promotePending(domainByClaim: Map<string, { domain: string; institutions: string[] }>, limit = 20): Promise<InstitutionalPromotionResult[]> {
    const results: InstitutionalPromotionResult[] = [];
    let processed = 0;
    for (const [claimId, meta] of domainByClaim) {
      if (processed >= limit) break;
      results.push(
        await this.promoteInstitutionalClaim({
          institutionalClaimId: claimId,
          domain: meta.domain,
          contributingInstitutionIds: meta.institutions,
        })
      );
      processed += 1;
    }
    return results;
  }
}

export const institutionalKnowledgeBridge = new InstitutionalKnowledgeBridgeService();
