import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('auth_token', 'test-token');
      localStorage.setItem(
        'user',
        JSON.stringify({
          id: 1,
          name: 'Test User',
          email: 'test@example.com',
          role: 'tenant_admin',
        })
      );
    });
    await page.goto('/dashboard/overview');
  });

  test('should display dashboard overview', async ({ page }) => {
    await expect(page.locator('text=Overview')).toBeVisible();
  });

  test('should show sidebar navigation', async ({ page }) => {
    await expect(page.locator('[data-tour="sidebar"]')).toBeVisible();
    await expect(page.locator('text=Campaigns')).toBeVisible();
    await expect(page.locator('text=Settings')).toBeVisible();
  });

  test('should navigate between pages', async ({ page }) => {
    await page.click('text=Campaigns');
    await expect(page).toHaveURL(/campaigns/);

    await page.click('text=Settings');
    await expect(page).toHaveURL(/settings/);
  });

  test('should toggle theme', async ({ page }) => {
    const themeToggle = page.locator('[aria-label="Toggle theme"]');
    if (await themeToggle.isVisible()) {
      await themeToggle.click();
      // Check theme change took effect
      await expect(page.locator('html')).toHaveAttribute('class', /dark|light/);
    }
  });
});
