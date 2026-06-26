/**
 * Orchestrator Service - Unified Pipeline
 * Routes questions to optimal solver and fuses results with Bayesian calibration
 *
 * Pipeline:
 * 1. Classify question type
 * 2. Route to appropriate solver (Symbolic / Ensemble / RAG)
 * 3. Retrieve evidence and calibration data
 * 4. Apply Bayesian fusion
 * 5. Compute trustworthiness score
 * 6. Return comprehensive answer bundle
 */

import { ragService } from './rag.service';
import { ensembleService } from './ensemble.service';
import { symbolicService } from './symbolic.service';
import { bayesianService } from './bayesian.service';
import { trustworthinessService } from './trustworthiness.service';

interface AnswerBundle {
  question: string;
  answer: string;
  confidence: number;
  uncertainty_interval: { lower: number; upper: number };
  prediction_set: string[];
  trust_score: number;
  trust_level: 'low' | 'moderate' | 'high' | 'critical';
  reasoning: string;
  evidence_used: string[];
  method_used: string[];
  recommendation: string;
}

export class OrchestratorService {
  /**
   * Main orchestration pipeline
   */
  async processQuestion(question: string): Promise<AnswerBundle> {
    console.log(`[Orchestrator] Processing: ${question}`);

    // Step 1: Classify question and route
    const symbolicProblem = symbolicService.classifyProblem(question);
    console.log(`[Orchestrator] Problem type: ${symbolicProblem.type} (confidence: ${symbolicProblem.confidence})`);

    let primaryAnswer: string;
    let primaryConfidence: number;
    const methodsUsed: string[] = [];
    const evidenceUsed: string[] = [];

    // Step 2: Try symbolic solver first for logic/math/patterns
    if (symbolicProblem.confidence > 0.7) {
      console.log('[Orchestrator] Routing to Symbolic Solver');
      const symbolicResult = await symbolicService.solve(question);
      if (symbolicResult.solved) {
        primaryAnswer = symbolicResult.answer;
        primaryConfidence = symbolicResult.confidence;
        methodsUsed.push(`Symbolic (${symbolicResult.method})`);
        evidenceUsed.push(symbolicResult.reasoning);
      } else {
        // Fallback to ensemble
        console.log('[Orchestrator] Symbolic solver failed, routing to Ensemble');
        const ensembleResult = await ensembleService.ensembleVote(question);
        primaryAnswer = ensembleResult.final_answer;
        primaryConfidence = ensembleResult.confidence;
        methodsUsed.push('Ensemble');
        evidenceUsed.push(ensembleResult.reasoning);
      }
    } else {
      // Route to ensemble for open-ended questions
      console.log('[Orchestrator] Routing to Ensemble Voting');
      const ensembleResult = await ensembleService.ensembleVote(question);
      primaryAnswer = ensembleResult.final_answer;
      primaryConfidence = ensembleResult.confidence;
      methodsUsed.push('Ensemble');
      evidenceUsed.push(ensembleResult.reasoning);
    }

    // Step 3: Apply RAG for knowledge validation
    console.log('[Orchestrator] Applying RAG for evidence verification');
    const ragResult = await ragService.augmentAnswer(question, primaryAnswer, primaryConfidence);
    if (ragResult.final_confidence > primaryConfidence) {
      primaryAnswer = ragResult.final_answer;
      primaryConfidence = ragResult.final_confidence;
      methodsUsed.push('RAG');
      evidenceUsed.push(ragResult.reasoning);
    }

    // Step 4: Apply Bayesian calibration
    console.log('[Orchestrator] Computing Bayesian calibration');
    const evidenceQuality = this.computeEvidenceQuality(ragResult.evidence_consensus.sources);
    const sourceReliability = this.computeSourceReliability(ragResult.evidence_consensus.sources);
    const calibrationError = this.estimateCalibrationError(primaryConfidence, ragResult.final_confidence);
    const consistency = this.computeAgreement(primaryAnswer, ragResult.final_answer, ragResult.evidence_consensus.agreement_ratio);
    const explainability = this.computeExplainability(evidenceUsed);
    const bayesianResult = await bayesianService.bayesianFusion(
      [
        { model: 'ensemble', answer: primaryAnswer, confidence: primaryConfidence },
        { model: 'rag', answer: ragResult.final_answer, confidence: ragResult.final_confidence },
      ],
      evidenceQuality,
      sourceReliability,
    );

    // Step 5: Compute trustworthiness score
    console.log('[Orchestrator] Computing trustworthiness score');
    const trustScore = trustworthinessService.computeTrustScore(
      Math.min(1, primaryConfidence * 1.1), // Base accuracy (boosted by ensemble)
      calibrationError,
      consistency,
      explainability,
      0.90, // Uncertainty quality
      0.92, // Conformal coverage
    );

    // Step 6: Return comprehensive bundle
    const bundle: AnswerBundle = {
      question,
      answer: bayesianResult.answer,
      confidence: bayesianResult.confidence,
      uncertainty_interval: {
        lower: bayesianResult.lower_bound,
        upper: bayesianResult.upper_bound,
      },
      prediction_set: bayesianResult.prediction_set,
      trust_score: trustScore.overall_trust,
      trust_level: trustScore.risk_level,
      reasoning: evidenceUsed.join(' | '),
      evidence_used: evidenceUsed,
      method_used: methodsUsed,
      recommendation: trustScore.recommendation,
    };

    console.log(
      `[Orchestrator] Complete. Answer: "${bundle.answer}" (confidence: ${(bundle.confidence * 100).toFixed(1)}%, trust: ${(bundle.trust_score * 100).toFixed(1)}%)`,
    );

    return bundle;
  }

  computeEvidenceQuality(sources: Array<{ relevance?: number; snippet?: string; url?: string }>): number {
    if (sources.length === 0) {
      return 0.2;
    }
    const avgRelevance = sources.reduce((sum, source) => sum + Math.max(0, Math.min(1, source.relevance ?? 0)), 0) / sources.length;
    const provenanceCompleteness = sources.filter((source) => source.url && source.snippet).length / sources.length;
    const sourceDiversity = new Set(sources.map((source) => {
      try {
        return new URL(source.url || '').hostname;
      } catch {
        return source.url || 'unknown';
      }
    })).size / sources.length;
    return this.clamp(avgRelevance * 0.5 + provenanceCompleteness * 0.3 + sourceDiversity * 0.2, 0, 1);
  }

  computeSourceReliability(sources: Array<{ source?: string; url?: string }>): number {
    if (sources.length === 0) {
      return 0.2;
    }
    const reliabilityBySource: Record<string, number> = {
      Wikipedia: 0.78,
      ArXiv: 0.86,
    };
    const total = sources.reduce((sum, source) => {
      const base = reliabilityBySource[source.source || ''] ?? 0.55;
      const hasHttps = (source.url || '').startsWith('https://') ? 0.05 : 0;
      return sum + Math.min(1, base + hasHttps);
    }, 0);
    return this.clamp(total / sources.length, 0, 1);
  }

  estimateCalibrationError(primaryConfidence: number, evidenceAdjustedConfidence: number): number {
    return this.clamp(Math.abs(primaryConfidence - evidenceAdjustedConfidence), 0, 1);
  }

  computeAgreement(primaryAnswer: string, evidenceAnswer: string, evidenceAgreementRatio: number): number {
    if (!evidenceAnswer) {
      return 0.5;
    }
    const normalize = (value: string) => value.toLowerCase().replace(/[^a-z0-9]/g, '');
    const primary = normalize(primaryAnswer);
    const evidence = normalize(evidenceAnswer);
    const textualAgreement = primary && evidence && (primary.includes(evidence) || evidence.includes(primary)) ? 1 : 0;
    return this.clamp(textualAgreement * 0.6 + evidenceAgreementRatio * 0.4, 0, 1);
  }

  computeExplainability(evidenceUsed: string[]): number {
    if (evidenceUsed.length === 0) {
      return 0.3;
    }
    const nonEmpty = evidenceUsed.filter((item) => item.trim().length > 0).length;
    const detailScore = Math.min(1, evidenceUsed.join(' ').length / 300);
    return this.clamp((nonEmpty / evidenceUsed.length) * 0.6 + detailScore * 0.4, 0, 1);
  }

  private clamp(value: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, value));
  }

  /**
   * Format answer bundle for user display
   */
  formatAnswerBundle(bundle: AnswerBundle): string {
    return `
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 QUESTION: ${bundle.question}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ ANSWER: ${bundle.answer}

📊 CONFIDENCE: ${(bundle.confidence * 100).toFixed(1)}%
  Uncertainty interval: [${(bundle.uncertainty_interval.lower * 100).toFixed(1)}%, ${(bundle.uncertainty_interval.upper * 100).toFixed(1)}%]
  Prediction set: ${bundle.prediction_set.join(', ')}

🔐 TRUSTWORTHINESS: ${(bundle.trust_score * 100).toFixed(1)}% (${bundle.trust_level})
  → ${bundle.recommendation}

🔍 REASONING:
  Methods used: ${bundle.method_used.join(', ')}
  Evidence: ${bundle.evidence_used.join('\n  → ')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;
  }
}

export const orchestratorService = new OrchestratorService();
