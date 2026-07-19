# Loop Decisions

- Existing non-claims remain active: real capability baseline not established, hosted staging unverified, production readiness unverified, capability improvement not claimed.

## DEC-001 — Continue Without Confirmation While Status Is CONTINUE

- Decision: when `.loop/status` is `CONTINUE`, future iterations continue autonomously without asking for confirmation.
- Rationale: the outer loop is designed to restart iterations until the status changes.
- Alternatives considered: ask before each iteration; rejected because it prevents unattended loop progress.
- Reversibility: reversible by a later loop decision if the operating prompt changes.
- Claims/docs updated: `.loop/LOOP_LOG.md` records ongoing iteration summaries; no capability or production claim changed.

## DEC-002 — Adopt Continuous Completion Loop v2 Authority Model

- Decision: replace approval-gated memory with autonomous decision authority for scope, model choice from verified account availability, invalid-evidence quarantine, dependency/architecture choices, and standard-item descoping as last resort.
- Rationale: the current operating prompt explicitly removes human approval waits; decisions may change scope but cannot create evidence or upgrade claims.
- Alternatives considered: preserve old `Human action required` blocking language; rejected because it conflicts with the v2 loop protocol and causes unnecessary pauses.
- Reversibility: reversible by future committed loop protocol change, but evidence claims must remain truthful.
- Claims/docs updated: `.loop/BLOCKED.md` now points to `.loop/PROVISIONING.md`; standard non-claims remain active.
