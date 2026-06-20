# Institution Kernel

The Institution Kernel is the current civilization-side substrate. It models Institution -> Department -> Agent membership and enforces bounded review, governance, memory, and reputation behavior.

## Current Invariants

- Institutions are created with the five mandatory departments: Production, Verification, Audit, Adversarial, and Improvement.
- Contracts must define inputs, outputs, external reviewer, failure conditions, escalation target, and reputation metric.
- Duplicate active institutions are rejected by the creation service when the duplicate detector is enabled.
- Institution creation budget is enforced from `civilization/controls.yaml`.
- Review self-certification is rejected.
- Review status transitions are finite-state and illegal transitions fail closed.
- Challenges write `challenge_opened`; challenged reviews resolved as approved or rejected write `challenge_resolved`.
- Membership roles are validated.
- Expired or evicted members are excluded from active membership and reputation propagation.
- Reputation score writes are guarded by the DB trigger and must go through propagation.

## Boundary

This is not yet a production Society or Civilization layer. Jurisdiction, judiciary, economy, constitutional governance, and lifecycle evolution remain future phases.
