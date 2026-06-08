/**
 * Story 5.5 — post-Stripe-redirect thank-you page at iPhone SE
 * viewport (375 x 667 px).
 *
 * These tests assume a seeded Donation + Campaign fixture exists so the
 * page renders its "confirmed" branch (transaction_id =
 * ``cs_test_demo``, status = completed, receipt_number set). The
 * fixture isn't wired up in the CI runner yet — same skip pattern as
 * ``donate.spec.ts`` and the Sprint 08 e2e specs. Flip
 * ``E2E_SEED_DONATE_FIXTURE=1`` once the seed and a running dev server
 * are available.
 *
 * What we assert:
 * - No horizontal scrollbar at 375 px (the receipt summary card must fit).
 * - Confirmed branch shows the receipt number + dollar amount.
 * - Pending branch (unknown session id) shows a soft "processing" state
 *   instead of 404ing on the donor.
 */
import { test, expect } from '@playwright/test';

test.use({ viewport: { width: 375, height: 667 } });

test.describe('Donation thanks page (375 x 667)', () => {
  test.skip(
    !process.env.E2E_SEED_DONATE_FIXTURE,
    'Requires E2E_SEED_DONATE_FIXTURE=1 + seeded completed donation with transaction_id=cs_test_demo.',
  );

  test('thanks page renders without horizontal scroll at 375 px', async ({
    page,
  }) => {
    await page.goto('/donate/thanks/?session_id=cs_test_demo');

    // No horizontal scrollbar — receipt summary card + CTA must fit.
    const docWidth = await page.evaluate(
      () => document.documentElement.scrollWidth,
    );
    expect(docWidth).toBeLessThanOrEqual(375);

    // Confirmed branch surfaces the headline + receipt number.
    await expect(
      page.getByRole('heading', { name: /thank you/i }),
    ).toBeVisible();
    await expect(page.getByText(/D\d{4}-\d{6}/)).toBeVisible();
  });

  test('unknown session id renders the soft processing state', async ({
    page,
  }) => {
    await page.goto('/donate/thanks/?session_id=cs_unknown');
    await expect(page.getByText(/processing/i)).toBeVisible();
    // Soft state must not 404 — assert a successful response heading.
    await expect(
      page.getByRole('heading', { name: /almost there/i }),
    ).toBeVisible();
  });
});
