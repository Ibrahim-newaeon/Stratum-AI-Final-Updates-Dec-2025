/**
 * Generator: export the marketing-page seed modules to a static JSON artifact
 * the backend seed (`backend/scripts/seed_marketing_pages.py`) loads to create
 * editable CMS pages for the public marketing pages.
 *
 * Re-run after editing any scripts/seed/marketing/*.ts:
 *   npx tsx frontend/scripts/gen-marketing-seed.ts
 */
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { marketingSeed } from './seed/index';

const out = marketingSeed.map((e) => ({
  slug: e.slug,
  title: e.title,
  template: e.template,
  meta_title: (e.meta_title ?? e.title).slice(0, 70),
  meta_description: (e.meta_description ?? '').slice(0, 160),
  content_json: e.content_json ?? null,
  content: e.content ?? null,
}));

const target = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../../backend/scripts/data/marketing_seed.json'
);
mkdirSync(dirname(target), { recursive: true });
writeFileSync(target, `${JSON.stringify(out, null, 2)}\n`);
console.log(`Wrote ${out.length} marketing pages -> ${target}`);
