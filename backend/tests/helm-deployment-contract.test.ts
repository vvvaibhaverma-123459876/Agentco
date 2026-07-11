import fs from 'fs';
import path from 'path';

const chartRoot = path.resolve(__dirname, '../../infrastructure/kubernetes/helm/agentco');

function readChartFile(relativePath: string): string {
  return fs.readFileSync(path.join(chartRoot, relativePath), 'utf8');
}

function readTemplate(name: string): string {
  return readChartFile(`templates/${name}`);
}

describe('Helm deployment contract', () => {
  test('chart renders the production topology, not only the backend Deployment', () => {
    const templates = fs.readdirSync(path.join(chartRoot, 'templates')).sort();

    expect(templates).toEqual(expect.arrayContaining([
      'deployment.yaml',
      'frontend-deployment.yaml',
      'hpa.yaml',
      'ingress.yaml',
      'migration-job.yaml',
      'outbox-worker-deployment.yaml',
      'pdb.yaml',
      'serviceaccount.yaml',
      'services.yaml',
    ]));
  });

  test('frontend workload receives only server-side service credentials', () => {
    const frontendDeployment = readTemplate('frontend-deployment.yaml');

    expect(frontendDeployment).toContain('name: frontend');
    expect(frontendDeployment).toContain('name: NEXT_PUBLIC_API_URL');
    expect(frontendDeployment).toContain('name: AGENTCO_API_URL');
    expect(frontendDeployment).toContain('name: AGENTCO_API_KEY');
    expect(frontendDeployment).not.toContain('NEXT_PUBLIC_AGENTCO_API_KEY');
  });

  test('backend and frontend Services match ingress service targets', () => {
    const services = readTemplate('services.yaml');
    const ingress = readTemplate('ingress.yaml');

    expect(services).toContain('name: {{ include "agentco.fullname" . }}-backend');
    expect(services).toContain('name: {{ include "agentco.fullname" . }}-frontend');
    expect(ingress).toContain('{{ include "agentco.fullname" $ }}-backend');
    expect(ingress).toContain('{{ include "agentco.fullname" $ }}-frontend');
  });

  test('outbox relay is deployed as a runtime worker', () => {
    const worker = readTemplate('outbox-worker-deployment.yaml');

    expect(worker).toContain('app.kubernetes.io/component: outbox-worker');
    expect(worker).toContain('node", "dist/workers/outbox-worker.js');
    expect(worker).toContain('name: DATABASE_URL');
    expect(worker).toContain('name: KAFKA_BROKERS');
  });

  test('schema migrations run as a Helm hook with separate migration credentials', () => {
    const migrationJob = readTemplate('migration-job.yaml');
    const values = readChartFile('values.yaml');
    const dockerfile = fs.readFileSync(path.resolve(__dirname, '../Dockerfile'), 'utf8');

    expect(migrationJob).toContain('kind: Job');
    expect(migrationJob).toContain('"helm.sh/hook": pre-install,pre-upgrade');
    expect(migrationJob).toContain('command: ["node", "dist/db/migrate.js"]');
    expect(migrationJob).toContain('name: DATABASE_URL');
    expect(migrationJob).toContain('.Values.backend.migrationJob.existingSecret');
    expect(migrationJob).toContain('.Values.backend.migrationJob.databaseUrlKey');
    expect(values).toContain('agentco-migration-secrets');
    expect(values).toContain('databaseUrlKey: MIGRATION_DATABASE_URL');
    expect(dockerfile).toContain('/app/src/db/migrations ./dist/db/migrations');
  });

  test('deployment image tags consume component-specific deploy workflow overrides', () => {
    const backend = readTemplate('deployment.yaml');
    const frontend = readTemplate('frontend-deployment.yaml');
    const deployWorkflow = fs.readFileSync(path.resolve(__dirname, '../../.github/workflows/deploy.yml'), 'utf8');

    expect(deployWorkflow).toContain('--set backend.image.tag=${{ github.sha }}');
    expect(deployWorkflow).toContain('--set frontend.image.tag=${{ github.sha }}');
    expect(backend).toContain('.Values.backend.image.tag | default .Values.global.image.tag');
    expect(frontend).toContain('.Values.frontend.image.tag | default .Values.global.image.tag');
  });

  test('backend deployment wires durable LLM budget and outbox delivery settings', () => {
    const backend = readTemplate('deployment.yaml');

    expect(backend).toContain('name: LLM_RESOURCE_ACTOR_ID');
    expect(backend).toContain('key: LLM_RESOURCE_ACTOR_ID');
    expect(backend).toContain('name: LLM_RESOURCE_ACCOUNT_ID');
    expect(backend).toContain('key: LLM_RESOURCE_ACCOUNT_ID');
    expect(backend).toContain('name: EVENT_BUS_DELIVERY_MODE');
    expect(backend).toContain('name: KAFKA_MANDATORY');
  });

  test('backend image runs as non-root in the final Docker stage', () => {
    const dockerfile = fs.readFileSync(path.resolve(__dirname, '../Dockerfile'), 'utf8');

    expect(dockerfile).toContain('adduser --system --uid 1001 agentco');
    expect(dockerfile).toContain('USER agentco');
  });

  test('frontend container has the public directory expected by its Dockerfile', () => {
    const dockerfile = fs.readFileSync(path.resolve(__dirname, '../../frontend/Dockerfile'), 'utf8');

    expect(dockerfile).toContain('COPY --from=builder /app/public ./public');
    expect(fs.existsSync(path.resolve(__dirname, '../../frontend/public'))).toBe(true);
  });

  test('Redis chart defaults to authenticated secret-backed production cache', () => {
    const values = readChartFile('values.yaml');

    expect(values).toContain('redis:');
    expect(values).toContain('auth:');
    expect(values).toContain('enabled: true');
    expect(values).toContain('existingSecret: agentco-redis-secret');
    expect(values).toContain('existingSecretPasswordKey: password');
  });
});
