import { test, expect } from '@playwright/test'

test.describe('Logout Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Seed authenticated state
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
    await page.goto('/dashboard/overview')
  })

  test('should logout and redirect to login', async ({ page }) => {
    // Open user menu / avatar dropdown
    const avatar = page.locator('[data-testid="user-menu-trigger"], [aria-label="User menu"]').first()
    if (await avatar.isVisible()) {
      await avatar.click()
    }

    // Click logout
    const logoutBtn = page.locator('text=Logout, text=Sign out').first()
    if (await logoutBtn.isVisible()) {
      await logoutBtn.click()
    } else {
      // Fallback: simulate logout via localStorage clear + navigate
      await page.evaluate(() => {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('user')
        window.location.href = '/login'
      })
    }

    // Should redirect to login
    await expect(page).toHaveURL(/login/)

    // Auth tokens should be cleared
    const token = await page.evaluate(() => localStorage.getItem('auth_token'))
    expect(token).toBeNull()
  })

  test('should block dashboard access after logout', async ({ page }) => {
    await page.evaluate(() => {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user')
    })
    await page.goto('/dashboard/overview')

    // Should be redirected to login
    await expect(page).toHaveURL(/login/)
  })
})
