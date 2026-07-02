# Critical: LLM Integration Gaps Report

**Date:** 2026-06-22  
**Status:** ⚠️ COMPONENTS DON'T ACTUALLY USE OPENAI

---

## Executive Summary

❌ **0 out of 12 core components actually call OpenAI**

While the provider configuration is set up and tests pass with fixtures, the actual system components **do not make real LLM API calls**.

This means:
- ✅ Tests pass (using mock data)
- ✅ Architecture is sound
- ❌ System doesn't actually use OpenAI for real work

---

## Components Not Calling LLM

### 1. **Learning Loop** (`learning/cycle.py`)
- **What it should do:** Call OpenAI to extract claims from signals
- **What it actually does:** Processes signals with ingestion pipeline (which also doesn't call LLM)
- **Impact:** Claims generated are from text parsing, not LLM analysis
- **Fix needed:** Integrate OpenAI for claim generation and hypothesis validation

### 2. **Ingestion Pipeline** (`ingestion/pipeline.py`)
- **What it should do:** Use OpenAI to understand documents and extract claims
- **What it actually does:** Uses ClaimExtractor (regex/text parsing)
- **Impact:** Can only extract simple text patterns, no semantic understanding
- **Fix needed:** Replace/augment ClaimExtractor with OpenAI-powered extraction

### 3. **RAG System** (`ingestion/rag.py`)
- **What it should do:** Use OpenAI for retrieval-augmented generation
- **What it actually does:** Unknown (likely simulated)
- **Impact:** No real knowledge enhancement
- **Fix needed:** Wire retrieval + generation to OpenAI

### 4. **Validation Suite** (`validation/`)
- **What it should do:** Use OpenAI to validate claims and outputs
- **What it actually does:** Fixture-based validation
- **Impact:** No real external validation
- **Fix needed:** Integrate OpenAI for real validation checks

### 5. **Model Foundry** (`foundry/`)
- **What it should do:** Use OpenAI for training data generation and evaluation
- **What it actually does:** Uses fixtures
- **Impact:** No real model training feedback
- **Fix needed:** Hook OpenAI for training data and evaluation

### 6. **Governance** (`institutions/society.py`)
- **What it should do:** Use OpenAI to reason about decisions
- **What it actually does:** Rule-based decisions
- **Impact:** No intelligent decision-making
- **Fix needed:** Add OpenAI reasoning to governance decisions

### 7. **World Simulation** (`simulation/world_lab.py`)
- **What it should do:** Use OpenAI for scenario generation and testing
- **What it actually does:** Simulated scenarios
- **Impact:** No real scenario validation
- **Fix needed:** Use OpenAI for scenario creation and evaluation

### 8-12. Other Components
- **Trust Calculator, Uncertainty Stack, Memory Kernel, Evidence Kernel, Civilization Framework**
- These are data structures and logic layers - they don't need direct LLM calls
- But they should receive data from components that DO call OpenAI

---

## Root Cause Analysis

**Why does this happen?**

1. **Provider config exists but isn't used** - It's available in `runtime/base_agent/provider_config.py` but core components don't import or use it

2. **Components built to be provider-agnostic** - Learning loop, ingestion, etc. don't know about or care about providers. They just process data.

3. **Tests use fixtures** - All regression tests pass with mock data, so there's no immediate failure signal

4. **No dependency chain** - The learning loop doesn't import provider_config, so there's no path from "we have OpenAI configured" to "use it here"

---

## What's Actually Happening

```
Current Flow:
Signal → Learning Loop → ClaimExtractor (regex) → Evidence Kernel
                            ↓
                      No LLM calls here

Expected Flow:
Signal → Learning Loop → OpenAI (analyze signal) → Claims
           ↓
        OpenAI (generate hypothesis) → Hypothesis
           ↓
        OpenAI (generate experiment) → Experiment
           ↓
        Evidence Kernel, Memory Kernel
```

---

## Impact Assessment

| Layer | Real LLM | Status | Severity |
|-------|----------|--------|----------|
| Learning Loop | ❌ No | Uses text parsing only | High |
| Ingestion | ❌ No | Regex-based claim extraction | High |
| RAG | ❌ No | Not real retrieval-augmented | High |
| Validation | ❌ No | Fixture-based only | Medium |
| Governance | ❌ No | Rule-based, not intelligent | High |
| Simulation | ❌ No | Pre-generated scenarios | Medium |
| Trust/Calibration | N/A | Data layers (no LLM needed) | Low |
| Memory/Evidence | N/A | Storage layers (no LLM needed) | Low |

---

## Integration Implementation Plan

### Phase 1: Core LLM Integration (Priority: HIGH)

#### 1.1 Learning Loop Integration
**File:** `learning/cycle.py`

```python
# Add OpenAI integration
from backend.src.config.provider_config import get_config

class AutonomousLearningLoop:
    def __init__(self, ...):
        self.config = get_config("standard")
        self.client = OpenAI(api_key=self.config.api_key)
    
    def run(self, signal_text: str, *, source_uri: str = "memory://signal") -> dict:
        # Call OpenAI to extract claims
        claims = self._extract_claims_with_llm(signal_text)
        
        # Call OpenAI to generate hypothesis
        hypothesis = self._generate_hypothesis_with_llm(signal_text, claims)
        
        # Call OpenAI to design experiment
        experiment = self._design_experiment_with_llm(hypothesis)
        
        return {
            "claims": claims,
            "hypothesis": hypothesis,
            "experiment": experiment,
            ...
        }
    
    def _extract_claims_with_llm(self, signal_text: str):
        """Use OpenAI to extract claims from signal"""
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "Extract factual claims from text"},
                {"role": "user", "content": signal_text}
            ]
        )
        # Parse claims from response
        ...
    
    # Similar for hypothesis and experiment generation
```

#### 1.2 Ingestion Pipeline Integration
**File:** `ingestion/pipeline.py`

Replace regex-based `ClaimExtractor` with OpenAI-powered extraction:

```python
from backend.src.config.provider_config import get_config

class IntelligentClaimExtractor:
    def __init__(self):
        self.config = get_config("standard")
        self.client = OpenAI(api_key=self.config.api_key)
    
    def extract(self, document: IngestedDocument) -> list[str]:
        """Use OpenAI to understand document and extract claims"""
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "Extract key factual claims"},
                {"role": "user", "content": document.content}
            ]
        )
        # Parse and return claims
        ...
```

#### 1.3 RAG System Integration
**File:** `ingestion/rag.py`

Implement actual retrieval-augmented generation:

```python
def retrieve_and_generate(self, query: str):
    # 1. Retrieve relevant documents
    docs = self.retriever.retrieve(query)
    
    # 2. Use OpenAI to generate with context
    response = self.client.chat.completions.create(
        model=self.config.model,
        messages=[
            {"role": "system", "content": "Use the following documents to answer"},
            {"role": "user", "content": f"Documents:\n{docs}\n\nQuery: {query}"}
        ]
    )
    
    return response.choices[0].message.content
```

### Phase 2: Intelligence Integration (Priority: MEDIUM)

#### 2.1 Governance with OpenAI Reasoning
**File:** `institutions/society.py`

Add OpenAI reasoning to governance decisions:

```python
def decide(self, proposal_id: str, approved: bool = None):
    if approved is None:
        # Let OpenAI reason about the proposal
        reasoning = self._get_llm_reasoning(proposal_id)
        approved = self._parse_approval(reasoning)
    
    # Record decision
    ...

def _get_llm_reasoning(self, proposal_id: str):
    proposal = self.proposals[proposal_id]
    response = self.client.chat.completions.create(
        model=self.config.model,
        messages=[
            {"role": "system", "content": "Evaluate governance proposal"},
            {"role": "user", "content": f"Proposal: {proposal}"}
        ]
    )
    return response.choices[0].message.content
```

#### 2.2 Validation with OpenAI
**File:** `validation/`

Use OpenAI for external validation:

```python
def validate(self, claim: str, context: str):
    response = self.client.chat.completions.create(
        model=self.config.model,
        messages=[
            {"role": "system", "content": "Validate claims"},
            {"role": "user", "content": f"Claim: {claim}\nContext: {context}"}
        ]
    )
    # Parse validation result
    ...
```

---

## Effort Estimate

| Component | Effort | Impact | Timeline |
|-----------|--------|--------|----------|
| Learning Loop | 2-4 hours | High | Week 1 |
| Ingestion | 2-3 hours | High | Week 1 |
| RAG System | 3-4 hours | High | Week 1 |
| Governance | 2-3 hours | High | Week 2 |
| Validation | 2-3 hours | Medium | Week 2 |
| Simulation | 3-4 hours | Medium | Week 2 |

**Total: ~15-20 hours of integration work**

---

## Success Criteria

After implementing LLM integration:

- [ ] Learning loop calls OpenAI for claim extraction
- [ ] Learning loop calls OpenAI for hypothesis generation
- [ ] Ingestion pipeline uses OpenAI for document understanding
- [ ] RAG system uses OpenAI for generation
- [ ] Governance uses OpenAI for reasoning
- [ ] Validation uses OpenAI for checking
- [ ] All 121 tests still pass with OpenAI models
- [ ] System can run end-to-end with no fixtures

---

## Verdict

**Currently:** Agentco passes tests but doesn't use OpenAI for actual work.

**After Integration:** Agentco will be a fully OpenAI-powered autonomous system.

**Timeline:** 2-3 weeks to full LLM integration

