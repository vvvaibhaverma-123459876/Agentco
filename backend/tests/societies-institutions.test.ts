import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { citizenshipService } from '../src/services/citizenship.service';
import { societyService, DEFAULT_SOCIETIES } from '../src/services/society.service';
import { institutionGovernance, MANDATORY_INSTITUTIONS } from '../src/services/institution-governance.service';
import { institutionsService } from '../src/services/institutions.service';

async function applyMigrations() {
  for (const file of ['129_civilization_kernel.sql', '130_citizenship.sql', '131_societies_and_institution_charters.sql']) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${file}`), 'utf8');
    await migrationDb.query(migration);
  }
}

async function registerActor(prefix: string): Promise<string> {
  const actor = await identityAuthorityService.registerActor({
    actor_type: 'human',
    name: `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}`,
  });
  return actor.id;
}

describe('societies and institution governance (C3)', () => {
  beforeAll(async () => {
    await applyMigrations();
    await civilizationKernel.ensureCivilizationRoot();
  });

  test('default societies seed idempotently and at least two are active', async () => {
    const first = await societyService.ensureDefaultSocieties();
    const second = await societyService.ensureDefaultSocieties();
    expect(second.map(s => s.id).sort()).toEqual(first.map(s => s.id).sort());
    const active = first.filter(s => s.status === 'active');
    expect(active.length).toBeGreaterThanOrEqual(2);
    expect(first.map(s => s.name).sort()).toEqual(DEFAULT_SOCIETIES.map(s => s.name).sort());

    const topology = await societyService.getTopology();
    expect(topology.civilization_id).not.toBeNull();
    expect(topology.societies.length).toBeGreaterThanOrEqual(2);
    const core = topology.societies.find(s => s.name === 'Core Operations');
    expect(core!.jurisdictions).toContain('global');
  });

  test('society jurisdiction cannot exceed civilization jurisdiction (DB-enforced subset)', async () => {
    const [society] = await societyService.ensureDefaultSocieties();
    const operator = await registerActor('soc-jurisdiction');
    await expect(societyService.addJurisdiction({
      society_id: society.id,
      jurisdiction_key: `never-granted-${Date.now()}`,
      granted_by_actor_id: operator,
    })).rejects.toThrow(/cannot exceed civilization jurisdiction/);
  });

  test('society lifecycle: suspension blocks joins and attachments; dissolution requires empty society', async () => {
    const operator = await registerActor('soc-lifecycle');
    const society = await societyService.createSociety({
      name: `Test Society ${Date.now()}`,
      created_by_actor_id: operator,
    });
    expect(society.status).toBe('forming');
    await societyService.transitionSociety({
      society_id: society.id, to_status: 'active', actor_id: operator, reason: 'activate for test',
    });

    // Register an active citizen and join.
    const citizenActor = await registerActor('soc-citizen');
    const citizen = await citizenshipService.registerCitizen({ actor_id: citizenActor, citizen_type: 'human' });
    await citizenshipService.transitionCitizen({ citizen_id: citizen.id, to_status: 'probationary', actor_id: operator, reason: 'vetted' });
    await citizenshipService.transitionCitizen({ citizen_id: citizen.id, to_status: 'active', actor_id: operator, reason: 'ok' });
    await societyService.joinSociety({ society_id: society.id, citizen_id: citizen.id, actor_id: operator });

    await societyService.transitionSociety({
      society_id: society.id, to_status: 'suspended', actor_id: operator, reason: 'containment drill',
    });

    const otherActor = await registerActor('soc-citizen-2');
    const other = await citizenshipService.registerCitizen({ actor_id: otherActor, citizen_type: 'human' });
    await expect(societyService.joinSociety({
      society_id: society.id, citizen_id: other.id, actor_id: operator,
    })).rejects.toThrow(/suspended/);

    const institution = await institutionsService.createCanonicalInstitution({
      name: `Suspension Test Institute ${Date.now()}`,
      domain: 'testing',
    });
    await expect(societyService.attachInstitution({
      society_id: society.id, institution_id: institution.institutionId, actor_id: operator,
    })).rejects.toThrow(/suspended/);

    // History preserved: membership from before suspension still visible.
    const memberships = await db.query(
      `SELECT status FROM society_memberships WHERE society_id = $1`,
      [society.id]
    );
    expect(memberships.rowCount).toBe(1);

    // Direct status mutation is blocked.
    await expect(
      db.query(`UPDATE societies SET status = 'active' WHERE id = $1`, [society.id])
    ).rejects.toThrow(/SOCIETY GUARD/);

    // Dissolution requires ending memberships first.
    await expect(societyService.transitionSociety({
      society_id: society.id, to_status: 'dissolved', actor_id: operator, reason: 'cleanup',
    })).rejects.toThrow(/ending all active/);
    await societyService.leaveSociety({
      society_id: society.id, citizen_id: citizen.id, actor_id: operator, reason: 'cleanup',
    });
    const dissolved = await societyService.transitionSociety({
      society_id: society.id, to_status: 'dissolved', actor_id: operator, reason: 'cleanup',
    });
    expect(dissolved.status).toBe('dissolved');
    await expect(societyService.transitionSociety({
      society_id: society.id, to_status: 'active', actor_id: operator, reason: 'resurrect',
    })).rejects.toThrow(/illegal society transition/);
  });

  test('mandatory institutions seed idempotently with departments, charters, powers, limits, jurisdiction', async () => {
    const first = await institutionGovernance.ensureMandatoryInstitutions();
    const second = await institutionGovernance.ensureMandatoryInstitutions();
    expect(first.length).toBe(MANDATORY_INSTITUTIONS.length);
    expect(second.map(r => r.institution_id).sort()).toEqual(first.map(r => r.institution_id).sort());

    for (const record of first) {
      const departments = await db.query<{ count: string }>(
        `SELECT COUNT(DISTINCT name)::int AS count FROM departments
          WHERE institution_id = $1 AND status = 'active'
            AND name = ANY($2::text[])`,
        [record.institution_id, ['Production', 'Verification', 'Audit', 'Adversarial', 'Improvement']]
      );
      expect(Number(departments.rows[0].count)).toBe(5);

      const governance = await institutionGovernance.listGovernance(record.institution_id);
      expect(governance.charter).not.toBeNull();
      expect(governance.mandates.length).toBeGreaterThanOrEqual(1);
      expect(governance.powers.length).toBeGreaterThanOrEqual(1);
      expect(governance.limits.length).toBeGreaterThanOrEqual(1);

      const jurisdiction = await db.query(
        `SELECT id FROM institution_jurisdiction_grants
          WHERE institution_id = $1 AND jurisdiction_key = 'global' AND status = 'active'`,
        [record.institution_id]
      );
      expect(jurisdiction.rowCount).toBe(1);
    }
  });

  test('institution charters are append-only and versioned', async () => {
    const seeded = await institutionGovernance.ensureMandatoryInstitutions();
    const evidenceCourt = seeded.find(r => r.name === 'Evidence Court')!;
    const operator = await registerActor('inst-charter');

    const before = await institutionGovernance.getActiveCharter(evidenceCourt.institution_id);
    const draft = await institutionGovernance.proposeCharter({
      institution_id: evidenceCourt.institution_id,
      charter: { name: 'Evidence Court', amendment: Date.now() },
      actor_id: operator,
    });
    expect(draft.version_number).toBeGreaterThan(before!.version_number);
    await institutionGovernance.activateCharter(draft.id, operator);
    const after = await institutionGovernance.getActiveCharter(evidenceCourt.institution_id);
    expect(after!.id).toBe(draft.id);

    await expect(
      db.query(`UPDATE institution_charters SET charter_json = '{}'::jsonb WHERE id = $1`, [draft.id])
    ).rejects.toThrow(/charter content is immutable/);
  });

  test('an institution cannot unilaterally expand its own powers', async () => {
    const seeded = await institutionGovernance.ensureMandatoryInstitutions();
    const treasury = seeded.find(r => r.name === 'Treasury')!;
    const treasuryActor = await institutionGovernance.institutionActorId(treasury.institution_id);
    expect(treasuryActor).not.toBeNull();

    await expect(institutionGovernance.grantPower({
      institution_id: treasury.institution_id,
      power_key: 'unlimited_spending',
      authorized_decision_ref: 'decision:self-serve',
      granted_by_actor_id: treasuryActor!,
    })).rejects.toThrow(/cannot unilaterally expand its own powers/);

    const operator = await registerActor('inst-power');
    await expect(institutionGovernance.grantPower({
      institution_id: treasury.institution_id,
      power_key: 'audit_spending',
      authorized_decision_ref: '',
      granted_by_actor_id: operator,
    })).rejects.toThrow(/authorized_decision_ref/);

    const granted = await institutionGovernance.grantPower({
      institution_id: treasury.institution_id,
      power_key: `audit_spending_${Date.now()}`,
      authorized_decision_ref: 'decision:governance-42',
      granted_by_actor_id: operator,
    });
    expect(granted.id).toBeTruthy();
  });

  test('inter-institution contracts enforce lifecycle, acceptance separation, settlement, and frozen terms', async () => {
    const seeded = await institutionGovernance.ensureMandatoryInstitutions();
    const lab = seeded.find(r => r.name === 'Evaluation Lab')!;
    const court = seeded.find(r => r.name === 'Evidence Court')!;
    const proposer = await registerActor('contract-proposer');
    const acceptor = await registerActor('contract-acceptor');

    const contract = await institutionGovernance.proposeContract({
      from_institution_id: lab.institution_id,
      to_institution_id: court.institution_id,
      title: `Evaluation evidence exchange ${Date.now()}`,
      terms: { deliverable: 'benchmark evidence bundles', cadence: 'weekly' },
      commitments: [{ party: 'Evaluation Lab', commitment: 'deliver bundles' }],
      proposed_by_actor_id: proposer,
    });
    expect(contract.status).toBe('proposed');

    // The proposer cannot accept its own contract.
    await expect(institutionGovernance.transitionContract({
      contract_id: contract.id, to_status: 'accepted', actor_id: proposer,
    })).rejects.toThrow(/cannot be accepted by its own proposer/);

    // Illegal jump proposed -> fulfilled is blocked by the DB guard.
    await expect(institutionGovernance.transitionContract({
      contract_id: contract.id, to_status: 'fulfilled', actor_id: acceptor,
    })).rejects.toThrow();

    await institutionGovernance.transitionContract({
      contract_id: contract.id, to_status: 'accepted', actor_id: acceptor,
    });

    // Terms are frozen after acceptance.
    await expect(
      db.query(`UPDATE inter_institution_contracts SET terms_json = '{}'::jsonb WHERE id = $1`, [contract.id])
    ).rejects.toThrow(/terms are frozen/);

    await institutionGovernance.transitionContract({
      contract_id: contract.id, to_status: 'active', actor_id: acceptor,
    });

    // Breach requires a reason.
    await expect(institutionGovernance.transitionContract({
      contract_id: contract.id, to_status: 'breached', actor_id: acceptor,
    })).rejects.toThrow(/breach requires a reason/);

    const fulfilled = await institutionGovernance.transitionContract({
      contract_id: contract.id, to_status: 'fulfilled', actor_id: acceptor,
      settlement: { delivered_bundles: 4, disputes: 0 },
    });
    expect(fulfilled.status).toBe('fulfilled');

    const row = await db.query(
      `SELECT settlement_json, closed_at FROM inter_institution_contracts WHERE id = $1`,
      [contract.id]
    );
    expect(row.rows[0].settlement_json.delivered_bundles).toBe(4);
    expect(row.rows[0].closed_at).not.toBeNull();

    // Terminal contracts are immutable.
    await expect(institutionGovernance.transitionContract({
      contract_id: contract.id, to_status: 'terminated', actor_id: acceptor,
    })).rejects.toThrow();
  });

  test('institutions attach to exactly one active society', async () => {
    const operator = await registerActor('inst-attach');
    const [core, frontier] = await societyService.ensureDefaultSocieties();
    const institution = await institutionsService.createCanonicalInstitution({
      name: `Attachment Test Institute ${Date.now()}`,
      domain: 'testing',
    });
    const attached = await societyService.attachInstitution({
      society_id: core.id, institution_id: institution.institutionId, actor_id: operator,
    });
    const again = await societyService.attachInstitution({
      society_id: core.id, institution_id: institution.institutionId, actor_id: operator,
    });
    expect(again.id).toBe(attached.id);
    await expect(societyService.attachInstitution({
      society_id: frontier.id, institution_id: institution.institutionId, actor_id: operator,
    })).rejects.toThrow(/already belongs to another active society/);
  });
});
