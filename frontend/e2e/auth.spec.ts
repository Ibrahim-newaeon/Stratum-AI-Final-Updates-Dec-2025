import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display landing page', async ({ page }) => {
    await expect(page.locator('text=Stratum AI').first()).toBeVisible();
    await expect(page.locator('text=Get Started').first()).toBeVisible();
  });

  test('should navigate to login page', async ({ page }) => {
    await page.click('text=Login');
    await expect(page).toHaveURL('/login');
    await expect(page.locator('input[type="email"]')).toBeVisible();
  });

  test('should navigate to signup page', async ({ page }) => {
    await page.click('text=Get Started');
    await expect(page).toHaveURL('/signup');
    await expect(page.locator('text=Create your account')).toBeVisible();
  });

  test('should show validation errors on empty login', async ({ page }) => {
    await page.goto('/login');
    await page.click('button[type="submit"]');
    await expect(page.locator('text=Email is required')).toBeVisible();
  });

  test('should navigate to forgot password', async ({ page }) => {
    await page.goto('/login');
    await page.click('text=Forgot password');
    await expect(page).toHaveURL('/forgot-password');
  });
});
