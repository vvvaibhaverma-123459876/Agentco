# Production Readiness Module 8: Evidence-Derived Orchestrator Metrics

Date: 2026-06-26

## Verdict

Completed for the orchestrator calibration/trust input slice.

This module removes fixed orchestration constants previously used as evidence quality, source reliability, and calibration error inputs. The orchestrator now computes those values from retrieved evidence and answer agreement.

## Changes

- Bayesian fusion now receives evidence quality derived from source relevance, provenance completeness, and source diversity.
- Bayesian fusion now receives source reliability derived from source type and HTTPS provenance.
- Trust scoring now receives calibration error from confidence shift between primary and evidence-adjusted confidence.
- Trust scoring now receives consistency from answer agreement and evidence agreement ratio.
- Trust scoring now receives explainability from actual reasoning/evidence strings.
- Empty evidence degrades metrics rather than implying strong trust inputs.

## Verification

Commands run:

```bash
cd backend && npx tsc --noEmit
cd backend && npm test -- tests/orchestrator-real-metrics.test.ts --runInBand --forceExit
```

Results:

- TypeScript compile: passed.
- Orchestrator metric tests: 2 passed.

## Remaining Scope

The orchestrator still depends on the quality of upstream ensemble/RAG outputs. This module makes the trust inputs evidence-derived; it does not certify that every upstream answer source is production-grade.
