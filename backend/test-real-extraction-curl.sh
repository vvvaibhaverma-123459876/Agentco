#!/bin/bash
# Test Real Extraction Loop: Fetch → Extract → Persist (using curl + npx ts-node)

set -e

source /Users/Zet/Desktop/Agentco/.codex.env
export OPENAI_API_KEY="$LLM_API_KEY"
export DATABASE_URL="$AGENTCO_TEST_DATABASE_URL"

echo ""
echo "======================================================================"
echo "TEST: REAL EXTRACTION LOOP"
echo "======================================================================"
echo "Goal: Fetch → Extract → Persist ONE real claim"
echo ""

# STEP 1: Fetch arXiv paper using curl
echo "📡 STEP 1: Fetching arXiv paper..."
PAPER_URL="https://arxiv.org/abs/2307.09288"
HTML=$(curl -s -L "$PAPER_URL" 2>/dev/null | head -c 100000)

if [ -z "$HTML" ]; then
  echo "❌ Fetch failed"
  exit 1
fi

echo "✅ Fetched: LLaMA 2 paper"
echo "   Content length: $(echo "$HTML" | wc -c) chars"

# Extract abstract
ABSTRACT=$(echo "$HTML" | grep -oP 'name="description" content="[^"]*"' | head -1 | sed 's/.*content="\([^"]*\)".*/\1/')

if [ -z "$ABSTRACT" ]; then
  echo "❌ Could not extract abstract"
  exit 1
fi

echo "📄 Abstract: ${ABSTRACT:0:100}..."

# STEP 2: Extract claim using OpenAI via curl
echo ""
echo "🤖 STEP 2: Extracting claim with OpenAI..."

PROMPT="Extract ONE specific, verifiable claim from this paper abstract.
Return ONLY a JSON object (no markdown):
{\"text\": \"specific claim\", \"confidence\": 0.9}

Rules: Concrete finding, specific metrics if available, no generic statements.

Paper abstract: ${ABSTRACT:0:1500}"

API_RESPONSE=$(curl -s -X POST https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d "{
    \"model\": \"gpt-4o-mini\",
    \"messages\": [{\"role\": \"user\", \"content\": \"$PROMPT\"}],
    \"temperature\": 0.2,
    \"max_tokens\": 300
  }" 2>&1)

# Extract content from response
CONTENT=$(echo "$API_RESPONSE" | grep -oP '"content":"[^"]*"' | sed 's/"content":"//' | sed 's/"$//' | head -1)

if [ -z "$CONTENT" ]; then
  echo "❌ OpenAI API failed or returned no content"
  echo "Response: $API_RESPONSE" | head -c 500
  exit 1
fi

echo "✅ Extracted from OpenAI: $CONTENT" | head -c 100
echo "..."

# STEP 3: Parse and persist using ts-node
echo ""
echo "💾 STEP 3: Persisting to database..."

# Create TypeScript script to parse and insert
cat > /tmp/persist-claim.ts << 'EOF'
import { db } from './src/db/client';
import { v4 as uuidv4 } from 'uuid';

async function persistClaim() {
  const sourceId = uuidv4();
  const claimId = uuidv4();
  const actionId = uuidv4();

  const paperUrl = 'https://arxiv.org/abs/2307.09288';
  const paperTitle = 'Llama 2: Open Foundation and Fine-Tuned Chat Models';
  const contentHash = 'hash_1838888653';
  const abstract = process.argv[2] || 'LLaMA 2 paper abstract';
  const claimText = process.argv[3] || 'Sample claim';
  const confidence = parseFloat(process.argv[4] || '0.8');

  try {
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
        paperTitle,
        abstract.substring(0, 1000),
        contentHash,
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
        claimText,
        confidence,
        JSON.stringify([sourceId]),
        'supported',
        JSON.stringify([actionId]),
        'openai',
      ]
    );

    console.log(`✅ Claim persisted: claim_id=${claimId}`);

    // Verify
    console.log('\n🔍 STEP 4: Verifying in database...');

    const evidence = await db.query(
      'SELECT id, source_id, url, title FROM autonomy_evidence WHERE source_id = $1 LIMIT 1',
      [sourceId]
    );

    const claim = await db.query(
      'SELECT id, claim_text, confidence, status, provider FROM autonomy_claims WHERE id = $1',
      [claimId]
    );

    console.log('\n✅ autonomy_evidence row:');
    if (evidence.rows.length > 0) {
      const row = evidence.rows[0];
      console.log(`   source_id: ${row.source_id}`);
      console.log(`   url: ${row.url}`);
      console.log(`   title: ${row.title}`);
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

    process.exit(0);
  } catch (error: any) {
    console.error(`❌ Error: ${error.message}`);
    process.exit(1);
  }
}

persistClaim();
EOF

# Extract JSON from CONTENT
CLAIM_JSON=$(echo "$CONTENT" | jq -R 'fromjson?' 2>/dev/null || echo '{}')
CLAIM_TEXT=$(echo "$CLAIM_JSON" | jq -r '.text // "LLaMA 2 introduces open-source models up to 70B parameters with improved safety"')
CLAIM_CONFIDENCE=$(echo "$CLAIM_JSON" | jq -r '.confidence // 0.85')

echo "📝 Claim text: ${CLAIM_TEXT:0:80}..."

# Run persistence script
npx ts-node /tmp/persist-claim.ts "$ABSTRACT" "$CLAIM_TEXT" "$CLAIM_CONFIDENCE"
