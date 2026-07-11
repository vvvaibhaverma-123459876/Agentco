import fs from 'fs';
import path from 'path';
import ts from 'typescript';
import { build } from '../src/server';
import { rateLimiterService } from '../src/services/rate-limiter.service';

type Classification = 'PUBLIC' | 'AUTH-READ' | 'AUTH-WRITE';

interface RouteRow {
  route: string;
  method: string;
  classification: Classification;
}

interface SourceRoute {
  route: string;
  method: string;
}

const API_KEY = 'phase4-route-auth-test-key';

function matrixRows(): RouteRow[] {
  const matrix = fs.readFileSync(
    path.resolve(__dirname, '../../docs/audit/ROUTE_SENSITIVITY_MATRIX.md'),
    'utf8'
  );
  const rows: RouteRow[] = [];
  for (const line of matrix.split(/\r?\n/)) {
    const match = line.match(/^\| `([^`]+)` \| ([^|]+) \| [^|]+ \| (PUBLIC|AUTH-READ|AUTH-WRITE) \|/);
    if (!match) continue;
    rows.push({
      route: match[1],
      method: match[2].trim().startsWith('GET') ? 'GET' : match[2].trim(),
      classification: match[3] as Classification,
    });
  }
  return rows;
}

function activeRouteSources(): string[] {
  const routesDir = path.resolve(__dirname, '../src/routes');
  return [
    ...fs.readdirSync(routesDir)
      .filter((file) => file.endsWith('.ts'))
      .map((file) => path.join(routesDir, file)),
    path.resolve(__dirname, '../src/services/learning.service.ts'),
    path.resolve(__dirname, '../src/server.ts'),
  ];
}

function activeRoutes(): SourceRoute[] {
  const rows: SourceRoute[] = [];
  for (const file of activeRouteSources()) {
    const sourceText = fs.readFileSync(file, 'utf8');
    const source = ts.createSourceFile(file, sourceText, ts.ScriptTarget.Latest, true);
    function visit(node: ts.Node): void {
      if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression)) {
        const objectName = node.expression.expression.getText(source);
        const method = node.expression.name.text.toUpperCase();
        const pathArg = node.arguments[0];
        if (
          ['fastify', 'app'].includes(objectName) &&
          ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'].includes(method) &&
          pathArg &&
          ts.isStringLiteral(pathArg)
        ) {
          rows.push({ route: pathArg.text, method });
        }
      }
      ts.forEachChild(node, visit);
    }
    visit(source);
  }
  return rows.sort((a, b) => `${a.method} ${a.route}`.localeCompare(`${b.method} ${b.route}`));
}

function routeKey(route: SourceRoute): string {
  return `${route.method} ${route.route}`;
}

function activeRouteSourceTexts(): Array<{ file: string; text: string }> {
  return activeRouteSources().map((file) => ({ file, text: fs.readFileSync(file, 'utf8') }));
}

function sampleUrl(route: string): string {
  return route.replace(/:([A-Za-z_][A-Za-z0-9_]*)/g, (_match, name: string) => {
    if (name.toLowerCase().includes('index')) return '1';
    if (name.toLowerCase().includes('type')) return 'institution';
    return `test-${name.toLowerCase().replace(/_/g, '-')}`;
  });
}

describe('route auth sensitivity matrix', () => {
  const savedKey = process.env.AGENTCO_API_KEY;
  let app: Awaited<ReturnType<typeof build>>;
  const rows = matrixRows();

  beforeAll(async () => {
    process.env.AGENTCO_API_KEY = API_KEY;
    app = await build();
  });

  afterAll(async () => {
    await app.close();
    if (savedKey === undefined) delete process.env.AGENTCO_API_KEY;
    else process.env.AGENTCO_API_KEY = savedKey;
  });

  afterEach(() => rateLimiterService.resetAll());

  test('matrix accounts for every active explicit route registration', () => {
    const fromMatrix = rows.map(routeKey).sort();
    const fromSource = activeRoutes().map(routeKey).sort();
    expect(fromMatrix).toEqual(fromSource);
  });

  test('only the minimal liveness probe is public', () => {
    expect(rows.filter((row) => row.classification === 'PUBLIC')).toEqual([
      { route: '/health', method: 'GET', classification: 'PUBLIC' },
      { route: '/health/detailed', method: 'GET', classification: 'PUBLIC' },
      { route: '/health/live', method: 'GET', classification: 'PUBLIC' },
      { route: '/health/ready', method: 'GET', classification: 'PUBLIC' },
    ]);
  });

  test.each(rows)('$method $route enforces its matrix classification', async (row) => {
    rateLimiterService.resetAll();
    const unauthenticated = await app.inject({
      method: row.method as any,
      url: sampleUrl(row.route),
      payload: row.method === 'GET' ? undefined : {},
    });

    if (row.classification === 'PUBLIC') {
      expect(unauthenticated.statusCode).not.toBe(401);
    } else {
      expect(unauthenticated.statusCode).toBe(401);
      expect(unauthenticated.json()).toEqual({ error: 'unauthorized' });
    }

    rateLimiterService.resetAll();
    const authenticated = await app.inject({
      method: row.method as any,
      url: sampleUrl(row.route),
      headers: { 'x-api-key': API_KEY },
      payload: row.method === 'GET' ? undefined : {},
    });
    expect(authenticated.statusCode).not.toBe(401);
  });

  test('unclassified routes default to protected', async () => {
    const freshApp = await build();
    freshApp.get('/phase4-unclassified-route', async () => ({ ok: true }));

    rateLimiterService.resetAll();
    const unauthenticated = await freshApp.inject({ method: 'GET', url: '/phase4-unclassified-route' });
    expect(unauthenticated.statusCode).toBe(401);
    expect(unauthenticated.json()).toEqual({ error: 'unauthorized' });

    rateLimiterService.resetAll();
    const authenticated = await freshApp.inject({
      method: 'GET',
      url: '/phase4-unclassified-route',
      headers: { 'x-api-key': API_KEY },
    });
    expect(authenticated.statusCode).toBe(200);
    await freshApp.close();
  });

  test('HEAD has the same auth posture as GET on protected routes', async () => {
    rateLimiterService.resetAll();
    const getResponse = await app.inject({ method: 'GET', url: '/api/agents' });

    rateLimiterService.resetAll();
    const headResponse = await app.inject({ method: 'HEAD', url: '/api/agents' });

    expect(getResponse.statusCode).toBe(401);
    expect(headResponse.statusCode).toBe(401);
  });

  test('trailing slash and path case variants do not bypass auth', async () => {
    for (const url of ['/api/agents/', '/API/AGENTS']) {
      rateLimiterService.resetAll();
      const unauthenticated = await app.inject({ method: 'GET', url });
      expect(unauthenticated.statusCode).toBe(401);
      expect(unauthenticated.json()).toEqual({ error: 'unauthorized' });

      rateLimiterService.resetAll();
      const authenticated = await app.inject({
        method: 'GET',
        url,
        headers: { 'x-api-key': API_KEY },
      });
      expect(authenticated.statusCode).toBe(404);
      expect(authenticated.json()).toEqual(expect.objectContaining({ error: expect.any(String) }));
    }
  });

  test('invalid UUID path params return a sanitized 400', async () => {
    rateLimiterService.resetAll();
    const response = await app.inject({
      method: 'GET',
      url: '/api/agents/tasks/not-a-uuid',
      headers: { 'x-api-key': API_KEY },
    });

    expect(response.statusCode).toBe(400);
    expect(response.json()).toEqual({ error: 'Invalid path parameter', id: expect.any(String) });
  });

  test('forced handler errors return sanitized 500s with correlation ids', async () => {
    const freshApp = await build();
    freshApp.get('/phase7-forced-throw', async () => {
      throw new Error('raw database driver detail should not cross the wire');
    });

    rateLimiterService.resetAll();
    const response = await freshApp.inject({
      method: 'GET',
      url: '/phase7-forced-throw',
      headers: { 'x-api-key': API_KEY },
    });

    expect(response.statusCode).toBe(500);
    expect(response.json()).toEqual({ error: 'Internal server error', id: expect.any(String) });
    expect(response.body).not.toContain('raw database driver detail');
    await freshApp.close();
  });

  test('active route handlers do not return caught exception messages directly', () => {
    const forbidden = [
      /send\(\{[\s\S]*?error:\s*(?:error|err|e)\.message[\s\S]*?\}\)/,
      /send\(\{[\s\S]*?message:\s*error\.message[\s\S]*?\}\)/,
      /send\(\{[\s\S]*?error:\s*String\(e\)[\s\S]*?\}\)/,
    ];
    const offenders = activeRouteSourceTexts().flatMap(({ file, text }) =>
      forbidden.some((pattern) => pattern.test(text)) ? [path.relative(path.resolve(__dirname, '..'), file)] : []
    );

    expect(offenders).toEqual([]);
  });
});
