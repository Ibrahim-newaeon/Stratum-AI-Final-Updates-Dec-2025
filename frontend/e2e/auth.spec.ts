import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should display landing page', async ({ page }) => {
    await expect(page.locator('text=Stratum AI').first()).toBeVisible()
    await expect(page.getByRole('button', { name: /Start Free/i }).first()).toBeVisible()
  })

  test('should navigate to login page', async ({ page }) => {
    await page.getByRole('link', { name: /Sign In/i }).first().click()
    await expect(page).toHaveURL(/\/login$/)
    await expect(page.locator('input[type="email"]')).toBeVisible()
  })

  test('should navigate to signup page', async ({ page }) => {
    await page.getByRole('button', { name: /Start Free/i }).first().click()
    await expect(page).toHaveURL(/\/signup$/)
    await expect(page.getByRole('heading', { name: /Start in under a minute/i })).toBeVisible()
  })

  test('should require email and password on empty login', async ({ page }) => {
    await page.goto('/login')
    await page.locator('button[type="submit"]').click()
    // Required-field validation keeps us on /login rather than submitting.
    await expect(page).toHaveURL(/\/login$/)
    await expect(page.locator('input[type="email"]')).toBeVisible()
  })

  test('should navigate to forgot password', async ({ page }) => {
    await page.goto('/login')
    await page.getByRole('link', { name: /Forgot/i }).first().click()
    await expect(page).toHaveURL(/\/forgot-password$/)
  })
})
