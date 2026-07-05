/**
 * Goal-Relevant Source Discovery (G4 / Phase B)
 * =============================================
 * Replaces goal-agnostic seed-pack bootstrapping. For a goal:
 *
 *   1. derive a search query from the goal's content-bearing tokens;
 *   2. run it through the search adapter (SearXNG/Google/Bing/DDG live, or
 *      the deterministic fixture backend in offline/CI runs);
 *   3. score every candidate's relevance to the goal BEFORE fetching —
 *      title + snippet + URL token overlap — and reject candidates below
 *      threshold;
 *   4. only if search yields nothing, fall back to the curated seed packs,
 *      but apply the SAME relevance gate and label the survivors
 *      'seed_fallback' — a generic homepage that says nothing about the goal
 *      does not pass, so the old behavior (arxiv/github front pages for a
 *      Python question) cannot recur silently;
 *   5. persist EVERY candidate with score, decision, and reason in
 *      autonomy_source_candidates, so an auditor can see why each source was
 *      fetched or refused.
 */

import { db } from '../db/client';
import { RealWebAdapter } from '../adapters/real-web-adapter';
import { SourceDiscoveryEngine } from './source-discovery.service';
import { coreAssertionTokens } from './falsifiable-prediction.service';

export const RELEVANCE_THRESHOLD = 0.3;

/**
 * Claims are a sentence, not a page: they legitimately cover fewer of the
 * goal's tokens than a search result's title+snippet+url does, so the claim
 * gate uses a lower bar. An off-goal claim still scores ~0.
 */
export const CLAIM_RELEVANCE_THRESHOLD = 0.2;

export interface SourceCandidate {
  url: string;
  title: string;
  relevance: number;
  accepted: boolean;
  reason: string;
  discoveryMethod: 'search' | 'seed_fallback' | 'fixture_search';
}

export interface GoalDiscoveryResult {
  query: string;
  accepted: SourceCandidate[];
  rejected: SourceCandidate[];
  searchUsed: boolean;
  fallbackUsed: boolean;
  note: string;
}

export function relevanceScore(goalTokens: string[], text: string): number {
  if (goalTokens.length === 0) return 0;
  const haystack = new Set(
    text.toLowerCase().replace(/[^a-z0-9]+/g, ' ').split(/\s+/).filter(Boolean)
  );
  let hits = 0;
  for (const token of goalTokens) if (haystack.has(token)) hits += 1;
  return Number((hits / goalTokens.length).toFixed(4));
}

export class GoalSourceDiscoveryService {
  private webAdapter = new RealWebAdapter();
  private seedEngine = new SourceDiscoveryEngine();

  deriveQuery(goalText: string): string {
    return coreAssertionTokens(goalText, 8).join(' ');
  }

  async discoverForGoal(input: {
    goalId: string;
    goalText: string;
    limit?: number;
  }): Promise<GoalDiscoveryResult> {
    const limit = Math.max(1, Math.min(input.limit ?? 3, 10));
    const goalTokens = coreAssertionTokens(input.goalText, 12);
    const query = this.deriveQuery(input.goalText);
    const candidates: SourceCandidate[] = [];
    let searchUsed = false;
    let fallbackUsed = false;
    let note = '';

    // 1) search path
    try {
      const results = await this.webAdapter.search(query);
      searchUsed = true;
      for (const result of results.slice(0, 12)) {
        const basis = `${result.title ?? ''} ${result.snippet ?? ''} ${result.url}`;
        const relevance = relevanceScore(goalTokens, basis);
        const accepted = relevance >= RELEVANCE_THRESHOLD;
        candidates.push({
          url: result.url,
          title: result.title ?? '',
          relevance,
          accepted,
          reason: accepted
            ? `search result covers ${(relevance * 100).toFixed(0)}% of goal tokens`
            : `rejected: only ${(relevance * 100).toFixed(0)}% goal-token overlap (< ${RELEVANCE_THRESHOLD * 100}%)`,
          discoveryMethod: (result as any).backend === 'fixture' ? 'fixture_search' : 'search',
        });
      }
    } catch (error) {
      note = `search unavailable: ${error instanceof Error ? error.message.split('\n')[0] : error}`;
    }

    // 2) seed fallback — same relevance gate, explicit labeling. A curated
    // seed only survives if its topic/url actually overlaps the goal.
    if (candidates.filter(c => c.accepted).length === 0) {
      fallbackUsed = true;
      const packs = ['technical', 'scientific', 'governance', 'business'];
      for (const pack of packs) {
        let seeds;
        try {
          seeds = await this.seedEngine.discoverSourcesFromPack(pack, 5);
        } catch {
          continue;
        }
        for (const seed of seeds) {
          const basis = `${seed.topic_hint ?? ''} ${seed.source_pack} ${seed.source_url}`;
          const relevance = relevanceScore(goalTokens, basis);
          const accepted = relevance >= RELEVANCE_THRESHOLD;
          candidates.push({
            url: seed.source_url,
            title: seed.topic_hint ?? seed.source_domain,
            relevance,
            accepted,
            reason: accepted
              ? `FALLBACK seed (search unavailable) with ${(relevance * 100).toFixed(0)}% goal overlap`
              : `fallback seed rejected: ${(relevance * 100).toFixed(0)}% goal overlap — generic sources do not qualify`,
            discoveryMethod: 'seed_fallback',
          });
        }
      }
      if (candidates.filter(c => c.accepted).length === 0) {
        note = [note, 'no goal-relevant source found; refusing to fetch generic pages'].filter(Boolean).join('; ');
      }
    }

    // 3) persist the full decision trail
    for (const candidate of candidates) {
      await db.query(
        `INSERT INTO autonomy_source_candidates
           (goal_id, query, url, title, relevance_score, accepted, reason, discovery_method)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8)`,
        [
          input.goalId,
          query,
          candidate.url,
          candidate.title,
          candidate.relevance,
          candidate.accepted,
          candidate.reason,
          candidate.discoveryMethod,
        ]
      );
    }

    const accepted = candidates
      .filter(c => c.accepted)
      .sort((a, b) => b.relevance - a.relevance)
      .slice(0, limit);
    return {
      query,
      accepted,
      rejected: candidates.filter(c => !c.accepted),
      searchUsed,
      fallbackUsed,
      note,
    };
  }
}

export const goalSourceDiscovery = new GoalSourceDiscoveryService();
