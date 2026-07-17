import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';
import { auditLog } from './audit-log.service';
import { civilizationKernel } from './civilization-kernel.service';
import { PublicHttpError } from '../http-errors';

/**
 * Collective epistemics (build phase C9).
 *
 * Connects the existing evidence/claim/prediction/trust/memory systems into a
 * civilization-wide knowledge layer with a provenance graph and transitive
 * retraction. Retracting a node propagates to every dependent: claims become
 * 'retracted', memories are demoted (via the existing memory_demotions),
 * decisions are flagged. Civilization knowledge views return promoted claims
 * and memories together with their provenance and (actor, domain) trust
 * context.
 */

export type KnowledgeType = 'evidence' | 'claim' | 'prediction' | 'memory' | 'decision';

export class CollectiveKnowledgeService {
  /** Record that `to` derives from `from` (provenance edge). */
  async linkProvenance(input: {
    from_type: KnowledgeType; from_id: string; to_type: KnowledgeType; to_id: string;
    relation?: string; actor_id: string; civilization_id?: string;
  }): Promise<{ id: string }> {
    if (input.from_type === input.to_type && input.from_id === input.to_id) {
      throw new PublicHttpError(400, 'a knowledge node cannot derive from itself');
    }
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const civilizationId = input.civilization_id ?? (await this.rootId());
      const edgeId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'knowledge.provenance_linked',
        actor_id: input.actor_id,
        object_type: 'knowledge_provenance_edge',
        object_id: edgeId,
        correlation_id: crypto.randomUUID(),
        payload: { from: `${input.from_type}:${input.from_id}`, to: `${input.to_type}:${input.to_id}` },
      });
      await client.query(
        `INSERT INTO knowledge_provenance_edges
           (id, civilization_id, from_type, from_id, to_type, to_id, relation, created_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
         ON CONFLICT (from_type, from_id, to_type, to_id, relation) DO NOTHING`,
        [edgeId, civilizationId, input.from_type, input.from_id, input.to_type, input.to_id,
         input.relation ?? 'derives_from', input.actor_id, event.id]
      );
      await client.query('COMMIT');
      return { id: edgeId };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Retract a knowledge node and propagate transitively. Returns the affected
   * set. Fail-safe: propagation only ever weakens knowledge (retract/demote/
   * flag), never strengthens it.
   */
  async retract(input: {
    subject_type: KnowledgeType; subject_id: string; reason: string; actor_id: string; civilization_id?: string;
  }): Promise<{ retraction_id: string; affected: Array<{ type: string; id: string; effect: string; depth: number }> }> {
    if (!input.reason || input.reason.trim().length === 0) throw new PublicHttpError(400, 'reason is required');
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const civilizationId = input.civilization_id ?? (await this.rootId());
      const retractionId = crypto.randomUUID();
      const event = await eventLog.appendWithClient(client, {
        event_type: 'knowledge.retracted',
        actor_id: input.actor_id,
        object_type: 'knowledge_retraction',
        object_id: retractionId,
        correlation_id: crypto.randomUUID(),
        payload: { subject: `${input.subject_type}:${input.subject_id}`, reason: input.reason },
      });
      await client.query(
        `INSERT INTO knowledge_retractions
           (id, civilization_id, subject_type, subject_id, reason, retracted_by_actor_id, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7)`,
        [retractionId, civilizationId, input.subject_type, input.subject_id, input.reason, input.actor_id, event.id]
      );

      // Breadth-first traversal of the provenance graph from the subject.
      const affected: Array<{ type: string; id: string; effect: string; depth: number }> = [];
      const seen = new Set<string>([`${input.subject_type}:${input.subject_id}`]);
      let frontier: Array<{ type: KnowledgeType; id: string; depth: number }> = [
        { type: input.subject_type, id: input.subject_id, depth: 0 },
      ];

      // Apply the direct effect on the subject itself.
      await this.applyEffect(client, retractionId, input.subject_type, input.subject_id, 0, input.reason, affected);

      while (frontier.length > 0) {
        const next: Array<{ type: KnowledgeType; id: string; depth: number }> = [];
        for (const node of frontier) {
          // Explicit provenance edges.
          const edges = await client.query<{ to_type: KnowledgeType; to_id: string }>(
            `SELECT to_type, to_id FROM knowledge_provenance_edges WHERE from_type = $1 AND from_id = $2`,
            [node.type, node.id]
          );
          // Auto-discovered claim dependents: claims whose support_source_ids
          // include a retracted evidence/claim id.
          const dependents: Array<{ to_type: KnowledgeType; to_id: string }> = [...edges.rows];
          if (node.type === 'evidence' || node.type === 'claim') {
            const claims = await client.query<{ claim_id: string }>(
              `SELECT claim_id FROM autonomy_claims WHERE support_source_ids @> $1::jsonb`,
              [JSON.stringify([node.id])]
            );
            for (const c of claims.rows) dependents.push({ to_type: 'claim', to_id: c.claim_id });
          }

          for (const dep of dependents) {
            const key = `${dep.to_type}:${dep.to_id}`;
            if (seen.has(key)) continue;
            seen.add(key);
            await this.applyEffect(client, retractionId, dep.to_type, dep.to_id, node.depth + 1, input.reason, affected);
            next.push({ type: dep.to_type, id: dep.to_id, depth: node.depth + 1 });
          }
        }
        frontier = next;
      }

      await client.query(`UPDATE knowledge_retractions SET propagated_count = $2 WHERE id = $1`, [retractionId, affected.length]);
      await auditLog.appendWithClient(client, {
        agent_id: input.actor_id,
        action_type: 'decision',
        input_summary: `retract ${input.subject_type}:${input.subject_id}: ${input.reason}`,
        output_summary: `retraction ${retractionId} propagated to ${affected.length} node(s)`,
        confidence_score: 1, risk_level: 'high', human_approved: false,
        downstream_events: [event.id],
      }, { timestamp: new Date().toISOString() });
      await client.query('COMMIT');
      return { retraction_id: retractionId, affected };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  private async applyEffect(
    client: PoolClient, retractionId: string, type: KnowledgeType, id: string, depth: number, reason: string,
    affected: Array<{ type: string; id: string; effect: string; depth: number }>
  ): Promise<void> {
    let effect: string;
    if (type === 'claim') {
      await client.query(
        `UPDATE autonomy_claims SET status = 'retracted' WHERE claim_id = $1 AND status <> 'retracted'`,
        [id]
      );
      effect = 'claim_retracted';
    } else if (type === 'memory') {
      // Demote via the existing append-only memory_demotions (unique per memory).
      await client.query(
        `INSERT INTO memory_demotions (memory_id, reason, demoted_by)
         VALUES ($1,$2,'collective-knowledge-retraction') ON CONFLICT (memory_id) DO NOTHING`,
        [id, `retraction ${retractionId}: ${reason}`]
      );
      effect = 'memory_demoted';
    } else if (type === 'decision') {
      await client.query(
        `INSERT INTO decision_retraction_flags (decision_id, retraction_id, reason)
         VALUES ($1,$2,$3) ON CONFLICT (decision_id, retraction_id) DO NOTHING`,
        [id, retractionId, reason]
      );
      effect = 'decision_flagged';
    } else if (type === 'prediction') {
      effect = 'prediction_flagged';
    } else {
      effect = 'evidence_flagged';
    }
    // depth 0 is the subject itself; record propagations at depth >= 1 and the
    // subject's own effect (so the direct claim/memory retraction is visible).
    await client.query(
      `INSERT INTO retraction_propagations (retraction_id, affected_type, affected_id, effect, depth)
       VALUES ($1,$2,$3,$4,$5)`,
      [retractionId, type, id, effect, depth]
    );
    affected.push({ type, id, effect, depth });
  }

  async isRetracted(type: KnowledgeType, id: string): Promise<boolean> {
    if (type === 'claim') {
      const r = await db.query<{ status: string }>(`SELECT status FROM autonomy_claims WHERE claim_id = $1 LIMIT 1`, [id]);
      return r.rows[0]?.status === 'retracted';
    }
    if (type === 'memory') {
      const r = await db.query<{ count: string }>(`SELECT COUNT(*)::int AS count FROM memory_demotions WHERE memory_id = $1`, [id]);
      return Number(r.rows[0].count) > 0;
    }
    const r = await db.query<{ count: string }>(
      `SELECT COUNT(*)::int AS count FROM knowledge_retractions WHERE subject_type = $1 AND subject_id = $2`, [type, id]
    );
    return Number(r.rows[0].count) > 0;
  }

  /**
   * Reconciliation sweep: find provenance edges whose source claim is already
   * retracted while the dependent claim is still standing (possible if a crash
   * interrupted propagation or an edge was linked after the retraction), and
   * apply the missing weakening. Propagation only ever weakens; the propagation
   * row is attributed to the original retraction at one depth deeper. Idempotent
   * — a reconciled claim matches no row on re-run. Driven by the OS tick (C12).
   */
  async sweepDanglingProvenance(limit = 25): Promise<number> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const dangling = await client.query<{ to_id: string; retraction_id: string; depth: number }>(
        `SELECT DISTINCT e.to_id, rp.retraction_id, rp.depth
           FROM knowledge_provenance_edges e
           JOIN retraction_propagations rp
             ON rp.affected_type = 'claim' AND rp.affected_id::text = e.from_id::text AND rp.effect = 'claim_retracted'
           JOIN autonomy_claims c ON c.claim_id::text = e.to_id::text AND c.status <> 'retracted'
          WHERE e.from_type = 'claim' AND e.to_type = 'claim'
          LIMIT $1`,
        [limit]
      );
      let reconciled = 0;
      for (const row of dangling.rows) {
        const updated = await client.query(
          `UPDATE autonomy_claims SET status = 'retracted' WHERE claim_id::text = $1 AND status <> 'retracted'`,
          [row.to_id]
        );
        await client.query(
          `INSERT INTO retraction_propagations (retraction_id, affected_type, affected_id, effect, depth)
           SELECT $1, 'claim', $2, 'claim_retracted', $3
            WHERE NOT EXISTS (
              SELECT 1 FROM retraction_propagations
               WHERE retraction_id = $1 AND affected_type = 'claim' AND affected_id = $2)`,
          [row.retraction_id, row.to_id, row.depth + 1]
        );
        if ((updated.rowCount ?? 0) > 0) reconciled++;
      }
      await client.query('COMMIT');
      return reconciled;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async getRetraction(retractionId: string): Promise<{ subject: string; reason: string; propagations: Array<{ affected_type: string; affected_id: string; effect: string; depth: number }> } | null> {
    const r = await db.query<{ subject_type: string; subject_id: string; reason: string }>(
      `SELECT subject_type, subject_id, reason FROM knowledge_retractions WHERE id = $1`, [retractionId]
    );
    if ((r.rowCount ?? 0) !== 1) return null;
    const props = await db.query(
      `SELECT affected_type, affected_id, effect, depth FROM retraction_propagations WHERE retraction_id = $1 ORDER BY depth`, [retractionId]
    );
    return {
      subject: `${r.rows[0].subject_type}:${r.rows[0].subject_id}`,
      reason: r.rows[0].reason,
      propagations: props.rows as any,
    };
  }

  /**
   * Civilization knowledge view: supported, non-retracted claims and
   * non-demoted promoted memories, each with provenance and (actor, domain)
   * trust context. This is the civilization-aware retrieval surface.
   */
  async civilizationKnowledge(input: { domain?: string; limit?: number } = {}): Promise<{
    claims: Array<{ claim_id: string; text: string; status: string; support_source_ids: unknown; producer: string; domain_trust: number | null }>;
    memories: Array<{ memory_id: string; agent_id: string; domain: string | null; summary: string; domain_trust: number | null; demoted: boolean }>;
  }> {
    const limit = Math.min(input.limit ?? 50, 200);
    const claims = await db.query<any>(
      `SELECT c.claim_id, c.text, c.status, c.support_source_ids, c.generated_by AS producer,
              (SELECT trust_factor FROM trust_scores ts
                 WHERE ts.subject_id = c.generated_by AND ($1::text IS NULL OR ts.domain = $1)
                   AND ts.force_downgrade = false
                 ORDER BY ts.window_end DESC LIMIT 1) AS domain_trust
         FROM autonomy_claims c
        WHERE c.status IN ('supported','weakly_supported')
        ORDER BY c.created_at DESC LIMIT $2`,
      [input.domain ?? null, limit]
    );
    const memories = await db.query<any>(
      `SELECT m.id AS memory_id, m.agent_id, m.domain, m.summary,
              (m.id IN (SELECT memory_id FROM memory_demotions)) AS demoted,
              (SELECT trust_factor FROM trust_scores ts
                 WHERE ts.subject_id = m.agent_id AND ($1::text IS NULL OR ts.domain = m.domain)
                   AND ts.force_downgrade = false
                 ORDER BY ts.window_end DESC LIMIT 1) AS domain_trust
         FROM agent_memories m
        WHERE m.superseded_by IS NULL
          AND m.id NOT IN (SELECT memory_id FROM memory_demotions)
          AND ($1::text IS NULL OR m.domain = $1)
        ORDER BY m.created_at DESC LIMIT $2`,
      [input.domain ?? null, limit]
    );
    return {
      claims: claims.rows.map(r => ({ ...r, domain_trust: r.domain_trust !== null ? Number(r.domain_trust) : null })),
      memories: memories.rows.map(r => ({ ...r, domain_trust: r.domain_trust !== null ? Number(r.domain_trust) : null })),
    };
  }

  private async rootId(): Promise<string> {
    const root = await civilizationKernel.ensureCivilizationRoot();
    return root.id;
  }
}

export const collectiveKnowledge = new CollectiveKnowledgeService();
