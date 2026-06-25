/**
 * Learning enforcement — the deterministic core that CLOSES the learning loop.
 *
 * Background (experiment, 2026-06-25): the reflection mechanism stores + retrieves + feeds a
 * lesson to the planner, but gpt-4o-mini IGNORES it (it repeated the exact `spawn_specialist`
 * action a reflection flagged). Prompting is insufficient, so the orchestrator derives the
 * flagged action types from reflections and FORBIDS them — overriding the planner. This tests
 * that derivation deterministically (no LLM), which is the part that makes a lesson change behaviour.
 */
import { describe, it, expect } from '@jest/globals';
import { avoidedActionTypesFromReflections, Reflection } from '../src/services/reflection.service';

function reflection(over: Partial<Reflection>): Reflection {
  return {
    id: 'r1', goalId: 'g1', summary: '', loopType: 'identical_action_repeat',
    failurePattern: 'spawn_specialist was repeated 3 times with args: {}',
    suggestedStrategy: 'TRY evaluate_progress', confidence: 0.9, createdAt: new Date(), ...over,
  };
}

describe('avoidedActionTypesFromReflections', () => {
  it('forbids the action type a repeat-loop reflection flagged', () => {
    const s = avoidedActionTypesFromReflections([reflection({})]);
    expect(s.has('spawn_specialist')).toBe(true);
  });

  it('parses the action type from different failure patterns', () => {
    const s = avoidedActionTypesFromReflections([
      reflection({ failurePattern: 'web_search was repeated 4 times with args: {"query":"x"}' }),
      reflection({ id: 'r2', failurePattern: 'fetch_page was repeated 3 times with args: {}' }),
    ]);
    expect(s.has('web_search')).toBe(true);
    expect(s.has('fetch_page')).toBe(true);
  });

  it('does NOT forbid actions from non-repeat reflections (e.g. no_progress_streak)', () => {
    const s = avoidedActionTypesFromReflections([
      reflection({ loopType: 'no_progress_streak', failurePattern: 'no progress for 5 actions' }),
    ]);
    expect(s.size).toBe(0);
  });

  it('returns an empty set for no reflections (nothing learned yet => nothing forbidden)', () => {
    expect(avoidedActionTypesFromReflections([]).size).toBe(0);
  });

  it('aggregates multiple distinct flagged actions', () => {
    const s = avoidedActionTypesFromReflections([
      reflection({ failurePattern: 'spawn_specialist was repeated 3 times' }),
      reflection({ id: 'r2', failurePattern: 'generate_claim was repeated 3 times' }),
    ]);
    expect([...s].sort()).toEqual(['generate_claim', 'spawn_specialist']);
  });
});
