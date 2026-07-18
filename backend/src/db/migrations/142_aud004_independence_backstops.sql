-- Migration 142 (AUD-004 M4): DB backstops for conditions 16 & 25 independence.
--
-- The audit found independence was APPLICATION-ONLY (a direct-SQL writer could bypass the
-- evaluator<>proposer and appellate<>complainant/trial-judge checks). These BEFORE INSERT
-- triggers enforce the same relationships at the database, over authenticated actor ids, so a
-- direct-SQL path cannot defeat them. Additive; coexists with the existing append-only guards.

-- Condition 25: independent evaluation — evaluator may not be the candidate's proposer.
CREATE OR REPLACE FUNCTION civ_evaluation_independence_guard() RETURNS trigger AS $$
DECLARE proposer UUID;
BEGIN
  SELECT proposer_actor_id INTO proposer FROM civ_learning_candidates WHERE id = NEW.candidate_id;
  IF proposer IS NOT NULL AND proposer = NEW.evaluator_actor_id THEN
    RAISE EXCEPTION 'EVALUATION INDEPENDENCE (cond 25): evaluator % may not be the proposer of candidate %',
      NEW.evaluator_actor_id, NEW.candidate_id;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_civ_evaluation_independence ON civ_evaluations;
CREATE TRIGGER trg_civ_evaluation_independence
  BEFORE INSERT ON civ_evaluations
  FOR EACH ROW EXECUTE FUNCTION civ_evaluation_independence_guard();

-- Condition 16: appeals by an independent authority — the appellate authority may not be the
-- complainant nor the trial (non-appellate) judge on the same case.
CREATE OR REPLACE FUNCTION judiciary_appellate_independence_guard() RETURNS trigger AS $$
DECLARE complainant UUID; trial_judge UUID;
BEGIN
  IF NEW.is_appellate = true THEN
    SELECT complainant_actor_id INTO complainant FROM judiciary_cases WHERE id = NEW.case_id;
    SELECT ruling_actor_id INTO trial_judge
      FROM judiciary_rulings WHERE case_id = NEW.case_id AND is_appellate = false LIMIT 1;
    IF complainant IS NOT NULL AND complainant = NEW.ruling_actor_id THEN
      RAISE EXCEPTION 'APPEAL INDEPENDENCE (cond 16): appellate authority % may not be the complainant', NEW.ruling_actor_id;
    END IF;
    IF trial_judge IS NOT NULL AND trial_judge = NEW.ruling_actor_id THEN
      RAISE EXCEPTION 'APPEAL INDEPENDENCE (cond 16): appellate authority % may not be the trial judge', NEW.ruling_actor_id;
    END IF;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_judiciary_appellate_independence ON judiciary_rulings;
CREATE TRIGGER trg_judiciary_appellate_independence
  BEFORE INSERT ON judiciary_rulings
  FOR EACH ROW EXECUTE FUNCTION judiciary_appellate_independence_guard();
