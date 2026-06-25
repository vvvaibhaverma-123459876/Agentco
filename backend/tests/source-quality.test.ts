/**
 * Source-quality scoring — pure credibility logic, anchored to the REAL data from the
 * discriminating test (2026-06-25):
 *   junk arXiv:1810.02188 ("6m theorem") -> 0 citations / 0 influential / no venue
 *   Maynard arXiv:1311.4600 ("Small gaps") -> 145 citations / 29 influential / venue
 * The whole point: separate credible-from-junk (citations), where journal-ref/DOI failed.
 */
import { describe, it, expect } from '@jest/globals';
import { scoreSourceQuality, arxivIdFromUrl } from '../src/services/source-quality.service';

describe('scoreSourceQuality — separates junk from legit (the real cases)', () => {
  it('ranks the junk preprint LOW (0 citations, established)', () => {
    const s = scoreSourceQuality({ citationCount: 0, influentialCitationCount: 0, venue: '', year: 2018 }, 2026);
    expect(s.tier).toBe('low');
    expect(s.quality).toBeLessThan(0.3);
  });

  it('ranks the landmark paper HIGH (145 citations, 29 influential, venue)', () => {
    const s = scoreSourceQuality(
      { citationCount: 145, influentialCitationCount: 29, venue: 'Graduate Studies in Mathematics', year: 2013 },
      2026,
    );
    expect(s.tier).toBe('high');
    expect(s.quality).toBeGreaterThan(0.7);
  });

  it('the junk paper scores STRICTLY BELOW the landmark paper', () => {
    const junk = scoreSourceQuality({ citationCount: 0, influentialCitationCount: 0, venue: '', year: 2018 }, 2026);
    const legit = scoreSourceQuality({ citationCount: 145, influentialCitationCount: 29, venue: 'GSM', year: 2013 }, 2026);
    expect(junk.quality).toBeLessThan(legit.quality);
  });
});

describe('scoreSourceQuality — fail-soft & age-aware (no false penalties)', () => {
  it('UNKNOWN (null citations) is NEUTRAL, never penalised', () => {
    const s = scoreSourceQuality({ citationCount: null, influentialCitationCount: null }, 2026);
    expect(s.tier).toBe('unknown');
    expect(s.quality).toBe(0.5);
  });

  it('a RECENT paper with 0 citations is "too new to judge" (neutral), NOT low', () => {
    const s = scoreSourceQuality({ citationCount: 0, influentialCitationCount: 0, year: 2026 }, 2026);
    expect(s.tier).toBe('unknown');
    expect(s.quality).toBe(0.5);
  });

  it('an established paper with modest traction is medium', () => {
    const s = scoreSourceQuality({ citationCount: 8, influentialCitationCount: 1, year: 2015 }, 2026);
    expect(['medium', 'high']).toContain(s.tier);
    expect(s.quality).toBeGreaterThanOrEqual(0.6);
  });
});

describe('arxivIdFromUrl', () => {
  it('extracts ids from /abs/ and /pdf/ and versioned URLs', () => {
    expect(arxivIdFromUrl('https://arxiv.org/abs/1810.02188')).toBe('1810.02188');
    expect(arxivIdFromUrl('https://arxiv.org/abs/1311.4600v3')).toBe('1311.4600');
    expect(arxivIdFromUrl('http://arxiv.org/pdf/2310.20697')).toBe('2310.20697');
  });
  it('returns null for non-arXiv URLs', () => {
    expect(arxivIdFromUrl('https://scholar.google.com/')).toBeNull();
  });
});
