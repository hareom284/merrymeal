/**
 * Story 4.11 — 2-tap meal feedback prompt at iPhone SE viewport.
 *
 * These tests assume a seeded "Margaret" member whose today delivery
 * has already flipped to ``delivered`` (status check is the gate that
 * makes the prompt render). The fixture seeder isn't wired up yet
 * (see Story 4.8/4.9/4.10's specs for the same skip pattern); flip
 * ``E2E_SEED_MEMBER_FIXTURE`` on once the seed lands.
 */
import { test, expect } from '@playwright/test';

test.use({ viewport: { width: 375, height: 667 } });

test.describe("2-tap feedback prompt (375 × 667)", () => {
  test.skip(
    !process.env.E2E_SEED_MEMBER_FIXTURE,
    'Requires E2E_SEED_MEMBER_FIXTURE=1 + seeded margaret-just-delivered.'
  );

  test("2-tap feedback at 375x667", async ({ page }) => {
    await page.goto("/?fixture=margaret-just-delivered");

    const card = page.getByTestId("feedback-card");
    await expect(card).toBeVisible();

    // No horizontal scrollbar — the card must fit the 375 px viewport.
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > 375
    );
    expect(overflow).toBe(false);

    // Stars and chips each ≥ 44 px tall — thumb-friendly. The visible
    // glyph can be smaller (36 px star, e.g.) but the wrapping
    // ``<label>`` must hit the WCAG target.
    for (const tid of ["star", "tag-chip"]) {
      const els = page.getByTestId(tid);
      const count = await els.count();
      expect(count).toBeGreaterThan(0);
      for (let i = 0; i < count; i++) {
        const box = await els.nth(i).boundingBox();
        expect(box!.height).toBeGreaterThanOrEqual(44);
      }
    }

    // Two taps: 4th star + "Loved it" chip → submit.
    await page.locator("input[name=rating][value='4']").check({ force: true });
    await page
      .locator("input[name=tags][value=loved_it]")
      .check({ force: true });
    await page.getByTestId("feedback-submit").click();

    await expect(page.getByTestId("feedback-thanks")).toBeVisible();
  });
});
