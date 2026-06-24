import crypto from 'crypto';
import { query } from '../db/client';

const { privateKey, publicKey } = crypto.generateKeyPairSync('ed25519');

export interface ActionAttestationInput {
  intent_id?: string | null;
  principal_id: string;
  tool_id?: string | null;
  policy_id?: string | null;
  input: unknown;
  output?: unknown;
  evidence_refs?: string[];
  trusted_confidence?: number | null;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  tee_quote?: string | null;
}

function hash(value: unknown): string {
  return crypto.createHash('sha256').update(JSON.stringify(value ?? null)).digest('hex');
}

function signPayload(payload: object): string {
  return crypto.sign(null, Buffer.from(JSON.stringify(payload)), privateKey).toString('hex');
}

export class ProvenanceService {
  async attestAction(input: ActionAttestationInput): Promise<{ action_id: string; signature_ed25519: string }> {
    await query(
      `INSERT INTO principals (principal_id, principal_type, status)
       VALUES ($1, 'agent', 'active')
       ON CONFLICT (principal_id) DO NOTHING`,
      [input.principal_id],
    );
    const input_hash = hash(input.input);
    const output_hash = hash(input.output);
    const payload = {
      principal_id: input.principal_id,
      tool_id: input.tool_id ?? null,
      input_hash,
      output_hash,
      risk_level: input.risk_level,
      trusted_confidence: input.trusted_confidence ?? null,
    };
    const signature = signPayload(payload);
    const rows = await query<{ action_id: string }>(
      `INSERT INTO action_attestations
         (intent_id, principal_id, tool_id, policy_id, input_hash, output_hash,
          evidence_refs, trusted_confidence, risk_level, tee_quote, signature_ed25519,
          transparency_ref)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
       RETURNING action_id`,
      [
        input.intent_id ?? null,
        input.principal_id,
        input.tool_id ?? null,
        input.policy_id ?? null,
        input_hash,
        output_hash,
        input.evidence_refs ?? [],
        input.trusted_confidence ?? null,
        input.risk_level,
        input.tee_quote ?? null,
        signature,
        `local-transparency:${input_hash.slice(0, 16)}`,
      ],
    );
    return { action_id: rows[0].action_id, signature_ed25519: signature };
  }

  verifyDetached(payload: object, signatureHex: string): boolean {
    return crypto.verify(null, Buffer.from(JSON.stringify(payload)), publicKey, Buffer.from(signatureHex, 'hex'));
  }
}

export const provenance = new ProvenanceService();
