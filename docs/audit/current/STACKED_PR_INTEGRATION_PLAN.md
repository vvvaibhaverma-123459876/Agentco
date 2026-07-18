# Stacked PR Integration Plan

## Current Topology

- PR #27: open, unmerged, not draft, currently reported `DIRTY` by GitHub.
- PR #28: open, draft, unmerged, base
  `audit/remediation-07-cross-version-civilization-evaluation`, merge state
  `CLEAN`.
- PR #28 tip: `89af203e24b6a9e4f5c1636cf5d5bd0c5513ba81`.

## Inherited Contracts From PR #27

PR #28 depends on Batch 07 evidence-integrity and audit infrastructure,
including:

- cross-version evidence classification conventions,
- hosted-staging blocked classification,
- longitudinal evidence separation,
- audit-current documentation layout,
- release, clean-room, runtime-integration and staging gate preservation,
- score-validation and forensic-ledger gates.

## PR #28 Dependent Changes

PR #28 adds:

- `agentco-capability-v1` runtime code,
- capability request/response schemas,
- backend capability routes and route-auth contracts,
- provider adapters and trust-boundary controls,
- protocol/capability benchmark directories,
- V5 freeze candidate, manifest and binding,
- Protocol V3 and Genesis V5 campaign logic.

## Merge Order

Recommended order remains:

1. finish and independently approve PR #27;
2. merge PR #27;
3. rebase or retarget PR #28;
4. regenerate candidate freeze, manifest and binding;
5. rerun Protocol V3 and Genesis V5 governed HOLD;
6. rerun release, clean-room, runtime, staging and capability-runtime workflows;
7. only then move PR #28 from draft to ready for review.

## Rebase/Retarget Impact

PR #28 can be rebased or retargeted only after PR #27 lands. Any rebase,
merge-base change or conflict resolution invalidates the current V5 freeze
binding because the final source tree and workflow head change. Required
regeneration:

- freeze candidate commit,
- freeze manifest commit,
- freeze binding commit,
- Protocol V3 artifact,
- Genesis V5 HOLD artifact,
- release/clean-room/runtime/staging/capability workflow evidence.

Expected conflict areas after PR #27 merges:

- `docs/audit/current/**`
- forensic ledgers
- score-validation reports
- workflow definitions
- Makefile audit targets

PR #28 should remain draft until this regeneration is complete.
