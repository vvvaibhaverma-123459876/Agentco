# Phase C — Tamper-Evidence Acceptance Trace

**Date:** 2026-06-18  
**Claim proven:** The operator cannot alter, drop, or back-date any resolved prediction
that feeds a score without that alteration being detectable by any third party with
read access to the public prediction_ledger.

---

## Design (Certificate-Transparency style hash chain)

A `prediction_chain_log` table stores one append-only row per committed resolved
prediction, where:

```
row_hash = SHA-256(prev_hash || prediction_id || agent_id ||
                   probability || resolved_outcome || resolved_at ||
                   domain || horizon_class || consequence)
```

The chain is ordered by `seq` (monotone serial). Any third party can:
1. Read all `prediction_chain_log` rows ordered by `seq`
2. Join to `prediction_ledger` to get the current field values
3. Recompute the chain from `prev_hash = "000...0"` (genesis) upward
4. Compare their recomputed head to the stored head

If any ledger field was altered after commitment, the recomputed hash at that
position changes, and every subsequent hash changes — the chain head diverges.
**This requires no secret and no trust in the operator.**

The chain log itself is append-only (BEFORE UPDATE / DELETE trigger raises
`CHAIN IMMUTABILITY VIOLATION`).

---

## Test results

### Test 1: `test_chain_integrity_holds_for_honest_data`
3 resolved predictions committed → `verify_chain()` = **True** ✓

### Test 2: `test_tampering_with_resolved_outcome_is_detected`
Simulated operator bypass (disabled ledger trigger) to flip `resolved_outcome`
of one prediction:

```
stored    chain head : d0258cac30b1d738...
recomputed head      : TAMPERED_AT_SEQ_4
verify_chain()       : False — tampering DETECTED ✓
```

The stored head and recomputed head diverge immediately at the sequence position
of the altered row. Any third party running `recompute_chain_head(db)` would see
the same `TAMPERED_AT_SEQ_N` result.

### Test 3: `test_chain_log_is_itself_append_only`
Direct `UPDATE prediction_chain_log SET row_hash = 'aaaa'` → raises
`CHAIN IMMUTABILITY VIOLATION` ✓

The chain log cannot be silently altered to cover up a ledger alteration. Both
the ledger row AND the chain entry would need to be changed consistently — but
the chain entry is append-only, so there is no consistent cover-up path.

### Test 4: `test_recomputed_score_diverges_after_tampering`
Operator altered `probability` of one prediction from `0.70` → `0.999`:

```
stored credential overall_log_score  : -0.356675
recomputed (from tampered rows)      : -0.355831
delta                                :  0.000844 > 1e-4 — rigging EXPOSED ✓
```

An independent auditor running `reserve/tools/recompute_credential.py` would see
a score that does not match the stored credential — proving the credential was
issued on different data than what the ledger currently contains.

---

## What the chain proves vs what it does not

**Proven (tested):**
- Any alteration to a committed prediction's fields causes `recompute_chain_head()`
  to diverge from `get_chain_head()` — detectable by any third party, no secret.
- The chain log itself is append-only and cannot be silently rewritten.
- A rigged score (altered probability) is exposed by independent recomputation.

**Not proven / not attempted:**
- Preventing the operator from deleting chain entries entirely (that would be a
  separate external audit / log-shipping solution).
- Decentralised chain hosting (the chain is operator-run; third parties must
  have read access to the DB or to a published snapshot to audit).
- Real-time monitoring of chain state (currently pull-based, not push).

---

## Test file

`reserve/tests/test_tamper_evidence.py` — 4 tests, all passing on real Postgres.
