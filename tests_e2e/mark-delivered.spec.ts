/**
 * Story 4.9 — mark-delivered happy path at iPhone SE viewport.
 *
 * These tests assume a seeded "Sarah" volunteer with three pending
 * deliveries on today's route. The seed lives in the same fixture
 * loader used by Story 4.8's e2e (``volunteer_availability.spec.ts``)
 * — when that lands, swap the ``test.skip`` for the real navigation.
 */
import { test, expect } from '@playwright/test';
import path from 'path';

test.use({ viewport: { width: 375, height: 667 } });

test.describe('Mark-delivered with POD photo (375 × 667)', () => {
  test.skip(
    !process.env.E2E_SEED_VOLUNTEER_FIXTURE,
    'Requires E2E_SEED_VOLUNTEER_FIXTURE=1 + seeded sarah-three-stops.'
  );

  test('mark-delivered uploads file and advances stop', async ({ page }) => {
    await page.goto('/volunteer/today/?fixture=sarah-three-stops');
    await expect(page.getByTestId('mark-delivered-cta').first()).toBeVisible();

    const filePath = path.join(__dirname, 'fixtures', 'pod.jpg');
    const input = page.locator("input[type=file][name=photo]").first();
    await input.setInputFiles(filePath);

    // After the HTMX swap, the next stop's CTA appears.
    await expect(
      page.getByTestId('mark-delivered-cta').first()
    ).toBeVisible();
  });

  test('offline queue badge appears when network fails', async ({
    page,
    context,
  }) => {
    await page.goto('/volunteer/today/?fixture=sarah-three-stops');
    await context.setOffline(true);
    const input = page.locator("input[type=file][name=photo]").first();
    await input.setInputFiles(path.join(__dirname, 'fixtures', 'pod.jpg'));
    await expect(page.getByTestId('queue-badge')).toBeVisible();
    await expect(page.getByTestId('queue-badge')).toHaveText(/queued/);
  });
});
