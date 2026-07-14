# Longitudinal History Storage Contract

Batch 06A uses GitHub Actions artifacts only as workflow evidence storage. This is not hosted AgentCo runtime evidence.

Each manual or scheduled campaign produces a compact aggregate history containing:

- campaign series
- observation windows
- execution attempts
- failed attempts
- successful attempts
- previous aggregate hash
- current aggregate hash
- benchmark versions
- evaluator versions
- evaluated commits
- milestone eligibility

The first aggregate is a genesis record. Later aggregates must include the full compact chain, link to the prior aggregate hash, and preserve failed attempts. A missing or expired prior artifact is recorded as a continuity gap; it is not treated as a passing observation.

Scheduled observation IDs use:

`weekly-foundation-v1-YYYY-Www-<commit12>`

Manual observation IDs use:

`manual-YYYYMMDDTHHMMSSZ-<commit12>-<github_run_id>`

Attempt IDs use:

`<observation_id>-attempt-<github_run_attempt>`

Manual attempts never advance calendar milestones. Multiple successful scheduled attempts in the same UTC ISO week fail validation rather than inflating milestone counts.
