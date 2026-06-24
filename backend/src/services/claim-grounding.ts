/**
 * Claim Grounding — pure validation logic (no I/O).
 * =================================================
 * The single source of truth for whether a claim is grounded in its cited sources.
 * Kept free of any database/network access so it can be unit-tested against the REAL
 * logic (not a copy). The executor fetches source content, then delegates here.
 *
 * A claim is grounded only if ALL hold:
 *  1. Named-concept check  — every "<Name> theorem/conjecture/..." in the claim appears in sources.
 *  2. Term-overlap check   — ≥30% of meaningful claim terms appear in sources.
 *  3. Red-flag check       — fabrication patterns ("6m theorem", "newly discovered X theorem")
 *                            whose concept is absent from sources are rejected.
 *  4. Snippet-substring    — when snippets are required/provided, every support snippet must be a
 *                            verbatim (whitespace-normalised, case-insensitive) substring of the
 *                            cited source content. This is the hard grounding guarantee: an accepted
 *                            claim must quote text that actually exists in a source.
 */

export interface GroundingSource {
  sourceId: string;
  /** Abstract / page text used as the grounding corpus. */
  content: string;
}

export interface GroundingResult {
  valid: boolean;
  reason?: string;
  /** Snippets confirmed to be verbatim substrings of the sources. */
  groundedSnippets?: string[];
}

export interface GroundingOptions {
  /** Require at least one valid support snippet for acceptance. Default: true. */
  requireSnippet?: boolean;
  /** Minimum fraction of claim terms that must appear in sources. Default: 0.3. */
  minTermOverlap?: number;
}

const STOPWORDS = new Set([
  'the', 'and', 'that', 'this', 'with', 'from', 'have', 'been', 'about', 'also', 'which',
  'their', 'these', 'those', 'than', 'then', 'they', 'such', 'into', 'when', 'where',
]);

/** Normalise whitespace and lowercase for substring comparison. */
function normalise(text: string): string {
  return text.replace(/\s+/g, ' ').trim().toLowerCase();
}

export function validateGrounding(
  claimText: string,
  sources: GroundingSource[],
  supportSnippets: string[] = [],
  options: GroundingOptions = {},
): GroundingResult {
  const requireSnippet = options.requireSnippet ?? true;
  const minTermOverlap = options.minTermOverlap ?? 0.3;

  if (!claimText || !claimText.trim()) {
    return { valid: false, reason: 'Empty claim text' };
  }
  if (sources.length === 0) {
    return { valid: false, reason: 'No sources provided' };
  }

  const sourceContents = sources.map(s => s.content || '').join(' ');
  const sourceNorm = normalise(sourceContents);
  if (!sourceNorm) {
    return { valid: false, reason: 'Sources have no content to ground against' };
  }

  // ===== CHECK 1: Named-Concept Verification =====
  // Case-insensitive on the keyword so "Verma Conjecture" (capitalised) is caught;
  // the name group still requires an initial capital to target proper names.
  const namedConceptPattern =
    /\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(theorem|conjecture|lemma|hypothesis|method|algorithm|principle|law|axiom|corollary)\b/gi;
  const foundConcepts = new Set<string>();
  let match: RegExpExecArray | null;
  while ((match = namedConceptPattern.exec(claimText)) !== null) {
    foundConcepts.add(`${match[1].toLowerCase()} ${match[2].toLowerCase()}`);
  }
  const missingConcepts: string[] = [];
  for (const concept of foundConcepts) {
    if (!sourceNorm.includes(concept)) missingConcepts.push(concept);
  }
  if (missingConcepts.length > 0) {
    return { valid: false, reason: `Named concept(s) not found in sources: ${missingConcepts.join(', ')}` };
  }

  // ===== CHECK 2: Term-Overlap Analysis =====
  const claimTerms = (claimText.match(/\b[a-z]{4,}\b/gi) || [])
    .filter(t => !STOPWORDS.has(t.toLowerCase()));
  let matchCount = 0;
  for (const term of claimTerms) {
    if (sourceNorm.includes(term.toLowerCase())) matchCount++;
  }
  const matchRatio = claimTerms.length > 0 ? matchCount / claimTerms.length : 0;
  if (matchRatio < minTermOverlap && claimTerms.length > 5) {
    return {
      valid: false,
      reason: `Only ${(matchRatio * 100).toFixed(0)}% of claim terms found in sources (need ≥${(minTermOverlap * 100).toFixed(0)}%)`,
    };
  }

  // ===== CHECK 3: Red-Flag Pattern Detection =====
  const redFlags = [
    /(\d+[a-z]m?\s+theorem)/i,
    /\b(newly|recently)\s+discovered\s+[a-z\s]+theorem/i,
    /\b(hypothetical|proposed)\s+[a-z\s]+theorem/i,
  ];
  for (const pattern of redFlags) {
    if (pattern.test(claimText)) {
      const conceptMatch = claimText.match(/([a-zA-Z\s]+(?:theorem|conjecture|lemma|method))/i);
      if (conceptMatch) {
        const concept = normalise(conceptMatch[1]);
        if (!sourceNorm.includes(concept)) {
          return { valid: false, reason: `Red-flag concept "${concept}" not found in sources` };
        }
      }
    }
  }

  // ===== CHECK 4: Snippet-Substring Grounding =====
  // Every provided snippet must be a verbatim substring of the sources (catches fabricated quotes).
  const groundedSnippets: string[] = [];
  for (const snippet of supportSnippets) {
    const snippetNorm = normalise(snippet);
    if (!snippetNorm) continue;
    if (sourceNorm.includes(snippetNorm)) {
      groundedSnippets.push(snippet);
    } else {
      return { valid: false, reason: `Support snippet not found verbatim in sources: "${snippet.slice(0, 60)}"` };
    }
  }

  if (requireSnippet && groundedSnippets.length === 0) {
    return {
      valid: false,
      reason: 'Claim has no grounded snippet: at least one supportSnippet must be a verbatim substring of a cited source',
    };
  }

  return { valid: true, groundedSnippets };
}
