# Epistemic Disputes And Precedent

## Implemented

- `epistemic/disputes/dispute_model.py` defines dispute types and dispute records.
- `epistemic/disputes/dispute_service.py` provides an in-memory dispute service for foundation behavior.
- `epistemic/disputes/ruling_service.py` records rulings and applies final ruling outcomes to claim state.
- `epistemic/disputes/precedent_service.py` creates precedents from rulings.
- `backend/src/db/migrations/019_epistemic_foundation.sql` includes `claim_disputes`, `rulings`, and `precedents` tables.

## Tested

- Opening a serious unresolved dispute blocks promotion.
- Final overturned rulings move claims to `overturned`.
- Precedents can be created from rulings.
- Fraudulent rulings can mark claims fraudulent and carry a penalty payload.

Run:

```bash
python3 -m pytest tests/test_epistemic_disputes_and_precedent.py
```

## Not Implemented

- DB-backed dispute/ruling/precedent services.
- Backend routes for disputes.
- Appeals and jurisdiction routing.
- Reputation penalty propagation from fraudulent rulings.

## Future Work

- Persist disputes and rulings in Postgres.
- Integrate jurisdiction and authority checks.
- Apply final rulings to claim registry records through an audited service.
