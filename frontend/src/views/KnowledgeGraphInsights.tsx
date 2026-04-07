/**
 * Knowledge Graph Insights View
 *
 * Dashboard page for viewing AI-powered problem detection
 * and suggested solutions from the Knowledge Graph.
 */

import { Helmet } from 'react-helmet-async';
import { KGInsights } from '@/components/knowledge-graph';

export default function KnowledgeGraphInsights() {
  return (
    <>
      <Helmet>
        <title>Knowledge Graph Insights | Stratum AI</title>
        <meta
          name="description"
          content="AI-powered problem detection with root cause analysis and suggested solutions"
        />
      </Helmet>

      <div className="max-w-7xl mx-auto">
        <KGInsights />
      </div>
    </>
  );
}
