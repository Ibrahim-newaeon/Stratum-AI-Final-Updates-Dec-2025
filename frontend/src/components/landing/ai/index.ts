/**
 * AI Landing Components - Export Index
 */

export { default as AIHero } from './AIHero';
export { default as AIFeatures } from './AIFeatures';
export { default as TrustEngine } from './TrustEngine';
export { default as BattleCard } from './BattleCard';
export { default as AIPricing } from './AIPricing';
// AITestimonials and AICTA were deleted (2026-08-17). Both were unreachable —
// nothing imports this barrel — and both carried fabricated claims: four
// invented named testimonials, plus "$2.4B+ Revenue Optimized",
// "4.9/5 Customer Rating" and "500+ Companies". Dead code holding numbers
// nobody can substantiate is a liability, because someone wires it up later
// and ships all of it at once. Do not restore without attributable figures.
export { default as AIFooter } from './AIFooter';
