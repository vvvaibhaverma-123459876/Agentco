# Provider Trust Boundary Audit

## Scope

Audited provider configuration and execution boundaries for:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_BASE_URL`
- `AGENTCO_PROVIDER_HOST_ALLOWLIST`
- Anthropic-compatible equivalents
- generic HTTP provider configuration

No provider credentials were added. No live provider execution was performed.

## Current Controls

- Missing API key/model/base URL/allowlist fails closed.
- HTTPS is required except explicit local development URLs:
  `http://127.0.0.1` and `http://localhost`.
- Hostname must appear in `AGENTCO_PROVIDER_HOST_ALLOWLIST`.
- Provider request headers redact authorization/key/token values in recorded
  metadata.
- Response-size limits are enforced.
- Timeout and bounded retry settings are provider-specific.
- Retryable HTTP classes are separated from non-retryable `400`.
- Provider preflight does not claim availability unless configuration,
  host allowlist, credentials, reachability and model access are verified.
- Paid/model-access preflight requires explicit
  `AGENTCO_PROVIDER_PREFLIGHT_ALLOW_MODEL_CALL=1`.

## Gaps

`GCR-005`: DNS rebinding/private-range protection is not complete. The current
allowlist is hostname-string based and does not resolve the endpoint to reject
private, link-local or loopback addresses for non-local live-provider hosts.

`GCR-006`: Redirect handling is not explicitly constrained. The current urllib
transport should block redirects or revalidate scheme, host allowlist and
resolved address after each redirect.

These gaps block stronger live-provider trust-boundary confidence. They do not
invalidate Protocol V3 because Protocol V3 uses local mock providers and does
not claim real provider capability.
