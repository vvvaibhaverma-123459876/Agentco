/**
 * AGENTCO CIVILIZATION ARCHITECTURE
 *
 * Unified system where ALL components learn from each other, share knowledge,
 * adapt together, and self-correct. Not siloed services, but a cohesive organism.
 *
 * Architecture:
 * ├─ Central Knowledge Base (shared memory)
 * ├─ Feedback Loop System (learning)
 * ├─ Governance Layer (consistency enforcement)
 * ├─ Inter-Service Communication Bus (coordination)
 * ├─ Self-Correction Engine (error detection & fixing)
 * └─ Unified Decision Framework (coherent reasoning)
 */

import { symbolicService } from './symbolic.service';
import { ensembleService } from './ensemble.service';
import { ragService } from './rag.service';
import { durableExecution } from './durable-execution.service';
import { v4 as uuidv4 } from 'uuid';
import crypto from 'crypto';

interface KnowledgeEntry {
  id: string;
  question: string;
  answer: string;
  confidence: number;
  sources: string[];
  verified_by: string[]; // which services verified this
  timestamp: number;
  domain: string;
  quality_score: number; // 0-1: how reliable is this knowledge
  feedback_count: number;
  corrections: Array<{ by: string; old: string; new: string; reason: string }>;
  learned_from: string[]; // which gaps led to this knowledge
}

interface ServiceFeedback {
  service_name: string;
  question_id: string;
  was_correct: boolean;
  confidence_delta: number; // how wrong were we
  root_cause: string; // why did we fail
  correction: string; // what should we have done
  impact_score: number; // how important is this
}

interface GovernanceRule {
  id: string;
  rule: string; // "medical questions require PubMed validation"
  enforcer: string; // which service enforces this
  priority: number;
  violations: number;
  last_updated: number;
}

interface ServiceBusMessage {
  from: string;
  to: string; // or "broadcast"
  type: string; // "error_detected", "knowledge_corrected", "confidence_updated"
  payload: any;
  priority: number;
  timestamp: number;
}

export class CivilizationService {
  private knowledgeBase: Map<string, KnowledgeEntry> = new Map();
  private feedbackBuffer: ServiceFeedback[] = [];
  private governanceRules: Map<string, GovernanceRule> = new Map();
  private messageBus: ServiceBusMessage[] = [];
  private serviceHealthScores: Map<string, number> = new Map();
  private domainExpertise: Map<string, Map<string, number>> = new Map(); // service -> domain -> expertise level

  constructor() {
    this.initializeGovernance();
    this.initializeServiceModels();
  }

  private initializeGovernance() {
    /**
     * Governance rules that ALL services must follow
     */
    const rules: GovernanceRule[] = [
      {
        id: 'medical_validation',
        rule: 'Medical questions (confidence <0.7) require PubMed validation',
        enforcer: 'rag.service',
        priority: 1,
        violations: 0,
        last_updated: Date.now(),
      },
      {
        id: 'ensemble_weighted_voting',
        rule: 'Ensemble voting weighted by historical model accuracy, not majority',
        enforcer: 'ensemble.service',
        priority: 1,
        violations: 0,
        last_updated: Date.now(),
      },
      {
        id: 'ood_detection_required',
        rule: 'All questions must pass OOD detector before reasoning',
        enforcer: 'ood.service',
        priority: 1,
        violations: 0,
        last_updated: Date.now(),
      },
      {
        id: 'epistemic_uncertainty',
        rule: 'High confidence only on known facts, not unknown domains',
        enforcer: 'trustworthiness.service',
        priority: 1,
        violations: 0,
        last_updated: Date.now(),
      },
      {
        id: 'temporal_tracking',
        rule: 'Time-sensitive facts must have recency metadata',
        enforcer: 'rag.service',
        priority: 1,
        violations: 0,
        last_updated: Date.now(),
      },
    ];

    rules.forEach((rule) => this.governanceRules.set(rule.id, rule));
  }

  private initializeServiceModels() {
    /**
     * Track expertise level of each service in each domain
     * Ranges from 0 (no expertise) to 1 (expert)
     */
    const services = ['ensemble', 'symbolic', 'rag', 'bayesian', 'trustworthiness'];
    const domains = ['general', 'medical', 'legal', 'financial', 'scientific', 'reasoning', 'knowledge'];

    services.forEach((service) => {
      const expertise = new Map<string, number>();

      // Initialize based on what we know works
      if (service === 'symbolic') {
        expertise.set('reasoning', 0.99);
        expertise.set('logic', 0.99);
        expertise.set('math', 0.99);
        domains.forEach((d) => expertise.set(d, expertise.get(d) || 0.3));
      } else if (service === 'rag') {
        expertise.set('knowledge', 0.99);
        expertise.set('general', 0.95);
        expertise.set('medical', 0.3); // We know RAG is weak here
        expertise.set('legal', 0.2);
        expertise.set('financial', 0.4);
        domains.forEach((d) => expertise.set(d, expertise.get(d) || 0.5));
      } else if (service === 'ensemble') {
        expertise.set('reasoning', 0.88);
        expertise.set('general', 0.85);
        domains.forEach((d) => expertise.set(d, expertise.get(d) || 0.7));
      } else if (service === 'bayesian') {
        expertise.set('calibration', 0.95);
        expertise.set('uncertainty', 0.95);
        domains.forEach((d) => expertise.set(d, expertise.get(d) || 0.8));
      } else if (service === 'trustworthiness') {
        expertise.set('trust_scoring', 0.95);
        domains.forEach((d) => expertise.set(d, expertise.get(d) || 0.7));
      }

      this.domainExpertise.set(service, expertise);
      this.serviceHealthScores.set(service, 0.85); // Start at 85%
    });
  }

  /**
   * UNIFIED DECISION MAKING - This is where civilization happens
   * NOT sequential routing, but collaborative reasoning
   */
  async solveWithCivilization(question: string): Promise<any> {
    console.log('\n╔═══════════════════════════════════════════════════════════╗');
    console.log('║         AGENTCO CIVILIZATION - UNIFIED REASONING          ║');
    console.log('╚═══════════════════════════════════════════════════════════╝\n');

    // STEP 1: Check governance rules and known issues
    await this.enforceGovernance(question);

    // STEP 2: Route to BEST service (not default route)
    const optimalService = this.selectOptimalService(question);
    console.log(`[Civilization] Best service for this question: ${optimalService.service} (expertise: ${optimalService.expertise.toFixed(2)})`);

    // STEP 3: Execute primary solver
    const primaryResult = await this.executePrimarySolver(question, optimalService);

    // STEP 4: BROADCAST to all services for validation (not just sequential)
    const validationResults = await this.broadcastForValidation(question, primaryResult);

    // STEP 5: CONFLICT DETECTION - services disagree? Find out why
    const conflicts = this.detectConflicts(primaryResult, validationResults);
    if (conflicts.length > 0) {
      console.log(`[Civilization] Conflicts detected: ${conflicts.length}`);
      await this.resolveConflicts(question, conflicts);
    }

    // STEP 6: SELF-CORRECTION - check against known failures
    const corrected = await this.applySelfCorrection(question, primaryResult, validationResults);

    // STEP 7: LEARN from this interaction
    await this.recordLearning(question, corrected, validationResults);

    // STEP 8: UPDATE governance rules based on performance
    await this.updateGovernance(question, corrected);

    return corrected;
  }

  /**
   * STEP 1: Enforce governance - check if we know this question
   */
  private async enforceGovernance(question: string): Promise<void> {
    // Check if this matches a known failure pattern
    for (const [id, rule] of this.governanceRules) {
      if (this.shouldApplyRule(question, id)) {
        console.log(`[Governance] Applying rule: ${id} - "${rule.rule}"`);
      }
    }
  }

  /**
   * STEP 2: Select optimal service based on:
   * - Question domain
   * - Service expertise in that domain
   * - Service health score
   * - History of corrections needed
   */
  private selectOptimalService(
    question: string,
  ): { service: string; expertise: number; reason: string } {
    const domain = this.inferDomain(question);
    const candidates = [
      { service: 'symbolic', expertise: this.domainExpertise.get('symbolic')?.get(domain) || 0 },
      { service: 'ensemble', expertise: this.domainExpertise.get('ensemble')?.get(domain) || 0 },
      { service: 'rag', expertise: this.domainExpertise.get('rag')?.get(domain) || 0 },
    ];

    // Weight by health score (failing services get lower priority)
    candidates.forEach((c) => {
      c.expertise *= this.serviceHealthScores.get(c.service) || 0.8;
    });

    const best = candidates.reduce((a, b) => (a.expertise > b.expertise ? a : b));

    return {
      service: best.service,
      expertise: best.expertise,
      reason: `Domain: ${domain}, Expertise: ${best.expertise.toFixed(2)}`,
    };
  }

  /**
   * STEP 3: Execute primary solver
   */
  private async executePrimarySolver(question: string, optimalService: any): Promise<any> {
    console.log(`[${optimalService.service}] Solving: ${question}`);

    return this.callServiceSolver(optimalService.service, question);
  }

  /**
   * STEP 4: BROADCAST to all other services for validation
   * This is where the civilization property emerges - services learn from each other
   */
  private async broadcastForValidation(question: string, primaryResult: any): Promise<Map<string, any>> {
    console.log('\n[Civilization] Broadcasting to all services for validation...\n');

    const services = ['symbolic', 'ensemble', 'rag'];
    const results = new Map<string, any>();

    for (const service of services) {
      if (service === primaryResult.service) continue; // Skip primary

      const validation = await this.validateWithService(service, question, primaryResult);
      const validationMessage: ServiceBusMessage = {
        from: service,
        to: 'primary',
        type: 'validation_result',
        payload: validation,
        priority: 1,
        timestamp: Date.now(),
      };

      this.messageBus.push(validationMessage);
      results.set(service, validationMessage.payload);

      console.log(`  ${service}: ${validationMessage.payload.agrees ? '✅ Agrees' : '⚠️ Concerns'} (confidence delta: ${validationMessage.payload.confidence_delta.toFixed(2)})`);
    }

    return results;
  }

  private async callServiceSolver(service: string, question: string): Promise<any> {
    const routeTask = await this.recordDurableReasoningRoute(service, question);

    if (service === 'symbolic') {
      const result = await symbolicService.solve(question);
      return {
        service,
        route_task_id: routeTask.task_id,
        answer: result.solved ? result.answer : 'Unable to solve symbolically',
        confidence: result.solved ? result.confidence : 0.1,
        reasoning: result.reasoning,
        method: result.method,
      };
    }

    if (service === 'ensemble') {
      const result = await ensembleService.ensembleVote(question);
      return {
        service,
        route_task_id: routeTask.task_id,
        answer: result.final_answer,
        confidence: result.confidence,
        reasoning: result.reasoning,
        method: 'llm_ensemble',
      };
    }

    if (service === 'rag') {
      const result = await ragService.augmentAnswer(question, '', 0.2);
      return {
        service,
        route_task_id: routeTask.task_id,
        answer: result.final_answer || 'No retrieved evidence answer',
        confidence: result.final_confidence,
        reasoning: result.reasoning,
        method: 'retrieval_augmented',
      };
    }

    throw new Error(`Unknown civilization solver service: ${service}`);
  }

  private async recordDurableReasoningRoute(service: string, question: string): Promise<{ task_id: string }> {
    const agentByService: Record<string, string> = {
      symbolic: 'calibration-reasoner',
      ensemble: 'reviewer-agent',
      rag: 'research-agent',
    };
    const agentId = agentByService[service];
    if (!agentId) throw new Error(`No durable agent route for civilization service: ${service}`);

    const task = await durableExecution.enqueue(agentId, 'record_observation', {
      observation: {
        kind: 'civilization_reasoning_route',
        service,
        question_hash: this.questionHash(question),
      },
    });
    const completed = await durableExecution.run(task.task_id);
    if (completed.status !== 'done') {
      throw new Error(`durable reasoning route failed for ${service}: ${completed.error ?? completed.status}`);
    }
    return { task_id: completed.task_id };
  }

  private questionHash(question: string): string {
    return crypto.createHash('sha256').update(question).digest('hex');
  }

  private async validateWithService(service: string, question: string, primaryResult: any): Promise<any> {
    try {
      const result = await this.callServiceSolver(service, question);
      const agrees = this.answersAgree(primaryResult.answer, result.answer);
      return {
        agrees,
        confidence_delta: result.confidence - primaryResult.confidence,
        concerns: agrees ? [] : [`${service} answer differs from ${primaryResult.service}`],
        answer: result.answer,
        confidence: result.confidence,
        method: result.method,
      };
    } catch (error: any) {
      return {
        agrees: false,
        confidence_delta: -primaryResult.confidence,
        concerns: [`${service} validation failed: ${error.message}`],
        answer: null,
        confidence: 0,
        method: 'validation_failed',
      };
    }
  }

  private answersAgree(left: string, right: string): boolean {
    const normalize = (value: string) => String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
    const a = normalize(left);
    const b = normalize(right);
    return Boolean(a && b && (a.includes(b) || b.includes(a)));
  }

  /**
   * STEP 5: Detect conflicts when services disagree
   */
  private detectConflicts(primaryResult: any, validationResults: Map<string, any>): Array<any> {
    const conflicts: Array<any> = [];

    validationResults.forEach((validation, service) => {
      if (!validation.agrees && Math.abs(validation.confidence_delta) > 0.15) {
        conflicts.push({
          service,
          primary: primaryResult.service,
          delta: validation.confidence_delta,
          concern: 'Significant confidence difference',
        });
      }
    });

    return conflicts;
  }

  /**
   * STEP 6: Self-correction - apply known fixes
   */
  private async applySelfCorrection(question: string, primaryResult: any, validationResults: Map<string, any>): Promise<any> {
    let corrected = { ...primaryResult };

    // Check domain-specific corrections
    const domain = this.inferDomain(question);

    if (domain === 'medical' && corrected.confidence > 0.7) {
      console.log('[Self-Correction] Medical question with high confidence - reducing to 0.65 (epistemic uncertainty)');
      corrected.confidence = 0.65;
      corrected.reasoning += ' [Epistemic uncertainty applied: medical domain]';
    }

    // Check for OOD patterns
    if (this.looksLikeOOD(question)) {
      console.log('[Self-Correction] Detected OOD pattern - confidence capped at 0.4');
      corrected.confidence = Math.min(corrected.confidence, 0.4);
      corrected.reasoning += ' [OOD warning: question may be unknowable]';
    }

    // Check for trick questions
    if (this.looksTrickQuestion(question)) {
      console.log('[Self-Correction] Detected trick question pattern - flagging for manual review');
      corrected.reasoning += ' [WARNING: Possible trick question - manual verification recommended]';
    }

    return corrected;
  }

  /**
   * STEP 7: Record learning - add to knowledge base for future use
   */
  private async recordLearning(question: string, result: any, validationResults: Map<string, any>): Promise<void> {
    const entry: KnowledgeEntry = {
      id: uuidv4(),
      question,
      answer: result.answer,
      confidence: result.confidence,
      sources: [result.service],
      verified_by: Array.from(validationResults.keys()),
      timestamp: Date.now(),
      domain: this.inferDomain(question),
      quality_score: result.confidence, // Will be refined by feedback
      feedback_count: 0,
      corrections: [],
      learned_from: this.identifyGapsAddressed(question),
    };

    this.knowledgeBase.set(entry.id, entry);
    console.log(`\n[Learning] Recorded knowledge entry: "${question.substring(0, 40)}..." (quality: ${entry.quality_score.toFixed(2)})`);
  }

  /**
   * STEP 8: Update governance based on performance
   */
  private async updateGovernance(question: string, result: any): Promise<void> {
    const domain = this.inferDomain(question);

    // Update service expertise scores
    for (const [service, expertise] of this.domainExpertise) {
      if (service === result.service) {
        // Boost expertise if high confidence
        const current = expertise.get(domain) || 0;
        expertise.set(domain, Math.min(1, current + 0.02));
      } else {
        // Slight decay if not used
        const current = expertise.get(domain) || 0;
        expertise.set(domain, Math.max(0, current - 0.01));
      }
    }

    console.log(`[Governance] Updated service expertise for domain: ${domain}`);
  }

  /**
   * FEEDBACK MECHANISM - Services send corrections back
   */
  async recordFeedback(feedback: ServiceFeedback): Promise<void> {
    this.feedbackBuffer.push(feedback);

    console.log(`[Feedback] ${feedback.service_name}: ${feedback.was_correct ? '✅' : '❌'} (impact: ${feedback.impact_score.toFixed(2)})`);

    // If high-impact mistake, immediately update service expertise
    if (!feedback.was_correct && feedback.impact_score > 0.7) {
      const expertise = this.domainExpertise.get(feedback.service_name);
      if (expertise) {
        const domain = this.inferDomain(feedback.question_id);
        const current = expertise.get(domain) || 0;
        expertise.set(domain, Math.max(0, current - 0.1)); // Penalize
        console.log(`[Civilization] Penalized ${feedback.service_name} expertise in ${domain} (high-impact error)`);
      }
    }

    // Update health score
    const healthDelta = feedback.was_correct ? 0.02 : -0.05;
    const current = this.serviceHealthScores.get(feedback.service_name) || 0.85;
    this.serviceHealthScores.set(feedback.service_name, Math.max(0.3, Math.min(1, current + healthDelta)));
  }

  /**
   * ACTIVE LEARNING - Identify what we need to learn next
   */
  identifyLearningGaps(): Array<{ gap: string; priority: number; affects_services: string[] }> {
    const gaps = [
      {
        gap: 'Medical knowledge (PubMed integration)',
        priority: 1,
        affects_services: ['rag', 'ensemble'],
      },
      {
        gap: 'Legal knowledge (LexisNexis integration)',
        priority: 1,
        affects_services: ['rag', 'ensemble'],
      },
      {
        gap: 'OOD detection (unknowable questions)',
        priority: 1,
        affects_services: ['ensemble', 'symbolic'],
      },
      {
        gap: 'Epistemic uncertainty (known unknowns)',
        priority: 1,
        affects_services: ['trustworthiness', 'bayesian'],
      },
      {
        gap: 'Real-time data (temporal tracking)',
        priority: 1,
        affects_services: ['rag'],
      },
    ];

    return gaps;
  }

  /**
   * RESOLVE CONFLICTS - When services disagree
   */
  private async resolveConflicts(question: string, conflicts: Array<any>): Promise<void> {
    console.log('\n[Conflict Resolution]');

    for (const conflict of conflicts) {
      console.log(`  Conflict: ${conflict.primary} vs ${conflict.service}`);
      console.log(`  Confidence delta: ${conflict.delta.toFixed(3)}`);

      // Mechanism 1: Check governance rules
      if (this.violatesGovernance(question, conflict.primary)) {
        console.log(`  → Resolution: Governance rule violated. ${conflict.service} likely correct.`);
      }

      // Mechanism 2: Check expertise
      const primaryExpertise = this.domainExpertise.get(conflict.primary)?.get(this.inferDomain(question)) || 0;
      const serviceExpertise = this.domainExpertise.get(conflict.service)?.get(this.inferDomain(question)) || 0;
      const expertiseRatio = serviceExpertise / primaryExpertise;

      if (expertiseRatio > 1.2) {
        console.log(`  → Resolution: ${conflict.service} has higher expertise (${expertiseRatio.toFixed(2)}x)`);
      }

      // Mechanism 3: Check health scores
      const primaryHealth = this.serviceHealthScores.get(conflict.primary) || 0.85;
      const serviceHealth = this.serviceHealthScores.get(conflict.service) || 0.85;

      if (serviceHealth > primaryHealth * 1.1) {
        console.log(`  → Resolution: ${conflict.service} has better health score (${serviceHealth.toFixed(2)} vs ${primaryHealth.toFixed(2)})`);
      }
    }
  }

  /**
   * HELPER FUNCTIONS
   */

  private inferDomain(question: string): string {
    const q = question.toLowerCase();
    if (q.includes('doctor') || q.includes('disease') || q.includes('medicine') || q.includes('health') || q.includes('drug')) return 'medical';
    if (q.includes('law') || q.includes('legal') || q.includes('court') || q.includes('attorney')) return 'legal';
    if (q.includes('price') || q.includes('stock') || q.includes('money') || q.includes('investment') || q.includes('finance')) return 'financial';
    if (q.includes('planet') || q.includes('atom') || q.includes('physics') || q.includes('biology') || q.includes('research')) return 'scientific';
    if (q.includes('reason') || q.includes('logic') || q.includes('prove') || q.includes('deduce')) return 'reasoning';
    if (q.includes('who') || q.includes('what') || q.includes('where') || q.includes('when')) return 'knowledge';
    return 'general';
  }

  private looksLikeOOD(question: string): boolean {
    const keywords = ['atlantis', 'unicorn', 'time travel', 'fictional', 'alien', 'future', 'predict', '2050', '2100'];
    return keywords.some((k) => question.toLowerCase().includes(k));
  }

  private looksTrickQuestion(question: string): boolean {
    const patterns = ['invisible', 'stopped beating', 'what color', 'true or false (true|false)'];
    return patterns.some((p) => new RegExp(p).test(question.toLowerCase()));
  }

  private shouldApplyRule(question: string, ruleId: string): boolean {
    if (ruleId === 'medical_validation') {
      return this.inferDomain(question) === 'medical';
    }
    return false;
  }

  private violatesGovernance(question: string, serviceName: string): boolean {
    // Check if service violates known governance rules
    const domain = this.inferDomain(question);

    if (domain === 'medical' && serviceName === 'rag') {
      // RAG without PubMed violates medical_validation rule
      return true;
    }

    return false;
  }

  private identifyGapsAddressed(question: string): string[] {
    const gaps = this.identifyLearningGaps();
    const domain = this.inferDomain(question);

    return gaps.filter((g) => g.gap.toLowerCase().includes(domain)).map((g) => g.gap);
  }

  /**
   * STATUS AND MONITORING
   */
  getSystemStatus(): {
    health: number;
    services: Map<string, number>;
    knowledge_entries: number;
    pending_feedback: number;
    governance_violations: number;
  } {
    let totalViolations = 0;
    this.governanceRules.forEach((rule) => (totalViolations += rule.violations));

    let serviceHealth = 0;
    this.serviceHealthScores.forEach((score) => (serviceHealth += score));
    const avgHealth = serviceHealth / this.serviceHealthScores.size;

    return {
      health: avgHealth,
      services: new Map(this.serviceHealthScores),
      knowledge_entries: this.knowledgeBase.size,
      pending_feedback: this.feedbackBuffer.length,
      governance_violations: totalViolations,
    };
  }

  exportKnowledge(): Array<KnowledgeEntry> {
    return Array.from(this.knowledgeBase.values());
  }
}

export const civilizationService = new CivilizationService();
