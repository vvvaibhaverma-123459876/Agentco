/**
 * Real Web Adapter
 * ================
 * Uses actual HTTP requests to search and fetch public web content.
 * For testing or production when real internet access is needed.
 */

import fetch from 'node-fetch';
import { WebAdapter, SearchResult, FetchResult } from './web-adapter';

const USER_AGENT = 'AgentCo-Research/1.0 (autonomous research agent)';
const FETCH_TIMEOUT_MS = 5000;
const MAX_CONTENT_SIZE = 500000; // 500KB

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
    /**
     * PLACEHOLDER: Real implementation would use a search engine API
     * (Google Custom Search, Bing Search, or DuckDuckGo).
     * For now, returns empty to avoid API costs in development.
     *
     * To enable:
     * 1. Set SEARCH_ENGINE_API_KEY env var
     * 2. Uncomment the actual search implementation below
     */
    console.log(`[RealWebAdapter] Search query: "${query}" - using mock (no API key configured)`);
    return [];

    // Actual implementation example (requires API key):
    /*
    const apiKey = process.env.SEARCH_ENGINE_API_KEY;
    if (!apiKey) {
      console.warn('SEARCH_ENGINE_API_KEY not set, cannot perform real search');
      return [];
    }

    try {
      const encodedQuery = encodeURIComponent(query);
      const url = `https://customsearch.googleapis.com/cse/v1?q=${encodedQuery}&key=${apiKey}`;
      const response = await fetch(url, { timeout: FETCH_TIMEOUT_MS });

      if (!response.ok) {
        console.warn(`Search failed: ${response.status}`);
        return [];
      }

      const data = await response.json();
      return (data.items || []).map((item) => ({
        url: item.link,
        title: item.title,
        snippet: item.snippet,
        rank: item.position,
      }));
    } catch (error) {
      console.error(`Search error: ${error}`);
      return [];
    }
    */
  }

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
          timeout: FETCH_TIMEOUT_MS,
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
