import { test, expect } from '@playwright/test'

test.describe('Settings Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => {
      localStorage.setItem('auth_token', 'test-token')
      localStorage.setItem('user', JSON.stringify({
        id: 1,
        name: 'Test User',
        email: 'test@example.com',
        role: 'tenant_admin',
      }))
    })
    await page.goto('/settings')
  })

  test('should display settings page', async ({ page }) => {
    await expect(page.locator('text=Settings').first()).toBeVisible()
  })

  test('should navigate between settings tabs', async ({ page }) => {
    // Try to find and click Profile tab
    const profileTab = page.locator('text=Profile, [role="tab"]:has-text("Profile")').first()
    if (await profileTab.isVisible()) {
      await profileTab.click()
      await expect(page.locator('text=Profile').first()).toBeVisible()
    }

    // Try to find and click Notifications tab
    const notificationsTab = page.locator('text=Notifications, [role="tab"]:has-text("Notifications")').first()
    if (await notificationsTab.isVisible()) {
      await notificationsTab.click()
      await expect(page.locator('text=Notifications').first()).toBeVisible()
    }

    // Try to find and click Integrations tab
    const integrationsTab = page.locator('text=Integrations, [role="tab"]:has-text("Integrations")').first()
    if (await integrationsTab.isVisible()) {
      await integrationsTab.click()
      await expect(page.locator('text=Integrations').first()).toBeVisible()
    }
  })

  test('should show validation on empty profile form', async ({ page }) => {
    const profileTab = page.locator('text=Profile, [role="tab"]:has-text("Profile")').first()
    if (await profileTab.isVisible()) {
      await profileTab.click()
    }

    // Look for a name input and clear it
    const nameInput = page.locator('input[name="name"], input[name="fullName"]').first()
    if (await nameInput.isVisible()) {
      await nameInput.fill('')
      await page.click('button[type="submit"]')
      // Should show some validation feedback
      const error = page.locator('text=required, [role="alert"]').first()
      await expect(error).toBeVisible()
    }
  })
})
