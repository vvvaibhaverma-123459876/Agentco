# Remediation 06A: Longitudinal Remote Closure

## Scope

Batch 06A closes remote-execution and workflow-integrity gaps in the Batch 06 longitudinal mission-evidence foundation. It does not start the cross-version improvement campaign and does not upgrade hosted staging, production, four-week, or twelve-week evidence.

## Batch 06 Base

- Batch 06 final commit: `db538c6a00d0e7e8464fbaa79801473270d8388a`
- Batch 06A final commit: the commit containing this report. The exact immutable SHA is recorded in the final execution response and pull-request metadata after commit creation.
- Working branch: `audit/remediation-06a-longitudinal-remote-closure`

## Remote Execution Gaps Found

1. The longitudinal workflow could run from a pull-request merge SHA rather than the exact PR branch head.
2. Pull-request validation and full campaign execution were not clearly separated.
3. The workflow used the general requirements file instead of the governed lockfile.
4. The manual workflow input exposed the fixed `initial-foundation-v1` campaign ID.
5. Scheduled/manual observations lacked a distinct series, observation, and attempt contract.
6. Aggregate historical evidence relied on ephemeral workflow runs without an explicit append-only chain.
7. Calendar milestones could not yet prove fail-closed handling of duplicate weeks, manual runs, backdated timestamps, or missing failed attempts.

## Corrections

- `.github/workflows/longitudinal-evidence.yml` now checks out `${{ github.event.pull_request.head.sha || github.sha }}` with full history and records `EXPECTED_AUDIT_SHA`.
- Pull-request execution runs protocol validation, benchmark governance, evidence-integrity tests, and foundation snapshot validation only.
- Manual and scheduled executions generate bounded campaign observation IDs and run the full campaign only when the workflow is active on the default branch.
- Python dependencies install from `requirements/requirements.lock.txt`.
- The fixed recurring campaign ID was removed from workflow inputs. `initial-foundation-v1` remains only as the Batch 06 foundation campaign.
- `scripts/verify_longitudinal_evidence.py` validates exact commit binding, clean working tree status, benchmark hash, evaluator version, output hashes, provider classification, and hosted/production claim boundaries.
- `scripts/aggregate_longitudinal_history.py` records scheduled/manual attempts into an append-only aggregate history with failed-attempt retention and aggregate-chain hashing.
- `scripts/calculate_longitudinal_milestones.py` calculates milestone eligibility from immutable observation history. Manual runs and same-week reruns cannot advance calendar milestones.
- `schemas/longitudinal_history.schema.json` documents the aggregate history contract.

## Observation Contract

- Campaign series: `weekly-foundation-v1`
- Scheduled observation ID: `weekly-foundation-v1-YYYY-Www-<commit12>`
- Manual observation ID: `manual-YYYYMMDDTHHMMSSZ-<commit12>-<github_run_id>`
- Attempt ID: `<observation_id>-attempt-<github_run_attempt>`

Unsuccessful attempts are preserved. A successful retry may add a later successful attempt, but it does not delete the failed attempt or create an additional calendar week.

## Aggregate History Contract

The aggregate history records:

- campaign series,
- previous aggregate hash,
- current aggregate hash,
- observation windows,
- all attempts,
- failed attempts,
- successful attempts,
- missing windows,
- benchmark versions,
- evaluator versions,
- commits,
- calendar span,
- milestone eligibility.

The first valid aggregate is an explicit genesis record. Historical observations before workflow activation are rejected.

## Negative Tests

The remote-closure regression suite verifies fail-closed behaviour for:

- PR merge SHA recorded instead of branch-head SHA,
- manifest evidence from another commit,
- fixed campaign ID reuse for scheduled observations,
- duplicate successful scheduled observations in the same ISO week,
- failed attempt omission,
- manual run advancing the four-week milestone,
- same-day runs counted as multiple weeks,
- backdated observations,
- modified aggregate history,
- broken aggregate chain,
- silent benchmark hash changes,
- undisclosed evaluator-version changes,
- missing required evidence artifacts,
- artifact repository/workflow mismatch,
- dirty working tree evidence,
- hosted evidence claimed by deterministic local runs,
- production evidence claimed by GitHub-hosted runners,
- unmerged PR workflow claiming schedule activation,
- historical observations before workflow activation.

Focused local result before final commit: `45 passed`.

## Pull Request Topology

- Current `main`: `2d1eff732c1b14bea09eee5b7c41979be41a1372`
- Batch 04 PR #24 is merged.
- No Batch 05 or Batch 06 PR was found in the current PR list.
- Batch 06A PR is expected to be cumulative over Batch 05, Batch 06, and Batch 06A.
- No PR is merged automatically by this batch.

## Remaining Limitations

- Schedule activation remains pending default-branch merge.
- Cross-version evidence is not executed.
- Four-week and twelve-week evidence remain time-blocked.
- Hosted staging remains blocked because real cloud/provider prerequisites are unavailable in this local environment.
- GitHub Actions artifact IDs, digests, and workflow conclusions must be filled from the remote PR runs after the final branch commit is pushed.

## Rollback

Revert the final Batch 06A commit to restore the Batch 06 longitudinal workflow and scripts. This removes the new exact-SHA workflow verifier, aggregate history contract, calendar milestone calculator, and remote-closure tests without modifying frozen benchmark cases or hidden expectations.
