# Civilization Memory Events

Canonical event types currently accepted by `civilization_memory_events`:

- `output_created`: an output entered the institutional review system.
- `review_completed`: an external review reached an approved or otherwise completed decision.
- `challenge_opened`: a review was challenged with evidence.
- `challenge_resolved`: a previously challenged review was resolved.
- `governance_decision`: a governance decision was proposed or transitioned.
- `reputation_updated`: derived reputation changed through the reputation propagation service.
- `institution_created`: an institution was created with its mandatory departments.
- `institution_retired`: an institution was retired.
- `failure_recorded`: a failure, rejection, timeout, or escalation was recorded.
- `lesson_extracted`: a lesson was extracted from approved evidence or repeated patterns.

Memory events are audit evidence. They do not directly grant trust, reputation, authority, jurisdiction, budget, or governance power.
