import crypto from 'crypto';
import { query } from '../db/client';

const ALGORITHM = 'log_score+brier/hardness_weighted/v1';
const EPSILON = 1e-9;

interface LedgerRow {
  prediction_id: string;
  probability: string | number;
  resolved_outcome: boolean;
  domain: string;
  horizon_class: string;
  consequence: boolean;
  resolved_at: string;
}

function hardness(p: number): number {
  return 2.0 * p * (1.0 - p);
}

function weight(p: number, consequence: boolean): number {
  return hardness(p) * (consequence ? 2.0 : 1.0);
}

function logScore(pRaw: number, outcome: boolean): number {
  const p = Math.max(Math.min(pRaw, 1.0 - EPSILON), EPSILON);
  return outcome ? Math.log(p) : Math.log(1.0 - p);
}

function brierScore(p: number, outcome: boolean): number {
  const o = outcome ? 1.0 : 0.0;
  return (p - o) ** 2;
}

function sortForJson(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortForJson);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, item]) => [key, sortForJson(item)]),
    );
  }
  return value;
}

function canonicalPayload(payload: Record<string, unknown>): string {
  return JSON.stringify(sortForJson(payload));
}

export async function issueCredential(agentId: string) {
  const rows = await query<LedgerRow>(
    `SELECT prediction_id, probability, resolved_outcome, domain, horizon_class,
            COALESCE(consequence, FALSE) AS consequence, resolved_at
       FROM prediction_ledger
      WHERE producing_agent_id = $1
        AND resolved = TRUE
        AND resolved_outcome IS NOT NULL
        AND (post_hoc IS NULL OR post_hoc = FALSE)
      ORDER BY resolved_at`,
    [agentId],
  );

  if (rows.length === 0) return null;

  const grouped = new Map<string, LedgerRow[]>();
  for (const row of rows) {
    const key = `${row.domain}\u0000${row.horizon_class}`;
    grouped.set(key, [...(grouped.get(key) ?? []), row]);
  }

  const cells = Array.from(grouped.entries()).sort(([a], [b]) => a.localeCompare(b)).map(([key, cellRows]) => {
    const [domain, horizon_class] = key.split('\u0000');
    let totalWeight = 0;
    let weightedLog = 0;
    let weightedBrier = 0;
    let sharpness = 0;
    let lastRealityContact = '';

    for (const row of cellRows) {
      const p = Number(row.probability);
      const w = weight(p, row.consequence);
      totalWeight += w;
      weightedLog += w * logScore(p, row.resolved_outcome);
      weightedBrier += w * brierScore(p, row.resolved_outcome);
      sharpness += p * (1.0 - p);
      if (!lastRealityContact || String(row.resolved_at) > lastRealityContact) {
        lastRealityContact = String(row.resolved_at);
      }
    }

    return {
      domain,
      horizon_class,
      weighted_log_score: totalWeight > 0 ? weightedLog / totalWeight : 0,
      weighted_brier_score: totalWeight > 0 ? weightedBrier / totalWeight : 0,
      sharpness: sharpness / cellRows.length,
      sample_count: cellRows.length,
      total_weight: totalWeight,
      last_reality_contact: lastRealityContact,
    };
  });

  const overallLog = cells.reduce((sum, cell) => sum + cell.weighted_log_score, 0) / cells.length;
  const overallBrier = cells.reduce((sum, cell) => sum + cell.weighted_brier_score, 0) / cells.length;
  const issuedAt = new Date();
  const expiresAt = new Date(issuedAt.getTime() + 30 * 24 * 60 * 60 * 1000);
  const credential = {
    credential_id: crypto.randomUUID(),
    agent_id: agentId,
    issued_at: issuedAt.toISOString(),
    expires_at: expiresAt.toISOString(),
    cells,
    overall_log_score: overallLog,
    overall_brier_score: overallBrier,
    sample_count: rows.length,
    algorithm: ALGORITHM,
  };
  const signingKey = process.env.RESERVE_SIGNING_KEY || 'dev-insecure-key';
  const hmac_sha256 = crypto.createHmac('sha256', signingKey).update(canonicalPayload(credential)).digest('hex');

  return {
    ...credential,
    hmac_sha256,
    recompute: {
      command: `python3 reserve/tools/recompute_credential.py ${agentId}`,
      description: 'Recomputes this score from public prediction_ledger rows without any signing secret.',
    },
  };
}
