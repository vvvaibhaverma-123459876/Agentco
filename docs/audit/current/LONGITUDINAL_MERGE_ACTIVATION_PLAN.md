# Longitudinal Merge Activation Plan

Generated for Batch 06A.

## Repository State

- Current `main` SHA: `2d1eff732c1b14bea09eee5b7c41979be41a1372`
- Batch 06 base SHA: `db538c6a00d0e7e8464fbaa79801473270d8388a`
- Working branch: `audit/remediation-06a-longitudinal-remote-closure`
- Branch ancestry: Batch 06A is based on Batch 06, which is based on Batch 05, which is based on Batch 04.
- Batch 04 PR #24: merged.
- Batch 05 PR: not found in the current PR list.
- Batch 06 PR: not found in the current PR list.
- Other open PRs: PR #19 (`feature/phase-calibration-transfer`) and PR #15 draft are unrelated to the audit/remediation branch lineage.

## Merge Order

The cleanest logical order remains:

1. Batch 05 hosted-staging fail-closed controls.
2. Batch 06 longitudinal mission-evidence foundation.
3. Batch 06A longitudinal remote-closure controls.

Because Batch 05 and Batch 06 do not currently have open PRs and are ancestors of this branch, the Batch 06A PR to `main` is expected to be cumulative. The PR body must state that it includes Batch 05, Batch 06, and Batch 06A changes.

## Workflow Activation

Expected pull-request workflows:

- CI
- Clean-Room Audit
- Runtime Integration Audit
- Staging Deployment Audit
- Longitudinal Evidence protocol validation

The `Longitudinal Evidence` scheduled and manual full-campaign paths are not considered activated until the workflow file is merged to the default branch. Pull-request execution validates protocol, benchmark governance, manifest integrity, calendar policy, and workflow contract only.

## Pull Request Policy

No pull request was merged automatically during this batch. Existing ancestor and unrelated PRs were not retargeted, closed, or modified.

## Evidence Status

Hosted staging remains blocked. Cross-version evidence is not executed in this batch. Four-week and twelve-week milestones remain time-blocked.
