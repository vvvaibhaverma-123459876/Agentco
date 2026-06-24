import { describe, it, expect, beforeEach } from '@jest/globals';
import { v4 as uuidv4 } from 'uuid';

// Mock evidence store (in-memory for unit testing)
interface MockEvidence {
  sourceId: string;
  url: string;
  snippet: string;
}

describe('Claim Grounding Validation — Foundation Step 1', () => {
  let mockEvidenceStore: Map<string, MockEvidence>;

  beforeEach(() => {
    // Clear mock store before each test
    mockEvidenceStore = new Map();
  });

  describe('Named-Concept Verification', () => {
    it('REJECTS fake theorem: "the Verma Conjecture" when not in source', () => {
      // Setup: Create a source about prime numbers that does NOT mention "Verma Conjecture"
      const sourceId = uuidv4();
      const abstractText = `
        This paper investigates fundamental properties of prime numbers and their applications
        in cryptography. We study the Goldbach conjecture and its variants, proving new bounds
        on prime gaps. The work builds on classical theorems by Euclid, Fermat, and Riemann.
        Recent computational evidence supports our theoretical framework.
      `;

      mockEvidenceStore.set(sourceId, {
        sourceId,
        url: `https://arxiv.org/abs/1003.4015`,
        snippet: abstractText
      });

      // Attempt: Plant a fake theorem claim
      const fakeClaimText = `The Verma Conjecture for prime numbers establishes a novel relationship between
        prime gaps and modular arithmetic, recently discovered in the field of analytic number theory.`;

      // Validation call (simulating action executor)
      const validation = validateClaimGroundingTest(fakeClaimText, [sourceId], mockEvidenceStore);

      // Assert: MUST be rejected because "Verma Conjecture" is not in abstract
      expect(validation.valid).toBe(false);
      expect(validation.reason).toMatch(/Verma Conjecture|not found in sources/i);
      console.log(`✅ CORRECTLY REJECTED fake theorem: "${validation.reason}"`);
    });

    it('REJECTS "the Fibonacci Theorem" when Fibonacci not in sources', () => {
      const sourceId = uuidv4();
      const abstractText = `
        Analysis of properties of prime numbers. We examine the distribution of primes
        using sieve methods and probabilistic techniques. Classical results by Chebyshev
        are extended with modern computational methods.
      `;

      mockEvidenceStore.set(sourceId, {
        sourceId,
        url: `https://arxiv.org/abs/paper2`,
        snippet: abstractText
      });

      const fakeClaimText = `The Fibonacci Theorem describes a fundamental property of prime number sequences,
        extending classical number-theoretic results to new domains.`;

      const validation = validateClaimGroundingTest(fakeClaimText, [sourceId], mockEvidenceStore);

      expect(validation.valid).toBe(false);
      expect(validation.reason).toMatch(/Fibonacci|not found/i);
      console.log(`✅ CORRECTLY REJECTED: "${validation.reason}"`);
    });
  });

  describe('Term-Overlap Verification', () => {
    it('REJECTS generic claims with <30% term overlap', () => {
      const sourceId = uuidv4();
      const abstractText = `
        Prime number distribution. Sieve methods. Riemann hypothesis. Chebyshev bounds.
        Computational verification of twin prime conjecture. Classical analysis of primes.
      `;

      mockEvidenceStore.set(sourceId, {
        sourceId,
        url: `https://arxiv.org/abs/paper3`,
        snippet: abstractText
      });

      // Claim with unrelated terms (AI, machine learning, neural networks)
      const genericClaimText = `Artificial intelligence applications in quantum computing. Neural networks enable
        machine learning frameworks. Deep learning models provide pattern recognition. Autonomous systems benefit
        from reinforcement learning techniques.`;

      const validation = validateClaimGroundingTest(genericClaimText, [sourceId], mockEvidenceStore);

      expect(validation.valid).toBe(false);
      expect(validation.reason).toMatch(/terms found/i);
      console.log(`✅ CORRECTLY REJECTED generic claim: "${validation.reason}"`);
    });
  });

  describe('Real-Claim Acceptance', () => {
    it('ACCEPTS legitimate claim about Goldbach conjecture', () => {
      const sourceId = uuidv4();
      const abstractText = `
        We investigate the Goldbach conjecture and related conjectures about prime sums.
        The paper presents new computational evidence for twin prime conjecture and proves
        bounds on prime gaps. Methods build on Euclid's infinitude of primes and Riemann zeta function analysis.
        We validate theorems by Chebyshev and Hardy-Littlewood on prime distribution.
      `;

      mockEvidenceStore.set(sourceId, {
        sourceId,
        url: `https://arxiv.org/abs/1003.4015`,
        snippet: abstractText
      });

      // Real claim grounded in the abstract
      const realClaimText = `The Goldbach conjecture states that every even integer greater than two can be
        expressed as the sum of two primes. This paper extends classical results with computational evidence
        and new bounds on prime gaps.`;

      const validation = validateClaimGroundingTest(realClaimText, [sourceId], mockEvidenceStore);

      expect(validation.valid).toBe(true);
      console.log(`✅ CORRECTLY ACCEPTED real claim about Goldbach conjecture`);
    });

    it('ACCEPTS claim with multiple verified concepts', () => {
      const sourceId = uuidv4();
      const abstractText = `
        The Riemann hypothesis and its implications for prime distribution. Hardy-Littlewood conjecture
        on prime tuples. Chebyshev bounds on prime gaps. We present computational verification using
        classical methods from analytic number theory. The paper extends work on the Dirichlet theorem
        for arithmetic progressions.
      `;

      mockEvidenceStore.set(sourceId, {
        sourceId,
        url: `https://arxiv.org/abs/1306.0795`,
        snippet: abstractText
      });

      // Claim with multiple verified concepts
      const realClaimText = `The Hardy-Littlewood conjecture extends the Riemann hypothesis to prime tuples.
        Combined with Chebyshev bounds, this provides new insight into the distribution of primes
        in arithmetic progressions, as established by the Dirichlet theorem.`;

      const validation = validateClaimGroundingTest(realClaimText, [sourceId], mockEvidenceStore);

      expect(validation.valid).toBe(true);
      console.log(`✅ CORRECTLY ACCEPTED multi-concept claim`);
    });
  });

  describe('Reproducibility Tests', () => {
    it('Consistently rejects "the Verma Conjecture" across different sources (RUN 1)', () => {
      // Run 1: Different source about cryptography
      const sourceId = uuidv4();
      const abstractText = `
        Cryptographic applications of number theory. RSA security depends on prime factorization difficulty.
        Elliptic curve cryptography uses algebraic geometry. Discrete logarithm problem foundations.
      `;

      mockEvidenceStore.set(sourceId, {
        sourceId,
        url: `https://arxiv.org/abs/1810.02188`,
        snippet: abstractText
      });

      const fakeClaimText = `The Verma Conjecture provides theoretical foundations for cryptographic protocols
        by establishing bounds on modular exponentiation sequences.`;

      const validation = validateClaimGroundingTest(fakeClaimText, [sourceId], mockEvidenceStore);

      expect(validation.valid).toBe(false);
      console.log(`✅ RUN 1: REJECTED Verma Conjecture claim`);
    });

    it('Consistently rejects "the Verma Conjecture" across different sources (RUN 2)', () => {
      // Run 2: Different source about group theory
      const sourceId = uuidv4();
      const abstractText = `
        Group theory and its applications in algebraic structures. Galois theory principles.
        Field extensions and polynomial equations. Fundamental theorem of Galois theory with applications
        to unsolvability of the quintic. Symmetry groups in physics and chemistry.
      `;

      mockEvidenceStore.set(sourceId, {
        sourceId,
        url: `https://arxiv.org/abs/alg_geometry`,
        snippet: abstractText
      });

      const fakeClaimText = `Recent work on the Verma Conjecture in group theory extends Galois theory
        to new algebraic structures with applications to polynomial equations.`;

      const validation = validateClaimGroundingTest(fakeClaimText, [sourceId], mockEvidenceStore);

      expect(validation.valid).toBe(false);
      console.log(`✅ RUN 2: REJECTED Verma Conjecture claim (different domain)`);
    });

    it('Consistently accepts real theorem claims (RUN 1 & 2)', () => {
      // Run 1: Fundamental Theorem of Arithmetic
      const sourceId1 = uuidv4();
      const abstractText1 = `
        The Fundamental Theorem of Arithmetic states that every integer greater than one is either prime
        or a unique product of prime factors. This paper provides new computational verification and extends
        the theorem to Gaussian integers. Classical proofs by Euclid and modern techniques are combined.
      `;

      mockEvidenceStore.set(sourceId1, {
        sourceId: sourceId1,
        url: `https://arxiv.org/abs/fund_arith`,
        snippet: abstractText1
      });

      const claim1 = `The Fundamental Theorem of Arithmetic guarantees unique prime factorization
        for all integers, extending naturally to Gaussian integers in the complex plane.`;

      const validation1 = validateClaimGroundingTest(claim1, [sourceId1], mockEvidenceStore);
      expect(validation1.valid).toBe(true);
      console.log(`✅ RUN 1: ACCEPTED Fundamental Theorem claim`);

      // Run 2: Different theorem in different source
      const sourceId2 = uuidv4();
      const abstractText2 = `
        Chinese Remainder Theorem provides methods for solving systems of congruences.
        The theorem states that if moduli are pairwise coprime, unique solutions exist modulo the product.
        Applications to cryptography and error correction codes are discussed.
      `;

      mockEvidenceStore.set(sourceId2, {
        sourceId: sourceId2,
        url: `https://arxiv.org/abs/chin_rem`,
        snippet: abstractText2
      });

      const claim2 = `The Chinese Remainder Theorem guarantees unique solutions for systems of congruences
        when moduli are pairwise coprime, with applications to error correction.`;

      const validation2 = validateClaimGroundingTest(claim2, [sourceId2], mockEvidenceStore);
      expect(validation2.valid).toBe(true);
      console.log(`✅ RUN 2: ACCEPTED Chinese Remainder Theorem claim (different theorem)`);
    });
  });
});

/**
 * Helper function to test claim grounding validation
 * Mimics the logic in ActionExecutorService.validateClaimGrounding()
 */
function validateClaimGroundingTest(
  claimText: string,
  sourceIds: string[],
  evidenceStore: Map<string, MockEvidence>
): { valid: boolean; reason?: string } {
  if (sourceIds.length === 0) {
    return { valid: false, reason: 'No source IDs provided' };
  }

  // Fetch sources from mock store
  const sources: MockEvidence[] = [];
  for (const id of sourceIds) {
    const evidence = evidenceStore.get(id);
    if (evidence) {
      sources.push(evidence);
    }
  }

  if (sources.length === 0) {
    return { valid: false, reason: `Sources not found (tried ${sourceIds.length} IDs)` };
  }

  const sourceContents = sources.map(s => s.snippet || s.url).join(' ');
  const sourceLower = sourceContents.toLowerCase();

  // ===== CHECK 1: Named-Concept Verification =====
  const namedConceptPattern = /\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(theorem|conjecture|lemma|hypothesis|method|algorithm|principle|law|axiom|corollary)\b/gi;

  const foundConcepts = new Set<string>();
  let regexMatch;
  while ((regexMatch = namedConceptPattern.exec(claimText)) !== null) {
    // Just capture the concept name + keyword, not the surrounding text
    foundConcepts.add(`${regexMatch[1].toLowerCase()} ${regexMatch[2].toLowerCase()}`);
  }

  const missingConcepts: string[] = [];
  for (const concept of foundConcepts) {
    if (!sourceLower.includes(concept)) {
      missingConcepts.push(concept);
    }
  }

  if (missingConcepts.length > 0) {
    return {
      valid: false,
      reason: `Named concept(s) not found in sources: ${missingConcepts.join(', ')}`
    };
  }

  // ===== CHECK 2: Term-Overlap Analysis =====
  const stopwords = new Set(['the', 'and', 'that', 'this', 'with', 'from', 'have', 'been', 'about', 'also', 'which']);
  const claimTerms = (claimText.match(/\b[a-z]{4,}\b/gi) || [])
    .filter(t => !stopwords.has(t.toLowerCase()));

  let matchCount = 0;
  for (const term of claimTerms) {
    if (sourceLower.includes(term.toLowerCase())) {
      matchCount++;
    }
  }

  const matchRatio = claimTerms.length > 0 ? matchCount / claimTerms.length : 0;
  if (matchRatio < 0.3 && claimTerms.length > 5) {
    return {
      valid: false,
      reason: `Only ${(matchRatio * 100).toFixed(0)}% of claim terms found in sources (need ≥30%)`
    };
  }

  return { valid: true };
}
