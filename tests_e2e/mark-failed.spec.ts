/**
 * Story 4.10 — mark-failed bottom-sheet flow at iPhone SE viewport.
 *
 * These tests assume a seeded "Sarah" volunteer with three pending
 * deliveries on today's route — the same fixture Story 4.9's e2e
 * uses. The fixture seeder isn't wired up yet (see Story 4.8's e2e
 * for the same skip pattern); flip ``E2E_SEED_VOLUNTEER_FIXTURE`` on
 * once the seed lands.
 */
import { test, expect } from '@playwright/test';

test.use({ viewport: { width: 375, height: 667 } });

test.describe("Mark-failed bottom sheet (375 × 667)", () => {
  test.skip(
    !process.env.E2E_SEED_VOLUNTEER_FIXTURE,
    'Requires E2E_SEED_VOLUNTEER_FIXTURE=1 + seeded sarah-three-stops.'
  );

  test("mark-failed flow at 375x667", async ({ page }) => {
    await page.goto("/volunteer/today/?fixture=sarah-three-stops");

    // "Couldn't deliver" link is visually secondary — a small text link
    // under the primary CTA, NOT a competing button.
    const link = page.getByTestId("couldnt-deliver-link");
    await expect(link).toBeVisible();
    const fontSize = await link.evaluate(
      (el) => parseFloat(getComputedStyle(el).fontSize)
    );
    expect(fontSize).toBeLessThanOrEqual(18);

    await link.click();

    // Bottom sheet appears; viewport must not gain a horizontal scrollbar.
    const sheet = page.getByTestId("fail-sheet");
    await expect(sheet).toBeVisible();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > 375
    );
    expect(overflow).toBe(false);

    // Each chip is at least 44 px tall — thumb-friendly.
    const chips = page.getByTestId("reason-chip");
    const count = await chips.count();
    for (let i = 0; i < count; i++) {
      const box = await chips.nth(i).boundingBox();
      expect(box!.height).toBeGreaterThanOrEqual(44);
    }

    // Submit
    await page
      .locator("input[name=reason][value=no_answer]")
      .check({ force: true });
    await page.locator("textarea[name=notes]").fill("rang twice");
    await page.getByTestId("fail-submit").click();

    // Failed stop is replaced; next stop becomes current.
    await expect(page.getByText(/Mark .+ delivered/)).toBeVisible();
  });
});
