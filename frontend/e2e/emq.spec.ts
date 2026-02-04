import { test, expect } from '@playwright/test';

test.describe('EMQ Dashboard', () => {
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
    await page.goto('/dashboard/emq-dashboard');
  });

  test('should display EMQ score', async ({ page }) => {
    // Wait for EMQ score to load
    await expect(page.locator('text=EMQ Score')).toBeVisible({ timeout: 10000 });
  });

  test('should show confidence band', async ({ page }) => {
    await expect(
      page.locator('[data-tour="confidence-band"], text=/Reliable|Directional|Unsafe/')
    ).toBeVisible({ timeout: 10000 });
  });

  test('should display driver breakdown', async ({ page }) => {
    await expect(page.locator('text=/Freshness|Data Loss|Variance|Errors/')).toBeVisible({
      timeout: 10000,
    });
  });
});

test.describe('Tenant Overview', () => {
  test.beforeEach(async ({ page }) => {
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
    await page.goto('/app/1/overview');
  });

  test('should display trust header', async ({ page }) => {
    await expect(page.locator('[data-tour="trust-header"]')).toBeVisible({ timeout: 10000 });
  });

  test('should show KPI strip', async ({ page }) => {
    await expect(page.locator('[data-tour="kpi-strip"]')).toBeVisible({ timeout: 10000 });
  });

  test('should display fix playbook', async ({ page }) => {
    await expect(page.locator('[data-tour="fix-playbook"]')).toBeVisible({ timeout: 10000 });
  });
});
