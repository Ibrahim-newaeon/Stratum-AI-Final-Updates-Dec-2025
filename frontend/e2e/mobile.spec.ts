import { test, expect } from '@playwright/test'
import { authenticate } from './utils/session'

// Use explicit viewports (not full device descriptors) so we stay on the
// --project browser instead of forcing webkit via defaultBrowserType.
test.describe('Mobile Responsiveness', () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })

  test('should show mobile menu toggle', async ({ page }) => {
    await authenticate(page)
    await page.goto('/dashboard/overview')
    // The sidebar is collapsed on mobile; an "Open navigation" toggle appears.
    await expect(page.locator('button[aria-label="Open navigation"]')).toBeVisible({
      timeout: 15000,
    })
  })

  test('should open mobile sidebar on toggle', async ({ page }) => {
    await authenticate(page)
    await page.goto('/dashboard/overview')
    const toggle = page.locator('button[aria-label="Open navigation"]')
    await toggle.click()
    await expect(page.locator('aside[aria-label="Primary navigation"]')).toBeVisible()
  })

  test('landing page should be responsive', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('text=Stratum AI').first()).toBeVisible()
    await expect(page.getByRole('button', { name: /Start Free/i }).first()).toBeVisible()
  })
})

test.describe('Tablet Responsiveness', () => {
  test.use({ viewport: { width: 768, height: 1024 } })

  test('should display dashboard on tablet', async ({ page }) => {
    await authenticate(page)
    await page.goto('/dashboard/overview')
    await expect(page.locator('text=Overview').first()).toBeVisible({ timeout: 15000 })
  })
})
