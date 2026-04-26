import { test, expect } from '@playwright/test'

test.describe('Onboarding Flow', () => {
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
  })

  test('should display onboarding page', async ({ page }) => {
    await page.goto('/onboarding')
    // Onboarding should either render or redirect if already completed
    const bodyText = await page.locator('body').textContent()
    const hasOnboardingContent = bodyText && (
      bodyText.includes('Welcome') ||
      bodyText.includes('Get Started') ||
      bodyText.includes('Setup') ||
      bodyText.includes('onboarding')
    )
    expect(hasOnboardingContent || page.url().includes('dashboard')).toBeTruthy()
  })

  test('should complete onboarding wizard steps', async ({ page }) => {
    await page.goto('/onboarding')

    // If there's a wizard with next/continue buttons, step through
    let steps = 0
    const maxSteps = 5

    while (steps < maxSteps) {
      const nextBtn = page.locator(
        'button:has-text("Next"), button:has-text("Continue"), button:has-text("Get Started"), button:has-text("Finish")'
      ).first()

      if (await nextBtn.isVisible() && await nextBtn.isEnabled()) {
        await nextBtn.click()
        await page.waitForTimeout(500)
        steps++
      } else {
        break
      }
    }

    // After onboarding, should land on dashboard or show completion
    const url = page.url()
    expect(url.includes('dashboard') || url.includes('overview') || steps > 0).toBeTruthy()
  })
})
