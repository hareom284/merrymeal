import { expect, test } from '@playwright/test';

test.describe('admin weekly planner', () => {
  // Story 3.3 — target viewport is 1280 × 800 (desktop primary).
  test.use({ viewport: { width: 1280, height: 800 } });

  // Pre-conditions seeded out-of-band:
  //  - admin user `ops@merrymeal.test` / `pw` with role=admin
  //  - at least one Kitchen and one active Meal in the database
  async function signIn(page) {
    await page.goto('/accounts/login/');
    await page.getByLabel('Email').fill('ops@merrymeal.test');
    await page.getByLabel('Password').fill('pw');
    await page.getByRole('button', { name: /sign in|log in/i }).click();
  }

  test('admin sees a 7-day grid and at least one kitchen row', async ({ page }) => {
    await signIn(page);
    await page.goto('/admin/planner/');

    await expect(page.getByRole('heading', { name: /Weekly planner/i })).toBeVisible();

    // 7 day-headers (Mon–Sun).
    const headers = page.locator('table.planner-grid thead th[scope="col"]');
    // 1 "Kitchen" column header + 7 day-headers = 8.
    await expect(headers).toHaveCount(8);

    // At least one kitchen row.
    const kitchenRows = page.locator('table.planner-grid tbody tr');
    expect(await kitchenRows.count()).toBeGreaterThanOrEqual(1);
  });

  test('admin sets a meal in an empty cell via the HTMX modal', async ({ page }) => {
    await signIn(page);
    await page.goto('/admin/planner/');

    // Click the first "Set meal" button (any empty cell).
    const setMealButton = page.getByRole('button', { name: /Set meal/i }).first();
    await setMealButton.click();

    // Modal appears with the meal <select> and a planned_quantity input.
    const modal = page.locator('#modal');
    await expect(modal.locator('form')).toBeVisible();

    // Select the first non-empty option in the meal dropdown.
    const select = modal.locator('select[name="meal"]');
    const options = await select.locator('option').all();
    let chosenLabel = '';
    for (const opt of options) {
      const val = await opt.getAttribute('value');
      if (val) {
        chosenLabel = (await opt.textContent()) ?? '';
        await select.selectOption(val);
        break;
      }
    }
    expect(chosenLabel.trim().length).toBeGreaterThan(0);

    await modal.locator('input[name="planned_quantity"]').fill('30');
    await modal.getByRole('button', { name: /Save/i }).click();

    // The cell now shows the chosen meal's name.
    await expect(page.locator('table.planner-grid')).toContainText(chosenLabel.trim());
  });
});
