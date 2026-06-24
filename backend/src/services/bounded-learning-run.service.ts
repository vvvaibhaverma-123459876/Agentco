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
      const discovered = await this.sourceDiscovery.discoverSourcesFromPack(
        config.sourcePack,
        config.maxPages ?? 5
      );

      console.log(`✅ Discovered ${discovered.length} sources`);
      return discovered as any;
    } catch (error: any) {
      console.warn(`⚠️ Source discovery failed: ${error.message}`);
      this.warnings.push(`Source discovery failed: ${error.message}`);
      return [];
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
            claims.push(
              ...extracted.map((claim: any) => ({
                ...claim,
                sourceId: doc.sourceId,
                provider: 'openai',
                isTestFixture: false,
              }))
            );
            this.logAuditEvent('claim_extracted_openai', {
              sourceId: doc.sourceId,
              claimsCount: extracted.length,
            });
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
              content: `You are a claim extractor. Extract 1-3 factual claims from the provided content.
Return ONLY a valid JSON array with objects having: text (string), confidence (0-1 number).
Example: [{"text": "claim 1", "confidence": 0.9}]
Claims must be supported by evidence in the content.
Do not invent claims not present in the text.`,
            },
            {
              role: 'user',
              content: `Extract claims from:\n\nTitle: ${document.title}\n\nContent:\n${document.extractedText.substring(0, 3000)}`,
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
}

// Singleton instance
export const boundedLearningRun = new BoundedCivilizationLearningRun();
