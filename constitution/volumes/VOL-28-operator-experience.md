# Volume 28 — Operator Experience

## 1. Header

| Field | Value |
|---|---|
| Volume | 28 |
| Name | Operator Experience |
| Tier | regulation |
| Epistemic status | mixed |
| Doc status | written |
| Related volumes | V27 (Operator Control Plane), V18 (Civilization Self Model), V17 (Self Inspection), V10 (Reasoning Engine), V32 (Security) |

## 2. Purpose

Operator Experience is the visual, human-facing surface: the pages through which an
operator sees and understands the civilization. It is distinct from the Control Plane
(V27, *what an operator may do*) — this volume is *how the operator perceives*. Its
load-bearing built property is that the frontend is a **thin, governed view**: every value
comes from the governed backend through a server-side proxy that injects the API key so the
credential is never exposed to the browser, and no page fabricates data. The richer
visualizations the Vision names (architecture graph, institution tree, capability map,
mission graph, reasoning/learning explorers) are the growth direction and depend on the
Self Model (V18). Regulation tier; mixed status; every present-tense claim cites its file.

```text
BROWSER (no secrets)
   ▼  server-side proxy  frontend/src/app/api/[...path]/route.ts
   │    injects AGENTCO_API_KEY as x-api-key  (key never reaches the client)
   ▼
GOVERNED BACKEND
   ▲
PAGES (13 today): dashboard · civilization · governance · autonomy · audit ·
   events · finance · incidents · performance · validation · evals · config · override
   ▼  growth direction (needs V18 Self Model):
   architecture graph · institution tree · capability map · mission graph ·
   reasoning explorer · learning explorer
```

## 3. Definitions

- **Operator page** — a Next.js page rendering a governed view
  (`frontend/src/app/*/page.tsx`, 13 today).
- **Server-side proxy** — the API route that forwards browser requests to the backend
  with the injected API key (`frontend/src/app/api/[...path]/route.ts`).
- **Governed view** — a surface that renders only backend-sourced data, never fabricated.
- **Explorer** — a graph/tree visualization of a subsystem (architecture, institution,
  capability, mission, reasoning, learning) — mostly to be built, needing the Self Model
  (V18).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V28-INV-001 | The browser never receives the backend API key; it is injected server-side by the proxy. | enforced | `frontend/src/app/api/[...path]/route.ts` |
| V28-INV-002 | The frontend reaches the backend only through the server-side proxy, so hop-by-hop headers are stripped and auth is centralized. | enforced | `frontend/src/app/api/[...path]/route.ts` |
| V28-INV-003 | The civilization operator console renders only governed backend data, never fabricated or placeholder values. | enforced | `frontend/src/app/civilization/page.tsx`, `backend/tests/civilization-operator.test.ts` |
| V28-INV-004 | Operator pages exist for the civilization's principal subsystems (dashboard, governance, autonomy, audit, events, finance, incidents, performance, validation). | enforced | `frontend/src/app` |
| V28-INV-005 | A health route is exposed for the frontend independent of backend auth. | enforced | `frontend/src/app/api/health/route.ts` |
| V28-INV-006 | The architecture, institution, capability, and mission graphs are visualized from the Self Model as first-class explorers. | planned | — |
| V28-INV-007 | A reasoning explorer reconstructs why any decision was made (the V10 obligation, surfaced). | planned | — |
| V28-INV-008 | A learning explorer shows the failure→candidate→promotion/rollback lineage (V14) visually. | planned | — |
| V28-INV-009 | Every operator page declares which governed endpoint sources each value, so a fabricated value would fail a view-contract check. | planned | — |

## 5. Interfaces

- **Proxy** — `frontend/src/app/api/[...path]/route.ts` (key injection, header
  stripping); `frontend/src/app/api/health/route.ts`.
- **Client libs** — `frontend/src/lib/api.ts`, `frontend/src/lib/api/*`.
- **Pages** — `frontend/src/app/{dashboard,civilization,governance,autonomy,audit,events,finance,incidents,performance,validation,evals,config,override}/page.tsx`.
- **Backend sources** — the governed routes each page reads (classified in the V32
  matrix); operator overview via `civilization-operator.service.ts` (V27).
- **Self Model dependency** — the explorers (V28-INV-006..008) require V18.

## 6. State

- **Frontend:** `frontend/src/app/` (13 pages + api proxy + health), `frontend/src/lib/`.
- **Config:** `AGENTCO_API_KEY` (server-side only), backend base URL.
- **No client-side secrets:** the proxy is the only credential holder.

## 7. Failure modes and responses

- **Leaked credential** — the API key lives only server-side and is injected by the proxy
  (V28-INV-001), so a browser bundle cannot carry it.
- **Direct-to-backend bypass** — the frontend routes through the proxy, centralizing auth
  and stripping hop-by-hop headers (V28-INV-002).
- **Fabricated dashboards** — the civilization console renders only governed data
  (V28-INV-003), enforced by the operator service test; extending this contract to every
  page is V28-INV-009 (planned).
- **No system-shape view** — the graph explorers (architecture/institution/capability/
  mission/reasoning/learning) mostly do not exist because they need the Self Model (V18)
  as their data source (V28-INV-006..008 planned; open question 1) — the main growth gap.

## 8. Verification obligations

Existing and green today: `backend/tests/civilization-operator.test.ts` (governed data),
frontend build (Next.js), the proxy key-injection path.

Must exist before the planned invariants flip: the Self-Model-backed explorers with tests
(V28-INV-006..008), and a per-page view-contract asserting every rendered value has a
governed source (V28-INV-009).

## 9. Implementation mapping

- `frontend/src/app/api/[...path]/route.ts` — server-side proxy with key injection.
- `frontend/src/app/civilization/page.tsx` — governed operator console (V27/V28 seam).
- `frontend/src/app/*/page.tsx` — the 13 operator pages.
- `frontend/src/lib/api/*` — client API helpers.
- Self Model (V18) — the required data source for the unbuilt explorers.

## 10. Open questions

1. **Explorers need the Self Model.** The architecture graph, institution tree, capability
   map, mission graph, and reasoning/learning explorers (the Vision's richer UX) cannot be
   built well until the Self Model (V18) materializes the graphs they would render
   (V28-INV-006..008). This volume's growth is gated on V18.
2. **View contracts.** Only the civilization console is test-enforced to show governed
   data; a general per-page "every value has a governed source" contract (V28-INV-009)
   would generalize the no-fabrication rule across all 13 pages.
3. **Regulation tier.** As a freely-changeable UI layer, Operator Experience should bind
   only the security-load-bearing invariants (no client secret, proxy-only, no
   fabrication) and let visual design iterate freely.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 26) | Bind the thin-governed-view frontend (server-side key injection, proxy-only, no fabrication) into one citable operator-experience layer, and mark the Self-Model-dependent explorers as the growth direction. |
