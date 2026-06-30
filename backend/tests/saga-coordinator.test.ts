import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { sagaCoordinator } from '../src/services/saga-coordinator.service';

async function applyMigrations() {
  for (const name of [
    '079_identity_authority.sql',
    '080_event_log.sql',
    '083_transactional_outbox.sql',
    '019_durable_execution.sql',
    '100_saga_coordinator.sql',
  ]) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await db.query(migration);
  }
}

async function createActor(prefix: string) {
  return identityAuthorityService.registerActor({
    actor_type: 'service',
    name: `${prefix}-${Date.now()}-${Math.random()}`,
    service_identity: {
      service_name: `${prefix}-${Date.now()}-${Math.random()}`,
      scopes: ['saga.execute'],
    },
  });
}

describe('saga coordinator', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('coordinates multi-step saga success with canonical event/outbox provenance', async () => {
    const actor = await createActor('saga-success-service');
    const saga = await sagaCoordinator.startSaga({
      saga_type: 'customer_onboarding',
      actor_id: actor.id,
      payload: { customer_id: 'cust-1' },
    });
    const provision = await sagaCoordinator.addStep({
      saga_id: saga.id,
      step_name: 'provision_workspace',
      step_order: 0,
      payload: { workspace: 'cust-1' },
    });
    const notify = await sagaCoordinator.addStep({
      saga_id: saga.id,
      step_name: 'notify_customer',
      step_order: 1,
      payload: { template: 'welcome' },
    });

    await sagaCoordinator.startStep(provision.id);
    await sagaCoordinator.completeStep(provision.id, { workspace_id: 'ws-1' });
    await sagaCoordinator.startStep(notify.id);
    await sagaCoordinator.completeStep(notify.id, { message_id: 'msg-1' });
    const completed = await sagaCoordinator.completeSaga(saga.id);
    const stored = await sagaCoordinator.getSaga(saga.id);

    expect(completed.status).toBe('completed');
    expect(stored?.steps.map(step => step.status)).toEqual(['completed', 'completed']);

    const events = await db.query(
      `SELECT id, event_type FROM event_log
        WHERE correlation_id = $1
          AND event_type LIKE 'saga.%'
        ORDER BY occurred_at ASC`,
      [saga.correlation_id]
    );
    expect(events.rows.map(row => row.event_type)).toEqual(expect.arrayContaining([
      'saga.started',
      'saga.step_added',
      'saga.step_started',
      'saga.step_completed',
      'saga.completed',
    ]));

    const outbox = await db.query(
      `SELECT COUNT(*)::int AS count
         FROM event_outbox
        WHERE event_log_id = ANY($1::uuid[])`,
      [events.rows.map(row => row.id)]
    );
    expect(outbox.rows[0].count).toBe(events.rowCount);
  });

  test('marks completed steps compensation-pending when a later step fails', async () => {
    const actor = await createActor('saga-compensation-service');
    const saga = await sagaCoordinator.startSaga({
      saga_type: 'billing_change',
      actor_id: actor.id,
      payload: { account_id: 'acct-1' },
    });
    const reserve = await sagaCoordinator.addStep({
      saga_id: saga.id,
      step_name: 'reserve_credit',
      step_order: 0,
      compensation_payload: { action: 'release_credit' },
    });
    const charge = await sagaCoordinator.addStep({
      saga_id: saga.id,
      step_name: 'charge_card',
      step_order: 1,
    });

    await sagaCoordinator.startStep(reserve.id);
    await sagaCoordinator.completeStep(reserve.id, { reservation_id: 'res-1' });
    await sagaCoordinator.startStep(charge.id);
    const failed = await sagaCoordinator.failStepAndCompensate(charge.id, 'card declined');
    let stored = await sagaCoordinator.getSaga(saga.id);

    expect(failed.status).toBe('compensating');
    expect(failed.failure_reason).toBe('card declined');
    expect(stored?.steps.map(step => [step.step_name, step.status])).toEqual([
      ['reserve_credit', 'compensation_pending'],
      ['charge_card', 'failed'],
    ]);

    await sagaCoordinator.markStepCompensated(reserve.id, { released: true });
    stored = await sagaCoordinator.getSaga(saga.id);

    expect(stored?.status).toBe('compensated');
    expect(stored?.steps[0].status).toBe('compensated');
  });
});
