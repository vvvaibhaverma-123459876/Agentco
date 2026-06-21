# Credential Canonicalization

## Implemented

- The canonical credential path is Python Reserve:
  - `reserve/scoring/scoring_function.py`
  - `reserve/credentials/proof_of_calibration.py`
  - `reserve/tools/recompute_credential.py`
- Backend `GET /api/credential/:agent_id` reads the latest stored row from `calibration_credentials`.
- `scripts/issue_canonical_credential.py` issues credentials through the canonical Python Reserve path.
- Backend `POST /api/credential/:agent_id/issue` invokes the Python issuer boundary and requires credential issuer scope.
- Backend `POST /api/credential/:agent_id/verify` invokes recomputation and reports correctness/authorship fields.
- The backend response distinguishes credential data from verification instructions.
- The backend no longer emits a new TypeScript-computed HMAC credential as the primary credential.
- TypeScript does not score or sign credentials independently; it delegates issuance/recomputation to Python.

## Tested

- Backend credential service returns stored canonical credentials with Ed25519 verification metadata.
- Backend credential service returns `null` when no stored canonical credential exists instead of synthesizing a noncanonical HMAC credential.
- Backend issue route requires credential issuer scope and returns Python issuer output.
- Backend verify route returns correctness and authorship fields.
- Python issuer creates and persists canonical credentials.
- Python issuer output matches independent recomputation from ledger rows.

Run:

```bash
python3 -m pytest reserve/tests/test_canonical_credential_issuer_service.py
cd backend && npm test -- credential-canonical.test.ts credential-routes.test.ts
```

## Not Implemented

- Backend currently reports Ed25519 signature presence but does not perform public-key signature verification inside TypeScript.
- Stored DB schema preserves the legacy `overall_score` field for overall log score; overall brier score is available from issued JSON/recomputation but not stored as a separate DB column.
- Legacy HMAC remains for compatibility and is explicitly noncanonical.

## Future Work

- Add TypeScript-side public-key signature verification or delegate authorship verification to a Python verifier command.
- Deprecate legacy HMAC fields after migration compatibility is no longer needed.
- Add key rotation metadata and issuer identity records.

## Manual Verification

```bash
python3 scripts/issue_canonical_credential.py <agent_id>
python3 reserve/tools/recompute_credential.py <agent_id>
```

Correctness is verified by comparing issued score fields against recomputation. Authorship is verified with the Reserve Ed25519 public key when `ed25519_signature` is present.
