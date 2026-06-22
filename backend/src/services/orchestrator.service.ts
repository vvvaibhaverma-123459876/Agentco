/**
 * Orchestrator Service: Coordinate Phases 1-4 into unified pipeline
 *
 * Architecture:
 * Question → Router → [RAG + Ensemble + Symbolic] → Bayesian Fusion → Trust Scoring
 *
 * Phases:
 * 1. RAG: Retrieve evidence from knowledge base
 * 2. Ensemble: Multi-model voting with semantic agreement
 * 3. Symbolic: Logic/math/pattern solving
 * 4. Bayesian: Fuse results with proper calibration
 * 5. Trust Score: Comprehensive trustworthiness metric
 */

import { ragService } from './rag.service';
import { ensembleService, EnsembleResult } from './ensemble.service';
import { symbolicService, SymbolicAnswer } from './symbolic.service';
import { bayesianService, CalibratedAnswer } from './bayesian.service';
import { trustService } from './trustworthiness.service';

export interface OrchestratorInput {
  question: string;
  models: Array<{ name: string; generate: (q: string) => Promise<{ answer: string; confidence: number }> }>;
  evidence?: any;
}

export interface OrchestratorOutput {
  question: string;
  final_answer: string;
  confidence: number;
  uncertainty_interval: [number, number];
  reasoning: string;
  method_chain: string[];
  trust_score: number;
  components: {
    rag_result?: any;
    ensemble_result?: EnsembleResult;
    symbolic_result?: SymbolicAnswer;
    bayesian_result?: CalibratedAnswer;
    trustworthiness?: any;
  };
  metadata: {
    processing_time_ms: number;
    models_queried: string[];
    abstentions: string[];
  };
}

export class OrchestratorService {
  /**
   * Main orchestration pipeline
   */
  async orchestrate(input: OrchestratorInput): Promise<OrchestratorOutput> {
    const startTime = Date.now();
    const methodChain: string[] = [];
    const components: any = {};
    const abstentions: string[] = [];

    // Route 1: Symbolic Reasoning (fastest, most reliable)
    const symbolicResult = await symbolicService.solve(input.question);
    if (symbolicResult) {
      methodChain.push('Symbolic Reasoning');
      components.symbolic_result = symbolicResult;

      return {
        question: input.question,
        final_answer: symbolicResult.answer,
        confidence: symbolicResult.is_guaranteed ? 0.99 : 0.85,
        uncertainty_interval: symbolicResult.is_guaranteed ? [0.98, 1.0] : [0.75, 0.95],
        reasoning: symbolicResult.reasoning,
        method_chain: methodChain,
        trust_score: symbolicResult.is_guaranteed ? 0.99 : 0.9,
        components,
        metadata: {
          processing_time_ms: Date.now() - startTime,
          models_queried: [],
          abstentions,
        },
      };
    }

    // Route 2: Ensemble Multi-Model Voting
    methodChain.push('Ensemble Voting');
    const modelAnswers = await Promise.all(
      input.models.map(async (m) => {
        try {
          const result = await m.generate(input.question);
          return {
            model: m.name,
            answer: result.answer,
            confidence: result.confidence,
          };
        } catch (err) {
          abstentions.push(`${m.name}: ${(err as Error).message}`);
          return null;
        }
      }),
    );

    const validAnswers = modelAnswers.filter((a): a is NonNullable<typeof a> => a !== null);

    let ensembleResult: EnsembleResult | null = null;
    if (validAnswers.length > 0) {
      ensembleResult = await ensembleService.fuse(validAnswers);
      components.ensemble_result = ensembleResult;

      if (ensembleResult.abstention) {
        abstentions.push(`Ensemble: ${ensembleResult.abstention_reason}`);
      }
    }

    // Route 3: RAG Enhancement (Knowledge Retrieval)
    methodChain.push('RAG Enhancement');
    const ragCandidate = ensembleResult?.final_answer || validAnswers[0]?.answer;
    const ragConfidence = ensembleResult?.confidence || validAnswers[0]?.confidence || 0.5;

    const ragResult = await ragService.augmentAnswer(
      input.question,
      ragCandidate,
      ragConfidence,
    );
    components.rag_result = ragResult;

    // Use RAG-enhanced answer if it improved things
    const fusedAnswer = ragResult.final_answer;
    const fusedConfidence = ragResult.final_confidence;

    // Route 4: Bayesian Calibration (Uncertainty Quantification)
    methodChain.push('Bayesian Calibration');

    const prior = {
      model_accuracy: 0.7, // Historical baseline
      source_reliability: ragResult.evidence_consensus?.confidence || 0.5,
      calibration_score: 0.73, // From evidence kernel
    };

    const likelihood = {
      evidence_quality: ragResult.evidence_consensus?.confidence || 0.5,
      source_agreement: ragResult.evidence_consensus?.agreement_ratio || 0.5,
      consistency_score: fusedConfidence,
    };

    const bayesianResult = bayesianService.fuse(
      fusedAnswer,
      fusedConfidence,
      ragResult.evidence_consensus?.confidence || 0.5,
      prior,
      likelihood,
      ragResult.evidence_consensus?.sources?.slice(0, 2).map(s => s.title) || [],
    );
    components.bayesian_result = bayesianResult;

    // Route 5: Trust Score Computation
    methodChain.push('Trust Scoring');
    const trustResult = trustService.computeTrustScore({
      answer: bayesianResult.answer,
      confidence: bayesianResult.confidence,
      rag_quality: ragResult.evidence_consensus?.confidence || 0,
      ensemble_agreement: ensembleResult?.cluster_consensus || 0,
      symbolic_guaranteed: false,
      calibration_error: 0.1, // Would be computed from historical data
      explanation: bayesianResult.reasoning,
    });
    components.trustworthiness = trustResult;

    return {
      question: input.question,
      final_answer: bayesianResult.answer,
      confidence: bayesianResult.confidence,
      uncertainty_interval: bayesianResult.uncertainty_interval,
      reasoning: bayesianResult.reasoning,
      method_chain: methodChain,
      trust_score: trustResult.trust_score,
      components,
      metadata: {
        processing_time_ms: Date.now() - startTime,
        models_queried: validAnswers.map(a => a.model),
        abstentions,
      },
    };
  }

  /**
   * Determine optimal routing based on question characteristics
   */
  private analyzeQuestion(question: string): 'symbolic' | 'ensemble' | 'rag' {
    const q = question.toLowerCase();

    // Symbolic: logic, math, patterns
    if (/^(if|solve|sequence|pattern|logic|formula|equation)/.test(q)) {
      return 'symbolic';
    }

    // Ensemble: subjective, complex reasoning, safety
    if (/^(should|would|might|opinion|ethical|safety)/.test(q)) {
      return 'ensemble';
    }

    // RAG: factual, knowledge-based
    return 'rag';
  }
}

export const orchestratorService = new OrchestratorService();
