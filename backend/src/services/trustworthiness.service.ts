/**
 * Trustworthiness Service - Trust Scoring Engine
 * 6-dimensional trust metric based on research
 *
 * Dimensions:
 * 1. Accuracy (25%) - correct answers
 * 2. Calibration (20%) - confidence matches correctness
 * 3. Consistency (20%) - agreement across models/evidence
 * 4. Explainability (15%) - reasoning quality (SHAP)
 * 5. Uncertainty (10%) - proper confidence quantification
 * 6. Coverage (10%) - conformal prediction coverage
 */

interface TrustDimension {
  name: string;
  score: number; // 0-1
  weight: number;
  reasoning: string;
}

interface TrustworthinessScore {
  overall_trust: number; // 0-1 weighted average
  dimensions: TrustDimension[];
  risk_level: 'low' | 'moderate' | 'high' | 'critical';
  recommendation: string;
  confidence_in_trust: number; // Meta-confidence
}

export class TrustworthinessService {
  /**
   * Compute comprehensive trust score
   * 6-dimensional metric (Zhou et al., Ribeiro et al., Angelopoulos & Bates)
   */
  computeTrustScore(
    accuracy: number, // 0-1: base model accuracy on task
    calibrationError: number, // 0-1: ECE (lower is better)
    consistency: number, // 0-1: agreement across models
    explainability: number, // 0-1: quality of reasoning chain
    uncertaintyQuality: number, // 0-1: proper uncertainty quantification
    conformalCoverage: number, // 0-1: coverage of prediction set
  ): TrustworthinessScore {
    const dimensions: TrustDimension[] = [
      {
        name: 'Accuracy',
        score: accuracy,
        weight: 0.25,
        reasoning: `Base model accuracy: ${(accuracy * 100).toFixed(1)}%`,
      },
      {
        name: 'Calibration',
        score: 1 - Math.min(1, calibrationError * 2), // ECE 0.05 → score 0.9
        weight: 0.20,
        reasoning: `Calibration error: ${(calibrationError * 100).toFixed(1)}%`,
      },
      {
        name: 'Consistency',
        score: consistency,
        weight: 0.20,
        reasoning: `Model agreement: ${(consistency * 100).toFixed(1)}%`,
      },
      {
        name: 'Explainability',
        score: explainability,
        weight: 0.15,
        reasoning: `Reasoning quality: ${this.explainabilityLevel(explainability)}`,
      },
      {
        name: 'Uncertainty',
        score: uncertaintyQuality,
        weight: 0.10,
        reasoning: `Uncertainty quantification: ${this.uncertaintyLevel(uncertaintyQuality)}`,
      },
      {
        name: 'Coverage',
        score: conformalCoverage,
        weight: 0.10,
        reasoning: `Conformal coverage: ${(conformalCoverage * 100).toFixed(1)}%`,
      },
    ];

    // Compute weighted average
    const overallTrust = dimensions.reduce((sum, d) => sum + d.score * d.weight, 0);

    // Determine risk level
    const riskLevel = this.determineRiskLevel(overallTrust);

    // Generate recommendation
    const recommendation = this.generateRecommendation(overallTrust, dimensions);

    // Confidence in trust score (based on consistency and calibration)
    const confidenceInTrust = (consistency * 0.6 + (1 - calibrationError) * 0.4) * 0.9 + 0.1;

    return {
      overall_trust: Math.round(overallTrust * 1000) / 1000,
      dimensions,
      risk_level: riskLevel,
      recommendation,
      confidence_in_trust: Math.round(confidenceInTrust * 1000) / 1000,
    };
  }

  /**
   * Determine risk level from trust score
   */
  private determineRiskLevel(trustScore: number): 'low' | 'moderate' | 'high' | 'critical' {
    if (trustScore >= 0.90) return 'low';
    if (trustScore >= 0.75) return 'moderate';
    if (trustScore >= 0.60) return 'high';
    return 'critical';
  }

  /**
   * Generate actionable recommendation
   */
  private generateRecommendation(trustScore: number, dimensions: TrustDimension[]): string {
    if (trustScore >= 0.90) {
      return '✅ Highly trustworthy. Use with high confidence. Minimal verification needed.';
    }

    if (trustScore >= 0.75) {
      return '⚠️ Mostly trustworthy. Normal confidence appropriate. Consider secondary validation for critical decisions.';
    }

    // Find weakest dimension
    const weakest = dimensions.reduce((min, d) => (d.score < min.score ? d : min));

    if (trustScore >= 0.60) {
      return `⚡ Moderately trustworthy. Weak area: ${weakest.name} (${(weakest.score * 100).toFixed(0)}%). Request verification for important decisions.`;
    }

    return `❌ Low trustworthiness. Weak areas: ${dimensions.filter(d => d.score < 0.5).map(d => d.name).join(', ')}. Reject answer or seek alternative.`;
  }

  private explainabilityLevel(score: number): string {
    if (score >= 0.9) return 'Excellent (clear reasoning + SHAP)';
    if (score >= 0.7) return 'Good (coherent reasoning)';
    if (score >= 0.5) return 'Moderate (some explanation)';
    return 'Poor (minimal reasoning)';
  }

  private uncertaintyLevel(score: number): string {
    if (score >= 0.9) return 'Excellent (proper calibration + conformal sets)';
    if (score >= 0.7) return 'Good (well-calibrated confidence)';
    if (score >= 0.5) return 'Moderate (rough uncertainty estimates)';
    return 'Poor (overconfident predictions)';
  }

  /**
   * Risk assessment for specific answer
   */
  assessAnswerRisk(
    answer: string,
    trustScore: number,
    domain: 'safety' | 'financial' | 'medical' | 'general',
  ): { risk_level: string; requires_review: boolean; suggested_actions: string[] } {
    const domainThresholds: { [key: string]: number } = {
      safety: 0.95,
      financial: 0.90,
      medical: 0.92,
      general: 0.75,
    };

    const threshold = domainThresholds[domain];
    const requires_review = trustScore < threshold;

    const actions: string[] = [];
    if (trustScore < 0.90) actions.push('Request verification');
    if (trustScore < 0.75) actions.push('Escalate to human expert');
    if (trustScore < 0.60) actions.push('Reject answer');

    return {
      risk_level: requires_review ? 'HIGH' : 'LOW',
      requires_review,
      suggested_actions: actions,
    };
  }
}

export const trustworthinessService = new TrustworthinessService();
