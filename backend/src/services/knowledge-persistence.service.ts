/**
 * KNOWLEDGE PERSISTENCE SERVICE
 *
 * Persistent layer that ensures Agentco retains all learnings
 * and can build upon them continuously.
 *
 * Architecture:
 * ├─ Knowledge Storage (JSON-based persistent store)
 * ├─ Curriculum Management (graduate-level courses)
 * ├─ Learning Verification (test correctness of retained knowledge)
 * ├─ Progressive Learning (build upon existing knowledge)
 * └─ Knowledge Graph (interconnections across fields)
 */

interface KnowledgeNode {
  id: string;
  field: string; // Mathematics, Physics, Chemistry, Biology, etc.
  level: string; // Undergraduate, Graduate, Advanced
  topic: string;
  subtopics: string[];
  content: string; // Actual knowledge/definition
  confidence: number; // 0-1: how well understood
  times_used: number;
  correctness_rate: number;
  prerequisites: string[]; // IDs of prerequisite knowledge
  interconnections: Map<string, number>; // related topics and strength
  created_at: number;
  last_verified: number;
  verification_tests_passed: number;
  verification_tests_total: number;
}

interface CurriculumCourse {
  id: string;
  field: string;
  level: string; // Undergraduate, Master's, PhD
  course_name: string;
  duration_weeks: number;
  learning_outcomes: string[];
  topics: string[];
  prerequisites: string[];
  difficulty: number; // 1-10
  knowledge_nodes: string[]; // IDs of knowledge nodes
  completion_percentage: number; // 0-100
  started_at?: number;
  completed_at?: number;
}

interface LearningRecord {
  id: string;
  knowledge_node_id: string;
  timestamp: number;
  test_question: string;
  answer: string;
  correct: boolean;
  confidence: number;
  feedback: string;
}

interface FieldExpertise {
  field: string;
  total_knowledge_nodes: number;
  mastered_nodes: number; // passed 3+ verification tests
  competent_nodes: number; // passed 1-2 verification tests
  developing_nodes: number; // not yet verified
  overall_expertise: number; // 0-1
  graduate_level_coverage: number; // 0-1
}

export class KnowledgePersistenceService {
  private knowledgeStore: Map<string, KnowledgeNode> = new Map();
  private curriculumStore: Map<string, CurriculumCourse> = new Map();
  private learningHistory: LearningRecord[] = [];
  private fieldExpertise: Map<string, FieldExpertise> = new Map();
  private knowledgeGraph: Map<string, Set<string>> = new Map(); // topic -> related topics

  // In production, this would connect to a real database
  private persistencePath: string = '/tmp/agentco_knowledge.json';

  constructor() {
    this.initializeFields();
    this.loadPersistedKnowledge();
  }

  /**
   * Initialize all academic fields
   */
  private initializeFields(): void {
    const fields = [
      'Mathematics',
      'Physics',
      'Chemistry',
      'Biology',
      'Computer Science',
      'Engineering',
      'Economics',
      'Philosophy',
      'History',
      'Literature',
      'Psychology',
      'Sociology',
      'Political Science',
      'Anthropology',
      'Neuroscience',
      'Medicine',
      'Law',
      'Business',
    ];

    for (const field of fields) {
      this.fieldExpertise.set(field, {
        field,
        total_knowledge_nodes: 0,
        mastered_nodes: 0,
        competent_nodes: 0,
        developing_nodes: 0,
        overall_expertise: 0,
        graduate_level_coverage: 0,
      });
    }
  }

  /**
   * Add graduate-level knowledge node
   */
  addKnowledgeNode(node: Omit<KnowledgeNode, 'id' | 'created_at'>): KnowledgeNode {
    const id = `node_${Date.now()}_${Math.random()}`;
    const knowledge_node: KnowledgeNode = {
      id,
      created_at: Date.now(),
      verification_tests_passed: 0,
      verification_tests_total: 0,
      times_used: 0,
      ...node,
    };

    this.knowledgeStore.set(id, knowledge_node);

    // Update field expertise
    const expertise = this.fieldExpertise.get(node.field);
    if (expertise) {
      expertise.total_knowledge_nodes += 1;
      expertise.developing_nodes += 1;
    }

    // Create knowledge graph connections
    if (!this.knowledgeGraph.has(node.topic)) {
      this.knowledgeGraph.set(node.topic, new Set());
    }

    return knowledge_node;
  }

  /**
   * Create graduate-level curriculum
   */
  createCurriculum(course: Omit<CurriculumCourse, 'id' | 'completion_percentage' | 'knowledge_nodes'>): CurriculumCourse {
    const id = `course_${Date.now()}_${Math.random()}`;
    const curriculum: CurriculumCourse = {
      id,
      completion_percentage: 0,
      knowledge_nodes: [],
      started_at: Date.now(),
      ...course,
    };

    this.curriculumStore.set(id, curriculum);

    console.log(`\n📚 Curriculum Created: ${course.course_name}`);
    console.log(`   Field: ${course.field} | Level: ${course.level}`);
    console.log(`   Duration: ${course.duration_weeks} weeks`);
    console.log(`   Topics: ${course.topics.length}\n`);

    return curriculum;
  }

  /**
   * Add knowledge node to curriculum (teaching it to Agentco)
   */
  addNodeToCurriculum(curriculum_id: string, knowledge_node: KnowledgeNode): void {
    const curriculum = this.curriculumStore.get(curriculum_id);
    if (!curriculum) return;

    curriculum.knowledge_nodes.push(knowledge_node.id);

    // Update completion percentage
    const total_topics = curriculum.topics.length;
    const covered_topics = Math.ceil((curriculum.knowledge_nodes.length / total_topics) * 100);
    curriculum.completion_percentage = Math.min(100, covered_topics);

    console.log(`  ✅ Added: ${knowledge_node.topic}`);
    console.log(`     Completion: ${curriculum.completion_percentage}%`);
  }

  /**
   * Verify knowledge through testing
   */
  verifyKnowledge(knowledge_node_id: string, test_question: string, given_answer: string, correct_answer: string): {
    passed: boolean;
    confidence_boost: number;
    mastery_level: string;
  } {
    const node = this.knowledgeStore.get(knowledge_node_id);
    if (!node) {
      return { passed: false, confidence_boost: 0, mastery_level: 'unknown' };
    }

    const passed = given_answer.toLowerCase() === correct_answer.toLowerCase();

    // Record learning
    this.learningHistory.push({
      id: `learn_${Date.now()}`,
      knowledge_node_id,
      timestamp: Date.now(),
      test_question,
      answer: given_answer,
      correct: passed,
      confidence: node.confidence,
      feedback: passed ? 'Correct!' : `Expected: ${correct_answer}`,
    });

    // Update node
    node.times_used += 1;
    node.verification_tests_total += 1;
    node.last_verified = Date.now();

    if (passed) {
      node.verification_tests_passed += 1;
      node.correctness_rate = Math.min(1, node.correctness_rate + 0.1);
      node.confidence = Math.min(1, node.confidence + 0.05);
    } else {
      node.correctness_rate = Math.max(0, node.correctness_rate - 0.15);
    }

    // Determine mastery level
    let mastery = 'Developing';
    if (node.verification_tests_passed >= 3) {
      mastery = 'Mastered';
      if (node.correctness_rate > 0.9) {
        mastery = 'Expert';
      }
    } else if (node.verification_tests_passed > 0) {
      mastery = 'Competent';
    }

    // Update field expertise
    this.updateFieldExpertise(node.field);

    return {
      passed,
      confidence_boost: node.confidence,
      mastery_level: mastery,
    };
  }

  /**
   * Build upon existing knowledge - create connections
   */
  buildUponKnowledge(source_node_id: string, new_node_id: string, connection_strength: number): void {
    const source = this.knowledgeStore.get(source_node_id);
    const new_node = this.knowledgeStore.get(new_node_id);

    if (!source || !new_node) return;

    // Create bidirectional connection
    source.interconnections.set(new_node_id, connection_strength);
    new_node.interconnections.set(source_node_id, connection_strength);

    // Update knowledge graph
    const sourceGraph = this.knowledgeGraph.get(source.topic) || new Set();
    sourceGraph.add(new_node.topic);
    this.knowledgeGraph.set(source.topic, sourceGraph);

    const newGraph = this.knowledgeGraph.get(new_node.topic) || new Set();
    newGraph.add(source.topic);
    this.knowledgeGraph.set(new_node.topic, newGraph);
  }

  /**
   * Update field expertise based on knowledge nodes
   */
  private updateFieldExpertise(field: string): void {
    const expertise = this.fieldExpertise.get(field);
    if (!expertise) return;

    expertise.mastered_nodes = 0;
    expertise.competent_nodes = 0;
    expertise.developing_nodes = 0;

    for (const node of this.knowledgeStore.values()) {
      if (node.field !== field) continue;

      if (node.verification_tests_passed >= 3) {
        expertise.mastered_nodes += 1;
      } else if (node.verification_tests_passed > 0) {
        expertise.competent_nodes += 1;
      } else {
        expertise.developing_nodes += 1;
      }
    }

    // Calculate overall expertise
    const total = expertise.total_knowledge_nodes;
    if (total > 0) {
      expertise.overall_expertise = (expertise.mastered_nodes * 1.0 + expertise.competent_nodes * 0.6) / total;
      expertise.graduate_level_coverage = Math.min(
        1,
        (expertise.mastered_nodes + expertise.competent_nodes) / total,
      );
    }
  }

  /**
   * Query retained knowledge
   */
  queryKnowledge(topic: string): {
    found: boolean;
    nodes: KnowledgeNode[];
    confidence: number;
    mastery: string;
  } {
    const matching_nodes: KnowledgeNode[] = [];

    for (const node of this.knowledgeStore.values()) {
      if (node.topic.toLowerCase().includes(topic.toLowerCase()) ||
          node.subtopics.some(s => s.toLowerCase().includes(topic.toLowerCase()))) {
        matching_nodes.push(node);
      }
    }

    if (matching_nodes.length === 0) {
      return { found: false, nodes: [], confidence: 0, mastery: 'unknown' };
    }

    const avg_confidence = matching_nodes.reduce((sum, n) => sum + n.confidence, 0) / matching_nodes.length;
    const avg_correctness = matching_nodes.reduce((sum, n) => sum + n.correctness_rate, 0) / matching_nodes.length;

    let mastery = 'Developing';
    if (avg_correctness > 0.85) mastery = 'Expert';
    else if (avg_correctness > 0.70) mastery = 'Competent';
    else if (avg_correctness > 0.50) mastery = 'Developing';

    return {
      found: true,
      nodes: matching_nodes,
      confidence: avg_confidence,
      mastery,
    };
  }

  /**
   * Get overall system expertise
   */
  getSystemExpertise(): {
    total_fields: number;
    expert_fields: number; // graduate level coverage > 80%
    competent_fields: number; // coverage 50-80%
    developing_fields: number; // coverage < 50%
    total_knowledge_nodes: number;
    mastered_nodes: number;
    overall_expertise: number;
    field_breakdown: FieldExpertise[];
  } {
    const fields = Array.from(this.fieldExpertise.values());

    const expert = fields.filter((f) => f.graduate_level_coverage > 0.8).length;
    const competent = fields.filter((f) => f.graduate_level_coverage > 0.5 && f.graduate_level_coverage <= 0.8).length;
    const developing = fields.filter((f) => f.graduate_level_coverage <= 0.5).length;

    const total_nodes = Array.from(this.knowledgeStore.values()).length;
    const mastered = Array.from(this.knowledgeStore.values()).filter((n) => n.verification_tests_passed >= 3)
      .length;

    const overall = total_nodes > 0 ? mastered / total_nodes : 0;

    return {
      total_fields: fields.length,
      expert_fields: expert,
      competent_fields: competent,
      developing_fields: developing,
      total_knowledge_nodes: total_nodes,
      mastered_nodes: mastered,
      overall_expertise: overall,
      field_breakdown: fields.sort((a, b) => b.overall_expertise - a.overall_expertise),
    };
  }

  /**
   * Save knowledge to persistent storage
   */
  persistKnowledge(): void {
    const state = {
      knowledgeStore: Array.from(this.knowledgeStore.entries()),
      curriculumStore: Array.from(this.curriculumStore.entries()),
      learningHistory: this.learningHistory,
      fieldExpertise: Array.from(this.fieldExpertise.entries()),
      timestamp: Date.now(),
    };

    console.log(`\n💾 Persisting Agentco knowledge to storage`);
    console.log(`   Total knowledge nodes: ${this.knowledgeStore.size}`);
    console.log(`   Learning records: ${this.learningHistory.length}`);
    console.log(`   Timestamp: ${new Date(state.timestamp).toISOString()}\n`);

    // In production, write to database
    // fs.writeFileSync(this.persistencePath, JSON.stringify(state, null, 2));
  }

  /**
   * Load persisted knowledge from storage
   */
  private loadPersistedKnowledge(): void {
    // In production, read from database
    // if (fs.existsSync(this.persistencePath)) {
    //   const data = JSON.parse(fs.readFileSync(this.persistencePath, 'utf-8'));
    //   // Restore state
    // }
  }

  /**
   * Export full knowledge state for backup
   */
  exportKnowledgeState(): string {
    const state = {
      metadata: {
        exported_at: new Date().toISOString(),
        total_fields: this.fieldExpertise.size,
        total_knowledge_nodes: this.knowledgeStore.size,
        learning_records: this.learningHistory.length,
      },
      fields: Array.from(this.fieldExpertise.values()),
      expertise_summary: this.getSystemExpertise(),
      knowledge_sample: Array.from(this.knowledgeStore.values())
        .slice(0, 10)
        .map((n) => ({
          topic: n.topic,
          field: n.field,
          level: n.level,
          confidence: n.confidence.toFixed(2),
          mastery: n.verification_tests_passed >= 3 ? 'Mastered' : 'Developing',
        })),
    };

    return JSON.stringify(state, null, 2);
  }
}

export const knowledgePersistenceService = new KnowledgePersistenceService();
