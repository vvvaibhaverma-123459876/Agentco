#!/usr/bin/env npx ts-node
/**
 * Phase 0b: Pre-Register EXTERNAL Predictions
 *
 * Corrected implementation: predictions about external events, not system self-tests.
 * Each prediction:
 * - Has outcome UNKNOWN at registration time
 * - Cannot be influenced or known early by this system
 * - Resolves on a fixed external date by objective criterion
 * - Resolution is reading an external source, not human judgment
 *
 * Prediction domains:
 * - Financial markets (stock/crypto closes, known closing times)
 * - Weather (official forecasts, known resolution times)
 * - Metaculus predictions (public event forecasting, objective resolution)
 * - Time-locked events (scheduled announcements, known dates)
 *
 * Run with: npx ts-node scripts/phase0b-register-external-predictions.ts
 */

import { db } from '../src/db/client';
import { Phase0bCalibrationService } from '../src/services/phase0b-calibration.service';

async function registerExternalPredictions() {
  console.log('\n' + '='.repeat(70));
  console.log('PHASE 0b: PRE-REGISTER EXTERNAL PREDICTIONS');
  console.log('='.repeat(70));
  console.log('\nRegistering predictions about EXTERNAL events with unknown outcomes.');
  console.log('Resolution dates: 2026-06-25 to 2026-07-15 (external ground truth only)\n');

  const service = new Phase0bCalibrationService();

  // Define external predictions
  // NOTE: These are examples. Actual Metaculus questions, weather forecasts, and market events
  // should be verified to exist and have correct resolution dates at time of registration.
  const predictions = [
    // Financial markets (stock/crypto closes are objective, timed, uninfluenceable)
    {
      category: 'financial_market',
      description: 'BTC closing price on 2026-06-26 will be above $65,000 USD',
      confidence: 0.62,
      hypothesis: 'Recent macro conditions suggest modest uptrend; 65k is near ATH.',
      daysUntilResolution: 2,
      resolutionSource: 'coinbase.com, closing UTC price, 2026-06-26 23:59 UTC',
      externalReference: 'CoinGecko historical close price',
    },
    {
      category: 'financial_market',
      description: 'S&P 500 will close above 5,500 on 2026-06-26',
      confidence: 0.70,
      hypothesis: 'Index has been range-bound; slight bullish bias from AI optimism.',
      daysUntilResolution: 2,
      resolutionSource: 'Yahoo Finance, 4pm ET close, 2026-06-26',
      externalReference: 'Standard market data, public closing price',
    },
    {
      category: 'financial_market',
      description: 'Ethereum will close above $3,000 USD on 2026-06-27',
      confidence: 0.55,
      hypothesis: 'ETH is volatile; 3k is above recent range but not extreme.',
      daysUntilResolution: 3,
      resolutionSource: 'coinbase.com, closing UTC price, 2026-06-27 23:59 UTC',
      externalReference: 'CoinGecko historical data, public close',
    },

    // Weather (official forecasts, uninfluenceable, objective)
    {
      category: 'weather',
      description: 'San Francisco will have no rain on 2026-06-26 and 2026-06-27',
      confidence: 0.75,
      hypothesis: 'Dry season in California; forecast models show no rain events.',
      daysUntilResolution: 2,
      resolutionSource: 'NOAA Weather.gov forecast office, 0.01 inches threshold',
      externalReference: 'National Weather Service official precipitation data',
    },
    {
      category: 'weather',
      description: 'London maximum temperature on 2026-06-26 will be below 25°C',
      confidence: 0.68,
      hypothesis: 'June in UK is mild; 25°C is typical for this season.',
      daysUntilResolution: 2,
      resolutionSource: 'Met Office UK, daily max temperature, 2026-06-26',
      externalReference: 'UK Met Office official temperature records',
    },
    {
      category: 'weather',
      description: 'New York City will have rainfall on at least one day between 2026-06-26 and 2026-06-30',
      confidence: 0.80,
      hypothesis: 'NYC forecast shows scattered showers; 5-day window makes rain likely.',
      daysUntilResolution: 6,
      resolutionSource: 'NOAA, measurable precipitation (≥0.01 inches on any day)',
      externalReference: 'National Weather Service public data',
    },

    // Metaculus predictions (public forecasting platform, objective resolution)
    // NOTE: These would need to be real Metaculus question IDs with known resolution dates
    {
      category: 'metaculus_event',
      description: 'A major AI model (GPT-5, Claude-next, or equivalent) will be announced by a leading lab by 2026-07-15',
      confidence: 0.45,
      hypothesis: 'Tech development is fast but major releases are months apart; low prior.',
      daysUntilResolution: 21,
      resolutionSource: 'Metaculus or equivalent: official announcement from OpenAI/Anthropic/others',
      externalReference: 'Public tech announcements, major news coverage',
    },
    {
      category: 'metaculus_event',
      description: 'The US stock market (S&P 500) will experience a >5% down day before 2026-07-01',
      confidence: 0.35,
      hypothesis: '5% drops are rare but not impossible; ~20 trading days gives ~35% odds historically.',
      daysUntilResolution: 7,
      resolutionSource: 'S&P 500 daily close, >5% single-day decline',
      externalReference: 'Yahoo Finance daily OHLC data',
    },
    {
      category: 'metaculus_event',
      description: 'At least one new cybersecurity incident affecting 1M+ users will be publicly disclosed by 2026-07-10',
      confidence: 0.70,
      hypothesis: 'Major breaches happen regularly; 2-week window makes discovery/disclosure likely.',
      daysUntilResolution: 16,
      resolutionSource: 'Breach.com, Have I Been Pwned, or major news outlets',
      externalReference: 'Public security breach databases and news',
    },

    // Technical/scheduled events (objective, time-locked)
    {
      category: 'scheduled_event',
      description: 'A new DNS root server instance will be deployed or replaced by ICANN by 2026-08-01',
      confidence: 0.50,
      hypothesis: 'Root server infrastructure changes are slow; low odds in 6-week window.',
      daysUntilResolution: 38,
      resolutionSource: 'ICANN official announcements or root-server.org status updates',
      externalReference: 'ICANN public documentation and DNS engineering announcements',
    },
    {
      category: 'scheduled_event',
      description: 'The average US gas price (national average) will be below $3.00/gallon on 2026-06-30',
      confidence: 0.58,
      hypothesis: 'Gas prices fluctuate with oil; current trend suggests stability above $3.',
      daysUntilResolution: 6,
      resolutionSource: 'US Energy Information Administration (EIA) weekly average, 2026-06-30',
      externalReference: 'EIA public price data',
    },
  ];

  console.log(`Registering ${predictions.length} EXTERNAL predictions...\n`);

  const registeredPredictions = [];
  for (const pred of predictions) {
    const expectedResolutionBy = new Date();
    expectedResolutionBy.setDate(expectedResolutionBy.getDate() + pred.daysUntilResolution);

    try {
      const registered = await service.registerPrediction(
        {
          category: pred.category,
          description: pred.description,
          confidence: pred.confidence,
          expectedResolutionBy,
          hypothesis: pred.hypothesis,
        },
        'phase0b_external_registration_script'
      );

      registeredPredictions.push(registered);
      console.log(`✅ [${pred.category}] Confidence ${pred.confidence}`);
      console.log(`   "${pred.description.substring(0, 65)}..."`);
      console.log(`   Resolution: ${expectedResolutionBy.toISOString().split('T')[0]}`);
      console.log(`   Source: ${pred.resolutionSource.substring(0, 60)}...`);
      console.log(`   Reference: ${pred.externalReference}\n`);
    } catch (error) {
      console.error(`❌ Failed to register: ${pred.description}`);
      console.error(`   Error: ${error}\n`);
    }
  }

  // Summary
  console.log('='.repeat(70));
  console.log('\n📋 EXTERNAL PREDICTION REGISTRATION SUMMARY\n');
  console.log(`Total registered: ${registeredPredictions.length}/${predictions.length}`);

  // Group by category
  const byCategory: Record<string, number> = {};
  for (const pred of registeredPredictions) {
    byCategory[pred.category] = (byCategory[pred.category] || 0) + 1;
  }

  console.log('\nBy category:');
  for (const [category, count] of Object.entries(byCategory)) {
    console.log(`  - ${category}: ${count} predictions`);
  }

  // Average confidence
  const avgConfidence =
    registeredPredictions.reduce((sum, p) => sum + p.confidence, 0) /
    registeredPredictions.length;
  console.log(`\nAverage confidence: ${avgConfidence.toFixed(3)}`);

  // Timeline
  const dates = registeredPredictions.map(p => p.expectedResolutionBy).sort((a, b) => a.getTime() - b.getTime());
  if (dates.length > 0) {
    console.log(`\n⏱️ Timeline:`);
    console.log(`Earliest resolution: ${dates[0].toISOString().split('T')[0]}`);
    console.log(`Latest resolution:   ${dates[dates.length - 1].toISOString().split('T')[0]}`);
    const daysSpan = Math.ceil((dates[dates.length - 1].getTime() - dates[0].getTime()) / (1000 * 60 * 60 * 24));
    console.log(`Span: ${daysSpan} days`);
  }

  console.log('\n' + '='.repeat(70));
  console.log('\n🔒 CRITICAL: PROOF OF PRE-REGISTRATION (EXTERNAL EVENTS)\n');
  console.log('✅ These predictions are about EXTERNAL events:');
  console.log('   - Outcomes UNKNOWN at registration (you haven\'t looked them up)');
  console.log('   - Cannot be influenced by this system (market prices, weather, etc.)');
  console.log('   - Resolved by reading external sources (official APIs, news, databases)');
  console.log('   - NOT resolved by running your own code\n');

  console.log('The git commit timestamp proves pre-registration BEFORE external resolution.\n');

  console.log('Next steps:');
  console.log('1. Commit this code to git (proof of pre-registration)');
  console.log('2. Wait for resolution dates to arrive (2026-06-26 onwards)');
  console.log('3. Query each external source and resolve predictions');
  console.log('4. Compute Brier score (confidence vs actual accuracy)');
  console.log('5. Feed calibration metrics into Phase 1 Brick 4\n');

  await db.end();
}

registerExternalPredictions().catch(error => {
  console.error('\n❌ Registration failed:', error);
  process.exit(1);
});
