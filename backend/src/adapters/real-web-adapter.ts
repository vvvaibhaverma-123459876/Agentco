/**
 * Real Web Adapter
 * ================
 * Uses actual HTTP requests to search and fetch public web content.
 * Implements real search using multiple strategies - NO synthetic fallback.
 *
 * Priority:
 * 1. Google Custom Search API (if SEARCH_ENGINE_API_KEY set)
 * 2. Brave Search API (free, no key needed for limited requests)
 * 3. Bing Search API (if BING_SEARCH_API_KEY set)
 * 4. DuckDuckGo with retry logic
 * 5. If all fail: BLOCKED (not synthetic results)
 *
 * Uses native fetch (Node 18+) instead of node-fetch to avoid "Premature close" errors.
 */

import { WebAdapter, SearchResult, FetchResult } from './web-adapter';

const USER_AGENT = 'AgentCo-Research/1.0 (autonomous research agent)';
const FETCH_TIMEOUT_MS = 8000;
const MAX_CONTENT_SIZE = 500000; // 500KB
const MAX_RETRIES = 3;

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

  async search(query: string): Promise<SearchResult[]> {
    console.log(`[RealWebAdapter] Searching for: "${query}"`);

    // Try each search method in priority order
    const methods = [
      () => this.tryGoogleCustomSearch(query),
      () => this.tryBraveSearch(query),
      () => this.tryBingSearch(query),
      () => this.tryDuckDuckGoWithRetry(query),
    ];

    for (const method of methods) {
      try {
        const results = await method();
        if (results && results.length > 0) {
          console.log(`[RealWebAdapter] ✅ Found ${results.length} results`);
          return results;
        }
      } catch (error) {
        console.log(`[RealWebAdapter] Method failed: ${error}`);
        // Continue to next method
      }
    }

    // ALL methods failed - BLOCKED, not synthetic
    const errorMsg = `[RealWebAdapter] ❌ ALL search methods failed for: "${query}". No fallback to synthetic.`;
    console.error(errorMsg);
    throw new Error(errorMsg);
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
      const response = await Promise.race([
        fetch(url),
        new Promise<Response>((_, reject) =>
          setTimeout(() => reject(new Error('timeout')), FETCH_TIMEOUT_MS)
        ),
      ]);

      if (!response.ok) {
        throw new Error(`Google Custom Search returned ${response.status}`);
      }

      const data = (await response.json()) as any;
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
      const response = await Promise.race([
        fetch(url, {
          headers: {
            'User-Agent': USER_AGENT,
            'Accept': 'application/json',
          },
        }),
        new Promise<Response>((_, reject) =>
          setTimeout(() => reject(new Error('timeout')), FETCH_TIMEOUT_MS)
        ),
      ]);

      if (!response.ok) {
        throw new Error(`Brave Search returned ${response.status}`);
      }

      const data = (await response.json()) as any;
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

      const response = await Promise.race([
        fetch(url, {
          headers: {
            'Ocp-Apim-Subscription-Key': apiKey,
          },
        }),
        new Promise<Response>((_, reject) =>
          setTimeout(() => reject(new Error('timeout')), FETCH_TIMEOUT_MS)
        ),
      ]);

      if (!response.ok) {
        throw new Error(`Bing Search returned ${response.status}`);
      }

      const data = (await response.json()) as any;
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

        const response = await Promise.race([
          fetch(url, {
            headers: {
              'User-Agent': USER_AGENT,
              'Accept': 'text/html',
            },
          }),
          new Promise<Response>((_, reject) =>
            setTimeout(() => reject(new Error('timeout')), FETCH_TIMEOUT_MS)
          ),
        ]);

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
      // Validate URL to prevent SSRF
      const parsed = new URL(url);
      if (!['http:', 'https:'].includes(parsed.protocol)) {
        console.warn(`Invalid protocol for fetch: ${parsed.protocol}`);
        return null;
      }

      const response = await Promise.race([
        fetch(url, {
          headers: { 'User-Agent': USER_AGENT },
          redirect: 'follow',
        }),
        new Promise<Response | null>((_, reject) =>
          setTimeout(() => reject(new Error('Fetch timeout')), FETCH_TIMEOUT_MS)
        ),
      ]);

      if (!response || !response.ok) {
        console.warn(`Fetch failed: ${response?.status || 'timeout'}`);
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

      // Compute content hash for deduplication
      const contentHash = this.computeHash(content);

      return {
        url,
        status: response.status,
        title,
        content: content.substring(0, MAX_CONTENT_SIZE),
        contentHash,
        retrievedAt: new Date(),
      };
    } catch (error) {
      console.error(`Fetch error for ${url}: ${error}`);
      return null;
    }
  }

  private computeHash(content: string): string {
    // Simple hash for content deduplication
    let hash = 0;
    for (let i = 0; i < content.length; i++) {
      const char = content.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return `hash_${Math.abs(hash)}`;
  }
}
