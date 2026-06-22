import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/**', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    });
    await page.goto('/');
  });

  test('sidebar navigation areas are visible', async ({ page }) => {
    await expect(page.locator('[data-testid="sidebar-core"]')).toBeVisible();
    await expect(page.locator('[data-testid="sidebar-monitor"]')).toBeVisible();
  });

  test('panel switch does not produce console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    await page.click('[data-testid="nav-chat"]');
    await page.waitForTimeout(500);
    await page.click('[data-testid="nav-dashboard"]');
    await page.waitForTimeout(500);

    // Filter out network errors (expected in mock mode)
    const nonNetworkErrors = errors.filter(e => !e.includes('Failed to load') && !e.includes('net::ERR'));
    expect(nonNetworkErrors.length).toBe(0);
  });

  test('sidebar highlights active panel', async ({ page }) => {
    await page.click('[data-testid="nav-chat"]');
    await expect(page.locator('[data-testid="nav-chat"].bg-sidebarActive')).toBeVisible();
  });
});
