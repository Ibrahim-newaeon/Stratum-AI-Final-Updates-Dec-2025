/**
 * Documentation content model.
 *
 * Articles are authored as a sequence of typed blocks so the renderer
 * (`DocArticlePage`) can present them with the landing "ink + ember" theme
 * without any per-article markup. Keep authoring in `content/*.ts`.
 */

import type { ComponentType } from 'react';

export type DocBlock =
  | { type: 'heading'; text: string }
  | { type: 'subheading'; text: string }
  | { type: 'paragraph'; text: string }
  | { type: 'list'; ordered?: boolean; items: string[] }
  | { type: 'code'; language?: string; code: string }
  | { type: 'callout'; tone?: 'info' | 'warning' | 'success'; title?: string; text: string };

export interface DocArticle {
  /** Path after `/docs/` — e.g. `quickstart` or `cdp/profiles`. */
  slug: string;
  /** Category title this article belongs to (must match a `DocNavCategory.title`). */
  category: string;
  title: string;
  description: string;
  /** Human read estimate, e.g. `5 min`. */
  readTime: string;
  blocks: DocBlock[];
}

export interface DocNavLink {
  name: string;
  /** Absolute route, e.g. `/docs/quickstart` or the external `/api-docs`. */
  href: string;
}

export interface DocNavCategory {
  title: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
  links: DocNavLink[];
}
