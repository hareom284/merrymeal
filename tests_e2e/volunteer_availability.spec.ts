import { expect, test } from '@playwright/test';

test.describe('Volunteer availability editor (mobile 375 × 667)', () => {
  // Pre-conditions seeded out-of-band:
  //   - volunteer user `vol@example.com` / `pw12345!` with role=volunteer
  //   - the volunteer has NO existing availabilities before the test runs
  async function signInAsVolunteer(page) {
    await page.goto('/accounts/login/');
    await page.getByLabel('Email').fill('vol@example.com');
    await page.getByLabel('Password').fill('pw12345!');
    await page.getByRole('button', { name: /sign in|log in/i }).click();
  }

  test('tap a cell, reload, retap — state persists; 44px target; no horizontal scroll', async ({ page }) => {
    await signInAsVolunteer(page);
    await page.goto('/volunteer/availability/');

    const cell = page.locator('#slot-mon-morning');
    await expect(cell).toHaveAttribute('aria-pressed', 'false');

    // 44 × 44 px touch target.
    const box = await cell.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.height).toBeGreaterThanOrEqual(44);
    expect(box!.width).toBeGreaterThanOrEqual(44);

    // Tap on — HTMX swap to aria-pressed=true.
    await cell.click();
    await expect(cell).toHaveAttribute('aria-pressed', 'true');

    // Reload — server-rendered state matches.
    await page.reload();
    await expect(page.locator('#slot-mon-morning')).toHaveAttribute('aria-pressed', 'true');

    // Tap off.
    await page.locator('#slot-mon-morning').click();
    await expect(page.locator('#slot-mon-morning')).toHaveAttribute('aria-pressed', 'false');

    // No horizontal scroll at 375 px.
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(375);
  });
});
