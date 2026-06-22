import { test, expect } from '@playwright/test';

test.describe('App Core Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Mock all API calls
    await page.route('**/api/**', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] }),
      });
    });
    await page.goto('/');
  });

  test('page loads with sidebar and logo', async ({ page }) => {
    await expect(page.locator('[data-testid="sidebar"]')).toBeVisible();
    await expect(page.locator('text=太极AGI')).toBeVisible();
  });

  test('panel switching works', async ({ page }) => {
    // Click different sidebar icons and verify main area updates
    await page.click('[data-testid="nav-chat"]');
    await expect(page.locator('[data-testid="main-content"]')).toBeVisible();
    
    await page.click('[data-testid="nav-dashboard"]');
    await expect(page.locator('[data-testid="main-content"]')).toBeVisible();
  });

  test('chat panel has input', async ({ page }) => {
    await page.click('[data-testid="nav-chat"]');
    await expect(page.locator('textarea')).toBeVisible();
  });

  test('API key modal can be opened and closed', async ({ page }) => {
    await page.click('[data-testid="nav-settings"]');
    await expect(page.locator('text=API Key')).toBeVisible();
    await page.keyboard.press('Escape');
  });
});
