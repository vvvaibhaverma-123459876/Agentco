# Human Decisions

- No human descoping decisions are recorded yet.
- Existing non-claims remain active: real capability baseline not established, hosted staging unverified, production readiness unverified, capability improvement not claimed.
- Loop continuation policy: when `.loop/status` is `CONTINUE`, future iterations should continue autonomously without asking the user for confirmation. Ask only when the next step requires a human-only input, credential, provider authorization, hosted infrastructure decision, or other action that cannot be safely inferred from repository state.
