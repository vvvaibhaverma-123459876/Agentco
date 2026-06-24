# Round 4: Diverse Target Sources for Claim Extraction

## Objective
Extract claims from 8-10 papers with **different topics** (not repeating causation/scaling/deployment) to improve diversity and accuracy toward 85% threshold.

## Selected Papers

### 1. Vision-Language Models
- **URL**: https://arxiv.org/abs/2310.16934
- **Title**: GPT-4V(ision) System Card
- **Topic**: Multimodal capabilities, safety properties, limitations
- **Expected Claims**: Specific vision+language capabilities, safety evaluation results, limitations by domain

### 2. Alignment & Safety
- **URL**: https://arxiv.org/abs/2305.00050
- **Title**: Constitutional AI: Harmlessness from AI Feedback
- **Topic**: Alignment methodology, scaling properties of RLHF, safety evaluation
- **Expected Claims**: Constitutional AI reduces harmful outputs by X%, specific evaluation metrics, methodology details

### 3. Agent Reasoning
- **URL**: https://arxiv.org/abs/2310.03684
- **Title**: Reflexion: Language Agents with Verbal Reinforcement Learning
- **Topic**: Agent self-improvement, reflection mechanisms, task performance
- **Expected Claims**: Reflexion improves success rate, specific benchmark results, methodology for in-context learning

### 4. Knowledge Distillation
- **URL**: https://arxiv.org/abs/2306.01400
- **Title**: Distilling the Knowledge in a Neural Network
- **Topic**: Model compression, performance trade-offs, training methodology
- **Expected Claims**: Distillation maintains X% of original performance, compression ratios, temperature coefficients

### 5. Prompt Engineering
- **URL**: https://arxiv.org/abs/2201.11903
- **Title**: Chain-of-Thought Prompting Elicits Reasoning in Large Language Models
- **Topic**: Prompting techniques, zero-shot reasoning, benchmark improvements
- **Expected Claims**: CoT improves accuracy on specific benchmarks, specific prompt formats, generalization properties

### 6. Interpretability
- **URL**: https://arxiv.org/abs/2212.03860
- **Title**: Scaling Monosemanticity: Interpreting Superposition in Neural Networks
- **Topic**: Neural network interpretability, feature analysis, scaling behavior
- **Expected Claims**: Superposition mechanism description, feature interpretation accuracy, scaling patterns

### 7. Training Efficiency
- **URL**: https://arxiv.org/abs/2309.01882
- **Title**: Flash Attention: Fast and Memory-Efficient Exact Attention with IO-Awareness
- **Topic**: Attention efficiency, computational improvements, throughput gains
- **Expected Claims**: Reduces memory by X%, improves speed by Y%, maintains exact attention

### 8. Model Evaluation
- **URL**: https://arxiv.org/abs/2306.05685
- **Title**: AlpacaEval: An Automatic Evaluator of Instruction-following Language Models
- **Topic**: Evaluation methodology, benchmark design, reliability analysis
- **Expected Claims**: AlpacaEval correlates with human judgement, specific correlation metrics, evaluation reliability

### 9. Emergent Abilities
- **URL**: https://arxiv.org/abs/2206.07682
- **Title**: Emergent Abilities of Large Language Models
- **Topic**: Scaling, emergent capabilities, phase transitions
- **Expected Claims**: Specific tasks exhibit emergent abilities, scaling laws, benchmark results

### 10. In-Context Learning
- **URL**: https://arxiv.org/abs/2212.04037
- **Title**: Larger Language Models Do In-Context Learning Differently
- **Topic**: In-context learning mechanisms, scaling effects, learning dynamics
- **Expected Claims**: Scaling changes in-context learning mechanism, specific experimental evidence, efficiency metrics

---

## Extraction Strategy

1. **Fetch each paper's abstract and introduction** (already extracted from arXiv HTML)
2. **Extract 2-4 specific claims per paper** using improved prompt:
   - Focus on **concrete findings** (not methodology descriptions)
   - Require **specific metrics or numbers** where available
   - Avoid generic statements
   - Prefer novel/surprising claims over standard results

3. **Claim Categories Expected**:
   - Methodological contributions (what technique was introduced)
   - Performance improvements (X% increase, Y seconds faster)
   - Limitations or trade-offs (when method fails)
   - Surprising findings (unexpected scaling behavior)

4. **Target claim count**: 2-4 per paper × 10 papers = 20-40 new claims
5. **Validation diversity**: Mix of high-confidence (88%+ likely TRUE) and exploratory (50%+ confident UNRESOLVED)
6. **Combined total**: 48 existing + 30 new = 78 total claims
7. **Target accuracy**: If new claims average 85%+, combined accuracy: (48×0.69 + 30×0.85) / 78 = **78%+** toward 85% threshold

---

## Next Steps

1. Fetch full papers (or at least abstracts + introduction sections)
2. Run claim extraction with improved prompt
3. Deduplicate against existing claims
4. Export for validation
5. Validate and compute metrics
6. Assess progress toward 85% gate

