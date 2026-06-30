-- The civilization verifier uses Reserve recomputation, but the backend
-- migration runner does not apply reserve/migrations. Keep the ledger fields
-- required by that public recomputation path in the backend migration stream.

ALTER TABLE prediction_ledger
  ADD COLUMN IF NOT EXISTS consequence BOOLEAN DEFAULT FALSE;

UPDATE prediction_ledger
   SET consequence = FALSE
 WHERE consequence IS NULL;

ALTER TABLE prediction_ledger
  ALTER COLUMN consequence SET DEFAULT FALSE,
  ALTER COLUMN consequence SET NOT NULL;

CREATE OR REPLACE FUNCTION trg_reserve_fields_immutable()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.hardness IS DISTINCT FROM OLD.hardness THEN
        RAISE EXCEPTION
            'IMMUTABILITY VIOLATION: prediction_ledger.hardness is write-once (prediction_id=%)',
            OLD.prediction_id;
    END IF;

    IF OLD.consequence = TRUE AND NEW.consequence = FALSE THEN
        RAISE EXCEPTION
            'IMMUTABILITY VIOLATION: prediction_ledger.consequence cannot be reverted (prediction_id=%)',
            OLD.prediction_id;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_reserve_fields_immutable ON prediction_ledger;
CREATE TRIGGER trg_reserve_fields_immutable
    BEFORE UPDATE ON prediction_ledger
    FOR EACH ROW EXECUTE FUNCTION trg_reserve_fields_immutable();
