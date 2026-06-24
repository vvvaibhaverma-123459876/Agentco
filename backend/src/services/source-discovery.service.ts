/**
 * Source Discovery Engine (D1)
 * =============================
 * Discovers real URLs without needing a search API.
 *
 * Strategies:
 * 1. Seed URL registry - curated trusted sources
 * 2. RSS/Atom feed parsing - live feed discovery
 * 3. Sitemap.xml fetching - site structure discovery
 * 4. Previously discovered links - build on past discoveries
 *
 * Each discovered source has provenance metadata:
 * - source_url
 * - discovery_method ('seed', 'rss_feed', 'sitemap', 'link_extraction')
 * - discovery_timestamp
 * - source_domain
 * - source_pack ('technical', 'scientific', 'governance', 'business')
 * - topic_hint
 * - trust_tier ('seed', 'verified', 'discovered')
 * - allowed_to_fetch (boolean)
 * - risk_classification ('safe', 'caution', 'blocked')
 *
 * Uses native fetch (Node 18+) instead of node-fetch to avoid "Premature close" errors.
 */

interface DiscoveredSource {
  source_url: string;
  discovery_method: 'seed' | 'rss_feed' | 'sitemap' | 'link_extraction';
  discovery_timestamp: Date;
  source_domain: string;
  source_pack: 'technical' | 'scientific' | 'governance' | 'business' | 'ai_tech';
  topic_hint?: string;
  trust_tier: 'seed' | 'verified' | 'discovered';
  allowed_to_fetch: boolean;
  reason_allowed?: string;
  risk_classification: 'safe' | 'caution' | 'blocked';
}

interface SourcePack {
  name: string;
  description: string;
  sources: {
    url: string;
    title?: string;
    type: 'direct_page' | 'rss_feed' | 'sitemap';
    topic?: string;
  }[];
}

export class SourceDiscoveryEngine {
  private seedRegistry: Map<string, SourcePack> = new Map();

  constructor() {
    this.initializeSeedRegistry();
  }

  /**
   * Initialize curated source packs with known, reachable URLs
   * No paid APIs required - all sources are public
   */
  private initializeSeedRegistry(): void {
    // Technical & Software Engineering sources
    this.seedRegistry.set('technical', {
      name: 'Technical & Software Sources',
      description: 'Engineering, software architecture, programming best practices',
      sources: [
        // ArXiv CS papers (direct RSS + HTML pages)
        {
          url: 'http://arxiv.org/list/cs.AI/recent',
          title: 'ArXiv - Computer Science (Recent)',
          type: 'direct_page',
          topic: 'AI & Computer Science'
        },
        {
          url: 'http://feeds.arxiv.org/api/query?search_query=cat:cs.AI&start=0&max_results=10&sortBy=submittedDate&sortOrder=descending',
          title: 'ArXiv CS.AI Feed',
          type: 'rss_feed',
          topic: 'AI Research'
        },
        // GitHub Trending (public HTML)
        {
          url: 'https://github.com/trending',
          title: 'GitHub Trending',
          type: 'direct_page',
          topic: 'Open Source Projects'
        },
        // Stack Overflow Latest Questions
        {
          url: 'https://stackoverflow.com/questions/newest',
          title: 'Stack Overflow - Newest',
          type: 'direct_page',
          topic: 'Programming Q&A'
        },
        // HackerNews (YCombinator)
        {
          url: 'https://news.ycombinator.com/',
          title: 'Hacker News',
          type: 'direct_page',
          topic: 'Tech News & Discussion'
        },
      ]
    });

    // AI & Autonomy specific sources
    this.seedRegistry.set('ai_tech', {
      name: 'AI & Autonomy Sources',
      description: 'AI research, autonomy, agent systems, LLM developments',
      sources: [
        {
          url: 'https://openai.com/blog',
          title: 'OpenAI Blog',
          type: 'direct_page',
          topic: 'LLM & AI Updates'
        },
        {
          url: 'https://www.anthropic.com/news',
          title: 'Anthropic News',
          type: 'direct_page',
          topic: 'AI Safety & Capabilities'
        },
        {
          url: 'https://deepmind.google/blog/',
          title: 'DeepMind Blog',
          type: 'direct_page',
          topic: 'AI Research'
        },
        // arXiv AI papers
        {
          url: 'https://arxiv.org/list/cs.AI/recent',
          title: 'arXiv AI Papers (Recent)',
          type: 'direct_page',
          topic: 'AI Research'
        },
      ]
    });

    // Scientific & Research sources
    this.seedRegistry.set('scientific', {
      name: 'Scientific & Research Sources',
      description: 'Academic research, peer-reviewed studies, scientific preprints',
      sources: [
        {
          url: 'https://arxiv.org/list/q-bio/recent',
          title: 'arXiv - Quantitative Biology',
          type: 'direct_page',
          topic: 'Biology & Medicine Research'
        },
        {
          url: 'https://scholar.google.com/',
          title: 'Google Scholar',
          type: 'direct_page',
          topic: 'Academic Papers'
        },
      ]
    });

    // Business & Economics sources
    this.seedRegistry.set('business', {
      name: 'Business & Economics Sources',
      description: 'Business news, economic data, market analysis',
      sources: [
        {
          url: 'https://www.bloomberg.com/',
          title: 'Bloomberg',
          type: 'direct_page',
          topic: 'Business & Markets'
        },
        {
          url: 'https://news.ycombinator.com/',
          title: 'Hacker News',
          type: 'direct_page',
          topic: 'Tech Business News'
        },
      ]
    });

    // Governance & Policy sources
    this.seedRegistry.set('governance', {
      name: 'Governance & Policy Sources',
      description: 'Regulatory, policy, governance, AI ethics',
      sources: [
        {
          url: 'https://www.eff.org/',
          title: 'Electronic Frontier Foundation',
          type: 'direct_page',
          topic: 'Digital Rights & Policy'
        },
        {
          url: 'https://www.brookings.edu/',
          title: 'Brookings Institution',
          type: 'direct_page',
          topic: 'Policy & Research'
        },
      ]
    });
  }

  /**
   * Discover sources from a source pack without needing a search API
   * Returns real, reachable URLs with provenance metadata
   */
  async discoverSourcesFromPack(
    packName: string,
    maxSources?: number
  ): Promise<DiscoveredSource[]> {
    const pack = this.seedRegistry.get(packName);
    if (!pack) {
      console.warn(`Source pack not found: ${packName}`);
      return [];
    }

    const discovered: DiscoveredSource[] = [];
    const now = new Date();

    for (const source of pack.sources) {
      // Validate each source is reachable
      const isReachable = await this.validateSourceReachability(source.url);

      if (isReachable) {
        discovered.push({
          source_url: source.url,
          discovery_method: source.type === 'rss_feed' ? 'rss_feed' : 'seed',
          discovery_timestamp: now,
          source_domain: new URL(source.url).hostname || 'unknown',
          source_pack: packName as any,
          topic_hint: source.topic,
          trust_tier: 'seed',
          allowed_to_fetch: true,
          reason_allowed: `Seed registry - ${pack.name}`,
          risk_classification: 'safe',
        });
      } else {
        console.warn(`Source not reachable: ${source.url}`);
      }

      // Honor maxSources limit
      if (maxSources && discovered.length >= maxSources) {
        break;
      }
    }

    return discovered;
  }

  /**
   * Discover sources from an RSS/Atom feed
   * Parses feed and extracts article URLs
   */
  async discoverSourcesFromRssFeed(
    feedUrl: string,
    packName: string,
    maxItems: number = 10
  ): Promise<DiscoveredSource[]> {
    const discovered: DiscoveredSource[] = [];

    try {
      const response = await Promise.race([
        fetch(feedUrl),
        new Promise<Response>((_, reject) =>
          setTimeout(() => reject(new Error('timeout')), 8000)
        ),
      ]);
      if (!response.ok) {
        console.warn(`RSS feed not reachable: ${feedUrl}`);
        return [];
      }

      const feedContent = await response.text();

      // Simple RSS/Atom parsing - look for item URLs
      // This is a simple implementation; full XML parsing requires xml2js
      const urlPattern = /<link[^>]*>([^<]+)<\/link>/g;
      const now = new Date();
      let count = 0;

      let match;
      while ((match = urlPattern.exec(feedContent)) && count < maxItems) {
        const url = match[1].trim();

        // Validate URL format
        try {
          new URL(url);

          // Validate reachability
          const isReachable = await this.validateSourceReachability(url);
          if (isReachable) {
            discovered.push({
              source_url: url,
              discovery_method: 'rss_feed',
              discovery_timestamp: now,
              source_domain: new URL(url).hostname || 'unknown',
              source_pack: packName as any,
              trust_tier: 'discovered',
              allowed_to_fetch: true,
              reason_allowed: `Discovered from RSS feed: ${feedUrl}`,
              risk_classification: 'safe',
            });

            count++;
          }
        } catch (error) {
          // Invalid URL, skip
          continue;
        }
      }
    } catch (error) {
      console.error(`Error parsing RSS feed ${feedUrl}: ${error}`);
    }

    return discovered;
  }

  /**
   * Discover sources from sitemap.xml
   */
  async discoverSourcesFromSitemap(
    sitemapUrl: string,
    packName: string,
    maxUrls: number = 20
  ): Promise<DiscoveredSource[]> {
    const discovered: DiscoveredSource[] = [];

    try {
      const response = await Promise.race([
        fetch(sitemapUrl),
        new Promise<Response>((_, reject) =>
          setTimeout(() => reject(new Error('timeout')), 8000)
        ),
      ]);
      if (!response.ok) {
        console.warn(`Sitemap not reachable: ${sitemapUrl}`);
        return [];
      }

      const sitemapContent = await response.text();

      // Parse XML sitemap
      const urlPattern = /<loc>([^<]+)<\/loc>/g;
      const now = new Date();
      let count = 0;

      let match;
      while ((match = urlPattern.exec(sitemapContent)) && count < maxUrls) {
        const url = match[1].trim();

        try {
          new URL(url);

          const isReachable = await this.validateSourceReachability(url);
          if (isReachable) {
            discovered.push({
              source_url: url,
              discovery_method: 'sitemap',
              discovery_timestamp: now,
              source_domain: new URL(url).hostname || 'unknown',
              source_pack: packName as any,
              trust_tier: 'discovered',
              allowed_to_fetch: true,
              reason_allowed: `Discovered from sitemap: ${sitemapUrl}`,
              risk_classification: 'safe',
            });

            count++;
          }
        } catch (error) {
          continue;
        }
      }
    } catch (error) {
      console.error(`Error parsing sitemap ${sitemapUrl}: ${error}`);
    }

    return discovered;
  }

  /**
   * Quick reachability check - HEAD request with timeout
   * Returns true if URL responds, false if unreachable
   */
  private async validateSourceReachability(url: string): Promise<boolean> {
    try {
      const response = await Promise.race([
        fetch(url, {
          method: 'HEAD',
        }),
        new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error('timeout')), 3000)
        ),
      ]);

      return response.ok || response.status < 500;
    } catch (error) {
      // Unreachable
      return false;
    }
  }

  /**
   * Get all available source packs
   */
  getAvailableSourcePacks(): string[] {
    return Array.from(this.seedRegistry.keys());
  }

  /**
   * Get description of a source pack
   */
  getSourcePackDescription(packName: string): string | null {
    const pack = this.seedRegistry.get(packName);
    return pack ? pack.description : null;
  }
}

// Singleton instance
export const sourceDiscovery = new SourceDiscoveryEngine();
