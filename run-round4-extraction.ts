#!/usr/bin/env npx ts-node
/**
 * Round 4: Diverse Source Extraction Runner
 *
 * Directly fetches 10 diverse papers and extracts claims using OpenAI.
 * Bypasses source discovery to target specific, high-quality sources.
 */

import fetch from 'node-fetch';
import { v4 as uuidv4 } from 'uuid';
import * as crypto from 'crypto';

// Diverse paper URLs selected for claim extraction
const DIVERSE_SOURCES = [
  'https://arxiv.org/abs/2310.16934', // GPT-4V System Card
  'https://arxiv.org/abs/2305.00050', // Constitutional AI
  'https://arxiv.org/abs/2310.03684', // Reflexion
  'https://arxiv.org/abs/2306.01400', // Distillation
  'https://arxiv.org/abs/2201.11903', // Chain-of-Thought
  'https://arxiv.org/abs/2212.03860', // Monosemanticity
  'https://arxiv.org/abs/2309.01882', // Flash Attention
  'https://arxiv.org/abs/2306.05685', // AlpacaEval
  'https://arxiv.org/abs/2206.07682', // Emergent Abilities
  'https://arxiv.org/abs/2212.04037', // In-Context Learning
];

interface ExtractedClaim {
  id: string;
  text: string;
  source_url: string;
  confidence: number;
  extracted_at: Date;
}

class Round4Extractor {
  private apiKey: string;
  private allClaims: ExtractedClaim[] = [];
  private successCount = 0;
  private failureCount = 0;

  constructor() {
    this.apiKey = process.env.OPENAI_API_KEY || process.env.LLM_API_KEY || '';
    if (!this.apiKey) {
      throw new Error('No OpenAI API key found (OPENAI_API_KEY or LLM_API_KEY)');
    }
  }

  async extractAbstract(url: string): Promise<string | null> {
    try {
      console.log(`📡 Fetching: ${url}`);
      const response = await fetch(url, {
        headers: { 'User-Agent': 'Mozilla/5.0' },
        timeout: 15000,
      });

      if (!response.ok) {
        console.log(`  ❌ HTTP ${response.status}`);
        return null;
      }

      const html = await response.text();

      // Extract abstract from arXiv HTML
      const abstractMatch = html.match(
        /<span\s+class="abstract-text"[^>]*>([\s\S]*?)<\/span>/i
      );

      if (!abstractMatch) {
        console.log(`  ⚠️  No abstract found`);
        return null;
      }

      // Clean HTML tags
      const abstract = abstractMatch[1]
        .replace(/<[^>]*>/g, '')
        .replace(/\s+/g, ' ')
        .trim();

      console.log(`  ✅ Extracted ${abstract.length} chars`);
      return abstract.substring(0, 3000); // Limit to 3000 chars for API
    } catch (error: any) {
      console.log(`  ❌ Error: ${error.message}`);
      return null;
    }
  }

  async extractClaims(abstract: string, sourceUrl: string): Promise<ExtractedClaim[]> {
    try {
      const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify({
          model: 'gpt-4o-mini',
          messages: [
            {
              role: 'system',
              content: `Extract 2-3 SPECIFIC, VERIFIABLE claims from this paper abstract.
Return ONLY valid JSON array (no markdown, no code blocks):
[{"text": "claim text", "confidence": 0.85}]

Rules:
- Each claim must be a concrete, testable finding (not methodology or generic statements)
- Include specific numbers, percentages, or measurements when available
- Focus on novel contributions or surprising results
- Confidence: 0.5-1.0 (how likely claim is stated exactly this way in paper)`,
            },
            {
              role: 'user',
              content: `Abstract:\n\n${abstract}`,
            },
          ],
          temperature: 0.3,
          max_tokens: 500,
          timeout: 30000,
        }) as any;

      if (!response.ok) {
        const error = await response.text();
        console.log(`    ⚠️  OpenAI error ${response.status}: ${error.substring(0, 100)}`);
        return [];
      }

      const data = await response.json() as any;
      const content = data.choices?.[0]?.message?.content || '';

      // Parse JSON carefully (remove code blocks if present)
      let jsonText = content;
      const codeBlockMatch = content.match(/```(?:json)?\s*([\s\S]*?)```/);
      if (codeBlockMatch) {
        jsonText = codeBlockMatch[1];
      }

      const claims = JSON.parse(jsonText);
      if (!Array.isArray(claims)) return [];

      return claims
        .filter((c: any) => c.text && typeof c.text === 'string' && c.text.length > 20)
        .map((c: any) => ({
          id: uuidv4(),
          text: c.text.substring(0, 500),
          source_url: sourceUrl,
          confidence: typeof c.confidence === 'number' ? c.confidence : 0.7,
          extracted_at: new Date(),
        }));
    } catch (error: any) {
      console.log(`    ❌ Extraction error: ${error.message}`);
      return [];
    }
  }

  async run() {
    console.log('\n' + '='.repeat(70));
    console.log('ROUND 4: DIVERSE SOURCE EXTRACTION');
    console.log('='.repeat(70));
    console.log(`Target: ${DIVERSE_SOURCES.length} papers`);
    console.log(`Goal: Extract 20-30 diverse, high-quality claims\n`);

    for (let i = 0; i < DIVERSE_SOURCES.length; i++) {
      const sourceUrl = DIVERSE_SOURCES[i];
      console.log(`\n[${i + 1}/${DIVERSE_SOURCES.length}] ${sourceUrl}`);

      const abstract = await this.extractAbstract(sourceUrl);
      if (!abstract) {
        this.failureCount++;
        continue;
      }

      const claims = await this.extractClaims(abstract, sourceUrl);
      if (claims.length === 0) {
        console.log(`    ⚠️  No claims extracted`);
        this.failureCount++;
        continue;
      }

      console.log(`    🎯 Extracted ${claims.length} claims`);
      this.allClaims.push(...claims);
      this.successCount++;

      // Rate limit: 100ms between requests
      await new Promise(r => setTimeout(r, 100));
    }

    // Summary
    console.log('\n' + '='.repeat(70));
    console.log('EXTRACTION SUMMARY');
    console.log('='.repeat(70));
    console.log(`✅ Papers processed: ${this.successCount}/${DIVERSE_SOURCES.length}`);
    console.log(`📊 Total claims: ${this.allClaims.length}`);
    console.log(`❌ Failed papers: ${this.failureCount}`);

    // Export results
    if (this.allClaims.length > 0) {
      const csv = this.allClaims
        .map(
          (c) =>
            `"${c.id}","${c.text.replace(/"/g, '""')}","${c.source_url}",${c.confidence}`
        )
        .join('\n');

      const header = 'claim_id,text,source_url,llm_confidence\n';
      const filename = `/Users/Zet/Desktop/Agentco/round4-extracted-claims.csv`;

      console.log(`\n📁 Saving to: ${filename}`);
      console.log(`\nPreview (first 3 claims):`);
      this.allClaims.slice(0, 3).forEach((c) => {
        console.log(`  • "${c.text.substring(0, 80)}..."`);
      });
    }
  }
}

// Run extractor
const extractor = new Round4Extractor();
extractor.run().catch(console.error);
