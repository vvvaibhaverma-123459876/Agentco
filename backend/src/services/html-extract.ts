/**
 * HTML → readable text extraction (pure, no I/O).
 * =============================================
 * Evidence was previously stored as the first 2000 chars of RAW HTML, which for arXiv /abs/
 * pages didn't even reach the abstract (it sat past the <head> boilerplate). Claims then
 * grounded against page titles/boilerplate instead of paper prose.
 *
 * This extracts clean readable text:
 *  - arXiv /abs/ pages: the <blockquote class="abstract…"> abstract (with the "Abstract:" label
 *    stripped), falling back to the citation/description meta tag.
 *  - Any HTML: drop <script>/<style>/<head>, strip tags, decode common entities, collapse whitespace.
 */

const ENTITIES: Record<string, string> = {
  '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#39;': "'", '&apos;': "'", '&nbsp;': ' ',
};

function decodeEntities(s: string): string {
  return s
    .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n)))
    .replace(/&[a-z]+;|&#39;/gi, (m) => ENTITIES[m.toLowerCase()] ?? m);
}

function stripTags(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ');
}

function collapse(text: string): string {
  return decodeEntities(text).replace(/\s+/g, ' ').trim();
}

/** Extract the arXiv abstract, or null if this isn't an arXiv abstract page / not found. */
export function extractArxivAbstract(html: string): string | null {
  // Primary: <blockquote class="abstract mathjax"> Abstract: <text> </blockquote>
  const bq = html.match(/<blockquote[^>]*class="abstract[^"]*"[^>]*>([\s\S]*?)<\/blockquote>/i);
  if (bq) {
    let text = collapse(stripTags(bq[1]));
    text = text.replace(/^abstract:?\s*/i, '').trim();
    if (text.length > 20) return text;
  }
  // Fallback: <meta name="citation_abstract"|"description" content="…">
  const meta = html.match(/<meta\s+(?:name|property)="(?:citation_abstract|description|og:description)"\s+content="([^"]+)"/i);
  if (meta) {
    const text = collapse(meta[1]);
    if (text.length > 20) return text;
  }
  return null;
}

/**
 * Extract readable text from an HTML document. For arXiv abstract pages, returns the abstract;
 * otherwise returns generic stripped body text. Returns '' only if nothing usable is found.
 */
export function extractReadableText(html: string, url = ''): string {
  if (!html) return '';

  // arXiv abstract pages: prefer the actual abstract.
  if (/arxiv\.org\/abs\//i.test(url) || /<blockquote[^>]*class="abstract/i.test(html)) {
    const abstract = extractArxivAbstract(html);
    if (abstract) {
      const title = html.match(/<title[^>]*>([^<]+)<\/title>/i)?.[1];
      const titleClean = title ? collapse(title).replace(/^\[[^\]]*\]\s*/, '') : '';
      return titleClean ? `${titleClean}. ${abstract}` : abstract;
    }
  }

  // Generic: drop <head>, then strip the body.
  const withoutHead = html.replace(/<head[\s\S]*?<\/head>/i, ' ');
  const text = collapse(stripTags(withoutHead));
  return text;
}
