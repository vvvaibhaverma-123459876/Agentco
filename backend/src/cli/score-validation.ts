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
import * as crypto from 'crypto';
import * as fs from 'fs';
import * as path from 'path';

const backendRoot = path.resolve(__dirname, '..', '..');
const repoRoot = path.resolve(backendRoot, '..');
const checkOnly = process.argv.includes('--check');
let commit = 'unknown';
try {
  commit = execSync('git rev-parse HEAD', { cwd: repoRoot }).toString().trim();
} catch {
  /* not a git checkout */
}

function fileExists(rel: string, base = backendRoot): boolean {
  return fs.existsSync(path.resolve(base, rel));
}

function fileContains(rel: string, needle: string, base = backendRoot): boolean {
  const p = path.resolve(base, rel);
  return fs.existsSync(p) && fs.readFileSync(p, 'utf8').includes(needle);
}

function hashReportInputs(): string {
  const inputs = [
    'Makefile',
    'backend/src/cli/score-validation.ts',
    'scripts/verify_gate_integrity.py',
    'scripts/verify_make_targets.py',
    'scripts/generate_forensic_audit_controls.py',
    'scripts/generate_forensic_inventory.py',
    'docs/audit/FORENSIC_AUDIT_CONTROLS.json',
    'docs/audit/FORENSIC_FILE_INVENTORY.json',
    'tests/test_forensic_inventory.py',
    'tests/test_gate_integrity_controls.py',
  ];
  const digest = crypto.createHash('sha256');
  for (const rel of inputs) {
    const full = path.resolve(repoRoot, rel);
    digest.update(rel);
    digest.update('\0');
    if (fs.existsSync(full)) {
      digest.update(fs.readFileSync(full));
    } else {
      digest.update('MISSING');
    }
    digest.update('\0');
  }
  return digest.digest('hex');
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

check(
  'J1_health_helm_contract',
  'backend liveness/readiness endpoints are aligned with Helm probes and tested',
  fileContains('src/server.ts', "/health/live") &&
    fileContains('src/server.ts', "/health/ready") &&
    fileContains('infrastructure/kubernetes/helm/agentco/values.yaml', 'path: /health/live', repoRoot) &&
    fileContains('infrastructure/kubernetes/helm/agentco/values.yaml', 'path: /health/ready', repoRoot) &&
    fileExists('tests/health-contract.test.ts'),
  'server health routes + Helm values + health-contract.test.ts'
);

check(
  'J2_browser_secret_removed',
  'browser bundle is scanned for privileged API key exposure',
  fileExists('frontend/scripts/check-smoke.mjs', repoRoot) &&
    fileContains('frontend/scripts/check-smoke.mjs', 'NEXT_PUBLIC_AGENTCO_API_KEY', repoRoot) &&
    fileContains('README.md', 'server-side proxy', repoRoot),
  'frontend/scripts/check-smoke.mjs + README server-side proxy contract'
);

check(
  'J3_durable_governance_stores',
  'evaluation, learning, and experiment stores fail closed to durable storage in production',
  fileExists('runtime/tests/test_runtime_durable_governance_stores.py', repoRoot) &&
    fileContains('runtime/evaluation/evaluators.py', 'PostgresEvaluationStore', repoRoot) &&
    fileContains('runtime/controlled_learning/pipeline.py', 'PostgresLearningArtifactStore', repoRoot) &&
    fileContains('runtime/self_improvement/experiments.py', 'PostgresExperimentStore', repoRoot),
  'runtime durable store implementations + durable-governance test'
);

check(
  'J4_durable_llm_budget',
  'backend LLM provider reserves and settles durable resource-ledger budget',
  fileContains('src/services/llm-provider.service.ts', 'resourceLedger.reserve') &&
    fileContains('src/services/llm-provider.service.ts', 'settleReservationUsage') &&
    fileContains('src/security.ts', 'LLM_RESOURCE_ACCOUNT_ID') &&
    fileContains('tests/llm-provider.test.ts', 'reserves and settles durable budget'),
  'llm-provider durable budget path + startup guard + tests'
);

check(
  'J5_event_outbox_worker',
  'transactional and signed event-bus outboxes have an executable relay worker',
  fileExists('src/workers/outbox-worker.ts') &&
    fileContains('package.json', 'agentco:outbox-worker') &&
    fileExists('tests/outbox-worker.test.ts') &&
    fileContains('src/db/migrations/128_event_bus_outbox.sql', 'event_bus_outbox'),
  'outbox-worker entrypoint + script + test + event_bus_outbox migration'
);

check(
  'J6_release_gate_enforces_core_contracts',
  'release gate checks route auth, audit chain, generated reports, and clean-tree behavior',
  fileContains('Makefile', 'route-auth-contract.test.ts', repoRoot) &&
    fileContains('Makefile', 'audit-chain-cross-writer.test.ts', repoRoot) &&
    fileContains('Makefile', 'agent-protocol-matrix-check', repoRoot) &&
    fileContains('Makefile', 'git status --porcelain', repoRoot),
  'Makefile release-gate contract'
);

check(
  'J7_helm_deployment_topology',
  'Helm chart contains backend, frontend, Services, Ingress, autoscaling, disruption budgets, migration job, and outbox worker',
  fileExists('infrastructure/kubernetes/helm/agentco/templates/deployment.yaml', repoRoot) &&
    fileExists('infrastructure/kubernetes/helm/agentco/templates/frontend-deployment.yaml', repoRoot) &&
    fileExists('infrastructure/kubernetes/helm/agentco/templates/services.yaml', repoRoot) &&
    fileExists('infrastructure/kubernetes/helm/agentco/templates/ingress.yaml', repoRoot) &&
    fileExists('infrastructure/kubernetes/helm/agentco/templates/hpa.yaml', repoRoot) &&
    fileExists('infrastructure/kubernetes/helm/agentco/templates/pdb.yaml', repoRoot) &&
    fileExists('infrastructure/kubernetes/helm/agentco/templates/migration-job.yaml', repoRoot) &&
    fileExists('infrastructure/kubernetes/helm/agentco/templates/outbox-worker-deployment.yaml', repoRoot) &&
    fileExists('tests/helm-deployment-contract.test.ts'),
  'Helm topology templates + helm-deployment-contract.test.ts'
);

check(
  'J8_forensic_audit_controls',
  'audit controls include requirements-to-behaviour, external dependency, completeness, and post-remediation ledgers',
  fileExists('scripts/generate_forensic_audit_controls.py', repoRoot) &&
    fileExists('docs/audit/FORENSIC_AUDIT_CONTROLS.json', repoRoot) &&
    fileExists('docs/audit/FORENSIC_AUDIT_CONTROLS.md', repoRoot) &&
    fileContains('docs/audit/FORENSIC_AUDIT_CONTROLS.md', 'Requirements-To-Behaviour Matrix', repoRoot) &&
    fileContains('docs/audit/FORENSIC_AUDIT_CONTROLS.md', 'Cross-Repository And External Dependency Audit', repoRoot) &&
    fileContains('docs/audit/FORENSIC_AUDIT_CONTROLS.md', 'Finding Completeness Ledger', repoRoot) &&
    fileContains('docs/audit/FORENSIC_AUDIT_CONTROLS.md', 'Independent Post-Remediation Re-Audit Checklist', repoRoot) &&
    fileContains('tests/test_forensic_inventory.py', 'test_forensic_audit_controls_cover_requirements_dependencies_and_completeness', repoRoot),
  'forensic audit controls generator + generated ledgers + regression test'
);

check(
  'J9_gate_integrity_controls',
  'release gate includes fake-success scanner and advertised-target validation',
  fileExists('scripts/verify_gate_integrity.py', repoRoot) &&
    fileExists('scripts/verify_make_targets.py', repoRoot) &&
    fileContains('Makefile', 'gate-integrity', repoRoot) &&
    fileContains('Makefile', 'verify-advertised-targets', repoRoot),
  'gate-integrity scanner + advertised target validator + Makefile release-gate wiring'
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
  { name: 'Documentation accuracy', baseline: 6, target: 9, gated: passed('A4') && passed('I') && passed('J') },
  { name: 'Architecture coherence', baseline: 6, target: 8, gated: passed('I') },
  { name: 'Code completeness', baseline: 6, target: 9, gated: passed('B') && passed('C') && passed('J4') && passed('J5') },
  { name: 'Integration completeness', baseline: 5, target: 9, gated: passed('B') && passed('F') && passed('J5') && passed('J6') },
  { name: 'Test quality', baseline: 7, target: 9, gated: passed('C2') && passed('E2') && passed('J1') && passed('J4') && passed('J5') },
  { name: 'Evidence governance', baseline: 7, target: 9, gated: passed('H') && passed('J3') && passed('J4') },
  { name: 'Calibration loop', baseline: 6, target: 8, gated: passed('E') },
  { name: 'Learning loop', baseline: 5, target: 8, gated: passed('C') && passed('D') },
  { name: 'Autonomy', baseline: 3, target: 6, gated: passed('G') },
  { name: 'Civilization implementation', baseline: 4, target: 8, gated: passed('F') },
  { name: 'Self-improvement', baseline: 3, target: 7, gated: passed('C') && passed('D') },
  { name: 'Safety', baseline: 7, target: 9, gated: passed('H') && passed('J2') && passed('J4') },
  { name: 'Production readiness', baseline: 4, target: 8, gated: passed('H') && passed('A') && passed('J') },
  { name: 'Real-world usefulness', baseline: 3, target: 7, gated: passed('D') && passed('G') && passed('J5') },
  { name: 'Alignment with stated goal', baseline: 5, target: 9, gated: passed('B') && passed('D') && passed('F') && passed('J') },
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

const allChecksPass = checks.every(c => c.pass);
const inputHash = hashReportInputs();
const existingReportPath = path.resolve(repoRoot, 'reports/system_run/latest/score_validation.json');
let existingReportFresh = true;
let existingReportCommit = 'missing';
let existingReportInputHash = 'missing';
if (checkOnly && fs.existsSync(existingReportPath)) {
  try {
    const existing = JSON.parse(fs.readFileSync(existingReportPath, 'utf8'));
    existingReportCommit = String(existing.commit ?? 'missing');
    existingReportInputHash = String(existing.inputHash ?? 'missing');
    existingReportFresh = existingReportInputHash === inputHash;
  } catch {
    existingReportFresh = false;
    existingReportCommit = 'unreadable';
    existingReportInputHash = 'unreadable';
  }
}
const report = {
  generatedAt: new Date().toISOString(),
  commit,
  inputHash,
  note: 'This report separates structural acceptance from verified behaviour. The structural score is based on repository signals. This command does NOT execute the test suites and therefore does not emit an overall production-readiness score; run `make release-gate` and clean-room/staging commands for behavioural proof.',
  acceptanceChecks: checks,
  acceptanceAllPass: allChecksPass,
  dimensions: scored,
  totalOutOf160,
  structuralScoreOutOf100: scoreOutOf100,
  verifiedBehaviorScoreOutOf100: null,
  scorePolicy: 'Structural score must not be presented as verified behaviour.',
  claims80Plus: allChecksPass && scoreOutOf100 >= 80,
  existingReportFresh,
  existingReportCommit,
  existingReportInputHash,
};

const outDir = path.resolve(repoRoot, 'reports/system_run/latest');
const md = [
  '# Score Validation (signal-gated)',
  '',
  `Generated ${report.generatedAt} at commit \`${commit}\`.`,
  `Input hash: \`${inputHash}\`.`,
  '',
  report.note,
  '',
  `**Acceptance checks:** ${checks.filter(c => c.pass).length}/${checks.length} pass.`,
  `**Structural score:** ${scoreOutOf100}/100 (${totalOutOf160}/160).`,
  '**Verified behaviour score:** not emitted by this structural validator.',
  `**Existing report fresh for HEAD:** ${existingReportFresh}`,
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
if (!checkOnly) {
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'score_validation.json'), JSON.stringify(report, null, 2) + '\n');
  fs.writeFileSync(path.join(outDir, 'score_validation.md'), md);
}

console.log(`[score-validation] ${checks.filter(c => c.pass).length}/${checks.length} checks pass`);
console.log(`[score-validation] structural score ${scoreOutOf100}/100; verifiedBehaviorScore=null; claims80Plus=${report.claims80Plus}`);
if (checkOnly) {
  console.log('[score-validation] check mode: report not written');
} else {
  console.log(`[score-validation] report written to ${outDir}/score_validation.{json,md}`);
}
if (checkOnly && !existingReportFresh) {
  console.error(`[score-validation] stale existing report input hash: ${existingReportInputHash} != ${inputHash}`);
}
if (!allChecksPass || !report.claims80Plus || (checkOnly && !existingReportFresh)) {
  console.error('[score-validation] some acceptance checks failed:');
  for (const c of checks.filter(x => !x.pass)) console.error(`  ❌ ${c.id}: ${c.description}`);
  process.exitCode = 1;
}
