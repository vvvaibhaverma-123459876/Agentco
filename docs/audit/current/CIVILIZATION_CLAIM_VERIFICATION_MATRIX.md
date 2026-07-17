# Civilization Claim Verification Matrix

This matrix audits civilization-layer claims separately from the blind paired benchmark. Claim-derived tests are not used as primary promotion evidence.

| Claim | Actual status | Evidence | Limitation |
|---|---|---|---|
| C0 canonical runtime selection | static_only | canonical runtime map files | Authority conflicts still require deeper runtime audit. |
| C1 civilization kernel | unit_verified | `backend/tests/civilization-kernel.test.ts` | No hosted or long-run proof. |
| C2 citizenry | unit_verified | `backend/tests/citizenship.test.ts` | Local lifecycle proof only. |
| C3 societies/institutions | unit_verified | `backend/tests/societies-institutions.test.ts` | Deployment-boundary proof absent. |
| C4 coalitions | unit_verified | `backend/tests/coalitions.test.ts` | Mission-level coalition proof remains partial. |
| C5 missions | unit_verified | `backend/tests/missions.test.ts` | Full governed lifecycle E2E remains partial. |
| C6 economy | unit_verified | `backend/tests/treasury.test.ts` | Not tied to hosted billing controls. |
| C7 governance | unit_verified | `backend/tests/governance.test.ts` | Runtime policy rollback E2E remains partial. |
| C8 judiciary | unit_verified | `backend/tests/judiciary-case.test.ts` | Appeal/independent-review E2E remains partial. |
| C9 collective epistemics | unit_verified | `backend/tests/collective-knowledge.test.ts` | No longitudinal proof. |
| C10 safe evolution | unit_verified | `backend/tests/safe-evolution.test.ts` | No automatic promotion; bounded only. |
| C11 capability expansion | unit_verified | `backend/tests/capability-expansion.test.ts` | No hosted or long-running proof. |
| C12 operating-system loop | not_implemented | none | Outside current evidence. |
| C13 operator plane | not_implemented | none | Outside current evidence. |
| C14 reliability/security/deployment | partial | Batch 04 local staging controls | Hosted remains blocked. |
| C15 completion proof | not_implemented | none | Mission completion not proven. |

Status counts: `unit_verified=11`, `static_only=1`, `partial=1`, `not_implemented=3`.
