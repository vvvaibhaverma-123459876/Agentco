import { FastifyInstance } from 'fastify';
import { EventEmitter } from 'events';

/**
 * Learning Service: Integrates autonomous learning loop into agent decisions
 *
 * Architecture:
 * 1. LEARNING SIGNALS: Captured from agent decisions, evidence updates, outcomes
 * 2. LEARNING LOOP: Analyzes signals, extracts insights, proposes improvements
 * 3. FEEDBACK: Learning results feed back into decision-making
 * 4. MEMORY: All learning outcomes stored for future decisions
 */

export interface LearningSignal {
  signal_id: string;
  agent_id: string;
  type: 'decision' | 'evidence_update' | 'outcome' | 'contradiction';
  content: Record<string, unknown>;
  timestamp: string;
  provenance_ref: string;
}

export interface LearningInsight {
  insight_id: string;
  signal_id: string;
  analysis: {
    claims_extracted: number;
    hypothesis_valid: boolean;
    risk_level: string;
    confidence: number;
  };
  recommendations: string[];
  timestamp: string;
}

export interface AdaptationProposal {
  proposal_id: string;
  insight_id: string;
  agent_id: string;
  change_type: 'decision_refinement' | 'institutional_change' | 'governance_update';
  rationale: string;
  status: 'proposed' | 'approved' | 'rejected' | 'active';
  timestamp: string;
}

class LearningService extends EventEmitter {
  private signals: Map<string, LearningSignal> = new Map();
  private insights: Map<string, LearningInsight> = new Map();
  private proposals: Map<string, AdaptationProposal> = new Map();
  private learningLoop: any; // Reference to Python learning loop
  private processingQueue: LearningSignal[] = [];
  private isProcessing = false;

  constructor() {
    super();
  }

  /**
   * Capture a learning signal from an agent decision or evidence update
   */
  captureSignal(
    agentId: string,
    type: 'decision' | 'evidence_update' | 'outcome' | 'contradiction',
    content: Record<string, unknown>,
    provenanceRef: string,
  ): LearningSignal {
    const signal: LearningSignal = {
      signal_id: `signal_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      agent_id: agentId,
      type,
      content,
      timestamp: new Date().toISOString(),
      provenance_ref: provenanceRef,
    };

    this.signals.set(signal.signal_id, signal);
    this.processingQueue.push(signal);
    this.emit('signal_captured', signal);

    // Auto-process if not already processing
    if (!this.isProcessing) {
      this.processQueuedSignals();
    }

    return signal;
  }

  /**
   * Process queued learning signals through the learning loop
   */
  private async processQueuedSignals(): Promise<void> {
    if (this.isProcessing || this.processingQueue.length === 0) {
      return;
    }

    this.isProcessing = true;

    while (this.processingQueue.length > 0) {
      const signal = this.processingQueue.shift()!;

      try {
        // Extract actionable insights from the signal
        const insight = await this.analyzeSignal(signal);
        this.insights.set(insight.insight_id, insight);
        this.emit('insight_generated', insight);

        // Generate adaptation proposal if insight quality is high
        if (insight.analysis.confidence > 0.7) {
          const proposal = this.proposeAdaptation(signal, insight);
          this.proposals.set(proposal.proposal_id, proposal);
          this.emit('proposal_generated', proposal);
        }
      } catch (error) {
        console.error(`Error processing signal ${signal.signal_id}:`, error);
      }
    }

    this.isProcessing = false;
  }

  /**
   * Analyze a signal through the learning loop
   */
  private async analyzeSignal(signal: LearningSignal): Promise<LearningInsight> {
    // Extract key information based on signal type
    const analysis = {
      claims_extracted: this.extractClaims(signal.content).length,
      hypothesis_valid: this.validateHypothesis(signal.content),
      risk_level: this.assessRisk(signal.content),
      confidence: this.calculateConfidence(signal),
    };

    const insight: LearningInsight = {
      insight_id: `insight_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      signal_id: signal.signal_id,
      analysis,
      recommendations: this.generateRecommendations(signal, analysis),
      timestamp: new Date().toISOString(),
    };

    return insight;
  }

  /**
   * Extract claims from signal content
   */
  private extractClaims(content: Record<string, unknown>): string[] {
    const claims: string[] = [];
    if (content.decision) claims.push(String(content.decision));
    if (content.hypothesis) claims.push(String(content.hypothesis));
    if (content.claim) claims.push(String(content.claim));
    return claims.filter(c => c && c.length > 0);
  }

  /**
   * Validate hypothesis in signal
   */
  private validateHypothesis(content: Record<string, unknown>): boolean {
    return (
      Boolean(content.hypothesis) &&
      Boolean(content.evidence) &&
      (typeof content.confidence === 'number' && content.confidence > 0.5)
    );
  }

  /**
   * Assess risk level of signal
   */
  private assessRisk(content: Record<string, unknown>): string {
    const confidence = typeof content.confidence === 'number' ? content.confidence : 0.5;
    if (confidence < 0.3) return 'critical';
    if (confidence < 0.6) return 'high';
    if (confidence < 0.85) return 'medium';
    return 'low';
  }

  /**
   * Calculate overall confidence in the signal
   */
  private calculateConfidence(signal: LearningSignal): number {
    const baseConfidence = 0.5;
    const claimBoost = (this.extractClaims(signal.content).length / 5) * 0.2;
    const evidenceBoost = (signal.content.evidence ? 0.2 : 0);
    return Math.min(1, baseConfidence + claimBoost + evidenceBoost);
  }

  /**
   * Generate recommendations based on analysis
   */
  private generateRecommendations(
    signal: LearningSignal,
    analysis: { claims_extracted: number; hypothesis_valid: boolean; risk_level: string },
  ): string[] {
    const recommendations: string[] = [];

    if (signal.type === 'decision') {
      if (analysis.claims_extracted === 0) {
        recommendations.push('Increase claim extraction for better evidence grounding');
      }
      if (!analysis.hypothesis_valid) {
        recommendations.push('Strengthen hypothesis validation before committing decision');
      }
      if (analysis.risk_level === 'critical') {
        recommendations.push('Escalate decision to governance for override approval');
      }
    }

    if (signal.type === 'contradiction') {
      recommendations.push('Investigate source reliability and independence');
      recommendations.push('Update evidence resolution with contradiction');
    }

    if (signal.type === 'outcome') {
      recommendations.push('Calibrate confidence based on outcome match');
      recommendations.push('Update historical accuracy metrics');
    }

    return recommendations;
  }

  /**
   * Propose institutional adaptation based on insight
   */
  private proposeAdaptation(signal: LearningSignal, insight: LearningInsight): AdaptationProposal {
    const changeType: 'decision_refinement' | 'institutional_change' | 'governance_update' =
      insight.analysis.confidence > 0.85 ? 'decision_refinement' :
      insight.analysis.confidence > 0.7 ? 'institutional_change' :
      'governance_update';

    return {
      proposal_id: `proposal_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      insight_id: insight.insight_id,
      agent_id: signal.agent_id,
      change_type: changeType,
      rationale: `Learning loop analysis: ${insight.analysis.claims_extracted} claims, ` +
                 `hypothesis_valid=${insight.analysis.hypothesis_valid}, ` +
                 `risk=${insight.analysis.risk_level}`,
      status: 'proposed',
      timestamp: new Date().toISOString(),
    };
  }

  /**
   * Apply a learning-based adaptation
   */
  applyAdaptation(proposalId: string): AdaptationProposal | null {
    const proposal = this.proposals.get(proposalId);
    if (!proposal) return null;

    proposal.status = 'active';
    this.proposals.set(proposalId, proposal);
    this.emit('adaptation_applied', proposal);

    return proposal;
  }

  /**
   * Get learning history for an agent
   */
  getAgentLearningHistory(agentId: string, limit: number = 100): {
    signals: LearningSignal[];
    insights: LearningInsight[];
    proposals: AdaptationProposal[];
  } {
    const agentSignals = Array.from(this.signals.values())
      .filter(s => s.agent_id === agentId)
      .slice(-limit);

    const signalIds = new Set(agentSignals.map(s => s.signal_id));
    const agentInsights = Array.from(this.insights.values())
      .filter(i => signalIds.has(i.signal_id))
      .slice(-limit);

    const insightIds = new Set(agentInsights.map(i => i.insight_id));
    const agentProposals = Array.from(this.proposals.values())
      .filter(p => insightIds.has(p.insight_id))
      .slice(-limit);

    return { signals: agentSignals, insights: agentInsights, proposals: agentProposals };
  }

  /**
   * Get learning statistics
   */
  getStats(): {
    total_signals: number;
    total_insights: number;
    total_proposals: number;
    proposals_active: number;
    avg_confidence: number;
    processing_queue: number;
  } {
    const insights = Array.from(this.insights.values());
    const avgConfidence = insights.length > 0
      ? insights.reduce((sum, i) => sum + i.analysis.confidence, 0) / insights.length
      : 0;

    return {
      total_signals: this.signals.size,
      total_insights: this.insights.size,
      total_proposals: this.proposals.size,
      proposals_active: Array.from(this.proposals.values()).filter(p => p.status === 'active').length,
      avg_confidence: avgConfidence,
      processing_queue: this.processingQueue.length,
    };
  }
}

// Singleton instance
export const learningService = new LearningService();

/**
 * Register learning routes on Fastify instance
 */
export async function learningRoutes(fastify: FastifyInstance) {
  // GET /api/learning/stats - Learning service statistics
  fastify.get('/api/learning/stats', async (_req, reply) => {
    return reply.send(learningService.getStats());
  });

  // POST /api/learning/signal - Capture a learning signal
  fastify.post<{
    Body: {
      agent_id: string;
      type: 'decision' | 'evidence_update' | 'outcome' | 'contradiction';
      content: Record<string, unknown>;
      provenance_ref: string;
    };
  }>('/api/learning/signal', async (req, reply) => {
    const { agent_id, type, content, provenance_ref } = req.body;
    const signal = learningService.captureSignal(agent_id, type, content, provenance_ref);
    return reply.status(201).send({ status: 'captured', signal });
  });

  // GET /api/learning/agent/:agent_id - Get agent learning history
  fastify.get<{ Params: { agent_id: string } }>('/api/learning/agent/:agent_id', async (req, reply) => {
    const { agent_id } = req.params;
    const history = learningService.getAgentLearningHistory(agent_id);
    return reply.send(history);
  });

  // GET /api/learning/insights - Get recent insights
  fastify.get('/api/learning/insights', async (req, reply) => {
    const query = req.query as Record<string, unknown>;
    const limit = typeof query.limit === 'string' ? parseInt(query.limit) : 50;
    // Return recent insights (implementation depends on internal structure)
    return reply.send({ status: 'ok', count: learningService.getStats().total_insights });
  });

  // POST /api/learning/proposals/:proposal_id/apply - Apply a learning proposal
  fastify.post<{ Params: { proposal_id: string } }>('/api/learning/proposals/:proposal_id/apply', async (req, reply) => {
    const { proposal_id } = req.params;
    const result = learningService.applyAdaptation(proposal_id);
    if (!result) {
      return reply.status(404).send({ error: 'Proposal not found' });
    }
    return reply.send({ status: 'applied', proposal: result });
  });
}
