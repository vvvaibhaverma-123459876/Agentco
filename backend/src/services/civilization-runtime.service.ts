import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { db } from '../db/client';
import { domainRegistry, QualifiedInstitutionRoute } from './domain-registry.service';

type RuntimeNodeStatus = 'reachable' | 'missing';
type DispatchType = 'institution' | 'coalition';
type DispatchStatus = 'dispatched' | 'failed';

export interface CivilizationRuntimeNode {
  id: string;
  layer: string;
  requiredTables: string[];
  requiredRoutes: string[];
  status: RuntimeNodeStatus;
  missingTables: string[];
  missingRoutes: string[];
}

export interface CivilizationReachabilityTick {
  runId: string;
  correlationId: string;
  runtimeMode: string;
  tickId: string;
  tickType: 'reachability_gate';
  status: 'passed' | 'failed';
  nodes: CivilizationRuntimeNode[];
  missingTables: string[];
  missingRoutes: string[];
}

export interface CivilizationDispatchGoalInput {
  goalId?: string;
  objective: string;
  domains: string[];
  rigorTier?: 'lite' | 'full';
  riskLevel?: 'low' | 'medium' | 'high';
  budget?: {
    tokens?: number;
    iterations?: number;
    seconds?: number;
  };
  runtimeMode?: string;
}

export interface CivilizationDispatchAssignment {
  institutionId: string;
  departmentId: string;
  domains: string[];
  workRequestId: string;
  matchTypes: Array<QualifiedInstitutionRoute['match_type']>;
  trustFactors: number[];
}

export interface CivilizationDispatchTick {
  runId: string;
  correlationId: string;
  runtimeMode: string;
  tickId: string;
  tickType: 'dispatch_tick';
  status: DispatchStatus;
  dispatchType: DispatchType | null;
  goalId: string;
  objective: string;
  domains: string[];
  missingDomains: string[];
  assignments: CivilizationDispatchAssignment[];
  coalitionId: string | null;
}

const RUNTIME_GRAPH: Array<Omit<CivilizationRuntimeNode, 'status' | 'missingTables' | 'missingRoutes'>> = [
  {
    id: 'runtime_substrate_and_idempotency',
    layer: 'L0',
    requiredTables: ['build_ledger', 'idempotency_records'],
    requiredRoutes: ['/system/build-status', '/system/readiness', '/system/feature-gates'],
  },
  {
    id: 'identity_authority',
    layer: 'L1',
    requiredTables: ['actors', 'permissions', 'event_log'],
    requiredRoutes: ['/identity/actors', '/identity/verify'],
  },
  {
    id: 'resource_budgeting',
    layer: 'L2',
    requiredTables: [
      'resource_accounts',
      'civilization_resource_accounts',
      'civilization_resource_transactions',
      'civilization_resource_reservations',
    ],
    requiredRoutes: ['/resources/accounts', '/resources/transactions/credit', '/resources/reservations'],
  },
  {
    id: 'event_audit_outbox',
    layer: 'L3',
    requiredTables: ['event_log', 'event_outbox', 'decision_log', 'audit_events'],
    requiredRoutes: ['/api/audit'],
  },
  {
    id: 'durable_task_execution',
    layer: 'L8',
    requiredTables: ['workflow_tasks', 'agent_tasks', 'agent_task_events'],
    requiredRoutes: ['/api/autonomy/tasks', '/api/autonomy/runs'],
  },
  {
    id: 'institution_registry',
    layer: 'L9',
    requiredTables: ['institutions', 'departments', 'institution_work_requests'],
    requiredRoutes: ['/api/autonomy/work-requests'],
  },
  {
    id: 'constitution_and_policy',
    layer: 'L10',
    requiredTables: [
      'calibration_constitution_versions',
      'trust_policy_versions',
      'policy_canary_deployments',
      'protected_surfaces',
      'allowed_change_types',
      'prohibited_change_types',
      'self_modification_validations',
      'governance_kill_switches',
    ],
    requiredRoutes: ['/api/civilization/constitution/active', '/api/civilization/policies/active'],
  },
  {
    id: 'evidence_claim_resolution',
    layer: 'L4-L5',
    requiredTables: ['autonomy_evidence', 'autonomy_claims', 'prediction_ledger'],
    requiredRoutes: ['/api/autonomy/evidence/:sourceEvidenceId/deduplicate'],
  },
  {
    id: 'trust_memory_learning',
    layer: 'L6-L7',
    requiredTables: ['trust_scores', 'shared_knowledge', 'learner_candidates'],
    requiredRoutes: ['/api/civilization/reputation/:entityType/:entityId', '/api/learning/stats'],
  },
  {
    id: 'civilization_runtime_trace',
    layer: 'L14',
    requiredTables: [
      'civilization_vertical_slice_runs',
      'civilization_coordinator_ticks',
      'civilization_generality_metrics',
      'domain_registry',
    ],
    requiredRoutes: [
      '/api/civilization/runtime/graph',
      '/api/civilization/runtime/reachability-tick',
      '/api/civilization/runtime/dispatch-tick',
      '/api/civilization/runtime/scheduler',
      '/api/civilization/runtime/scheduler/run-once',
    ],
  },
];

export class CivilizationRuntimeService {
  runtimeGraph(): Array<Omit<CivilizationRuntimeNode, 'status' | 'missingTables' | 'missingRoutes'>> {
    return RUNTIME_GRAPH.map(node => ({
      ...node,
      requiredTables: [...node.requiredTables],
      requiredRoutes: [...node.requiredRoutes],
    }));
  }

  async runReachabilityTick(runtimeMode = 'backend_l14_runtime'): Promise<CivilizationReachabilityTick> {
    const runId = crypto.randomUUID();
    const correlationId = crypto.randomUUID();
    const nodes = await this.evaluateRuntimeGraph();
    const missingTables = [...new Set(nodes.flatMap(node => node.missingTables))].sort();
    const missingRoutes = [...new Set(nodes.flatMap(node => node.missingRoutes))].sort();
    const status: 'passed' | 'failed' = missingTables.length === 0 && missingRoutes.length === 0 ? 'passed' : 'failed';
    const stageResults = {
      reachability_gate: {
        status,
        nodes: nodes.map(node => ({
          id: node.id,
          layer: node.layer,
          status: node.status,
          missing_tables: node.missingTables,
          missing_routes: node.missingRoutes,
          required_routes: node.requiredRoutes,
        })),
      },
    };
    const trace = [
      {
        stage: 'reachability_gate',
        status,
        checked_nodes: nodes.length,
        missing_tables: missingTables,
        missing_routes: missingRoutes,
        at: new Date().toISOString(),
      },
    ];

    await db.query(
      `INSERT INTO civilization_vertical_slice_runs
         (id, correlation_id, status, runtime_mode, stage_results, runtime_trace, failure_reason, completed_at)
       VALUES ($1,$2,$3,$4,$5::jsonb,$6::jsonb,$7,now())`,
      [
        runId,
        correlationId,
        status,
        runtimeMode,
        JSON.stringify(stageResults),
        JSON.stringify(trace),
        missingTables.length > 0 || missingRoutes.length > 0
          ? `missing tables: ${missingTables.join(', ')}; missing routes: ${missingRoutes.join(', ')}`
          : null,
      ],
    );

    const tickResult = await db.query<{ id: string }>(
      `INSERT INTO civilization_coordinator_ticks (run_id, tick_type, trace_json)
       VALUES ($1,'reachability_gate',$2::jsonb)
       RETURNING id`,
      [
        runId,
        JSON.stringify({
          correlation_id: correlationId,
          status,
          nodes,
          missing_tables: missingTables,
          missing_routes: missingRoutes,
        }),
      ],
    );

    return {
      runId,
      correlationId,
      runtimeMode,
      tickId: tickResult.rows[0].id,
      tickType: 'reachability_gate',
      status,
      nodes,
      missingTables,
      missingRoutes,
    };
  }

  async runDispatchTick(input: CivilizationDispatchGoalInput): Promise<CivilizationDispatchTick> {
    if (!input.objective.trim()) throw new Error('objective is required');
    const domains = [...new Set(input.domains.map(domain => domain.trim().toLowerCase()).filter(Boolean))];
    if (domains.length === 0) throw new Error('at least one domain is required');

    const runId = crypto.randomUUID();
    const correlationId = crypto.randomUUID();
    const goalId = input.goalId ?? crypto.randomUUID();
    const runtimeMode = input.runtimeMode ?? 'backend_l14_dispatch';
    const rigorTier = input.rigorTier ?? 'lite';
    const budget = {
      tokens: input.budget?.tokens ?? 10_000,
      iterations: input.budget?.iterations ?? (rigorTier === 'full' ? 5 : 2),
      seconds: input.budget?.seconds ?? (rigorTier === 'full' ? 1800 : 600),
    };

    const routed = await Promise.all(
      domains.map(async domain => ({
        domain,
        route: await domainRegistry.bestInstitutionForDomain(domain),
      }))
    );
    const missingDomains = routed.filter(item => item.route == null).map(item => item.domain);
    if (missingDomains.length > 0) {
      return this.persistDispatchTick({
        runId,
        correlationId,
        runtimeMode,
        status: 'failed',
        dispatchType: null,
        goalId,
        objective: input.objective,
        domains,
        missingDomains,
        assignments: [],
        coalitionId: null,
        trace: {
          reason: 'no qualifying active institution for one or more requested domains',
          requested_domains: domains,
          missing_domains: missingDomains,
        },
      });
    }

    const groups = new Map<string, { route: QualifiedInstitutionRoute; domains: string[]; routes: QualifiedInstitutionRoute[] }>();
    for (const item of routed) {
      const route = item.route as QualifiedInstitutionRoute;
      const current = groups.get(route.institution_id) ?? { route, domains: [], routes: [] };
      current.domains.push(item.domain);
      current.routes.push(route);
      groups.set(route.institution_id, current);
    }

    const dispatchType: DispatchType = groups.size > 1 ? 'coalition' : 'institution';
    const coalitionId = dispatchType === 'coalition' ? crypto.randomUUID() : null;
    const assignments: CivilizationDispatchAssignment[] = [];
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      for (const group of groups.values()) {
        const production = await client.query<{ id: string }>(
          `SELECT id
             FROM departments
            WHERE institution_id = $1
              AND name = 'Production'
              AND status = 'active'
            LIMIT 1`,
          [group.route.institution_id]
        );
        if ((production.rowCount ?? 0) !== 1) {
          throw new Error(`Production department not found for institution ${group.route.institution_id}`);
        }

        const workRequestId = crypto.randomUUID();
        const work = await client.query<{ id: string }>(
          `INSERT INTO institution_work_requests
             (id, institution_id, department_id, objective, required_specialists,
              budget_tokens, budget_iterations, budget_seconds, verification_required,
              reputation_metric, risk_level, status, autonomy_goal_id, result_summary)
           VALUES ($1,$2,$3,$4,$5::jsonb,$6,$7,$8,$9,$10,$11,'queued',$12,$13::jsonb)
           RETURNING id`,
          [
            workRequestId,
            group.route.institution_id,
            production.rows[0].id,
            input.objective,
            JSON.stringify([{ role: 'institution_production', priority: 1 }]),
            budget.tokens,
            budget.iterations,
            budget.seconds,
            rigorTier === 'full' || input.riskLevel === 'high',
            'civilization_dispatch',
            input.riskLevel ?? (rigorTier === 'full' ? 'medium' : 'low'),
            goalId,
            JSON.stringify({
              coordinator_tick: 'pending',
              dispatch_type: dispatchType,
              coalition_id: coalitionId,
              domains: group.domains,
              rigor_tier: rigorTier,
              routed_by: 'L14 coordinator dispatch tick',
            }),
          ]
        );

        await client.query(
          `INSERT INTO work_cycle_events
             (id, work_request_id, cycle_phase, event_type, details)
           VALUES ($1,$2,'coordinator_dispatch','work_request_created',$3::jsonb)`,
          [
            crypto.randomUUID(),
            work.rows[0].id,
            JSON.stringify({
              goal_id: goalId,
              domains: group.domains,
              dispatch_type: dispatchType,
              coalition_id: coalitionId,
              matched_domains: group.routes.map(route => route.matched_domain_key),
            }),
          ]
        );

        assignments.push({
          institutionId: group.route.institution_id,
          departmentId: production.rows[0].id,
          domains: group.domains,
          workRequestId: work.rows[0].id,
          matchTypes: group.routes.map(route => route.match_type),
          trustFactors: group.routes.map(route => Number(route.latest_trust_factor)),
        });
      }
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }

    return this.persistDispatchTick({
      runId,
      correlationId,
      runtimeMode,
      status: 'dispatched',
      dispatchType,
      goalId,
      objective: input.objective,
      domains,
      missingDomains: [],
      assignments,
      coalitionId,
      trace: {
        dispatch_type: dispatchType,
        coalition_id: coalitionId,
        assignments,
      },
    });
  }

  private async evaluateRuntimeGraph(): Promise<CivilizationRuntimeNode[]> {
    const requiredTables = [...new Set(RUNTIME_GRAPH.flatMap(node => node.requiredTables))].sort();
    const tableResult = await db.query<{ table_name: string }>(
      `SELECT table_name
         FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = ANY($1::text[])`,
      [requiredTables],
    );
    const foundTables = new Set(tableResult.rows.map(row => row.table_name));
    const routeText = this.routeSourceText();

    return RUNTIME_GRAPH.map(node => {
      const missingTables = node.requiredTables.filter(table => !foundTables.has(table)).sort();
      const missingRoutes = node.requiredRoutes.filter(route => !routeText.includes(route)).sort();
      return {
        ...node,
        requiredTables: [...node.requiredTables],
        requiredRoutes: [...node.requiredRoutes],
        status: missingTables.length === 0 && missingRoutes.length === 0 ? 'reachable' : 'missing',
        missingTables,
        missingRoutes,
      };
    });
  }

  private async persistDispatchTick(input: {
    runId: string;
    correlationId: string;
    runtimeMode: string;
    status: DispatchStatus;
    dispatchType: DispatchType | null;
    goalId: string;
    objective: string;
    domains: string[];
    missingDomains: string[];
    assignments: CivilizationDispatchAssignment[];
    coalitionId: string | null;
    trace: Record<string, unknown>;
  }): Promise<CivilizationDispatchTick> {
    const runStatus = input.status === 'dispatched' ? 'passed' : 'failed';
    const stageResults = {
      dispatch_tick: {
        status: input.status,
        dispatch_type: input.dispatchType,
        goal_id: input.goalId,
        requested_domains: input.domains,
        missing_domains: input.missingDomains,
        assignments: input.assignments,
        coalition_id: input.coalitionId,
      },
    };
    const runtimeTrace = [
      {
        stage: 'dispatch_tick',
        status: input.status,
        at: new Date().toISOString(),
        ...input.trace,
      },
    ];

    await db.query(
      `INSERT INTO civilization_vertical_slice_runs
         (id, correlation_id, status, runtime_mode, stage_results, runtime_trace, failure_reason, completed_at)
       VALUES ($1,$2,$3,$4,$5::jsonb,$6::jsonb,$7,now())`,
      [
        input.runId,
        input.correlationId,
        runStatus,
        input.runtimeMode,
        JSON.stringify(stageResults),
        JSON.stringify(runtimeTrace),
        input.missingDomains.length > 0 ? `missing domains: ${input.missingDomains.join(', ')}` : null,
      ]
    );

    const tickResult = await db.query<{ id: string }>(
      `INSERT INTO civilization_coordinator_ticks (run_id, tick_type, trace_json)
       VALUES ($1,'dispatch_tick',$2::jsonb)
       RETURNING id`,
      [
        input.runId,
        JSON.stringify({
          correlation_id: input.correlationId,
          status: input.status,
          dispatch_type: input.dispatchType,
          goal_id: input.goalId,
          requested_domains: input.domains,
          missing_domains: input.missingDomains,
          assignments: input.assignments,
          coalition_id: input.coalitionId,
        }),
      ]
    );

    return {
      runId: input.runId,
      correlationId: input.correlationId,
      runtimeMode: input.runtimeMode,
      tickId: tickResult.rows[0].id,
      tickType: 'dispatch_tick',
      status: input.status,
      dispatchType: input.dispatchType,
      goalId: input.goalId,
      objective: input.objective,
      domains: input.domains,
      missingDomains: input.missingDomains,
      assignments: input.assignments,
      coalitionId: input.coalitionId,
    };
  }

  private routeSourceText(): string {
    const srcRoot = path.resolve(__dirname, '..');
    const chunks: string[] = [];

    const walk = (dir: string) => {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          if (!['tests', '__tests__'].includes(entry.name)) walk(fullPath);
          continue;
        }
        if (entry.isFile() && entry.name.endsWith('.ts')) {
          chunks.push(fs.readFileSync(fullPath, 'utf8'));
        }
      }
    };

    walk(srcRoot);
    return chunks.join('\n');
  }
}

export const civilizationRuntimeService = new CivilizationRuntimeService();
