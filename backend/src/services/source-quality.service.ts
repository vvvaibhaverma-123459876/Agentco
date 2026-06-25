/**
 * Source-quality scoring (credibility, not just traceability).
 * ===========================================================
 * Motivation: grounding proves a claim traces to a cited source, NOT that the source is credible.
 * The autonomy loop happily grounded claims in arXiv 1810.02188 ("6m theorem"), a vanity preprint.
 *
 * Discriminating test (2026-06-25): journal-ref / publisher-DOI does NOT separate junk from legit
 * (Maynard's landmark "Small gaps between primes" has no arXiv journal-ref, same as the crank paper).
 * The signal that DOES separate them is CITATIONS:
 *   junk 1810.02188 -> 0 citations / 0 influential / no venue
 *   Maynard 1311.4600 -> 145 citations / 29 influential / venue "Graduate Studies in Mathematics"
 *
 * Design (per advisor):
 *  - WEIGHT, don't hard-gate. The score adjusts claim confidence; it never silently drops evidence.
 *  - FAIL-SOFT. Unknown (API down/rate-limited, or paper too new to judge) -> NEUTRAL, never "junk".
 *  - AGE-AWARE. A great paper from last month has few citations; don't punish recency.
 */

export interface SourceCitationMeta {
  citationCount: number | null;
  influentialCitationCount: number | null;
  venue?: string | null;
  /** Publication/submission year, if known (for recency handling). */
  year?: number | null;
}

export type QualityTier = 'high' | 'medium' | 'low' | 'unknown';

export interface SourceQualityScore {
  /** 0..1; 0.5 is neutral/unknown (never penalises on missing data). */
  quality: number;
  tier: QualityTier;
  reason: string;
}

const NEUTRAL = 0.5;
const RECENT_YEARS = 1.5; // younger than this with few citations => "too new to judge", not "low"

/**
 * Pure citation-based credibility score. No I/O.
 * @param meta   citation metadata (null counts => unknown)
 * @param nowYear current year (injectable for tests)
 */
export function scoreSourceQuality(meta: SourceCitationMeta, nowYear = new Date().getFullYear()): SourceQualityScore {
  const cites = meta.citationCount;
  const influential = meta.influentialCitationCount ?? 0;
  const hasVenue = !!(meta.venue && meta.venue.trim());

  // Unknown citation data => fail-soft neutral.
  if (cites == null) {
    return { quality: NEUTRAL, tier: 'unknown', reason: 'citation data unavailable (neutral, not penalised)' };
  }

  const ageYears = meta.year != null ? Math.max(0, nowYear - meta.year) : null;
  const isRecent = ageYears != null && ageYears < RECENT_YEARS;

  // Strong credibility: influential citations or a real venue, or many citations.
  if (influential >= 3 || cites >= 25 || (hasVenue && cites >= 5)) {
    const q = Math.min(1, 0.7 + Math.min(0.3, cites / 500 + influential / 50));
    return { quality: q, tier: 'high', reason: `${cites} citations (${influential} influential)${hasVenue ? `, venue "${meta.venue}"` : ''}` };
  }

  // Some traction.
  if (cites >= 5 || influential >= 1) {
    return { quality: 0.6, tier: 'medium', reason: `${cites} citations (${influential} influential)` };
  }

  // Few/zero citations on a RECENT paper => too new to judge => neutral, not low.
  if (isRecent) {
    return { quality: NEUTRAL, tier: 'unknown', reason: `only ${cites} citations but paper is recent (${ageYears!.toFixed(1)}y) — too new to judge` };
  }

  // Few/zero citations on an ESTABLISHED paper => genuine low-credibility signal (the junk case).
  if (cites === 0) {
    return { quality: 0.2, tier: 'low', reason: ageYears != null ? `0 citations after ${ageYears.toFixed(0)}y` : '0 citations (established)' };
  }
  return { quality: 0.4, tier: 'low', reason: `${cites} citations (established, low traction)` };
}

/** Extract a bare arXiv id (e.g. "1810.02188") from an arxiv.org URL, or null. */
export function arxivIdFromUrl(url: string): string | null {
  const m = url.match(/arxiv\.org\/(?:abs|pdf)\/([0-9]{4}\.[0-9]{4,5})(v\d+)?/i);
  return m ? m[1] : null;
}

const SEMANTIC_SCHOLAR = 'https://api.semanticscholar.org/graph/v1/paper';

/**
 * Resolves source credibility for a URL, with caching and fail-soft behaviour.
 * Currently knows how to score arXiv papers (via Semantic Scholar citations). Non-arXiv or
 * unreachable sources return a NEUTRAL 'unknown' score — credibility is never assumed-junk.
 */
export class SourceQualityService {
  private cache = new Map<string, SourceQualityScore>();

  /** Fetch citation metadata for an arXiv id. Returns null on any failure (fail-soft). */
  async fetchArxivCitations(arxivId: string): Promise<SourceCitationMeta | null> {
    try {
      const key = process.env.SEMANTIC_SCHOLAR_API_KEY;
      const url = `${SEMANTIC_SCHOLAR}/arXiv:${arxivId}?fields=citationCount,influentialCitationCount,venue,year`;
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 8000);
      const res = await fetch(url, {
        signal: controller.signal,
        headers: key ? { 'x-api-key': key } : {},
      });
      clearTimeout(timer);
      if (!res.ok) return null; // 429 / 404 / etc. -> unknown
      const data: any = await res.json();
      if (data == null || typeof data.citationCount === 'undefined') return null;
      return {
        citationCount: data.citationCount ?? null,
        influentialCitationCount: data.influentialCitationCount ?? null,
        venue: data.venue ?? null,
        year: data.year ?? null,
      };
    } catch {
      return null;
    }
  }

  /** Credibility score for a source URL (cached). Always returns a score (neutral on unknown). */
  async getQualityForUrl(url: string): Promise<SourceQualityScore> {
    const cached = this.cache.get(url);
    if (cached) return cached;

    const arxivId = arxivIdFromUrl(url);
    let score: SourceQualityScore;
    if (!arxivId) {
      score = { quality: NEUTRAL, tier: 'unknown', reason: 'non-arXiv source — credibility not scored' };
    } else {
      const meta = await this.fetchArxivCitations(arxivId);
      score = meta
        ? scoreSourceQuality(meta)
        : { quality: NEUTRAL, tier: 'unknown', reason: 'citation lookup failed/rate-limited (neutral)' };
    }
    this.cache.set(url, score);
    return score;
  }
}

export const sourceQualityService = new SourceQualityService();
