# Institution Kernel Hardening Status

Phase 2 hardens the bounded Institution Kernel without claiming a completed Society or Civilization layer.

## Implemented In Phase 2

- Duplicate active institution creation blocked in the creation service.
- Institution creation budget enforced from controls.
- Membership expiry and eviction fields added to the civilization migration.
- Role validation added for membership writes.
- Active membership listing excludes expired and evicted members.
- Reputation propagation excludes expired and evicted members.
- Review timeout escalation records failure memory.
- `challenge_resolved` memory event path fixed for challenged reviews resolved to approved or rejected.
- Cross-institution reputation view added.

## Remaining Risks

- Reputation floor currently remains a policy/control value; automatic probation or suspension is not fully implemented.
- Department-level governance is still represented by memory/governance primitives, not a dedicated department governance table.
- Durable production API boundaries arrive in a later phase.
