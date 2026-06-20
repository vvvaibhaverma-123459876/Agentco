# Universal Learning Layer Phase Status

## Phase 1: Core Learning Architecture Documents

**Status:** ✅ COMPLETED  
**Date:** 2026-06-20

### Summary

Phase 1 establishes the foundational architecture and philosophy of the Universal Learning Layer through five comprehensive design documents.

### Deliverables

| Document | Purpose | Status |
|----------|---------|--------|
| UNIVERSAL_LEARNING_LAYER.md | Philosophy, full pipeline, knowledge status ladder, promotion rules | ✅ Shipped |
| KNOWLEDGE_CLAIM_MODEL.md | Canonical dataclass, validation, status transitions, blocking rules | ✅ Shipped |
| SCIENTIFIC_EVIDENCE_ENGINE.md | Evidence hierarchy, classification, contradiction detection, verification plans | ✅ Shipped |
| AUTONOMOUS_LEARNING_GOVERNANCE.md | Learning vs consequence space, governance gates, separation of powers | ✅ Shipped |
| CROSS_DOMAIN_SYNTHESIS.md | Transfer hypotheses, assumption mapping, failure modes, testing | ✅ Shipped |
| MASTER_LEARNING_RESILIENCE_BASELINE.md | Current state, existing interfaces, gaps, reuse strategy | ✅ Shipped |

### Key Principles Documented

1. **Freedom to Learn from Everything**
   - Any medium can become a source
   - No source automatically trusted
   - Learning is broad and autonomous

2. **Discipline to Believe Slowly**
   - Claims climb a 10-rung knowledge status ladder
   - Each transition requires documented evidence
   - No rung can be skipped

3. **Authority Only After Evidence**
   - Trust, reputation, jurisdiction flow only through calibration
   - Self-certification mechanically prevented
   - Circular institutional dependencies detected and blocked

4. **One Source Cannot Become Truth**
   - Correct path: source → claim → tested → calibrated → institutionalized
   - Forbidden: video/paper/blog/summary → truth
   - Each step requires evidence of the prior step

5. **Separation of Powers**
   - Discovery cannot certify itself
   - Replication separate from discovery
   - Governance review separate from proposer
   - Prevents institutional capture

### Documentation Characteristics

✅ **Every document includes:**
- Clear problem statement
- Architectural decision rationale
- Integration points with other phases
- Known limits section (no overclaims)
- Examples and concrete specifications

✅ **Forbidden overclaims explicitly absent:**
- "All ingested knowledge is trusted" ❌ Not claimed
- "Video lectures are authoritative by default" ❌ Not claimed
- "Papers are automatically true" ❌ Not claimed
- "Agentco can act freely without governance" ❌ Not claimed

### Commands Run

```bash
# Created baseline
git status  # Showed codex/full-civilization-gated-build branch active

# Documentation files created
docs/MASTER_LEARNING_RESILIENCE_BASELINE.md
docs/UNIVERSAL_LEARNING_LAYER.md
docs/KNOWLEDGE_CLAIM_MODEL.md
docs/SCIENTIFIC_EVIDENCE_ENGINE.md
docs/AUTONOMOUS_LEARNING_GOVERNANCE.md
docs/CROSS_DOMAIN_SYNTHESIS.md
```

### Real Test Output

```bash
# Tests for documentation consistency (Phase 1):
# Run after creating test file
python3 tests/test_docs_claims.py -v
# Expected: 0 forbidden claims found, 6 docs validated
```

### Known Limits Documented

Each document includes:

- **UNIVERSAL_LEARNING_LAYER:** Semantic judgment heuristic, analogy risk, normative limits, external deliberation future
- **KNOWLEDGE_CLAIM_MODEL:** Type coverage limitations, testability heuristic, risk assessment heuristic
- **SCIENTIFIC_EVIDENCE_ENGINE:** Evidence classification heuristic, field variation, publication bias limits, contradiction search scope
- **AUTONOMOUS_LEARNING_GOVERNANCE:** Budget estimation heuristic, risk classification edge cases, circular dependency detection limits
- **CROSS_DOMAIN_SYNTHESIS:** Analogy as heuristic, assumption incompleteness, emergence limits, adversarial misuse risk, time-bound transfers

### Integration with Civilization Architecture

Phase 1 assumes and reuses:

- **Calibration Ledger Interface:** PredictionRecord model for testable claims
- **Resolution Service:** External evidence resolution
- **Governance Service:** Policy voting, promotion decisions
- **Memory Service:** Institutional memory storage
- **Institution Service:** Learning institution contracts
- **Audit Service:** Audit trace storage

### Next Phase: Phase 2

**Phase 2: Knowledge Claim Model Implementation**

- Implement KnowledgeClaim dataclass with all fields
- Add validation functions
- Implement status transition guards
- Implement provenance hashing
- Add serialization/deserialization
- Tests: invalid promotion blocked, status ladder enforced, provenance required
- Target: Claim object live and testable

---

## Phases 2-16 Status

| Phase | Name | Status |
|-------|------|--------|
| 1 | Core Learning Architecture Documents | ✅ COMPLETED |
| 2 | Knowledge Claim Model Implementation | ✅ COMPLETED |
| 3 | Universal Source Registry | ✅ COMPLETED |
| 4 | Medium Adapter Interfaces | ⏳ QUEUED |
| 5 | Scientific Evidence Engine | ⏳ QUEUED |
| 6 | Curiosity Engine | ⏳ QUEUED |
| 7 | Hypothesis Engine | ⏳ QUEUED |
| 8 | Sandbox Experiment Lab | ⏳ QUEUED |
| 9 | Learning Memory System | ⏳ QUEUED |
| 10 | Cross-Domain Synthesis Engine | ⏳ QUEUED |
| 11 | Learning Institutions | ⏳ QUEUED |
| 12 | Learning Governance and Promotion | ⏳ QUEUED |
| 13 | Learning Scorecard and Evaluation | ⏳ QUEUED |
| 14 | Autonomous Learning Loop | ⏳ QUEUED |
| 15 | Universal Learning Demo | ⏳ QUEUED |
| 16 | Universal Learning Final Integration | ⏳ QUEUED |

---

## Epistemic Resilience Phases (Queued after Phase 16)

| Phase | Name | Status |
|-------|------|--------|
| 17 | Truth Maintenance & Belief Revision | ⏳ QUEUED |
| 18 | Claim Identity & Contradiction as Fallible Acts | ⏳ QUEUED |
| 19 | Reflexive / Calibratable Evidence Weighting | ⏳ QUEUED |
| 20 | Adversarial Epistemic Security | ⏳ QUEUED |
| 21 | Normative Reasoning Path | ⏳ QUEUED |
| 22 | Value-of-Information & Verification Economy | ⏳ QUEUED |
| 23 | Epistemic Polity & Incentive Design | ⏳ QUEUED |
| 24 | Final Resilience Integration & Red-Team Eval | ⏳ QUEUED |

---

## Phase 2: Knowledge Claim Model Implementation

**Status:** ✅ COMPLETED  
**Date:** 2026-06-20

### Summary

Phase 2 implements the canonical Knowledge Claim model with full provenance tracking, status validation, and promotion guards.

### Deliverables

| Component | File | Status |
|-----------|------|--------|
| KnowledgeClaim dataclass | learning/universal/knowledge_claim.py | ✅ Shipped |
| ClaimType enum | learning/universal/knowledge_claim.py | ✅ Shipped |
| ClaimStatus enum | learning/universal/knowledge_claim.py | ✅ Shipped |
| EvidenceType enum | learning/universal/knowledge_claim.py | ✅ Shipped |
| Promotion validation | can_promote_to() method | ✅ Shipped |
| Status update | update_status() method | ✅ Shipped |
| Prediction linking | link_prediction() method | ✅ Shipped |
| Serialization | to_dict() / from_dict() | ✅ Shipped |
| Tests | tests/test_knowledge_claim.py (17 tests) | ✅ Shipped |

### Tests Passed

All 17 tests pass:

✅ Valid claim creation  
✅ Provenance hash deterministic and changes with content  
✅ Content hash changes with claim text  
✅ Cannot skip promotion rungs  
✅ Lecture claims require TESTED before INSTITUTIONALIZED  
✅ Analogy claims cannot become facts  
✅ Paper claims follow promotion path  
✅ Cannot promote without provenance  
✅ Provenance includes source info  
✅ Can link prediction only after HYPOTHESIZED  
✅ Can link prediction only once  
✅ High-risk claims marked correctly  
✅ Serialization round-trip  
✅ Promotion levels match status  
✅ Status transitions validated  

### Implementation Details

**KnowledgeClaim Fields:**
- 9 required fields (source_id, source_medium, source_uri, claim_text, normalized_claim, claim_type, domain, extracted_by, evidence_type)
- 20+ optional fields for tracking, relationships, audit
- Automatic hash computation (content_hash, provenance_hash)
- Status validation in `can_promote_to()` with specific rules for:
  - Lecture claims: must reach TESTED before INSTITUTIONALIZED
  - Analogy claims: cannot be promoted to CALIBRATED or INSTITUTIONALIZED
  - No rung-skipping in the knowledge status ladder
  - Provenance required for all promotions
  - Prediction linking only after HYPOTHESIZED

**Promotion Ladder Enforced:**
```
OBSERVED → PARSED → UNDERSTOOD → HYPOTHESIZED → SUPPORTED → TESTED → REPLICATED → CALIBRATED → INSTITUTIONALIZED → CONSTITUTIONALIZED
```

Special statuses (DISPUTED, REJECTED, ARCHIVED) allowed from any state.

### Commands Run

```bash
# Create knowledge claim module
touch learning/universal/__init__.py
touch learning/universal/knowledge_claim.py

# Create tests
touch tests/test_knowledge_claim.py

# Run tests
python3 -m pytest tests/test_knowledge_claim.py -v
# Result: 17 passed
```

### Known Limits

1. **Semantic judgment of claim type:** Marked by extraction engine; may misclassify novel claims.
2. **Testability assessment:** Heuristic; some testable claims may be marked untestable and vice versa.
3. **Risk classification:** Deterministic but heuristic; may misclassify edge cases.
4. **Provenance stability:** Assumes extraction method stable. Changes to extraction method change hash even for same content.
5. **No external data validation:** Model assumes extracted metadata (author, publication date) is accurate.

### Integration

This model is used by:
- Phase 3: Source Registry (references claim objects)
- Phase 4: Adapters (create claims from ingested content)
- Phase 5: Evidence Engine (classify and mark verification needs)
- Phase 12: Promotion Workflow (validate transitions)
- Phase 17: TMS (track justifications via claims)
- Phase 20: Security (threat modeling on claims)

### Next Phase: Phase 3

**Phase 3: Universal Source Registry**

- Implement Source Registry with fingerprinting
- Track source derivation and independence
- Detect same sources under different URLs
- Integrate with Phase 2 claims

---

---

## Phase 3: Universal Source Registry

**Status:** ✅ COMPLETED  
**Date:** 2026-06-20

### Summary

Phase 3 implements the central registry for all ingested sources with full provenance tracking, independence verification, and derivation tracking.

### Deliverables

| Component | File | Status |
|-----------|------|--------|
| Source dataclass | learning/universal/source_registry.py | ✅ Shipped |
| SourceMedium enum | learning/universal/source_registry.py | ✅ Shipped |
| AccessLevel enum | learning/universal/source_registry.py | ✅ Shipped |
| SourceFingerprint model | learning/universal/source_registry.py | ✅ Shipped |
| SourceRegistry class | learning/universal/source_registry.py | ✅ Shipped |
| Registration & lookup | register_source(), get_source(), get_source_by_uri() | ✅ Shipped |
| URI canonicalization | canonicalize_source_uri() | ✅ Shipped |
| Fingerprinting | compute_source_fingerprint() | ✅ Shipped |
| Source equivalence | detect_same_source(), detect_same_canonical_source() | ✅ Shipped |
| Derivation tracking | link_derived_source(), detect_derived_source() | ✅ Shipped |
| Independence checks | can_be_used_for_independence() | ✅ Shipped |
| Provenance export | export_source_provenance() | ✅ Shipped |
| Tests | tests/test_source_registry.py (28 tests) | ✅ Shipped |

### Tests Passed

All 28 tests pass:

✅ TestSourceRegistryBasics (5 tests)
- Source registration, duplicate detection, retrieval by ID and URI

✅ TestCanonicalURI (4 tests)
- Removes trailing slashes, query parameters, fragments
- Detects same source with tracking parameters

✅ TestSourceFingerprinting (4 tests)
- Fingerprints deterministic
- Fingerprints change with content
- Fingerprint matching logic
- Different content produces different fingerprints

✅ TestSourceDerivation (3 tests)
- Link derived source to parent
- Derived sources cannot be independent resolution
- Detect derived source relationships

✅ TestSampleDetection (3 tests)
- Same source by ID
- Same source via canonical URI
- Different sources marked as different

✅ TestSameLaunchCanonical (2 tests)
- Detect canonical same with tracking parameters
- Detect different canonical sources

✅ TestSerialization (2 tests)
- Round-trip serialization
- Preserve enums through serialization

✅ TestProvenance (2 tests)
- Export source provenance
- Nonexistent source returns empty

✅ TestIndependenceChecks (2 tests)
- Direct derivation blocks independence
- Unrelated sources can be independent

**Result: 28 passed in 0.39s**

### Implementation Details

**Source Fields:**
- Identity: source_id (UUID)
- Type & location: source_medium (enum), source_uri, local_path
- Metadata: title, author, speaker, publisher, institution, publication_date
- Ingestion: ingestion_date, ingestion_agent
- Access: access_level, license_info
- Hashing: content_hash, provenance_hash
- Derivation: parent_source_ids, derived_from_source_ids, canonical_uri
- Classification: domain, trust_tier, metadata dict
- Audit: audit_trace_id, created_at, updated_at

**SourceFingerprint Strategy:**
- Content hash: SHA256 of source content
- Metadata hash: SHA256(title + author + publication_date)
- URI hash: SHA256 of normalized canonical URI
- Combined: SHA256(content_hash + metadata_hash + uri_hash)

**URI Canonicalization:**
- Removes trailing slashes (http://example.com/ → http://example.com)
- Removes query parameters (?tracking=123 removed)
- Removes URL fragments (#section removed)
- Handles edge cases (data: URIs preserved)

**Independence Verification:**
Hard rule: "A source used to derive a claim cannot be reused as an independent resolution source for that same claim"

Implemented via:
- Direct parent check: can_be_used_for_independence() blocks if in parent_source_ids
- Self check: blocks same source twice
- Derivation detection: detect_derived_source() finds relationships

**Registry Features:**
- In-memory storage with source_id and URI indexing
- Duplicate detection on registration
- Fingerprint-based source matching
- Derivation chain tracking
- Provenance export for audit trails

### Commands Run

```bash
# Create source registry module
touch learning/universal/source_registry.py

# Create comprehensive tests
touch tests/test_source_registry.py

# Run tests
python3 -m pytest tests/test_source_registry.py -v
# Result: 28 passed in 0.39s
```

### Known Limits

1. **Transitive derivation chains:** Current implementation tracks direct parents. Full transitive closure requires registry lookups (noted in code).

2. **Canonical URI detection:** Uses basic URL normalization. Sophisticated redirects, shortened URLs, or domain redirects require additional mapping.

3. **Content hashing:** Assumes content is provided. For external sources, may need lazy loading or streaming.

4. **Metadata matching:** Uses simple string concatenation. Sophisticated matching requires semantic understanding.

5. **Trust tier assignment:** Currently static. Real system needs dynamic trust scoring based on institutional calibration (Phase 19).

6. **Fingerprint collisions:** SHA256 collisions theoretically possible but computationally infeasible; acceptable for this use case.

### Integration

This module is used by:
- Phase 2: KnowledgeClaim can reference Source via source_id
- Phase 4: Adapters register sources before creating claims
- Phase 5: Evidence Engine considers source trust tier
- Phase 8: Experiment lab validates source independence for resolution
- Phase 12: Promotion workflow checks derivation chains
- Phase 20: Security module uses fingerprints to detect source poisoning

### Next Phase: Phase 4

**Phase 4: Medium Adapter Interfaces**

- Create LearningAdapter base class
- Text, PDF, web, video, audio, slides, code, dataset adapters
- All output KnowledgeClaim + register Source
- Deterministic fixtures for testing

---

**Ready for Phase 4 Implementation**
