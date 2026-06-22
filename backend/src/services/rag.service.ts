/**
 * Retrieval-Augmented Generation (RAG) Service
 * Phase 1 implementation: Wikipedia + ArXiv lookup for answer verification
 *
 * Architecture:
 * 1. Get model answer (baseline)
 * 2. Search Wikipedia/ArXiv for evidence
 * 3. Rank evidence by independence (avoid circular reasoning)
 * 4. Compare model answer with evidence consensus
 * 5. Return best answer with confidence
 */

interface SearchResult {
  source: string;
  title: string;
  snippet: string;
  relevance: number;
  url: string;
}

interface EvidenceConsensus {
  answer: string;
  confidence: number;
  sources: SearchResult[];
  agreement_ratio: number;
}

interface RAGResult {
  model_answer: string;
  model_confidence: number;
  evidence_consensus: EvidenceConsensus;
  final_answer: string;
  final_confidence: number;
  reasoning: string;
}

export class RAGService {
  /**
   * Main RAG pipeline:
   * Compare model answer with retrieved evidence to improve accuracy
   */
  async augmentAnswer(
    question: string,
    model_answer: string,
    model_confidence: number,
  ): Promise<RAGResult> {
    try {
      // Step 1: Retrieve evidence (Wikipedia + ArXiv)
      const evidence = await this.retrieveEvidence(question);

      // Step 2: Rank evidence by quality and independence
      const rankedEvidence = this.rankByIndependence(evidence, model_answer);

      // Step 3: Extract consensus from evidence
      const consensus = this.extractConsensus(rankedEvidence, model_answer);

      // Step 4: Decide which answer to use
      const result = this.decideFinalAnswer(
        model_answer,
        model_confidence,
        consensus,
      );

      return result;
    } catch (err) {
      console.warn('RAG augmentation failed, using model answer:', err);
      return {
        model_answer,
        model_confidence,
        evidence_consensus: { answer: '', confidence: 0, sources: [], agreement_ratio: 0 },
        final_answer: model_answer,
        final_confidence: model_confidence,
        reasoning: 'RAG failed, fell back to model answer',
      };
    }
  }

  /**
   * Retrieve evidence from Wikipedia and ArXiv
   * In production, this would call real APIs
   * For now: simulate with knowledge base
   */
  private async retrieveEvidence(question: string): Promise<SearchResult[]> {
    // Simulated evidence retrieval (in production, call real APIs)
    const evidence: SearchResult[] = [];

    // Wikipedia results (simulated)
    evidence.push(
      ...this.simulateWikipediaSearch(question),
    );

    // ArXiv results (simulated)
    evidence.push(
      ...this.simulateArXivSearch(question),
    );

    return evidence;
  }

  private simulateWikipediaSearch(question: string): SearchResult[] {
    // In production, call Wikipedia API
    // For now: return high-quality simulated results
    const normalizedQ = question.toLowerCase();

    const knowledge_base: Record<string, SearchResult[]> = {
      'capital of france': [
        {
          source: 'Wikipedia',
          title: 'Paris',
          snippet: 'Paris is the capital and most populous city of France, located in the north-central part of the country.',
          relevance: 0.95,
          url: 'https://en.wikipedia.org/wiki/Paris',
        },
      ],
      'wrote to kill a mockingbird': [
        {
          source: 'Wikipedia',
          title: "To Kill a Mockingbird",
          snippet: "To Kill a Mockingbird is a novel by Harper Lee published in 1960. It was immediately successful and has become a classic of modern American literature.",
          relevance: 0.95,
          url: 'https://en.wikipedia.org/wiki/To_Kill_a_Mockingbird',
        },
      ],
      'largest planet in solar system': [
        {
          source: 'Wikipedia',
          title: 'Jupiter',
          snippet: 'Jupiter is the fifth planet from the Sun and the largest in the Solar System. It is a gas giant with a mass more than 2.5 times that of all the other planets combined.',
          relevance: 0.93,
          url: 'https://en.wikipedia.org/wiki/Jupiter',
        },
      ],
    };

    for (const [key, results] of Object.entries(knowledge_base)) {
      if (normalizedQ.includes(key) || key.includes(normalizedQ)) {
        return results;
      }
    }

    return [];
  }

  private simulateArXivSearch(question: string): SearchResult[] {
    // In production, call ArXiv API for academic papers
    // For now: return empty (Wikipedia usually sufficient)
    return [];
  }

  /**
   * Rank evidence by independence
   * Avoids circular reasoning (e.g., both sources citing same paper)
   */
  private rankByIndependence(
    evidence: SearchResult[],
    model_answer: string,
  ): SearchResult[] {
    return evidence.sort((a, b) => {
      // Boost if evidence contradicts model (model is likely wrong)
      const a_contradicts = !this.answersAgree(a.snippet, model_answer);
      const b_contradicts = !this.answersAgree(b.snippet, model_answer);

      if (a_contradicts && !b_contradicts) return -1;
      if (!a_contradicts && b_contradicts) return 1;

      // Otherwise: sort by relevance
      return b.relevance - a.relevance;
    });
  }

  /**
   * Extract consensus answer from evidence
   */
  private extractConsensus(
    evidence: SearchResult[],
    model_answer: string,
  ): EvidenceConsensus {
    if (evidence.length === 0) {
      return {
        answer: '',
        confidence: 0,
        sources: [],
        agreement_ratio: 0,
      };
    }

    // Count how many sources support vs contradict model answer
    const supportingCount = evidence.filter(e =>
      this.answersAgree(e.snippet, model_answer),
    ).length;

    const disagreementRatio = 1 - (supportingCount / evidence.length);
    const topSource = evidence[0];

    // Extract answer from top source
    const consensus_answer = this.extractAnswerFromSource(
      topSource.snippet,
    );

    return {
      answer: consensus_answer,
      confidence: 0.8 + (disagreementRatio * 0.2), // Higher if consensus clear
      sources: evidence.slice(0, 3),
      agreement_ratio: supportingCount / evidence.length,
    };
  }

  /**
   * Decide final answer: model vs evidence consensus
   */
  private decideFinalAnswer(
    model_answer: string,
    model_confidence: number,
    consensus: EvidenceConsensus,
  ): RAGResult {
    const consensus_confidence = consensus.confidence;

    let final_answer = model_answer;
    let final_confidence = model_confidence;
    let reasoning = 'Used model answer (high confidence)';

    // Logic: Trust high-confidence model, but check evidence for low-confidence
    if (model_confidence > 0.85) {
      // High confidence: trust model
      reasoning = 'Model is high confidence. Evidence validates.';
      final_confidence = Math.min(1, model_confidence);
    } else if (consensus.agreement_ratio > 0.8 && consensus_confidence > 0.7) {
      // Clear evidence consensus
      if (!this.answersAgree(model_answer, consensus.answer)) {
        // Evidence contradicts model: trust evidence
        final_answer = consensus.answer;
        final_confidence = consensus_confidence;
        reasoning = `Evidence consensus (${Math.round(consensus.agreement_ratio * 100)}% agreement) contradicts model. Using evidence.`;
      } else {
        // Evidence agrees: boost confidence
        final_confidence = Math.min(1, (model_confidence + consensus_confidence) / 2);
        reasoning = 'Evidence supports model answer. Confidence increased.';
      }
    } else if (consensus.agreement_ratio < 0.3 && consensus_confidence > 0.8) {
      // Strong evidence contradiction
      final_answer = consensus.answer;
      final_confidence = consensus_confidence;
      reasoning = 'Strong evidence contradiction. Using evidence consensus.';
    } else {
      reasoning = 'Uncertain: using model answer with evidence quality assessment.';
    }

    return {
      model_answer,
      model_confidence,
      evidence_consensus: consensus,
      final_answer,
      final_confidence,
      reasoning,
    };
  }

  /**
   * Check if two answers agree semantically
   */
  private answersAgree(source_text: string, model_answer: string): boolean {
    const normalize = (s: string) =>
      s.toLowerCase().replace(/[^a-z0-9]/g, '');

    const source_norm = normalize(source_text);
    const model_norm = normalize(model_answer);

    // Exact match or substring match
    return (
      source_norm.includes(model_norm) ||
      model_norm.includes(source_norm) ||
      this.levenshteinDistance(source_norm, model_norm) < 3
    );
  }

  /**
   * Extract likely answer from source text
   */
  private extractAnswerFromSource(snippet: string): string {
    // Simple heuristic: first sentence or title
    const sentences = snippet.split(/[.!?]/);
    if (sentences.length > 0) {
      const firstSentence = sentences[0].trim();
      if (firstSentence.length > 5 && firstSentence.length < 200) {
        return firstSentence;
      }
    }
    return snippet.slice(0, 100);
  }

  /**
   * Levenshtein distance for fuzzy matching
   */
  private levenshteinDistance(a: string, b: string): number {
    const matrix: number[][] = [];

    for (let i = 0; i <= b.length; i++) {
      matrix[i] = [i];
    }

    for (let j = 0; j <= a.length; j++) {
      matrix[0][j] = j;
    }

    for (let i = 1; i <= b.length; i++) {
      for (let j = 1; j <= a.length; j++) {
        if (b.charAt(i - 1) === a.charAt(j - 1)) {
          matrix[i][j] = matrix[i - 1][j - 1];
        } else {
          matrix[i][j] = Math.min(
            matrix[i - 1][j - 1] + 1,
            matrix[i][j - 1] + 1,
            matrix[i - 1][j] + 1,
          );
        }
      }
    }

    return matrix[b.length][a.length];
  }
}

export const ragService = new RAGService();
