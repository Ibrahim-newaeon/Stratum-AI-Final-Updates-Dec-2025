/**
 * Feature #20 — Natural Language Filters Card
 *
 * Accepts natural language queries and converts them to dashboard filters.
 */

import { useState, useCallback } from 'react';
import {
  Search,
  Sparkles,
  Filter,
  Clock,
  ArrowRight,
  X,
  Tag,
} from 'lucide-react';
import {
  useNLFilter,
  type ParsedFilter,
  type QuerySuggestion,
  type RecentQuery,
} from '@/api/dashboard';

const intentConfig: Record<string, { color: string; bg: string; label: string }> = {
  filter: { color: 'text-blue-600', bg: 'bg-blue-50', label: 'Filter' },
  compare: { color: 'text-purple-600', bg: 'bg-purple-50', label: 'Compare' },
  analyze: { color: 'text-amber-600', bg: 'bg-amber-50', label: 'Analyze' },
  summarize: { color: 'text-emerald-600', bg: 'bg-emerald-50', label: 'Summary' },
  question: { color: 'text-cyan-600', bg: 'bg-cyan-50', label: 'Question' },
};

function FilterChip({ filter, onRemove }: { filter: ParsedFilter; onRemove?: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 text-xs font-medium rounded-lg">
      <Filter className="w-3 h-3" />
      {filter.display_label}
      {onRemove && (
        <button onClick={onRemove} aria-label="Remove filter" className="hover:text-blue-900 transition-colors">
          <X className="w-3 h-3" />
        </button>
      )}
    </span>
  );
}

function SuggestionChip({ suggestion, onClick }: { suggestion: QuerySuggestion; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 p-2.5 rounded-lg border hover:bg-muted/30 hover:border-foreground/15 transition-colors text-left group"
    >
      <div className="w-7 h-7 rounded-lg bg-muted/30 flex items-center justify-center shrink-0 group-hover:bg-blue-50 transition-colors">
        <Sparkles className="w-3.5 h-3.5 text-muted-foreground/50 group-hover:text-blue-500 transition-colors" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-xs font-semibold text-foreground truncate">{suggestion.query}</div>
        <div className="text-[10px] text-muted-foreground/50 truncate">{suggestion.description}</div>
      </div>
      <ArrowRight className="w-3.5 h-3.5 text-muted-foreground/30 group-hover:text-blue-400 transition-colors shrink-0" />
    </button>
  );
}

function RecentQueryRow({ rq, onClick }: { rq: RecentQuery; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 p-2 rounded-lg hover:bg-muted/30 transition-colors text-left w-full"
    >
      <Clock className="w-3.5 h-3.5 text-muted-foreground/30 shrink-0" />
      <span className="text-xs text-muted-foreground truncate flex-1">{rq.query}</span>
      <span className="text-[10px] text-muted-foreground/50 shrink-0">{rq.filters_count} filters</span>
    </button>
  );
}

export function NLFilterCard() {
  const [inputValue, setInputValue] = useState('');
  const [activeQuery, setActiveQuery] = useState('');
  const { data, isLoading } = useNLFilter(activeQuery, true);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      setActiveQuery(inputValue.trim());
    }
  }, [inputValue]);

  const handleSuggestionClick = useCallback((query: string) => {
    setInputValue(query);
    setActiveQuery(query);
  }, []);

  const handleClear = useCallback(() => {
    setInputValue('');
    setActiveQuery('');
  }, []);

  const hasResults = data?.interpretation?.applied;
  const icfg = data?.interpretation?.intent ? intentConfig[data.interpretation.intent] || intentConfig.filter : null;

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      <div className="px-6 pt-5 pb-4 border-b border">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-50 to-violet-50 flex items-center justify-center">
            <Search className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-foreground">Smart Filters</h3>
              <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-gradient-to-r from-blue-50 to-violet-50 text-violet-600">
                Natural Language
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">Ask in plain English to filter your dashboard</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="relative">
          <div className="flex items-center gap-2 px-4 py-3 bg-muted/30 rounded-xl border focus-within:border-blue-300 focus-within:ring-2 focus-within:ring-blue-100 transition-colors">
            <Sparkles className="w-4 h-4 text-muted-foreground/50 shrink-0" />
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="e.g., Show Meta campaigns with ROAS above 3x"
              aria-label="Filter campaigns"
              className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/50 outline-none"
            />
            {inputValue && (
              <button type="button" onClick={handleClear} aria-label="Clear input" className="text-muted-foreground/50 hover:text-muted-foreground transition-colors">
                <X className="w-4 h-4" />
              </button>
            )}
            <button
              type="submit"
              disabled={!inputValue.trim() || isLoading}
              className="px-3 py-1 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? '...' : 'Search'}
            </button>
          </div>
        </form>

        {/* Active filters */}
        {hasResults && data?.interpretation && (
          <div className="mt-3 space-y-2">
            <div className="flex items-center gap-2">
              {icfg && (
                <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${icfg.bg} ${icfg.color}`}>
                  {icfg.label}
                </span>
              )}
              <span className="text-xs text-muted-foreground">{data.interpretation.explanation}</span>
              <span className="text-[10px] text-muted-foreground/50">{data.interpretation.confidence.toFixed(0)}% confidence</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {data.interpretation.parsed_filters.map((f, i) => (
                <FilterChip key={i} filter={f} />
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="p-4 space-y-4 max-h-[25rem] overflow-y-auto">
        {/* Suggestions */}
        {data?.suggestions && data.suggestions.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Sparkles className="w-3.5 h-3.5 text-muted-foreground/50" />
              <span className="text-[10px] font-bold uppercase text-muted-foreground/50">Suggested Queries</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {data.suggestions.map((s, i) => (
                <SuggestionChip key={i} suggestion={s} onClick={() => handleSuggestionClick(s.query)} />
              ))}
            </div>
          </div>
        )}

        {/* Recent queries */}
        {data?.recent_queries && data.recent_queries.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Clock className="w-3.5 h-3.5 text-muted-foreground/50" />
              <span className="text-[10px] font-bold uppercase text-muted-foreground/50">Recent Searches</span>
            </div>
            <div className="space-y-0.5">
              {data.recent_queries.map((rq, i) => (
                <RecentQueryRow key={i} rq={rq} onClick={() => handleSuggestionClick(rq.query)} />
              ))}
            </div>
          </div>
        )}

        {/* Example queries (when empty) */}
        {!activeQuery && data?.example_queries && (
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Tag className="w-3.5 h-3.5 text-muted-foreground/50" />
              <span className="text-[10px] font-bold uppercase text-muted-foreground/50">Try These</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {data.example_queries.map((eq, i) => (
                <button
                  key={i}
                  onClick={() => handleSuggestionClick(eq)}
                  className="text-xs px-2.5 py-1.5 rounded-lg bg-muted/30 text-muted-foreground hover:bg-blue-50 hover:text-blue-600 transition-colors"
                >
                  {eq}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
