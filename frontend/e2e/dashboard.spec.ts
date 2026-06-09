import { test, expect } from '@playwright/test'
import { authenticate } from './utils/session'

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await authenticate(page)
    await page.goto('/dashboard/overview')
  })

  test('should display dashboard overview', async ({ page }) => {
    await expect(page.locator('text=Overview').first()).toBeVisible({ timeout: 15000 })
  })

  test('should show sidebar navigation', async ({ page }) => {
    await expect(page.locator('aside[aria-label="Primary navigation"]')).toBeVisible()
    await expect(page.getByRole('link', { name: /^Campaigns$/i }).first()).toBeVisible()
    await expect(page.getByRole('link', { name: /^Settings$/i }).first()).toBeVisible()
  })

  test('should navigate between pages', async ({ page }) => {
    await page.getByRole('link', { name: /^Campaigns$/i }).first().click()
    await expect(page).toHaveURL(/campaigns/)

    await page.getByRole('link', { name: /^Settings$/i }).first().click()
    await expect(page).toHaveURL(/settings/)
  })

  test('should toggle theme', async ({ page }) => {
    const themeToggle = page.locator('[aria-label*="theme" i], [aria-label*="Dark" i], [aria-label*="Light" i]').first()
    if (await themeToggle.isVisible().catch(() => false)) {
      await themeToggle.click()
      await expect(page.locator('html')).toHaveAttribute('class', /dark|light/)
    }
  })
})
