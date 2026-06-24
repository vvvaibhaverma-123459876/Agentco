import { db } from '../db/client';
import { v4 as uuidv4 } from 'uuid';

export interface WorkerLease {
  id: string;
  taskId: string;
  workerId: string;
  acquiredAt: Date;
  expiresAt: Date;
  lastHeartbeatAt: Date;
  heartbeatIntervalSeconds: number;
  status: 'active' | 'expired' | 'released';
}

/**
 * Worker Coordinator Service
 *
 * Manages distributed task execution by coordinating leases across multiple workers.
 * Ensures only one worker can execute a task at a time.
 *
 * Features:
 * - Pessimistic locking via database constraints
 * - Automatic lease expiration detection
 * - Heartbeat-based liveness checking
 */
export class WorkerCoordinatorService {
  private workerId: string;
  private heartbeatIntervalSeconds: number = 5;

  constructor(workerId?: string) {
    this.workerId = workerId || `worker-${process.pid}-${Date.now()}`;
  }

  /**
   * Acquire a lease for a task
   * Only succeeds if no other worker has an active lease for this task
   *
   * @param taskId The task to lease
   * @param durationMs How long the lease lasts (in milliseconds)
   * @returns The lease ID if acquired, throws if already leased
   */
  async acquireTaskLease(taskId: string, durationMs: number = 30000): Promise<string> {
    const leaseId = uuidv4();
    const now = new Date();
    const expiresAt = new Date(now.getTime() + durationMs);

    try {
      const result = await db.query(
        `INSERT INTO worker_leases (
          id, task_id, worker_id, lease_acquired_at, lease_expires_at,
          last_heartbeat_at, heartbeat_interval_seconds, status
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
         RETURNING id`,
        [
          leaseId,
          taskId,
          this.workerId,
          now,
          expiresAt,
          now,
          this.heartbeatIntervalSeconds,
          'active',
        ]
      );

      if (result.rows.length === 0) {
        throw new Error('Failed to acquire lease');
      }

      console.log(`[LEASE] Acquired lease ${leaseId} for task ${taskId}`);
      return leaseId;
    } catch (error: any) {
      // UNIQUE constraint violation means another worker already has this task
      if (error.message.includes('unique constraint') || error.code === '23505') {
        throw new Error(`Task ${taskId} is already leased by another worker`);
      }
      throw error;
    }
  }

  /**
   * Renew an existing lease (update heartbeat + extend expiration)
   *
   * @param leaseId The lease to renew
   * @param durationMs How long to extend the lease
   */
  async renewLease(leaseId: string, durationMs: number = 30000): Promise<void> {
    const now = new Date();
    const expiresAt = new Date(now.getTime() + durationMs);

    const result = await db.query(
      `UPDATE worker_leases
       SET last_heartbeat_at = $1, lease_expires_at = $2
       WHERE id = $3 AND status = 'active'
       RETURNING id`,
      [now, expiresAt, leaseId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Lease ${leaseId} not found or already expired`);
    }
  }

  /**
   * Release a lease (mark as released)
   *
   * @param leaseId The lease to release
   */
  async releaseLease(leaseId: string): Promise<void> {
    const result = await db.query(
      `UPDATE worker_leases
       SET status = 'released'
       WHERE id = $1
       RETURNING id`,
      [leaseId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Lease ${leaseId} not found`);
    }

    console.log(`[LEASE] Released lease ${leaseId}`);
  }

  /**
   * Detect and expire leases that have exceeded their deadline
   * Call this periodically (e.g., every 5 seconds) to clean up stale leases
   */
  async detectExpiredLeases(): Promise<number> {
    const result = await db.query(
      `UPDATE worker_leases
       SET status = 'expired'
       WHERE status = 'active' AND lease_expires_at < NOW()
       RETURNING id`
    );

    const expiredCount = result.rows.length;
    if (expiredCount > 0) {
      console.log(`[LEASE] Detected and expired ${expiredCount} stale leases`);
    }
    return expiredCount;
  }

  /**
   * Get an active lease for a task (if it exists)
   */
  async getActiveLease(taskId: string): Promise<WorkerLease | null> {
    const result = await db.query(
      `SELECT id, task_id, worker_id, lease_acquired_at, lease_expires_at,
              last_heartbeat_at, heartbeat_interval_seconds, status
       FROM worker_leases
       WHERE task_id = $1 AND status = 'active'
       LIMIT 1`,
      [taskId]
    );

    if (result.rows.length === 0) {
      return null;
    }

    const row = result.rows[0];
    return {
      id: row.id,
      taskId: row.task_id,
      workerId: row.worker_id,
      acquiredAt: row.lease_acquired_at,
      expiresAt: row.lease_expires_at,
      lastHeartbeatAt: row.last_heartbeat_at,
      heartbeatIntervalSeconds: row.heartbeat_interval_seconds,
      status: row.status,
    };
  }

  /**
   * Check if a task is currently leased by another worker
   */
  async isTaskLeased(taskId: string): Promise<boolean> {
    const lease = await this.getActiveLease(taskId);
    return lease !== null && lease.workerId !== this.workerId;
  }
}

// Export singleton instance
export const workerCoordinator = new WorkerCoordinatorService();
