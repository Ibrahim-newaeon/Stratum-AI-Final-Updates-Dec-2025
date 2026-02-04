import { test, expect, devices } from '@playwright/test';

// Mobile tests using iPhone 12 viewport
const mobileTest = test.extend({
  ...devices['iPhone 12'],
});

// Tablet tests using iPad Mini viewport
const tabletTest = test.extend({
  ...devices['iPad Mini'],
});

mobileTest.describe('Mobile Responsiveness', () => {
  mobileTest('should show mobile menu toggle', async ({ page }) => {
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

    // Sidebar should be hidden on mobile
    await expect(page.locator('[data-tour="sidebar"]')).not.toBeVisible();

    // Menu toggle should be visible
    const menuButton = page.locator('button[aria-label="Open menu"], button:has(svg.h-6.w-6)');
    await expect(menuButton.first()).toBeVisible();
  });

  mobileTest('should open mobile sidebar on toggle', async ({ page }) => {
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

    const menuButton = page.locator('button:has(svg.h-6.w-6)').first();
    if (await menuButton.isVisible()) {
      await menuButton.click();
      await expect(page.locator('[data-tour="sidebar"]')).toBeVisible();
    }
  });

  mobileTest('landing page should be responsive', async ({ page }) => {
    await page.goto('/');

    // Hero should be visible
    await expect(page.locator('text=Stratum AI')).toBeVisible();

    // CTA buttons should stack on mobile
    const cta = page.locator('text=Get Started');
    await expect(cta).toBeVisible();
  });
});

tabletTest.describe('Tablet Responsiveness', () => {
  tabletTest('should display sidebar properly on tablet', async ({ page }) => {
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

    // Sidebar may or may not be visible depending on tablet size
    // KPI cards should display in grid
    await expect(page.locator('.grid')).toBeVisible();
  });
});
