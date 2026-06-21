# Civilization / Institution Kernel

## Implemented

- The durable, tested core is an institution kernel centered on Institution -> Department -> Agent.
- Review transitions support `proposed -> under_review -> challenged|approved|rejected`, `challenged -> approved|rejected`, and terminal archival transitions.
- Current `review_service.py` writes `challenge_opened`, `challenge_resolved`, `review_completed`, and `failure_recorded` events for the relevant transitions.
- Controls are configured in `civilization/controls.yaml`.
- `reserve/migrations/018_institution_kernel_hardening.sql` expands membership lifecycle columns and memory event types.
- `civilization/services/membership_service.py` supports add, expire, evict, and active membership listing with memory events.
- `civilization/services/review_timeout_service.py` escalates timed-out reviews without auto-approval.
- `civilization/services/reputation_floor_service.py` suspends institutions/departments below the configured reputation floor without deleting them.

## Tested

- Existing tests cover migration, review/reputation behavior, governance, and institution kernel hardening.
- New lifecycle tests cover membership expiry/eviction memory events, review timeout escalation without auto-approval, and reputation floor suspension.

Run:

```bash
python3 -m pytest tests/civilization/test_institution_kernel_lifecycle_services.py
```

## Not Implemented

- This pass did not add full Society or Civilization production semantics.
- Institution creation budget enforcement still needs a service/API path.
- Department governance remains future work.
- Emergency shutdown enforcement remains partial.
- Review timeout and reputation floor services need scheduled deployment wiring.

## Future Work

- Enforce controls through services and DB constraints where practical.
- Keep documentation aligned with actual DB event types.
- Avoid claiming production-grade civilization until constitution, jurisdiction, dispute resolution, economy/resource allocation, and cross-society governance are implemented and tested end to end.
