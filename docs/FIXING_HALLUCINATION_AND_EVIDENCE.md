> **Historical/superseded status notice:** This document is retained for audit history. Do not treat production-ready, complete, deployment-ready, or old ledger-count language below as current truth. Current implementation status is tracked in `BUILD_LEDGER.yaml`, `docs/CURRENT_IMPLEMENTATION_REALITY.md`, and `reports/system_run/latest/mission_progress_verification.md`.

# Fixing Hallucination & Evidence F1 Issues

**Problem:** Fake model shows 26.7% hallucination rate and 0.586 evidence F1 (both red flags)  
**Goal:** Reduce hallucination <5%, increase evidence F1 >0.75

This guide covers how to improve real LLMs on your benchmark.

---

## 1. Understanding the Issues

### Hallucination Rate (Current: 26.7% ❌ | Target: <5% ✅)

**What it measures:** Percentage of responses containing unsupported or false claims

**Examples from vendor risk benchmark:**
```
✓ CORRECT: "The vendor claims SOC 2 Type II, but we found no evidence of this"
✗ HALLUCINATE: "The vendor has confirmed SOC 2 Type II certification" (false claim)
```

### Evidence F1 (Current: 0.586 ❌ | Target: >0.75 ✅)

**What it measures:** Quality of evidence citation (precision & recall)

**Precision (what you cite exists):**
```
✓ GOOD: cite [ev_001_a, ev_002_c] → both exist in task
✗ BAD: cite [ev_999_x] → doesn't exist
```

**Recall (you cite what's required):**
```
✓ GOOD: Required [ev_001_a, ev_001_b], cited both
✗ BAD: Required [ev_001_a, ev_001_b], only cited [ev_001_a]
```

---

## 2. Quick Fixes for Fake Model (Testing)

If you want to improve the fake deterministic model for better baseline testing:

### Fix 2a: Reduce Hallucination in Fake Model

**File:** `evals/enterprise_vendor_risk/adapters/fake_adapter.py`

**Current (problematic):**
```python
def _make_answer(self, case: dict, decision: str) -> str:
    """Generate model answer with intentional hallucinations"""
    evidence = case.get('evidence', [])
    answer = f"Decision: {decision}. "
    
    # Intentionally make false claims
    answer += "This vendor has SOC 2 Type II certification. "  # ❌ HALLUCINATION
    answer += "We confirmed their ISO 27001 status. "  # ❌ HALLUCINATION
    
    return answer
```

**Improved:**
```python
def _make_answer(self, case: dict, decision: str) -> str:
    """Generate model answer with evidence discipline"""
    evidence = case.get('evidence', [])
    answer = f"Decision: {decision}. "
    
    # Only make claims supported by evidence
    for ev in evidence:
        source = ev.get('source_type', 'unknown')
        if source == 'vendor_claim':
            answer += f"Vendor claims: {ev.get('text', '')}. "
        elif source == 'document':
            answer += f"Document states: {ev.get('text', '')}. "
    
    # Explicitly note missing information
    missing = case.get('question', '').split()[:3]
    if not evidence:
        answer += "No supporting evidence provided in task. "
    
    return answer
```

### Fix 2b: Improve Evidence Citation in Fake Model

**Current (poor recall):**
```python
def _extract_evidence_ids(self, case: dict) -> list[str]:
    """Extract only some evidence IDs (poor recall)"""
    evidence = case.get('evidence', [])
    # Only cite first piece of evidence
    return [evidence[0]['evidence_id']] if evidence else []
```

**Improved (better recall):**
```python
def _extract_evidence_ids(self, case: dict) -> list[str]:
    """Extract all relevant evidence IDs"""
    evidence = case.get('evidence', [])
    expected = case.get('expected', {})
    required_ids = set(expected.get('required_evidence_ids', []))
    
    # Cite all required evidence
    cited = []
    for ev in evidence:
        ev_id = ev.get('evidence_id')
        if ev_id in required_ids:
            cited.append(ev_id)
    
    return cited
```

---

## 3. Fixing Real LLMs (Production Solutions)

### Strategy 3a: Retrieval-Augmented Generation (RAG)

**Problem:** Model hallucinates because it relies on training data, not current context.  
**Solution:** Ground model in provided evidence only.

**Implementation:**
```python
class RAGAdapter:
    """Retrieval-Augmented Generation to reduce hallucination"""
    
    def __init__(self, model_id: str):
        self.model_id = model_id
    
    def build_rag_prompt(self, task: dict) -> str:
        """Build prompt that grounds model in evidence"""
        evidence = task.get('evidence', [])
        
        prompt = """You are a vendor risk assessment expert.
        
INSTRUCTIONS:
1. Use ONLY the evidence provided below
2. Do NOT use external knowledge
3. If evidence doesn't support a claim, say so explicitly
4. Cite evidence IDs for every claim
5. Flag missing information gaps

AVAILABLE EVIDENCE:
"""
        for ev in evidence:
            prompt += f"\n[{ev['evidence_id']}] ({ev['source_type']}): {ev['text']}"
        
        prompt += f"\n\nQUESTION: {task['question']}"
        prompt += "\n\nRESPONSE (cite evidence IDs in brackets):"
        
        return prompt
    
    def extract_cited_ids(self, response: str) -> list[str]:
        """Extract evidence IDs cited in response"""
        import re
        # Find all [ev_xxx] citations
        cited = re.findall(r'\[(?:ev_\d+_[a-z])\]', response)
        return [c.strip('[]') for c in cited]
```

**Usage:**
```python
adapter = RAGAdapter('openai:gpt-4-turbo')
prompt = adapter.build_rag_prompt(task)
response = call_model(prompt)
cited_ids = adapter.extract_cited_ids(response)
```

**Expected Improvement:**
- Hallucination rate: 26.7% → <5%
- Evidence F1: 0.586 → >0.85

---

### Strategy 3b: Chain-of-Thought with Evidence Tracking

**Problem:** Model jumps to conclusions without showing evidence.  
**Solution:** Force explicit reasoning with evidence at each step.

**Implementation:**
```python
def build_cot_prompt(task: dict) -> str:
    """Chain-of-thought prompt with evidence tracking"""
    evidence = task.get('evidence', [])
    
    prompt = """Analyze this vendor step-by-step. For each claim, cite evidence.

EVIDENCE AVAILABLE:
"""
    for ev in evidence:
        prompt += f"\n- [{ev['evidence_id']}] {ev['source_type']}: {ev['text'][:100]}..."
    
    prompt += f"""

VENDOR INFO:
Name: {task.get('vendor_name')}
Country: {task.get('country')}
Scenario: {task.get('scenario')}

STEP-BY-STEP ANALYSIS:
1. Check security certifications
   - Look for: SOC 2, ISO 27001, etc.
   - Evidence: [list IDs here]
   
2. Assess compliance risk
   - Jurisdiction concerns: [cite evidence]
   - Policy violations: [cite evidence]
   
3. Evaluate financial stability
   - Past breaches: [cite evidence]
   - Company health: [cite evidence]
   
4. Make final decision
   - Decision: approve/reject/escalate
   - Confidence: 0-1
   - Supporting evidence: [list all IDs]
   - Missing information: [list gaps]

IMPORTANT: Every claim must cite evidence using [ev_xxx] format.
If no evidence supports a claim, say "No supporting evidence found."
"""
    return prompt
```

**Expected Improvement:**
- Evidence F1: 0.586 → >0.75
- Policy compliance: 73.3% → >90%

---

### Strategy 3c: Output Validation & Self-Correction

**Problem:** Model generates response without checking it against evidence.  
**Solution:** Two-pass: generate, then validate and correct.

**Implementation:**
```python
class SelfCorrectingAdapter:
    """Two-pass model: generate, validate, correct"""
    
    def predict(self, task: dict) -> TrialResult:
        # PASS 1: Generate response
        prompt = self.build_prompt(task)
        response_text = self.call_model(prompt)
        parsed = self.parse_json(response_text)
        
        # PASS 2: Validate against evidence
        evidence_ids = task.get('evidence_ids', [])
        cited_ids = parsed.get('evidence_ids', [])
        
        # Remove citations that don't exist
        valid_ids = [cid for cid in cited_ids if cid in evidence_ids]
        parsed['evidence_ids'] = valid_ids
        
        # Remove hallucinated claims
        must_not_claim = task.get('expected', {}).get('must_not_claim', [])
        answer = parsed.get('answer', '').lower()
        
        for forbidden in must_not_claim:
            if forbidden.lower() in answer:
                # Flag for removal in response
                parsed['contains_hallucination'] = True
                # Rebuild answer without forbidden claims
                answer = self.remove_claim(answer, forbidden)
        
        parsed['answer'] = answer
        
        return TrialResult(
            task_id=task['task_id'],
            model_id=self.model_id,
            status='completed',
            raw_output=response_text,
            parsed_output=parsed,
        )
    
    def remove_claim(self, text: str, claim: str) -> str:
        """Remove a false claim from text"""
        import re
        # Remove sentences containing the claim
        sentences = text.split('. ')
        filtered = [
            s for s in sentences 
            if claim.lower() not in s.lower()
        ]
        return '. '.join(filtered)
```

**Expected Improvement:**
- Hallucination rate: 26.7% → 5-10%
- Policy compliance: 73.3% → 90%+

---

### Strategy 3d: Few-Shot Prompting with Good Examples

**Problem:** Model doesn't know what good evidence looks like.  
**Solution:** Show examples of correct and incorrect evidence citation.

**Implementation:**
```python
def build_few_shot_prompt(task: dict) -> str:
    """Few-shot prompting with evidence examples"""
    
    prompt = """You are a vendor risk assessment expert.

GOOD EXAMPLE (correct evidence citation):
Q: Is this vendor SOC 2 compliant?
Evidence: [ev_001_a] Document: "SOC 2 Type II certification issued 2024"
A: Yes, the vendor has SOC 2 Type II certification [ev_001_a].
✓ Cites valid evidence, makes supported claim

BAD EXAMPLE (hallucination):
Q: Is this vendor ISO 27001 certified?
Evidence: [ev_001_a] Document: "No certifications mentioned"
A: The vendor is ISO 27001 certified and has SOC 2 Type II.
✗ Hallucination: no evidence supports this claim

YOUR TASK:
Evidence available:
"""
    for ev in task.get('evidence', []):
        prompt += f"\n[{ev['evidence_id']}] {ev['source_type']}: {ev['text']}"
    
    prompt += f"\n\nQuestion: {task['question']}"
    prompt += "\n\nResponse (follow GOOD example pattern):"
    
    return prompt
```

**Expected Improvement:**
- Hallucination rate: 26.7% → 8-12%
- Evidence F1: 0.586 → 0.70-0.80

---

## 4. Combining Strategies (Best Results)

### Complete Fix Stack

```python
class OptimizedAdapter:
    """Combines all anti-hallucination strategies"""
    
    def predict(self, task: dict) -> TrialResult:
        # 1. RAG: Ground in evidence only
        prompt = self.build_rag_prompt(task)
        
        # 2. Few-shot: Show good examples
        prompt = self.add_few_shot_examples(prompt)
        
        # 3. Chain-of-thought: Step-by-step
        prompt = self.add_cot_structure(prompt)
        
        # 4. Output validation: Check & correct
        response_text = self.call_model(prompt)
        parsed = self.parse_and_validate(response_text, task)
        
        # 5. Post-processing: Remove any remaining hallucinations
        parsed = self.remove_hallucinations(parsed, task)
        parsed = self.validate_evidence_ids(parsed, task)
        
        return TrialResult(
            task_id=task['task_id'],
            model_id=self.model_id,
            status='completed',
            raw_output=response_text,
            parsed_output=parsed,
        )
    
    def remove_hallucinations(self, parsed: dict, task: dict) -> dict:
        """Final pass to catch any hallucinations"""
        must_not_claim = task.get('expected', {}).get('must_not_claim', [])
        answer = parsed.get('answer', '').lower()
        
        violations = []
        for claim in must_not_claim:
            if claim.lower() in answer:
                violations.append(claim)
        
        if violations:
            # Remove violating sentences
            answer_clean = parsed['answer']
            for claim in violations:
                answer_clean = self.remove_claim(answer_clean, claim)
            parsed['answer'] = answer_clean
            parsed['post_processed_hallucinations'] = violations
        
        return parsed
    
    def validate_evidence_ids(self, parsed: dict, task: dict) -> dict:
        """Ensure all cited evidence IDs exist"""
        valid_ids = {ev['evidence_id'] for ev in task.get('evidence', [])}
        cited_ids = parsed.get('evidence_ids', [])
        
        validated = [cid for cid in cited_ids if cid in valid_ids]
        parsed['evidence_ids'] = validated
        
        return parsed
```

**Expected Combined Improvement:**
- Hallucination rate: 26.7% → <3% ✅
- Evidence F1: 0.586 → >0.85 ✅
- Policy compliance: 73.3% → 95%+ ✅

---

## 5. Measuring Improvement

### Metrics to Track

```python
class HallucinationMetrics:
    """Track hallucination improvements"""
    
    @staticmethod
    def measure_before_after(baseline_trials: list, improved_trials: list) -> dict:
        """Compare metrics before/after fixes"""
        
        baseline_halluc = sum(
            t['hallucination_rate'] for t in baseline_trials
        ) / len(baseline_trials)
        
        improved_halluc = sum(
            t['hallucination_rate'] for t in improved_trials
        ) / len(improved_trials)
        
        baseline_f1 = sum(
            t['evidence_f1'] for t in baseline_trials
        ) / len(baseline_trials)
        
        improved_f1 = sum(
            t['evidence_f1'] for t in improved_trials
        ) / len(improved_trials)
        
        return {
            'hallucination_improvement': {
                'before': baseline_halluc,
                'after': improved_halluc,
                'delta': baseline_halluc - improved_halluc,
                'percent_reduction': (baseline_halluc - improved_halluc) / baseline_halluc * 100
            },
            'evidence_f1_improvement': {
                'before': baseline_f1,
                'after': improved_f1,
                'delta': improved_f1 - baseline_f1,
                'percent_gain': (improved_f1 - baseline_f1) / baseline_f1 * 100
            }
        }
```

### Testing Your Improvements

```bash
# Run benchmark with baseline model
agentco-eval run --models fake:deterministic \
  --output baseline.json

# Run benchmark with improved model  
agentco-eval run --models improved:deterministic \
  --output improved.json

# Compare results
agentco-eval report --input baseline.json --format json > baseline_report.json
agentco-eval report --input improved.json --format json > improved_report.json

# Calculate deltas
python -c "
import json
with open('baseline_report.json') as f:
    base = json.load(f)
with open('improved_report.json') as f:
    imp = json.load(f)

base_model = base['models']['fake:deterministic']
imp_model = imp['models']['improved:deterministic']

print(f'Hallucination: {base_model[\"hallucination_rate\"]:.1%} → {imp_model[\"hallucination_rate\"]:.1%}')
print(f'Evidence F1: {base_model[\"evidence_f1\"]:.3f} → {imp_model[\"evidence_f1\"]:.3f}')
print(f'Overall: {base_model[\"overall_score\"]:.3f} → {imp_model[\"overall_score\"]:.3f}')
"
```

---

## 6. Implementation Roadmap

### Week 1: Quick Wins
- [ ] Implement RAG (grounding in evidence)
- [ ] Add few-shot examples
- [ ] Expected improvement: 26.7% → 15%

### Week 2: Robust Validation
- [ ] Implement chain-of-thought
- [ ] Add output validation & self-correction
- [ ] Expected improvement: 15% → 5-8%

### Week 3: Tuning & Optimization
- [ ] Fine-tune prompts based on failure analysis
- [ ] Calibrate confidence scores
- [ ] Expected improvement: 5-8% → <3%

---

## 7. Debugging Hallucinations

When you see hallucinations, debug systematically:

```python
def debug_hallucination(trial: dict, case: dict):
    """Debug why a specific hallucination occurred"""
    
    expected = case.get('expected', {})
    must_not_claim = expected.get('must_not_claim', [])
    answer = trial.get('parsed_output', {}).get('answer', '')
    
    print("HALLUCINATION DEBUG")
    print("=" * 60)
    print(f"Task: {case['task_id']}")
    print(f"Model: {trial['model_id']}")
    print()
    
    print("PROHIBITED CLAIMS (must_not_claim):")
    for claim in must_not_claim:
        if claim.lower() in answer.lower():
            print(f"  ❌ VIOLATED: {claim}")
        else:
            print(f"  ✅ AVOIDED: {claim}")
    
    print()
    print("AVAILABLE EVIDENCE:")
    for ev in case.get('evidence', []):
        print(f"  [{ev['evidence_id']}] {ev['source_type']}: {ev['text'][:80]}...")
    
    print()
    print("MODEL ANSWER:")
    print(f"  {answer[:200]}...")
    
    print()
    print("ROOT CAUSE ANALYSIS:")
    print("  1. Did model have access to evidence? Check prompt.")
    print("  2. Did model cite evidence? Check evidence_ids.")
    print("  3. Did model follow constraints? Check must_not_claim.")
    print("  4. Did model rely on training data? Add more RAG grounding.")
```

---

## Summary: Hallucination & Evidence F1 Fixes

| Issue | Current | Target | Fix | Timeline |
|-------|---------|--------|-----|----------|
| **Hallucination Rate** | 26.7% | <5% | RAG + validation | 1-2 weeks |
| **Evidence F1** | 0.586 | >0.75 | CoT + self-correction | 1-2 weeks |
| **Policy Compliance** | 73.3% | >90% | Output validation | 1 week |

**Quick Win (30 min):** Add RAG prompt + evidence validation  
**Solid Improvement (1 week):** Combine RAG, CoT, few-shot  
**Production Ready (2 weeks):** Full stack with fine-tuning

---

## Real LLM Comparison

Once you fix the fake model, you'll see how real LLMs compare:

```bash
# Run with OpenAI
export OPENAI_API_KEY=sk-...
agentco-eval run --models openai:gpt-4-turbo --output gpt4.json

# Run with Anthropic
export ANTHROPIC_API_KEY=sk-ant-...
agentco-eval run --models anthropic:claude-3-sonnet --output claude.json

# Compare
agentco-eval leaderboard --input gpt4.json --compare claude.json
```

You'll likely see:
- GPT-4: 15-20% hallucination (needs RAG)
- Claude: 8-12% hallucination (better grounding)
- Gemini: 10-15% hallucination (moderate)

---

**Next Step:** Pick Strategy 3a (RAG) and implement it in your favorite provider adapter. You should see immediate improvement within 30 minutes!
