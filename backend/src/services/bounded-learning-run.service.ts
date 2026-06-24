/**
 * Bounded Civilization Learning Run Service
 * =========================================
 *
 * Orchestrates a complete learning cycle:
 * - Source discovery from seed registries
 * - Governance policy checks
 * - Real web fetch with safety boundaries
 * - Content extraction
 * - LLM-based claim extraction
 * - Evidence classification
 * - Society/institution routing
 * - Audit trace recording
 *
 * Mission: Real autonomous learning with honest provenance, no synthetic data.
 */

import { v4 as uuidv4 } from 'uuid';
import { db } from '../db/client';
import { SourceDiscoveryEngine } from './source-discovery.service';
import { RealWebAdapter } from '../adapters/real-web-adapter';
import { ActionStatus } from '../types/action.types';

interface BoundedLearningRunConfig {
  goal: string;
  sourcePack: string;
  maxPages?: number;
  maxDepth?: number;
  maxDurationSeconds?: number;
  maxClaims?: number;
  allowedDomains?: string[];
  deniedDomains?: string[];
  provider?: 'openai' | 'local_llm' | 'deterministic_test_only';
  dryRun?: boolean;
  realWebEnabled?: boolean;
  useGoalBasedSearch?: boolean;  // NEW: Enable goal-aware search for sources
}

interface BoundedLearningRunResult {
  runId: string;
  status: 'success' | 'partial' | 'failed';
  goalText: string;
  sourcePack: string;
  sourcesDiscovered: number;
  sourcesAllowed: number;
  sourcesFetched: number;
  documentsFetched: number;
  claimsExtracted: number;
  claimsPersisted: number;
  claimsRouted: number;
  auditEventsLogged: number;
  errors: string[];
  warnings: string[];
  startedAt: Date;
  completedAt: Date;
  durationMs: number;
}

interface DiscoveredSource {
  source_url: string;
  source_domain: string;
  source_pack: string;
  trust_tier: string;
  allowed_to_fetch: boolean;
  reason_allowed?: string;
}

interface FetchedDocument {
  sourceId: string;
  url: string;
  title: string;
  content: string;
  contentHash: string;
  fetchedAt: Date;
}

interface ArticleMetadata {
  url: string;
  title: string;
  relevanceScore?: number;
}

export class BoundedCivilizationLearningRun {
  private sourceDiscovery = new SourceDiscoveryEngine();
  private webAdapter = new RealWebAdapter();
  private runId: string = '';
  private auditEvents: any[] = [];
  private errors: string[] = [];
  private warnings: string[] = [];

  async execute(config: BoundedLearningRunConfig): Promise<BoundedLearningRunResult> {
    this.runId = `learning_run_${Date.now()}`;
    const startedAt = new Date();

    console.log(`\n${'='.repeat(70)}`);
    console.log('BOUNDED CIVILIZATION LEARNING RUN');
    console.log(`${'='.repeat(70)}`);
    console.log(`Run ID: ${this.runId}`);
    console.log(`Goal: ${config.goal}`);
    console.log(`Source Pack: ${config.sourcePack}`);
    console.log(`Provider: ${config.provider || 'local_llm'}`);
    console.log(`Real Web Enabled: ${config.realWebEnabled ?? false}`);
    console.log(`Dry Run: ${config.dryRun ?? false}`);

    try {
      // Step 1: Discover sources
      console.log(`\n[1/8] Discovering sources from '${config.sourcePack}' pack...`);
      const discovered = await this.discoverSources(config);
      this.logAuditEvent('source_discovery_completed', {
        sourcePack: config.sourcePack,
        sourcesDiscovered: discovered.length,
      });

      // Step 2: Apply governance policy
      console.log(`\n[2/8] Applying governance policy...`);
      const allowed = this.applyGovernancePolicy(discovered, config);
      this.logAuditEvent('governance_policy_applied', {
        sourcesDiscovered: discovered.length,
        sourcesAllowed: allowed.length,
      });

      // Step 3: Fetch documents
      console.log(`\n[3/8] Fetching documents...`);
      const documents = await this.fetchDocuments(allowed, config);
      this.logAuditEvent('documents_fetched', {
        sourcesAllowed: allowed.length,
        documentsFetched: documents.length,
      });

      // Step 4: Extract content
      console.log(`\n[4/8] Extracting content...`);
      const extractedContent = documents.map(doc => ({
        ...doc,
        extractedText: doc.content.substring(0, 3000), // Limit for extraction
      }));

      // Step 5: Extract claims using LLM
      console.log(`\n[5/8] Extracting claims (provider: ${config.provider || 'local_llm'})...`);
      const claims = await this.extractClaims(extractedContent, config);
      this.logAuditEvent('claims_extracted', {
        documentsFetched: documents.length,
        claimsExtracted: claims.length,
      });

      // Step 6: Classify evidence
      console.log(`\n[6/8] Classifying evidence...`);
      const classified = this.classifyEvidence(claims, documents);
      this.logAuditEvent('evidence_classified', {
        claimsExtracted: claims.length,
        claimsClassified: classified.length,
      });

      // Step 7: Persist claims and evidence
      console.log(`\n[7/8] Persisting claims and evidence...`);
      const persisted = await this.persistClaims(classified, config);
      this.logAuditEvent('claims_persisted', {
        claimsClassified: classified.length,
        claimsPersisted: persisted.length,
      });

      // Step 8: Route to societies
      console.log(`\n[8/8] Routing claims to societies...`);
      const routed = await this.routeToSocieties(persisted, config);
      this.logAuditEvent('claims_routed', {
        claimsPersisted: persisted.length,
        claimsRouted: routed.length,
      });

      // Write audit trace
      await this.writeAuditTrace(this.runId);

      const completedAt = new Date();
      const durationMs = completedAt.getTime() - startedAt.getTime();

      console.log(`\n${'='.repeat(70)}`);
      console.log('LEARNING RUN COMPLETED');
      console.log(`${'='.repeat(70)}`);
      console.log(`Status: success`);
      console.log(`Duration: ${(durationMs / 1000).toFixed(1)}s`);
      console.log(`Sources discovered: ${discovered.length}`);
      console.log(`Sources allowed: ${allowed.length}`);
      console.log(`Documents fetched: ${documents.length}`);
      console.log(`Claims extracted: ${claims.length}`);
      console.log(`Claims persisted: ${persisted.length}`);
      console.log(`Claims routed: ${routed.length}`);
      console.log(`Audit events: ${this.auditEvents.length}`);

      return {
        runId: this.runId,
        status: 'success',
        goalText: config.goal,
        sourcePack: config.sourcePack,
        sourcesDiscovered: discovered.length,
        sourcesAllowed: allowed.length,
        sourcesFetched: documents.length,
        documentsFetched: documents.length,
        claimsExtracted: claims.length,
        claimsPersisted: persisted.length,
        claimsRouted: routed.length,
        auditEventsLogged: this.auditEvents.length,
        errors: this.errors,
        warnings: this.warnings,
        startedAt,
        completedAt,
        durationMs,
      };
    } catch (error: any) {
      const completedAt = new Date();
      const durationMs = completedAt.getTime() - startedAt.getTime();

      this.errors.push(error.message);
      this.logAuditEvent('run_failed', { error: error.message });

      console.error(`\n❌ LEARNING RUN FAILED: ${error.message}`);

      return {
        runId: this.runId,
        status: 'failed',
        goalText: config.goal,
        sourcePack: config.sourcePack,
        sourcesDiscovered: 0,
        sourcesAllowed: 0,
        sourcesFetched: 0,
        documentsFetched: 0,
        claimsExtracted: 0,
        claimsPersisted: 0,
        claimsRouted: 0,
        auditEventsLogged: this.auditEvents.length,
        errors: this.errors,
        warnings: this.warnings,
        startedAt,
        completedAt,
        durationMs,
      };
    }
  }

  private async discoverSources(config: BoundedLearningRunConfig): Promise<DiscoveredSource[]> {
    try {
      // First try: seed registry with goal-aware arxiv selection
      const discovered = await this.sourceDiscovery.discoverSourcesWithGoalAwareness(
        config.goal,
        config.sourcePack,
        config.maxPages ?? 5
      );

      console.log(`✅ Discovered ${discovered.length} sources (with goal-aware arxiv selection)`);

      // Second try: if enabled, augment with goal-based search results
      if (config.useGoalBasedSearch && discovered.length > 0) {
        try {
          const searchResults = await this.discoverSourcesViaGoalSearch(config.goal, 3);
          if (searchResults.length > 0) {
            console.log(`✅ Discovered ${searchResults.length} additional sources via goal-based search`);
            discovered.push(...(searchResults as any));
            this.logAuditEvent('sources_discovered_via_goal_search', {
              goal: config.goal,
              searchSourcesCount: searchResults.length,
            });
          }
        } catch (searchError: any) {
          console.warn(`⚠️ Goal-based search failed (non-blocking): ${searchError.message}`);
          // Don't fail the whole run; goal-based search is augmentation, not required
        }
      }

      return discovered as any;
    } catch (error: any) {
      console.warn(`⚠️ Source discovery failed: ${error.message}`);
      this.warnings.push(`Source discovery failed: ${error.message}`);
      return [];
    }
  }

  private async discoverSourcesViaGoalSearch(goal: string, maxResults: number = 3): Promise<DiscoveredSource[]> {
    // Extract search query from goal (remove common words, keep meaningful terms)
    const searchQuery = goal
      .replace(/\b(find|discover|research|recent|developments|advances|learn|about|in|the|a|and|or)\b/gi, '')
      .split(/\s+/)
      .filter(word => word.length > 3)
      .slice(0, 5)
      .join(' ')
      .trim();

    if (!searchQuery) {
      console.warn('⚠️ Could not extract search query from goal');
      return [];
    }

    try {
      console.log(`  🔍 Searching for goal-relevant sources: "${searchQuery}"`);
      const results = await this.webAdapter.search(searchQuery);

      if (!results || results.length === 0) {
        console.warn(`⚠️ Search returned no results for: "${searchQuery}"`);
        return [];
      }

      const discovered: any[] = results.slice(0, maxResults).map((result: any) => ({
        source_url: result.url,
        source_domain: new URL(result.url).hostname || 'unknown',
        source_pack: 'search_results',
        trust_tier: 'discovered',
        allowed_to_fetch: true,
        reason_allowed: `Discovered via goal-based search: "${goal}"`,
      }));

      return discovered as DiscoveredSource[];
    } catch (error: any) {
      throw new Error(`Goal-based search failed: ${error.message}`);
    }
  }

  private applyGovernancePolicy(
    sources: DiscoveredSource[],
    config: BoundedLearningRunConfig
  ): DiscoveredSource[] {
    const allowed = sources.filter(source => {
      // Check against denied domains
      if (config.deniedDomains?.includes(source.source_domain)) {
        this.logAuditEvent('source_denied', {
          url: source.source_url,
          reason: 'domain_in_denied_list',
        });
        return false;
      }

      // Check against allowed domains (if specified)
      if (config.allowedDomains && !config.allowedDomains.includes(source.source_domain)) {
        this.logAuditEvent('source_denied', {
          url: source.source_url,
          reason: 'domain_not_in_allowed_list',
        });
        return false;
      }

      // Check trust tier
      if (source.trust_tier !== 'seed' && source.trust_tier !== 'verified') {
        this.logAuditEvent('source_denied', {
          url: source.source_url,
          reason: 'low_trust_tier',
        });
        return false;
      }

      this.logAuditEvent('source_allowed', {
        url: source.source_url,
        domain: source.source_domain,
        trustTier: source.trust_tier,
      });
      return true;
    });

    console.log(`✅ Allowed ${allowed.length}/${sources.length} sources after policy check`);
    return allowed;
  }

  private async fetchDocuments(
    sources: DiscoveredSource[],
    config: BoundedLearningRunConfig
  ): Promise<FetchedDocument[]> {
    const documents: FetchedDocument[] = [];
    const maxPages = config.maxPages ?? 5;

    for (let i = 0; i < Math.min(sources.length, maxPages); i++) {
      const source = sources[i];

      try {
        if (config.dryRun) {
          console.log(`  [dry-run] Would fetch: ${source.source_url}`);
          this.logAuditEvent('fetch_skipped_dry_run', { url: source.source_url });
          continue;
        }

        if (!config.realWebEnabled) {
          console.log(`  [real-web disabled] Skipping: ${source.source_url}`);
          this.logAuditEvent('fetch_skipped_real_web_disabled', { url: source.source_url });
          continue;
        }

        // Check if this is a list page that needs URL extraction
        const isListPage = source.source_url.includes('/list') ||
                          source.source_url.includes('/trending') ||
                          source.source_url.includes('/blog/') ||
                          source.source_url.includes('/recent');

        if (isListPage) {
          // For arXiv, prefer API-based discovery for goal-relevant papers
          if (source.source_url.includes('arxiv.org')) {
            const categoryMatch = source.source_url.match(/\/list\/([^/]+)/);
            const category = categoryMatch ? categoryMatch[1] : undefined;

            console.log(`  📡 Fetching from arXiv API (goal-aware)`);
            const papers = await this.sourceDiscovery.discoverPapersViaArxivApi(config.goal, category, 10);

            if (papers.length > 0) {
              console.log(`  📄 Found ${papers.length} papers via arXiv API`);

              // Rank by goal relevance and select top-3
              const rankedArticles = this.rankArticlesByGoalRelevance(papers, config.goal);
              const selectedArticles = rankedArticles.slice(0, 3);

              // Fetch selected articles for content extraction
              for (let j = 0; j < selectedArticles.length; j++) {
                const article = selectedArticles[j];
                const articleUrl = article.url;
                console.log(`    Fetching (score: ${article.relevanceScore?.toFixed(2)}, title: ${article.title})`);

                try {
                const articleResult = await this.webAdapter.fetch(articleUrl);
                if (articleResult && articleResult.content.length > 500) {
                  const sourceId = uuidv4();

                  // Persist the actual article content
                  await db.query(
                    `INSERT INTO autonomy_evidence (
                      id, source_id, url, title, snippet, retrieved_at, content_hash,
                      source_type, is_public_access, created_at
                    ) VALUES ($1, $2, $3, $4, $5, NOW(), $6, $7, $8, NOW())`,
                    [
                      uuidv4(),
                      sourceId,
                      articleUrl,
                      articleResult.title || 'Untitled Article',
                      articleResult.content.substring(0, 2000),
                      articleResult.contentHash,
                      'web',
                      true,
                    ]
                  );

                  documents.push({
                    sourceId,
                    url: articleUrl,
                    title: articleResult.title || 'Untitled Article',
                    content: articleResult.content,
                    contentHash: articleResult.contentHash,
                    fetchedAt: new Date(),
                  });

                  this.logAuditEvent('fetch_succeeded', {
                    url: articleUrl,
                    sourceId,
                    contentLength: articleResult.content.length,
                    contentHash: articleResult.contentHash,
                  });
                }
              } catch (articleError: any) {
                this.logAuditEvent('fetch_failed', { url: articleUrl, error: articleError.message });
              }
              }
            }
          } else {
            // Non-arxiv list pages: use HTML scraping fallback
            const listResult = await this.webAdapter.fetch(source.source_url);
            if (listResult) {
              const articles = this.extractArticlesFromListPage(source.source_url, listResult.content);
              console.log(`  📄 Found ${articles.length} articles to evaluate`);

              const rankedArticles = this.rankArticlesByGoalRelevance(articles, config.goal);
              const selectedArticles = rankedArticles.slice(0, 3);

              for (let j = 0; j < selectedArticles.length; j++) {
                const article = selectedArticles[j];
                const articleUrl = article.url;
                try {
                  const articleResult = await this.webAdapter.fetch(articleUrl);
                  if (articleResult && articleResult.content.length > 500) {
                    const sourceId = uuidv4();
                    await db.query(
                      `INSERT INTO autonomy_evidence (
                        id, source_id, url, title, snippet, retrieved_at, content_hash,
                        source_type, is_public_access, created_at
                      ) VALUES ($1, $2, $3, $4, $5, NOW(), $6, $7, $8, NOW())`,
                      [
                        uuidv4(),
                        sourceId,
                        articleUrl,
                        articleResult.title || 'Untitled Article',
                        articleResult.content.substring(0, 2000),
                        articleResult.contentHash,
                        'web',
                        true,
                      ]
                    );

                    documents.push({
                      sourceId,
                      url: articleUrl,
                      title: articleResult.title || 'Untitled Article',
                      content: articleResult.content,
                      contentHash: articleResult.contentHash,
                      fetchedAt: new Date(),
                    });

                    this.logAuditEvent('fetch_succeeded', {
                      url: articleUrl,
                      sourceId,
                      contentLength: articleResult.content.length,
                      contentHash: articleResult.contentHash,
                    });
                  }
                } catch (articleError: any) {
                  this.logAuditEvent('fetch_failed', { url: articleUrl, error: articleError.message });
                }
              }
            }
          }
          continue;
        }

        console.log(`  Fetching: ${source.source_url}`);
        const result = await this.webAdapter.fetch(source.source_url);

        if (!result) {
          this.logAuditEvent('fetch_failed', { url: source.source_url, reason: 'http_error' });
          this.warnings.push(`Failed to fetch: ${source.source_url}`);
          continue;
        }

        const sourceId = uuidv4();

        // IMPORTANT: Persist evidence to autonomy_evidence so claims can link to real sources
        try {
          await db.query(
            `INSERT INTO autonomy_evidence (
              id, source_id, url, title, snippet, retrieved_at, content_hash,
              source_type, is_public_access, created_at
            ) VALUES ($1, $2, $3, $4, $5, NOW(), $6, $7, $8, NOW())`,
            [
              uuidv4(),
              sourceId,
              source.source_url,
              result.title || 'Untitled',
              result.content.substring(0, 2000), // First 2000 chars as snippet
              result.contentHash,
              'web',
              true,
            ]
          );
        } catch (dbError: any) {
          this.logAuditEvent('evidence_persistence_failed', {
            url: source.source_url,
            sourceId,
            error: dbError.message,
          });
          this.warnings.push(`Failed to persist evidence for ${source.source_url}: ${dbError.message}`);
          continue; // Skip this document if evidence can't be persisted
        }

        documents.push({
          sourceId,
          url: source.source_url,
          title: result.title || 'Untitled',
          content: result.content,
          contentHash: result.contentHash,
          fetchedAt: new Date(),
        });

        this.logAuditEvent('fetch_succeeded', {
          url: source.source_url,
          sourceId,
          contentLength: result.content.length,
          contentHash: result.contentHash,
        });
      } catch (error: any) {
        this.logAuditEvent('fetch_failed', { url: source.source_url, error: error.message });
        this.warnings.push(`Error fetching ${source.source_url}: ${error.message}`);
      }
    }

    console.log(`✅ Fetched ${documents.length} documents`);
    return documents;
  }

  private async extractClaims(documents: any[], config: BoundedLearningRunConfig): Promise<any[]> {
    const claims: any[] = [];
    const seenClaimTexts = new Set<string>(); // Track extracted claims to avoid duplicates

    // If provider is test-only, use deterministic extraction
    if (config.provider === 'deterministic_test_only') {
      console.log(`  Using deterministic test-only extraction`);
      for (const doc of documents) {
        claims.push({
          id: uuidv4(),
          text: `Test claim extracted from ${doc.title}`,
          sourceId: doc.sourceId,
          provider: 'deterministic_test_only',
          isTestFixture: true,
          confidence: 0.5,
        });
        this.logAuditEvent('claim_extracted_test_only', {
          sourceId: doc.sourceId,
          isTestFixture: true,
        });
      }
      return claims;
    }

    // Use OpenAI for real extraction if credentials available
    if (config.provider === 'openai' && process.env.OPENAI_API_KEY) {
      console.log(`  Using OpenAI GPT-4o-mini for extraction`);
      for (const doc of documents) {
        try {
          const extracted = await this.extractClaimsWithOpenAI(doc);
          if (extracted && extracted.length > 0) {
            // Filter out duplicate claims (same text)
            const uniqueClaims = extracted.filter((claim: any) => {
              const claimText = claim.text.toLowerCase().trim();
              if (seenClaimTexts.has(claimText)) {
                this.logAuditEvent('claim_deduplicated', {
                  text: claim.text.substring(0, 50),
                  sourceId: doc.sourceId,
                });
                return false; // Skip duplicate
              }
              seenClaimTexts.add(claimText);
              return true;
            });

            if (uniqueClaims.length > 0) {
              claims.push(
                ...uniqueClaims.map((claim: any) => ({
                  ...claim,
                  sourceId: doc.sourceId,
                  provider: 'openai',
                  isTestFixture: false,
                }))
              );
              this.logAuditEvent('claim_extracted_openai', {
                sourceId: doc.sourceId,
                claimsCount: uniqueClaims.length,
                duplicatesFiltered: extracted.length - uniqueClaims.length,
              });
            } else {
              this.logAuditEvent('claim_extraction_all_duplicates', {
                sourceId: doc.sourceId,
                totalExtracted: extracted.length,
              });
            }
          }
        } catch (error: any) {
          this.logAuditEvent('claim_extraction_failed', {
            sourceId: doc.sourceId,
            error: error.message,
          });
          this.warnings.push(`Failed to extract claims from ${doc.url}: ${error.message}`);
        }
      }
      return claims;
    }

    // If no valid provider, log and skip
    this.logAuditEvent('claim_extraction_skipped', {
      reason: `no_provider_available`,
    });
    console.log(`  ⚠️ No valid claim extraction provider configured`);

    return claims;
  }

  private async extractClaimsWithOpenAI(document: any): Promise<any[]> {
    const openaiKey = process.env.OPENAI_API_KEY || process.env.LLM_API_KEY;
    if (!openaiKey) {
      console.warn('  ⚠️ No OpenAI API key available');
      return [];
    }

    // Skip if no extracted text
    if (!document.extractedText || document.extractedText.trim().length === 0) {
      console.warn(`  ⚠️ No content to extract from: ${document.url}`);
      return [];
    }

    try {
      console.log(`  Calling OpenAI for ${document.url}...`);
      const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${openaiKey}`,
        },
        body: JSON.stringify({
          model: 'gpt-4o-mini',
          messages: [
            {
              role: 'system',
              content: `You are a claim extractor. Extract 2-4 factual claims from the provided content.

REQUIREMENTS:
- Claims must be specific and verifiable (not generic)
- Claims must be directly supported by the text
- Each claim should assert something about the research work or findings
- Avoid ONLY starting claims with "This paper", "The authors", "The work introduces"
- Focus on concrete findings, results, and claims from the work
- Do not invent or extrapolate beyond what is stated

Return ONLY a valid JSON array: [{"text": "...", "confidence": 0.0-1.0}]
Example: [{"text": "The study found 87% accuracy", "confidence": 0.95}]`,
            },
            {
              role: 'user',
              content: `Extract SPECIFIC FACTUAL CLAIMS from:\n\nTitle: ${document.title}\n\nAbstract/Content:\n${document.extractedText.substring(0, 2500)}`,
            },
          ],
          temperature: 0.3,
          max_tokens: 500,
        }),
      });

      if (!response.ok) {
        throw new Error(`OpenAI API error: ${response.status}`);
      }

      const data: any = await response.json();
      const content = data.choices?.[0]?.message?.content;

      if (!content) {
        console.warn('  ⚠️ OpenAI returned empty response');
        return [];
      }

      // Parse JSON response - handle markdown code blocks and plain JSON
      try {
        // Try to extract from markdown code block first
        let jsonText = content;
        const codeBlockMatch = content.match(/```(?:json)?\s*([\s\S]*?)```/);
        if (codeBlockMatch) {
          jsonText = codeBlockMatch[1].trim();
        } else {
          // Try to find JSON array
          const arrayMatch = content.match(/\[[\s\S]*\]/);
          if (arrayMatch) {
            jsonText = arrayMatch[0];
          }
        }

        const parsed = JSON.parse(jsonText);
        if (Array.isArray(parsed)) {
          if (parsed.length > 0) {
            console.log(`  ✅ Extracted ${parsed.length} claims from OpenAI`);
            return parsed.map((claim: any) => ({
              id: uuidv4(),
              text: claim.text || '',
              confidence: typeof claim.confidence === 'number' ? claim.confidence : 0.7,
            }));
          } else {
            console.log(`  ℹ️ OpenAI returned empty array (no claims found in content)`);
            return [];
          }
        }
      } catch (parseError: any) {
        console.warn(`  ⚠️ Failed to parse OpenAI JSON: ${parseError.message}\n     Response: ${content.substring(0, 150)}`);
      }

      return [];
    } catch (error: any) {
      console.warn(`  ⚠️ OpenAI extraction error: ${error.message}`);
      throw new Error(`OpenAI extraction failed: ${error.message}`);
    }
  }

  private classifyEvidence(claims: any[], documents: FetchedDocument[]): any[] {
    return claims.map(claim => ({
      ...claim,
      evidenceType: 'WEBSITE_ARTICLE',
      classification: 'OBSERVED',
      supportSourceIds: [claim.sourceId],
    }));
  }

  private async persistClaims(classified: any[], config: BoundedLearningRunConfig): Promise<any[]> {
    const persisted: any[] = [];

    for (const claim of classified) {
      try {
        // Don't persist test-only claims as real evidence
        if (claim.isTestFixture && config.provider === 'deterministic_test_only') {
          this.logAuditEvent('claim_rejected_test_only', {
            claimId: claim.id,
            reason: 'test_fixture_not_persisted',
          });
          continue;
        }

        const claimId = uuidv4();
        await db.query(
          `INSERT INTO autonomy_claims (
            id, claim_id, text, status, confidence, support_source_ids,
            generated_by, generated_at, created_at
          ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())`,
          [
            uuidv4(),
            claimId,
            claim.text,
            'OBSERVED', // Raw claims start as OBSERVED, not VERIFIED
            claim.confidence,
            JSON.stringify(claim.supportSourceIds),
            claim.provider || 'local_llm',
          ]
        );

        persisted.push({
          ...claim,
          claimId,
          persistedAt: new Date(),
        });

        this.logAuditEvent('claim_persisted', {
          claimId,
          text: claim.text.substring(0, 50),
          provider: claim.provider,
          isTestFixture: claim.isTestFixture,
        });
      } catch (error: any) {
        this.logAuditEvent('claim_persistence_failed', {
          error: error.message,
        });
        this.warnings.push(`Failed to persist claim: ${error.message}`);
      }
    }

    console.log(`✅ Persisted ${persisted.length} claims`);
    return persisted;
  }

  private async routeToSocieties(persisted: any[], config: BoundedLearningRunConfig): Promise<any[]> {
    const routed: any[] = [];

    for (const claim of persisted) {
      try {
        // Route to appropriate society based on source pack
        let society = 'SCIENTIFIC_SOCIETY';
        let institution = 'EVIDENCE_REVIEW';

        if (config.sourcePack === 'ai_tech' || config.sourcePack === 'technical') {
          society = 'ENGINEERING_SOCIETY';
          institution = 'TECHNICAL_REVIEW';
        } else if (config.sourcePack === 'governance') {
          society = 'GOVERNANCE_SOCIETY';
          institution = 'POLICY_REVIEW';
        }

        await db.query(
          `INSERT INTO autonomy_routed_claims (
            id, claim_id, destination_society, destination_institution,
            routing_reason, routing_confidence, status, created_at
          ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())`,
          [
            uuidv4(),
            claim.claimId,
            society,
            institution,
            `Routed from ${config.sourcePack} source pack`,
            0.9,
            'QUEUED_FOR_REVIEW',
          ]
        );

        routed.push({
          ...claim,
          destinationSociety: society,
          destinationInstitution: institution,
        });

        this.logAuditEvent('claim_routed', {
          claimId: claim.claimId,
          society,
          institution,
        });
      } catch (error: any) {
        this.logAuditEvent('claim_routing_failed', {
          error: error.message,
        });
        this.warnings.push(`Failed to route claim: ${error.message}`);
      }
    }

    console.log(`✅ Routed ${routed.length} claims to societies`);
    return routed;
  }

  private logAuditEvent(eventType: string, data?: any): void {
    const event = {
      runId: this.runId,
      eventType,
      timestamp: new Date().toISOString(),
      data,
    };
    this.auditEvents.push(event);
  }

  private async writeAuditTrace(runId: string): Promise<void> {
    try {
      for (const event of this.auditEvents) {
        await db.query(
          `INSERT INTO autonomy_audit_events (
            id, run_id, event_type, event_data, timestamp, created_at
          ) VALUES ($1, $2, $3, $4, $5, NOW())`,
          [
            uuidv4(),
            runId,
            event.eventType,
            JSON.stringify(event.data),
            event.timestamp,
          ]
        );
      }
    } catch (error: any) {
      console.warn(`Warning: Failed to write audit trace: ${error.message}`);
    }
  }

  private rankArticlesByGoalRelevance(articles: ArticleMetadata[], goal: string): ArticleMetadata[] {
    // Extract meaningful keywords from goal
    const goalKeywords = goal
      .toLowerCase()
      .split(/\s+/)
      .filter(word => word.length > 4)
      .map(word => word.replace(/[^a-z0-9]/g, ''));

    // Score each article
    const scored = articles.map(article => {
      const titleLower = article.title.toLowerCase().replace(/[^a-z0-9\s]/g, '');
      let score = 0;

      // Count keyword matches in title
      for (const keyword of goalKeywords) {
        if (titleLower.includes(keyword)) {
          score += 1;
        }
      }

      return {
        ...article,
        relevanceScore: score / Math.max(1, goalKeywords.length),
      };
    });

    // Sort by relevance score descending
    scored.sort((a, b) => (b.relevanceScore || 0) - (a.relevanceScore || 0));

    return scored;
  }

  private extractArticlesFromListPage(listUrl: string, content: string): ArticleMetadata[] {
    const articles: ArticleMetadata[] = [];

    // ArXiv export API format (Atom XML)
    if (listUrl.includes('arxiv.org') || content.includes('<?xml') || content.includes('<entry>')) {
      // Parse Atom XML entries: <entry> → <id> (URL) + <title> (title)
      const entryPattern = /<entry>[\s\S]*?<id>([^<]+)<\/id>[\s\S]*?<title>([^<]+)<\/title>/gi;

      let match;
      while ((match = entryPattern.exec(content)) && articles.length < 20) {
        let arxivUrl = match[1].trim();
        const title = match[2]
          .replace(/&amp;/g, '&')
          .replace(/&lt;/g, '<')
          .replace(/&gt;/g, '>')
          .replace(/&quot;/g, '"')
          .replace(/\s+/g, ' ')
          .trim();

        // Convert arxiv ID to https URL if needed
        if (arxivUrl.startsWith('http://arxiv.org')) {
          arxivUrl = arxivUrl.replace('http://', 'https://');
        } else if (!arxivUrl.startsWith('https://')) {
          arxivUrl = `https://arxiv.org${arxivUrl}`;
        }

        if (title.length > 5) {
          articles.push({
            url: arxivUrl,
            title: title.substring(0, 200),
          });
        }
      }
    }

    // Fallback for HTML list pages (non-arxiv)
    if (articles.length === 0) {
      const allLinks = content.match(/<a\s+href="([^"]+)"[^>]*>([^<]+)<\/a>/gi) || [];
      for (const link of allLinks.slice(0, 15)) {
        const match = link.match(/<a\s+href="([^"]+)"[^>]*>([^<]+)<\/a>/i);
        if (match) {
          const href = match[1];
          const text = match[2].trim();
          if (href.startsWith('http') && text.length > 5 && text.length < 200) {
            articles.push({ url: href, title: text });
          }
        }
      }
    }

    return articles;
  }

  private extractArticleUrlsFromListPage(listUrl: string, content: string): string[] {
    const urls = new Set<string>();

    // ArXiv patterns - target actual paper links
    if (listUrl.includes('arxiv.org')) {
      // Pattern: /abs/YYYY.NNNNN (paper abstract pages)
      const arxivMatches = content.match(/\/abs\/\d{4}\.\d{4,5}/g);
      if (arxivMatches) {
        for (const path of arxivMatches) {
          urls.add(`https://arxiv.org${path}`);
        }
      }
    }

    // GitHub patterns
    if (listUrl.includes('github.com')) {
      // Pattern: /[user]/[repo]
      const ghMatches = content.match(/href="(\/[a-zA-Z0-9_-]+\/[a-zA-Z0-9_.-]+)"/g);
      if (ghMatches) {
        for (const match of ghMatches) {
          const path = match.replace(/href="([^"]+)"/, '$1');
          if (!path.includes('/issues') && !path.includes('/settings') && !path.includes('/search')) {
            urls.add(`https://github.com${path}`);
          }
        }
      }
    }

    // Medium.com patterns
    if (listUrl.includes('medium.com')) {
      // Look for article links
      const mediumMatches = content.match(/href="https:\/\/medium\.com\/[^"]+"/g);
      if (mediumMatches) {
        for (const match of mediumMatches) {
          const url = match.replace('href="', '').replace('"', '');
          if (url && !url.includes('?') && url.length < 500) {
            urls.add(url);
          }
        }
      }
    }

    // Generic article link patterns (but be selective)
    const allHrefs = content.match(/href="([^"]+)"/g);
    if (allHrefs) {
      for (const match of allHrefs) {
        const href = match.replace('href="', '').replace('"', '');
        try {
          // Only accept http(s) absolute URLs, not anchors or page jumps
          if (href.startsWith('http') && !href.includes('?') && href.length < 500) {
            // Skip common non-article patterns
            if (!href.match(/\.(pdf|jpg|png|gif|css|js)$/i) &&
                !href.includes('/search') &&
                !href.includes('/tag/') &&
                !href.includes('/author/') &&
                !href.includes('/ads/') &&
                !href.includes('/static/')) {
              urls.add(href);
            }
          }
        } catch {
          // Skip invalid URLs
        }
      }
    }

    return Array.from(urls).slice(0, 15); // Return top 15 URLs
  }
}

// Singleton instance
export const boundedLearningRun = new BoundedCivilizationLearningRun();
