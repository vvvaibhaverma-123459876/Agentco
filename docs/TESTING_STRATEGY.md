# Testing Strategy

Agentco tests are grouped by gate:

- Calibration and reserve tests verify pre-registration, independent resolution, trust scoring, tamper evidence, credentials, and audit behavior.
- Civilization tests verify Institution, Society, Jurisdiction, Judiciary, Economy, Constitution, Memory, and Lifecycle invariants.
- Backend Jest tests verify governed API, RBAC, security guards, audit, memory, events, and override queue behavior.
- Frontend build verifies the App Router dashboard surface and typed client compilation.
- Offline smoke and demo verify runnability without paid LLM keys or external services.

Primary local gate:

```bash
make test
```

Focused runnability gates:

```bash
make doctor
make smoke
make demo
```
