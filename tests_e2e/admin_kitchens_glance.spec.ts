import { expect, test } from '@playwright/test';

test.describe('admin kitchens at-a-glance', () => {
  test.use({ viewport: { width: 1024, height: 800 } });

  test('admin sees a card per kitchen with three metric tiles', async ({ page }) => {
    // Pre-conditions seeded out-of-band:
    //  - admin user `ops@merrymeal.test` / `pw`
    //  - at least one Kitchen named `Footscray`
    //  - at least one IngredientBatch expiring within 3 days at that kitchen
    await page.goto('/accounts/login/');
    await page.getByLabel('Email').fill('ops@merrymeal.test');
    await page.getByLabel('Password').fill('pw');
    await page.getByRole('button', { name: /sign in|log in/i }).click();

    await page.goto('/admin/kitchens/');
    await expect(page.getByRole('heading', { name: /Kitchens — today at a glance/i })).toBeVisible();

    const card = page.locator('article', { hasText: 'Footscray' });
    await expect(card).toBeVisible();
    await expect(card.getByText('Expiring ≤ 3 days')).toBeVisible();
    await expect(card.getByText(/Pass-rate \(24 h\)/)).toBeVisible();
    await expect(card.getByText('Last failure')).toBeVisible();
  });

  test('clicking the expiring tile navigates to a filtered list', async ({ page }) => {
    await page.goto('/accounts/login/');
    await page.getByLabel('Email').fill('ops@merrymeal.test');
    await page.getByLabel('Password').fill('pw');
    await page.getByRole('button', { name: /sign in|log in/i }).click();

    await page.goto('/admin/kitchens/');
    const card = page.locator('article', { hasText: 'Footscray' });
    await card.getByText('Expiring ≤ 3 days').click();
    await expect(page).toHaveURL(/kitchen/);
  });
});
