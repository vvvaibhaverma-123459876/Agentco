import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';

export type ResourceType =
  | 'compute'
  | 'llm_tokens'
  | 'tool_calls'
  | 'money'
  | 'time_seconds'
  | 'memory_bytes'
  | 'human_review';

export interface ResourceAccount {
  id: string;
  owner_actor_id: string;
  resource_type: ResourceType;
  unit: string;
  balance: string;
  reserved_balance: string;
  status: 'active' | 'frozen' | 'closed';
  metadata_json: Record<string, unknown>;
}

export interface ResourceTransaction {
  id: string;
  account_id: string;
  actor_id: string;
  transaction_type: 'credit' | 'debit' | 'adjustment';
  amount: string;
  balance_after: string;
  reason: string;
  idempotency_key: string;
  event_log_id: string;
}

export interface CreateAccountInput {
  owner_actor_id: string;
  resource_type: ResourceType;
  unit: string;
  metadata?: Record<string, unknown>;
  correlation_id?: string;
}

export interface TransactionInput {
  account_id: string;
  actor_id: string;
  amount: number;
  reason: string;
  idempotency_key: string;
  correlation_id?: string;
}

export interface ReservationInput extends TransactionInput {
  expires_at: string;
}

export interface ResourceReservation {
  id: string;
  account_id: string;
  actor_id: string;
  amount: string;
  status: 'reserved' | 'settled' | 'released' | 'expired';
  reason: string;
  idempotency_key: string;
  expires_at: string;
  settled_transaction_id: string | null;
  event_log_id: string;
}

const RESOURCE_TYPES = new Set<ResourceType>([
  'compute',
  'llm_tokens',
  'tool_calls',
  'money',
  'time_seconds',
  'memory_bytes',
  'human_review',
]);

function requireUuid(value: string, field: string): void {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)) {
    throw new Error(`${field} must be a UUID`);
  }
}

function requireAmount(value: number): void {
  if (!Number.isFinite(value) || value <= 0) {
    throw new Error('amount must be a positive finite number');
  }
}

function auditContent(fields: Record<string, unknown>): string {
  return JSON.stringify(fields, Object.keys(fields).sort());
}

export class ResourceLedgerService {
  async createAccount(input: CreateAccountInput): Promise<ResourceAccount> {
    this.validateAccount(input);
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.requireActiveActor(client, input.owner_actor_id);
      const result = await client.query<ResourceAccount>(
        `INSERT INTO civilization_resource_accounts (owner_actor_id, resource_type, unit, metadata_json)
         VALUES ($1,$2,$3,$4::jsonb)
         ON CONFLICT (owner_actor_id, resource_type)
         DO UPDATE SET updated_at = civilization_resource_accounts.updated_at
         RETURNING id, owner_actor_id, resource_type, unit, balance, reserved_balance, status, metadata_json`,
        [
          input.owner_actor_id,
          input.resource_type,
          input.unit.trim(),
          JSON.stringify(input.metadata ?? {}),
        ]
      );
      const account = result.rows[0];

      const eventId = await this.writeEventAndAudit(client, {
        actorId: input.owner_actor_id,
        eventType: 'resource.account_created',
        objectType: 'resource_account',
        objectId: account.id,
        payload: {
          account_id: account.id,
          owner_actor_id: account.owner_actor_id,
          resource_type: account.resource_type,
          unit: account.unit,
        },
        correlationId: input.correlation_id,
        inputSummary: `create resource account type=${account.resource_type}`,
        outputSummary: `account_id=${account.id}`,
      });
      if (!eventId) throw new Error('resource account event was not written');

      await client.query('COMMIT');
      return account;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async credit(input: TransactionInput): Promise<ResourceTransaction> {
    return this.applyTransaction('credit', input);
  }

  async debit(input: TransactionInput): Promise<ResourceTransaction> {
    return this.applyTransaction('debit', input);
  }

  async reserve(input: ReservationInput): Promise<ResourceReservation> {
    this.validateReservation(input);
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.requireActiveActor(client, input.actor_id);

      const existing = await client.query<ResourceReservation>(
        `SELECT id, account_id, actor_id, amount, status, reason, idempotency_key,
                expires_at, settled_transaction_id, event_log_id
           FROM civilization_resource_reservations
          WHERE idempotency_key = $1`,
        [input.idempotency_key]
      );
      if ((existing.rowCount ?? 0) > 0) {
        await client.query('COMMIT');
        return existing.rows[0];
      }

      const account = await this.lockActiveAccount(client, input.account_id);
      const available = Number(account.balance) - Number(account.reserved_balance);
      if (available < input.amount) {
        throw new Error(`insufficient available ${account.resource_type} balance`);
      }

      const eventId = await this.writeEventAndAudit(client, {
        actorId: input.actor_id,
        eventType: 'resource.reserved',
        objectType: 'resource_account',
        objectId: input.account_id,
        payload: {
          account_id: input.account_id,
          actor_id: input.actor_id,
          amount: input.amount,
          available_before: available,
          reserved_balance_after: Number(account.reserved_balance) + input.amount,
          reason: input.reason,
          idempotency_key: input.idempotency_key,
          expires_at: input.expires_at,
        },
        correlationId: input.correlation_id,
        inputSummary: `reserve resource amount=${input.amount}`,
        outputSummary: `reserved_until=${input.expires_at}`,
      });

      await client.query(
        `UPDATE civilization_resource_accounts
            SET reserved_balance = reserved_balance + $1,
                updated_at = now()
          WHERE id = $2`,
        [input.amount, input.account_id]
      );

      const reservation = await client.query<ResourceReservation>(
        `INSERT INTO civilization_resource_reservations
           (account_id, actor_id, amount, status, reason, idempotency_key, expires_at, event_log_id)
         VALUES ($1,$2,$3,'reserved',$4,$5,$6,$7)
         RETURNING id, account_id, actor_id, amount, status, reason, idempotency_key,
                   expires_at, settled_transaction_id, event_log_id`,
        [input.account_id, input.actor_id, input.amount, input.reason, input.idempotency_key, input.expires_at, eventId]
      );

      await client.query('COMMIT');
      return reservation.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async settleReservation(reservationId: string, actorId: string, idempotencyKey: string): Promise<ResourceTransaction> {
    requireUuid(reservationId, 'reservation_id');
    requireUuid(actorId, 'actor_id');
    if (!idempotencyKey?.trim()) throw new Error('idempotency_key is required');
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.requireActiveActor(client, actorId);
      const reservation = await this.lockReservation(client, reservationId);
      if (reservation.status === 'settled' && reservation.settled_transaction_id) {
        const existing = await client.query<ResourceTransaction>(
          `SELECT id, account_id, actor_id, transaction_type, amount, balance_after,
                  reason, idempotency_key, event_log_id
             FROM civilization_resource_transactions
            WHERE id = $1`,
          [reservation.settled_transaction_id]
        );
        await client.query('COMMIT');
        return existing.rows[0];
      }
      if (reservation.status !== 'reserved') throw new Error(`reservation is not reserved: ${reservation.status}`);
      if (new Date(reservation.expires_at).getTime() <= Date.now()) {
        await this.expireLockedReservation(client, reservation, actorId);
        throw new Error('reservation expired');
      }

      const account = await this.lockActiveAccount(client, reservation.account_id);
      const amount = Number(reservation.amount);
      const nextBalance = Number(account.balance) - amount;
      const nextReserved = Number(account.reserved_balance) - amount;
      if (nextBalance < 0 || nextReserved < 0) throw new Error(`insufficient reserved ${account.resource_type} balance`);

      const eventId = await this.writeEventAndAudit(client, {
        actorId,
        eventType: 'resource.reservation_settled',
        objectType: 'resource_reservation',
        objectId: reservation.id,
        payload: {
          reservation_id: reservation.id,
          account_id: reservation.account_id,
          actor_id: actorId,
          amount,
          balance_after: nextBalance,
          reserved_balance_after: nextReserved,
          idempotency_key: idempotencyKey,
        },
        inputSummary: `settle reservation amount=${amount}`,
        outputSummary: `balance_after=${nextBalance}`,
      });

      await client.query(
        `UPDATE civilization_resource_accounts
            SET balance = $1,
                reserved_balance = $2,
                updated_at = now()
          WHERE id = $3`,
        [nextBalance, nextReserved, reservation.account_id]
      );

      const transaction = await client.query<ResourceTransaction>(
        `INSERT INTO civilization_resource_transactions
           (account_id, actor_id, transaction_type, amount, balance_after,
            reason, idempotency_key, event_log_id)
         VALUES ($1,$2,'debit',$3,$4,$5,$6,$7)
         RETURNING id, account_id, actor_id, transaction_type, amount, balance_after,
                   reason, idempotency_key, event_log_id`,
        [reservation.account_id, actorId, amount, nextBalance, `settled reservation ${reservation.id}`, idempotencyKey, eventId]
      );
      await client.query(
        `UPDATE civilization_resource_reservations
            SET status = 'settled',
                settled_transaction_id = $1,
                updated_at = now()
          WHERE id = $2`,
        [transaction.rows[0].id, reservation.id]
      );

      await client.query('COMMIT');
      return transaction.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async releaseReservation(reservationId: string, actorId: string): Promise<ResourceReservation> {
    requireUuid(reservationId, 'reservation_id');
    requireUuid(actorId, 'actor_id');
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.requireActiveActor(client, actorId);
      const reservation = await this.lockReservation(client, reservationId);
      if (reservation.status !== 'reserved') {
        await client.query('COMMIT');
        return reservation;
      }
      await this.releaseLockedReservation(client, reservation, actorId, 'resource.reservation_released');
      const updated = await this.getReservationWithClient(client, reservationId);
      await client.query('COMMIT');
      return updated;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async expireReservations(limit = 100): Promise<number> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const expired = await client.query<ResourceReservation>(
        `SELECT id, account_id, actor_id, amount, status, reason, idempotency_key,
                expires_at, settled_transaction_id, event_log_id
           FROM civilization_resource_reservations
          WHERE status = 'reserved' AND expires_at <= now()
          ORDER BY expires_at ASC
          LIMIT $1
          FOR UPDATE`,
        [limit]
      );
      for (const reservation of expired.rows) {
        await this.expireLockedReservation(client, reservation, reservation.actor_id);
      }
      await client.query('COMMIT');
      return expired.rowCount ?? 0;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async getAccount(accountId: string): Promise<ResourceAccount | null> {
    requireUuid(accountId, 'account_id');
    const result = await db.query<ResourceAccount>(
      `SELECT id, owner_actor_id, resource_type, unit, balance, reserved_balance, status, metadata_json
         FROM civilization_resource_accounts
        WHERE id = $1`,
      [accountId]
    );
    return result.rows[0] ?? null;
  }

  private async applyTransaction(
    transactionType: 'credit' | 'debit',
    input: TransactionInput
  ): Promise<ResourceTransaction> {
    this.validateTransaction(input);
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.requireActiveActor(client, input.actor_id);

      const existing = await client.query<ResourceTransaction>(
        `SELECT id, account_id, actor_id, transaction_type, amount, balance_after,
                reason, idempotency_key, event_log_id
           FROM civilization_resource_transactions
          WHERE idempotency_key = $1`,
        [input.idempotency_key]
      );
      if ((existing.rowCount ?? 0) > 0) {
        await client.query('COMMIT');
        return existing.rows[0];
      }

      const account = await this.lockActiveAccount(client, input.account_id);

      const currentBalance = Number(account.balance);
      const currentReserved = Number(account.reserved_balance);
      const nextBalance = transactionType === 'credit'
        ? currentBalance + input.amount
        : currentBalance - input.amount;
      if (nextBalance < currentReserved) {
        throw new Error(`insufficient ${account.resource_type} balance`);
      }

      const eventId = await this.writeEventAndAudit(client, {
        actorId: input.actor_id,
        eventType: transactionType === 'credit' ? 'resource.credited' : 'resource.spent',
        objectType: 'resource_account',
        objectId: input.account_id,
        payload: {
          account_id: input.account_id,
          actor_id: input.actor_id,
          transaction_type: transactionType,
          amount: input.amount,
          balance_before: currentBalance,
          balance_after: nextBalance,
          reason: input.reason,
          idempotency_key: input.idempotency_key,
        },
        correlationId: input.correlation_id,
        inputSummary: `${transactionType} resource amount=${input.amount}`,
        outputSummary: `balance_after=${nextBalance}`,
      });

      await client.query(
        `UPDATE civilization_resource_accounts
            SET balance = $1, updated_at = now()
          WHERE id = $2`,
        [nextBalance, input.account_id]
      );

      const transactionResult = await client.query<ResourceTransaction>(
        `INSERT INTO civilization_resource_transactions
           (account_id, actor_id, transaction_type, amount, balance_after,
            reason, idempotency_key, event_log_id)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
         RETURNING id, account_id, actor_id, transaction_type, amount, balance_after,
                   reason, idempotency_key, event_log_id`,
        [
          input.account_id,
          input.actor_id,
          transactionType,
          input.amount,
          nextBalance,
          input.reason,
          input.idempotency_key,
          eventId,
        ]
      );

      await client.query('COMMIT');
      return transactionResult.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  private validateAccount(input: CreateAccountInput): void {
    requireUuid(input.owner_actor_id, 'owner_actor_id');
    if (!RESOURCE_TYPES.has(input.resource_type)) throw new Error(`invalid resource_type: ${input.resource_type}`);
    if (!input.unit?.trim()) throw new Error('unit is required');
    if (input.correlation_id) requireUuid(input.correlation_id, 'correlation_id');
  }

  private validateTransaction(input: TransactionInput): void {
    requireUuid(input.account_id, 'account_id');
    requireUuid(input.actor_id, 'actor_id');
    requireAmount(input.amount);
    if (!input.reason?.trim()) throw new Error('reason is required');
    if (!input.idempotency_key?.trim()) throw new Error('idempotency_key is required');
    if (input.correlation_id) requireUuid(input.correlation_id, 'correlation_id');
  }

  private validateReservation(input: ReservationInput): void {
    this.validateTransaction(input);
    const expires = new Date(input.expires_at);
    if (Number.isNaN(expires.getTime())) throw new Error('expires_at must be a valid timestamp');
    if (expires.getTime() <= Date.now()) throw new Error('expires_at must be in the future');
  }

  private async lockActiveAccount(client: PoolClient, accountId: string): Promise<ResourceAccount> {
    const accountResult = await client.query<ResourceAccount>(
      `SELECT id, owner_actor_id, resource_type, unit, balance, reserved_balance, status, metadata_json
         FROM civilization_resource_accounts
        WHERE id = $1
        FOR UPDATE`,
      [accountId]
    );
    if (accountResult.rowCount !== 1) throw new Error(`resource account not found: ${accountId}`);
    const account = accountResult.rows[0];
    if (account.status !== 'active') throw new Error(`resource account is not active: ${accountId}`);
    return account;
  }

  private async lockReservation(client: PoolClient, reservationId: string): Promise<ResourceReservation> {
    const result = await client.query<ResourceReservation>(
      `SELECT id, account_id, actor_id, amount, status, reason, idempotency_key,
              expires_at, settled_transaction_id, event_log_id
         FROM civilization_resource_reservations
        WHERE id = $1
        FOR UPDATE`,
      [reservationId]
    );
    if (result.rowCount !== 1) throw new Error(`reservation not found: ${reservationId}`);
    return result.rows[0];
  }

  private async getReservationWithClient(client: PoolClient, reservationId: string): Promise<ResourceReservation> {
    const result = await client.query<ResourceReservation>(
      `SELECT id, account_id, actor_id, amount, status, reason, idempotency_key,
              expires_at, settled_transaction_id, event_log_id
         FROM civilization_resource_reservations
        WHERE id = $1`,
      [reservationId]
    );
    if (result.rowCount !== 1) throw new Error(`reservation not found: ${reservationId}`);
    return result.rows[0];
  }

  private async releaseLockedReservation(
    client: PoolClient,
    reservation: ResourceReservation,
    actorId: string,
    eventType: 'resource.reservation_released' | 'resource.reservation_expired'
  ): Promise<void> {
    const account = await this.lockActiveAccount(client, reservation.account_id);
    const amount = Number(reservation.amount);
    const nextReserved = Number(account.reserved_balance) - amount;
    if (nextReserved < 0) throw new Error(`reserved balance is inconsistent for account ${reservation.account_id}`);
    await this.writeEventAndAudit(client, {
      actorId,
      eventType,
      objectType: 'resource_reservation',
      objectId: reservation.id,
      payload: {
        reservation_id: reservation.id,
        account_id: reservation.account_id,
        actor_id: actorId,
        amount,
        reserved_balance_after: nextReserved,
      },
      inputSummary: `${eventType} amount=${amount}`,
      outputSummary: `reserved_balance_after=${nextReserved}`,
    });
    await client.query(
      `UPDATE civilization_resource_accounts
          SET reserved_balance = $1,
              updated_at = now()
        WHERE id = $2`,
      [nextReserved, reservation.account_id]
    );
    await client.query(
      `UPDATE civilization_resource_reservations
          SET status = $1,
              updated_at = now()
        WHERE id = $2`,
      [eventType === 'resource.reservation_expired' ? 'expired' : 'released', reservation.id]
    );
  }

  private async expireLockedReservation(
    client: PoolClient,
    reservation: ResourceReservation,
    actorId: string
  ): Promise<void> {
    await this.releaseLockedReservation(client, reservation, actorId, 'resource.reservation_expired');
  }

  private async requireActiveActor(client: PoolClient, actorId: string): Promise<void> {
    const result = await client.query('SELECT 1 FROM actors WHERE id = $1 AND status = $2', [actorId, 'active']);
    if (result.rowCount !== 1) throw new Error(`actor is not active: ${actorId}`);
  }

  private async writeEventAndAudit(
    client: PoolClient,
    input: {
      actorId: string;
      eventType: string;
      objectType: string;
      objectId: string;
      payload: Record<string, unknown>;
      correlationId?: string;
      inputSummary: string;
      outputSummary: string;
    }
  ): Promise<string> {
    const timestamp = new Date().toISOString();
    const sessionId = input.correlationId ?? crypto.randomUUID();
    const canonicalEvent = await eventLog.appendWithClient(client, {
      event_type: input.eventType,
      actor_id: input.actorId,
      object_type: input.objectType,
      object_id: input.objectId,
      payload: input.payload,
      correlation_id: sessionId,
      occurred_at: timestamp,
    });

    const previous = await client.query<{ chain_hash: string }>(
      `SELECT chain_hash
         FROM decision_log
        WHERE chain_hash <> ''
        ORDER BY timestamp DESC, log_id DESC
        LIMIT 1`
    );
    const prevHash = previous.rows[0]?.chain_hash ?? '0'.repeat(64);
    const logId = crypto.randomUUID();
    const content = auditContent({
      log_id: logId,
      timestamp,
      prev_hash: prevHash,
      agent_id: input.actorId,
      action_type: 'event_published',
      input_summary: input.inputSummary,
      output_summary: input.outputSummary,
      confidence_score: 1,
      risk_level: 'low',
      human_approved: false,
      human_approver_id: null,
      downstream_events: [canonicalEvent.id],
      session_id: sessionId,
    });
    const chainHash = crypto.createHash('sha256').update(prevHash + content).digest('hex');

    await client.query(
      `INSERT INTO decision_log
         (log_id, agent_id, action_type, input_summary, output_summary,
          confidence_score, risk_level, human_approved, downstream_events,
          session_id, timestamp, chain_hash, prev_hash)
       VALUES ($1,$2,'event_published',$3,$4,1.0,'low',false,$5::uuid[],$6,$7,$8,$9)`,
      [
        logId,
        input.actorId,
        input.inputSummary,
        input.outputSummary,
        [canonicalEvent.id],
        sessionId,
        timestamp,
        chainHash,
        prevHash,
      ]
    );

    return canonicalEvent.id;
  }
}

export const resourceLedger = new ResourceLedgerService();
