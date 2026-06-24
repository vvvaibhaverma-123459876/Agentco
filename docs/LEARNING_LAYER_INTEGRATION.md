# Learning Layer Integration

## Overview

The Autonomous Learning Layer is now integrated across all major systems:

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT DECISIONS & OPERATIONS                 │
├─────────────────────────────────────────────────────────────────┤
│                     ↓ capture signals                            │
├─────────────────────────────────────────────────────────────────┤
│           TypeScript Learning Service (learning.service.ts)      │
│  • Signal capture & queuing                                      │
│  • Signal → Insight transformation                               │
│  • Adaptation proposal generation                                │
│  • API routes for learning operations                            │
├─────────────────────────────────────────────────────────────────┤
│                    ↓ process & analyze                           │
├─────────────────────────────────────────────────────────────────┤
│         Python Learning Bridge (learning_bridge.py)              │
│  • Connect TypeScript backend with Python learning loop          │
│  • AutonomousLearningLoop integration                            │
│  • Evidence kernel integration                                   │
│  • Memory persistence                                            │
│  • Institutional governance                                      │
├─────────────────────────────────────────────────────────────────┤
│                    ↓ generate insights                           │
├─────────────────────────────────────────────────────────────────┤
│      Python AutonomousLearningLoop (learning/cycle.py)           │
│  • Claim extraction from signals                                 │
│  • Hypothesis generation & validation                            │
│  • Risk assessment                                               │
│  • Experiment proposal                                           │
│  • Memory write (provenance tracking)                            │
│  • Uncertainty-driven decisions                                  │
├─────────────────────────────────────────────────────────────────┤
│                  ↓ feedback to agents                            │
├─────────────────────────────────────────────────────────────────┤
│     Agent Decision Middleware (agents.routes.ts)                 │
│  • Learning insights inform next decisions                       │
│  • Confidence calibration from learning                          │
│  • Governance approvals for risky changes                        │
│  • Outcome feedback closes the loop                              │
└─────────────────────────────────────────────────────────────────┘
```

## Integration Points

### 1. Agent Dispatch Pipeline (INTEGRATED ✓)

**File**: `backend/src/routes/agents.routes.ts`

**What happens**:
- Agent receives dispatch request
- Learning signal captured: decision type
- Task executed
- Learning signal captured: outcome type
- Memory updated with results

**Code**:
```typescript
learningService.captureSignal(
  id,
  'decision',
  { task_type, payload, agent_id: id, ... },
  `agent://dispatch/${task.task_id}`,
);
```

### 2. Learning Service (INTEGRATED ✓)

**File**: `backend/src/services/learning.service.ts`

**Functionality**:
- Signal capture & queuing
- Insight generation (confidence, risk, recommendations)
- Proposal creation (decision_refinement, institutional_change, governance_update)
- API endpoints:
  - `POST /api/learning/signal` - Capture signal
  - `GET /api/learning/stats` - Learning stats
  - `GET /api/learning/agent/:agent_id` - Agent learning history
  - `POST /api/learning/proposals/:proposal_id/apply` - Apply learning-based change

### 3. Learning Bridge (INTEGRATED ✓)

**File**: `backend/src/services/learning_bridge.py`

**Purpose**: Bridge TypeScript backend with Python autonomous learning loop

**Capabilities**:
- Process signals through AutonomousLearningLoop
- Extract claims from natural language signals
- Validate hypotheses
- Assess risk levels
- Generate recommendations
- Approve proposals institutionally

### 4. Memory Integration (INTEGRATED ✓)

**Files**:
- `memory_kernel/memory_kernel.py` - Stores learning experiences
- `learning_bridge.py` - Writes outcomes to memory

**What's tracked**:
- Every signal processed
- Every insight generated
- Every proposal created
- Approval/rejection decisions
- Outcomes of applied changes

## Signal Types

All major operations capture learning signals:

```python
# Decision signals
learningService.captureSignal(agent_id, 'decision', {
  'decision': str,
  'evidence': str,
  'confidence': float,
  ...
})

# Outcome signals
learningService.captureSignal(agent_id, 'outcome', {
  'task_id': str,
  'outcome': 'success' | 'failed',
  'result': Any,
  ...
})

# Evidence update signals
learningService.captureSignal(agent_id, 'evidence_update', {
  'claim': str,
  'evidence': str,
  'source': str,
  ...
})

# Contradiction signals
learningService.captureSignal(agent_id, 'contradiction', {
  'claim1': str,
  'claim2': str,
  'independent': bool,
  ...
})
```

## Feedback Loop

### Signal → Insight → Proposal → Decision → Outcome → Signal

1. **Signal Capture**: Agent action generates signal (decision, outcome, evidence, contradiction)
2. **Signal Processing**: Learning service queues and processes asynchronously
3. **Learning Analysis**: Python bridge runs AutonomousLearningLoop
4. **Insight Generation**: Claims extracted, hypotheses validated, risk assessed
5. **Proposal Creation**: Institutional changes proposed if confidence > 0.7
6. **Governance Decision**: Proposals approved/rejected based on evidence quality
7. **Outcome Recording**: Results stored in memory kernel
8. **Next Signal**: Learning from outcome informs next decision

## What Still Needs Integration

### High Priority

- [ ] **Evidence Integration**: Connect evidence_update signals to EvidenceKernel.create_claim()
- [ ] **Override Queue**: Capture escalation decisions as learning signals
- [ ] **Audit Log**: Feed audit events to learning as outcome signals
- [ ] **Real-time Feedback**: Apply approved learning proposals to live agents

### Medium Priority

- [ ] **Dashboard**: Learning statistics in frontend (/api/learning/stats)
- [ ] **Batch Processing**: Async learning service for high-volume signal processing
- [ ] **Model Fine-tuning**: Use learning insights to adjust model selection/prompts
- [ ] **Confidence Calibration**: Learning outcomes → dynamic confidence adjustments

### Lower Priority

- [ ] **Cross-agent Learning**: Share insights between agents
- [ ] **Institutional Evolution**: Governance structure adapts based on learning
- [ ] **Causal Analysis**: Understand which learning led to which outcomes
- [ ] **Prediction**: Forecast outcomes based on learning history

## How to Add Learning to Any Operation

**Pattern**:

```typescript
// Before operation
const context = { agent_id, operation, payload };

// Execute operation
const result = await someOperation();

// Capture outcome signal
learningService.captureSignal(
  agent_id,
  'outcome',
  {
    operation,
    success: result.ok,
    result: result.data,
    confidence: 0.8,
  },
  `system://operation/${operation}/${Date.now()}`,
);
```

## Testing Learning Integration

```bash
# Run test with learning enabled
curl -X POST http://localhost:3001/api/agents/test-agent/dispatch \
  -H "Content-Type: application/json" \
  -d '{"task_type":"test","payload":{}}'

# Check learning stats
curl http://localhost:3001/api/learning/stats

# Check agent learning history
curl http://localhost:3001/api/learning/agent/test-agent
```

## Monitoring

**Key metrics**:
- `total_signals`: Signals captured
- `total_insights`: Insights generated
- `total_proposals`: Proposals created
- `proposals_active`: Applied changes
- `avg_confidence`: Average insight quality
- `processing_queue`: Pending signals

Access via: `GET /api/learning/stats`

## Performance Considerations

1. **Signal Queuing**: Signals are queued and processed asynchronously to avoid blocking agent operations
2. **Memory Growth**: Monitor memory_kernel size; old events can be archived
3. **Proposal Limit**: Cap active proposals per agent to prevent overflow
4. **Confidence Threshold**: Only create proposals if insight confidence > 0.7

## Future: Full System Autonomy

Once fully integrated, the learning layer enables:
- **Self-healing**: Agents detect their own failures and propose fixes
- **Self-improvement**: Learning insights → better decisions → positive outcomes
- **Institutional adaptation**: Governance structures evolve based on learning
- **Cross-agent coordination**: Agents learn from each other's experiences
