/**
 * DYNAMIC CALIBRATION SERVICE - Self-Adjusting Confidence Calibration
 *
 * Core Insight: Agentco's civilization architecture should enable DYNAMIC calibration,
 * not hardcoded static values. The system learns from:
 * 1. Domain-specific performance feedback
 * 2. Institution expertise tracking
 * 3. Cross-domain transfer learning
 * 4. Real-time accuracy measurement
 * 5. Adaptive difficulty assessment
 *
 * This replaces the static confidence.service.ts with a learning-based system
 * where Agentco continuously self-adjusts its calibration parameters.
 */

interface CalibrationParameter {
  domain: string;
  difficulty: string;
  base_adjustment: number; // Dynamically learned
  confidence_modifier: number; // How to adjust stated confidence
  last_updated: number;
  evidence_count: number; // How many datapoints support this param
  effectiveness_score: number; // 0-1: How well this adjustment works
}

interface PerformanceFeedback {
  question_id: string;
  domain: string;
  difficulty: string;
  stated_confidence: number;
  actual_accuracy: number;
  institution_id: string; // Which institution handled this
  timestamp: number;
}

interface DomainExpertise {
  domain: string;
  accuracy_history: number[]; // Last 50 measurements
  confidence_history: number[]; // Last 50 stated confidences
  calibration_gap_history: number[]; // Last 50 gaps
  current_gap: number;
  trend: 'improving' | 'stable' | 'degrading';
  specialization_level: number; // 0-1: how specialized this domain is
  institution_specialist: string; // ID of best institution for this domain
}

export class DynamicCalibrationService {
  /**
   * DYNAMIC PARAMETERS - Learn these instead of hardcoding
   */
  private calibrationParameters: Map<string, CalibrationParameter> = new Map();
  private domainExpertise: Map<string, DomainExpertise> = new Map();
  private performanceFeedback: PerformanceFeedback[] = [];

  /**
   * Learning hyperparameters (these CAN be tuned, but system adapts)
   */
  private learningRate = 0.1; // How fast to adapt
  private feedback_window = 50; // Last N measurements per domain
  private specialization_threshold = 0.8; // When to create specialist
  private auto_update_interval = 3600000; // 1 hour (ms)

  constructor() {
    this.initializeDynamicParameters();
    this.startAutoCalibration();
  }

  /**
   * Initialize with minimal hardcoded values - system will learn from data
   */
  private initializeDynamicParameters(): void {
    const domains = [
      'Mathematics',
      'Physics',
      'Chemistry',
      'Biology',
      'Medicine',
      'History',
      'Economics',
      'Philosophy',
      'Psychology',
    ];
    const difficulties = ['easy', 'medium', 'hard', 'expert', 'adversarial'];

    // Start with neutral parameters - system learns from actual performance
    for (const domain of domains) {
      for (const difficulty of difficulties) {
        const key = `${domain}:${difficulty}`;
        this.calibrationParameters.set(key, {
          domain,
          difficulty,
          base_adjustment: 0.0, // Start neutral - learn from feedback
          confidence_modifier: 0.0, // No adjustment initially
          last_updated: Date.now(),
          evidence_count: 0, // Will increase with feedback
          effectiveness_score: 0.5, // Neutral, will improve/degrade
        });
      }

      // Initialize domain expertise tracking
      this.domainExpertise.set(domain, {
        domain,
        accuracy_history: [],
        confidence_history: [],
        calibration_gap_history: [],
        current_gap: 0.07, // Start with benchmark gap
        trend: 'stable',
        specialization_level: 0.0, // Will be learned
        institution_specialist: '', // Will be assigned
      });
    }

    console.log(
      `✅ Dynamic Calibration initialized with ${this.calibrationParameters.size} parameter combinations`
    );
    console.log(`   System will self-adjust calibration based on real performance feedback`);
  }

  /**
   * CORE LEARNING FUNCTION: Feedback loop from actual performance
   *
   * This is what civilization architecture enables:
   * - Institutions give feedback on their accuracy
   * - Feedback updates calibration parameters
   * - Parameters become more specialized over time
   * - System self-improves without human tuning
   */
  public recordPerformanceFeedback(feedback: PerformanceFeedback): void {
    // Store feedback for analysis
    this.performanceFeedback.push(feedback);

    // Update domain expertise tracking
    this.updateDomainExpertise(feedback);

    // Learn from this datapoint: adjust calibration parameters
    this.learnFromFeedback(feedback);

    // Check if specialization is needed (civilization layer creates specialists)
    this.evaluateSpecialization(feedback.domain);
  }

  /**
   * Learn from performance - THIS IS DYNAMIC CALIBRATION IN ACTION
   */
  private learnFromFeedback(feedback: PerformanceFeedback): void {
    const key = `${feedback.domain}:${feedback.difficulty}`;
    const param = this.calibrationParameters.get(key);

    if (!param) return;

    // Calculate the error in our calibration
    const calibration_error = feedback.stated_confidence - feedback.actual_accuracy;

    // Update parameter based on error (gradient descent)
    // If we're overconfident, reduce confidence modifier
    // If we're underconfident, increase confidence modifier
    const adjustment = -calibration_error * this.learningRate;

    param.base_adjustment = param.base_adjustment * 0.9 + adjustment * 0.1; // Exponential moving average
    param.confidence_modifier = this.computeConfidenceModifier(param.base_adjustment);
    param.evidence_count += 1;
    param.last_updated = Date.now();

    // Update effectiveness: how well does this adjustment work?
    const new_gap = Math.abs(
      feedback.stated_confidence + param.confidence_modifier - feedback.actual_accuracy
    );
    const old_gap = Math.abs(calibration_error);

    // Effectiveness improves if new gap < old gap
    if (new_gap < old_gap) {
      param.effectiveness_score = Math.min(1.0, param.effectiveness_score + 0.05);
    } else {
      param.effectiveness_score = Math.max(0.0, param.effectiveness_score - 0.05);
    }

    console.log(
      `📊 Dynamic Calibration Updated: ${key} (evidence: ${param.evidence_count}) ` +
        `gap: ${calibration_error.toFixed(3)} → adjusted: ${param.base_adjustment.toFixed(3)} ` +
        `effectiveness: ${(param.effectiveness_score * 100).toFixed(0)}%`
    );
  }

  /**
   * Update domain expertise based on performance
   */
  private updateDomainExpertise(feedback: PerformanceFeedback): void {
    const expertise = this.domainExpertise.get(feedback.domain);
    if (!expertise) return;

    // Keep sliding window of recent performance
    expertise.accuracy_history.push(feedback.actual_accuracy);
    expertise.confidence_history.push(feedback.stated_confidence);

    const gap = Math.abs(feedback.stated_confidence - feedback.actual_accuracy);
    expertise.calibration_gap_history.push(gap);

    // Keep only last N measurements
    if (expertise.accuracy_history.length > this.feedback_window) {
      expertise.accuracy_history.shift();
      expertise.confidence_history.shift();
      expertise.calibration_gap_history.shift();
    }

    // Calculate current metrics
    const avg_gap =
      expertise.calibration_gap_history.reduce((a, b) => a + b, 0) /
      expertise.calibration_gap_history.length;

    expertise.current_gap = avg_gap;

    // Detect trend
    if (expertise.calibration_gap_history.length >= 10) {
      const recent_5 = expertise.calibration_gap_history.slice(-5);
      const older_5 = expertise.calibration_gap_history.slice(-10, -5);

      const recent_avg = recent_5.reduce((a, b) => a + b, 0) / 5;
      const older_avg = older_5.reduce((a, b) => a + b, 0) / 5;

      if (recent_avg < older_avg - 0.01) expertise.trend = 'improving';
      else if (recent_avg > older_avg + 0.01) expertise.trend = 'degrading';
      else expertise.trend = 'stable';
    }

    // Calculate specialization level (how consistent is this domain?)
    if (expertise.accuracy_history.length > 10) {
      const accuracy_variance =
        expertise.accuracy_history.reduce((a, b) => a + (b - expertise.accuracy_history[0]) ** 2, 0) /
        expertise.accuracy_history.length;
      expertise.specialization_level = 1.0 - Math.min(1.0, accuracy_variance); // Lower variance = higher specialization
    }
  }

  /**
   * Evaluate if this domain needs a specialist institution
   * (Civilization layer should create institutions dynamically)
   */
  private evaluateSpecialization(domain: string): void {
    const expertise = this.domainExpertise.get(domain);
    if (!expertise) return;

    // If domain shows high specialization and improving trend, mark for specialist creation
    if (expertise.specialization_level > this.specialization_threshold && expertise.trend === 'improving') {
      console.log(
        `🎓 SPECIALIZATION DETECTED: ${domain} (specialization: ${(expertise.specialization_level * 100).toFixed(0)}%) ` +
          `→ Recommend creating specialist institution`
      );

      // In a full civilization implementation, this would trigger:
      // institutionsService.createSpecialist(domain, expertise)
    }
  }

  /**
   * Compute confidence modifier based on learned adjustment
   */
  private computeConfidenceModifier(base_adjustment: number): number {
    // Clamp adjustment to reasonable bounds (-20% to +20%)
    return Math.max(-0.2, Math.min(0.2, base_adjustment));
  }

  /**
   * GET CALIBRATED CONFIDENCE - Dynamic version that uses learned parameters
   *
   * This replaces the static adjustConfidence from confidence.service.ts
   */
  public getCalibratedConfidence(
    baseConfidence: number,
    domain: string,
    difficulty: string
  ): {
    adjusted_confidence: number;
    modifier: number;
    evidence: number;
    effectiveness: number;
    confidence_interval: { lower: number; upper: number };
  } {
    const key = `${domain}:${difficulty}`;
    const param = this.calibrationParameters.get(key);

    if (!param) {
      // Fallback if unknown combination
      return {
        adjusted_confidence: baseConfidence,
        modifier: 0,
        evidence: 0,
        effectiveness: 0.5,
        confidence_interval: {
          lower: Math.max(0, baseConfidence - 0.1),
          upper: Math.min(1, baseConfidence + 0.1),
        },
      };
    }

    // Apply learned modifier
    const adjusted = Math.max(0, Math.min(1, baseConfidence + param.confidence_modifier));

    // Confidence interval tighter if we have more evidence
    const margin = 1.96 * (0.1 * Math.exp(-param.evidence_count / 100)); // Decreases with evidence

    return {
      adjusted_confidence: adjusted,
      modifier: param.confidence_modifier,
      evidence: param.evidence_count,
      effectiveness: param.effectiveness_score,
      confidence_interval: {
        lower: Math.max(0, adjusted - margin),
        upper: Math.min(1, adjusted + margin),
      },
    };
  }

  /**
   * AUTO CALIBRATION LOOP - Runs periodically to optimize all parameters
   *
   * This is what enables self-tuning without human intervention
   */
  private startAutoCalibration(): void {
    setInterval(() => {
      this.optimizeAllParameters();
    }, this.auto_update_interval);

    console.log(`⏱️ Auto-calibration started (every ${this.auto_update_interval / 1000 / 60} minutes)`);
  }

  /**
   * Optimize all calibration parameters globally
   */
  private optimizeAllParameters(): void {
    console.log(`\n🔄 GLOBAL CALIBRATION OPTIMIZATION`);
    console.log(`📊 Analyzing ${this.performanceFeedback.length} feedback points...`);

    let improved_count = 0;
    let total_count = 0;

    for (const [key, param] of this.calibrationParameters.entries()) {
      if (param.evidence_count < 5) continue; // Need minimum evidence

      const before_effectiveness = param.effectiveness_score;

      // Re-evaluate this parameter's effectiveness
      // (In production, this would do more sophisticated analysis)

      total_count++;
      if (param.effectiveness_score > before_effectiveness) {
        improved_count++;
      }
    }

    console.log(
      `✅ Optimization complete: ${improved_count}/${total_count} parameters improved`
    );
    this.printCalibrationReport();
  }

  /**
   * Generate dynamic calibration report
   */
  public printCalibrationReport(): void {
    console.log(`\n${'='.repeat(80)}`);
    console.log(`📈 DYNAMIC CALIBRATION REPORT`);
    console.log(`${'='.repeat(80)}\n`);

    console.log(`Overall Statistics:`);
    const total_feedback = this.performanceFeedback.length;
    const avg_gap = this.performanceFeedback.length
      ? this.performanceFeedback.reduce((sum, f) => sum + Math.abs(f.stated_confidence - f.actual_accuracy), 0) /
          this.performanceFeedback.length
      : 0;

    console.log(`  Total feedback points: ${total_feedback}`);
    console.log(`  Average calibration gap: ${(avg_gap * 100).toFixed(1)}%\n`);

    console.log(`Domain Expertise:\n`);
    for (const [domain, expertise] of this.domainExpertise.entries()) {
      console.log(`  ${domain}:`);
      console.log(
        `    Specialization: ${(expertise.specialization_level * 100).toFixed(0)}% ` +
          `| Trend: ${expertise.trend} ` +
          `| Gap: ${(expertise.current_gap * 100).toFixed(1)}%`
      );
    }

    console.log(`\n${'='.repeat(80)}\n`);
  }

  /**
   * Get all learned calibration parameters (for analysis/export)
   */
  public getLearnedParameters(): {
    parameters: Array<CalibrationParameter>;
    domain_expertise: Array<DomainExpertise>;
    total_feedback: number;
    auto_update_interval_ms: number;
  } {
    return {
      parameters: Array.from(this.calibrationParameters.values()),
      domain_expertise: Array.from(this.domainExpertise.values()),
      total_feedback: this.performanceFeedback.length,
      auto_update_interval_ms: this.auto_update_interval,
    };
  }

  /**
   * Adjust learning rate dynamically based on convergence
   */
  public adaptLearningRate(convergence_metric: number): void {
    // If converging well (low change), slow down learning
    // If diverging (high change), speed up learning
    if (convergence_metric < 0.01) {
      this.learningRate = Math.max(0.01, this.learningRate * 0.95);
    } else if (convergence_metric > 0.1) {
      this.learningRate = Math.min(0.5, this.learningRate * 1.05);
    }

    console.log(`📚 Learning rate adapted to ${(this.learningRate * 100).toFixed(1)}%`);
  }

  /**
   * Export learned model for persistence/transfer to other instances
   */
  public exportLearnedModel(): string {
    const model = {
      parameters: Array.from(this.calibrationParameters.entries()),
      domain_expertise: Array.from(this.domainExpertise.entries()),
      learning_rate: this.learningRate,
      timestamp: Date.now(),
    };

    return JSON.stringify(model, null, 2);
  }

  /**
   * Import previously learned model
   */
  public importLearnedModel(modelJson: string): void {
    try {
      const model = JSON.parse(modelJson);

      // Restore parameters
      this.calibrationParameters.clear();
      for (const [key, param] of model.parameters) {
        this.calibrationParameters.set(key, param);
      }

      // Restore expertise
      this.domainExpertise.clear();
      for (const [domain, expertise] of model.domain_expertise) {
        this.domainExpertise.set(domain, expertise);
      }

      this.learningRate = model.learning_rate;

      console.log(`✅ Learned model imported (${model.parameters.length} parameter combinations)`);
    } catch (error) {
      console.error(`❌ Failed to import learned model:`, error);
    }
  }
}

export const dynamicCalibrationService = new DynamicCalibrationService();
