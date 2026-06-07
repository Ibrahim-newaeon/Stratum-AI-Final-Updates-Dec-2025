/**
 * Seed-entry shape for the marketing-page CMS seeder.
 *
 * Each `<slug>.ts` module in this folder default-exports one entry. Structured
 * pages set `content_json` (typed as the page's *PageContent interface at the
 * const declaration so `tsc` validates the shape); plain-HTML pages set
 * `content`. The generator (`frontend/scripts/gen-marketing-seed.ts`) collects
 * them into `backend/scripts/data/marketing_seed.json`.
 */
export interface MarketingSeedEntry {
  slug: string;
  title: string;
  /** CMS page template (from CMSPages PAGE_PRESETS), e.g. 'features', 'solution', 'default'. */
  template: string;
  meta_title?: string;
  meta_description?: string;
  /** Structured pages: the typed content_json (validated at the const declaration). */
  content_json?: unknown;
  /** Plain-HTML pages: rendered HTML body. */
  content?: string;
}
