# Threat Model

## Protected Assets

- Calibration ledger integrity.
- Independent resolution boundary.
- Proof-of-Calibration credential correctness.
- Institution authority and reputation.
- Mutation audit trail.

## Primary Threats

- Agent self-resolution or self-certification.
- Resolver issuing credentials.
- Reserve issuer mutating source ledger rows.
- Auditor mutating governed state.
- Admin bypassing calibration by directly resolving scoring claims.
- Production deployment with dev-default secrets.

## Current Mitigations

- Scoped role middleware on governed mutation routes.
- Resolver self-claim check on claim resolution.
- Production secret guard.
- Privileged rejection audit events.
- Calibration independence engine from Phase 1.

## Remaining Work

- Durable RBAC policy storage.
- Key rotation implementation beyond hooks/stubs.
- Infrastructure rate limiting.
- Full service identity issuance and revocation.
