import crypto from 'crypto';
import { query, withClient } from '../db/client';
import { auditLog } from './audit-log.service';
import { eventBus } from './event-bus.service';
import { provenance } from './provenance.service';

export type TaskStatus = 'queued' | 'running' | 'done' | 'failed' | 'blocked';

export interface WorkflowTask {
  task_id: string;
  agent_id: string;
  task_type: string;
  payload: Record<string, unknown>;
  queued_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  status: TaskStatus;
  result?: unknown;
  error?: string | null;
  audit_log_id?: string | null;
  event_id?: string | null;
  action_attestation_id?: string | null;
}

export class DurableExecutionService {
  async enqueue(agent_id: string, task_type: string, payload: Record<string, unknown>): Promise<WorkflowTask> {
    const rows = await query<WorkflowTask>(
      `INSERT INTO workflow_tasks (agent_id, task_type, payload, status)
       VALUES ($1,$2,$3,'queued') RETURNING *`,
      [agent_id, task_type, JSON.stringify(payload)],
    );
    return rows[0];
  }

  async get(task_id: string): Promise<WorkflowTask | null> {
    const rows = await query<WorkflowTask>('SELECT * FROM workflow_tasks WHERE task_id=$1', [task_id]);
    return rows[0] ?? null;
  }

  async list(): Promise<WorkflowTask[]> {
    return query<WorkflowTask>('SELECT * FROM workflow_tasks ORDER BY queued_at DESC LIMIT 200');
  }

  async run(task_id: string): Promise<WorkflowTask> {
    const task = await this.claim(task_id);
    if (!task) throw new Error(`task not found or not runnable: ${task_id}`);
    try {
      const result = await this.dispatch(task);
      const confidence_score = 0.8;
      const risk_level = 'low' as const;
      const attestation = await provenance.attestAction({
        principal_id: task.agent_id,
        tool_id: task.task_type,
        input: task.payload,
        output: result,
        trusted_confidence: confidence_score,
        risk_level,
        tee_quote: 'local-measured-backend-dispatch-v1',
      });
      const log_id = await auditLog.append({
        agent_id: task.agent_id,
        action_type: 'decision',
        input_summary: JSON.stringify({ task_type: task.task_type, payload: task.payload }).slice(0, 500),
        output_summary: JSON.stringify(result).slice(0, 500),
        confidence_score,
        risk_level,
        session_id: task.task_id,
      });
      const event_id = crypto.randomUUID();
      await eventBus.publish({
        event_id,
        event_type: `${task.agent_id}.task_completed`,
        producer_agent_id: task.agent_id,
        timestamp: new Date().toISOString(),
        confidence_score,
        payload: { task_id: task.task_id, task_type: task.task_type, log_id, action_id: attestation.action_id },
        correlation_id: task.task_id,
        risk_level,
        requires_ack: false,
      }).catch(() => undefined);
      await query(
        `UPDATE workflow_tasks
         SET status='done', completed_at=now(), result=$2, audit_log_id=$3, event_id=$4, action_attestation_id=$5
         WHERE task_id=$1`,
        [task.task_id, JSON.stringify(result), log_id, event_id, attestation.action_id],
      );
    } catch (err) {
      await query(
        `UPDATE workflow_tasks SET status='failed', completed_at=now(), error=$2 WHERE task_id=$1`,
        [task.task_id, String(err)],
      );
    }
    return (await this.get(task.task_id)) as WorkflowTask;
  }

  private async claim(task_id: string): Promise<WorkflowTask | null> {
    return withClient(async client => {
      await client.query('BEGIN');
      const { rows } = await client.query<WorkflowTask>(
        `UPDATE workflow_tasks
         SET status='running', started_at=now(), claimed_by='backend-dispatcher'
         WHERE task_id=$1 AND status IN ('queued','failed')
         RETURNING *`,
        [task_id],
      );
      await client.query('COMMIT');
      return rows[0] ?? null;
    });
  }

  private async dispatch(task: WorkflowTask): Promise<Record<string, unknown>> {
    this.validatePayload(task);
    if (task.task_type === 'health_check') {
      return {
        kind: 'health_check_result',
        agent_id: task.agent_id,
        received_payload_hash: crypto.createHash('sha256').update(JSON.stringify(task.payload)).digest('hex'),
        executed_by: 'durable-execution-service',
      };
    }
    if (task.task_type === 'record_observation') {
      return {
        kind: 'observation_recorded',
        agent_id: task.agent_id,
        observation: task.payload,
        executed_by: 'durable-execution-service',
      };
    }
    if (task.task_type === 'review') {
      return this.executeReview(task);
    }
    if (task.task_type === 'decision') {
      return this.executeDecision(task);
    }
    if (task.task_type === 'llm_call') {
      return this.executeLlmCall(task);
    }
    if (task.task_type === 'calibration') {
      const confidence = Number(task.payload.confidence);
      const outcome = task.payload.outcome === true || task.payload.outcome === 1 ? 1 : 0;
      return {
        kind: 'calibration_score',
        prediction_id: task.payload.prediction_id ?? null,
        confidence,
        outcome,
        brier_score: Math.pow(confidence - outcome, 2),
        executed_by: 'durable-execution-service',
      };
    }
    throw new Error(`unsupported durable task_type: ${task.task_type}`);
  }

  private validatePayload(task: WorkflowTask): void {
    const payload = task.payload || {};
    if (task.task_type === 'llm_call') {
      if (typeof payload.prompt !== 'string' || payload.prompt.trim().length === 0) {
        throw new Error('llm_call payload requires non-empty prompt');
      }
    } else if (task.task_type === 'calibration') {
      const confidence = Number(payload.confidence);
      const outcome = payload.outcome;
      if (!Number.isFinite(confidence) || confidence < 0 || confidence > 1) {
        throw new Error('calibration payload requires confidence in [0, 1]');
      }
      if (![0, 1, true, false].includes(outcome as any)) {
        throw new Error('calibration payload requires boolean/binary outcome');
      }
    } else if (task.task_type === 'review') {
      if (typeof payload.subject !== 'string' || payload.subject.trim().length === 0) {
        throw new Error('review payload requires non-empty subject');
      }
      if (!Array.isArray(payload.criteria) || payload.criteria.length === 0) {
        throw new Error('review payload requires non-empty criteria array');
      }
    } else if (task.task_type === 'decision') {
      if (!Array.isArray(payload.options) || payload.options.length < 2) {
        throw new Error('decision payload requires at least two options');
      }
      if (!Array.isArray(payload.criteria) || payload.criteria.length === 0) {
        throw new Error('decision payload requires non-empty criteria array');
      }
    }
  }

  private async executeLlmCall(task: WorkflowTask): Promise<Record<string, unknown>> {
    const response = await this.callLLMJson(
      'You execute AgentCo durable LLM tasks. Return JSON with keys answer and confidence.',
      String(task.payload.prompt),
    );
    return {
      kind: 'llm_call_result',
      answer: response.answer ?? response.review ?? response.decision ?? response,
      confidence: clampConfidence(response.confidence),
      model: process.env.LLM_MODEL_DEFAULT || 'gpt-4o-mini',
      executed_by: 'durable-execution-service',
    };
  }

  private async executeReview(task: WorkflowTask): Promise<Record<string, unknown>> {
    const payload = task.payload;
    const response = await this.callLLMJson(
      'You are AgentCo Review Service. Produce evidence-governed JSON only. Keys: decision, findings, required_changes, confidence, evidence_ids_used. decision must be approve, changes_requested, reject, or escalate.',
      JSON.stringify({
        subject: payload.subject,
        criteria: payload.criteria,
        evidence: payload.evidence ?? [],
        risk_level: payload.risk_level ?? 'medium',
      }),
    );
    const decision = String(response.decision ?? '').toLowerCase();
    if (!['approve', 'changes_requested', 'reject', 'escalate'].includes(decision)) {
      throw new Error(`review service returned invalid decision: ${decision}`);
    }
    return {
      kind: 'review_result',
      decision,
      findings: Array.isArray(response.findings) ? response.findings : [],
      required_changes: Array.isArray(response.required_changes) ? response.required_changes : [],
      confidence: clampConfidence(response.confidence),
      evidence_ids_used: Array.isArray(response.evidence_ids_used) ? response.evidence_ids_used : [],
      executed_by: 'durable-execution-service',
    };
  }

  private async executeDecision(task: WorkflowTask): Promise<Record<string, unknown>> {
    const payload = task.payload;
    const options = payload.options as unknown[];
    const response = await this.callLLMJson(
      'You are AgentCo Decision Service. Produce evidence-governed JSON only. Keys: selected_option, rationale, confidence, evidence_ids_used, escalation_required. selected_option must exactly match one provided option unless escalation_required is true.',
      JSON.stringify({
        decision_question: payload.question ?? payload.subject ?? 'Select the safest option.',
        options,
        criteria: payload.criteria,
        evidence: payload.evidence ?? [],
        risk_level: payload.risk_level ?? 'medium',
      }),
    );
    const selected = response.selected_option;
    const escalationRequired = response.escalation_required === true;
    if (!escalationRequired && !options.includes(selected)) {
      throw new Error(`decision service returned option not present in payload: ${String(selected)}`);
    }
    return {
      kind: 'decision_result',
      selected_option: escalationRequired ? null : selected,
      rationale: String(response.rationale ?? ''),
      confidence: clampConfidence(response.confidence),
      evidence_ids_used: Array.isArray(response.evidence_ids_used) ? response.evidence_ids_used : [],
      escalation_required: escalationRequired,
      executed_by: 'durable-execution-service',
    };
  }

  private async callLLMJson(system: string, user: string): Promise<Record<string, any>> {
    const apiKey = process.env.LLM_API_KEY || process.env.OPENAI_API_KEY;
    if (!apiKey) {
      throw new Error('LLM_API_KEY or OPENAI_API_KEY is required for durable LLM-backed task execution');
    }
    const baseUrl = (process.env.LLM_BASE_URL || 'https://api.openai.com/v1').replace(/\/$/, '');
    const model = process.env.LLM_MODEL_DEFAULT || 'gpt-4o-mini';
    const response = await fetch(`${baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model,
        temperature: 0,
        response_format: { type: 'json_object' },
        messages: [
          { role: 'system', content: system },
          { role: 'user', content: user },
        ],
      }),
    });
    if (!response.ok) {
      throw new Error(`durable LLM task failed: HTTP ${response.status}`);
    }
    const body = await response.json() as { choices?: Array<{ message?: { content?: string } }> };
    const content = body.choices?.[0]?.message?.content;
    if (!content) {
      throw new Error('durable LLM task returned empty content');
    }
    return JSON.parse(content);
  }
}

export const durableExecution = new DurableExecutionService();

function clampConfidence(value: unknown): number {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 0;
  return Math.max(0, Math.min(1, numeric));
}
