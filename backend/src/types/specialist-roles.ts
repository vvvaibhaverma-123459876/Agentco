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
  name: string;
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

  // TIER 1: Specialists using existing ActionTypes
  data_analyst: {
    roleId: 'data_analyst',
    name: 'data_analyst',
    description: 'Analyze datasets, compute statistics, identify patterns',
    defaultBudgets: {
      tokens: 8000,
      iterations: 25,
      seconds: 240,
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

  source_validator: {
    roleId: 'source_validator',
    name: 'source_validator',
    description: 'Verify source credibility, check for bias/manipulation',
    defaultBudgets: {
      tokens: 4000,
      iterations: 15,
      seconds: 150,
    },
    allowedToolTypes: [
      ActionType.FETCH_PAGE,
      ActionType.EXTRACT_EVIDENCE,
      ActionType.EVALUATE_PROGRESS,
    ],
    riskLevel: 'low',
    supervision: 'auto',
  },

  evidence_linker: {
    roleId: 'evidence_linker',
    name: 'evidence_linker',
    description: 'Connect related evidence, identify patterns across sources',
    defaultBudgets: {
      tokens: 3000,
      iterations: 12,
      seconds: 120,
    },
    allowedToolTypes: [
      ActionType.EXTRACT_EVIDENCE,
      ActionType.UPDATE_MEMORY,
      ActionType.EVALUATE_PROGRESS,
    ],
    riskLevel: 'low',
    supervision: 'auto',
  },

  contradiction_hunter: {
    roleId: 'contradiction_hunter',
    name: 'contradiction_hunter',
    description: 'Find contradictions in claims and evidence',
    defaultBudgets: {
      tokens: 5000,
      iterations: 20,
      seconds: 180,
    },
    allowedToolTypes: [
      ActionType.EXTRACT_EVIDENCE,
      ActionType.GENERATE_CLAIM,
      ActionType.EVALUATE_PROGRESS,
    ],
    riskLevel: 'low',
    supervision: 'auto',
  },

  synthesizer: {
    roleId: 'synthesizer',
    name: 'synthesizer',
    description: 'Combine multiple claims into higher-level conclusions',
    defaultBudgets: {
      tokens: 6000,
      iterations: 18,
      seconds: 200,
    },
    allowedToolTypes: [
      ActionType.GENERATE_CLAIM,
      ActionType.UPDATE_MEMORY,
      ActionType.EVALUATE_PROGRESS,
    ],
    riskLevel: 'low',
    supervision: 'auto',
  },

  background_researcher: {
    roleId: 'background_researcher',
    name: 'background_researcher',
    description: 'Deep research into context and history',
    defaultBudgets: {
      tokens: 12000,
      iterations: 40,
      seconds: 360,
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

  // TIER 2: Specialists requiring new ActionTypes
  code_reviewer: {
    roleId: 'code_reviewer',
    name: 'code_reviewer',
    description: 'Analyze code for bugs, performance, style violations',
    defaultBudgets: {
      tokens: 7000,
      iterations: 20,
      seconds: 200,
    },
    allowedToolTypes: [
      ActionType.FETCH_PAGE,
      ActionType.EXTRACT_EVIDENCE,
      ActionType.GENERATE_CLAIM,
      ActionType.EVALUATE_PROGRESS,
    ],
    riskLevel: 'low',
    supervision: 'auto',
  },

  doc_analyzer: {
    roleId: 'doc_analyzer',
    name: 'doc_analyzer',
    description: 'Extract structured data from PDFs, technical docs, specifications',
    defaultBudgets: {
      tokens: 9000,
      iterations: 25,
      seconds: 240,
    },
    allowedToolTypes: [
      ActionType.FETCH_PAGE,
      ActionType.EXTRACT_EVIDENCE,
      ActionType.GENERATE_CLAIM,
      ActionType.EVALUATE_PROGRESS,
    ],
    riskLevel: 'low',
    supervision: 'auto',
  },

  sentiment_analyzer: {
    roleId: 'sentiment_analyzer',
    name: 'sentiment_analyzer',
    description: 'Analyze sentiment/tone in text, identify bias, emotional weight',
    defaultBudgets: {
      tokens: 4000,
      iterations: 15,
      seconds: 120,
    },
    allowedToolTypes: [
      ActionType.EXTRACT_EVIDENCE,
      ActionType.GENERATE_CLAIM,
      ActionType.EVALUATE_PROGRESS,
    ],
    riskLevel: 'low',
    supervision: 'auto',
  },

  comparative_analyst: {
    roleId: 'comparative_analyst',
    name: 'comparative_analyst',
    description: 'Compare products, approaches, entities across multiple dimensions',
    defaultBudgets: {
      tokens: 8000,
      iterations: 22,
      seconds: 210,
    },
    allowedToolTypes: [
      ActionType.FETCH_PAGE,
      ActionType.GENERATE_CLAIM,
      ActionType.EVALUATE_PROGRESS,
    ],
    riskLevel: 'low',
    supervision: 'auto',
  },

  temporal_analyst: {
    roleId: 'temporal_analyst',
    name: 'temporal_analyst',
    description: 'Construct timelines, identify causality, sequence-dependent patterns',
    defaultBudgets: {
      tokens: 6000,
      iterations: 18,
      seconds: 180,
    },
    allowedToolTypes: [
      ActionType.EXTRACT_EVIDENCE,
      ActionType.GENERATE_CLAIM,
      ActionType.EVALUATE_PROGRESS,
    ],
    riskLevel: 'low',
    supervision: 'auto',
  },

  quality_auditor: {
    roleId: 'quality_auditor',
    name: 'quality_auditor',
    description: 'Audit quality metrics, compliance, standards adherence',
    defaultBudgets: {
      tokens: 7000,
      iterations: 19,
      seconds: 190,
    },
    allowedToolTypes: [
      ActionType.FETCH_PAGE,
      ActionType.EXTRACT_EVIDENCE,
      ActionType.GENERATE_CLAIM,
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
