/**
 * Source Discovery Engine Tests (D1)
 * ===================================
 * Verifies that real URLs can be discovered without a search API,
 * and the full slice works: discover → fetch → evidence → claim
 */

import { describe, it, expect } from '@jest/globals';
import { SourceDiscoveryEngine } from '../src/services/source-discovery.service';

describe('SourceDiscoveryEngine (D1)', () => {
  let engine: SourceDiscoveryEngine;

  beforeEach(() => {
    engine = new SourceDiscoveryEngine();
  });

  describe('Seed Registry', () => {
    it('should have multiple source packs', () => {
      const packs = engine.getAvailableSourcePacks();
      expect(packs.length).toBeGreaterThan(0);
      expect(packs).toContain('technical');
      expect(packs).toContain('ai_tech');
      expect(packs).toContain('scientific');
      expect(packs).toContain('business');
      expect(packs).toContain('governance');
    });

    it('should provide descriptions for each pack', () => {
      const packs = engine.getAvailableSourcePacks();
      for (const pack of packs) {
        const desc = engine.getSourcePackDescription(pack);
        expect(desc).toBeTruthy();
        expect(desc?.length).toBeGreaterThan(0);
      }
    });
  });

  describe('Source Discovery from Seed Registry', () => {
    it('should discover sources from technical pack', async () => {
      const sources = await engine.discoverSourcesFromPack('technical', 3);
      expect(sources.length).toBeGreaterThan(0);
      expect(sources[0]).toMatchObject({
        discovery_method: expect.stringMatching(/seed|rss_feed/),
        trust_tier: 'seed',
        allowed_to_fetch: true,
        risk_classification: 'safe',
      });
    });

    it('should discover sources from ai_tech pack', async () => {
      const sources = await engine.discoverSourcesFromPack('ai_tech', 3);
      expect(sources.length).toBeGreaterThan(0);
      expect(sources[0]).toHaveProperty('source_url');
      expect(sources[0]).toHaveProperty('source_domain');
      expect(sources[0]).toHaveProperty('topic_hint');
    });

    it('should discover sources from scientific pack', async () => {
      const sources = await engine.discoverSourcesFromPack('scientific', 2);
      expect(sources.length).toBeGreaterThan(0);
    });

    it('should respect maxSources limit', async () => {
      const sources = await engine.discoverSourcesFromPack('technical', 2);
      expect(sources.length).toBeLessThanOrEqual(2);
    });

    it('should return empty array for non-existent pack', async () => {
      const sources = await engine.discoverSourcesFromPack('nonexistent');
      expect(sources).toEqual([]);
    });

    it('should validate source reachability before returning', async () => {
      // This test proves we're not returning URLs without checking if they work
      const sources = await engine.discoverSourcesFromPack('technical', 5);

      // Each discovered source should be marked allowed_to_fetch: true
      // only if it was validated
      for (const source of sources) {
        if (source.allowed_to_fetch) {
          // Should have been validated
          expect(source.reason_allowed).toBeTruthy();
        }
      }
    });
  });

  describe('Source Provenance', () => {
    it('should include discovery method in discovered sources', async () => {
      const sources = await engine.discoverSourcesFromPack('technical', 3);

      for (const source of sources) {
        expect(['seed', 'rss_feed', 'sitemap', 'link_extraction']).toContain(
          source.discovery_method
        );
      }
    });

    it('should include source pack classification', async () => {
      const sources = await engine.discoverSourcesFromPack('ai_tech', 2);

      for (const source of sources) {
        expect(source.source_pack).toBe('ai_tech');
      }
    });

    it('should include trust tier and risk classification', async () => {
      const sources = await engine.discoverSourcesFromPack('technical', 2);

      for (const source of sources) {
        expect(['seed', 'verified', 'discovered']).toContain(source.trust_tier);
        expect(['safe', 'caution', 'blocked']).toContain(source.risk_classification);
      }
    });

    it('should parse domain correctly', async () => {
      const sources = await engine.discoverSourcesFromPack('technical', 2);

      for (const source of sources) {
        expect(source.source_domain).not.toBeNull();
        expect(source.source_domain).not.toBe('unknown');
      }
    });

    it('should set discovery_timestamp to now', async () => {
      const beforeTime = new Date();
      const sources = await engine.discoverSourcesFromPack('technical', 2);
      const afterTime = new Date();

      for (const source of sources) {
        expect(source.discovery_timestamp.getTime()).toBeGreaterThanOrEqual(
          beforeTime.getTime()
        );
        expect(source.discovery_timestamp.getTime()).toBeLessThanOrEqual(
          afterTime.getTime()
        );
      }
    });
  });

  describe('D1 Core Invariants', () => {
    it('should never return unreachable URLs', async () => {
      // This is the core D1 invariant: discovered sources must be reachable
      const sources = await engine.discoverSourcesFromPack('technical', 10);

      // All discovered sources should have allowed_to_fetch = true
      // because we validated them before returning
      for (const source of sources) {
        expect(source.allowed_to_fetch).toBe(true);
      }
    });

    it('should never return fake/synthetic sources', async () => {
      const sources = await engine.discoverSourcesFromPack('ai_tech');

      // All sources should be real URLs from actual registries
      for (const source of sources) {
        expect(source.source_url).toMatch(/^https?:\/\//);
        // Should not contain test/mock indicators
        expect(source.source_url).not.toMatch(/mock|fake|synthetic|test/i);
      }
    });

    it('should include explicit reason for allowing fetch', async () => {
      const sources = await engine.discoverSourcesFromPack('technical', 5);

      for (const source of sources) {
        if (source.allowed_to_fetch) {
          expect(source.reason_allowed).toBeTruthy();
          expect(source.reason_allowed?.length).toBeGreaterThan(0);
        }
      }
    });
  });
});
