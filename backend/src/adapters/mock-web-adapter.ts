/**
 * Mock Web Adapter
 * ================
 * Returns deterministic test data for CI/testing.
 * Allows autonomy loop to run without network dependency.
 */

import { WebAdapter, SearchResult, FetchResult } from './web-adapter';
import { MOCK_DATA } from './mock-data';

export class MockWebAdapter implements WebAdapter {
  getName(): string {
    return 'MockWebAdapter';
  }

  async isReady(): Promise<boolean> {
    // Always ready in test mode
    return true;
  }

  async search(query: string): Promise<SearchResult[]> {
    // Normalize query for lookup
    const normalized = query.toLowerCase().replace(/[^\w\s]/g, '');

    // Find matching mock data
    for (const [key, data] of Object.entries(MOCK_DATA.searches)) {
      if (key.includes(normalized)) {
        console.log(`[MockWebAdapter] Search "${query}" → matched key "${key}"`);
        return data.results;
      }
    }

    // Default fallback for unmatched queries
    console.log(`[MockWebAdapter] Search "${query}" → no exact match, returning default`);
    return [
      {
        url: 'https://example.com/default-result',
        title: 'Research Paper on Topic',
        snippet: `Results for "${query}". This is a deterministic mock result.`,
        rank: 1,
      },
    ];
  }

  async fetch(url: string): Promise<FetchResult | null> {
    // Check if this exact URL is in mock data
    if (MOCK_DATA.fetches[url]) {
      console.log(`[MockWebAdapter] Fetch "${url}" → exact match in mock data`);
      const data = MOCK_DATA.fetches[url];
      return {
        url,
        status: 200,
        title: data.title,
        content: data.content,
        contentHash: this.computeHash(data.content),
        retrievedAt: new Date(),
      };
    }

    // Try to match by domain
    const urlObj = new URL(url);
    const domain = urlObj.hostname;

    for (const [mockUrl, mockData] of Object.entries(MOCK_DATA.fetches)) {
      const mockDomain = new URL(mockUrl).hostname;
      if (domain === mockDomain) {
        console.log(`[MockWebAdapter] Fetch "${url}" → matched domain "${domain}"`);
        return {
          url,
          status: 200,
          title: mockData.title,
          content: mockData.content,
          contentHash: this.computeHash(mockData.content),
          retrievedAt: new Date(),
        };
      }
    }

    // Return generic fallback for unmocked URLs
    console.log(`[MockWebAdapter] Fetch "${url}" → no match, returning default`);
    return {
      url,
      status: 200,
      title: 'Generic Research Result',
      content: `Content fetched from ${url}. This is deterministic mock data for testing.`,
      contentHash: this.computeHash(url),
      retrievedAt: new Date(),
    };
  }

  private computeHash(content: string): string {
    let hash = 0;
    for (let i = 0; i < content.length; i++) {
      const char = content.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash;
    }
    return `hash_${Math.abs(hash)}`;
  }
}
