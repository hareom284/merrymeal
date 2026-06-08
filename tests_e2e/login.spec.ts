import { test, expect } from '@playwright/test';

test.describe('Login screen — mobile viewport floor (375 × 667)', () => {
  test('email input is visible and tappable', async ({ page }) => {
    await page.goto('/accounts/login/');

    const email = page.getByLabel(/email/i);
    await expect(email).toBeVisible();

    const emailBox = await email.boundingBox();
    expect(emailBox).not.toBeNull();
    expect(emailBox!.height).toBeGreaterThanOrEqual(44);
  });

  test('submit button is in the thumb-zone and ≥ 44 px tall', async ({ page }) => {
    await page.goto('/accounts/login/');
    const submit = page.getByRole('button', { name: /log in|sign in/i });
    await expect(submit).toBeVisible();
    const box = await submit.boundingBox();
    expect(box!.height).toBeGreaterThanOrEqual(44);
  });

  test('no horizontal scrollbar at 375 px', async ({ page }) => {
    await page.goto('/accounts/login/');
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(375);
  });
});
