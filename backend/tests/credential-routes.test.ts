jest.mock('../src/services/credential.service', () => ({
  getCanonicalCredential: jest.fn(),
  issueCanonicalCredential: jest.fn(),
  verifyCanonicalCredential: jest.fn(),
}));

import { build } from '../src/server';
import {
  getCanonicalCredential,
  issueCanonicalCredential,
  verifyCanonicalCredential,
} from '../src/services/credential.service';

const key = 'dev-api-key';
const issuerHeaders = { 'x-agentco-api-key': key, 'x-agentco-role': 'reserve_issuer' };
const resolverHeaders = { 'x-agentco-api-key': key, 'x-agentco-role': 'resolver_service' };

describe('credential routes canonical boundary', () => {
  beforeEach(() => {
    (getCanonicalCredential as jest.Mock).mockReset();
    (issueCanonicalCredential as jest.Mock).mockReset();
    (verifyCanonicalCredential as jest.Mock).mockReset();
  });

  test('issue route requires credential issuer scope', async () => {
    const app = await build();
    const denied = await app.inject({
      method: 'POST',
      url: '/api/credential/agent-1/issue',
      headers: resolverHeaders,
    });
    expect(denied.statusCode).toBe(403);
    await app.close();
  });

  test('issue route returns canonical Python issuer output', async () => {
    (issueCanonicalCredential as jest.Mock).mockResolvedValueOnce({
      credential: { credential_id: 'cred-1', agent_id: 'agent-1' },
      verification: { canonical_source: 'reserve/credentials/proof_of_calibration.py' },
    });
    const app = await build();
    const issued = await app.inject({
      method: 'POST',
      url: '/api/credential/agent-1/issue',
      headers: issuerHeaders,
    });
    expect(issued.statusCode).toBe(201);
    expect(JSON.parse(issued.payload).credential.credential_id).toBe('cred-1');
    await app.close();
  });

  test('verify route returns correctness and authorship fields', async () => {
    (verifyCanonicalCredential as jest.Mock).mockResolvedValueOnce({
      valid: true,
      correctness: 'passed',
      authorship: 'signature_present_verify_with_public_key',
    });
    const app = await build();
    const verified = await app.inject({
      method: 'POST',
      url: '/api/credential/agent-1/verify',
      headers: issuerHeaders,
    });
    expect(verified.statusCode).toBe(200);
    expect(JSON.parse(verified.payload).correctness).toBe('passed');
    expect(JSON.parse(verified.payload).authorship).toContain('signature');
    await app.close();
  });

  test('issuer failure with no resolved predictions returns clear 404', async () => {
    (issueCanonicalCredential as jest.Mock).mockRejectedValueOnce(
      new Error("no resolved non-post-hoc predictions for agent_id='agent-1'"),
    );
    const app = await build();
    const issued = await app.inject({
      method: 'POST',
      url: '/api/credential/agent-1/issue',
      headers: issuerHeaders,
    });
    expect(issued.statusCode).toBe(404);
    expect(JSON.parse(issued.payload).error).toBe('canonical credential issuance failed');
    await app.close();
  });
});
