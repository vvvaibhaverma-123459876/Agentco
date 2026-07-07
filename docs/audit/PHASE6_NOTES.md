# Phase 6 Notes — V1 Retirement and Post-Merge Verification

## Task 1 — Chain Seam Verification

Verdict: full-chain verification recomputes historical `decision_log` entry hashes, and versioned verification was needed for the Phase 5 canonicalization seam.

What the verifier does:

- `backend/src/services/audit-log.service.ts::verifyChainIntegrity()` selects all rows with 64-character hex `chain_hash` and `prev_hash`.
- It walks oldest to newest (`ORDER BY timestamp ASC, log_id ASC`).
- It recomputes each row hash as `SHA-256(prev_hash || serialized_row_content)` and compares it with the stored `chain_hash`.

Phase 5 already accepted two serialization buckets:

- `v2.sorted-json`: sorted-key compact JSON, the current TypeScript/Python writer contract.
- `v1.ts-insertion-json`: TypeScript `JSON.stringify(fields)` insertion order, the pre-Phase-5 TypeScript writer contract.

Phase 6 added the missing legacy Python bucket:

- `v1.python-insertion-json`: Python insertion-order compact JSON with the original `datetime.now(timezone.utc).isoformat()` timestamp shape.

Implementation note: the verifier now selects `timestamp::text AS timestamp_text`. That preserves Postgres microseconds, which JavaScript `Date` would otherwise truncate to milliseconds. The Python legacy timestamp is reconstructed from Postgres text before hashing.

Verification:

```text
npm test -- audit-chain-cross-writer.test.ts --runInBand
PASS tests/audit-chain-cross-writer.test.ts
  ✓ verifier accepts legacy Python insertion-order rows across the canonicalization seam
  ✓ TS -> Python -> TS entries verify as one chain
```

Full local chain probe:

```json
{
  "span": {
    "count": 2790,
    "min_ts": "2026-07-05 10:28:35.455+05:30",
    "max_ts": "2026-07-07 09:12:54.679+05:30"
  },
  "verification": {
    "valid": true
  }
}
```
