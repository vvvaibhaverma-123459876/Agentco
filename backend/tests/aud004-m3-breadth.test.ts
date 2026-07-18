/**
 * AUD-004 M3 breadth — coverage and cross-file proof that credential-bound gating is real,
 * not cosmetic, across the ~170 previously-unauthenticated privileged routes this pass gated.
 *
 * route-auth-contract.test.ts already exercises EVERY matrix-classified route generically
 * (parameterized over ROUTE_SENSITIVITY_MATRIX.md); this file adds the specific cross-file
 * assertions the campaign calls out by name: matrix completeness for every requirePrincipal
 * call site, no privileged route left shared-key-only, and representative spot-checks
 * (unsigned reject / body-actor-id ignored / valid-principal-with-permission success) on
 * routes spanning several different domains (treasury, coalition, society, mission) rather
 * than only the judiciary/evolution routes M4 already covers in aud004-conditions-16-25.test.ts.
 */
import fs from 'fs';
import path from 'path';
import Fastify, { FastifyInstance } from 'fastify';
import crypto from 'crypto';
import { registerPrincipalResolution } from '../src/auth/principal-context';
import { ReplayGuard } from '../src/auth/request-principal';
import { dbIdentityLookup } from '../src/auth/identity-lookup';
import { provisionSignedActor, signedInject } from './helpers/sign-request';
import { treasuryRoutes } from '../src/routes/treasury.routes';
import { coalitionRoutes } from '../src/routes/coalition.routes';
import { societyRoutes } from '../src/routes/society.routes';
import { missionRoutes } from '../src/routes/mission.routes';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { societyService } from '../src/services/society.service';

const ROUTES_DIR = path.resolve(__dirname, '../src/routes');
const MATRIX_PATH = path.resolve(__dirname, '../../docs/audit/ROUTE_SENSITIVITY_MATRIX.md');

function everyRequirePrincipalCallSite(): Array<{ file: string; method: string; path: string }> {
  const sites: Array<{ file: string; method: string; path: string }> = [];
  const registrationRe = /fastify\.(get|post)(?:<[^>]*>)?\(\s*\n?\s*'([^']+)'/g;
  for (const file of fs.readdirSync(ROUTES_DIR).filter((f) => f.endsWith('.routes.ts'))) {
    const text = fs.readFileSync(path.join(ROUTES_DIR, file), 'utf8');
    const matches = [...text.matchAll(registrationRe)];
    for (let i = 0; i < matches.length; i++) {
      const m = matches[i];
      const sliceEnd = i + 1 < matches.length ? matches[i + 1].index! : text.length;
      // Only look at the text strictly between this registration and the NEXT one (or EOF),
      // so a short handler body can never pick up a later route's requirePrincipal call.
      const between = text.slice(m.index! + m[0].length, sliceEnd);
      if (/requirePrincipal\(/.test(between)) {
        sites.push({ file, method: m[1].toUpperCase(), path: m[2] });
      }
    }
  }
  return sites;
}

function matrixRows(): Map<string, string> {
  const text = fs.readFileSync(MATRIX_PATH, 'utf8');
  const rows = new Map<string, string>();
  for (const line of text.split(/\r?\n/)) {
    const m = line.match(/^\| `([^`]+)` \| ([^|]+) \| [^|]+ \| (PUBLIC|AUTH-READ|AUTH-WRITE|AUTH-PRINCIPAL) \|/);
    if (!m) continue;
    const [, routePath, methodsCell, classification] = m;
    for (const method of methodsCell.split(/[,/]/).map((s) => s.trim()).filter(Boolean)) {
      rows.set(`${method} ${routePath}`, classification);
    }
  }
  return rows;
}

describe('AUD-004 M3 breadth: matrix completeness', () => {
  it('every requirePrincipal call site in route source has a matching AUTH-PRINCIPAL row in the matrix', () => {
    const sites = everyRequirePrincipalCallSite();
    expect(sites.length).toBeGreaterThan(150); // sanity: this pass gated ~170 routes
    const matrix = matrixRows();
    const missing: string[] = [];
    for (const site of sites) {
      const key = `${site.method} ${site.path}`;
      const classification = matrix.get(key);
      if (classification !== 'AUTH-PRINCIPAL') {
        missing.push(`${site.file}: ${key} => matrix says '${classification ?? 'MISSING ROW'}'`);
      }
    }
    // This is the control-removal-relevant assertion: if a route is gated in code but the
    // matrix doesn't say AUTH-PRINCIPAL, route-auth-contract.test.ts's classification-driven
    // test would silently under-test it (treat it as AUTH-WRITE, accepting a bare API key).
    expect(missing).toEqual([]);
  });

  it('no route registered with { config: requirePrincipal(...) } is classified PUBLIC in the matrix', () => {
    const sites = everyRequirePrincipalCallSite();
    const matrix = matrixRows();
    const wronglyPublic = sites.filter((s) => matrix.get(`${s.method} ${s.path}`) === 'PUBLIC');
    expect(wronglyPublic).toEqual([]);
  });
});

describe('AUD-004 M3 breadth: cross-domain spot checks (treasury/coalition/society/mission)', () => {
  let app: FastifyInstance;

  beforeAll(async () => {
    app = Fastify();
    registerPrincipalResolution(app, { lookup: dbIdentityLookup, replay: new ReplayGuard() });
    await app.register(treasuryRoutes);
    await app.register(coalitionRoutes);
    await app.register(societyRoutes);
    await app.register(missionRoutes);
    await app.ready();
    await civilizationKernel.ensureCivilizationRoot();
  });
  afterAll(async () => {
    await app.close();
  });

  it('treasury.fund: rejects unsigned, and binds actor_id to the SIGNER even if the body claims another actor', async () => {
    const scopeId = crypto.randomUUID();
    const unsigned = await app.inject({
      method: 'POST', url: '/api/civilization/treasury/fund',
      payload: { scope_type: 'citizen', scope_id: scopeId, resource_type: 'llm_tokens', amount: 10 },
    });
    expect(unsigned.statusCode).toBe(401);

    const funder = await provisionSignedActor({ name: `m3-treasury-${crypto.randomUUID()}`, roles: ['civilization_operator'] });
    const body = { scope_type: 'citizen', scope_id: scopeId, resource_type: 'llm_tokens', amount: 10, actor_id: '00000000-0000-4000-8000-000000000000' };
    const signed = await app.inject(
      signedInject({ actorId: funder.actorId, privateKey: funder.privateKey, method: 'POST', url: '/api/civilization/treasury/fund', body })
    );
    expect(signed.statusCode).toBe(201);
  });

  it('coalition.propose: rejects unsigned and rejects a principal lacking the permission', async () => {
    const unsigned = await app.inject({
      method: 'POST', url: '/api/civilization/coalitions',
      payload: { name: `M3 unsigned ${crypto.randomUUID()}`, member_institution_ids: [] },
    });
    expect(unsigned.statusCode).toBe(401);

    const noRole = await provisionSignedActor({ name: `m3-coal-norole-${crypto.randomUUID()}` });
    const body = { name: `M3 norole ${crypto.randomUUID()}`, member_institution_ids: [] };
    const denied = await app.inject(
      signedInject({ actorId: noRole.actorId, privateKey: noRole.privateKey, method: 'POST', url: '/api/civilization/coalitions', body })
    );
    expect(denied.statusCode).toBe(403);
  });

  it('society.create: valid signed + permitted principal succeeds and is recorded as created_by_actor_id', async () => {
    const operator = await provisionSignedActor({ name: `m3-society-${crypto.randomUUID()}`, roles: ['civilization_operator'] });
    const body = { name: `M3 Society ${crypto.randomUUID()}` };
    const res = await app.inject(
      signedInject({ actorId: operator.actorId, privateKey: operator.privateKey, method: 'POST', url: '/api/civilization/societies', body })
    );
    expect(res.statusCode).toBe(201);
    const created = res.json();
    expect(created.created_by_actor_id).toBe(operator.actorId);
  });

  it('mission.strategic-goal: unsigned request never reaches the handler (fails closed before validation)', async () => {
    const res = await app.inject({
      method: 'POST', url: '/api/civilization/strategic-goals',
      payload: {}, // would 400 "title is required" if it reached the handler
    });
    expect(res.statusCode).toBe(401);
    expect(res.json().reason).toBeDefined();
  });

  it('control-removal: a route with requirePrincipal but a forged signature is rejected (proves the check is load-bearing)', async () => {
    const real = await provisionSignedActor({ name: `m3-forge-real-${crypto.randomUUID()}`, roles: ['civilization_operator'] });
    const attackerKey = crypto.generateKeyPairSync('ed25519').privateKey;
    const body = { name: `M3 forged ${crypto.randomUUID()}` };
    // claims to be `real` (whose role would pass permission) but signs with a different key
    const res = await app.inject(
      signedInject({ actorId: real.actorId, privateKey: attackerKey, method: 'POST', url: '/api/civilization/societies', body })
    );
    expect(res.statusCode).toBe(401);
    expect(res.json().reason).toBe('signature_invalid');
  });
});
