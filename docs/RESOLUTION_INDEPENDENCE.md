# Resolution Independence

## Implemented

- `calibration/resolution/independence_engine.py` creates source fingerprints for claim and resolution sources.
- The engine checks canonical URL equality, normalized domain equality, exact content hash equality, publisher owner equality, resolver identity, resolver type, producer/resolver conflict, and internal/self/simulation source markers.
- `ResolutionService.resolve()` accepts `resolver_id`, `resolver_type`, `claim_source_url`, `resolution_url`, and evidence metadata.
- `ResolutionService.resolve()` also accepts claim/resolution source content and derives SHA-256 content hashes when supplied.
- Production mode rejects missing resolver identity.
- Resolution records carry an independence verdict and evidence snapshot hash.
- `backend/src/db/migrations/017_resolution_evidence_snapshots.sql` adds append-only durable evidence snapshots.
- `PredictionLedger.persist_resolution()` requires a snapshot and persists snapshot plus resolution update in one transaction.

## Tested

- Same canonical URL rejection.
- Tracking parameter canonicalization.
- Same content hash rejection.
- Same-domain warning.
- Internal source rejection.
- Resolver equals producer rejection.
- Missing resolver identity rejection in production mode.
- Deterministic evidence snapshot hashing.
- Resolution service attaches verdict and snapshot metadata.
- Postgres migration creates `resolution_evidence_snapshots`.
- Snapshot rows are inserted and linked by `prediction_id`.
- Snapshot rows cannot be updated or deleted.
- Resolution fails and rolls back if snapshot insertion fails.
- Snapshot evidence survives reload.

Run:

```bash
python3 -m pytest tests/test_resolution_independence_engine.py tests/integration/test_resolution_evidence_snapshots.py
```

## Not Implemented

- Fuzzy duplicate content detection beyond exact content hash.
- Automated publisher ownership registry.
- Full dispute adjudication workflow over snapshots.
- Resolver key identity and rotation.

## Future Work

- Add resolver service identities with scoped keys.
- Require secondary independent evidence for same-owner warnings in high-risk domains.
- Add Postgres integration coverage for evidence snapshot persistence.
