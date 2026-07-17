# Volume 24 — Interaction Intelligence

## 1. Header

| Field | Value |
|---|---|
| Volume | 24 |
| Name | Interaction Intelligence |
| Tier | regulation |
| Epistemic status | prescriptive |
| Doc status | written |
| Related volumes | V9 (Knowledge System), V11 (Trust & Calibration), V10 (Reasoning Engine), V27 (Operator Control Plane), V33 (Model Governance) |

## 2. Purpose

Interaction Intelligence is how AgentCo interacts with the world across *many* modes — not
just chat. The Domain Neutrality correction renamed this from "Response Intelligence"
because **conversation must not be the architectural center** (`GENERALIZATION_REPORT.md`
§6): chat is one interaction mode among planning, execution, negotiation, governance,
teaching, explanation, simulation, supervision, inspection, and collaboration. This volume
defines the mode-agnostic contract: whatever the mode, an interaction routes to the right
capability, grounds its assertions in evidence (V9), carries calibrated confidence (V11),
and records its reasoning (V10). Prescriptive tier: the unified interaction layer does not
yet exist as such; §9 cites the substrate honestly.

```text
INTERACTION (any mode)
   modes: chat · planning · execution · negotiation · governance · teaching ·
          explanation · simulation · supervision · inspection · collaboration
   ▼  ROUTE   calibration-aware-routing.service.ts (rank by calibration history)
   ▼  REASON  planner / ensembles (autonomy-action-planner, multi-agent-ensemble)
   ▼  GROUND  every assertion cites registered evidence (V9 claim-grounding)
   ▼  CALIBRATE  confidence from trust (V11)
   ▼  RECORD  reasoning + constraints (V10 / V23 obligations)
   ▼  RESPOND (mode-appropriate output)  ── feedback loops back to trust (V11)
```

## 3. Definitions

- **Interaction mode** — one of the ways AgentCo engages (chat, planning, execution,
  negotiation, governance, teaching, explanation, simulation, supervision, inspection,
  collaboration). (Prescriptive: modes as first-class is to be built.)
- **Routing** — selecting the capability/agent for an interaction, ranked by calibration
  history (`backend/src/services/calibration-aware-routing.service.ts`).
- **Grounding** — the requirement that an assertion cite registered evidence (V9).
- **Calibration** — the confidence attached to a response, from trust (V11).
- **Ensemble** — multi-agent collaboration on an interaction
  (`backend/src/services/multi-agent-ensemble.service.ts`).

## 4. Invariants

Prescriptive: mostly planned. Enforced entries are genuine substrate, not a claim the
unified layer exists.

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V24-INV-001 | Interactions are routed by calibration history, so the most-calibrated capability is preferred. | enforced | `backend/src/services/calibration-aware-routing.service.ts` |
| V24-INV-002 | Interaction reasoning is produced through the planner/ensemble path, not ad hoc, so multi-agent collaboration is a first-class interaction. | enforced | `backend/src/services/autonomy-action-planner.service.ts`, `backend/src/services/multi-agent-ensemble.service.ts` |
| V24-INV-003 | An assertion made in an interaction must be grounded in registered evidence (the V9 contract applies to responses). | enforced | `backend/src/services/claim-grounding.service.ts`, `backend/tests/planner-claim-bias.test.ts` |
| V24-INV-004 | Interaction modes (chat, planning, execution, negotiation, governance, teaching, explanation, simulation, supervision, inspection, collaboration) are first-class and mode-agnostic routing selects among them. | planned | — |
| V24-INV-005 | Conversation/chat is one mode, not the architectural center — no capability is reachable only via chat. | planned | — |
| V24-INV-006 | Every interaction response carries a calibrated confidence derived from trust (V11). | planned | — |
| V24-INV-007 | Every interaction records its reasoning (V10) and the constraints it passed (V23). | planned | — |
| V24-INV-008 | Interaction feedback (was the response useful/correct?) feeds back into trust and learning as resolved outcomes. | planned | — |
| V24-INV-009 | A teaching/explanation mode can render the "why" of any decision to a human at an appropriate level of detail. | planned | — |

## 5. Interfaces

Prescriptive — the intended contract:

- **Router** — `calibration-aware-routing.service.ts` (rank by calibration).
- **Reasoners** — `autonomy-action-planner.service.ts`, `ensemble.service.ts`,
  `multi-agent-ensemble.service.ts`, `planner.service.ts`.
- **Grounding** — `claim-grounding.service.ts` (V9).
- **Model** — `llm-provider.service.ts` (V33) for generative modes.
- **Substrate today** — `backend/src/routes/autonomy-tasks.routes.ts` (task interaction);
  the operator console chat surface (V27/V28).

## 6. State

- **To be built:** a mode registry and a mode-agnostic interaction router with per-mode
  contracts.
- **Substrate today:** calibration routing, planner/ensemble reasoning, claim grounding,
  trust scores (V11), the model provider (V33).

## 7. Failure modes and responses

- **Chat-centrism** — the renamed volume's core rule: no capability may be reachable only
  via chat (V24-INV-005 planned); today interaction is task/planner-centric, which is
  already not chat-centric, but modes are not first-class (V24-INV-004 planned).
- **Ungrounded answers** — the V9 grounding contract applies to interaction assertions
  (V24-INV-003), so a response cannot fabricate support; this is enforced today via claim
  grounding.
- **Overconfident responses** — per-response calibrated confidence from trust is not yet
  wired into every interaction (V24-INV-006 planned).
- **Unexplainable answers** — a teaching/explanation mode rendering a decision's "why"
  (V10) to a human is not yet built (V24-INV-009 planned).

## 8. Verification obligations

Existing and green today: `backend/tests/planner-claim-bias.test.ts` (grounded claims),
calibration-aware routing behaviour.

Must exist to satisfy the volume: a mode registry + mode-agnostic router with tests
(V24-INV-004/005), per-response calibration (V24-INV-006), reasoning/constraint recording
per interaction (V24-INV-007), and a feedback-to-trust loop (V24-INV-008).

## 9. Implementation mapping

- **Enforced substrate:** `calibration-aware-routing.service.ts` (routing),
  `autonomy-action-planner.service.ts` / `multi-agent-ensemble.service.ts` (reasoning),
  `claim-grounding.service.ts` (grounding).
- **Not yet built:** the unified mode-agnostic interaction layer — a mode registry, a
  router that treats chat as one mode among eleven, per-response calibration, and a
  feedback loop into trust/learning.
- **Adjacent:** `llm-provider.service.ts` (V33), operator chat surface (V27/V28).

## 10. Open questions

1. **Modes as data vs code.** The eleven interaction modes should be a registry (so a new
   mode is added without new architecture — the Domain Neutrality spirit applied to
   interaction), not a hardcoded enum (V24-INV-004).
2. **Feedback loop is missing.** Interaction outcomes should resolve as predictions feeding
   trust (V11) and learning (V14) — "was this response correct?" is exactly the kind of
   falsifiable outcome the calibration loop consumes (V24-INV-008).
3. **Teaching mode and V10.** The reasoning records V10 mandates are the raw material for
   an explanation/teaching mode (V24-INV-009); this volume is where V10's "why" becomes
   human-facing.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written (renamed from Response Intelligence per GENERALIZATION_REPORT §6). | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 27) | Reframe interaction as mode-agnostic — chat one mode among many — with routing, grounding, calibration, and reasoning contracts, while honestly marking the unified interaction layer as to-be-built over the existing routing/planner/grounding substrate. |
