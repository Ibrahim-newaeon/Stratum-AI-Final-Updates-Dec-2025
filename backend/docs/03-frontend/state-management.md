# State Management

## Overview

Stratum AI uses a hybrid state management approach:

| Type | Technology | Use Case |
|------|------------|----------|
| Server State | TanStack Query | API data caching |
| Global State | Zustand | User preferences, UI state |
| Context State | React Context | Auth, Theme, Demo mode |
| Local State | useState/useReducer | Component-specific state |

---

## TanStack Query (Server State)

### Setup

```tsx
// main.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

<QueryClientProvider client={queryClient}>
  <App />
</QueryClientProvider>
```

### Query Hooks

```tsx
// api/campaigns.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

export function useCampaigns(options?: QueryOptions) {
  return useQuery({
    queryKey: ['campaigns', options],
    queryFn: () => fetchCampaigns(options),
    staleTime: 5 * 60 * 1000,
  })
}

export function useCreateCampaign() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createCampaign,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
    },
  })
}
```

### Usage in Components

```tsx
function CampaignList() {
  const { data, isLoading, error } = useCampaigns({ status: 'active' })

  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorMessage error={error} />

  return (
    <ul>
      {data?.items.map(campaign => (
        <li key={campaign.id}>{campaign.name}</li>
      ))}
    </ul>
  )
}
```

### Cache Invalidation

```tsx
const queryClient = useQueryClient()

// Invalidate specific query
queryClient.invalidateQueries({ queryKey: ['campaigns'] })

// Invalidate with pattern
queryClient.invalidateQueries({ queryKey: ['campaigns', tenantId] })

// Optimistic update
const mutation = useMutation({
  mutationFn: updateCampaign,
  onMutate: async (newData) => {
    await queryClient.cancelQueries({ queryKey: ['campaign', id] })
    const previous = queryClient.getQueryData(['campaign', id])
    queryClient.setQueryData(['campaign', id], newData)
    return { previous }
  },
  onError: (err, newData, context) => {
    queryClient.setQueryData(['campaign', id], context.previous)
  },
})
```

---

## Zustand (Global State)

### Store Definition

```tsx
// stores/tenantStore.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface TenantState {
  currentTenantId: number | null
  tenants: Tenant[]
  setCurrentTenant: (id: number) => void
  setTenants: (tenants: Tenant[]) => void
}

export const useTenantStore = create<TenantState>()(
  persist(
    (set) => ({
      currentTenantId: null,
      tenants: [],
      setCurrentTenant: (id) => set({ currentTenantId: id }),
      setTenants: (tenants) => set({ tenants }),
    }),
    {
      name: 'tenant-storage',
    }
  )
)
```

### Feature Flags Store

```tsx
// stores/featureFlagsStore.ts
interface FeatureFlagsState {
  flags: Record<string, boolean>
  setFlags: (flags: Record<string, boolean>) => void
  isEnabled: (flag: string) => boolean
}

export const useFeatureFlags = create<FeatureFlagsState>((set, get) => ({
  flags: {},
  setFlags: (flags) => set({ flags }),
  isEnabled: (flag) => get().flags[flag] ?? false,
}))
```

### Usage

```tsx
function Component() {
  const { currentTenantId, setCurrentTenant } = useTenantStore()
  const { isEnabled } = useFeatureFlags()

  if (!isEnabled('cdp')) {
    return null
  }

  return <div>Current tenant: {currentTenantId}</div>
}
```

### Subscribing to Changes

```tsx
// Subscribe to store changes
const unsub = useTenantStore.subscribe(
  (state) => state.currentTenantId,
  (tenantId) => {
    console.log('Tenant changed:', tenantId)
  }
)
```

---

## React Context (App-Wide State)

### AuthContext

```tsx
// contexts/AuthContext.tsx
interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Check for existing session
    checkAuth().then(user => {
      setUser(user)
      setIsLoading(false)
    })
  }, [])

  const login = async (credentials: LoginCredentials) => {
    const { user, tokens } = await authApi.login(credentials)
    setUser(user)
    storeTokens(tokens)
  }

  const logout = () => {
    setUser(null)
    clearTokens()
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        refreshToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
```

### ThemeContext

```tsx
// contexts/ThemeContext.tsx
type Theme = 'light' | 'dark' | 'system'

interface ThemeContextType {
  theme: Theme
  setTheme: (theme: Theme) => void
  resolvedTheme: 'light' | 'dark'
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState<Theme>('system')

  const resolvedTheme = useMemo(() => {
    if (theme === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
    }
    return theme
  }, [theme])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', resolvedTheme === 'dark')
  }, [resolvedTheme])

  return (
    <ThemeContext.Provider value={{ theme, setTheme, resolvedTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}
```

### DemoContext

```tsx
// contexts/DemoContext.tsx
interface DemoContextType {
  isDemo: boolean
  enableDemo: () => void
  disableDemo: () => void
}

export function DemoProvider({ children }) {
  const [isDemo, setIsDemo] = useState(false)

  return (
    <DemoContext.Provider
      value={{
        isDemo,
        enableDemo: () => setIsDemo(true),
        disableDemo: () => setIsDemo(false),
      }}
    >
      {children}
    </DemoContext.Provider>
  )
}
```

---

## Local State Patterns

### useState for Simple State

```tsx
function Counter() {
  const [count, setCount] = useState(0)

  return (
    <button onClick={() => setCount(c => c + 1)}>
      Count: {count}
    </button>
  )
}
```

### useReducer for Complex State

```tsx
type State = {
  filters: Filter[]
  sort: SortOption
  page: number
}

type Action =
  | { type: 'SET_FILTERS'; filters: Filter[] }
  | { type: 'SET_SORT'; sort: SortOption }
  | { type: 'SET_PAGE'; page: number }
  | { type: 'RESET' }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET_FILTERS':
      return { ...state, filters: action.filters, page: 1 }
    case 'SET_SORT':
      return { ...state, sort: action.sort }
    case 'SET_PAGE':
      return { ...state, page: action.page }
    case 'RESET':
      return initialState
    default:
      return state
  }
}

function CampaignTable() {
  const [state, dispatch] = useReducer(reducer, initialState)
}
```

---

## State Selection Guidelines

```
┌─────────────────────────────────────────────────────────────┐
│                    When to Use What                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  TanStack Query                                             │
│  ├── Data from API                                          │
│  ├── Cached/stale data management                           │
│  └── Background refetching                                  │
│                                                             │
│  Zustand                                                    │
│  ├── User preferences (persist)                             │
│  ├── UI state shared across routes                          │
│  └── Feature flags                                          │
│                                                             │
│  React Context                                              │
│  ├── Auth state (changes infrequently)                      │
│  ├── Theme (dark/light mode)                                │
│  └── Localization                                           │
│                                                             │
│  useState/useReducer                                        │
│  ├── Form state                                             │
│  ├── Component-local UI state                               │
│  └── Temporary state (modals, selections)                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Best Practices

### 1. Avoid Prop Drilling

```tsx
// Bad: Passing props through many levels
<GrandParent data={data}>
  <Parent data={data}>
    <Child data={data} />
  </Parent>
</GrandParent>

// Good: Use context or query hooks
function Child() {
  const { data } = useCampaigns()
  return <div>{data.name}</div>
}
```

### 2. Colocate State

Keep state close to where it's used:

```tsx
// Form state stays in the form component
function CampaignForm() {
  const [formData, setFormData] = useState(initialValues)
  // ...
}
```

### 3. Derive State When Possible

```tsx
// Bad: Storing derived state
const [items, setItems] = useState([])
const [filteredItems, setFilteredItems] = useState([])

// Good: Derive from source
const [items, setItems] = useState([])
const filteredItems = useMemo(
  () => items.filter(item => item.active),
  [items]
)
```

### 4. Use Query Keys Consistently

```tsx
// Define query keys centrally
const queryKeys = {
  campaigns: {
    all: ['campaigns'] as const,
    list: (filters) => [...queryKeys.campaigns.all, filters] as const,
    detail: (id) => [...queryKeys.campaigns.all, id] as const,
  },
}
```
