# Production Readiness Module 4: Reputation-Driven Governance and Coalition Routing

Date: 2026-06-26

## Verdict

Completed for the governance/coalition routing slice.

This module removes canned governance and coalition outputs from the backend services. Candidate selection, policy reliability assessment, governance history, and team composition recommendations now derive from live `ReputationLearningService` records. Governance coalition requests now have a backing migration.

## Changes

- Exposed current reputation records through `ReputationLearningService.listReputations()`.
- `GovernanceReputationIntegrationService.formCoalition()` now recruits eligible members by specialization, collaboration score, and reliability.
- `GovernanceReputationIntegrationService.evaluatePolicyProposal()` now computes average voter reliability from recorded proposal votes or current reputation records.
- `GovernanceReputationIntegrationService.getGovernanceHistory()` now reports actual in-process proposals, votes, approvals, rejections, and coalitions.
- `CoalitionFormationService.findCandidates()` now returns real reputation-backed candidates and excludes agents already active in coalitions.
- `CoalitionFormationService.recommendTeamComposition()` now selects a lead and success estimate from available reputation records and persists the recommendation.
- Added `074_governance_coalition_formations.sql` so governance coalition formation writes have a real table.

## Verification

Commands run:

```bash
cd backend && DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco npm run db:migrate
cd backend && npx tsc --noEmit
cd backend && DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco npm test -- tests/governance-coalition-integration.test.ts tests/full-autonomy-integration.test.ts --runInBand --forceExit
```

Results:

- Migration `074_governance_coalition_formations.sql`: applied.
- TypeScript compile: passed.
- Governance/coalition tests: 2 suites passed, 22 tests passed.

## Remaining Scope

This module does not claim full production readiness. Production mode still correctly fails closed without non-development secrets and production deployment posture. Some other subsystems may still contain explicitly marked offline fixtures or disabled historical routes; they must not be counted as production behavior.
