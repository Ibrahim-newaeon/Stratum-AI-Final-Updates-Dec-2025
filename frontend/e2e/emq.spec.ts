import { test, expect } from '@playwright/test'
import { authenticate } from './utils/session'

test.describe('EMQ / Signal Hub', () => {
  test.beforeEach(async ({ page }) => {
    await authenticate(page)
    await page.goto('/app/1/signal-hub')
  })

  test('should display EMQ drivers', async ({ page }) => {
    await expect(page.locator('[data-tour="emq-drivers"]')).toBeVisible({ timeout: 15000 })
  })

  test('should show platform signals', async ({ page }) => {
    await expect(page.locator('[data-tour="platform-signals"]')).toBeVisible({ timeout: 15000 })
  })

  test('should display volatility badge', async ({ page }) => {
    await expect(page.locator('[data-tour="volatility-badge"]')).toBeVisible({ timeout: 15000 })
  })
})

test.describe('Tenant Overview (Trust)', () => {
  test.beforeEach(async ({ page }) => {
    await authenticate(page)
    await page.goto('/app/1/trust')
  })

  test('should display trust header', async ({ page }) => {
    await expect(page.locator('[data-tour="trust-header"]')).toBeVisible({ timeout: 15000 })
  })

  test('should show KPI strip', async ({ page }) => {
    await expect(page.locator('[data-tour="kpi-strip"]')).toBeVisible({ timeout: 15000 })
  })

  test('should display fix playbook', async ({ page }) => {
    await expect(page.locator('[data-tour="fix-playbook"]')).toBeVisible({ timeout: 15000 })
  })
})
