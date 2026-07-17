# Cross-Version Ancestry Report

## Subjects

- Version A audited baseline: `fb27dc0529d3c5d11480503bfbcf6f2d156f5b04`
- Version B raw candidate: `651794a41513db1e40930f08c253ef261af7c1e7`
- Civilization-layer source head: `75406a50882ad84bd7a5a18ee84b6309d908a034`
- Merge base: `fb27dc0529d3c5d11480503bfbcf6f2d156f5b04`

## Merge Lineage

- PR #25 merge: `5ec0d66fd126a2493b0111328f1d35741d57daef`
- PR #25 parents: `2d1eff732c1b14bea09eee5b7c41979be41a1372`, `fb27dc0529d3c5d11480503bfbcf6f2d156f5b04`
- PR #26 merge: `651794a41513db1e40930f08c253ef261af7c1e7`
- PR #26 parents: `5ec0d66fd126a2493b0111328f1d35741d57daef`, `75406a50882ad84bd7a5a18ee84b6309d908a034`

Git produced a merge commit for PR #26, but semantic compatibility is not implied by the absence of textual conflicts.

## Primary Semantic Conflict

The merged tree contains two migration files with the numeric prefix `129`:

- `backend/src/db/migrations/129_civilization_kernel.sql`
- `backend/src/db/migrations/129_longitudinal_mission_evidence.sql`

Version B remains preserved as the raw candidate. Version C adds an explicit migration identity/content-hash contract and a validator so the duplicate numeric prefix is governed rather than implicit.

## Representative Version B Scope

Version B introduced the civilization runtime routes, services, migrations, tests, and ledger files, including:

- `CIVILIZATION_BUILD_LEDGER.yaml`
- `backend/src/routes/civilization-kernel.routes.ts`
- `backend/src/services/civilization-kernel.service.ts`
- `backend/tests/civilization-kernel.test.ts`
- `docs/civilization/PLAN_AND_PROGRESS.md`

## Conclusion

The primary reconciliation requirement is migration identity hardening. No hidden benchmark or validation outcome was used to produce Version C.
