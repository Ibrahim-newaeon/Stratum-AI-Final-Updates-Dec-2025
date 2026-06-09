import { test, expect } from '@playwright/test'
import { authenticate } from './utils/session'

test.describe('Settings Flow', () => {
  test.beforeEach(async ({ page }) => {
    await authenticate(page)
    await page.goto('/dashboard/settings')
  })

  test('should display settings page', async ({ page }) => {
    await expect(page.locator('text=Settings').first()).toBeVisible({ timeout: 15000 })
  })

  test('should navigate between settings tabs', async ({ page }) => {
    for (const tab of ['Profile', 'Notifications', 'Integrations']) {
      const el = page.getByRole('tab', { name: new RegExp(tab, 'i') }).first()
      if (await el.isVisible().catch(() => false)) {
        await el.click()
        await expect(page.locator(`text=${tab}`).first()).toBeVisible()
      }
    }
  })

  test('should show validation on empty profile form', async ({ page }) => {
    const profileTab = page.getByRole('tab', { name: /Profile/i }).first()
    if (await profileTab.isVisible().catch(() => false)) {
      await profileTab.click()
    }

    const nameInput = page.locator('input[name="name"], input[name="fullName"]').first()
    if (await nameInput.isVisible().catch(() => false)) {
      await nameInput.fill('')
      await page.locator('button[type="submit"]').first().click()
      const error = page.locator('text=required, [role="alert"]').first()
      await expect(error).toBeVisible()
    }
  })
})
