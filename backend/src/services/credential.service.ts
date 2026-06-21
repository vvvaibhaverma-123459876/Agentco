import { execFile } from 'child_process';
import path from 'path';
import fs from 'fs';
import crypto from 'crypto';
import { query } from '../db/client';

interface StoredCredentialRow {
  credential_id: string;
  agent_id: string;
  issued_at: string;
  expires_at: string;
  domain_cells: unknown;
  overall_score: string | number;
  sample_count: number;
  algorithm: string;
  hmac_sha256: string | null;
  ed25519_signature: string | null;
  is_valid: boolean;
}

export interface BackendCredentialResponse {
  credential: Record<string, unknown>;
  verification: {
    correctness: string;
    authorship: string;
    command: string;
    expired: boolean;
    canonical_source: string;
  };
}

function repoRoot(): string {
  return path.resolve(__dirname, '..', '..', '..');
}

function loadReservePublicKey(): Buffer | null {
  try {
    const keyPath = path.resolve(repoRoot(), 'reserve', 'keys', 'agentco_reserve_public.pem');
    const base64Content = fs.readFileSync(keyPath, 'utf-8').trim();
    return Buffer.from(base64Content, 'base64');
  } catch {
    return null;
  }
}

function verifyEd25519Signature(
  signatureHex: string,
  payloadJson: string,
  publicKeyBytes: Buffer,
): boolean {
  try {
    const signatureBuffer = Buffer.from(signatureHex, 'hex');
    const keyObject = crypto.createPublicKey({
      key: publicKeyBytes,
      format: 'raw',
      type: 'ed25519',
    });
    return crypto.verify(
      null,
      Buffer.from(payloadJson, 'utf-8'),
      keyObject,
      signatureBuffer,
    );
  } catch {
    return false;
  }
}

function runPythonJson(script: string, args: string[]): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const root = repoRoot();
    execFile('python3', [script, ...args], { cwd: root, env: process.env }, (error, stdout, stderr) => {
      if (error) {
        const message = stderr?.trim() || error.message;
        reject(new Error(message));
        return;
      }
      try {
        resolve(JSON.parse(stdout));
      } catch (parseError) {
        reject(new Error(`canonical credential command returned non-JSON output: ${String(parseError)}`));
      }
    });
  });
}

export async function getCanonicalCredential(agentId: string): Promise<BackendCredentialResponse | null> {
  const rows = await query<StoredCredentialRow>(
    `SELECT credential_id, agent_id, issued_at, expires_at, domain_cells,
            overall_score, sample_count, algorithm, hmac_sha256,
            ed25519_signature, is_valid
       FROM calibration_credentials
      WHERE agent_id = $1
        AND is_valid = TRUE
      ORDER BY issued_at DESC
      LIMIT 1`,
    [agentId],
  );

  if (rows.length === 0) return null;

  const row = rows[0];
  const expired = new Date(String(row.expires_at)).getTime() <= Date.now();
  return {
    credential: {
      credential_id: row.credential_id,
      agent_id: row.agent_id,
      issued_at: row.issued_at,
      expires_at: row.expires_at,
      cells: row.domain_cells,
      overall_log_score: Number(row.overall_score),
      sample_count: Number(row.sample_count),
      algorithm: row.algorithm,
      ed25519_signature: row.ed25519_signature ?? '',
      legacy_hmac_sha256: row.hmac_sha256 ?? '',
      expired,
    },
    verification: {
      correctness: 'recompute from resolved, non-post-hoc prediction_ledger rows',
      authorship: 'verify Ed25519 signature with reserve/keys/agentco_reserve_public.pem when ed25519_signature is present',
      command: `python3 reserve/tools/recompute_credential.py ${agentId}`,
      expired,
      canonical_source: 'reserve/credentials/proof_of_calibration.py',
    },
  };
}

export async function issueCanonicalCredential(agentId: string): Promise<Record<string, unknown>> {
  return runPythonJson('scripts/issue_canonical_credential.py', [agentId]);
}

export async function verifyCanonicalCredential(agentId: string): Promise<Record<string, unknown>> {
  const stored = await getCanonicalCredential(agentId);
  if (!stored) {
    return {
      valid: false,
      correctness: 'no stored canonical credential',
      authorship: 'not_checked',
      recompute_command: `python3 reserve/tools/recompute_credential.py ${agentId}`,
    };
  }
  try {
    const recomputed = await runPythonJson('reserve/tools/recompute_credential.py', [agentId]);
    const score = (recomputed.score ?? {}) as Record<string, unknown>;
    const credential = stored.credential;
    const storedLog = Number(credential.overall_log_score);
    const recomputedLog = Number(score.overall_log_score);
    const storedCount = Number(credential.sample_count);
    const recomputedCount = Number(score.total_sample_count);
    const correctnessValid = Math.abs(storedLog - recomputedLog) < 1e-9 && storedCount === recomputedCount;

    let authorshipValid = false;
    let authorshipStatus = 'not_checked';
    if (credential.ed25519_signature) {
      const pubKeyBytes = loadReservePublicKey();
      if (pubKeyBytes) {
        const canonicalPayload = JSON.stringify(
          {
            credential_id: credential.credential_id,
            agent_id: credential.agent_id,
            issued_at: credential.issued_at,
            expires_at: credential.expires_at,
            cells: Array.isArray(credential.cells) ? credential.cells : [],
            overall_log_score: storedLog,
            overall_brier_score: credential.overall_brier_score ?? 0,
            sample_count: storedCount,
            algorithm: credential.algorithm,
          },
          (key: string, value: unknown) => {
            if (typeof value === 'number') {
              return parseFloat(value.toString()).toFixed(10).replace(/\.?0+$/, '');
            }
            return value;
          },
        );
        authorshipValid = verifyEd25519Signature(
          credential.ed25519_signature,
          canonicalPayload,
          pubKeyBytes,
        );
        authorshipStatus = authorshipValid ? 'verified' : 'verification_failed';
      } else {
        authorshipStatus = 'public_key_unavailable';
      }
    } else {
      authorshipStatus = 'no_ed25519_signature_present';
    }

    return {
      valid: correctnessValid && authorshipValid,
      correctness: correctnessValid ? 'passed' : 'failed',
      authorship: authorshipStatus,
      recompute_command: `python3 reserve/tools/recompute_credential.py ${agentId}`,
      stored: {
        overall_log_score: storedLog,
        sample_count: storedCount,
        expired: credential.expired,
      },
      recomputed: {
        overall_log_score: recomputedLog,
        sample_count: recomputedCount,
      },
    };
  } catch (error) {
    const credential = stored.credential;
    let authorshipStatus = 'not_checked';
    if (credential.ed25519_signature) {
      const pubKeyBytes = loadReservePublicKey();
      authorshipStatus = pubKeyBytes ? 'verification_skipped_due_to_recompute_error' : 'public_key_unavailable';
    }
    return {
      valid: false,
      correctness: 'recompute_failed',
      authorship: authorshipStatus,
      error: String(error instanceof Error ? error.message : error),
      recompute_command: `python3 reserve/tools/recompute_credential.py ${agentId}`,
    };
  }
}
