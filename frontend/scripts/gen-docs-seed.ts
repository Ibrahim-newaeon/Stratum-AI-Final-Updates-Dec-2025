/**
 * Generator: export the built-in documentation registry to a static JSON
 * artifact the backend seed script (`backend/scripts/seed_docs_pages.py`)
 * loads to create editable CMS pages (slug `docs-<slug>`).
 *
 * The frontend TS registry stays the single source of truth; re-run after
 * editing any content/*.ts:
 *
 *   npx tsx frontend/scripts/gen-docs-seed.ts
 *
 * Imports ONLY the content arrays (pure data, type-only imports) so the
 * script never pulls in React/heroicons.
 */

import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { gettingStartedArticles } from '../src/views/pages/resources/docs/content/gettingStarted';
import { apiReferenceArticles } from '../src/views/pages/resources/docs/content/apiReference';
import { trustEngineArticles } from '../src/views/pages/resources/docs/content/trustEngine';
import { cdpArticles } from '../src/views/pages/resources/docs/content/cdp';
import { integrationsArticles } from '../src/views/pages/resources/docs/content/integrations';
import { tutorialsArticles } from '../src/views/pages/resources/docs/content/tutorials';
import type { DocArticle, DocBlock } from '../src/views/pages/resources/docs/types';

const all: DocArticle[] = [
  ...gettingStartedArticles,
  ...apiReferenceArticles,
  ...trustEngineArticles,
  ...cdpArticles,
  ...integrationsArticles,
  ...tutorialsArticles,
];

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function blockToHtml(b: DocBlock): string {
  switch (b.type) {
    case 'heading':
      return `<h2>${esc(b.text)}</h2>`;
    case 'subheading':
      return `<h3>${esc(b.text)}</h3>`;
    case 'paragraph':
      return `<p>${esc(b.text)}</p>`;
    case 'list': {
      const items = b.items.map((i) => `<li>${esc(i)}</li>`).join('');
      return b.ordered ? `<ol>${items}</ol>` : `<ul>${items}</ul>`;
    }
    case 'code':
      return `<pre><code>${esc(b.code)}</code></pre>`;
    case 'callout': {
      const title = b.title ? `<strong>${esc(b.title)}: </strong>` : '';
      return `<blockquote><p>${title}${esc(b.text)}</p></blockquote>`;
    }
    default:
      return '';
  }
}

const out = all.map((a) => ({
  slug: `docs-${a.slug.replace(/\//g, '-')}`,
  route: `/docs/${a.slug}`,
  title: a.title,
  category: a.category,
  meta_title: a.title.slice(0, 70),
  meta_description: a.description.slice(0, 160),
  content: a.blocks.map(blockToHtml).join('\n'),
}));

const target = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../../backend/scripts/data/docs_seed.json'
);
mkdirSync(dirname(target), { recursive: true });
writeFileSync(target, `${JSON.stringify(out, null, 2)}\n`);
console.log(`Wrote ${out.length} doc pages -> ${target}`);
