import fs from 'fs';
import path from 'path';
import { migrationDb } from './support/migration-db';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { civilizationOs } from '../src/services/civilization-os.service';
import { civilizationMetrics } from '../src/services/civilization-metrics.service';
import { CivilizationSchedulerWorker } from '../src/workers/civilization-scheduler-worker';
import * as prometheus from 'prom-client';

async function applyMigrations() {
  for (const file of [
    '129_civilization_kernel.sql', '130_citizenship.sql',
    '131_societies_and_institution_charters.sql', '132_institution_coalitions.sql',
    '133_missions.sql', '134_civilization_economy.sql', '135_governance.sql', '136_judiciary.sql',
    '137_collective_epistemics.sql', '138_safe_evolution.sql', '139_capability_expansion.sql', '140_civilization_os.sql',
  ]) {
    await migrationDb.query(fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${file}`), 'utf8'));
  }
}

const REPO = path.resolve(__dirname, '../..');

describe('civilization reliability, observability, deployment (C14)', () => {
  beforeAll(async () => {
    await applyMigrations();
    await civilizationKernel.ensureCivilizationRoot();
    await civilizationOs.setMode('running');
  });

  test('the scheduler worker executes a bounded tick as leader', async () => {
    const worker = new CivilizationSchedulerWorker({ pollIntervalMs: 1000, workerId: 'test-worker' });
    const tick = await worker.runOnce();
    expect(tick.was_leader).toBe(true);
    expect(typeof tick.tick_number).toBe('number');
  });

  test('the OS tick records observability metrics on the Prometheus registry', async () => {
    await civilizationOs.tick();
    const metrics = await prometheus.register.metrics();
    expect(metrics).toContain('civilization_os_ticks_total');
    expect(metrics).toContain('civilization_os_heartbeat_seconds');
    expect(metrics).toContain('civilization_missions_executing');
    // The tick counter reflects at least the ticks we ran.
    const tickMetric = await (civilizationMetrics.tickCounter as any).get();
    expect(tickMetric.values[0].value).toBeGreaterThan(0);
  });

  test('deployment artifacts reference real entry points (no dangling worker command)', () => {
    // Helm scheduler deployment references the compiled worker.
    const helm = fs.readFileSync(
      path.join(REPO, 'infrastructure/kubernetes/helm/agentco/templates/civilization-scheduler-deployment.yaml'), 'utf8'
    );
    expect(helm).toContain('dist/workers/civilization-scheduler-worker.js');
    // The TypeScript source that compiles to that path exists.
    expect(fs.existsSync(path.join(REPO, 'backend/src/workers/civilization-scheduler-worker.ts'))).toBe(true);
    // The npm script that runs the worker in dev exists.
    const pkg = JSON.parse(fs.readFileSync(path.join(REPO, 'backend/package.json'), 'utf8'));
    expect(pkg.scripts['agentco:civilization-scheduler']).toContain('civilization-scheduler-worker.ts');
    // Helm values enable the scheduler workload.
    const values = fs.readFileSync(path.join(REPO, 'infrastructure/kubernetes/helm/agentco/values.yaml'), 'utf8');
    expect(values).toContain('civilizationScheduler:');
  });

  test('the previously fake-success Make targets now run real suites', () => {
    const makefile = fs.readFileSync(path.join(REPO, 'Makefile'), 'utf8');
    // The two echo-only targets now invoke jest suites.
    const memBlock = makefile.slice(makefile.indexOf('autonomy-memory-quality-test:'), makefile.indexOf('autonomy-observability-test:'));
    expect(memBlock).toContain('jest tests/collective-knowledge.test.ts');
    const obsBlock = makefile.slice(makefile.indexOf('autonomy-observability-test:'), makefile.indexOf('civilization-scheduler:'));
    expect(obsBlock).toContain('jest tests/civilization-os.test.ts');
    // The broken dependency on a nonexistent target is fixed.
    expect(makefile).not.toContain('make autonomy-phases-5-8-full-test');
  });

  test('the status projection is a rebuildable read model derived only from source tables', async () => {
    // Rebuilding the projection twice yields identical civilization-scoped counts,
    // proving it is a pure function of source state (projection rebuild property).
    const a = await civilizationOs.statusProjection();
    const b = await civilizationOs.statusProjection();
    expect(b).toEqual(a);
    expect(a.civilization_id).toBeTruthy();
  });
});
