# Cross-Domain Synthesis: Learning Across Disciplines

**Status:** Phase 1 Documentation  
**Date:** 2026-06-20

Agentco learns from every domain but must not naively transfer insights across domains. Cross-domain synthesis makes transfer hypotheses explicit and testable.

---

## Core Challenge

Deep knowledge in one domain sometimes transfers powerfully to another:

- **Biology → Institutional Evolution:** Species adapt to environmental pressure; institutions adapt to governance pressure
- **Physics → Resource Constraints:** Conservation of energy; conservation of capital
- **Law → Governance & Precedent:** Stare decisis (case law precedent); civilization constitutional precedent
- **Markets → Incentives:** Price discovery; reputation discovery
- **Software → Modularity:** Encapsulation and interfaces; institutional separation of powers
- **History → Collapse Prevention:** Pattern recognition from civilizational failures; design to avoid them
- **Ecology → System Balance:** Predator/prey cycles; institutional power cycles
- **Security → Adversarial Design:** Red-teaming; adversarial critique (Phase 20)

But transfer is also a primary failure mode:

- Biological evolution doesn't optimize for justice or fairness
- Physical conservation laws don't apply to information
- Legal precedent from one jurisdiction may not fit another culture
- Market incentives can misalign with public welfare
- Software modularity doesn't guarantee institutional separation
- Historical patterns can mislead if context is different
- Ecological cycles scale poorly to human timescales
- Security techniques can be gamed in new domains

---

## Transfer Hypothesis Model

When a principle from Domain A might transfer to Domain B:

```python
@dataclass
class CrossDomainTransfer:
    """A hypothesis that a principle transfers across domains."""
    
    transfer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Source
    source_domain: str  # Domain principle originates from
    source_principle_id: str  # ID of the principle/claim
    source_principle_text: str  # What is the principle?
    
    # Target
    target_domain: str  # Domain we want to apply principle to
    extracted_principle: str  # Abstract core of the principle
    transfer_hypothesis: str  # Concrete application in target domain
    analogy_claim: str  # The analogy itself
    
    # Explicit Assumptions (Critical)
    assumptions: List[str] = field(default_factory=list)
    # Example: 
    #   "Predator-prey dynamics exist in both ecosystems and markets"
    #   "Feedback loops operate similarly in biology and institutions"
    #   "Competition drives improvement in both domains"
    
    # Failure Modes (Mandatory)
    failure_modes: List[str] = field(default_factory=list)
    # Example:
    #   "Prey strategies (camouflage) don't translate to market entry"
    #   "Biological extinction is irreversible; institutional recovery is possible"
    #   "Evolution operates over millions of years; markets change in weeks"
    
    # Test Plan
    proposed_test: str  # How to test in target domain?
    resolution_criteria: str  # What counts as success/failure?
    
    # Confidence
    confidence: float = 0.3  # Initials low (transfer is risky)
    uncertainty: float = 0.7
    
    # Status
    status: str = "hypothesis"  # hypothesis | tested | supported | rejected | archived
    linked_experiment_id: Optional[str] = None
    
    # Audit
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "synthesis_engine"
```

---

## Principle Extraction

To extract a transferable principle:

### 1. Identify the Core Insight

From a domain-specific claim, distill the abstract principle:

| Domain Claim | Abstract Principle |
|--------------|-------------------|
| "Large predators regulate prey populations" | "Power imbalance creates feedback loop" |
| "Markets clear through price discovery" | "Decentralized signals converge to equilibrium" |
| "Code modularity reduces coupling" | "Interface separation reduces dependencies" |
| "Precedent constrains current decisions" | "History anchors present choices" |
| "Mutation enables adaptation" | "Random variation creates option value" |

### 2. Map Domain-Specific Elements to Abstract Elements

Create an abstraction layer:

```
Predator-Prey (Biology)
  predator ← → abstract: "power holder"
  prey ← → abstract: "subordinate entity"
  hunt-reproduce cycle ← → abstract: "power cycle"
  environmental resource ← → abstract: "shared resource"

Market Entry (Business)
  incumbent ← → abstract: "power holder"
  entrant ← → abstract: "subordinate entity"
  market cycle ← → abstract: "power cycle"
  customer demand ← → abstract: "shared resource"

Institutional Power (Governance)
  dominant institution ← → abstract: "power holder"
  emerging institution ← → abstract: "subordinate entity"
  governance cycle ← → abstract: "power cycle"
  authority budget ← → abstract: "shared resource"
```

### 3. State the Transfer Hypothesis

"If the abstract principle holds in the source domain,  
and the target domain's elements map onto the abstract elements,  
then the principle should hold in the target domain (with caveats)."

---

## Assumption Mapping (Critical)

Every cross-domain transfer rests on **hidden assumptions**. Make them explicit:

### Common Assumptions

| Assumption | Predator-Prey | Market Entry | Institution |
|-----------|---------------|--------------|------------|
| Entities have local optima drives | Yes (survival) | Yes (profit) | Questionable (mission/power trade-off) |
| Feedback loops operate similarly | Yes | Yes | Partial (governance breaks feedback) |
| Timescales are comparable | No (generations) | No (quarters) | Variable |
| Resource scarcity is real | Yes (food) | Partial (capital fungible) | Complex (authority fungible) |
| Actors are rational | No (instinct) | Partial | No (bounded rationality) |
| No external intervention | No (humans hunt) | No (regulation) | No (court/revolution) |
| System is stable | No (extinction risk) | Partial (disruption risk) | No (regime change risk) |

**Document every assumption.** The transfer fails if assumptions are false.

---

## Failure Mode Analysis

Before proposing a transfer, enumerate ways it could fail:

### Categories of Failure

| Failure Type | Example | Mitigation |
|-------------|---------|-----------|
| Assumption Violation | Institutions don't optimize for individual benefit | Test in bounded institutional context first |
| Timescale Mismatch | Biological cycles are millennia; governance is years | Adjust parameters for different timescale |
| Scope Limitation | Predator-prey works in isolated populations; markets are global | Test at matching scope |
| Normative Misalignment | Predation is amoral; institutional power has justice requirements | Add normative constraints to model |
| Feedback Direction | Positive feedback in market (rich get richer); should be negative (dampen) | Invert feedback; test |
| Boundary Condition | Open vs closed systems operate differently | Specify boundary conditions explicitly |
| Emergence | New properties at scale (individual level doesn't predict collective) | Model emergence explicitly |
| Human Agency | Humans resist or subvert models; animals don't | Account for deliberate subversion |

### Critical Failure Modes

These make transfer **inadvisable** without extensive testing:

1. **Normative Claims from Descriptive Principles**
   - "Competition improves fitness" (true in biology) ≠ "Competition should structure society" (normative)
   - Mitigation: Separate is/ought; test normative claim independently

2. **Scale Mismatch**
   - "Ecosystem balance" at global scale ≠ "Organizational balance" at single institution
   - Mitigation: Test at matching scale; model scaling effects

3. **Reversibility Assumption**
   - Biological extinction is irreversible; institutional change can be reversed
   - Mitigation: Model reversibility explicitly; test rollback scenarios

4. **Incentive Misalignment**
   - Predators must hunt to survive; humans can choose altruism
   - Mitigation: Relax pure incentive assumptions; test with noise

---

## Test Plan Generation

To validate a cross-domain transfer:

### 1. Specify Test Domain

Example: Testing "market dynamics apply to institutional authority":

- **Target Domain:** Internal institutional authority distribution
- **Analogous Entities:** Departments as competing entities
- **Analogous Mechanism:** Authority allocation as "market clearing"
- **Boundary:** Single organization with multiple departments

### 2. Design Experiment

```python
def test_market_dynamics_in_institution():
    """
    Hypothesis: Authority distribution in institutions follows 
    market-like supply/demand dynamics.
    
    Test: Simulate department authority allocation under different 
    governance mechanisms (centralized vs decentralized) and 
    compare to economic models.
    """
    
    # Setup
    org = Organization(departments=5)
    
    # Mechanism 1: Centralized allocation (planning)
    allocate_centrally(org)
    measure_efficiency(org)  # Outcome: suboptimal
    
    # Mechanism 2: Decentralized bidding (market)
    allocate_via_bidding(org)
    measure_efficiency(org)  # Outcome: better?
    
    # Cross-check with market theory predictions
    economic_prediction = market_efficiency_model()
    if org_efficiency ~= economic_prediction:
        transfer_hypothesis = "SUPPORTED"
    else:
        transfer_hypothesis = "REJECTED"
        analyze_divergence()  # Why did it fail?
    
    return transfer_hypothesis, evidence
```

### 3. Resolution Criteria

What counts as success?

- **Strong support:** Experiment result matches both theory and prediction within 10%
- **Moderate support:** Result matches direction but magnitude off; assumptions identified
- **Weak support:** Result matches in outline; significant caveats required
- **Not supported:** Result contradicts theory or prediction
- **Tested but not actionable:** Result is domain-specific; transfer is risky

### 4. Record Outcome

Link test result back to transfer hypothesis:

```
transfer_hypothesis.linked_experiment_id = experiment.id
transfer_hypothesis.status = "tested"
transfer_hypothesis.confidence = 0.6  # Updated after test
transfer_hypothesis.uncertainty = 0.3
transfer_hypothesis.outcome = "SUPPORTED but with caveats"
transfer_hypothesis.caveats = [
  "Assumes departments are autonomous (false if central control)",
  "Does not account for cross-department dependencies",
  "Timescale is weeks; true market equilibration is months"
]
```

---

## Transfer Hypothesis Lifecycle

### Status Transitions

```
HYPOTHESIS
  ↓
  [Create test plan]
  ↓
TESTED
  ↓ (choose path)
  ├→ SUPPORTED (confidence > 0.6) → can inform policy
  ├→ WEAK (confidence 0.3-0.6) → hypothesis remains; test more
  ├→ REJECTED (confidence < 0.3) → archive; do not use
  ↓
  [If supported: propose institutional adoption]
  ↓
INSTITUTIONALIZED (if society/civilization governance approves)
```

### Promotion Threshold

A cross-domain transfer can only become institutional knowledge if:

1. ✓ Assumptions explicitly stated and tested
2. ✓ Failure modes enumerated and understood
3. ✓ Sandbox experiment run and result documented
4. ✓ Confidence > 0.6 (or higher threshold for high-risk)
5. ✓ Normative claims separated from descriptive principle
6. ✓ Institutional review approved
7. ✓ Reversibility/rollback plan documented

---

## Known Limits

1. **Analogy as Heuristic:** Transfer hypotheses are heuristics for learning, not proofs. Many fail in practice.

2. **Assumption Incompleteness:** Cannot enumerate all hidden assumptions. Some emerge only during testing.

3. **Emergence:** System-level effects in target domain may not be predicted by principle transfer.

4. **Adversarial Misuse:** A transfer hypothesis can be deliberately misapplied to justify harmful policies. Normative critique required.

5. **Domain Expertise Gap:** A principle from Biology may transfer, but institutional experts may spot flaws that the transfer engine missed.

6. **Time-Bound:** A transfer that works at one time may fail later as domain context changes.

---

## Integration with Phases

- **Phase 6 Curiosity Engine:** Flags cross-domain patterns as learning opportunities
- **Phase 7 Hypothesis Engine:** Converts analogies to testable transfer hypotheses
- **Phase 8 Experiment Lab:** Runs transfer tests in sandbox
- **Phase 10 (this phase):** Builds transfer hypotheses explicitly
- **Phase 12 Promotion Workflow:** Blocks transfer from becoming institutional knowledge without evidence
- **Phase 20 Adversarial Security:** Tests transfers against adversarial scenarios
- **Phase 21 Normative Reasoning:** Separates is/ought in transfers

---

## Next: Phase 1 Documentation Complete

With these five documents (UNIVERSAL_LEARNING_LAYER, KNOWLEDGE_CLAIM_MODEL, SCIENTIFIC_EVIDENCE_ENGINE, AUTONOMOUS_LEARNING_GOVERNANCE, CROSS_DOMAIN_SYNTHESIS), Phase 1 documentation is complete.

Next: Create tests and commit Phase 1.
