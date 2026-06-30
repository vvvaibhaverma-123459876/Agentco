/**
 * INSTITUTIONS SERVICE - Specialized Domain Learning Entities
 *
 * Institutions are self-organizing sub-civilizations that:
 * 1. Specialize in specific domains (Biology, Medicine, Physics, etc.)
 * 2. Learn from research papers and domain knowledge
 * 3. Evolve expertise over time through feedback
 * 4. Share knowledge with other institutions
 * 5. Self-organize based on demand and opportunity
 *
 * Architecture:
 * Civilization → Institutions (specialized) → Domain Expertise
 */

import crypto from 'crypto';
import { db } from '../db/client';
import { identityAuthorityService } from './identity-authority.service';

interface ResearchPaper {
  id: string;
  title: string;
  abstract: string;
  content: string;
  domain: string;
  citations: number;
  published_date: string;
  authors: string[];
  keywords: string[];
  quality_score: number; // 0-1 based on citations, peer review
}

interface InstitutionKnowledge {
  topic: string;
  confidence: number;
  source_papers: string[];
  interconnections: Map<string, number>; // related topics and strength
  last_updated: number;
  times_used: number;
  correctness_rate: number; // from feedback
}

interface InstitutionSpecialty {
  domain: string;
  expertise_level: number; // 0-1
  papers_read: number;
  knowledge_entries: number;
  success_rate: number;
  evolution_stage: number; // 1-5: nascent → mature
}

interface InstitutionMetrics {
  id: string;
  name: string;
  domain: string;
  total_expertise: number;
  papers_ingested: number;
  knowledge_entries: number;
  accuracy: number;
  growth_rate: number;
  health_score: number;
  evolution_stage: string;
  specialties: InstitutionSpecialty[];
  created_at: number;
  last_activity: number;
}

interface CanonicalInstitutionInput {
  name: string;
  domain: string;
  purpose?: string;
  authorityScope?: string[];
  metadata?: Record<string, unknown>;
}

interface CanonicalDepartmentRecord {
  id: string;
  name: string;
}

interface CanonicalInstitutionRecord {
  institutionId: string;
  actorId: string;
  departments: CanonicalDepartmentRecord[];
}

export class Institution {
  id: string;
  name: string;
  primary_domain: string;
  knowledge_base: Map<string, InstitutionKnowledge> = new Map();
  specialties: Map<string, InstitutionSpecialty> = new Map();
  papers_ingested: ResearchPaper[] = [];
  accuracy_history: number[] = [];
  feedback_buffer: Array<{ correct: boolean; topic: string; impact: number }> = [];
  interconnections: Map<string, number> = new Map(); // connections to other institutions
  creation_date: number;
  evolution_stage: number = 1; // 1-5: nascent → mature

  constructor(id: string, name: string, domain: string) {
    this.id = id;
    this.name = name;
    this.primary_domain = domain;
    this.creation_date = Date.now();
    this.initializeSpecialties();
  }

  private initializeSpecialties(): void {
    const domain_specialties: Record<string, InstitutionSpecialty> = {
      primary: {
        domain: this.primary_domain,
        expertise_level: 0.1, // Start nascent
        papers_read: 0,
        knowledge_entries: 0,
        success_rate: 0.5,
        evolution_stage: 1,
      },
      secondary: {
        domain: 'interdisciplinary',
        expertise_level: 0.0,
        papers_read: 0,
        knowledge_entries: 0,
        success_rate: 0.5,
        evolution_stage: 0,
      },
    };

    Object.entries(domain_specialties).forEach(([key, spec]) => {
      this.specialties.set(key, spec);
    });
  }

  /**
   * Ingest a research paper and learn from it
   */
  ingestPaper(paper: ResearchPaper): { learned_topics: number; expertise_gained: number } {
    console.log(`[Institution ${this.name}] Ingesting paper: "${paper.title}"`);

    this.papers_ingested.push(paper);

    // Extract knowledge from paper
    const learned_topics = this.extractKnowledgeFromPaper(paper);
    const expertise_gained = paper.quality_score * (paper.citations / 100); // Quality × Impact

    // Update primary specialty
    const primary = this.specialties.get('primary');
    if (primary) {
      primary.papers_read += 1;
      primary.knowledge_entries += learned_topics;
      primary.expertise_level = Math.min(1, primary.expertise_level + expertise_gained * 0.1);
    }

    // Check if we should create secondary specialty
    if (learned_topics > 5 && paper.domain !== this.primary_domain) {
      this.createSecondarySpecialty(paper.domain);
    }

    // Update evolution stage
    this.updateEvolutionStage();

    return {
      learned_topics,
      expertise_gained,
    };
  }

  /**
   * Extract knowledge from paper content
   */
  private extractKnowledgeFromPaper(paper: ResearchPaper): number {
    const keywords = paper.keywords || [];
    let topics_learned = 0;

    for (const keyword of keywords) {
      if (!this.knowledge_base.has(keyword)) {
        const knowledge: InstitutionKnowledge = {
          topic: keyword,
          confidence: paper.quality_score * 0.8, // Quality-based confidence
          source_papers: [paper.id],
          interconnections: new Map(),
          last_updated: Date.now(),
          times_used: 0,
          correctness_rate: 0.5,
        };

        this.knowledge_base.set(keyword, knowledge);
        topics_learned += 1;
      } else {
        // Strengthen existing knowledge
        const existing = this.knowledge_base.get(keyword);
        if (existing) {
          existing.confidence = Math.min(1, existing.confidence + 0.05);
          existing.source_papers.push(paper.id);
          existing.last_updated = Date.now();
        }
      }
    }

    // Create interconnections between topics
    this.createInterconnections(keywords);

    return topics_learned;
  }

  /**
   * Create connections between learned topics
   */
  private createInterconnections(keywords: string[]): void {
    for (let i = 0; i < keywords.length; i++) {
      for (let j = i + 1; j < keywords.length; j++) {
        const key1 = keywords[i];
        const key2 = keywords[j];

        const knowledge1 = this.knowledge_base.get(key1);
        const knowledge2 = this.knowledge_base.get(key2);

        if (knowledge1 && knowledge2) {
          const existing = knowledge1.interconnections.get(key2) || 0;
          knowledge1.interconnections.set(key2, existing + 0.5);
          knowledge2.interconnections.set(key1, existing + 0.5);
        }
      }
    }
  }

  /**
   * Create secondary specialty if institution learns outside primary domain
   */
  private createSecondarySpecialty(domain: string): void {
    if (!this.specialties.has(`secondary_${domain}`)) {
      console.log(`[Institution ${this.name}] Creating secondary specialty: ${domain}`);

      const specialty: InstitutionSpecialty = {
        domain,
        expertise_level: 0.3,
        papers_read: 1,
        knowledge_entries: 0,
        success_rate: 0.5,
        evolution_stage: 1,
      };

      this.specialties.set(`secondary_${domain}`, specialty);

      // Record interconnection with other domain
      const current = this.interconnections.get(domain) || 0;
      this.interconnections.set(domain, current + 1);
    }
  }

  /**
   * Update evolution stage based on knowledge accumulation
   */
  private updateEvolutionStage(): void {
    const primary = this.specialties.get('primary');
    if (!primary) return;

    const knowledge_count = this.knowledge_base.size;
    const papers_count = this.papers_ingested.length;
    const expertise = primary.expertise_level;

    // Evolution stages: nascent → emerging → developing → advanced → mature
    if (expertise < 0.2 || knowledge_count < 10) {
      this.evolution_stage = 1; // Nascent
    } else if (expertise < 0.4 || knowledge_count < 30) {
      this.evolution_stage = 2; // Emerging
    } else if (expertise < 0.6 || knowledge_count < 60) {
      this.evolution_stage = 3; // Developing
    } else if (expertise < 0.8 || knowledge_count < 100) {
      this.evolution_stage = 4; // Advanced
    } else {
      this.evolution_stage = 5; // Mature
    }

    if (primary) {
      primary.evolution_stage = this.evolution_stage;
    }
  }

  /**
   * Record feedback on institution's knowledge
   */
  recordFeedback(topic: string, was_correct: boolean, impact: number): void {
    this.feedback_buffer.push({
      correct: was_correct,
      topic,
      impact,
    });

    // Update knowledge correctness
    const knowledge = this.knowledge_base.get(topic);
    if (knowledge) {
      const current_rate = knowledge.correctness_rate;
      const new_rate = was_correct ? current_rate + 0.05 : current_rate - 0.1;
      knowledge.correctness_rate = Math.max(0, Math.min(1, new_rate));
    }

    // Update specialty success rate
    const primary = this.specialties.get('primary');
    if (primary) {
      const current_success = primary.success_rate;
      const new_success = was_correct ? current_success + 0.02 : current_success - 0.05;
      primary.success_rate = Math.max(0.3, Math.min(1, new_success));
    }
  }

  /**
   * Query institution's knowledge
   */
  queryKnowledge(topic: string): {
    known: boolean;
    confidence: number;
    related_topics: string[];
    reasoning: string;
  } {
    const knowledge = this.knowledge_base.get(topic);

    if (!knowledge) {
      return {
        known: false,
        confidence: 0,
        related_topics: [],
        reasoning: `Institution ${this.name} has no knowledge of "${topic}"`,
      };
    }

    const related = Array.from(knowledge.interconnections.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([t]) => t);

    return {
      known: true,
      confidence: knowledge.confidence * knowledge.correctness_rate,
      related_topics: related,
      reasoning: `Known from ${knowledge.source_papers.length} papers, confidence: ${knowledge.confidence.toFixed(2)}`,
    };
  }

  /**
   * Get institution metrics
   */
  getMetrics(): InstitutionMetrics {
    const primary = this.specialties.get('primary');
    const accuracy = this.accuracy_history.length > 0
      ? this.accuracy_history.reduce((a, b) => a + b) / this.accuracy_history.length
      : 0;

    const growth_rate = this.papers_ingested.length > 0
      ? this.knowledge_base.size / this.papers_ingested.length
      : 0;

    const health_score =
      (primary?.expertise_level || 0) * 0.4 +
      (primary?.success_rate || 0.5) * 0.3 +
      accuracy * 0.3;

    const evolution_names = ['', 'Nascent', 'Emerging', 'Developing', 'Advanced', 'Mature'];

    return {
      id: this.id,
      name: this.name,
      domain: this.primary_domain,
      total_expertise: primary?.expertise_level || 0,
      papers_ingested: this.papers_ingested.length,
      knowledge_entries: this.knowledge_base.size,
      accuracy,
      growth_rate,
      health_score,
      evolution_stage: evolution_names[this.evolution_stage],
      specialties: Array.from(this.specialties.values()),
      created_at: this.creation_date,
      last_activity: Date.now(),
    };
  }
}

export class InstitutionsService {
  institutions: Map<string, Institution> = new Map();
  paper_registry: Map<string, ResearchPaper> = new Map();
  inter_institution_knowledge: Map<string, number> = new Map(); // which institutions collaborate

  /**
   * Create a new institution for a domain
   */
  createInstitution(domain: string): Institution {
    const id = `inst_${domain}_${Date.now()}`;
    const name = this.generateInstitutionName(domain);
    const institution = new Institution(id, name, domain);

    this.institutions.set(id, institution);

    console.log(`\n✅ Institution Created: ${name}`);
    console.log(`   Domain: ${domain}`);
    console.log(`   ID: ${id}\n`);

    return institution;
  }

  async createCanonicalInstitution(input: CanonicalInstitutionInput): Promise<CanonicalInstitutionRecord> {
    const actor = await identityAuthorityService.registerActor({
      actor_type: 'institution',
      name: input.name,
      metadata: {
        domain: input.domain,
        ...(input.metadata ?? {}),
      },
    });
    const institutionId = crypto.randomUUID();
    const authorityScope = input.authorityScope ?? ['research_request'];
    await db.query(
      `INSERT INTO institutions
         (id, name, entity_type, parent_id, status, purpose, authority_scope, metadata, created_at, updated_at)
       VALUES ($1,$2,'institution',NULL,'active',$3,$4::jsonb,$5::jsonb,NOW(),NOW())`,
      [
        institutionId,
        input.name,
        input.purpose ?? `${input.domain} institution`,
        JSON.stringify(authorityScope),
        JSON.stringify({
          actor_id: actor.id,
          domain: input.domain,
          ...(input.metadata ?? {}),
        }),
      ]
    );

    const departmentNames = ['Production', 'Verification', 'Audit', 'Adversarial', 'Improvement'];
    const departments: CanonicalDepartmentRecord[] = [];
    for (const name of departmentNames) {
      const departmentId = crypto.randomUUID();
      await db.query(
        `INSERT INTO departments
           (id, institution_id, name, entity_type, parent_id, status, purpose, authority_scope, metadata, created_at, updated_at)
         VALUES ($1,$2,$3,'department',$2,'active',$4,'[]'::jsonb,$5::jsonb,NOW(),NOW())`,
        [
          departmentId,
          institutionId,
          name,
          `${name} department`,
          JSON.stringify({ institution_actor_id: actor.id }),
        ]
      );
      departments.push({ id: departmentId, name });
    }

    return { institutionId, actorId: actor.id, departments };
  }

  /**
   * Generate institution name based on domain
   */
  private generateInstitutionName(domain: string): string {
    const names: Record<string, string> = {
      biology: '🧬 Institute of Molecular Biology',
      medicine: '🏥 Medical Research Academy',
      physics: '⚛️ Institute of Theoretical Physics',
      chemistry: '⚗️ Department of Chemical Sciences',
      neuroscience: '🧠 Center for Neuroscience Research',
      genetics: '🧪 Genetics & Evolution Laboratory',
      ecology: '🌿 Ecology & Conservation Institute',
      immunology: '🛡️ Immunology Research Center',
      oncology: '🎯 Oncology & Cancer Research',
      virology: '🦠 Virology & Disease Research',
    };

    return names[domain] || `Institute of ${domain.charAt(0).toUpperCase() + domain.slice(1)}`;
  }

  /**
   * Register a research paper
   */
  registerPaper(paper: ResearchPaper): void {
    this.paper_registry.set(paper.id, paper);
    console.log(`📄 Paper registered: "${paper.title}"`);
  }

  /**
   * Distribute paper to relevant institutions
   */
  distributePaper(paper: ResearchPaper): Map<string, { topics: number; expertise: number }> {
    const results = new Map<string, { topics: number; expertise: number }>();

    // Find matching institutions or create new ones
    let matched = false;

    for (const institution of this.institutions.values()) {
      if (
        institution.primary_domain === paper.domain ||
        this.isRelevant(institution, paper)
      ) {
        const result = institution.ingestPaper(paper);
        results.set(institution.id, {
          topics: result.learned_topics,
          expertise: result.expertise_gained,
        });
        matched = true;
      }
    }

    // If no match, create new institution for this domain
    if (!matched && !Array.from(this.institutions.values()).some((i) => i.primary_domain === paper.domain)) {
      const new_inst = this.createInstitution(paper.domain);
      const result = new_inst.ingestPaper(paper);
      results.set(new_inst.id, {
        topics: result.learned_topics,
        expertise: result.expertise_gained,
      });
    }

    return results;
  }

  /**
   * Check if paper is relevant to institution
   */
  private isRelevant(institution: Institution, paper: ResearchPaper): boolean {
    const keywords = paper.keywords || [];
    const knowledge_keys = Array.from(institution.knowledge_base.keys());

    const overlap = keywords.filter((k) => knowledge_keys.includes(k)).length;
    return overlap > 0;
  }

  /**
   * Ingest multiple papers into civilization
   */
  ingestPaperCollection(papers: ResearchPaper[]): {
    institutions_created: number;
    total_topics_learned: number;
    expertise_gained: number;
  } {
    console.log(`\n${'='.repeat(80)}`);
    console.log(`📚 INGESTING ${papers.length} RESEARCH PAPERS INTO CIVILIZATION`);
    console.log(`${'='.repeat(80)}\n`);

    let topics_total = 0;
    let expertise_total = 0;
    const institutions_before = this.institutions.size;

    for (const paper of papers) {
      this.registerPaper(paper);
      const results = this.distributePaper(paper);

      for (const [inst_id, result] of results) {
        topics_total += result.topics;
        expertise_total += result.expertise;
      }
    }

    const institutions_created = this.institutions.size - institutions_before;

    console.log(`\n${'='.repeat(80)}`);
    console.log(`📊 INGESTION COMPLETE`);
    console.log(`${'='.repeat(80)}`);
    console.log(`  Papers processed:      ${papers.length}`);
    console.log(`  Institutions created:  ${institutions_created}`);
    console.log(`  Total institutions:    ${this.institutions.size}`);
    console.log(`  Topics learned:        ${topics_total}`);
    console.log(`  Expertise gained:      ${expertise_total.toFixed(2)}\n`);

    return {
      institutions_created,
      total_topics_learned: topics_total,
      expertise_gained: expertise_total,
    };
  }

  /**
   * Get status of all institutions
   */
  getInstitutionStatus(): InstitutionMetrics[] {
    const statuses: InstitutionMetrics[] = [];

    for (const institution of this.institutions.values()) {
      statuses.push(institution.getMetrics());
    }

    return statuses.sort((a, b) => b.health_score - a.health_score);
  }

  /**
   * Query across all institutions for knowledge
   */
  queryAllInstitutions(topic: string): Array<{
    institution: string;
    known: boolean;
    confidence: number;
    related_topics: string[];
  }> {
    const results = [];

    for (const institution of this.institutions.values()) {
      const query = institution.queryKnowledge(topic);
      results.push({
        institution: institution.name,
        known: query.known,
        confidence: query.confidence,
        related_topics: query.related_topics,
      });
    }

    return results.sort((a, b) => b.confidence - a.confidence);
  }

  /**
   * Simulate feedback and let institutions evolve
   */
  simulateFeedbackCycle(iterations: number): void {
    console.log(`\n${'='.repeat(80)}`);
    console.log(`🔄 SIMULATING ${iterations} FEEDBACK CYCLES`);
    console.log(`${'='.repeat(80)}\n`);

    for (let i = 1; i <= iterations; i++) {
      console.log(`\nCycle ${i}/${iterations}:`);

      for (const institution of this.institutions.values()) {
        // Simulate feedback on random topics
        const topics = Array.from(institution.knowledge_base.keys());
        if (topics.length === 0) continue;

        for (let j = 0; j < Math.min(3, topics.length); j++) {
          const topic = topics[Math.floor(Math.random() * topics.length)];
          const was_correct = Math.random() > 0.2; // 80% correct
          const impact = Math.random() * 1.0;

          institution.recordFeedback(topic, was_correct, impact);
        }

        const metrics = institution.getMetrics();
        console.log(
          `  ${institution.name}: ` +
            `${metrics.evolution_stage} | ` +
            `Expertise: ${metrics.total_expertise.toFixed(2)} | ` +
            `Health: ${metrics.health_score.toFixed(2)}`,
        );
      }
    }

    console.log(`\n${'='.repeat(80)}`);
  }

  /**
   * Export full civilization state
   */
  exportCivilizationState(): {
    institutions: InstitutionMetrics[];
    total_knowledge_entries: number;
    average_health: number;
    domains_covered: string[];
  } {
    const statuses = this.getInstitutionStatus();
    const total_knowledge = statuses.reduce((sum, s) => sum + s.knowledge_entries, 0);
    const avg_health = statuses.reduce((sum, s) => sum + s.health_score, 0) / statuses.length;
    const domains = Array.from(new Set(statuses.map((s) => s.domain)));

    return {
      institutions: statuses,
      total_knowledge_entries: total_knowledge,
      average_health: avg_health,
      domains_covered: domains,
    };
  }
}

export const institutionsService = new InstitutionsService();
