jest.mock('../src/db/client', () => ({
  query: jest.fn(),
}));
jest.mock('child_process', () => ({
  execFile: jest.fn(),
}));

import crypto from 'crypto';
import fs from 'fs';
import { execFile } from 'child_process';
import { query } from '../src/db/client';
import { getCanonicalCredential, issueCanonicalCredential, verifyCanonicalCredential } from '../src/services/credential.service';

const mockedQuery = query as jest.MockedFunction<typeof query>;
const mockedExecFile = execFile as unknown as jest.Mock;

// Build the exact canonical payload the implementation signs/verifies, so a real
// Ed25519 signature over it will verify. Mirrors verifyCanonicalCredential().
function canonicalPayloadFor(c: {
  credential_id: string; agent_id: string; issued_at: string; expires_at: string;
  cells: unknown[]; overall_log_score: number; overall_brier_score: number;
  sample_count: number; algorithm: string;
}): string {
  return JSON.stringify(c, (_key, value) =>
    typeof value === 'number' ? parseFloat(value.toString()).toFixed(10).replace(/\.?0+$/, '') : value,
  );
}

describe('canonical credential backend boundary', () => {
  beforeEach(() => {
    mockedQuery.mockReset();
    mockedExecFile.mockReset();
  });

  test('returns stored canonical Proof-of-Calibration credential with Ed25519 verification metadata', async () => {
    mockedQuery.mockResolvedValueOnce([
      {
        credential_id: 'cred-1',
        agent_id: 'agent-1',
        issued_at: '2026-06-01T00:00:00.000Z',
        expires_at: '2099-06-01T00:00:00.000Z',
        domain_cells: [{ domain: 'general', horizon_class: 'short' }],
        overall_score: '-0.42',
        sample_count: 7,
        algorithm: 'log_score+brier/hardness_weighted/v1',
        hmac_sha256: 'legacy-only',
        ed25519_signature: 'ed25519-sig',
        is_valid: true,
      },
    ]);

    const response = await getCanonicalCredential('agent-1');

    expect(response).not.toBeNull();
    expect(response!.credential.ed25519_signature).toBe('ed25519-sig');
    expect(response!.credential.legacy_hmac_sha256).toBe('legacy-only');
    expect(response!.verification.command).toBe('python3 reserve/tools/recompute_credential.py agent-1');
    expect(response!.verification.canonical_source).toContain('reserve/credentials/proof_of_calibration.py');
  });

  test('does not synthesize a TypeScript HMAC credential when no stored canonical credential exists', async () => {
    mockedQuery.mockResolvedValueOnce([]);

    const response = await getCanonicalCredential('missing-agent');

    expect(response).toBeNull();
    expect(mockedQuery.mock.calls[0][0]).toContain('FROM calibration_credentials');
  });

  test('issues through Python canonical Reserve boundary', async () => {
    mockedExecFile.mockImplementation((_cmd, args, _opts, cb) => {
      expect(args[0]).toBe('scripts/issue_canonical_credential.py');
      cb(null, JSON.stringify({
        credential: { credential_id: 'cred-issued', agent_id: 'agent-1', ed25519_signature: 'sig' },
        verification: { canonical_source: 'reserve/credentials/proof_of_calibration.py' },
      }), '');
    });

    const issued = await issueCanonicalCredential('agent-1');

    expect((issued.credential as { credential_id: string }).credential_id).toBe('cred-issued');
  });

  test('verify passes only when recompute matches AND the Ed25519 signature is genuine', async () => {
    // Security model B: valid = correctness AND authorship. Sign the real canonical payload.
    const { publicKey, privateKey } = crypto.generateKeyPairSync('ed25519');
    const spki = publicKey.export({ format: 'der', type: 'spki' }) as Buffer;
    const rawPubB64 = spki.subarray(spki.length - 32).toString('base64'); // raw 32-byte key, base64

    const payload = canonicalPayloadFor({
      credential_id: 'cred-1',
      agent_id: 'agent-1',
      issued_at: '2026-06-01T00:00:00.000Z',
      expires_at: '2099-06-01T00:00:00.000Z',
      cells: [],
      overall_log_score: -0.42,
      overall_brier_score: 0,
      sample_count: 7,
      algorithm: 'log_score+brier/hardness_weighted/v1',
    });
    const sigHex = crypto.sign(null, Buffer.from(payload, 'utf-8'), privateKey).toString('hex');

    // Inject our test public key where the service reads reserve/keys/agentco_reserve_public.pem.
    const readSpy = jest.spyOn(fs, 'readFileSync').mockImplementation(((p: unknown, ...rest: unknown[]) => {
      if (String(p).includes('agentco_reserve_public.pem')) return rawPubB64;
      return (jest.requireActual('fs').readFileSync as (...a: unknown[]) => unknown)(p, ...rest);
    }) as typeof fs.readFileSync);

    mockedQuery.mockResolvedValueOnce([
      {
        credential_id: 'cred-1',
        agent_id: 'agent-1',
        issued_at: '2026-06-01T00:00:00.000Z',
        expires_at: '2099-06-01T00:00:00.000Z',
        domain_cells: [],
        overall_score: '-0.42',
        sample_count: 7,
        algorithm: 'log_score+brier/hardness_weighted/v1',
        hmac_sha256: null,
        ed25519_signature: sigHex,
        is_valid: true,
      },
    ]);
    mockedExecFile.mockImplementation((_cmd, args, _opts, cb) => {
      expect(args[0]).toBe('reserve/tools/recompute_credential.py');
      cb(null, JSON.stringify({
        score: { overall_log_score: -0.42, total_sample_count: 7 },
      }), '');
    });

    const verified = await verifyCanonicalCredential('agent-1');

    expect(verified.valid).toBe(true);
    expect(verified.correctness).toBe('passed');
    expect(verified.authorship).toBe('verified');

    readSpy.mockRestore();
  });

  test('verify FAILS when the signature is forged even if the score recomputes (model B)', async () => {
    // Correct score, but a bogus signature -> must be rejected.
    mockedQuery.mockResolvedValueOnce([
      {
        credential_id: 'cred-1',
        agent_id: 'agent-1',
        issued_at: '2026-06-01T00:00:00.000Z',
        expires_at: '2099-06-01T00:00:00.000Z',
        domain_cells: [],
        overall_score: '-0.42',
        sample_count: 7,
        algorithm: 'log_score+brier/hardness_weighted/v1',
        hmac_sha256: null,
        ed25519_signature: 'deadbeef',
        is_valid: true,
      },
    ]);
    mockedExecFile.mockImplementation((_cmd, args, _opts, cb) => {
      cb(null, JSON.stringify({ score: { overall_log_score: -0.42, total_sample_count: 7 } }), '');
    });

    const verified = await verifyCanonicalCredential('agent-1');

    expect(verified.valid).toBe(false);
    expect(verified.correctness).toBe('passed');
    expect(verified.authorship).not.toBe('verified');
  });
});
