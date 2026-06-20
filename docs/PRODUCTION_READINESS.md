# Production Readiness

Agentco now has a tested calibration-first architecture path through institutions, societies, jurisdiction, disputes, economy, constitution, memory, lifecycle evolution, dashboards, and an offline demo.

Production blockers remain:

- Several new layers are service-level/domain implementations rather than fully durable, live API-integrated workflows.
- Dashboard data is deterministic mock/offline data.
- Governance voting, quorum identity, mediation, economy enforcement, and emergency handling are minimal implementations.
- CI readiness has been added for offline verification, but this branch has not been validated on GitHub Actions yet.
- Docker Compose minimal profile has been parsed and verified, but `make dev-minimal` was not started during Phase 13 or Phase 14.

Security posture:

- Production dev-secret guard remains in place.
- RBAC and scoped identities are tested at the governed API boundary.
- Circular/self-certified resolution is rejected by tests.
- Direct reputation writes are guarded by service-level authorization.
