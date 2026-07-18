# Provider Destination Security

## Findings Closed

- `GCR-005`: provider host allowlisting and resolved-destination enforcement.
- `GCR-006`: redirect handling and credential forwarding boundary.

Both findings are recorded as `resolved_batch_08f` in the governed capability
runtime findings ledger.

## Implemented Controls

Provider destination validation now enforces:

- HTTP(S) URL parsing with malformed authority rejection
- no user-info component
- HTTPS by default
- explicit local-development opt-in for HTTP loopback mock providers
- exact hostname allowlist and explicit `*.` wildcard semantics
- DNS resolution before connection
- validation of every resolved IPv4 and IPv6 address
- rejection of loopback, private, link-local, multicast, reserved and
  unspecified ranges outside explicit local development
- per-attempt URL revalidation before the request
- fail-closed behavior on ambiguous or unresolved destinations

Redirects are disabled by default through a no-redirect opener. A provider
request cannot follow a redirect to an unvalidated destination, and credentials
are not forwarded to redirect targets.

## Test Coverage

Focused provider tests cover:

- success through explicit local mock-provider opt-in
- loopback rejection without local opt-in
- allowlisted host resolving to a private address
- simulated DNS rebinding between validation and request attempt
- malformed URL rejection
- user-info rejection
- non-HTTPS scheme rejection
- redirect rejection

Live-provider Genesis execution remains unauthorized in this batch. These
controls are prerequisite boundary hardening only; they do not establish real
provider capability evidence.
