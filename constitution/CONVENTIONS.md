# Architecture Constitution — Conventions

These conventions govern every document under `constitution/`. They exist because this
repository's documentation has drifted from its code before (multiple status documents,
disagreeing numbers). A constitution is only valuable if it **cannot silently drift**, so
the automated checker (`scripts/constitution/check_constitution.py`, run in CI by
`.github/workflows/constitution.yml`) was built before any volume content. A volume that
does not pass the checker is not written; it is drift being born.

## Tiers

Every volume has exactly one tier. The tier states how hard the document is to change.

| Tier | Meaning |
|---|---|
| `constitutional` | Amend only with explicit human sign-off and a recorded rationale (a Change log entry naming the human and the reason). |
| `statute` | Normal review: change with an ordinary reviewed commit. |
| `regulation` | May change freely. |
| `article` | Cross-cutting; imposes obligations on ALL volumes (e.g. "every decision records its assumptions"). Articles are written as obligations other volumes must satisfy, not as service designs. |
| `charter` | One-page placeholder (max 120 lines) for a capability that does not exist yet. |

## Epistemic status

Every volume declares exactly one epistemic status. The status governs the voice the
volume is allowed to use.

| Status | Meaning |
|---|---|
| `descriptive` | The code exists and runs. Every normative sentence must cite the enforcing file or test. |
| `mixed` | Partially exists. Sentences about today's system cite file paths; everything else is clearly marked "to be built". |
| `prescriptive` | A buildable design. Must never claim any part already exists. |
| `aspirational` | Charter only, max 120 lines. No detailed design. |

## Invariant IDs

- Format: `V<vol>-INV-<3 digits>`, e.g. `V9-INV-004`.
- IDs are **never renumbered and never reused**. If an invariant is dropped, its registry
  entry stays and is annotated (`retired_reason`), not deleted.
- Each invariant is **one testable sentence**.
- An invariant is *defined* by exactly one volume (the one in its ID). Other volumes may
  reference it by ID in prose.

## Invariant registry (`constitution/invariants.yaml`)

Every invariant that appears in a volume's Invariants section MUST be registered here,
and every registered invariant MUST appear in its (written) volume. Fields:

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | `V<vol>-INV-<3 digits>` |
| `statement` | yes | One testable sentence. |
| `tier` | yes | `constitutional` \| `statute` \| `regulation` \| `article` \| `charter` |
| `status` | yes | `enforced` \| `planned` \| `aspirational` |
| `enforcement` | when `status: enforced` | List of repo file paths and/or test references that enforce the invariant. |
| `retired_reason` | no | Present only on retired invariants (entry is kept forever). |

Enforcement entry format: a repo-relative path that must exist (file or directory), or
`<path>::<test name>` where the path part must exist. The checker fails the build if an
`enforced` invariant has no enforcement entries or cites a path that does not exist.

## Volume files

- Location: `constitution/volumes/VOL-<NN>-<kebab-name>.md` (two-digit volume number).
- Every volume uses `constitution/TEMPLATE.md`'s sections, **in order, with those exact
  headings**. Exception: `charter`-tier volumes need only sections 1 (Header) and
  2 (Purpose), must contain an explicit "not yet designed" statement plus the conditions
  under which detailed design may begin, and must not exceed 120 lines total.
- The Header section is a two-column table whose `Volume`, `Name`, `Tier`,
  `Epistemic status`, and `Doc status` rows must agree exactly with the volume's row in
  `constitution/INDEX.md`. The checker enforces this.
- Doc status values in INDEX.md and volume headers: `not written` | `in progress` | `written`.
- Grounding rules (all volumes, forever):
  - Any sentence describing what the system does TODAY must cite a real file path.
  - Anything that does not exist yet must be worded as aspiration or design, never
    present tense.
  - Reuse the repo's existing vocabulary (evidence, claim, prediction, trust, memory,
    citizen, institution, mission, treasury, ledger, outbox). Do not invent synonyms.
  - Max ~400 lines per volume (charters: 120).

## Change discipline

- Writing a volume = the volume file + its registry entries + flipping its INDEX.md
  Doc status to `written` + a green checker run. Nothing less counts as written.
- Do not renumber volumes. Do not edit other volumes when writing one (the INDEX.md
  Doc status column is the only exception).
- `constitutional`-tier volumes: record amendments in the volume's Change log with the
  authorizing human and rationale.
