import { durableExecution } from '../services/durable-execution.service';
import { shutdownRuntimeResources } from '../runtime/shutdown';

async function main(): Promise<void> {
  const task = await durableExecution.enqueue('ceo-agent', 'health_check', {
    probe: 'durable-smoke',
    timestamp: new Date().toISOString(),
  });
  const result = await durableExecution.run(task.task_id);
  console.log(JSON.stringify({
    task_id: result.task_id,
    status: result.status,
    kind: (result.result as any)?.kind,
    attested: Boolean(result.action_attestation_id),
  }));
}

if (require.main === module) {
  main()
    .catch(error => {
      console.error(error);
      process.exitCode = 1;
    })
    .finally(async () => {
      await shutdownRuntimeResources({ closeDb: true });
    });
}
