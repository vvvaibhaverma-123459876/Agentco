/**
 * HTML extraction tests — against the REAL function and REAL arXiv markup.
 * The markup below mirrors a live arXiv /abs/ page (<blockquote class="abstract mathjax">).
 */
import { describe, it, expect } from '@jest/globals';
import { extractReadableText, extractArxivAbstract } from '../src/services/html-extract';

const ARXIV_HTML = `
<!DOCTYPE html><html><head>
  <link rel="stylesheet" href="/_next/static/chunks/01godr8u6mf._.css" nonce="abc"/>
  <title>[1810.02188] 6m Theorem for Prime numbers</title>
  <script>var x = 1;</script>
</head><body>
  <h1 class="title mathjax"><span>Title:</span> 6m Theorem for Prime numbers</h1>
  <blockquote class="abstract mathjax">
    <span class="descriptor">Abstract:</span> We show that for any prime P greater than three,
    P is congruent to plus or minus one modulo six. This bounds the distribution of primes.
  </blockquote>
  <div class="footer">contact arXiv</div>
</body></html>`;

describe('extractArxivAbstract', () => {
  it('extracts the abstract text and strips the "Abstract:" label', () => {
    const abs = extractArxivAbstract(ARXIV_HTML);
    expect(abs).toBeTruthy();
    expect(abs!.toLowerCase()).toContain('congruent to plus or minus one modulo six');
    expect(abs!.toLowerCase().startsWith('abstract')).toBe(false);
  });

  it('returns null when there is no abstract block', () => {
    expect(extractArxivAbstract('<html><body><p>no abstract here</p></body></html>')).toBeNull();
  });
});

describe('extractReadableText', () => {
  it('on an arXiv abs page returns clean text containing the abstract, NOT HTML/boilerplate', () => {
    const text = extractReadableText(ARXIV_HTML, 'https://arxiv.org/abs/1810.02188');
    // No HTML tags, no script, no CSS chunk refs.
    expect(text).not.toMatch(/<[a-z]/i);
    expect(text).not.toContain('_next/static');
    expect(text).not.toContain('var x');
    // Contains the real abstract prose.
    expect(text.toLowerCase()).toContain('modulo six');
    // Includes the (label-stripped) title for context.
    expect(text.toLowerCase()).toContain('6m theorem');
  });

  it('strips tags/script/style from generic HTML', () => {
    const html = '<html><head><style>.a{}</style></head><body><script>bad()</script><p>Hello <b>world</b></p></body></html>';
    const text = extractReadableText(html, 'https://example.com/x');
    expect(text).toContain('Hello world');
    expect(text).not.toMatch(/<[a-z]/i);
    expect(text).not.toContain('bad()');
  });

  it('decodes common entities', () => {
    const text = extractReadableText('<p>Tom &amp; Jerry &lt;3</p>', 'https://e.com');
    expect(text).toContain('Tom & Jerry <3');
  });

  it('returns empty string for empty input', () => {
    expect(extractReadableText('', '')).toBe('');
  });
});
