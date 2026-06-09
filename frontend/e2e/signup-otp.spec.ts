import { test, expect, Page } from '@playwright/test'

test.describe('Signup with WhatsApp OTP', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/v1/auth/whatsapp/send-otp', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { message: 'Verification code sent to your WhatsApp', expires_in: 300 },
          message: 'OTP sent successfully',
        }),
      })
    })

    await page.route('**/api/v1/auth/whatsapp/verify-otp', async (route) => {
      const body = route.request().postDataJSON()
      if (body?.otp_code === '123456') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { verified: true, verification_token: 'test-verification-token-12345' },
            message: 'Phone number verified successfully',
          }),
        })
      } else {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ success: false, detail: 'Invalid OTP code. Please try again.' }),
        })
      }
    })

    await page.route('**/api/v1/auth/register', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 1,
            email: 'test@example.com',
            full_name: 'Test User',
            role: 'user',
            is_active: true,
            is_verified: false,
          },
          message: 'Registration successful',
        }),
      })
    })

    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Not authenticated' }),
      })
    })
  })

  async function fillRegistration(page: Page, phone = '+12025550143') {
    await page.fill('input[name="name"]', 'Test User')
    await page.fill('input[name="email"]', 'test@example.com')
    await page.fill('input[name="phone"]', phone)
    await page.fill('input[name="password"]', 'Password123!')
    await page.fill('input[name="confirmPassword"]', 'Password123!')
    await page.locator('input#terms').check()
    await page.locator('button[type="submit"]').click()
  }

  // Step 2 is a method chooser ("Verify your identity"); pick WhatsApp to reach
  // the code-entry step ("Check your WhatsApp").
  async function chooseWhatsApp(page: Page) {
    await expect(page.getByText('Verify your identity')).toBeVisible({ timeout: 10000 })
    await page.getByRole('button', { name: /Verify via WhatsApp/i }).click()
    await expect(page.getByText(/Check your WhatsApp/i)).toBeVisible({ timeout: 10000 })
  }

  test('should display signup form with phone field', async ({ page }) => {
    await page.goto('/signup')
    await expect(page.locator('input[name="name"]')).toBeVisible()
    await expect(page.locator('input[name="email"]')).toBeVisible()
    await expect(page.locator('input[name="phone"]')).toBeVisible()
    await expect(page.locator('input[name="password"]')).toBeVisible()
    await expect(page.locator('input[name="confirmPassword"]')).toBeVisible()
  })

  test('should require fields before advancing', async ({ page }) => {
    await page.goto('/signup')
    // Submitting the empty form must not advance to the verification step.
    await page.locator('button[type="submit"]').click()
    await expect(page.getByText('Verify your identity')).not.toBeVisible()
    await expect(page).toHaveURL(/\/signup$/)
    await expect(page.locator('input[name="phone"]')).toBeVisible()
  })

  test('should proceed to OTP verification step', async ({ page }) => {
    await page.goto('/signup')
    await fillRegistration(page)
    await chooseWhatsApp(page)
    await expect(page.locator('input[maxlength="6"]')).toBeVisible({ timeout: 10000 })
  })

  test('should verify OTP and complete signup', async ({ page }) => {
    await page.goto('/signup')
    await page.waitForLoadState('networkidle')
    await fillRegistration(page)
    await chooseWhatsApp(page)

    await page.locator('input[maxlength="6"]').fill('123456')
    await page.getByRole('button', { name: /Verify & activate/i }).click()

    await expect(
      page
        .getByText(/Verifying/i)
        .or(page.getByText(/Account Created/i))
        .or(page.getByText(/successful/i))
        .or(page.getByText(/Welcome/i))
    ).toBeVisible({ timeout: 15000 })
  })

  test('should show error for invalid OTP', async ({ page }) => {
    await page.goto('/signup')
    await fillRegistration(page)
    await chooseWhatsApp(page)

    await page.locator('input[maxlength="6"]').fill('999999')
    await page.getByRole('button', { name: /Verify & activate/i }).click()

    // The verify call returns 400; the form surfaces the request error.
    await expect(
      page
        .getByText(/Invalid/i)
        .or(page.getByText(/failed/i))
        .or(page.getByText(/400/))
        .or(page.locator('[role="alert"]'))
    ).toBeVisible({ timeout: 10000 })
  })

  test('should show resend OTP countdown', async ({ page }) => {
    await page.goto('/signup')
    await fillRegistration(page)
    await chooseWhatsApp(page)
    await expect(page.getByText(/Resend in/i)).toBeVisible({ timeout: 5000 })
  })
})
