/**
 * Longitudinal Learning Harness
 * =============================
 * Proves durable improvement across THREE full cycles in clean-room mode:
 * two measured improvement cycles in different task families/domains plus a
 * demotion cycle where a projection-only candidate is rejected. Every cycle
 * has DB lineage (candidate, evaluation, canary, skill version, event log),
 * and the report is generated from database state.
 */

import fs from 'fs';
import path from 'path';
import { describe, expect, test, beforeAll } from '@jest/globals';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { longitudinalLearningHarness } from '../src/services/longitudinal-learning-harness.service';
import { skillRetrieval } from '../src/services/skill-retrieval.service';

async function applyMigrations() {
  for (const name of [
    '004_decision_log.sql',
    '012_decision_log_chain.sql',
    '014_decision_log_immutability_triggers.sql',
    '009_trust_scores.sql',
    '052b_institutions.sql',
    '062_runtime_schema_compatibility.sql',
    '079_identity_authority.sql',
    '080_event_log.sql',
    '083_transactional_outbox.sql',
    '102_domain_registry.sql',
    '103_generality_metric_tracker.sql',
    '104_candidate_regression_tests.sql',
    '105_skill_library.sql',
    '106_proof_of_competence.sql',
    '107_capability_expansion_gate.sql',
    '108_skill_promotion_loop.sql',
    '110_skill_usage_events.sql',
    '111_self_improvement_loop.sql',
  ]) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await migrationDb.query(migration);
  }
}

describe('longitudinal learning across runs', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('three full cycles: two measured improvements plus one demotion, all with DB lineage', async () => {
    const runLabel = `longrun_${Date.now()}`;
    const cycles = await longitudinalLearningHarness.runThreeCycles(runLabel);

    expect(cycles).toHaveLength(3);
    const [c1, c2, c3] = cycles;

    // Cycles 1 and 2: measured improvement in different families/domains.
    for (const cycle of [c1, c2]) {
      expect(cycle.outcome).toBe('improved');
      expect(cycle.scoreDelta).toBeGreaterThan(0);
      expect(cycle.improvedScore).toBeGreaterThan(cycle.baselineScore);
      expect(cycle.skillVersionId).toMatch(/^[0-9a-f-]{36}$/);
      expect(cycle.reused).toBe(true);
    }
    expect(c1.taskFamily).not.toBe(c2.taskFamily);
    expect(c1.domain).not.toBe(c2.domain);

    // Cycle 3: the loop says no — a projection-only candidate is rejected.
    expect(c3.outcome).toBe('rolled_back');
    expect(c3.skillVersionId).toBeNull();

    // DB lineage: cycle rows link candidate -> evaluation -> canary -> skill,
    // and each row carries an event-log id.
    const rows = await db.query<{
      cycle_label: string;
      candidate_id: string | null;
      evaluation_id: string | null;
      canary_run_id: string | null;
      skill_version_id: string | null;
      event_log_id: string | null;
      outcome: string;
    }>(
      `SELECT cycle_label, candidate_id, evaluation_id, canary_run_id,
              skill_version_id, event_log_id, outcome
         FROM longitudinal_learning_cycles
        WHERE cycle_label LIKE $1
        ORDER BY created_at ASC`,
      [`${runLabel}%`]
    );
    expect(rows.rowCount).toBe(3);
    for (const row of rows.rows) {
      expect(row.candidate_id).not.toBeNull();
      expect(row.evaluation_id).not.toBeNull();
      expect(row.event_log_id).not.toBeNull();
    }
    expect(rows.rows[0].canary_run_id).not.toBeNull();
    expect(rows.rows[0].skill_version_id).not.toBeNull();

    // The candidate statuses reflect the real lifecycle.
    const statuses = await db.query<{ status: string }>(
      `SELECT status FROM learner_candidates WHERE id = ANY($1::uuid[]) ORDER BY created_at`,
      [rows.rows.map(r => r.candidate_id)]
    );
    expect(statuses.rows.map(r => r.status).sort()).toEqual(['promoted', 'promoted', 'rejected']);

    // Later behavior change: the cycle-1 skill is retrievable for a NEW goal
    // in that domain (this is the same retrieval path the planner uses).
    const laterSkills = await skillRetrieval.retrieveForPlanning({
      goalText: 'A brand new research goal needing source selection help',
      domain: c1.domain,
    });
    expect(laterSkills.map(s => s.skillVersionId)).toContain(c1.skillVersionId);

    // The report is generated from DB state and certifies durable improvement.
    const report = await longitudinalLearningHarness.generateReport(runLabel);
    expect(report.cycles).toHaveLength(3);
    expect(report.improvedCycles).toBe(2);
    expect(report.rolledBackCycles).toBe(1);
    expect(report.durableImprovement).toBe(true);
  }, 60000);
});
