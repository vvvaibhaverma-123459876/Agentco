jest.mock('../src/db/client', () => ({
  query: jest.fn(),
}));
jest.mock('child_process', () => ({
  execFile: jest.fn(),
}));

import { execFile } from 'child_process';
import { query } from '../src/db/client';
import { getCanonicalCredential, issueCanonicalCredential, verifyCanonicalCredential } from '../src/services/credential.service';

const mockedQuery = query as jest.MockedFunction<typeof query>;
const mockedExecFile = execFile as unknown as jest.Mock;

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

  test('verify route helper compares stored credential with recomputation output', async () => {
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
        ed25519_signature: 'sig',
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
    expect(verified.authorship).toBe('signature_present_verify_with_public_key');
  });
});
