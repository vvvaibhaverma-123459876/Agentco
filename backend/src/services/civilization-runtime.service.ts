import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { db } from '../db/client';

type RuntimeNodeStatus = 'reachable' | 'missing';

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
    ],
    requiredRoutes: [
      '/api/civilization/runtime/graph',
      '/api/civilization/runtime/reachability-tick',
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
