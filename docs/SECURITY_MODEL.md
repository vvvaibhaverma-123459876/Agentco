# Security Model

## Implemented

- Production startup guard rejects known development defaults.
- `AGENTCO_SERVICE_KEYS_JSON` defines service principals and scopes.
- Requests authenticate with `x-agentco-service-key`.
- Dev mode still supports `x-agentco-api-key` plus `x-agentco-role` compatibility outside production only.
- Production mode fails closed without service keys.
- Scope checks support exact scopes and wildcards such as `read:*`, `governance:*`, and `admin:*`.
- Auth failures are recorded in the in-process security audit event buffer where route middleware runs.

Example:

```json
{
  "resolver-service": {
    "key": "replace-me",
    "scopes": ["prediction:resolve", "evidence:write"]
  },
  "credential-issuer": {
    "key": "replace-me",
    "scopes": ["credential:issue", "credential:verify"]
  },
  "task-dispatcher": {
    "key": "replace-me",
    "scopes": ["task:dispatch", "task:read", "task:cancel"]
  },
  "governance-admin": {
    "key": "replace-me",
    "scopes": ["governance:*", "admin:audit"]
  },
  "auditor": {
    "key": "replace-me",
    "scopes": ["read:*", "audit:read"]
  }
}
```

## Applied Scopes

- Credential issuance: `credential:issue`
- Credential verification: `credential:verify`
- Task dispatch: `task:dispatch`
- Task reads: `task:read`
- Task cancellation: `task:cancel`
- Governance/institution mutations: existing governance and institution scopes
- Override mutation: `governance:mutate`

## Tested

- Missing key rejected.
- Wrong key rejected.
- Valid service key accepted.
- Valid key without scope rejected.
- Wildcard scope accepted.
- Production without service keys fails startup guard.
- Dev fallback does not work in production.
- Auditor cannot mutate.
- Resolver cannot issue credentials.

Run:

```bash
cd backend && npm test -- service-identity.test.ts security.test.ts rbac.test.ts
```

## Not Implemented

- OAuth/OIDC.
- Key rotation.
- Persistent admin audit log for auth decisions.
- Per-route exhaustive scope audit across every prototype route.
- Fine-grained RBAC beyond service scopes.

## Future Work

- Add key identifiers and rotation windows.
- Persist security decisions to append-only audit storage.
- Replace compatibility role-header dev mode when service-key clients exist for all tools.
