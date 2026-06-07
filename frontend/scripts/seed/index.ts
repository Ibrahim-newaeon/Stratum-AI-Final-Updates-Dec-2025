/**
 * Aggregates the per-page marketing seed modules into one ordered list the
 * generator (`frontend/scripts/gen-marketing-seed.ts`) serializes to
 * `backend/scripts/data/marketing_seed.json`.
 */
import type { MarketingSeedEntry } from './marketing/types';

import features from './marketing/features';
import pricing from './marketing/pricing';
import integrations from './marketing/integrations';
import apiDocs from './marketing/api-docs';
import about from './marketing/about';
import careers from './marketing/careers';
import caseStudies from './marketing/case-studies';
import changelog from './marketing/changelog';
import compare from './marketing/compare';
import glossary from './marketing/glossary';
import resources from './marketing/resources';
import status from './marketing/status';
import solutionsCdp from './marketing/solutions-cdp';
import solutionsAudienceSync from './marketing/solutions-audience-sync';
import solutionsTrustEngine from './marketing/solutions-trust-engine';
import solutionsPredictions from './marketing/solutions-predictions';
import privacy from './marketing/privacy';
import terms from './marketing/terms';
import security from './marketing/security';
import dpa from './marketing/dpa';

export const marketingSeed: MarketingSeedEntry[] = [
  features,
  pricing,
  integrations,
  apiDocs,
  about,
  careers,
  caseStudies,
  changelog,
  compare,
  glossary,
  resources,
  status,
  solutionsCdp,
  solutionsAudienceSync,
  solutionsTrustEngine,
  solutionsPredictions,
  privacy,
  terms,
  security,
  dpa,
];
