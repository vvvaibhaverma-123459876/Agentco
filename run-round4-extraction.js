#!/usr/bin/env node
/**
 * Round 4: Diverse Source Extraction Runner
 *
 * Fetches 10 diverse AI/ML research papers and extracts claims.
 */

// Use backend node_modules
const Module = require('module');
const originalRequire = Module.prototype.require;
const path = require('path');

Module.prototype.require = function (id) {
  if (['node-fetch', 'uuid'].includes(id)) {
    const modulePath = path.join('/Users/Zet/Desktop/Agentco/backend/node_modules', id);
    return originalRequire.call(this, modulePath);
  }
  return originalRequire.apply(this, arguments);
};

const fetch = require('node-fetch');
const { v4: uuidv4 } = require('uuid');

// More reliable AI research papers
const DIVERSE_SOURCES = [
  'https://arxiv.org/abs/2307.09288', // LLaMA 2: Open Foundation and Fine-Tuned Chat Models
  'https://arxiv.org/abs/2305.02301', // An Introduction to Vision Transformers
  'https://arxiv.org/abs/2306.12929', // QLoRA: Efficient Finetuning of Quantized LLMs
  'https://arxiv.org/abs/2305.18290', // Scaling Laws and Emergent Abilities
  'https://arxiv.org/abs/2310.04406', // LLM Agents for Software Engineering
  'https://arxiv.org/abs/2305.14688', // Mixtral of Experts
  'https://arxiv.org/abs/2306.13549', // Scaling Vision with Sparse Mixture of Experts
  'https://arxiv.org/abs/2303.08774', // GPT-4 Technical Report
  'https://arxiv.org/abs/2308.12966', // LLaMA: Open and Efficient Foundation Language Models
  'https://arxiv.org/abs/2311.05666', // Mistral: A 7B Language Model
];

class Round4Extractor {
  constructor() {
    this.apiKey = process.env.OPENAI_API_KEY || process.env.LLM_API_KEY || '';
    if (!this.apiKey) {
      throw new Error('No OpenAI API key found');
    }
    this.allClaims = [];
    this.successCount = 0;
    this.failureCount = 0;
  }

  async fetchAbstract(url) {
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

      // Try to extract from HTML blockquote (most common arXiv format)
      let abstract = null;

      // Try blockquote format
      const blockquoteMatch = html.match(
        /<blockquote\s+class="[^"]*abstract[^"]*"[^>]*>([\s\S]*?)<\/blockquote>/i
      );
      if (blockquoteMatch) {
        abstract = blockquoteMatch[1]
          .replace(/<[^>]*>/g, '')
          .replace(/\s+/g, ' ')
          .trim();
      }

      // Try span format
      if (!abstract) {
        const spanMatch = html.match(
          /<span\s+class="[^"]*abstract[^"]*"[^>]*>([\s\S]*?)<\/span>/i
        );
        if (spanMatch) {
          abstract = spanMatch[1]
            .replace(/<[^>]*>/g, '')
            .replace(/\s+/g, ' ')
            .trim();
        }
      }

      // Try meta description
      if (!abstract) {
        const metaMatch = html.match(
          /<meta[^>]*name="description"[^>]*content="([^"]*)"/i
        );
        if (metaMatch) {
          abstract = metaMatch[1]
            .replace(/^Abstract page for arXiv paper [^:]*: /, '')
            .trim();
        }
      }

      if (!abstract || abstract.length < 100) {
        console.log(`  ⚠️  No abstract found or too short`);
        return null;
      }

      console.log(`  ✅ Extracted ${abstract.length} chars`);
      return abstract.substring(0, 4000);
    } catch (error) {
      console.log(`  ❌ Error: ${error.message}`);
      return null;
    }
  }

  async extractClaims(abstract, sourceUrl) {
    try {
      const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify({
          model: 'gpt-4o-mini',
          messages: [
            {
              role: 'system',
              content: `Extract 2-3 SPECIFIC, VERIFIABLE claims from this ML research paper abstract.
Return ONLY a JSON array with no code blocks or markdown:
[{"text": "specific claim with metrics", "confidence": 0.85}]

Rules for claims:
- Must be concrete findings, not methodology descriptions
- Include specific numbers, percentages, or performance metrics when mentioned
- Focus on novel contributions or empirical results
- Avoid generic motivational statements
- Each claim should be independently verifiable from the abstract
- Confidence: 0.5-1.0 (likelihood the exact claim appears in paper)`,
            },
            {
              role: 'user',
              content: `Paper abstract:\n\n${abstract}`,
            },
          ],
          temperature: 0.2,
          max_tokens: 600,
        }),
        timeout: 30000,
      });

      if (!response.ok) {
        console.log(`    ⚠️  OpenAI error ${response.status}`);
        return [];
      }

      const data = await response.json();
      const content = data.choices?.[0]?.message?.content || '';

      // Parse JSON carefully
      let jsonText = content.trim();

      // Remove markdown code blocks if present
      const codeBlockMatch = jsonText.match(/```(?:json)?\s*([\s\S]*?)```/);
      if (codeBlockMatch) {
        jsonText = codeBlockMatch[1].trim();
      }

      // Try to parse
      let claims = [];
      try {
        claims = JSON.parse(jsonText);
        if (!Array.isArray(claims)) {
          console.log(`    ⚠️  Response is not an array`);
          return [];
        }
      } catch (parseError) {
        console.log(`    ⚠️  JSON parse error: ${parseError.message}`);
        return [];
      }

      // Filter and map
      return claims
        .filter((c) => c && c.text && typeof c.text === 'string' && c.text.length > 25)
        .map((c) => ({
          id: uuidv4(),
          text: c.text.substring(0, 500),
          source_url: sourceUrl,
          confidence: typeof c.confidence === 'number' ? Math.min(1, Math.max(0.5, c.confidence)) : 0.75,
          extracted_at: new Date().toISOString(),
        }));
    } catch (error) {
      console.log(`    ❌ Error: ${error.message}`);
      return [];
    }
  }

  async run() {
    console.log('\n' + '='.repeat(70));
    console.log('ROUND 4: DIVERSE SOURCE EXTRACTION');
    console.log('='.repeat(70));
    console.log(`Target: ${DIVERSE_SOURCES.length} papers`);
    console.log(`Goal: Extract 20-30 diverse, high-quality AI research claims\n`);

    for (let i = 0; i < DIVERSE_SOURCES.length; i++) {
      const sourceUrl = DIVERSE_SOURCES[i];
      console.log(`\n[${i + 1}/${DIVERSE_SOURCES.length}] ${sourceUrl}`);

      const abstract = await this.fetchAbstract(sourceUrl);
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

      // Rate limit: 200ms between API calls
      await new Promise((r) => setTimeout(r, 200));
    }

    // Summary and export
    console.log('\n' + '='.repeat(70));
    console.log('EXTRACTION SUMMARY');
    console.log('='.repeat(70));
    console.log(`✅ Papers processed: ${this.successCount}/${DIVERSE_SOURCES.length}`);
    console.log(`📊 Total claims extracted: ${this.allClaims.length}`);
    console.log(`❌ Failed papers: ${this.failureCount}`);

    if (this.allClaims.length > 0) {
      const fs = require('fs');
      const csv = this.allClaims
        .map(
          (c) =>
            `"${c.id}","${c.text.replace(/"/g, '""')}","${c.source_url}",${c.confidence}`
        )
        .join('\n');

      const filename = '/Users/Zet/Desktop/Agentco/round4-extracted-claims.csv';
      fs.writeFileSync(filename, 'claim_id,text,source_url,llm_confidence\n' + csv);

      console.log(`\n📁 Saved to: ${filename}`);
      console.log(`\nSample claims (first 3):`);
      this.allClaims.slice(0, 3).forEach((c, idx) => {
        console.log(`\n  ${idx + 1}. "${c.text.substring(0, 90)}"`);
        console.log(`     Source: ${c.source_url.split('/').pop()}`);
        console.log(`     Confidence: ${c.confidence}`);
      });
    } else {
      console.log(`\n⚠️  No claims extracted. Check network or API key.`);
    }
  }
}

// Run
const extractor = new Round4Extractor();
extractor
  .run()
  .then(() => {
    process.exit(0);
  })
  .catch((err) => {
    console.error('❌ Fatal error:', err.message);
    process.exit(1);
  });
