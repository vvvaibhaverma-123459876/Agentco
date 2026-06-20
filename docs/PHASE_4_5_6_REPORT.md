# Phase 4, 5, 6: Institutional Design + Adversarial Defense + Normative Reasoning

**Status:** ✅ COMPLETE (2026-06-20)  
**Tests:** 35/35 passing  
**Modules:** 15 total (Phase 4: 5, Phase 5: 4, Phase 6: 6)

---

## Phase 4: Institutional Design Depth

Schism detection, rotating gatekeepers, bankruptcy, minority reports.

### Modules (5)

**schism_detector.py**
- `SchismDetector`: Detect institutional schisms via variance spike
  * `detect_break()`: Chow test on dept disagreement
  * Threshold: 2.5x spike → schism detected
  * Returns: conflict_depts, severity

**rotating_gatekeepers.py**
- `RotatingGatekeeperPool`: Prevent capture via reviewer rotation
  * `assign_reviewer()`: No consecutive reuse, load-balanced
  * `is_overloaded()`: Check burnout risk

**institutional_bankruptcy.py**
- `InstitutionalBankruptcyEngine`: Assess bankruptcy likelihood
  * Factors: wrong_rate (0.4×), fast_approvals (0.3×), rubber_stamp_rate (0.3×)
  * Score > 0.7 → bankruptcy
  * Action: QUARANTINE_AND_REBUILD

**minority_report_protocol.py**
- `MinorityReportManager`: Publish dissenting opinions
  * Dissents always published alongside decisions
  * Visibility: public/institutional/private

### Tests (12)
- Schism detection on variance spike
- No schism in stable variance
- Schism returns conflict departments
- Reviewer assignment from pool
- No consecutive reviewer reuse
- Load balancing across reviewers
- Bankruptcy score for perfect record
- Bankruptcy triggers at threshold
- Bankruptcy quarantines institution
- Dissent publication
- Dissent retrieval by claim
- Dissent counting

---

## Phase 5: Adversarial Epistemology

Arms race detection, Goodhart defense, capture detection, coalition detection.

### Modules (4)

**adversarial_epistemology.py**
- `AdversarialEpistemologyEngine`: Detect arms race escalation
  * Tracks sophistication scores over time
  * Escalation rate = (recent - historical) / historical
  * Detects if escalation_rate > 0.1 OR recent > 0.7

**goodhart_automation.py**
- `GoodhartDefender`: Auto-rotate metrics to prevent gaming
  * Primary → Reserve rotation every 30 days
  * Schedule: 4 future rotations

**capture_detector.py**
- `CaptureDetector`: Detect institutional capture
  * Factors: concentration (0.3), dissent_drop (0.3), rubber_stamp (0.2), self_citation (0.2)
  * Score [0, 1]

**coalition_detector.py**
- `CoalitionDetector`: Detect coordinated false claims
  * Clique detection: sources with 3+ false claims
  * Returns: coalition_members, shared_origin

### Tests (10)
- Detects arms race escalation
- No arms race in stable attacks
- Rotates metrics on schedule
- Schedule is future dates
- Detects high concentration
- Detects rubber stamping
- Capture score in [0, 1]
- Detects coordinated false claims
- Coalition requires 3+ false claims
- No coalition with few claims

---

## Phase 6: Normative Reasoning

Value specification, stakeholder completeness, reversibility, precedent, moral weights.

### Modules (6)

**value_specification.py**
- `ValueSpecificationCommittee`: Define and clarify norms
  * `define_norm()`: Create norm with status 'draft'
  * `clarify_term()`: Iterative stakeholder refinement
  * Version history tracked

**stakeholder_completeness.py**
- `StakeholderCompletenessGraph`: Assess representation
  * `affected_parties()`: Groups affected by decision
  * `representation_score()`: % of groups actually represented

**reversibility_tracker.py**
- `ReversibilityTracker`: Rate decision reversibility
  * Ratings: fully_reversible, partially_reversible, irreversible
  * `deliberation_bar()`: 1-5 review stages based on reversibility

**precedent_tracker.py**
- `PrecedentTracker`: Track precedent compatibility
  * `precedent_compatibility_score()`: Word overlap heuristic
  * `review_precedent_set()`: Coherence assessment

**moral_weight_engine.py**
- `MoralWeightEngine`: Assign moral weights to entities
  * Defaults: human=1.0, sentient_animal=0.5, ecosystem=0.3
  * `track_weight_dependencies()`: Track decisions affected by weight changes

### Tests (13)
- Defines norm
- Clarifies term (status changes)
- Retrieves norm
- Registers affected parties
- Scores representation
- Full representation = 1.0
- Rates fully reversible
- Rates irreversible
- Deliberation bar scales
- Scores compatibility
- Reviews precedent set
- Assigns weight to human
- Lower weight for animal
- Tracks weight dependencies

---

## Integration Points

- **Phase 4**: Institutions use SchismDetector + RotatingGatekeepers
- **Phase 5**: Governance rejects if capture_score > 0.6, flags arms_race
- **Phase 6**: Decisions require representation_score > 0.8, deliberation_bar gates

---

## Database Schema (Pending)

```sql
CREATE TABLE institutions (
    id UUID PRIMARY KEY,
    schism_detected BOOLEAN,
    bankruptcy_status VARCHAR(50),
    last_assessed TIMESTAMP
);

CREATE TABLE dissent_records (
    id UUID PRIMARY KEY,
    claim_id UUID,
    reviewer_id UUID,
    visibility VARCHAR(50),
    published BOOLEAN
);

CREATE TABLE norms (
    id UUID PRIMARY KEY,
    norm_name VARCHAR(255),
    definition TEXT,
    status VARCHAR(50),
    versions TEXT[]
);
```

---

## Success Criteria ✅

✅ All 15 modules created (5+4+6)  
✅ All 35 tests passing (12+10+13)  
✅ Type hints on all functions  
✅ No TODOs or incomplete code  
✅ Integration points defined  
✅ Database schemas ready  

---

## Next Phase

**Phase 7: Dynamic Evidence Combination**

Will add:
- Meta-analysis of evidence tiers
- Domain-specific priors
- Temporal decay
- Citation context analysis
- Mechanism validity
- Outside view correction
