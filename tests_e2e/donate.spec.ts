/**
 * Story 5.3 — public donate page at iPhone SE viewport (375 x 667 px).
 *
 * These tests assume a seeded "general-fund" Campaign exists (Admin/Ops
 * track in this sprint ships the data migration). The fixture isn't wired
 * up in the CI runner yet — same skip pattern as ``mark-failed.spec.ts``
 * and the Sprint 08 e2e specs. Flip ``E2E_SEED_DONATE_FIXTURE=1`` once the
 * seed and a running dev server are available.
 *
 * What we assert:
 * - No horizontal scrollbar at 375 px (chip grid must fit).
 * - Donate CTA is at least 48 px tall (Apple HIG touch target).
 * - Amount chips are at least 44 px tall (minimum tap target).
 * - Hero shows "General fund" when no ``?campaign=`` is supplied.
 *
 * Apple Pay / Google Pay surfaces are delegated to Stripe Checkout —
 * covered by manual verification in Story 5.4, not here.
 */
import { test, expect } from '@playwright/test';

test.use({ viewport: { width: 375, height: 667 } });

test.describe('Public donate page (375 x 667)', () => {
  test.skip(
    !process.env.E2E_SEED_DONATE_FIXTURE,
    'Requires E2E_SEED_DONATE_FIXTURE=1 + seeded general-fund campaign.'
  );

  test('donate page is mobile-friendly at 375 px', async ({ page }) => {
    await page.goto('/donate/');

    await expect(
      page.getByRole('heading', { name: /general fund/i })
    ).toBeVisible();

    // No horizontal scrollbar — chip grid + custom input must fit.
    const docWidth = await page.evaluate(
      () => document.documentElement.scrollWidth
    );
    expect(docWidth).toBeLessThanOrEqual(375);

    // CTA touch target (Apple HIG: 44 pt minimum; we go 48 px to match
    // the spec — see ``.btn-primary`` in static/src/input.css).
    const cta = page.getByRole('button', { name: 'Donate' });
    const ctaBox = await cta.boundingBox();
    expect(ctaBox).not.toBeNull();
    expect(ctaBox!.height).toBeGreaterThanOrEqual(48);

    // Chip touch target.
    const chip = page.getByRole('button', { name: '$50' });
    const chipBox = await chip.boundingBox();
    expect(chipBox).not.toBeNull();
    expect(chipBox!.height).toBeGreaterThanOrEqual(44);
  });

  test('cancelled toast renders when ?cancelled=1', async ({ page }) => {
    await page.goto('/donate/?cancelled=1');
    await expect(page.getByText(/cancelled/i)).toBeVisible();
  });
});
