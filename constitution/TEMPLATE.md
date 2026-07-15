# Volume Template

Every volume uses exactly these sections, in this order, with these exact `##` headings.
(`charter`-tier volumes: sections 1–2 only, ≤120 lines, per `CONVENTIONS.md`.)

---

# Volume <N> — <Name>

## 1. Header

| Field | Value |
|---|---|
| Volume | <N> |
| Name | <Name — exactly as in INDEX.md> |
| Tier | <constitutional \| statute \| regulation \| article \| charter> |
| Epistemic status | <descriptive \| mixed \| prescriptive \| aspirational> |
| Doc status | <not written \| in progress \| written> |
| Related volumes | <e.g. V1, V12> |

## 2. Purpose

Why this layer exists and what it is responsible for. One page maximum.

## 3. Definitions

Terms this volume introduces or relies on. Reuse existing repo vocabulary; do not
invent synonyms.

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V<N>-INV-001 | <one testable sentence> | enforced \| planned \| aspirational | <paths, or —> |

Every row here must be registered in `constitution/invariants.yaml`.

## 5. Interfaces

APIs, routes, events, and CLI/Make entry points this layer exposes and consumes.
Descriptive claims cite the defining file.

## 6. State

Database tables, migrations, files, and reports this layer owns. Cite migrations and
paths for what exists today.

## 7. Failure modes and responses

What can go wrong at this layer and what the system does about it (including honest
"nothing yet" statements for gaps).

## 8. Verification obligations

The tests and CI gates that must exist (and which of them exist today, with paths) for
this volume's invariants to be real.

## 9. Implementation mapping

What exists in THIS repo today for this layer, with file paths — the bridge between
constitution and code. This section is where epistemic honesty lives.

## 10. Open questions

Contradictions between intended design and observed code (with citations), unresolved
decisions, and known drift. Do not fix production code from here; record it.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
