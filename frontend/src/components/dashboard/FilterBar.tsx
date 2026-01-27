/**
 * Filter Bar Component
 * Responsive collapsible filter controls for dashboard with global region support
 */

import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, ChevronUp, Globe, Search, SlidersHorizontal, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { DashboardFilters } from '@/types/dashboard';

// Global regions organized by continent
export const GLOBAL_REGIONS = {
  'Middle East': [
    'Saudi Arabia',
    'UAE',
    'Qatar',
    'Kuwait',
    'Bahrain',
    'Oman',
    'Jordan',
    'Lebanon',
    'Iraq',
    'Egypt',
    'Israel',
    'Palestine',
    'Yemen',
    'Syria',
  ],
  'North America': ['United States', 'Canada', 'Mexico'],
  Europe: [
    'United Kingdom',
    'Germany',
    'France',
    'Italy',
    'Spain',
    'Netherlands',
    'Belgium',
    'Switzerland',
    'Austria',
    'Sweden',
    'Norway',
    'Denmark',
    'Finland',
    'Poland',
    'Portugal',
    'Ireland',
    'Greece',
    'Czech Republic',
    'Romania',
    'Hungary',
  ],
  'Asia Pacific': [
    'China',
    'Japan',
    'South Korea',
    'India',
    'Singapore',
    'Hong Kong',
    'Taiwan',
    'Thailand',
    'Malaysia',
    'Indonesia',
    'Philippines',
    'Vietnam',
    'Australia',
    'New Zealand',
    'Pakistan',
    'Bangladesh',
  ],
  'Latin America': [
    'Brazil',
    'Argentina',
    'Chile',
    'Colombia',
    'Peru',
    'Venezuela',
    'Ecuador',
    'Uruguay',
    'Costa Rica',
    'Panama',
  ],
  Africa: [
    'South Africa',
    'Nigeria',
    'Kenya',
    'Morocco',
    'Ghana',
    'Tanzania',
    'Ethiopia',
    'Algeria',
    'Tunisia',
  ],
};

// Flatten all regions for easy access
export const ALL_REGIONS = Object.values(GLOBAL_REGIONS).flat();

interface FilterBarProps {
  filters: DashboardFilters;
  onChange: (filters: Partial<DashboardFilters>) => void;
  platforms: string[];
  regions?: string[];
  useGlobalRegions?: boolean;
  className?: string;
  defaultExpanded?: boolean;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  onChange,
  platforms,
  regions,
  useGlobalRegions = true,
  className = '',
  defaultExpanded = false,
}) => {
  const { t } = useTranslation();
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [regionSearch, setRegionSearch] = useState('');
  const [expandedContinents, setExpandedContinents] = useState<string[]>(['Middle East']);

  // Use global regions or provided regions - stored for filter logic
  useMemo(() => {
    if (useGlobalRegions) {
      return ALL_REGIONS;
    }
    return regions || [];
  }, [useGlobalRegions, regions]);

  // Filter regions by search
  const filteredGlobalRegions = useMemo(() => {
    if (!regionSearch) return GLOBAL_REGIONS;

    const search = regionSearch.toLowerCase();
    const filtered: Record<string, string[]> = {};

    Object.entries(GLOBAL_REGIONS).forEach(([continent, countries]) => {
      const matchingCountries = countries.filter((country) =>
        country.toLowerCase().includes(search)
      );
      if (matchingCountries.length > 0) {
        filtered[continent] = matchingCountries;
      }
    });

    return filtered;
  }, [regionSearch]);

  // Toggle continent expansion
  const toggleContinent = (continent: string) => {
    setExpandedContinents((prev) =>
      prev.includes(continent) ? prev.filter((c) => c !== continent) : [...prev, continent]
    );
  };

  // Select all countries in a continent
  const selectContinent = (continent: string) => {
    const continentCountries = GLOBAL_REGIONS[continent as keyof typeof GLOBAL_REGIONS] || [];
    const newRegions = [...new Set([...filters.regions, ...continentCountries])];
    onChange({ regions: newRegions });
  };

  // Clear all countries in a continent
  const clearContinent = (continent: string) => {
    const continentCountries = GLOBAL_REGIONS[continent as keyof typeof GLOBAL_REGIONS] || [];
    const newRegions = filters.regions.filter((r) => !continentCountries.includes(r));
    onChange({ regions: newRegions });
  };

  // Check if all countries in a continent are selected
  const isContinentFullySelected = (continent: string) => {
    const continentCountries = GLOBAL_REGIONS[continent as keyof typeof GLOBAL_REGIONS] || [];
    return continentCountries.every((c) => filters.regions.includes(c));
  };

  // Handle date range change
  const handleDateChange = (type: 'start' | 'end', value: string) => {
    const newDateRange = { ...filters.dateRange };
    newDateRange[type] = new Date(value);
    onChange({ dateRange: newDateRange });
  };

  // Handle platform toggle
  const togglePlatform = (platform: string) => {
    const newPlatforms = filters.platforms.includes(platform)
      ? filters.platforms.filter((p) => p !== platform)
      : [...filters.platforms, platform];
    onChange({ platforms: newPlatforms });
  };

  // Handle region toggle
  const toggleRegion = (region: string) => {
    const newRegions = filters.regions.includes(region)
      ? filters.regions.filter((r) => r !== region)
      : [...filters.regions, region];
    onChange({ regions: newRegions });
  };

  // Select all / clear all
  const selectAllPlatforms = () => onChange({ platforms });
  const clearAllPlatforms = () => onChange({ platforms: [] });
  const clearAllRegions = () => onChange({ regions: [] });

  // Quick date presets
  const applyDatePreset = (preset: string) => {
    const end = new Date();
    let start = new Date();

    switch (preset) {
      case 'today':
        start = new Date();
        break;
      case '7days':
        start = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
        break;
      case '30days':
        start = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
        break;
      case '90days':
        start = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000);
        break;
      case 'thisMonth':
        start = new Date(end.getFullYear(), end.getMonth(), 1);
        break;
      case 'lastMonth':
        start = new Date(end.getFullYear(), end.getMonth() - 1, 1);
        end.setDate(0);
        break;
    }

    onChange({ dateRange: { start, end } });
  };

  // Calculate active filters count
  const activeFiltersCount = filters.platforms.length + filters.regions.length;

  return (
    <div className={cn('bg-card border rounded-lg shadow-sm', className)}>
      {/* Collapsible Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-muted/50 transition-colors rounded-t-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
        aria-expanded={isExpanded}
        aria-controls="filter-content"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg">
            <SlidersHorizontal className="h-5 w-5 text-primary" />
          </div>
          <div className="text-left">
            <h3 className="font-semibold text-foreground">{t('common.filters')}</h3>
            <p className="text-xs text-muted-foreground">
              {activeFiltersCount > 0 ? (
                <>
                  <span className="font-medium text-primary">{activeFiltersCount}</span> active
                  filters
                </>
              ) : (
                'No filters applied'
              )}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Quick Summary Pills (when collapsed) */}
          {!isExpanded && activeFiltersCount > 0 && (
            <div className="hidden sm:flex items-center gap-2">
              {filters.platforms.length > 0 && (
                <span className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-full">
                  {filters.platforms.length} platforms
                </span>
              )}
              {filters.regions.length > 0 && (
                <span className="px-2 py-1 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full">
                  {filters.regions.length} regions
                </span>
              )}
            </div>
          )}
          <div
            className={cn(
              'p-2 rounded-full transition-colors',
              isExpanded ? 'bg-primary/10' : 'bg-muted'
            )}
          >
            {isExpanded ? (
              <ChevronUp className="h-5 w-5 text-primary" />
            ) : (
              <ChevronDown className="h-5 w-5 text-muted-foreground" />
            )}
          </div>
        </div>
      </button>

      {/* Collapsible Content */}
      <div
        id="filter-content"
        className={cn(
          'overflow-hidden transition-all duration-300 ease-in-out',
          isExpanded ? 'max-h-[1000px] opacity-100' : 'max-h-0 opacity-0'
        )}
        aria-hidden={!isExpanded}
      >
        <div className="px-4 pb-4 pt-2 border-t">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
            {/* Date Range */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Date Range</label>

              {/* Quick Presets */}
              <div
                className="flex flex-wrap gap-2 mb-3"
                role="group"
                aria-label="Date range presets"
              >
                {['7days', '30days', '90days'].map((preset) => (
                  <button
                    key={preset}
                    onClick={() => applyDatePreset(preset)}
                    className="px-3 py-1 text-xs font-medium rounded-full bg-muted text-muted-foreground hover:bg-primary/10 hover:text-primary transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {preset === '7days'
                      ? 'Last 7 Days'
                      : preset === '30days'
                        ? 'Last 30 Days'
                        : 'Last 90 Days'}
                  </button>
                ))}
              </div>

              {/* Custom Date Inputs */}
              <div className="space-y-2">
                <input
                  type="date"
                  value={filters.dateRange.start.toISOString().split('T')[0]}
                  onChange={(e) => handleDateChange('start', e.target.value)}
                  max={filters.dateRange.end.toISOString().split('T')[0]}
                  className="w-full px-3 py-2 border rounded-md bg-background text-foreground text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-colors"
                  aria-label="Start date"
                />
                <input
                  type="date"
                  value={filters.dateRange.end.toISOString().split('T')[0]}
                  onChange={(e) => handleDateChange('end', e.target.value)}
                  min={filters.dateRange.start.toISOString().split('T')[0]}
                  max={new Date().toISOString().split('T')[0]}
                  className="w-full px-3 py-2 border rounded-md bg-background text-foreground text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-colors"
                  aria-label="End date"
                />
              </div>
            </div>

            {/* Platform Filter */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-foreground">Platforms</label>
                <div className="flex gap-2">
                  <button
                    onClick={selectAllPlatforms}
                    className="text-xs text-primary hover:underline focus:outline-none focus-visible:underline"
                    aria-label="Select all platforms"
                  >
                    All
                  </button>
                  <button
                    onClick={clearAllPlatforms}
                    className="text-xs text-muted-foreground hover:underline focus:outline-none focus-visible:underline"
                    aria-label="Clear all platforms"
                  >
                    Clear
                  </button>
                </div>
              </div>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {platforms.map((platform) => (
                  <label
                    key={platform}
                    className="flex items-center cursor-pointer hover:bg-muted/50 p-2 rounded transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={filters.platforms.includes(platform)}
                      onChange={() => togglePlatform(platform)}
                      className="h-4 w-4 text-primary focus:ring-primary border-border rounded"
                    />
                    <span className="ml-2 text-sm text-foreground">{platform}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Region Filter - Global Countries */}
            <div className="lg:col-span-2">
              <div className="flex items-center justify-between mb-2">
                <label className="flex items-center text-sm font-medium text-foreground">
                  <Globe className="h-4 w-4 mr-1.5 text-primary" />
                  Global Regions
                </label>
                <div className="flex gap-2">
                  <button
                    onClick={() => onChange({ regions: ALL_REGIONS })}
                    className="text-xs text-primary hover:underline"
                  >
                    All
                  </button>
                  <button
                    onClick={clearAllRegions}
                    className="text-xs text-muted-foreground hover:underline"
                  >
                    Clear
                  </button>
                </div>
              </div>

              {/* Region Search */}
              <div className="relative mb-3">
                <Search
                  className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground"
                  aria-hidden="true"
                />
                <input
                  type="text"
                  placeholder="Search countries..."
                  value={regionSearch}
                  onChange={(e) => setRegionSearch(e.target.value)}
                  className="w-full pl-9 pr-9 py-2 border rounded-md bg-background text-foreground text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-colors"
                  aria-label="Search countries"
                />
                {regionSearch && (
                  <button
                    onClick={() => setRegionSearch('')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors focus:outline-none focus-visible:text-foreground"
                    aria-label="Clear search"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>

              {/* Selected Count */}
              <div className="text-xs text-muted-foreground mb-2">
                <span className="font-semibold text-primary">{filters.regions.length}</span> of{' '}
                {ALL_REGIONS.length} countries selected
              </div>

              {/* Continent Groups */}
              <div className="space-y-1 max-h-48 overflow-y-auto border rounded-md p-2 bg-background">
                {Object.entries(filteredGlobalRegions).map(([continent, countries]) => (
                  <div key={continent} className="border-b last:border-b-0 pb-2 last:pb-0">
                    {/* Continent Header */}
                    <div className="flex items-center justify-between py-2 px-2 hover:bg-muted/50 rounded cursor-pointer">
                      <div
                        className="flex items-center flex-1"
                        onClick={() => toggleContinent(continent)}
                      >
                        <ChevronDown
                          className={cn(
                            'h-4 w-4 mr-2 text-muted-foreground transition-transform',
                            !expandedContinents.includes(continent) && '-rotate-90'
                          )}
                        />
                        <span className="font-medium text-sm text-foreground">{continent}</span>
                        <span className="ml-2 text-xs text-muted-foreground">
                          ({countries.filter((c) => filters.regions.includes(c)).length}/
                          {countries.length})
                        </span>
                      </div>
                      <div className="flex gap-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            selectContinent(continent);
                          }}
                          className={cn(
                            'px-2 py-0.5 text-xs rounded transition-colors',
                            isContinentFullySelected(continent)
                              ? 'bg-primary/20 text-primary'
                              : 'bg-muted text-muted-foreground hover:bg-primary/10 hover:text-primary'
                          )}
                        >
                          All
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            clearContinent(continent);
                          }}
                          className="px-2 py-0.5 text-xs bg-muted text-muted-foreground rounded hover:bg-destructive/10 hover:text-destructive transition-colors"
                        >
                          Clear
                        </button>
                      </div>
                    </div>

                    {/* Countries List */}
                    {expandedContinents.includes(continent) && (
                      <div className="grid grid-cols-2 gap-1 ml-6 mt-1">
                        {countries.map((country) => (
                          <label
                            key={country}
                            className="flex items-center cursor-pointer hover:bg-muted/50 p-1.5 rounded transition-colors text-sm"
                          >
                            <input
                              type="checkbox"
                              checked={filters.regions.includes(country)}
                              onChange={() => toggleRegion(country)}
                              className="h-3.5 w-3.5 text-primary focus:ring-primary border-border rounded"
                            />
                            <span className="ml-2 text-foreground truncate">{country}</span>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                ))}

                {Object.keys(filteredGlobalRegions).length === 0 && (
                  <div className="text-center py-4 text-muted-foreground text-sm">
                    No countries match "{regionSearch}"
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Footer with Clear All */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t">
            <div className="text-sm text-muted-foreground">
              <span className="font-semibold">{filters.platforms.length}</span> platforms,
              <span className="font-semibold ml-1">{filters.regions.length}</span> regions,
              <span className="font-semibold ml-1">
                {Math.ceil(
                  (filters.dateRange.end.getTime() - filters.dateRange.start.getTime()) /
                    (1000 * 60 * 60 * 24)
                )}
              </span>{' '}
              days
            </div>
            <button
              onClick={() => {
                clearAllPlatforms();
                clearAllRegions();
              }}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Clear all filters"
            >
              <X className="h-4 w-4" aria-hidden="true" />
              Clear All
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FilterBar;
