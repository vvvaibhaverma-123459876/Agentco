# Epistemic Engine Foundation

## Implemented

- `epistemic/claims/claim_model.py` defines structured claims, reality boundaries, and claim statuses.
- `epistemic/evidence/evidence_model.py` defines evidence records and evidence types.
- `epistemic/evidence/evidence_store.py` provides deterministic evidence hashing and an in-memory evidence store for foundation tests.
- `epistemic/validation/validation_rings.py` maps claim boundaries and risk to minimum validation rings.
- `epistemic/validation/validation_policy.py` seeds basic validation policies.
- `epistemic/validation/validation_policy_engine.py` selects policies and rejects high-risk claims with no policy.
- `epistemic/promotion/knowledge_promotion.py` enforces initial promotion rules.
- `backend/src/db/migrations/019_epistemic_foundation.sql` adds claim, evidence, policy, and validation assignment tables.

## Tested

- Internal ledger claims can internally verify with ledger/audit evidence.
- Simulation claims promote only to `simulation_validated`.
- External empirical claims require external evidence.
- Future claims cannot promote before resolution date.
- Normative claims use governance policy rather than empirical truth scoring.
- Unresolved serious disputes block promotion.
- Mechanical evidence can promote software claims to `mechanically_resolved`.
- Claim authority rings match boundary/risk rules.
- High-risk claims without policy are rejected.

Run:

```bash
python3 -m pytest tests/test_epistemic_engine_foundation.py
```

## Not Implemented

- Persistent claim/evidence services over Postgres.
- Backend API routes for the epistemic engine.
- Dispute ruling and precedent services.
- Authority/jurisdiction integration.
- Full policy authoring and governance approval flow.

## Future Work

- Wire the foundation to DB-backed services.
- Integrate promotion decisions with trust/reputation and dispute rulings.
- Add OpenAPI routes after the DB service layer is stable.
