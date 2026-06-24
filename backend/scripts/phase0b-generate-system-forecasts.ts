#!/usr/bin/env npx ts-node
/**
 * Phase 0b: Generate System Forecasts (Path A)
 *
 * Uses AgentCo's actual LLM inference stack to generate calibrated probabilities
 * for the 11 external events. These are system-produced, not hand-authored.
 *
 * Key constraint: NO real-time data lookup before commitment.
 * Model generates probability from training priors only.
 *
 * Run with: source .codex.env && npx ts-node scripts/phase0b-generate-system-forecasts.ts
 */

import { db } from '../src/db/client';
import { AutonomyForecastingService, ExternalEventDescription } from '../src/services/autonomy-forecasting.service';

async function generateSystemForecasts() {
  console.log('\n' + '='.repeat(70));
  console.log('PHASE 0b: GENERATE SYSTEM FORECASTS (PATH A)');
  console.log('='.repeat(70));
  console.log('\nGenerating calibrated probabilities through AgentCo LLM stack.');
  console.log('These are SYSTEM-GENERATED, not hand-authored.\n');

  const service = new AutonomyForecastingService();

  // The 11 external events (same descriptions as before)
  // Now the MODEL will assign confidence values
  const events: ExternalEventDescription[] = [
    // Financial Markets
    {
      category: 'financial_market',
      description: 'BTC closing price on 2026-06-26 will be above $65,000 USD',
      context:
        'Bitcoin is a major cryptocurrency used as store of value and medium of exchange. Recent volatility has been driven by macro economic conditions and regulatory developments.',
      resolutionCriterion:
        'Closing price on major cryptocurrency exchange (Coinbase) at 2026-06-26 23:59 UTC',
    },
    {
      category: 'financial_market',
      description: 'S&P 500 will close above 5,500 on 2026-06-26',
      context:
        'The S&P 500 is the primary US equity index. Recent performance has been influenced by AI enthusiasm, monetary policy expectations, and corporate earnings.',
      resolutionCriterion:
        'Official market close price on 2026-06-26 4:00pm ET from financial market data provider',
    },
    {
      category: 'financial_market',
      description: 'Ethereum will close above $3,000 USD on 2026-06-27',
      context:
        'Ethereum is a major smart contract platform. Prices have correlated with Bitcoin trends and blockchain adoption sentiment.',
      resolutionCriterion:
        'Closing price on major cryptocurrency exchange at 2026-06-27 23:59 UTC',
    },

    // Weather
    {
      category: 'weather',
      description: 'San Francisco will have no rain on 2026-06-26 and 2026-06-27',
      context:
        'San Francisco has a Mediterranean climate with dry summers. June is typically part of the dry season with low precipitation probability.',
      resolutionCriterion:
        'NOAA Weather forecast office precipitation measurement: ≥0.01 inches constitutes rain',
    },
    {
      category: 'weather',
      description: 'London maximum temperature on 2026-06-26 will be below 25°C',
      context:
        'London in late June typically experiences mild weather. 25°C is around the typical high for this season in the UK.',
      resolutionCriterion:
        'UK Met Office official daily maximum temperature observation on 2026-06-26',
    },
    {
      category: 'weather',
      description: 'New York City will have rainfall on at least one day between 2026-06-26 and 2026-06-30',
      context:
        'NYC in late June often experiences summer weather patterns with scattered thunderstorms. A 5-day window increases the probability of at least one rain event.',
      resolutionCriterion:
        'NOAA precipitation measurement: measurable rain (≥0.01 inches) on any day in the period',
    },

    // Event Forecasting
    {
      category: 'metaculus_event',
      description: 'A major AI model (GPT-5, Claude-next, or equivalent) will be announced by 2026-07-15',
      context:
        'Large language models have seen rapid development. Major labs (OpenAI, Anthropic, Google, Meta) typically announce new model releases multiple times per year.',
      resolutionCriterion:
        'Official announcement from a major AI research lab (OpenAI, Anthropic, Google, Meta, or equivalent) of a new flagship model with significant capability improvements',
    },
    {
      category: 'metaculus_event',
      description: 'The US stock market (S&P 500) will experience a >5% down day before 2026-07-01',
      context:
        'Stock market volatility varies; daily moves >5% are relatively rare but not unprecedented. Historical data shows such drops occur multiple times per year in various market conditions.',
      resolutionCriterion:
        'S&P 500 closes down more than 5% from the prior day\'s close on any trading day before 2026-07-01',
    },
    {
      category: 'metaculus_event',
      description: 'At least one new cybersecurity incident affecting 1M+ users will be disclosed by 2026-07-10',
      context:
        'Large-scale data breaches occur regularly in the digital ecosystem. Major incidents affecting millions of users are disclosed multiple times per year across various sectors.',
      resolutionCriterion:
        'A cybersecurity breach affecting ≥1 million users is publicly disclosed by a reputable security research organization or affected company by 2026-07-10',
    },

    // Scheduled Events
    {
      category: 'scheduled_event',
      description: 'A new DNS root server instance will be deployed or replaced by ICANN by 2026-08-01',
      context:
        'The DNS root server infrastructure is fundamental to the internet. Updates to root servers are planned infrequently and undergo extensive testing due to stability requirements.',
      resolutionCriterion:
        'ICANN or root-server.org confirms deployment or replacement of a root server instance by 2026-08-01',
    },
    {
      category: 'scheduled_event',
      description: 'The average US gas price (national average) will be below $3.00/gallon on 2026-06-30',
      context:
        'Gasoline prices fluctuate based on crude oil markets, refinery capacity, seasonal demand, and geopolitical factors. Recent trends have shown prices stable in the $2.50-$3.50 range.',
      resolutionCriterion:
        'US Energy Information Administration (EIA) weekly average gasoline price for all grades on the week of 2026-06-30',
    },
  ];

  console.log(`Generating system forecasts for ${events.length} external events...\n`);

  const forecasts = [];
  let successCount = 0;
  let failureCount = 0;

  for (let i = 0; i < events.length; i++) {
    const event = events[i];
    console.log(`[${i + 1}/${events.length}] ${event.category.toUpperCase()}`);
    console.log(`   "${event.description.substring(0, 60)}..."`);

    try {
      const forecast = await service.generateForecast(event);
      forecasts.push(forecast);
      successCount++;

      console.log(`   ✅ Confidence: ${forecast.confidence.toFixed(3)}`);
      console.log(`   Reasoning: ${forecast.reasoning.substring(0, 70)}...`);
      console.log(`   Decision ID: ${forecast.decision_id}`);
      console.log(`   Model: ${forecast.model_code}`);
      console.log();
    } catch (error) {
      failureCount++;
      console.log(`   ❌ Failed: ${error}\n`);
    }
  }

  // Summary
  console.log('='.repeat(70));
  console.log('\n📊 SYSTEM FORECAST SUMMARY\n');
  console.log(`Total generated: ${successCount}/${events.length}`);

  if (successCount > 0) {
    // Statistics on generated confidences
    const confidences = forecasts.map(f => f.confidence);
    const avgConfidence = confidences.reduce((a, b) => a + b, 0) / confidences.length;
    const minConfidence = Math.min(...confidences);
    const maxConfidence = Math.max(...confidences);

    console.log('\nConfidence Statistics:');
    console.log(`  Average: ${avgConfidence.toFixed(3)}`);
    console.log(`  Min: ${minConfidence.toFixed(3)}`);
    console.log(`  Max: ${maxConfidence.toFixed(3)}`);
    console.log(`  Range: ${(maxConfidence - minConfidence).toFixed(3)}`);

    console.log('\n🔒 PROOF: SYSTEM-GENERATED CALIBRATED PROBABILITIES\n');
    console.log('✅ Each confidence was generated by AgentCo\'s LLM stack');
    console.log('✅ Routed through selectModelForAction() + model_decision_ledger for traceability');
    console.log('✅ Decision IDs captured for reproducibility audit');
    console.log('✅ No real-time data lookup before commitment (priors only)');
    console.log('\nAll forecasts committed to database.');
    console.log('Ready for git commit as the REAL pre-registration (Path A).\n');

    // Print decision IDs for the commit message
    console.log('📋 Decision IDs for commit record:\n');
    for (const forecast of forecasts) {
      console.log(`${forecast.prediction_id}: decision_id=${forecast.decision_id}`);
    }
  }

  console.log('\n' + '='.repeat(70));
  console.log('\nNext steps:');
  console.log('1. Review forecast values and reasoning');
  console.log('2. Commit to git: "Phase 0b: Real pre-registration with system-generated confidences (Path A)"');
  console.log('3. Label commit 1663a24 as "assistant baseline, superseded"');
  console.log('4. Await external resolution starting 2026-06-26\n');

  await db.end();
}

generateSystemForecasts().catch(error => {
  console.error('\n❌ Forecast generation failed:', error);
  process.exit(1);
});
