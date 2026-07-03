#!/usr/bin/env ts-node
/**
 * Score Validation
 * ================
 * Emits an evidence-checked score report. It does NOT invent scores: each
 * acceptance-matrix item is PASS only if a concrete, checkable signal exists
 * (a required test file present, a required migration present, a required
 * service export present). Signals are structural + presence checks that run
 * without a database or network so the report is reproducible anywhere.
 *
 * The per-dimension scores are derived mechanically from which acceptance
 * items pass; they are estimates gated on real signals, and the report says
 * so. Nothing here asserts 80+ unless the acceptance items actually pass.
 *
 * Usage: ts-node src/cli/score-validation.ts   (writes reports/system_run/latest/)
 */

import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

const backendRoot = path.resolve(__dirname, '..', '..');
const repoRoot = path.resolve(backendRoot, '..');

function fileExists(rel: string, base = backendRoot): boolean {
  return fs.existsSync(path.resolve(base, rel));
}

function fileContains(rel: string, needle: string, base = backendRoot): boolean {
  const p = path.resolve(base, rel);
  return fs.existsSync(p) && fs.readFileSync(p, 'utf8').includes(needle);
}

interface Check {
  id: string;
  description: string;
  pass: boolean;
  evidence: string;
}

const checks: Check[] = [];
function check(id: string, description: string, pass: boolean, evidence: string) {
  checks.push({ id, description, pass, evidence });
}

// --- Acceptance matrix (structural signals) ---------------------------------

check(
  'A1_clean_room_target',
  'make verify-clean-room target exists',
  fileContains('Makefile', 'verify-clean-room', repoRoot),
  'Makefile:verify-clean-room'
);
check(
  'A2_py_live_gating',
  'Python live-LLM tests are opt-in (conftest gating)',
  fileContains('conftest.py', 'live_llm', repoRoot),
  'conftest.py live_llm marker'
);
check(
  'A3_ledger_scan_expanded',
  'build ledger scans autonomy/civilization/frontend',
  fileContains('scripts/build_ledger.py', 'Path("autonomy")', repoRoot) &&
    fileContains('scripts/build_ledger.py', 'Path("civilization")', repoRoot),
  'scripts/build_ledger.py RUNTIME_DIRS'
);
check(
  'A4_docs_archived',
  'legacy status docs archived under docs/history',
  fileExists('docs/history/README.md', repoRoot),
  'docs/history/README.md'
);

check(
  'B1_skill_retrieval',
  'SkillRetrievalService exists and planner consumes it',
  fileExists('src/services/skill-retrieval.service.ts') &&
    fileContains('src/services/autonomy-action-planner.service.ts', 'skillRetrieval'),
  'skill-retrieval.service.ts + planner import'
);
check(
  'B2_skill_usage_events',
  'skill_usage_events migration + skill-consumption E2E present',
  fileExists('src/db/migrations/110_skill_usage_events.sql') &&
    fileExists('tests/skill-consumption-e2e.test.ts'),
  'migration 110 + skill-consumption-e2e.test.ts'
);

check(
  'C1_eval_canary_deploy',
  'candidate evaluation, canary, deployment services exist',
  fileExists('src/services/candidate-evaluation.service.ts') &&
    fileExists('src/services/skill-canary.service.ts') &&
    fileExists('src/services/skill-deployment.service.ts'),
  'candidate-evaluation/skill-canary/skill-deployment services'
);
check(
  'C2_closed_loop_e2e',
  'self-improvement closed-loop E2E present',
  fileExists('tests/self-improvement-closed-loop-e2e.test.ts'),
  'self-improvement-closed-loop-e2e.test.ts'
);

check(
  'D1_longitudinal_harness',
  'longitudinal learning harness + 3-cycle test present',
  fileExists('src/services/longitudinal-learning-harness.service.ts') &&
    fileExists('tests/longitudinal-learning-harness.test.ts'),
  'longitudinal-learning-harness service + test'
);
check(
  'D2_longitudinal_cli',
  'longitudinal learning CLI generates a DB-derived report',
  fileExists('src/cli/run-longitudinal-learning.ts'),
  'run-longitudinal-learning.ts'
);

check(
  'E1_calibration_routing',
  'calibration-aware routing service + planner integration',
  fileExists('src/services/calibration-aware-routing.service.ts') &&
    fileContains('src/services/autonomy-action-planner.service.ts', 'calibrationAwareRouting'),
  'calibration-aware-routing.service.ts + planner import'
);
check(
  'E2_calibration_test',
  'calibration-driven planning test present',
  fileExists('tests/calibration-driven-planning.test.ts'),
  'calibration-driven-planning.test.ts'
);

check(
  'F1_civilization_live_flow',
  'civilization live flow service + E2E present',
  fileExists('src/services/civilization-live-flow.service.ts') &&
    fileExists('tests/civilization-live-flow-e2e.test.ts'),
  'civilization-live-flow service + e2e'
);
check(
  'F2_civilization_learning_backbone',
  'civilization produces learning: knowledge bridge + E2E (clean-room & live)',
  fileExists('src/services/institutional-knowledge-bridge.service.ts') &&
    fileExists('src/db/migrations/113_institutional_knowledge_promotions.sql') &&
    fileExists('tests/civilization-learning-backbone-e2e.test.ts') &&
    fileExists('tests/civilization-learning-backbone-live.test.ts'),
  'institutional-knowledge-bridge + migration 113 + backbone e2e + live test'
);

check(
  'G1_goal_formation_free_run',
  'goal formation + supervised free-run services + test',
  fileExists('src/services/goal-formation.service.ts') &&
    fileExists('src/services/supervised-free-run.service.ts') &&
    fileExists('tests/goal-formation-supervised-free-run.test.ts'),
  'goal-formation + supervised-free-run + test'
);
check(
  'G2_free_run_cli',
  'supervised free-run CLI present',
  fileExists('src/cli/supervised-free-run.ts'),
  'supervised-free-run.ts'
);

check(
  'H1_ssrf_guard',
  'URL safety (SSRF) guard wired into the web adapter',
  fileExists('src/adapters/url-safety.ts') &&
    fileContains('src/adapters/real-web-adapter.ts', 'assertPublicHttpUrl'),
  'url-safety.ts + real-web-adapter import'
);
check(
  'H2_prompt_injection',
  'untrusted-content wrapping wired into the planner',
  fileContains('src/services/autonomy-action-planner.service.ts', 'wrapUntrustedContent'),
  'planner wrapUntrustedContent'
);
check(
  'H3_rbac_and_safety_test',
  'safety hardening test + RBAC middleware decision doc',
  fileExists('tests/safety-hardening.test.ts') &&
    fileExists('docs/RBAC_AND_WEB_SAFETY.md', repoRoot),
  'safety-hardening.test.ts + RBAC_AND_WEB_SAFETY.md'
);

check(
  'I1_canonical_doc',
  'canonical runtime doc present',
  fileExists('docs/CURRENT_RUNTIME_CANONICAL.md', repoRoot),
  'docs/CURRENT_RUNTIME_CANONICAL.md'
);
check(
  'I2_db_usage_manifest',
  'DB table usage manifest present',
  fileExists('docs/DB_TABLE_USAGE.md', repoRoot),
  'docs/DB_TABLE_USAGE.md'
);

// --- Dimension scoring (mechanical, gated on signals) -----------------------

function passed(prefix: string): boolean {
  const items = checks.filter(c => c.id.startsWith(prefix));
  return items.length > 0 && items.every(c => c.pass);
}

// Baseline (pre-work) scores from the audit; each dimension is raised only if
// its acceptance signals pass.
const dimensions: Array<{ name: string; baseline: number; target: number; gated: boolean }> = [
  { name: 'Clean-room runnability', baseline: 7, target: 9, gated: passed('A') },
  { name: 'Documentation accuracy', baseline: 6, target: 8, gated: passed('A4') && passed('I') },
  { name: 'Architecture coherence', baseline: 6, target: 8, gated: passed('I') },
  { name: 'Code completeness', baseline: 6, target: 8, gated: passed('B') && passed('C') },
  { name: 'Integration completeness', baseline: 5, target: 8, gated: passed('B') && passed('F') },
  { name: 'Test quality', baseline: 7, target: 8, gated: passed('C2') && passed('E2') },
  { name: 'Evidence governance', baseline: 7, target: 8, gated: passed('H') },
  { name: 'Calibration loop', baseline: 6, target: 8, gated: passed('E') },
  { name: 'Learning loop', baseline: 5, target: 8, gated: passed('C') && passed('D') },
  { name: 'Autonomy', baseline: 3, target: 6, gated: passed('G') },
  { name: 'Civilization implementation', baseline: 4, target: 8, gated: passed('F') },
  { name: 'Self-improvement', baseline: 3, target: 7, gated: passed('C') && passed('D') },
  { name: 'Safety', baseline: 7, target: 8, gated: passed('H') },
  { name: 'Production readiness', baseline: 4, target: 6, gated: passed('H') && passed('A') },
  { name: 'Real-world usefulness', baseline: 3, target: 6, gated: passed('D') && passed('G') },
  { name: 'Alignment with stated goal', baseline: 5, target: 8, gated: passed('B') && passed('D') && passed('F') },
];

const scored = dimensions.map(d => ({
  name: d.name,
  score: d.gated ? d.target : d.baseline,
  baseline: d.baseline,
  target: d.target,
  gatePassed: d.gated,
}));
const totalOutOf160 = scored.reduce((sum, d) => sum + d.score, 0);
const scoreOutOf100 = Math.round((totalOutOf160 / 160) * 1000) / 10;

let commit = 'unknown';
try {
  commit = execSync('git rev-parse HEAD', { cwd: repoRoot }).toString().trim();
} catch {
  /* not a git checkout */
}

const allChecksPass = checks.every(c => c.pass);
const report = {
  generatedAt: new Date().toISOString(),
  commit,
  note: 'Scores are estimates gated on structural signals (presence of the required services, migrations, CLIs, tests, and docs). They do NOT execute the test suites; run `make verify-clean-room` for behavioral proof.',
  acceptanceChecks: checks,
  acceptanceAllPass: allChecksPass,
  dimensions: scored,
  totalOutOf160,
  scoreOutOf100,
  claims80Plus: allChecksPass && scoreOutOf100 >= 80,
};

const outDir = path.resolve(repoRoot, 'reports/system_run/latest');
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, 'score_validation.json'), JSON.stringify(report, null, 2) + '\n');

const md = [
  '# Score Validation (signal-gated)',
  '',
  `Generated ${report.generatedAt} at commit \`${commit}\`.`,
  '',
  report.note,
  '',
  `**Acceptance checks:** ${checks.filter(c => c.pass).length}/${checks.length} pass.`,
  `**Estimated score:** ${scoreOutOf100}/100 (${totalOutOf160}/160).`,
  `**Claims 80+ :** ${report.claims80Plus}`,
  '',
  '## Acceptance checks',
  '',
  '| ID | Check | Pass | Evidence |',
  '|---|---|---|---|',
  ...checks.map(c => `| ${c.id} | ${c.description} | ${c.pass ? '✅' : '❌'} | ${c.evidence} |`),
  '',
  '## Dimensions',
  '',
  '| Dimension | Baseline | Target | Gate passed | Score |',
  '|---|---|---|---|---|',
  ...scored.map(
    d => `| ${d.name} | ${d.baseline} | ${d.target} | ${d.gatePassed ? '✅' : '—'} | ${d.score} |`
  ),
  '',
].join('\n');
fs.writeFileSync(path.join(outDir, 'score_validation.md'), md);

console.log(`[score-validation] ${checks.filter(c => c.pass).length}/${checks.length} checks pass`);
console.log(`[score-validation] estimated score ${scoreOutOf100}/100; claims80Plus=${report.claims80Plus}`);
console.log(`[score-validation] report written to ${outDir}/score_validation.{json,md}`);
if (!allChecksPass) {
  console.error('[score-validation] some acceptance checks failed:');
  for (const c of checks.filter(x => !x.pass)) console.error(`  ❌ ${c.id}: ${c.description}`);
  process.exitCode = 1;
}
