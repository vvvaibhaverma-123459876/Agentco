/**
 * Planner Claim Bias (planner-strategy fix)
 * =========================================
 * When the loop has fetched evidence but has not yet produced a grounded
 * claim, the planner must drive extract_evidence/generate_claim from that
 * evidence — not spawn more specialists. In the full live run the planner
 * gathered real arxiv/github evidence but minted 0 claims because the decision
 * prompt pushed it toward spawn_specialist.
 */

import { describe, expect, test } from '@jest/globals';
import { AutonomyActionPlannerService } from '../src/services/autonomy-action-planner.service';

const evidenceSources = [
  { sourceId: 'src-arxiv-1', url: 'https://arxiv.org/list/cs.AI/recent', snippet: 'Recent papers on autonomous agents and planning under uncertainty.' },
  { sourceId: 'src-gh-1', url: 'https://github.com/trending', snippet: 'Trending agent frameworks this week.' },
];

describe('planner claim bias', () => {
  test('with fetched evidence and zero claims, the prompt drives claim generation, not specialists', () => {
    const planner = new AutonomyActionPlannerService();
    const prompt = planner.buildDecisionPrompt({
      goalText: 'Research recent advances in AI agent autonomy',
      claimsGenerated: 0,
      evidenceCount: 2,
      evidenceSources,
      loopDetection: { isLooping: false } as any,
      previousActions: [],
    });

    // Strong directive to generate a grounded claim from the available sources.
    expect(prompt).toMatch(/generate_claim/i);
    expect(prompt).toContain('src-arxiv-1'); // a concrete source id it can cite
    expect(prompt.toLowerCase()).toMatch(/generate.*grounded claim|create a grounded claim|produce.*claim now/);

    // The specialist-opportunity block must NOT appear before any claim exists.
    expect(prompt).not.toContain('SPECIALIST OPPORTUNITY');
  });

  test('once at least one claim exists, delegation guidance returns', () => {
    const planner = new AutonomyActionPlannerService();
    const prompt = planner.buildDecisionPrompt({
      goalText: 'Research recent advances in AI agent autonomy',
      claimsGenerated: 2,
      evidenceCount: 3,
      evidenceSources,
      loopDetection: { isLooping: false } as any,
      previousActions: [],
    });
    // With claims already made, the specialist opportunity may reappear.
    expect(prompt).toContain('SPECIALIST OPPORTUNITY');
  });
});
