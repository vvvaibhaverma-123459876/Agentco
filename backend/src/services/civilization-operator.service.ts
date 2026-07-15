import { db } from '../db/client';
import { civilizationKernel } from './civilization-kernel.service';
import { societyService } from './society.service';
import { civilizationOs } from './civilization-os.service';

/**
 * Civilization operator plane (build phase C13).
 *
 * A single governed read model that composes the civilization topology, the OS
 * status projection, and recent cross-layer activity for the operator console.
 * Every field is derived from canonical tables — there is no fabricated data.
 */
export class CivilizationOperatorService {
  async overview(): Promise<Record<string, unknown>> {
    const root = await civilizationKernel.getRoot();
    if (!root) return { bootstrapped: false, civilization: null };

    const [topology, status, recentEvents, recentTicks, openWork] = await Promise.all([
      societyService.getTopology(),
      civilizationOs.statusProjection(root.civilization.id),
      this.recentEvents(),
      civilizationOs.recentTicks(5),
      this.openWork(root.civilization.id),
    ]);

    return {
      bootstrapped: true,
      civilization: {
        id: root.civilization.id,
        name: root.civilization.name,
        status: root.civilization.status,
        active_charter_version: root.active_charter_version,
        protected_invariants: root.protected_invariants,
        active_emergencies: root.active_emergencies,
        objectives_by_status: root.objectives_by_status,
      },
      topology: {
        societies: topology.societies,
        civilization_wide_institutions: topology.civilization_wide_institutions,
      },
      status,
      open_work: openWork,
      recent_events: recentEvents,
      recent_ticks: recentTicks,
      generated_at: (await db.query<{ now: string }>(`SELECT now()::text AS now`)).rows[0].now,
    };
  }

  private async recentEvents(): Promise<Array<{ event_type: string; object_type: string | null; occurred_at: string }>> {
    const r = await db.query(
      `SELECT event_type, object_type, occurred_at
         FROM event_log WHERE event_type LIKE 'civilization%' OR event_type LIKE 'mission%'
            OR event_type LIKE 'governance%' OR event_type LIKE 'judiciary%'
            OR event_type LIKE 'learning%' OR event_type LIKE 'expansion%'
        ORDER BY occurred_at DESC LIMIT 20`
    );
    return r.rows as any;
  }

  private async openWork(civilizationId: string): Promise<Record<string, unknown>> {
    const q = async (sql: string) => {
      try { return (await db.query(sql, [civilizationId])).rows; } catch { return []; }
    };
    const [missions, disputes, proposals, candidates, expansions] = await Promise.all([
      q(`SELECT id, title, status FROM missions WHERE civilization_id = $1 AND status NOT IN ('completed','settled','archived','cancelled','failed') ORDER BY created_at DESC LIMIT 10`),
      q(`SELECT id, dispute_type, status FROM judiciary_cases WHERE civilization_id = $1 AND status NOT IN ('closed','dismissed','final') ORDER BY created_at DESC LIMIT 10`),
      q(`SELECT id, title, status FROM governance_proposals WHERE civilization_id = $1 AND status NOT IN ('active','rejected','superseded','repealed','rolled_back') ORDER BY created_at DESC LIMIT 10`),
      q(`SELECT id, title, status FROM civ_learning_candidates WHERE civilization_id = $1 AND status NOT IN ('rejected','retained','rolled_back') ORDER BY created_at DESC LIMIT 10`),
      q(`SELECT id, title, status FROM expansion_proposals WHERE civilization_id = $1 AND status NOT IN ('rejected','revoked','expanded') ORDER BY created_at DESC LIMIT 10`),
    ]);
    return {
      missions,
      disputes,
      governance_proposals: proposals,
      learning_candidates: candidates,
      expansion_proposals: expansions,
    };
  }
}

export const civilizationOperator = new CivilizationOperatorService();
