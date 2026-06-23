/**
 * Specialist Roles Definition
 * ==========================
 * Defines roles for autonomous agents spawned by the orchestrator.
 * Each role has:
 * - Specific tool access (restricted action types)
 * - Budget limits (tokens, iterations, wall-clock time)
 * - Risk level and supervision requirements
 */

import { ActionType } from './action.types';

export interface SpecialistRoleSpec {
  roleId: string;
  name: 'researcher' | 'fetcher' | 'evidence_summarizer' | 'claim_validator' | 'reviewer';
  description: string;
  defaultBudgets: {
    tokens: number;      // LLM token budget
    iterations: number;  // Max action steps
    seconds: number;     // Wall-clock timeout
  };
  allowedToolTypes: ActionType[];  // Restricted action types per role
  riskLevel: 'low' | 'medium' | 'high';
  supervision: 'auto' | 'approval_required';
}

export const SPECIALIST_ROLES: Record<string, SpecialistRoleSpec> = {
  researcher: {
    roleId: 'researcher',
    name: 'researcher',
    description: 'Broad research capabilities: search, fetch, extract evidence',
    defaultBudgets: {
      tokens: 10000,
      iterations: 30,
      seconds: 300,
    },
    allowedToolTypes: [
      ActionType.WEB_SEARCH,
      ActionType.FETCH_PAGE,
      ActionType.EXTRACT_EVIDENCE,
      ActionType.UPDATE_MEMORY,
      ActionType.EVALUATE_PROGRESS,
    ],
    riskLevel: 'medium',
    supervision: 'auto',
  },

  fetcher: {
    roleId: 'fetcher',
    name: 'fetcher',
    description: 'Read-only data gathering: fetch pages only',
    defaultBudgets: {
      tokens: 2000,
      iterations: 20,
      seconds: 120,
    },
    allowedToolTypes: [
      ActionType.FETCH_PAGE,
      ActionType.EVALUATE_PROGRESS,
    ],
    riskLevel: 'low',
    supervision: 'auto',
  },

  evidence_summarizer: {
    roleId: 'evidence_summarizer',
    name: 'evidence_summarizer',
    description: 'Passive evidence analysis and extraction',
    defaultBudgets: {
      tokens: 3000,
      iterations: 15,
      seconds: 180,
    },
    allowedToolTypes: [
      ActionType.EXTRACT_EVIDENCE,
      ActionType.UPDATE_MEMORY,
      ActionType.EVALUATE_PROGRESS,
    ],
    riskLevel: 'low',
    supervision: 'auto',
  },

  claim_validator: {
    roleId: 'claim_validator',
    name: 'claim_validator',
    description: 'Validate and generate claims backed by evidence',
    defaultBudgets: {
      tokens: 5000,
      iterations: 25,
      seconds: 200,
    },
    allowedToolTypes: [
      ActionType.EXTRACT_EVIDENCE,
      ActionType.GENERATE_CLAIM,
      ActionType.UPDATE_MEMORY,
      ActionType.EVALUATE_PROGRESS,
    ],
    riskLevel: 'low',
    supervision: 'auto',
  },

  reviewer: {
    roleId: 'reviewer',
    name: 'reviewer',
    description: 'Sanity check and progress evaluation',
    defaultBudgets: {
      tokens: 1000,
      iterations: 5,
      seconds: 60,
    },
    allowedToolTypes: [
      ActionType.EVALUATE_PROGRESS,
    ],
    riskLevel: 'low',
    supervision: 'auto',
  },
};

export function getSpecialistRole(name: string): SpecialistRoleSpec | null {
  return SPECIALIST_ROLES[name] || null;
}

export function isValidSpecialistRole(name: string): boolean {
  return name in SPECIALIST_ROLES;
}

export function getDefaultBudget(roleName: string) {
  const role = getSpecialistRole(roleName);
  return role ? role.defaultBudgets : null;
}
