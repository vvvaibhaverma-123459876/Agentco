# Component LLM Integration Implementation Plan

**Status:** Ready for implementation  
**LLM Service:** ✅ Complete (autonomy/llm_service.py)  
**Architecture:** ✅ Documented (docs/LLM_PROVIDER_INTEGRATION.md)  
**Next:** Wire service into 12 core components

---

## Quick Reference: What to Change

Every component follows this pattern:

### Before (Using Fixtures)
```python
# Component uses hardcoded or simulated responses
response = extract_claims(signal)  # Returns fixture data
```

### After (Using LLM Service)
```python
from autonomy import get_llm

class Component:
    def __init__(self):
        self.llm = get_llm("standard")  # Pick tier based on task
    
    def method(self, input_text: str):
        response = self.llm.complete(
            prompt=input_text,
            system="You are...",  # Context for the LLM
            max_tokens=500
        )
        return self._parse(response)
```

---

## Integration Checklist

### PHASE 1: Core Systems (Highest Impact)

#### 1. Learning Loop
- **File:** `learning/cycle.py`
- **Current:** Uses `ingestion.pipeline` which uses regex
- **Change:** Add LLM for claim extraction + hypothesis generation
- **Tier:** Use `get_llm("frontier")` (best reasoning)
- **Methods to update:**
  ```python
  def run(self, signal_text: str, *, source_uri: str = "memory://signal")
  def extract_claims(signal_text: str)  # Currently via ingestion
  def generate_hypothesis(claims: list[str])
  def design_experiment(hypothesis: dict)
  ```
- **Test file:** `evals/regression/test_gate8_learning_loop.py`
- **Verification:** Signal should generate claims via LLM, not regex

#### 2. Ingestion Pipeline
- **File:** `ingestion/pipeline.py`
- **Current:** `ClaimExtractor` uses regex (min 3 words, fixed patterns)
- **Change:** Wrap `ClaimExtractor` with LLM option or replace
- **Tier:** Use `get_llm("standard")` (balanced for document processing)
- **Key class:** `IntelligentClaimExtractor` (new)
- **Methods to add:**
  ```python
  def extract(self, document: IngestedDocument) -> list[str]
      # Use LLM to understand document semantically
      response = self.llm.complete(
          prompt=document.content,
          system="Extract key factual claims from this document"
      )
      return self._parse_claims(response)
  ```
- **Test file:** `evals/regression/test_gate7_ingestion.py`
- **Verification:** Documents should be analyzed by LLM, not just pattern-matched

#### 3. RAG System
- **File:** `ingestion/rag.py`
- **Current:** Likely fixture-based retrieval + generation
- **Change:** Wire real retrieval + LLM generation
- **Tier:** Use `get_llm("standard")`
- **Method to update:**
  ```python
  def retrieve_and_generate(self, query: str) -> str
      # 1. Retrieve relevant documents
      docs = self.retriever.retrieve(query)
      
      # 2. Use LLM to generate with context
      context = "\n".join([d.content for d in docs])
      response = self.llm.complete(
          prompt=f"Query: {query}\n\nContext:\n{context}",
          system="Answer based on the provided context",
          max_tokens=1000
      )
      return response
  ```
- **Test file:** Check ingestion tests
- **Verification:** RAG should actually retrieve and augment generation

#### 4. Governance / Institutions
- **File:** `institutions/society.py` or similar
- **Current:** Rule-based decisions without reasoning
- **Change:** Add LLM reasoning to decision-making
- **Tier:** Use `get_llm("frontier")` (best for complex reasoning)
- **Method to add:**
  ```python
  def decide(self, proposal_id: str) -> dict
      proposal = self.proposals[proposal_id]
      
      # Get LLM reasoning
      response = self.llm.complete(
          prompt=f"Proposal:\n{proposal}",
          system="Analyze this governance proposal. Recommend approve/reject.",
          temperature=0.5  # More consistent for decisions
      )
      
      reasoning = response
      approved = self._parse_decision(response)
      
      return {
          "proposal_id": proposal_id,
          "approved": approved,
          "reasoning": reasoning
      }
  ```
- **Test file:** `evals/regression/test_gate10_governance_policy.py`
- **Verification:** Decisions should have explicit reasoning from LLM

---

### PHASE 2: Intelligence Layers (Medium Impact)

#### 5. Validation Suite
- **File:** `validation/` (check structure)
- **Current:** Fixture-based validation
- **Change:** Use LLM for semantic validation
- **Tier:** Use `get_llm("monitor")` (lightweight for checking)
- **Method:**
  ```python
  def validate_claim(self, claim: str, context: str) -> dict
      response = self.llm.complete(
          prompt=f"Claim: {claim}\n\nContext: {context}",
          system="Is this claim valid given the context? Respond: VALID/INVALID with brief reasoning"
      )
      return self._parse_validation(response)
  ```
- **Test file:** `evals/regression/test_gate15_validation.py`
- **Verification:** Validation should use real LLM evaluation

#### 6. World Simulation / WorldLab
- **File:** `simulation/world_lab.py`
- **Current:** Pre-generated or hardcoded scenarios
- **Change:** Use LLM to generate scenarios + test outcomes
- **Tier:** Use `get_llm("standard")`
- **Methods:**
  ```python
  def generate_scenario(self, params: dict) -> Scenario
      response = self.llm.complete(
          prompt=f"Generate a test scenario with: {params}",
          system="Create a realistic scenario for testing"
      )
      return self._parse_scenario(response)
  
  def evaluate_outcome(self, scenario: Scenario, agent_response: str) -> dict
      response = self.llm.complete(
          prompt=f"Scenario: {scenario}\n\nAgent response: {agent_response}",
          system="Evaluate if agent handled scenario correctly"
      )
      return self._parse_evaluation(response)
  ```
- **Test file:** `evals/regression/test_gate12_simulation.py`
- **Verification:** Scenarios should be generated + evaluated by LLM

---

### PHASE 3: Data Layers (No Changes Needed)

These are storage/computation layers that consume data from above:

- **Trust Calculator** (`calibration/trust/`) - processes signals from other layers
- **Uncertainty Stack** (`calibration/uncertainty/`) - quantifies confidence
- **Memory Kernel** (`memory_kernel/`) - stores experiences
- **Evidence Kernel** (`calibration/evidence/`) - manages evidence
- **Civilization Framework** (`civilization/`) - orchestrates agents
- **Model Foundry** (`foundry/`) - could benefit from LLM for training data (Phase 2.5)

These don't need direct LLM integration; they receive processed data from Phase 1 & 2 components.

---

## Implementation Sequence

### Week 1: Phase 1 (Core Systems)
1. **Learning Loop** - 2-4 hours
   - Update `learning/cycle.py`
   - Test with `evals/regression/test_gate8_learning_loop.py`
   
2. **Ingestion Pipeline** - 2-3 hours
   - Update `ingestion/pipeline.py`
   - Test with `evals/regression/test_gate7_ingestion.py`
   
3. **RAG System** - 2-3 hours
   - Update `ingestion/rag.py`
   - Verify retrieval + generation integration

4. **Governance** - 2-3 hours
   - Update `institutions/society.py`
   - Test with `evals/regression/test_gate10_governance_policy.py`

**Week 1 Total:** ~8-13 hours  
**Verification:** All Phase 1 tests pass with real LLM calls (no fixtures)

### Week 2: Phase 2 (Intelligence Layers)
5. **Validation** - 2-3 hours
6. **Simulation** - 2-3 hours

**Week 2 Total:** ~4-6 hours

### Week 3: Verification & Cleanup
- End-to-end testing with all components
- Performance profiling (LLM latency)
- Provider switching tests (OpenAI → Anthropic → Ollama)
- Cost estimation (if using paid providers)

---

## Test Strategy

### Before Integration
```bash
# All tests pass with fixtures
python -m pytest evals/regression/ -v
# ✅ 121 tests pass
```

### During Integration
```bash
# Run specific component tests with LLM
export LLM_PROVIDER=openai
export LLM_API_KEY=sk-...
python -m pytest evals/regression/test_gate8_learning_loop.py -v

# Should see real API calls, not fixture data
```

### After Integration
```bash
# Full suite with real LLM
python -m pytest evals/regression/ -v
# ✅ 121 tests pass (with real LLM)

# Test provider switching
export LLM_PROVIDER=anthropic
python -m pytest evals/regression/ -v
# ✅ Should still pass with Anthropic

# Test provider switching
export LLM_PROVIDER=ollama
python -m pytest evals/regression/ -v
# ✅ Should work with local Ollama
```

---

## Integration Template (Copy-Paste)

### Step 1: Add LLM Service Initialization
```python
from autonomy import get_llm

class YourComponent:
    def __init__(self, ...):
        self.llm = get_llm("standard")  # Change tier as needed
        # ... rest of init
```

### Step 2: Replace Fixture/Regex Call
```python
# BEFORE (fixture)
response = hardcoded_response  # or parse_with_regex(input)

# AFTER (LLM)
response = self.llm.complete(
    prompt=input_text,
    system="Context: You are analyzing...",
    temperature=0.7,
    max_tokens=500
)
```

### Step 3: Test
```python
# Run component tests
pytest evals/regression/test_gate8_xxx.py -v
# Verify real LLM calls in output
```

---

## Configuration for Testing

### For Integration Testing
```bash
# Use fastest, cheapest OpenAI model for testing
export LLM_PROVIDER=openai
export LLM_MODEL_STANDARD=gpt-4o-mini
export LLM_MODEL_FRONTIER=gpt-4o-mini  # Use mini for faster testing

# Or use local Ollama (free)
export LLM_PROVIDER=ollama
export LLM_BASE_URL=http://localhost:11434/v1
# No API key needed

# Or use Groq (free tier available)
export LLM_PROVIDER=groq
export LLM_API_KEY=...
```

---

## Success Criteria

After implementing all components:

- [ ] Learning Loop calls LLM for claim extraction
- [ ] Learning Loop calls LLM for hypothesis generation
- [ ] Ingestion pipeline uses LLM for document understanding
- [ ] RAG system uses LLM for generation with retrieved context
- [ ] Governance uses LLM for reasoning
- [ ] Validation uses LLM for semantic checks
- [ ] Simulation uses LLM for scenario generation
- [ ] All 121 tests pass with real LLM
- [ ] System works with OpenAI, Anthropic, Ollama, Groq
- [ ] No hardcoded provider dependencies
- [ ] Configuration via environment variables only

---

## Debugging Tips

### "Module has no attribute..."
- Make sure `from autonomy import get_llm` is present
- Check that `autonomy/__init__.py` exports `get_llm`

### "Provider not found"
- Verify `LLM_PROVIDER` env var is set
- Run `python -c "from autonomy import get_llm; print(get_llm().get_provider_info())"`

### "API Key not found"
- Check `LLM_API_KEY` is set: `echo $LLM_API_KEY`
- Or set in code (not recommended for production)

### "Timeout"
- Increase `timeout` parameter: `llm.complete(..., timeout=60.0)`
- Check LLM provider is online

---

## Rollback Plan

If LLM integration breaks something:

1. Each component should have both fixture AND LLM paths
2. Set env var to use fixtures: `export USE_FIXTURES=true`
3. Or wrap in try/except:
   ```python
   try:
       response = self.llm.complete(prompt, system)
   except Exception:
       response = fallback_fixture_response
   ```

---

## Next: Component Integration

Ready to start? Pick a component from Phase 1 and create a PR with the integration.

Example:
1. `learning/cycle.py` - add LLM service + update claim extraction
2. Add tests to verify real LLM calls
3. Run full test suite
4. Submit PR

Each component should be ~100-200 lines of changes, ~2-4 hours work.

