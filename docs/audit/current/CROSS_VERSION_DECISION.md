# Cross-Version Decision

Decision: `INVALID_COMPARISON`

The prior `PROMOTION_PROPOSAL` for Version C is withdrawn. It is not valid
promotion evidence.

## Invalidation

The Batch 07 campaign `cross-version-civilization-v1` generated subject outputs
inside the evaluator with deterministic subject-specific rules. That means the
reported A/B/C capability deltas were not behavioral evidence from immutable
AgentCo subject processes.

Invalidated artifact IDs: `8314475888`, `8314717239`.

## Preserved Prior Rationale

The invalidated prior rationale is preserved for audit history:

- Version B was preserved as raw candidate.
- Version C resolved migration identity ambiguity.
- The invalid synthetic campaign reported A versus C and B versus C gains.

Those statements no longer support promotion.

## Required Replacement

Run `real-cross-version-civilization-v1` with subject-native process execution,
runtime-origin evidence, blinded labels, and no subject-specific answer
generation.
