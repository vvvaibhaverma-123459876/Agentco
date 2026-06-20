# Release Checklist

Release candidate planning requires:

- `make doctor` passes.
- `make smoke` passes offline.
- `make demo` passes offline and exports an audit package.
- `make test` passes.
- `cd backend && npm test && npm run build` passes with production secret guards intact.
- `cd frontend && npm run build` passes.
- Migration runner applies all migrations from a clean database.
- Launch status documents exact failures, limitations, shipped capabilities, and experimental capabilities.
- No paid external LLM keys are required by CI, tests, smoke, or demo.
- No future Society/Civilization feature is marketed as shipped unless executable code, tests, docs, and current branch implementation exist.
