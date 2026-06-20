# Scientific Evidence Engine

**Status:** Phase 1 Documentation  
**Date:** 2026-06-20

The Scientific Evidence Engine classifies evidence strength and identifies what verification is required before a scientific claim can be trusted.

---

## Evidence Hierarchy

The hierarchy ranks evidence types from strongest to weakest:

```
1. Formal Proof
2. Raw Dataset + Reproducible Code (with full audit)
3. Replicated Peer-Reviewed Study (multiple independent reproductions)
4. Meta-Analysis / Systematic Review
5. Textbook Consensus (across multiple textbooks, time-stable)
6. Single Peer-Reviewed Paper (in reputable venue)
7. Preprint (peer review pending or not submitted)
8. Expert Lecture / Professor Notes (explanation, not proof)
9. Blog Article / Science Explainer (public education)
10. Forum Claim (community discussion)
11. LLM Summary (synthesis without direct source)
```

**Important:** This is a **prior, not an axiom** (Phase 19 makes it reflexive and recalibratable).

---

## Classification Engine

For each scientific claim extracted, the engine must:

### 1. Determine Field/Domain

- Physics, Chemistry, Biology
- Computer Science, Mathematics
- Medicine, Pharmacology
- Psychology, Neuroscience
- Economics, Business
- Law, Policy
- History, Archaeology
- Social Science
- Engineering, Technical
- Other

### 2. Extract Method Description

- Literature review based on:
  - Original study? Yes/No
  - Original data? Yes/No
  - Original code? Yes/No
  - Original experiment? Yes/No
- Study design (randomized controlled trial, observational, simulation, etc.)
- Sample size if available
- Duration
- Reproducibility factors (open data, open code, etc.)

### 3. Classify Evidence Tier

Use deterministic rules:

```python
def classify_evidence(claim_metadata: dict) -> EvidenceType:
    """
    Deterministic classification based on claim metadata.
    """
    
    # Formal proof
    if claim_metadata.get("is_mathematical_proof"):
        return EvidenceType.FORMAL_PROOF
    
    # Raw dataset + reproducible code (highest empirical)
    if claim_metadata.get("has_raw_data") and claim_metadata.get("has_reproducible_code"):
        return EvidenceType.RAW_DATASET
    
    # Replicated peer reviewed
    if (claim_metadata.get("peer_reviewed") and 
        claim_metadata.get("replication_count", 0) >= 3):
        return EvidenceType.REPLICATED_PEER_REVIEWED_STUDY
    
    # Meta-analysis or systematic review
    if claim_metadata.get("is_meta_analysis") or claim_metadata.get("is_systematic_review"):
        return EvidenceType.META_ANALYSIS
    
    # Textbook consensus
    if claim_metadata.get("in_multiple_textbooks", 0) >= 2 and claim_metadata.get("stable_years", 0) > 5:
        return EvidenceType.TEXTBOOK
    
    # Single peer-reviewed
    if claim_metadata.get("peer_reviewed"):
        return EvidenceType.SINGLE_PEER_REVIEWED_PAPER
    
    # Preprint
    if claim_metadata.get("is_preprint"):
        return EvidenceType.PREPRINT
    
    # Expert lecture
    if claim_metadata.get("source_medium") == "video" and claim_metadata.get("is_expert_lecture"):
        return EvidenceType.EXPERT_LECTURE
    
    # Blog/explainer
    if claim_metadata.get("source_medium") in ["blog", "webpage"]:
        return EvidenceType.BLOG_ARTICLE
    
    # Forum/discussion
    if claim_metadata.get("source_medium") == "forum":
        return EvidenceType.FORUM_CLAIM
    
    # LLM summary
    if claim_metadata.get("generated_by_llm"):
        return EvidenceType.LLM_SUMMARY
    
    # Simulation result
    if claim_metadata.get("source_medium") == "simulation":
        return EvidenceType.SIMULATION_RESULT
    
    # Experiment result
    if claim_metadata.get("source_medium") == "experiment":
        return EvidenceType.EXPERIMENT_RESULT
    
    return EvidenceType.UNKNOWN
```

### 4. Extract Specific Evidence Attributes

For each scientific claim:

| Attribute | Type | Meaning | Example |
|-----------|------|---------|---------|
| sample_size | int | Statistical N | 500 participants |
| effect_size | float | Cohen's d or similar | 0.45 |
| confidence_interval | tuple | 95% CI | (0.35, 0.55) |
| p_value | float | Statistical significance | 0.03 |
| replication_count | int | How many independent reproductions | 5 |
| study_duration | str | How long the study ran | "24 months" |
| external_validity | str | How well generalizable | "limited to undergrads" |
| open_data | bool | Is data publicly available | true |
| open_code | bool | Is code publicly available | true |
| conflicts_of_interest | str | Funding/affiliation concerns | "funded by Company X" |
| date_published | datetime | Publication date | 2023-06-15 |
| citations | int | How many times cited | 342 |
| h_index | int | Author's h-index if known | 18 |

### 5. Assign Verification Requirements

Based on evidence tier and domain:

| Evidence Tier | Verification Requirement | Priority |
|---------------|-------------------------|----------|
| Formal Proof | Independent verification of proof steps | High |
| Raw Dataset + Code | Re-run code on data; verify statistical analysis | High |
| Replicated Peer-Reviewed | Verify replication studies; check for contradictions | Medium |
| Meta-Analysis | Check included studies; verify synthesis methods | Medium |
| Textbook Consensus | Spot-check a few textbook entries | Low |
| Single Peer-Reviewed | Replication required before high-consequence use | High |
| Preprint | Replication strongly recommended; track publication status | High |
| Expert Lecture | Verify with textbooks or original papers | Medium |
| Blog Article | Find original research; verify independently | High |
| Forum Claim | Treat as hypothesis; requires evidence | Very High |
| LLM Summary | Find original sources; verify accuracy | High |
| Simulation Result | Verify code, assumptions, boundary conditions | Medium |
| Experiment Result | Replication; check assumptions | Medium |

### 6. Mark Contradictions & Limitations

For each claim:

- Search for contradicting claims in the Source Registry
- Note any acknowledged limitations in the original source
- Flag external validity concerns
- Mark domain-specific assumptions

### 7. Create Verification Plan

If `verification_required`, suggest next steps:

```python
@dataclass
class VerificationPlan:
    """What to do next to verify a claim."""
    
    claim_id: str
    verification_type: str  # replication|reproduction|meta_analysis_check|peer_review|independent_test|benchmarking
    estimated_cost: str  # low|medium|high
    time_estimate: str  # hours|days|weeks
    required_expertise: str  # domain area
    success_criteria: str  # how to know verification succeeded
    responsible_institution: Optional[str]  # Which learning institution should handle this
```

---

## Contradiction Detection

For each scientific claim, attempt to:

1. **Find contradicting claims** in the Source Registry
2. **Classify contradiction type:**
   - Direct negation: "A is true" vs "A is false"
   - Mutually exclusive: "B is the cause" vs "C is the cause"
   - Quantitative conflict: "60% agree" vs "40% agree"
   - Scope conflict: "Always true" vs "True only in Domain X"
   - Conditional conflict: "If X then Y" vs "If X then not Y"
   - Incomparable: Cannot determine if these conflict

3. **Mark status if contradicted:**
   - `status = DISPUTED` if active contradiction exists
   - Link both claims to each other
   - Store contradiction reason and strength in audit trail

---

## Scientific Principle Extraction

For replicable, evidence-based principles:

1. Extract the core principle (e.g., "learning improves with spaced repetition")
2. Identify scope and domain (psychology/education; human memory)
3. Note qualifications ("for verbal material")
4. Mark transfer candidates (could apply to: institutional learning, model training, etc.)
5. Link to supporting papers/studies
6. Estimate cross-domain applicability

---

## Replication Marking

When a claim can be replicated or reproduced:

```python
@dataclass
class ReplicationMark:
    claim_id: str
    reproducible: bool  # Can code/data be re-run?
    reproducibility_reason: str  # Why or why not
    replication_level: str  # full|partial|cannot
    required_for_promotion: bool
    estimated_time: str
    required_resources: str  # Compute, equipment, expertise
    original_study_link: str
```

---

## Domain-Specific Guidance

### Physics

- Formal proofs highly valued
- Empirical validation via experiment required for novel claims
- Simulation results mark separately
- Contradictions with established principles flag immediately

### Medical / Pharmacology

- Randomized controlled trials (RCT) required for health claims
- Small sample sizes flagged
- Conflicts of interest with pharmaceutical companies noted
- Population specificity (age, sex, genetics) critical

### Computer Science / Benchmarking

- Reproducible code is essential
- Hardware/software version must be recorded
- Benchmark claims compared against standard suites
- Performance claims mark with specific conditions (cache config, input size)

### Psychology / Social Science

- Replication crisis awareness: single study insufficient
- Preregistration important for pre-hoc hypotheses
- Publication bias checked
- Effect sizes and confidence intervals critical

### Business / Economics

- Time-series stability checked
- Market/policy regime changes noted
- Causality claims require causal identification
- Backtesting over out-of-sample data important

---

## Known Limits

1. **Evidence Tier Heuristic:** Classification is deterministic but based on metadata heuristics, not semantic understanding. A paper claimed to be peer-reviewed may not actually be.

2. **Field-Specific Variation:** Evidence hierarchy prioritizes formal proof and RCTs, which are more valued in hard sciences. Other fields (qualitative research, law, history) have different standards.

3. **Publication Bias:** Cannot detect unpublished contradictions or failed replications.

4. **Metadata Extraction:** Assumes extracted metadata (peer_reviewed, has_data, etc.) is accurately extracted from the source. Phase 4 adapters determine extraction accuracy.

5. **Contradiction Search:** Limited to Source Registry. Cannot search global scientific literature.

6. **Cross-Domain Principle Transfer:** Marked but not validated by this engine. Requires Phase 10 (Cross-Domain Synthesis) for transfer testing.

7. **Temporal Dynamics:** Does not automatically detect when evidence becomes stale (e.g., "safe amount of X" changes over decades).

---

## Integration with Phases

- **Phase 4 Adapters:** Extract evidence attributes during ingestion
- **Phase 5 (this phase):** Classify evidence tier and mark verification needs
- **Phase 6 Curiosity Engine:** Uses verification requirements to prioritize learning
- **Phase 7 Hypothesis Engine:** Links hypotheses to required verification
- **Phase 8 Experiment Lab:** Executes verification plans
- **Phase 18 Judgment Engine:** Contradiction verdicts cross-check with this engine
- **Phase 19 Evidence Priors:** Scientific Evidence classifications feed into prior recalibration

---

## Next: Phase 5 Implementation

Phase 5 will implement:

- `classify_scientific_evidence()` function
- `create_verification_plan()` generator
- Contradiction detection and marking
- Replication assessment
- Tests with scientific fixture data
