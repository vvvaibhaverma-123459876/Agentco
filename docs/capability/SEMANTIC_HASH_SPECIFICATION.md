# Semantic Hash Specification

Batch 09A uses stable semantic hashes for readiness and future real-provider evidence.

Hashes:

- provider configuration hash: canonical JSON of provider configuration with credential values excluded;
- campaign authorization hash: canonical JSON of the authorization artifact;
- Genesis case manifest hash: canonical JSON of case metadata, request hashes and evaluator requirements;
- per-case execution semantic hash: canonical JSON of acceptance-relevant execution evidence;
- evaluator output hash: canonical JSON of evaluator result, scorer identity and rubric identity;
- aggregate capability report hash: canonical JSON of domain metrics, case metrics and decision inputs;
- final decision hash: canonical JSON of decision, predicate map, failures and evidence references.

Evidence must bind to:

- exact source commit;
- exact source tree;
- Protocol V3 identity;
- Genesis V5 campaign identity;
- authorization identity;
- provider/model identity;
- case-manifest hash.

Excluded from semantic hashes:

- timestamps unless they determine authorization expiry or observation windows;
- workflow run IDs;
- temporary paths;
- host-specific runner metadata;
- archive byte ordering.

Substantive protocol, evaluator, provider, case, budget, threshold and decision fields must never be normalized away.
