# Frontend Testing

## Overview

Stratum AI frontend uses Vitest for unit/integration tests and Playwright for E2E tests.

---

## Test Stack

| Tool | Purpose |
|------|---------|
| Vitest | Unit & integration tests |
| React Testing Library | Component testing |
| Playwright | End-to-end tests |
| MSW | API mocking |

---

## Running Tests

### Unit Tests

```bash
# Run all tests
npm run test

# Watch mode
npm run test -- --watch

# Coverage report
npm run test:coverage
```

### E2E Tests

```bash
# Run E2E tests
npm run test:e2e

# With UI
npm run test:e2e:ui

# Headed mode (visible browser)
npm run test:e2e:headed

# Show report
npm run test:e2e:report
```

---

## Unit Testing

### Component Test

```tsx
// components/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { Button } from './Button'

describe('Button', () => {
  it('renders correctly', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button')).toHaveTextContent('Click me')
  })

  it('handles click', () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>Click me</Button>)

    fireEvent.click(screen.getByRole('button'))

    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('is disabled when loading', () => {
    render(<Button isLoading>Click me</Button>)
    expect(screen.getByRole('button')).toBeDisabled()
  })
})
```

### Hook Test

```tsx
// hooks/useCounter.test.ts
import { renderHook, act } from '@testing-library/react'
import { useCounter } from './useCounter'

describe('useCounter', () => {
  it('increments counter', () => {
    const { result } = renderHook(() => useCounter())

    act(() => {
      result.current.increment()
    })

    expect(result.current.count).toBe(1)
  })
})
```

### API Hook Test

```tsx
// api/campaigns.test.ts
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useCampaigns } from './campaigns'

const wrapper = ({ children }) => (
  <QueryClientProvider client={new QueryClient()}>
    {children}
  </QueryClientProvider>
)

describe('useCampaigns', () => {
  it('fetches campaigns', async () => {
    const { result } = renderHook(() => useCampaigns(), { wrapper })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data).toHaveLength(5)
  })
})
```

---

## Component Testing Patterns

### Testing User Interactions

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

it('submits form with data', async () => {
  const user = userEvent.setup()
  const onSubmit = vi.fn()

  render(<CampaignForm onSubmit={onSubmit} />)

  await user.type(screen.getByLabelText('Name'), 'Campaign A')
  await user.selectOptions(screen.getByLabelText('Platform'), 'meta')
  await user.click(screen.getByRole('button', { name: /submit/i }))

  expect(onSubmit).toHaveBeenCalledWith({
    name: 'Campaign A',
    platform: 'meta',
  })
})
```

### Testing Async Behavior

```tsx
it('shows loading then data', async () => {
  render(<CampaignList />)

  // Initially shows loading
  expect(screen.getByText('Loading...')).toBeInTheDocument()

  // Wait for data
  await waitFor(() => {
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
  })

  // Data is displayed
  expect(screen.getByText('Campaign A')).toBeInTheDocument()
})
```

### Testing Error States

```tsx
it('shows error message', async () => {
  server.use(
    rest.get('/api/campaigns', (req, res, ctx) => {
      return res(ctx.status(500))
    })
  )

  render(<CampaignList />)

  await waitFor(() => {
    expect(screen.getByRole('alert')).toHaveTextContent('Error loading campaigns')
  })
})
```

---

## Mocking

### MSW Setup

```tsx
// mocks/handlers.ts
import { rest } from 'msw'

export const handlers = [
  rest.get('/api/campaigns', (req, res, ctx) => {
    return res(
      ctx.json({
        items: [
          { id: 1, name: 'Campaign A' },
          { id: 2, name: 'Campaign B' },
        ],
      })
    )
  }),
]

// mocks/server.ts
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

export const server = setupServer(...handlers)

// vitest.setup.ts
beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

### Mocking Modules

```tsx
// Mock entire module
vi.mock('@/api/campaigns', () => ({
  useCampaigns: () => ({
    data: [{ id: 1, name: 'Mock Campaign' }],
    isLoading: false,
  }),
}))

// Mock specific function
vi.mock('@/lib/analytics', () => ({
  trackEvent: vi.fn(),
}))
```

---

## E2E Testing with Playwright

### Basic Test

```ts
// tests/login.spec.ts
import { test, expect } from '@playwright/test'

test('user can login', async ({ page }) => {
  await page.goto('/login')

  await page.fill('input[name="email"]', 'test@example.com')
  await page.fill('input[name="password"]', 'password123')
  await page.click('button[type="submit"]')

  await expect(page).toHaveURL('/dashboard')
  await expect(page.getByText('Welcome')).toBeVisible()
})
```

### Page Object Model

```ts
// tests/pages/login.page.ts
export class LoginPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/login')
  }

  async login(email: string, password: string) {
    await this.page.fill('input[name="email"]', email)
    await this.page.fill('input[name="password"]', password)
    await this.page.click('button[type="submit"]')
  }
}

// tests/login.spec.ts
test('user can login', async ({ page }) => {
  const loginPage = new LoginPage(page)

  await loginPage.goto()
  await loginPage.login('test@example.com', 'password123')

  await expect(page).toHaveURL('/dashboard')
})
```

### Testing Dashboard

```ts
test('dashboard shows metrics', async ({ page }) => {
  // Login first
  await page.goto('/login')
  await page.fill('input[name="email"]', 'test@example.com')
  await page.fill('input[name="password"]', 'password123')
  await page.click('button[type="submit"]')

  // Navigate to dashboard
  await page.goto('/dashboard')

  // Check metrics are visible
  await expect(page.getByTestId('total-spend')).toBeVisible()
  await expect(page.getByTestId('total-revenue')).toBeVisible()
  await expect(page.getByTestId('roas')).toBeVisible()
})
```

### Visual Regression

```ts
test('dashboard matches snapshot', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(page).toHaveScreenshot('dashboard.png')
})
```

---

## Test Configuration

### Vitest Config

```ts
// vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['node_modules', 'tests'],
    },
  },
})
```

### Playwright Config

```ts
// playwright.config.ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
})
```

---

## Best Practices

### 1. Test Behavior, Not Implementation

```tsx
// Bad - tests implementation
expect(component.state.isOpen).toBe(true)

// Good - tests behavior
expect(screen.getByRole('dialog')).toBeVisible()
```

### 2. Use Accessible Queries

```tsx
// Priority order:
screen.getByRole('button', { name: 'Submit' })  // Best
screen.getByLabelText('Email')                   // Good
screen.getByText('Click here')                   // OK
screen.getByTestId('submit-btn')                 // Last resort
```

### 3. Avoid Testing Library Internals

```tsx
// Don't test React/library code
// Test YOUR component's behavior
```

### 4. Keep Tests Isolated

```tsx
beforeEach(() => {
  // Reset state between tests
  queryClient.clear()
})
```

---

## Coverage Targets

| Category | Target |
|----------|--------|
| Components | 80% |
| Hooks | 90% |
| Utils | 95% |
| Overall | 80% |
