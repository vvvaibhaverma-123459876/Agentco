-- Trigger-based immutability for decision_log.
-- REVOKE UPDATE/DELETE FROM PUBLIC cannot block superusers or the table owner,
-- so we use BEFORE triggers that raise unconditionally. Superusers disable the
-- trigger temporarily for administrative operations (chain tamper detection in tests).
CREATE OR REPLACE FUNCTION enforce_decision_log_immutable()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'decision_log is append-only: % is forbidden', TG_OP;
END;
$$;

DROP TRIGGER IF EXISTS trg_decision_log_no_update ON decision_log;
DROP TRIGGER IF EXISTS trg_decision_log_no_delete ON decision_log;

CREATE TRIGGER trg_decision_log_no_update
  BEFORE UPDATE ON decision_log
  FOR EACH ROW EXECUTE FUNCTION enforce_decision_log_immutable();

CREATE TRIGGER trg_decision_log_no_delete
  BEFORE DELETE ON decision_log
  FOR EACH ROW EXECUTE FUNCTION enforce_decision_log_immutable();
