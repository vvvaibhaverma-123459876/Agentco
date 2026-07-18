# Remediation 08 Governed Capability Runtime

## Scope

Batch 08 adds the first authoritative `agentco-capability-v1` runtime contract for future capability evaluation. It is not a cross-version promotion, hosted staging result, production result, or proof of long-horizon improvement.

## Runtime Contract

The runtime accepts versioned capability requests through both:

- CLI: `python -m agentco_capability execute --request <file>`
- HTTP: `POST /v1/capabilities/execute`

The backend also exposes:

- `POST /v1/capabilities/execute-async`
- `GET /v1/capabilities/attempts/:attemptId`
- `POST /v1/capabilities/attempts/:attemptId/cancel`

The JSON Schemas are:

- `schemas/agentco_capability_request.schema.json`
- `schemas/agentco_capability_response.schema.json`

## Provider Boundary

The deterministic reference provider is classified as `deterministic_protocol_reference`.
It supports protocol, lifecycle, authorization, budget, tool-boundary, storage,
audit and provider-contract validation. It does not perform reasoning, planning,
evidence evaluation, claim grounding, data analysis, software engineering or
cross-domain synthesis as AI capability tasks.

The provider is deterministic, local and benchmark-agnostic. It is suitable for
CI and clean-room protocol validation only. It is not equivalent to a frontier
model or live provider, and it must not be used as a real capability baseline.

## Governance Controls

Controls added in this batch:

- Deny-by-default capability execution unless `capability:execute` is present.
- Live provider adapters require explicit `provider:live` authorization and secret-backed configuration.
- Budget reservation rejects zero provider-call budgets before provider execution.
- Idempotent retries return the existing attempt instead of re-executing.
- Attempt responses include terminal failure states for denied, unsupported and budget-exceeded requests.
- Verified memory is required before memory can influence a response.

## Tools

Safe local tools are exposed only through an allowlist:

- calculator
- structured JSON transformer
- read-only fixture file reader
- SELECT-only fixture SQL
- isolated fixture test runner

The tools enforce workspace boundaries, input restrictions, timeouts and audit-visible results. No unrestricted shell access is provided.

## Persistence

The runtime writes attempts to PostgreSQL when `AGENTCO_CAPABILITY_DATABASE_URL` or `DATABASE_URL` is configured. Otherwise it writes local JSON attempt evidence under `artifacts/capability-runtime/attempts`.

Migration `140_governed_capability_runtime.sql` adds tables for:

- capability attempts
- provider calls
- tool calls
- memory events
- authorization events
- budget ledger entries
- recovery events
- result artifacts

## Genesis Campaign

`make governed-capability-genesis` runs `governed-capability-genesis-v1` after the branch is committed and the tree is clean.

The campaign records:

- exact commit SHA
- protocol version
- benchmark registry hash
- evaluator hash
- request and response artifacts
- internal payload manifest hash
- genesis decision

The campaign decision is one of:

- `GENESIS_BASELINE_ACCEPTED`
- `HOLD_FOR_MORE_EVIDENCE`
- `INVALID_CAMPAIGN`

This is a genesis baseline for future comparisons. It is not a promotion decision and does not claim improvement over another version.

## Hosted Status

Hosted staging remains `BLOCKED / UNVERIFIED`. Live providers remain opt-in and unverified unless real credentials and budget controls are supplied in a governed hosted batch.

## Rollback

Rollback removes:

- `agentco_capability/`
- `schemas/agentco_capability_*.schema.json`
- backend capability routes, service and types
- migration `140_governed_capability_runtime.sql`
- capability runtime tests and workflow
- `governed-capability-genesis` Make target

Existing Batch 07E evidence and PR #27 are unaffected by this stacked branch.
