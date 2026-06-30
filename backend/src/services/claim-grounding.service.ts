import { EvidenceRecord, evidenceRegistry } from './evidence-registry.service';

export interface ClaimGroundingInput {
  claimText: string;
  supportSourceIds: string[];
  supportSnippets: string[];
}

export interface ClaimGroundingResult {
  valid: boolean;
  evidenceRows: EvidenceRecord[];
  errors: string[];
}

function normalizeTokens(value: string): string[] {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean);
}

function isTokenSubsequence(needle: string[], haystack: string[]): boolean {
  if (needle.length === 0) return false;
  if (needle.length > haystack.length) return false;
  for (let start = 0; start <= haystack.length - needle.length; start += 1) {
    let matches = true;
    for (let offset = 0; offset < needle.length; offset += 1) {
      if (haystack[start + offset] !== needle[offset]) {
        matches = false;
        break;
      }
    }
    if (matches) return true;
  }
  return false;
}

export class ClaimGroundingService {
  async validate(input: ClaimGroundingInput): Promise<ClaimGroundingResult> {
    const errors: string[] = [];
    const supportSourceIds = Array.isArray(input.supportSourceIds) ? input.supportSourceIds : [];
    const supportSnippets = Array.isArray(input.supportSnippets) ? input.supportSnippets : [];

    if (!input.claimText?.trim()) errors.push('claimText is required');
    if (supportSourceIds.length === 0) errors.push('supported claims require at least one source id');

    const evidenceRows = await evidenceRegistry.getBySourceIds(supportSourceIds);
    const foundSourceIds = new Set(evidenceRows.map(row => row.source_id));
    for (const sourceId of supportSourceIds) {
      if (!foundSourceIds.has(sourceId)) {
        errors.push(`source id is not registered evidence: ${sourceId}`);
      }
    }

    const evidenceText = evidenceRows
      .map(row => [row.title, row.snippet, row.url].filter(Boolean).join(' '))
      .join(' ');
    const evidenceTokens = normalizeTokens(evidenceText);

    if (supportSnippets.length > 0) {
      for (const snippet of supportSnippets) {
        const snippetTokens = normalizeTokens(snippet);
        if (!isTokenSubsequence(snippetTokens, evidenceTokens)) {
          errors.push(`support snippet is not a token-subsequence of registered evidence: ${snippet}`);
        }
      }
    } else if (!evidenceRows.some(row => row.snippet || row.title)) {
      errors.push('supported claims require at least one grounded support snippet');
    }

    return { valid: errors.length === 0, evidenceRows, errors };
  }
}

export const claimGrounding = new ClaimGroundingService();
