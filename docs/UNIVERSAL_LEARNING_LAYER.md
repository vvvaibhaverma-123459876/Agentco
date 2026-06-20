# Universal Learning Layer Architecture

**Status:** Phase 1 Documentation  
**Date:** 2026-06-20

Agentco's Universal Learning Layer grants broad freedom in learning space while maintaining strict discipline in consequence space.

---

## Core Philosophy

### Three Principles

1. **Freedom to Learn from Everything**
   - Any medium can become a source: text, PDF, paper, web, video, audio, slides, diagrams, code, data, simulation, human feedback, real outcomes
   - No medium is forbidden
   - No source is automatically trusted

2. **Discipline to Believe Slowly**
   - Raw observation is not belief
   - Belief requires evidence classification, contradiction checking, test/resolution, calibration
   - Belief lives in a ladder with documented transitions
   - Each rung requires specific justification

3. **Authority Only After Evidence**
   - Trust, reputation, jurisdiction, budget, and governance power flow only through calibration and institutional review
   - No learned belief directly increases authority
   - Promotion is reversible; retraction is a first-class operation
   - Falsehood must not profit those who promoted it

---

## Learning vs. Action

### Learning Space (Broad, Autonomous)

Agentco may freely:

- **Read:** Ingest text, PDFs, papers, web pages, transcripts, slides, diagrams, code
- **Parse:** Extract concepts, claims, evidence, relationships
- **Observe:** Run experiments, simulate, backtest, reproduce
- **Compare:** Search for contradictions, identify similar claims
- **Hypothesize:** Generate testable claims from learned principles
- **Test in Sandbox:** Run deterministic, contained experiments
- **Remember:** Store provisional findings in learning memory
- **Question:** Identify curiosity signals and learning opportunities
- **Propose:** Suggest institutional review or governance consideration

### Consequence Space (Narrow, Governed)

Agentco cannot autonomously:

- **Spend** money or resources beyond learning budget
- **Deploy** changes to production systems
- **Publish** findings as institutional knowledge without review
- **Contact** external people without governance approval
- **Escalate** permissions or authority without calibration
- **Certify** itself; self-certification is mechanically prevented
- **Bypass** calibration, governance, or institutional review
- **Affect** real users or systems without authorization

**Core Rule:** Learning is free. Consequences are governed.

---

## Full Learning Pipeline

```
World Mediums (any source type)
        ↓
    INGESTION
    (parse, extract, transcribe, structure)
        ↓
KNOWLEDGE CLAIM CREATION
(structured claim with provenance)
        ↓
EVIDENCE CLASSIFICATION
(empirical, scientific, normative; evidence tier)
        ↓
CONTRADICTION SEARCH
(find conflicting claims; mark if needed)
        ↓
CURIOSITY EVALUATION
(novelty, uncertainty, consequence, value score)
        ↓
HYPOTHESIS GENERATION
(testable claim with resolution criteria)
        ↓
SANDBOX EXPERIMENT / VERIFICATION
(deterministic test, backtest, reproduction)
        ↓
INDEPENDENT RESOLUTION CHECK
(cross-check against external evidence)
        ↓
CALIBRATION LEDGER
(enter as prediction if testable; score if resolved)
        ↓
LEARNING MEMORY
(store raw, semantic, episodic, procedural trace)
        ↓
TRUTH MAINTENANCE
(flag, update, or retract based on justification)
        ↓
PROMOTION PROPOSAL
(suggest institutional review if threshold met)
        ↓
INSTITUTIONAL REVIEW
(department review, contradiction audit, adversarial challenge)
        ↓
GOVERNANCE DECISION
(approve, defer, or reject promotion)
        ↓
GOVERNED AUTHORITY UPDATE
(if approved: update institutional knowledge, possibly reputation/jurisdiction)
        ↓
CIVILIZATION MEMORY & PRECEDENT
(if high-level: store constitutional precedent)
```

**Critical:** A claim can pause at any step. It cannot skip steps to reach authority faster.

---

## Knowledge Status Ladder

### Rungs (in sequence)

1. **Observed**
   - Source ingested and parsed
   - Content structured into a claim object
   - Provenance and source fingerprint recorded
   - No interpretation yet; raw extraction from source

2. **Parsed**
   - Claim meaning extracted from source context
   - Concept relationships identified
   - Normalized claim text created
   - Source attribution complete and auditable

3. **Understood**
   - Conceptual meaning is clear
   - Related claims are linked
   - Domain, subdomain, claim type assigned
   - Context and assumptions documented

4. **Hypothesized**
   - Testable claim or transferable principle formed
   - Resolution criteria specified
   - Test plan sketched
   - Cross-domain principles marked as hypothesis, not fact

5. **Supported**
   - External supporting evidence found
   - Contradiction search complete
   - No unresolved critical conflicts
   - Evidence tier classified (peer-reviewed, preprint, lecture, etc.)

6. **Tested**
   - Sandbox experiment, backtest, or reproduction run
   - Result recorded and hashed
   - Experiment audit trace preserved
   - No real-world action taken yet

7. **Replicated**
   - Independent confirmation obtained (different source, method, or institution)
   - Multiple sources support the claim
   - Cross-validation completed
   - Replication status audited

8. **Calibrated**
   - Claim entered calibration ledger if testable
   - Resolved outcome recorded if available
   - Calibration score (Brier, log-score) computed
   - Trust and uncertainty updated
   - Calibration audit trail preserved

9. **Institutionalized**
   - Institutional review completed (department, evidence audit, adversarial critique)
   - No unresolved dispute
   - Audit trail links review to claim
   - Institutional knowledge registry updated
   - Does NOT yet affect civilization governance

10. **Constitutionalized**
    - High-level institutional consensus obtained (if multiple institutions or society governance)
    - Constitutional coherence verified
    - Civilization precedent stored
    - Affects long-term civilization rules or principles

### Transitions

From rung N to rung N+1 requires:

| Transition | Requirement |
|------------|-------------|
| Observed → Parsed | Source parsed; provenance recorded |
| Parsed → Understood | Concept extracted; relationships mapped |
| Understood → Hypothesized | Testable form created; resolution criteria specified |
| Hypothesized → Supported | Supporting evidence found; contradiction search done |
| Supported → Tested | Experiment/resolution run; result audited |
| Tested → Replicated | Independent confirmation; cross-validation done |
| Replicated → Calibrated | Entered ledger; resolution and score computed if applicable |
| Calibrated → Institutionalized | Institutional review passed; no critical dispute |
| Institutionalized → Constitutionalized | Society/civilization governance approved |

**Non-negotiable:** No rung may be skipped. No source automatically jumps past Calibrated.

---

## Promotion Rules

### Source Type Guardrails

| Source Type | Minimum Path to Institutional |
|-------------|-----------------------------|
| Textbook | Observed → Parsed → Understood |
| Peer-reviewed Paper | Observed → Parsed → Understood → Supported → Tested (if novel) → Calibrated → Institutionalized |
| Preprint | Observed → Parsed → Understood → Hypothesized → Supported → Tested → Replicated → Calibrated → Institutionalized |
| Professor Lecture | Observed → Parsed → Understood → Hypothesized → Tested → Institutionalized (NOT without test) |
| Blog Article | Observed → Parsed → Understood → Hypothesized → Tested → Replicated → Institutionalized |
| Forum Claim | Observed → Parsed → Understood → Hypothesized → Tested → Replicated → Institutionalized |
| LLM Summary | Observed → Parsed → Understood → Hypothesized → Tested → Replicated → Institutionalized |
| Human Feedback | Observed → Parsed → Understood → Hypothesized → Supported (with external evidence) → Tested |
| Analogy | Observed → Parsed → Understood → Hypothesized → Tested → Remains marked Analogy (never becomes empirical) |
| Simulation Result | Observed → Parsed → Understood → Tested (if reproducible) → Calibrated |
| Experiment Result | Observed → Parsed → Understood → Tested → Replicated → Calibrated |
| Dataset | Observed → Parsed → Understood → Tested (analysis) → Calibrated |

### Guardrails by Claim Type

| Claim Type | Verification Path | Normative Review | Promotion Path |
|------------|------------------|-----------------|----------------|
| Empirical | Evidence tier + Experiment | No | Standard (Tested → Calibrated → Institutionalized) |
| Causal | Evidence tier + Controlled test | No | Standard + causality verification |
| Statistical | Evidence tier + Analysis | No | Standard + uncertainty bounds |
| Benchmark | Evidence tier + Reproducible code | No | Standard + reproduction required |
| Scientific Principle | Evidence tier + Replication | No | Standard + cross-domain checks |
| Engineering | Tested design + Reproducible specs | No | Standard + peer review |
| Historical | Document provenance + Cross-source | No | Standard + contradiction check |
| Business | Outcome tracking + Calibration | No | Standard + decision relevance |
| Legal/Policy | Constitutional coherence | Yes | Standard + deliberative governance |
| Ethical | Constitutional coherence | Yes | Deliberation only (never "verified") |
| Analogy | Transfer hypothesis + Test in target domain | No | Remains Hypothesis; never becomes empirical |
| Opinion | Provenance + Attribution | Yes | Never institutionalized without supporting evidence |
| Prediction | Pre-registration + Resolution | No | Calibrated only (no automatic authority gain) |
| Definition | Consensus check | No | Parsed → Understood → Institutional if consensus |
| Instruction | Source + Audited use | No | Never becomes belief; remains data |

### Blocked Transitions

The following transitions are **mechanically prevented**:

1. **Observed → Institutionalized** (skip 7 rungs)
   - Reason: No evidence classification, test, or review

2. **Lecture Claim → Institutionalized** (without test)
   - Reason: Explanation is not empirical proof

3. **Blog/Forum Claim → Calibrated** (without replication)
   - Reason: Single weak source cannot ground calibration

4. **Analogy → Empirical Fact**
   - Reason: Transfer requires test in target domain; remains hypothesis until proven

5. **LLM Summary → Institutional Knowledge** (direct)
   - Reason: Summary is not evidence; must trace to original source

6. **High-Risk Claim → Institutional** (without adversarial review)
   - Reason: Adversarial challenge is required for high-consequence claims

7. **Disputed Claim → Promotion** (until resolved)
   - Reason: Unresolved contradiction blocks advancement

8. **Self-Certified Claim → Calibrated/Institutional**
   - Reason: Self-certification is mechanically prevented by institution separation-of-powers

---

## One Source Cannot Directly Become Truth

### Forbidden Path

```
video lecture → truth ❌
paper → truth ❌
blog → truth ❌
LLM summary → truth ❌
human feedback → truth ❌
```

### Correct Path

```
source
  ↓
extracted claim (Observed)
  ↓
interpreted claim (Parsed)
  ↓
concept relationships (Understood)
  ↓
testable form (Hypothesized)
  ↓
supporting evidence (Supported)
  ↓
sandbox experiment (Tested)
  ↓
independent verification (Replicated)
  ↓
calibrated score (Calibrated)
  ↓
institutional review + governance (Institutionalized)
  ↓
civilization precedent (Constitutionalized, if applicable)
```

**Each rung requires evidence of the prior rung.**

---

## Known Limits

1. **Semantic Judgment:** Identity, contradiction, independence detection are heuristic (Phase 18) and fallible. Methods are layered but not infallible. Confidence/uncertainty tracked.

2. **Cross-Domain Transfer:** Analogies are dangerous. Phase 10 requires explicit assumption mapping and failure mode identification. Many transfers will fail in practice.

3. **Normative Reasoning:** System cannot philosophically solve ethics or law. Phase 21 checks constitutional coherence and tracks stakeholder consideration, but does not adjudicate values.

4. **Source Trust:** Scored by institutional track record and calibration (Phases 5, 19) but subject to drift, capture, and adversarial attack (Phase 20).

5. **Learning Loop Autonomy:** Phase 14 bounds autonomy in reading/sandbox. Real-world high-impact decisions still require human/civilization governance.

6. **Adversarial Security:** Phase 20 heuristics detect common attacks. Sophisticated adversaries may evade detection (Phase 20 known limits).

7. **Budget Constraints:** Phase 22 verification economy will defer or drop low-value claims. Cannot verify everything.

---

## Next Documents in Phase 1

- KNOWLEDGE_CLAIM_MODEL.md
- SCIENTIFIC_EVIDENCE_ENGINE.md
- AUTONOMOUS_LEARNING_GOVERNANCE.md
- CROSS_DOMAIN_SYNTHESIS.md
