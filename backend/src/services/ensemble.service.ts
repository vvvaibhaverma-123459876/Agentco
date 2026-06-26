/**
 * Ensemble Voting Service - Phase 2
 * Multi-model orchestration with semantic disagreement detection
 *
 * Research: Zhou et al. (2012) - Ensemble diversity
 *           Kuhn et al. (2023) - Semantic uncertainty
 */

interface ModelAnswer {
  model: string;
  answer: string;
  confidence: number;
  reasoning: string;
}

interface EnsembleResult {
  final_answer: string;
  confidence: number;
  abstention: boolean;
  disagreement_level: number;
  model_votes: ModelAnswer[];
  reasoning: string;
}

export class EnsembleService {
  async queryModels(question: string): Promise<ModelAnswer[]> {
    const personas = [
      {
        model: 'general_reasoning',
        system: 'You are a careful general reasoning model. Answer concisely and calibrate confidence.',
      },
      {
        model: 'specialized_reasoning',
        system: 'You are a domain specialist. Focus on technical correctness, caveats, and uncertainty.',
      },
      {
        model: 'knowledge_grounded',
        system: 'You are an evidence-grounded reviewer. Avoid unsupported claims and flag uncertainty.',
      },
    ];

    return Promise.all(personas.map((persona) => this.callLLM(persona.model, persona.system, question)));
  }

  async ensembleVote(question: string): Promise<EnsembleResult> {
    const modelAnswers = await this.queryModels(question);
    const disagreementLevel = this.detectSemanticDisagreement(modelAnswers);
    const shouldAbstain = disagreementLevel > 0.5;

    if (shouldAbstain) {
      return {
        final_answer: 'UNCERTAIN',
        confidence: Math.max(...modelAnswers.map(m => m.confidence)) * 0.5,
        abstention: true,
        disagreement_level: disagreementLevel,
        model_votes: modelAnswers,
        reasoning: `High model disagreement (${(disagreementLevel * 100).toFixed(1)}%). System uncertain.`,
      };
    }

    const votedAnswer = this.weightedVoting(modelAnswers);

    return {
      final_answer: votedAnswer.answer,
      confidence: votedAnswer.confidence,
      abstention: false,
      disagreement_level: disagreementLevel,
      model_votes: modelAnswers,
      reasoning: `Ensemble consensus from ${modelAnswers.length} models. Disagreement: ${(disagreementLevel * 100).toFixed(1)}%`,
    };
  }

  private detectSemanticDisagreement(answers: ModelAnswer[]): number {
    if (answers.length < 2) return 0;

    const answersNormalized = answers.map(a => a.answer.toLowerCase().trim());
    let totalDissimilarity = 0;
    let comparisons = 0;

    for (let i = 0; i < answersNormalized.length; i++) {
      for (let j = i + 1; j < answersNormalized.length; j++) {
        const similarity = this.stringSimilarity(answersNormalized[i], answersNormalized[j]);
        totalDissimilarity += 1 - similarity;
        comparisons++;
      }
    }

    const avgDissimilarity = totalDissimilarity / comparisons;
    return Math.min(1, avgDissimilarity);
  }

  private weightedVoting(answers: ModelAnswer[]): { answer: string; confidence: number } {
    const answerGroups = this.groupSimilarAnswers(answers);

    const votedAnswers = answerGroups.map(group => ({
      answer: group.answer,
      weight: group.answers.reduce((sum, a) => sum + a.confidence, 0) / group.answers.length,
      confidence: group.answers[0].confidence,
      count: group.answers.length,
    }));

    votedAnswers.sort((a, b) => b.weight - a.weight);
    const winner = votedAnswers[0];
    const confidenceBoost = Math.min(0.95, winner.weight + 0.1);

    return {
      answer: winner.answer,
      confidence: confidenceBoost,
    };
  }

  private groupSimilarAnswers(
    answers: ModelAnswer[],
  ): Array<{ answer: string; answers: ModelAnswer[] }> {
    const groups: { [key: string]: ModelAnswer[] } = {};

    for (const answer of answers) {
      const normalized = answer.answer.toLowerCase().trim();
      let foundGroup = false;

      for (const [groupKey, groupAnswers] of Object.entries(groups)) {
        const similarity = this.stringSimilarity(normalized, groupKey);
        if (similarity > 0.7) {
          groupAnswers.push(answer);
          foundGroup = true;
          break;
        }
      }

      if (!foundGroup) {
        groups[normalized] = [answer];
      }
    }

    return Object.entries(groups).map(([answer, answers]) => ({ answer, answers }));
  }

  private stringSimilarity(a: string, b: string): number {
    const maxLen = Math.max(a.length, b.length);
    if (maxLen === 0) return 1;
    const distance = this.levenshteinDistance(a, b);
    return 1 - distance / maxLen;
  }

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

  private async callLLM(modelLabel: string, systemPrompt: string, question: string): Promise<ModelAnswer> {
    const apiKey = process.env.LLM_API_KEY || process.env.OPENAI_API_KEY;
    if (!apiKey) {
      throw new Error('LLM_API_KEY or OPENAI_API_KEY is required for ensemble voting');
    }

    const baseUrl = process.env.LLM_BASE_URL || 'https://api.openai.com/v1';
    const model = process.env.LLM_MODEL_DEFAULT || 'gpt-4o-mini';
    const response = await fetch(`${baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model,
        temperature: 0.1,
        response_format: { type: 'json_object' },
        messages: [
          { role: 'system', content: `${systemPrompt} Return JSON with keys answer, confidence, and reasoning. Confidence must be 0 to 1.` },
          { role: 'user', content: question },
        ],
      }),
    });

    if (!response.ok) {
      throw new Error(`LLM ensemble call failed for ${modelLabel}: HTTP ${response.status}`);
    }

    const payload = await response.json() as { choices?: Array<{ message?: { content?: string } }> };
    const content = payload.choices?.[0]?.message?.content;
    if (!content) {
      throw new Error(`LLM ensemble call returned empty content for ${modelLabel}`);
    }

    const parsed = JSON.parse(content) as { answer?: string; confidence?: number; reasoning?: string };
    if (!parsed.answer || typeof parsed.confidence !== 'number') {
      throw new Error(`LLM ensemble call returned invalid JSON for ${modelLabel}`);
    }

    return {
      model: modelLabel,
      answer: parsed.answer,
      confidence: Math.max(0, Math.min(1, parsed.confidence)),
      reasoning: parsed.reasoning || `${modelLabel} returned a calibrated answer`,
    };
  }
}

export const ensembleService = new EnsembleService();
