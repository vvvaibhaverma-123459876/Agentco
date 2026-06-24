/**
 * Mock Web Data
 * =============
 * Curated, deterministic test data for web searches and page fetches.
 * Used by MockWebAdapter for CI testing without network dependency.
 */

export const MOCK_DATA = {
  searches: {
    'autonomy AI agents': {
      results: [
        {
          url: 'https://example.com/autonomy-research',
          title: 'The State of AI Autonomy: A 2024 Review',
          snippet:
            'Recent advances in autonomous AI systems show significant progress in reasoning, planning, and self-correction.',
          rank: 1,
        },
        {
          url: 'https://example.com/agents-survey',
          title: 'Survey: Autonomous Agents and Multi-Agent Systems',
          snippet:
            'Comprehensive review of agent architectures, including ReAct, function-calling, and end-to-end autonomy.',
          rank: 2,
        },
        {
          url: 'https://example.com/loop-closure',
          title: 'Closing the Loop: Action Execution in Autonomous Agents',
          snippet:
            'How to connect decision-making to real-world action execution, avoiding silent failures and infinite loops.',
          rank: 3,
        },
      ],
    },
    'web research agent': {
      results: [
        {
          url: 'https://example.com/web-search-agents',
          title: 'Web Search Integration in Autonomous Agents',
          snippet:
            'Best practices for integrating web search, page fetching, and evidence extraction into agentic loops.',
          rank: 1,
        },
        {
          url: 'https://example.com/evidence-gathering',
          title: 'Evidence-Based Reasoning in AI Systems',
          snippet: 'How to collect, verify, and use external evidence to ground AI reasoning.',
          rank: 2,
        },
      ],
    },
    'AI safety governance': {
      results: [
        {
          url: 'https://example.com/safety-frameworks',
          title: 'Governance Frameworks for Autonomous AI',
          snippet:
            'Overview of policies, constraints, and approval mechanisms for autonomous system control.',
          rank: 1,
        },
        {
          url: 'https://example.com/risk-management',
          title: 'Risk Assessment and Mitigation for AI Autonomy',
          snippet:
            'Techniques for identifying, measuring, and mitigating risks in autonomous agent systems.',
          rank: 2,
        },
      ],
    },
  },

  fetches: {
    'https://example.com/autonomy-research': {
      title: 'The State of AI Autonomy: A 2024 Review',
      content: `
# The State of AI Autonomy: A 2024 Review

## Abstract
Recent advances in autonomous AI systems show significant progress in reasoning, planning, and self-correction. This review examines the current state of the art in autonomous agent development.

## Key Findings

### 1. Autonomy Requires Closed Loops
The most critical insight from 2024 research is that agent autonomy depends on closing the decision-execution loop. Reasoning without action, or action without observation, is fundamentally limited.

**Evidence:**
- ReAct (Yao et al., 2022) demonstrated that interleaving reasoning with action improves performance
- Function-calling in GPT-4 showed 40% improvement when paired with mandatory observation steps
- Agents that plan without executing achieve <15% task success rates

### 2. Loop Closure Requires Three Components
1. **Decision:** Structured output (ActionSpec) from LLM
2. **Execution:** Real tool invocation with observable result
3. **Observation:** State update based on result

Systems that skip any component fail to improve.

### 3. Evidence-Backed Claims Are Critical
When agents generate knowledge, it must be traceable to sources.

**Study Results:**
- Claims with evidence citations have 3x higher acceptance
- Unsupported claims cause downstream hallucination
- Enforcing evidence requirements reduces errors by 45%

### 4. Loop Detection Prevents Infinite Execution
Agents often repeat the same action when uncertain. Detecting loops (3+ identical actions, or 5+ no-progress) allows forced adaptation.

**Findings:**
- 30% of early autonomy runs got stuck in loops without detection
- Loop detection + replan strategy reduced infinite loops to <2%

### 5. Multi-Agent Systems Require Explicit Boundaries
When agents spawn other agents, unbounded nesting causes resource exhaustion. Successful systems impose:
- Role whitelists
- Budget enforcement (tokens, time, iterations)
- Depth limits (typically 2 levels)

## Conclusion
Autonomous AI systems in 2024 are moving toward explicit loop closure, evidence backing, and bounded multi-agent coordination. Systems that implement these patterns show 2-5x improvement in task completion rates.

## References
- Yao et al. (2022). "ReAct: Synergizing Reasoning and Acting in Language Models"
- OpenAI (2023). "GPT-4 Technical Report"
- Various benchmark results from WebArena and TheAgentCompany
      `,
    },

    'https://example.com/agents-survey': {
      title: 'Survey: Autonomous Agents and Multi-Agent Systems',
      content: `
# Autonomous Agents and Multi-Agent Systems: A Comprehensive Survey

## 1. Agent Architecture Patterns

### Pattern 1: ReAct (Reasoning + Acting)
Alternates between reasoning and acting based on environment feedback.

Pseudocode:
\`\`\`
goal = "Solve problem X"
while not done:
  thought = LLM.reason(goal, observations)
  action = parse_action(thought)
  observation = execute(action)
  update_memory(thought, action, observation)
\`\`\`

**Pros:** Adapts to feedback, transparent reasoning
**Cons:** Can loop indefinitely without detection

### Pattern 2: Function-Calling (OpenAI Responses API)
LLM selects tools; application executes and returns results.

\`\`\`
response = LLM.chat(
  messages=[...],
  tools=[web_search, fetch_page, generate_claim]
)
if response.tool_calls:
  for tool_call in response.tool_calls:
    result = execute_tool(tool_call)
    append_result_to_messages(result)
\`\`\`

**Pros:** Structured, controlled tool use
**Cons:** Requires tool interface overhead

### Pattern 3: Agents SDK / Orchestrator Pattern
Explicit state machine with separation of concerns.

\`\`\`
PLAN -> VALIDATE -> EXECUTE -> OBSERVE -> UPDATE_STATE
\`\`\`

**Pros:** Observable, debuggable, bounded
**Cons:** More implementation overhead

## 2. Failure Modes and Solutions

### Failure Mode: Silent Looping
Agent repeats same action without progress.

**Solutions:**
1. Loop detection (3+ identical actions)
2. No-progress tracking (5+ actions, 0 new artifacts)
3. Forced replan or termination

### Failure Mode: Unsupported Claims
Agent generates claims without evidence sources.

**Solutions:**
1. Require supportSourceIds in claims
2. Database constraints enforce non-empty evidence
3. Block claim generation if no sources

### Failure Mode: Unbounded Agent Spawning
Nested agents exhaust resources.

**Solutions:**
1. Explicit role registry (whitelist)
2. Per-agent budgets (tokens, time, iterations)
3. Depth limits (max 2-3 levels)

## 3. Multi-Agent Coordination

### Voting/Ensemble Approach
Multiple expert agents provide solutions; majority rules.

**Use Case:** When accuracy matters more than coverage

### Team Hierarchy Approach
Agents organized by role and responsibility.

**Use Case:** Complex domain problems with clear specialization

### Society Pattern
Multiple institutions (domain specializations), agents organized by expertise.

**Use Case:** Large-scale systems with emergent behavior

## References
- This survey draws from OpenAI, Anthropic, and academic research on autonomous systems
- Key papers: ReAct, MCTS-based planning, chain-of-thought reasoning
      `,
    },

    'https://example.com/loop-closure': {
      title: 'Closing the Loop: Action Execution in Autonomous Agents',
      content: `
# Closing the Loop: Action Execution in Autonomous Agents

## The Core Problem

Many early AI agent systems fail because they decouple reasoning from execution:

1. **Reasoning-Only Systems:** Agent chains multiple thoughts but never executes tools.
2. **Execution-Only Systems:** Agent calls tools but doesn't learn from results.
3. **Observation-Missing Systems:** Agent acts and reasons but doesn't capture state changes.

Result: Agent gets stuck in local optima or repeats same action indefinitely.

## The Solution: Closed-Loop Architecture

Every autonomous system needs:

### 1. Decision Phase
- LLM or planner produces structured ActionSpec
- Spec includes: action_type, objective, args, success_criteria, fallback
- Spec is validated before execution

### 2. Execution Phase
- Application (not LLM) executes the action
- Returns typed ActionResult with status, observations, artifacts
- Status is always set (COMPLETED, BLOCKED, or FAILED)

### 3. Observation Phase
- Results are structured and stored
- New artifacts are tracked
- State is updated

### 4. Next Decision Phase
- LLM uses observations to decide next action
- Loop detects if agent is repeating
- Adaptation triggered if stuck

## Key Insight: The Application Owns Execution

The LLM decides WHAT to do, but the APPLICATION decides IF it can be done.

**Bad Pattern:**
\`\`\`
decision = LLM.decide()
# LLM output treated as authoritative
execute(decision)  # May silently fail
\`\`\`

**Good Pattern:**
\`\`\`
spec = LLM.planNextAction()
result = executor.execute(spec)
if result.status == BLOCKED:
  reason = result.blockedReason  # Why execution was denied
  next_spec = LLM.planNextAction(feedback=reason)
\`\`\`

## Implementation Checklist

- [ ] Decisions produce ActionSpec (structured, not prose)
- [ ] Executor always returns ActionResult with status enum
- [ ] Status is COMPLETED or BLOCKED or FAILED (never null)
- [ ] Observations are stored for next iteration
- [ ] Loop detection runs after every action
- [ ] Loop triggers forced replan or termination

## Conclusion

Closing the loop is the difference between a chatbot and an autonomous agent.
      `,
    },
  },
};
