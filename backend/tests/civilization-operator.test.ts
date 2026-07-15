import fs from 'fs';
import path from 'path';
import { migrationDb } from './support/migration-db';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { institutionGovernance } from '../src/services/institution-governance.service';
import { societyService } from '../src/services/society.service';
import { civilizationOperator } from '../src/services/civilization-operator.service';
import { civilizationOs } from '../src/services/civilization-os.service';

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

describe('civilization operator plane (C13)', () => {
  beforeAll(async () => {
    await applyMigrations();
    await civilizationKernel.ensureCivilizationRoot();
    await societyService.ensureDefaultSocieties();
    await institutionGovernance.ensureMandatoryInstitutions();
    await civilizationOs.setMode('running');
  });

  test('the operator overview composes topology, status, and open work from governed tables', async () => {
    const overview = await civilizationOperator.overview() as any;
    expect(overview.bootstrapped).toBe(true);
    expect(overview.civilization).not.toBeNull();
    expect(overview.civilization.name).toBe('AgentCo');
    expect(overview.civilization.protected_invariants).toBeGreaterThanOrEqual(10);

    // Topology reflects the ≥2 seeded societies and the 10 mandatory institutions.
    expect(overview.topology.societies.length).toBeGreaterThanOrEqual(2);
    expect(Number(overview.status.institutions_active)).toBeGreaterThanOrEqual(10);
    expect(Number(overview.status.societies_active)).toBeGreaterThanOrEqual(2);

    // Composite shape is present for the operator console.
    expect(overview.open_work).toBeDefined();
    expect(Array.isArray(overview.open_work.missions)).toBe(true);
    expect(Array.isArray(overview.recent_events)).toBe(true);
    expect(overview.generated_at).toBeTruthy();
  });

  test('overview is null-safe before bootstrap-only fields and always reflects live status', async () => {
    const first = await civilizationOperator.overview() as any;
    // Run a coordinator tick, then confirm the overview status reflects the same civilization.
    await civilizationOs.tick();
    const second = await civilizationOperator.overview() as any;
    expect(second.civilization.id).toBe(first.civilization.id);
    expect(second.status.civilization_id).toBe(first.civilization.id);
  });
});
