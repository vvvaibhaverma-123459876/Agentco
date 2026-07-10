# Phase 9 Notes — Governed Active Agent Protocol

## Objective

Migrate every production-active agent to one enforced runtime contract so active
agents cannot bypass authorization, evidence capture, audit logging, spend
controls, tool policy, or failure recording.

## Runtime Contract

The mandatory active-agent runtime is a governed protocol surface. Python V2
agents use `BaseAgentV2`; TypeScript durable identities use
`DurableExecutionService` with registry task allowlisting, canonical audit
writes, provenance attestation, and workflow finalization.

- Authorization: `BaseAgentV2._authorize_action()` rejects undeclared action
  types before evidence capture or audit.
- Tool allowlisting: `BaseAgentV2.execute_tool()` rejects undeclared tools before
  dispatching to `agents.core.tool_registry.execute_tool()`.
- Budget controls: `SpendGuardrail.check_before_call()` runs before governed
  action execution.
- Evidence capture: `BaseAgentV2._capture_evidence()` records action payload,
  prediction id, and `attempt_id`.
- Audit writes: `BaseAgentV2._write_audit()` writes through the configured audit
  writer. The durable writer is the Phase 8 idempotent `DurableAuditWriter`.
- Finalization: `BaseAgentV2._record_success()` and `_record_failure()` record
  success, blocked, and spend-blocked outcomes.
- Retry identity: `AuditEntryV2.attempt_id` is generated before audit and passed
  to the writer; durable retries reuse that id.

## Inventory

Machine-derived source of truth:

- Manifest: `runtime/base_agent/agent_manifest.py`
- Matrix: `docs/audit/AGENT_PROTOCOL_CONFORMANCE_MATRIX.json`
- Generator/gate: `scripts/generate_agent_conformance_matrix.py --check`

### Active

These 11 agents are registered as runnable and covered by the shared
conformance suite. Nine are Python V2 agents; two are TypeScript durable
identities restricted to `record_observation` for Civilization routing.

| agent | entrypoint | implementation |
|---|---|---|
| `ceo-agent` | `CEOAgentV2.run` | `agents.executive.ceo_agent_v2.CEOAgentV2` |
| `cfo-agent` | `CFOAgentV2.run` | `agents.executive.cfo_agent_v2.CFOAgentV2` |
| `coo-agent` | `COOAgentV2.run` | `agents.executive.coo_agent_v2.COOAgentV2` |
| `coder-agent` | `CoderAgentV2.run` | `agents.engineering.coder_agent_v2.CoderAgentV2` |
| `reviewer-agent` | `ReviewerAgentV2.run` | `agents.engineering.reviewer_agent_v2.ReviewerAgentV2` |
| `devops-agent` | `DevOpsAgentV2.run` | `agents.engineering.devops_agent_v2.DevOpsAgentV2` |
| `pm-agent` | `PMAgentV2.run` | `agents.product.pm_agent_v2.PMAgentV2` |
| `privacy-agent` | `PrivacyAgentV2.run` | `agents.legal.privacy_agent_v2.PrivacyAgentV2` |
| `config-agent` | `ConfigAgentV2.run` | `agents.people_ops.config_agent_v2.ConfigAgentV2` |
| `research-agent` | `CivilizationService -> DurableExecutionService(record_observation)` | TypeScript durable identity |
| `calibration-reasoner` | `CivilizationService -> DurableExecutionService(record_observation)` | TypeScript durable identity |

### Experimental

`SpecialistAgent` and its 17 autonomy role subclasses remain reachable through
`TeamActivationService -> python -m agents.autonomy.<role> -> /execute`, but are
classified experimental rather than production-governed active agents. They are
not advertised as runnable by the production agent registry.

### Deprecated

The archived/no-active-implementation department agents are classified
deprecated and are marked `unsupported` in `backend/src/agent-registry.ts`.
Examples: `architect-agent`, `ux-agent`, `sdr-agent`, `contract-agent`, and
`risk-agent`.

### Test-Only

`test-agent` and `e2e-dispatch-agent` are test-only identities.

## Conformance Coverage

`runtime/tests/test_agent_protocol_conformance.py` runs shared checks across
the active runtime surface. Python V2 agents get behavioral execution checks;
TypeScript durable identities get registry, route, audit, provenance, failure
finalization, and protected-ledger static checks.

- unauthorized execution is rejected
- allowed execution succeeds
- undeclared tools are blocked
- success is audited
- failure is audited
- evidence is recorded
- spend limits are enforced
- `attempt_id` reaches audit entries
- active-agent source has no direct writes to `decision_log` or
  `prediction_ledger`

Current focused verification:

```text
python3.13 -m pytest runtime/tests/test_agent_protocol_conformance.py -q
68 passed
```

Matrix verification:

```text
python3.13 scripts/generate_agent_conformance_matrix.py --check
agent conformance matrix ok
```

## Remaining Bypasses

No production-active agent source writes directly to protected audit or
prediction ledgers. The V1 specialist process family remains experimental and
must be migrated before it can be promoted to production-active status.
