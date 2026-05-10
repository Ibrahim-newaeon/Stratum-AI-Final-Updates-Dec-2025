# Performance Optimization

## Overview

Stratum AI implements various performance optimizations for fast load times and smooth interactions.

---

## Code Splitting

### Route-Based Splitting

All views are lazy-loaded:

```tsx
// App.tsx
const CDPDashboard = lazy(() => import('./views/cdp/CDPDashboard'))
const Campaigns = lazy(() => import('./views/Campaigns'))

<Suspense fallback={<LoadingSpinner />}>
  <CDPDashboard />
</Suspense>
```

### Component-Based Splitting

Heavy components can be split:

```tsx
const HeavyChart = lazy(() => import('./components/charts/HeavyChart'))

function Dashboard() {
  return (
    <Suspense fallback={<ChartSkeleton />}>
      <HeavyChart data={data} />
    </Suspense>
  )
}
```

---

## Bundle Optimization

### Vite Configuration

```ts
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'chart-vendor': ['recharts', '@tremor/react'],
          'ui-vendor': ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
        },
      },
    },
    chunkSizeWarningLimit: 1000,
  },
})
```

### Tree Shaking

Import only what you need:

```tsx
// Bad - imports entire library
import _ from 'lodash'

// Good - imports only needed function
import debounce from 'lodash/debounce'

// Bad - imports all icons
import * as Icons from 'lucide-react'

// Good - imports only needed icons
import { Home, Settings, User } from 'lucide-react'
```

---

## Data Fetching

### TanStack Query Caching

```tsx
const { data } = useQuery({
  queryKey: ['campaigns', filters],
  queryFn: () => fetchCampaigns(filters),
  staleTime: 5 * 60 * 1000,      // 5 minutes
  gcTime: 30 * 60 * 1000,        // 30 minutes (formerly cacheTime)
  refetchOnWindowFocus: false,
})
```

### Prefetching

```tsx
const queryClient = useQueryClient()

// Prefetch on hover
<Link
  to="/campaigns"
  onMouseEnter={() => {
    queryClient.prefetchQuery({
      queryKey: ['campaigns'],
      queryFn: fetchCampaigns,
    })
  }}
>
  Campaigns
</Link>
```

### Pagination

```tsx
function CampaignList() {
  const [page, setPage] = useState(1)

  const { data } = useQuery({
    queryKey: ['campaigns', page],
    queryFn: () => fetchCampaigns({ page, limit: 20 }),
    keepPreviousData: true, // Smooth pagination
  })

  // Prefetch next page
  useEffect(() => {
    if (data?.hasNextPage) {
      queryClient.prefetchQuery({
        queryKey: ['campaigns', page + 1],
        queryFn: () => fetchCampaigns({ page: page + 1, limit: 20 }),
      })
    }
  }, [data, page])
}
```

---

## Rendering Optimization

### React.memo

```tsx
const ExpensiveComponent = memo(function ExpensiveComponent({ data }) {
  // Only re-renders when data changes
  return <div>{/* Complex rendering */}</div>
})
```

### useMemo

```tsx
function Dashboard({ campaigns }) {
  // Expensive calculation memoized
  const totalSpend = useMemo(() => {
    return campaigns.reduce((sum, c) => sum + c.spend, 0)
  }, [campaigns])

  return <MetricCard value={totalSpend} />
}
```

### useCallback

```tsx
function CampaignList({ onSelect }) {
  // Callback memoized for child components
  const handleSelect = useCallback((id: number) => {
    onSelect(id)
  }, [onSelect])

  return campaigns.map(c => (
    <CampaignRow key={c.id} onSelect={handleSelect} />
  ))
}
```

---

## List Virtualization

For large lists, use virtualization:

```tsx
import { useVirtualizer } from '@tanstack/react-virtual'

function VirtualList({ items }) {
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50,
  })

  return (
    <div ref={parentRef} style={{ height: 400, overflow: 'auto' }}>
      <div style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map(virtualRow => (
          <div
            key={virtualRow.key}
            style={{
              position: 'absolute',
              top: virtualRow.start,
              height: virtualRow.size,
            }}
          >
            {items[virtualRow.index].name}
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

## Image Optimization

### Lazy Loading

```tsx
<img
  src={imageSrc}
  loading="lazy"
  alt="Description"
/>
```

### Responsive Images

```tsx
<img
  srcSet="
    /image-400.webp 400w,
    /image-800.webp 800w,
    /image-1200.webp 1200w
  "
  sizes="(max-width: 400px) 400px, (max-width: 800px) 800px, 1200px"
  alt="Description"
/>
```

### WebP Format

Use WebP for smaller file sizes:

```tsx
<picture>
  <source srcSet="/image.webp" type="image/webp" />
  <source srcSet="/image.jpg" type="image/jpeg" />
  <img src="/image.jpg" alt="Description" />
</picture>
```

---

## Debouncing & Throttling

### Debounced Search

```tsx
import { useDebouncedValue } from '@/hooks/useDebouncedValue'

function SearchInput() {
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search, 300)

  const { data } = useQuery({
    queryKey: ['search', debouncedSearch],
    queryFn: () => searchCampaigns(debouncedSearch),
    enabled: debouncedSearch.length > 0,
  })
}
```

### Throttled Scroll

```tsx
import { throttle } from 'lodash'

function ScrollHandler() {
  const handleScroll = useMemo(
    () => throttle(() => {
      // Handle scroll
    }, 100),
    []
  )

  useEffect(() => {
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [handleScroll])
}
```

---

## State Updates

### Batch Updates

React 18 automatically batches updates:

```tsx
function handleClick() {
  // These are batched into one render
  setCount(c => c + 1)
  setFlag(f => !f)
  setName('new')
}
```

### Avoid Unnecessary State

```tsx
// Bad - derived state stored separately
const [items, setItems] = useState([])
const [filteredItems, setFilteredItems] = useState([])

// Good - derive from source
const [items, setItems] = useState([])
const filteredItems = useMemo(
  () => items.filter(i => i.active),
  [items]
)
```

---

## Web Vitals

### Metrics to Track

| Metric | Target | Description |
|--------|--------|-------------|
| LCP | < 2.5s | Largest Contentful Paint |
| FID | < 100ms | First Input Delay |
| CLS | < 0.1 | Cumulative Layout Shift |
| TTFB | < 600ms | Time to First Byte |

### Monitoring

```tsx
// Report web vitals
import { getCLS, getFID, getLCP, getTTFB } from 'web-vitals'

getCLS(console.log)
getFID(console.log)
getLCP(console.log)
getTTFB(console.log)
```

---

## Production Optimizations

### Compression

Vite builds with gzip:

```ts
// vite.config.ts
import viteCompression from 'vite-plugin-compression'

export default defineConfig({
  plugins: [
    viteCompression({
      algorithm: 'gzip',
    }),
  ],
})
```

### Minification

Built-in with Vite:

```bash
npm run build
# Output is minified and tree-shaken
```

### CDN

Static assets served via CloudFront:

```
- index.html: edge-cached
- assets/*.js: immutable cache (hashed filenames)
- assets/*.css: immutable cache
```

---

## Profiling

### React DevTools Profiler

1. Install React DevTools
2. Open Profiler tab
3. Record interactions
4. Analyze component render times

### Chrome DevTools

1. Performance tab
2. Record page load
3. Analyze:
   - JavaScript execution
   - Layout/Paint
   - Network requests

### Bundle Analysis

```bash
# Analyze bundle size
npx vite-bundle-visualizer
```
