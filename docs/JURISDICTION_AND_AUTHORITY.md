# Jurisdiction And Authority

## Implemented

- `civilization/jurisdiction/authority_grants.py` defines authority grants and decisions.
- `civilization/jurisdiction/jurisdiction_engine.py` checks action, domain, claim type, risk level, expiration, suspension, low reputation, unresolved disputes, and self-authority expansion.
- `backend/src/db/migrations/019_epistemic_foundation.sql` includes an `authority_grants` table.

## Tested

- Authorized entity passes.
- Expired grants fail.
- Wrong domain and wrong claim type fail.
- Risk above grant limit fails.
- Suspended entities fail.
- Self-authority expansion is rejected.
- Low reputation and unresolved disputes block high-risk authority.

Run:

```bash
python3 -m pytest tests/test_jurisdiction_authority.py
```

## Not Implemented

- DB-backed authority grant service.
- Backend authority APIs.
- Integration with live governance decisions.
- Authority expiry sweep or renewal workflow.

## Future Work

- Persist authority grants through audited governance decisions.
- Check authority before verification assignment, credential issuance, and high-risk approvals.
