# Security Model

Agentco uses fail-closed production secret checks and scoped service identity for governed API mutations.

## Roles

- `agent`: can register claims and read trust.
- `resolver_service`: can resolve claims and read claim audit/trust.
- `reserve_issuer`: can issue and verify credentials, but cannot mutate source claims.
- `human_reviewer`: can mutate institution outputs, reviews, and governance decisions.
- `auditor`: can read audit, verify credentials, and inspect claim audit/trust without mutating.
- `operator`: can operate institution/governance workflows.
- `admin`: manages configuration and can read audit, but does not directly resolve scoring claims.
- `service`: internal service role for governed service-to-service mutations.

Privileged rejections are logged to the security audit surface.

## Production Defaults

`AGENTCO_ENV=production` refuses dev-default API keys, event signing keys, JWT secret, Vault token, reserve signing key, and default database passwords.
