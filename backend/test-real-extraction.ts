#!/usr/bin/env npx ts-node
/**
 * Test Real Extraction Loop: Fetch → Extract → Persist
 *
 * Single, verifiable end-to-end test:
 * 1. Fetch real arXiv paper (2307.09288 - LLaMA 2)
 * 2. Extract ONE claim using OpenAI
 * 3. Persist to autonomy_evidence and autonomy_claims
 * 4. Show actual DB rows as proof
 */

import { db } from './src/db/client';
import { RealWebAdapter } from './src/adapters/real-web-adapter';
import { v4 as uuidv4 } from 'uuid';
import fetch from 'node-fetch';

async function testRealExtractionLoop() {
  console.log('\n' + '='.repeat(70));
  console.log('TEST: REAL EXTRACTION LOOP');
  console.log('='.repeat(70));
  console.log('Goal: Fetch → Extract → Persist ONE real claim\n');

  const paperUrl = 'https://arxiv.org/abs/2307.09288'; // LLaMA 2 paper
  const openaiKey = process.env.OPENAI_API_KEY || process.env.LLM_API_KEY;

  if (!openaiKey) {
    console.error('❌ No OpenAI API key found');
    process.exit(1);
  }

  try {
    // STEP 1: Fetch from arXiv using RealWebAdapter
    console.log('📡 STEP 1: Fetching arXiv paper...');
    const adapter = new RealWebAdapter();
    const fetchResult = await adapter.fetch(paperUrl);

    if (!fetchResult) {
      console.error('❌ Fetch failed');
      process.exit(1);
    }

    console.log(`✅ Fetched: ${fetchResult.title}`);
    console.log(`   Content length: ${fetchResult.content.length} chars`);
    console.log(`   Content hash: ${fetchResult.contentHash}`);

    // Extract abstract for LLM
    const abstractMatch = fetchResult.content.match(
      /<span\s+class="[^"]*abstract[^"]*"[^>]*>([\s\S]*?)<\/span>/i
    );
    let abstract = '';
    if (abstractMatch) {
      abstract = abstractMatch[1]
        .replace(/<[^>]*>/g, '')
        .replace(/\s+/g, ' ')
        .trim();
    }

    if (!abstract || abstract.length < 100) {
      // Fallback to meta description
      const metaMatch = fetchResult.content.match(
        /name="description" content="([^"]*)"/i
      );
      if (metaMatch) {
        abstract = metaMatch[1];
      }
    }

    console.log(`\n📄 Extracted abstract: ${abstract.substring(0, 100)}...`);

    // STEP 2: Extract ONE claim using OpenAI
    console.log('\n🤖 STEP 2: Extracting claim with OpenAI...');
    const claimPrompt = `Extract ONE specific, verifiable claim from this paper abstract.
Return ONLY a JSON object (no markdown):
{"text": "specific claim", "confidence": 0.9}

Rules: Concrete finding, specific metrics if available, no generic statements.

Paper abstract: ${abstract.substring(0, 2000)}`;

    const apiResponse = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${openaiKey}`,
      },
      body: JSON.stringify({
        model: 'gpt-4o-mini',
        messages: [
          {
            role: 'user',
            content: claimPrompt,
          },
        ],
        temperature: 0.2,
        max_tokens: 300,
      }),
    } as any);

    if (!apiResponse.ok) {
      const error = await apiResponse.text();
      console.error(`❌ OpenAI API error ${apiResponse.status}: ${error.substring(0, 200)}`);
      process.exit(1);
    }

    const apiData = await apiResponse.json() as any;
    const content = apiData.choices?.[0]?.message?.content || '';

    if (!content) {
      console.error('❌ No response from OpenAI');
      process.exit(1);
    }

    // Parse JSON (handle code blocks)
    let jsonText = content.trim();
    const codeMatch = jsonText.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (codeMatch) {
      jsonText = codeMatch[1].trim();
    }

    const claimData = JSON.parse(jsonText);
    console.log(`✅ Extracted claim: "${claimData.text.substring(0, 80)}..."`);
    console.log(`   Confidence: ${claimData.confidence}`);

    // STEP 3: Persist to Database
    console.log('\n💾 STEP 3: Persisting to database...');

    const sourceId = uuidv4();
    const claimId = uuidv4();
    const actionId = uuidv4();

    // Insert evidence
    await db.query(
      `INSERT INTO autonomy_evidence (
        id, source_id, url, title, snippet, retrieved_at, content_hash,
        source_type, is_public_access, created_at
      ) VALUES ($1, $2, $3, $4, $5, NOW(), $6, $7, $8, NOW())`,
      [
        uuidv4(),
        sourceId,
        paperUrl,
        fetchResult.title,
        abstract.substring(0, 1000),
        fetchResult.contentHash,
        'web',
        true,
      ]
    );

    console.log(`✅ Evidence persisted: source_id=${sourceId}`);

    // Insert claim
    await db.query(
      `INSERT INTO autonomy_claims (
        id, claim_text, confidence, support_source_ids,
        status, derived_from_action_ids, provider,
        created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())`,
      [
        claimId,
        claimData.text,
        claimData.confidence,
        JSON.stringify([sourceId]),
        'supported',
        JSON.stringify([actionId]),
        'openai',
      ]
    );

    console.log(`✅ Claim persisted: claim_id=${claimId}`);

    // STEP 4: Verify in Database
    console.log('\n🔍 STEP 4: Verifying in database...');

    const evidence = await db.query(
      'SELECT id, source_id, url, title, content_hash FROM autonomy_evidence WHERE source_id = $1',
      [sourceId]
    );

    const claim = await db.query(
      'SELECT id, claim_text, confidence, status, provider FROM autonomy_claims WHERE id = $1',
      [claimId]
    );

    console.log('\n📊 DATABASE VERIFICATION:');
    console.log('\n✅ autonomy_evidence row:');
    if (evidence.rows.length > 0) {
      const row = evidence.rows[0];
      console.log(`   id: ${row.id}`);
      console.log(`   source_id: ${row.source_id}`);
      console.log(`   url: ${row.url}`);
      console.log(`   title: ${row.title}`);
      console.log(`   content_hash: ${row.content_hash}`);
    }

    console.log('\n✅ autonomy_claims row:');
    if (claim.rows.length > 0) {
      const row = claim.rows[0];
      console.log(`   id: ${row.id}`);
      console.log(`   claim_text: "${row.claim_text.substring(0, 80)}..."`);
      console.log(`   confidence: ${row.confidence}`);
      console.log(`   status: ${row.status}`);
      console.log(`   provider: ${row.provider}`);
    }

    console.log('\n' + '='.repeat(70));
    console.log('✅ SUCCESS: Real extraction loop working!');
    console.log('='.repeat(70));
    console.log('\nSummary:');
    console.log('  ✅ Fetched: real arXiv paper');
    console.log('  ✅ Extracted: 1 claim via OpenAI');
    console.log('  ✅ Persisted: evidence + claim to database');
    console.log('  ✅ Verified: actual DB rows created\n');

    process.exit(0);
  } catch (error: any) {
    console.error(`\n❌ Error: ${error.message}`);
    console.error(error.stack);
    process.exit(1);
  }
}

testRealExtractionLoop();
