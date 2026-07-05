/**
 * Real Web Adapter
 * ================
 * Uses actual HTTP requests to search and fetch public web content.
 * Implements real search using multiple strategies - NO synthetic fallback.
 *
 * Priority:
 * 1. SearXNG self-hosted (if SEARXNG_URL set) — no rate limits, no key needed
 * 2. Google Custom Search API (if SEARCH_ENGINE_API_KEY set)
 * 3. Brave Search API (free, no key needed for limited requests)
 * 4. Bing Search API (if BING_SEARCH_API_KEY set)
 * 5. DuckDuckGo with retry logic
 * 6. If all fail: BLOCKED (not synthetic results)
 */

import crypto from 'crypto';
import fetch from 'node-fetch';
import { WebAdapter, SearchResult, FetchResult } from './web-adapter';
import { assertPublicHttpUrl } from './url-safety';

const USER_AGENT = 'AgentCo-Research/1.0 (autonomous research agent)';
const FETCH_TIMEOUT_MS = 8000;
const MAX_CONTENT_SIZE = 500000; // 500KB
const MAX_RETRIES = 3;
const MAX_REDIRECTS = 3;

export class RealWebAdapter implements WebAdapter {
  getName(): string {
    return 'RealWebAdapter';
  }

  async isReady(): Promise<boolean> {
    // Check basic connectivity
    try {
      const response = await Promise.race([
        fetch('https://www.google.com', { method: 'HEAD' }),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('timeout')), 3000)
        ),
      ]);
      return response !== null;
    } catch {
      return false;
    }
  }

  /**
   * Report which search backends are configured, so callers (and startup
   * logs) can see honestly whether real search is possible instead of
   * discovering it via a silent empty result. DuckDuckGo needs no key but is
   * an unreliable HTML scraper, so it is reported separately.
   */
  availableSearchBackends(): {
    searxng: { configured: boolean; envVar: string };
    google: { configured: boolean; envVar: string };
    bing: { configured: boolean; envVar: string };
    duckduckgo: { configured: boolean; note: string };
    anyKeyedBackend: boolean;
  } {
    const searxng = Boolean(process.env.SEARXNG_URL);
    const google = Boolean(process.env.SEARCH_ENGINE_API_KEY);
    const bing = Boolean(process.env.BING_SEARCH_API_KEY);
    return {
      searxng: { configured: searxng, envVar: 'SEARXNG_URL' },
      google: { configured: google, envVar: 'SEARCH_ENGINE_API_KEY' },
      bing: { configured: bing, envVar: 'BING_SEARCH_API_KEY' },
      duckduckgo: { configured: process.env.AGENTCO_DISABLE_DDG !== '1', note: 'no key; unreliable HTML scraper' },
      anyKeyedBackend: searxng || google || bing,
    };
  }

  async search(query: string): Promise<SearchResult[]> {
    const availability = this.availableSearchBackends();
    console.log(
      `[RealWebAdapter] Searching "${query}" — backends: ` +
        `searxng=${availability.searxng.configured} google=${availability.google.configured} ` +
        `bing=${availability.bing.configured} ddg=${availability.duckduckgo.configured}`
    );

    const methods: Array<() => Promise<SearchResult[]>> = [
      () => this.tryFixtureSearch(query),
      () => this.trySearXNG(query),
      () => this.tryGoogleCustomSearch(query),
      () => this.tryBraveSearch(query),
      () => this.tryBingSearch(query),
    ];
    if (process.env.AGENTCO_DISABLE_DDG !== '1') {
      methods.push(() => this.tryDuckDuckGoWithRetry(query));
    }

    for (const method of methods) {
      try {
        const results = await method();
        if (results && results.length > 0) {
          console.log(`[RealWebAdapter] ✅ Found ${results.length} results`);
          return results;
        }
      } catch (error) {
        console.log(`[RealWebAdapter] Method failed: ${error}`);
      }
    }

    // All backends failed — fail with an ACTIONABLE error that names the env
    // vars to configure and points to the keyless direct-fetch alternative.
    // Never return synthetic results.
    const errorMsg =
      `[RealWebAdapter] no working search backend for "${query}". ` +
      `Configure one of: SEARXNG_URL (self-hosted SearXNG, no key — see README), ` +
      `SEARCH_ENGINE_API_KEY (Google CSE), or BING_SEARCH_API_KEY. ` +
      `Alternatively use the keyless fetch_page action with an explicit URL.`;
    console.error(errorMsg);
    throw new Error(errorMsg);
  }

  /**
   * Deterministic fixture search backend for offline/CI runs (Phase B/G4).
   * Enabled ONLY when AGENTCO_SEARCH_FIXTURE_FILE points at a JSON file of
   * the form [{ "match": ["token", ...], "results": [{title,url,snippet}] }].
   * Results are returned when every match token appears in the query. This is
   * an explicitly-labeled test fixture, refused outright in production, and
   * results are tagged backend='fixture' so discovery can record their origin
   * honestly.
   */
  private async tryFixtureSearch(query: string): Promise<SearchResult[]> {
    const fixtureFile = process.env.AGENTCO_SEARCH_FIXTURE_FILE;
    if (!fixtureFile) return [];
    if (process.env.AGENTCO_ENV === 'production' || process.env.AGENTCO_ENV === 'staging') {
      throw new Error('fixture search backend is refused in production/staging');
    }
    const fs = await import('fs');
    const entries = JSON.parse(fs.readFileSync(fixtureFile, 'utf8')) as Array<{
      match: string[];
      results: Array<{ title: string; url: string; snippet: string }>;
    }>;
    const queryTokens = new Set(query.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean));
    const matched: SearchResult[] = [];
    for (const entry of entries) {
      if (entry.match.every(token => queryTokens.has(token.toLowerCase()))) {
        for (const result of entry.results) {
          matched.push({ ...result, backend: 'fixture' } as SearchResult & { backend: string });
        }
      }
    }
    if (matched.length > 0) {
      console.log(`[RealWebAdapter] using FIXTURE search backend (deterministic, offline/CI only): ${matched.length} results`);
    }
    return matched;
  }

  private async trySearXNG(query: string): Promise<SearchResult[]> {
    const baseUrl = process.env.SEARXNG_URL;
    if (!baseUrl) {
      return [];
    }

    try {
      const url = `${baseUrl.replace(/\/$/, '')}/search?q=${encodeURIComponent(query)}&format=json&language=en`;
      const response = await fetch(url, {
        headers: { 'User-Agent': USER_AGENT, 'Accept': 'application/json' },
        timeout: FETCH_TIMEOUT_MS,
      });

      if (!response.ok) {
        throw new Error(`SearXNG returned ${response.status}`);
      }

      const data = await response.json() as { results?: Array<{ url: string; title: string; content?: string }> };
      if (!data.results || data.results.length === 0) {
        throw new Error('No results from SearXNG');
      }

      return data.results.slice(0, 10).map((item, idx) => ({
        url: item.url,
        title: item.title,
        snippet: item.content || '',
        rank: idx + 1,
      }));
    } catch (error) {
      console.warn(`SearXNG failed: ${error}`);
      return [];
    }
  }

  private async tryGoogleCustomSearch(query: string): Promise<SearchResult[]> {
    const apiKey = process.env.SEARCH_ENGINE_API_KEY;
    if (!apiKey) {
      console.log('[RealWebAdapter] No SEARCH_ENGINE_API_KEY, skipping Google Custom Search');
      return [];
    }

    try {
      const encodedQuery = encodeURIComponent(query);
      const url = `https://customsearch.googleapis.com/cse/v1?q=${encodedQuery}&key=${apiKey}`;
      const response = await fetch(url, { timeout: FETCH_TIMEOUT_MS });

      if (!response.ok) {
        throw new Error(`Google Custom Search returned ${response.status}`);
      }

      const data = await response.json();
      if (!data.items || data.items.length === 0) {
        throw new Error('No results from Google Custom Search');
      }

      return data.items.map((item: any) => ({
        url: item.link,
        title: item.title,
        snippet: item.snippet,
        rank: item.position,
      }));
    } catch (error) {
      console.warn(`Google Custom Search failed: ${error}`);
      return [];
    }
  }

  private async tryBraveSearch(query: string): Promise<SearchResult[]> {
    // Brave Search has a free tier
    try {
      const encodedQuery = encodeURIComponent(query);
      // Using Brave's public search (no API key for basic search)
      const url = `https://api.search.brave.com/res/v1/web/search?q=${encodedQuery}`;

      // Try without API key first (Brave allows limited free requests)
      const response = await fetch(url, {
        headers: {
          'User-Agent': USER_AGENT,
          'Accept': 'application/json',
        },
        timeout: FETCH_TIMEOUT_MS,
      });

      if (!response.ok) {
        throw new Error(`Brave Search returned ${response.status}`);
      }

      const data = await response.json();
      if (!data.web || data.web.length === 0) {
        throw new Error('No results from Brave Search');
      }

      return data.web.slice(0, 10).map((item: any, idx: number) => ({
        url: item.url,
        title: item.title,
        snippet: item.description || item.snippet || '',
        rank: idx + 1,
      }));
    } catch (error) {
      console.warn(`Brave Search failed: ${error}`);
      return [];
    }
  }

  private async tryBingSearch(query: string): Promise<SearchResult[]> {
    const apiKey = process.env.BING_SEARCH_API_KEY;
    if (!apiKey) {
      console.log('[RealWebAdapter] No BING_SEARCH_API_KEY, skipping Bing Search');
      return [];
    }

    try {
      const encodedQuery = encodeURIComponent(query);
      const url = `https://api.bing.microsoft.com/v7.0/search?q=${encodedQuery}`;

      const response = await fetch(url, {
        headers: {
          'Ocp-Apim-Subscription-Key': apiKey,
        },
        timeout: FETCH_TIMEOUT_MS,
      });

      if (!response.ok) {
        throw new Error(`Bing Search returned ${response.status}`);
      }

      const data = await response.json();
      if (!data.webPages || data.webPages.value.length === 0) {
        throw new Error('No results from Bing Search');
      }

      return data.webPages.value.slice(0, 10).map((item: any, idx: number) => ({
        url: item.url,
        title: item.name,
        snippet: item.snippet,
        rank: idx + 1,
      }));
    } catch (error) {
      console.warn(`Bing Search failed: ${error}`);
      return [];
    }
  }

  private async tryDuckDuckGoWithRetry(query: string): Promise<SearchResult[]> {
    for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
      try {
        const encodedQuery = encodeURIComponent(query);
        const url = `https://duckduckgo.com/html/?q=${encodedQuery}`;

        const response = await fetch(url, {
          headers: {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html',
          },
          timeout: FETCH_TIMEOUT_MS,
        });

        if (!response.ok) {
          throw new Error(`DuckDuckGo returned ${response.status}`);
        }

        const content = await response.text();
        const results: SearchResult[] = [];

        // Extract results from DuckDuckGo HTML - multiple patterns for robustness
        const patterns = [
          // Pattern 1: Standard result
          /<span class="result__title">[\s\S]*?<a\s+href="([^"]+)">([^<]+)<\/a>/g,
          // Pattern 2: Alternative format
          /<a\s+href="([^"]+)"\s+class="result__a">([^<]+)<\/a>/g,
          // Pattern 3: Simple link with class
          /class="result__url"\s+href="([^"]+)">[\s\S]*?>([^<]+)</g,
        ];

        for (const pattern of patterns) {
          let match;
          let rank = 1;
          while ((match = pattern.exec(content)) && results.length < 10) {
            const url = match[1];
            const title = match[2] || 'Result';

            // Validate URL
            if (url && url.startsWith('http') && !url.includes('duckduckgo.com')) {
              results.push({
                url,
                title: title.trim(),
                snippet: `Result for: ${query}`,
                rank: rank++,
              });
            }
          }
          if (results.length > 0) break;
        }

        if (results.length > 0) {
          console.log(`[RealWebAdapter] DuckDuckGo found ${results.length} results (attempt ${attempt})`);
          return results;
        }

        throw new Error('No results extracted from DuckDuckGo');
      } catch (error) {
        console.warn(`DuckDuckGo attempt ${attempt}/${MAX_RETRIES} failed: ${error}`);

        if (attempt < MAX_RETRIES) {
          // Exponential backoff before retry
          const delayMs = Math.pow(2, attempt - 1) * 1000;
          await new Promise(resolve => setTimeout(resolve, delayMs));
        }
      }
    }

    return [];
  }

  // Note: No synthetic fallback - if all real searches fail, the search fails
  // The system should handle search failures gracefully without fake data

  async fetch(url: string): Promise<FetchResult | null> {
    try {
      // SSRF guard: only public HTTP(S) endpoints; hostnames that resolve to
      // private/reserved addresses are rejected. Loopback is only permitted
      // when a test fixture explicitly opts in.
      const allowLoopback = process.env.AGENTCO_ALLOW_LOOPBACK_FETCH === '1';
      let currentUrl = (await assertPublicHttpUrl(url, { allowLoopback })).toString();

      // Uses the Node built-in fetch (undici); node-fetch v2 raises "Premature
      // close" on Node 24. SSRF defense: the initial URL is validated above
      // (blocks direct fetches to loopback/private/metadata); redirects are
      // followed, then the FINAL resolved URL is re-validated so a public page
      // cannot land the fetch on an internal service.
      const response: Response = await globalThis.fetch(currentUrl, {
        headers: { 'User-Agent': USER_AGENT },
        signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
        redirect: 'follow',
      });
      if (response.redirected) {
        await assertPublicHttpUrl(response.url, { allowLoopback });
      }
      currentUrl = response.url || currentUrl;

      if (!response.ok) {
        console.warn(`Fetch failed: ${response.status}`);
        return null;
      }

      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('text/html') && !contentType.includes('text/plain')) {
        console.warn(`Skipping non-HTML content: ${contentType}`);
        return null;
      }

      const content = await response.text();

      if (content.length > MAX_CONTENT_SIZE) {
        console.warn(`Content truncated (${content.length} > ${MAX_CONTENT_SIZE})`);
      }

      // Extract title from HTML
      const titleMatch = content.match(/<title[^>]*>([^<]+)<\/title>/i);
      const title = titleMatch ? titleMatch[1].trim() : undefined;

      // Cryptographic content hash over the RAW bytes (exact-provenance).
      const contentHash = this.computeHash(content);

      return {
        url: currentUrl,
        status: response.status,
        title,
        content: content.substring(0, MAX_CONTENT_SIZE),
        // Readable prose so downstream claim-grounding has quotable text
        // instead of HTML markup.
        textContent: this.extractReadableText(content),
        contentHash,
        retrievedAt: new Date(),
      };
    } catch (error) {
      console.error(`Fetch error for ${url}: ${error}`);
      return null;
    }
  }

  private computeHash(content: string): string {
    return `sha256:${crypto.createHash('sha256').update(content).digest('hex')}`;
  }

  /**
   * Extract readable prose from HTML: drop script/style/head, strip tags,
   * decode a few common entities, collapse whitespace. Best-effort (no DOM
   * parser dependency) — enough for claim grounding to have real sentences to
   * quote instead of markup.
   */
  private extractReadableText(html: string): string {
    return html
      .replace(/<script[\s\S]*?<\/script>/gi, ' ')
      .replace(/<style[\s\S]*?<\/style>/gi, ' ')
      .replace(/<head[\s\S]*?<\/head>/gi, ' ')
      .replace(/<!--[\s\S]*?-->/g, ' ')
      .replace(/<[^>]+>/g, ' ')
      .replace(/&nbsp;/g, ' ')
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'")
      .replace(/\s+/g, ' ')
      .trim();
  }
}
