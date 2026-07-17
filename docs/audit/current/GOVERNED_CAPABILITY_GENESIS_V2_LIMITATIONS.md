# Governed Capability Genesis V2 Limitations

Finding `GCR-002` is recorded as S1 evidence-integrity risk. Genesis V2 remains preserved, but is reclassified as valid protocol execution evidence and protocol/capability separation evidence only. It is invalid as frozen-campaign binding evidence, has incomplete protocol acceptance criteria, and establishes no real capability baseline.

Corrected classifications:

- valid protocol execution evidence
- valid protocol/capability separation evidence
- invalid frozen-campaign binding
- incomplete protocol acceptance criteria
- no real capability baseline

Root causes:

- freeze manifest was not executable-verified
- benchmark hash terminology was ambiguous
- scorer-file hash was reported as scorer-bundle hash
- an empty rubric could enter real capability scoring
- domain correctness evidence could not be produced validly
- protocol acceptance was primarily based on completed statuses

Genesis V1 remains invalidated under `GCR-001`; its withdrawn decision is not restored.
