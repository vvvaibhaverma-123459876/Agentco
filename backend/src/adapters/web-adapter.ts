/**
 * Web Adapter Interface
 * =======================
 * Defines the contract for web operations (search, fetch).
 * Allows swapping between real web API calls and deterministic test data.
 */

export interface SearchResult {
  url: string;
  title: string;
  snippet: string;
  rank?: number;
}

export interface FetchResult {
  url: string;
  status: number;
  title?: string;
  content: string;
  /** Readable prose extracted from HTML (tags/scripts stripped). Groundable. */
  textContent?: string;
  contentHash: string;
  retrievedAt: Date;
}

export interface WebAdapter {
  /**
   * Search for public web content
   * Returns a list of search results (typically 5-10 results)
   */
  search(query: string): Promise<SearchResult[]>;

  /**
   * Fetch a public web page
   * Returns the page content, status code, and metadata
   */
  fetch(url: string): Promise<FetchResult | null>;

  /**
   * Check if adapter is ready (credentials, connectivity, etc.)
   */
  isReady(): Promise<boolean>;

  /**
   * Get adapter name for logging/identification
   */
  getName(): string;
}
