/**
 * Deterministic Ed25519 signer for decision receipts.
 *
 * The key derives from RECEIPT_SIGNING_SEED (32-byte hex) so signatures survive
 * process restarts and receipts remain verifiable across deployments of the
 * same environment — unlike provenance.service's ephemeral per-process key.
 * Receipts embed the public key (SPKI PEM); verification never needs the seed.
 *
 * Fail-closed in production-like environments: a missing seed refuses to sign
 * rather than silently falling back to an ephemeral key that would make every
 * receipt unverifiable after the next restart.
 */
import crypto from 'crypto';
import { isProductionEnv } from '../security';

// PKCS#8 DER prefix for a raw Ed25519 private key (RFC 8410).
const PKCS8_ED25519_PREFIX = Buffer.from('302e020100300506032b657004220420', 'hex');

let cached: { privateKey: crypto.KeyObject; publicKeyPem: string } | null = null;

function loadKey(): { privateKey: crypto.KeyObject; publicKeyPem: string } {
  if (cached) return cached;

  const seedHex = process.env.RECEIPT_SIGNING_SEED;
  if (!seedHex || !/^[0-9a-fA-F]{64}$/.test(seedHex)) {
    if (isProductionEnv()) {
      throw new Error('RECEIPT_SIGNING_SEED (32-byte hex) is required to sign receipts in production');
    }
    throw new Error('RECEIPT_SIGNING_SEED (32-byte hex) is not set; receipts cannot be signed');
  }

  const privateKey = crypto.createPrivateKey({
    key: Buffer.concat([PKCS8_ED25519_PREFIX, Buffer.from(seedHex, 'hex')]),
    format: 'der',
    type: 'pkcs8',
  });
  const publicKeyPem = crypto
    .createPublicKey(privateKey)
    .export({ type: 'spki', format: 'pem' })
    .toString();

  cached = { privateKey, publicKeyPem };
  return cached;
}

/** Stable JSON: object keys sorted recursively so hashes are reproducible. */
export function canonicalJson(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  const entries = Object.entries(value as Record<string, unknown>)
    .filter(([, v]) => v !== undefined)
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([k, v]) => `${JSON.stringify(k)}:${canonicalJson(v)}`);
  return `{${entries.join(',')}}`;
}

export function sha256Hex(input: string | Buffer): string {
  return crypto.createHash('sha256').update(input).digest('hex');
}

export function signReceipt(receipt: Record<string, unknown>): {
  contentHash: string;
  signature: string;
  publicKeyPem: string;
} {
  const { privateKey, publicKeyPem } = loadKey();
  const contentHash = sha256Hex(canonicalJson(receipt));
  const signature = crypto.sign(null, Buffer.from(contentHash, 'hex'), privateKey).toString('base64');
  return { contentHash, signature, publicKeyPem };
}

/** Verification is self-contained: only the receipt row's own fields are needed. */
export function verifyReceipt(
  receipt: Record<string, unknown>,
  contentHash: string,
  signature: string,
  publicKeyPem: string
): { hashValid: boolean; signatureValid: boolean } {
  const recomputed = sha256Hex(canonicalJson(receipt));
  const hashValid = recomputed === contentHash;
  let signatureValid = false;
  try {
    signatureValid = crypto.verify(
      null,
      Buffer.from(contentHash, 'hex'),
      crypto.createPublicKey(publicKeyPem),
      Buffer.from(signature, 'base64')
    );
  } catch {
    signatureValid = false;
  }
  return { hashValid, signatureValid };
}
