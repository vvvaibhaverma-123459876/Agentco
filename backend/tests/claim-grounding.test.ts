/**
 * Claim Grounding tests — exercise the REAL pure logic.
 * Imports `validateGrounding` directly from the service (no copied regex), so a green
 * test means the production grounding path is correct, not that a copy matches itself.
 */
import { describe, it, expect } from '@jest/globals';
import { validateGrounding, GroundingSource } from '../src/services/claim-grounding';

const src = (content: string, id = 'src-1'): GroundingSource[] => [{ sourceId: id, content }];

const PRIME_ABSTRACT = `
  This paper investigates fundamental properties of prime numbers and their applications
  in cryptography. We study the Goldbach conjecture and its variants, proving new bounds
  on prime gaps. The work builds on classical theorems by Euclid, Fermat, and Riemann.
  Recent computational evidence supports our theoretical framework.
`;

describe('validateGrounding — Named-Concept Verification', () => {
  it('REJECTS a fabricated theorem ("Verma Conjecture") by name', () => {
    const claim = 'The Verma Conjecture for prime numbers establishes a novel relationship between prime gaps and modular arithmetic.';
    const r = validateGrounding(claim, src(PRIME_ABSTRACT), [], { requireSnippet: false });
    expect(r.valid).toBe(false);
    expect(r.reason).toMatch(/verma conjecture/i);
  });

  it('REJECTS a numeric-prefixed fabrication ("6m theorem") absent from sources', () => {
    const claim = 'The 6m theorem establishes new bounds on prime gaps in cryptography.';
    const r = validateGrounding(claim, src(PRIME_ABSTRACT), [], { requireSnippet: false });
    expect(r.valid).toBe(false);
    expect(r.reason).toMatch(/6m theorem|not found/i);
  });

  it('REJECTS a fabricated "Fibonacci Theorem" when Fibonacci is absent', () => {
    const claim = 'The Fibonacci Theorem describes a fundamental property of prime number sequences.';
    const r = validateGrounding(claim, src(PRIME_ABSTRACT), [], { requireSnippet: false });
    expect(r.valid).toBe(false);
    expect(r.reason).toMatch(/fibonacci/i);
  });

  it('ACCEPTS a real concept ("Goldbach conjecture") present in the source', () => {
    // Terms drawn from the abstract (goldbach, conjecture, prime, gaps, bounds, computational, evidence).
    const claim = 'The Goldbach conjecture and new bounds on prime gaps are supported by recent computational evidence.';
    const r = validateGrounding(claim, src(PRIME_ABSTRACT), [], { requireSnippet: false });
    expect(r.valid).toBe(true);
  });
});

describe('validateGrounding — Term-Overlap', () => {
  it('REJECTS a generic off-topic claim (<30% overlap)', () => {
    const claim = 'Artificial intelligence neural networks enable machine learning frameworks for autonomous reinforcement systems.';
    const r = validateGrounding(claim, src(PRIME_ABSTRACT), [], { requireSnippet: false });
    expect(r.valid).toBe(false);
    expect(r.reason).toMatch(/terms found/i);
  });
});

describe('validateGrounding — Snippet-Substring (the hard grounding guarantee)', () => {
  it('REJECTS a claim whose support snippet is NOT verbatim in the source (fabricated quote)', () => {
    const claim = 'The paper proves new bounds on prime gaps.';
    const fabricated = ['primes are always twin primes beyond 10^9']; // not in source
    const r = validateGrounding(claim, src(PRIME_ABSTRACT), fabricated);
    expect(r.valid).toBe(false);
    expect(r.reason).toMatch(/snippet not found verbatim/i);
  });

  it('ACCEPTS a claim with a snippet that IS a verbatim substring of the source', () => {
    const claim = 'The paper proves new bounds on prime gaps.';
    const realQuote = ['proving new bounds on prime gaps']; // verbatim substring of abstract
    const r = validateGrounding(claim, src(PRIME_ABSTRACT), realQuote);
    expect(r.valid).toBe(true);
    expect(r.groundedSnippets).toContain('proving new bounds on prime gaps');
  });

  it('REJECTS (by default) an otherwise-grounded claim that provides NO snippet', () => {
    // High term-overlap with the abstract so it passes checks 1-3, isolating the snippet requirement.
    const claim = 'Prime numbers and their applications in cryptography rely on prime gaps and computational evidence.';
    const r = validateGrounding(claim, src(PRIME_ABSTRACT), []); // requireSnippet defaults true
    expect(r.valid).toBe(false);
    expect(r.reason).toMatch(/no grounded snippet/i);
  });

  it('matches snippets case-insensitively and whitespace-normalised', () => {
    const claim = 'Computational evidence supports the framework.';
    const messyQuote = ['Recent   COMPUTATIONAL evidence\n supports our theoretical framework'];
    const r = validateGrounding(claim, src(PRIME_ABSTRACT), messyQuote);
    expect(r.valid).toBe(true);
  });
});

describe('validateGrounding — Reproducibility across domains', () => {
  const CRYPTO = 'Cryptographic applications of number theory. RSA security depends on prime factorization difficulty. Elliptic curve cryptography uses algebraic geometry.';
  const GROUP = 'Group theory and algebraic structures. Galois theory principles. Field extensions and polynomial equations. Fundamental theorem of Galois theory.';

  it('RUN 1: rejects "Verma Conjecture" in a cryptography source', () => {
    const r = validateGrounding('The Verma Conjecture underpins cryptographic protocols.', src(CRYPTO), [], { requireSnippet: false });
    expect(r.valid).toBe(false);
  });

  it('RUN 2: rejects "Verma Conjecture" in a group-theory source', () => {
    const r = validateGrounding('Recent work on the Verma Conjecture extends Galois theory.', src(GROUP), [], { requireSnippet: false });
    expect(r.valid).toBe(false);
  });

  it('RUN 1&2: accepts real concepts grounded with verbatim snippets', () => {
    const r1 = validateGrounding(
      'RSA security depends on factorization.',
      src(CRYPTO),
      ['RSA security depends on prime factorization difficulty'],
    );
    expect(r1.valid).toBe(true);

    const r2 = validateGrounding(
      'The Galois theory of field extensions.',
      src(GROUP),
      ['Field extensions and polynomial equations'],
    );
    expect(r2.valid).toBe(true);
  });
});
