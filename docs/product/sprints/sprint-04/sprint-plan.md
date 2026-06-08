# Sprint 04 — Kitchen, ingredients, meals

**Weeks:** 7–8
**Primary epic:** [02 — Kitchen & inventory backbone](../../epics/02-kitchen-inventory.md)
**Sprint goal:** every model needed to describe a kitchen, its ingredients, and the dishes it can cook is in the DB. Kitchen staff can record a stock receipt from a tablet.

---

## Stories pulled

| ID | Title | Track | Status | Detail |
|---|---|---|---|---|
| 2.1 | `kitchens` app: `Kitchen` model | Backend | planned (sprint-04) | [stories/2.1-kitchen-model.md](stories/2.1-kitchen-model.md) |
| 2.2 | `Ingredient` model | Backend | planned (sprint-04) | [stories/2.2-ingredient-model.md](stories/2.2-ingredient-model.md) |
| 2.3 | `meals` app: `Meal` (recipe) model | Backend | planned (sprint-04) | [stories/2.3-meal-model.md](stories/2.3-meal-model.md) |
| 2.4 | `MealIngredient` through-model | Backend | planned (sprint-04) | [stories/2.4-meal-ingredient.md](stories/2.4-meal-ingredient.md) |
| 2.5 | `IngredientBatch` model | Backend | planned (sprint-04) | [stories/2.5-ingredient-batch.md](stories/2.5-ingredient-batch.md) |
| 2.6 | Stock receipt UI | FE + BE pair | planned (sprint-04) | [stories/2.6-stock-receipt-ui.md](stories/2.6-stock-receipt-ui.md) |

> **For executors:** each story file is a self-contained TDD plan with file paths, code, commands, and expected output. Pattern follows [Sprint 01's stories](../sprint-01/stories/). **Sprint backlog & spillover protocol:** see [backlog.md](backlog.md).

---

## Parallel tracks

### Backend track — Dev A
2.1 → 2.2 → 2.3 → 2.4 → 2.5 in order. Each is small (1 day-ish). The order matters because:
- 2.4 needs 2.3 (Meal) and 2.2 (Ingredient).
- 2.5 needs 2.1 (Kitchen) and 2.2 (Ingredient).

### Frontend track — Dev B
2.6 (stock receipt UI) depends on 2.1 + 2.2 + 2.5. Until those land, Dev B can:
- Wireframe the stock-receipt screen at 375 px and tablet (768 px).
- Pre-build the form template against a Python `unittest.mock`-ed view.
- Start 2.10 (admin "today's stock" widget — planned in Sprint 05, but begin the layout).

### Admin / ops mini-track — Dev C
Build `seed_ingredients` (Story 2.2) and a `seed_kitchens` helper that loads 2 demo kitchens with realistic Melbourne lat/lng (St Kilda + Footscray). Critical for Sprint 06 planning demos.

---

## Day-by-day suggestion

| Day | Backend | Frontend |
|---|---|---|
| Mon w1 | Sprint planning. 2.1 Kitchen model + admin. | Sprint planning. Wireframe stock-receipt at 375 px + 768 px. |
| Tue w1 | 2.1 merged. Start 2.2 Ingredient. | Static prototype of the form. |
| Wed w1 | 2.2 merged + `seed_ingredients`. Start 2.3 Meal. | Same. |
| Thu w1 | 2.3 merged. Start 2.4 MealIngredient inline. | Hook prototype to a mocked endpoint. |
| Fri w1 | 2.4 merged. Mid-sprint demo of admin flow. | Mid-sprint demo of prototype. |
| Mon w2 | 2.5 IngredientBatch + "expiring ≤ 3 days" admin filter. | Wait on 2.5 → swap mock for real endpoint. |
| Tue w2 | 2.5 merged. Pair with FE on 2.6. | Build 2.6 form against the real backend. |
| Wed w2 | Help debug 2.6. | 2.6 Playwright test at 375 px and 768 px. |
| Thu w2 | Bug-bash kitchen admin pages on a real tablet. | 2.6 in review. |
| Fri w2 | **Sprint demo + retro.** | Same. |

---

## Demo agenda (Fri w2)

1. **Admin (laptop)** — `/admin/`: register a new kitchen "Footscray Kitchen" at real lat/lng with default 10 km radius; add 5 ingredients; create one Meal (e.g. "Pumpkin curry") and inline-add 3 ingredients with quantities.
2. **Kitchen staff (tablet)** — log in, open `/kitchen/stock/receive/`, record 3 batches (rice 10 kg, pumpkin 3 kg, coconut milk 2 L) with expiry dates spanning 2 / 5 / 30 days. Use the "Receive another?" CTA between each.
3. **Admin (laptop)** — re-open `/admin/`, navigate to ingredient batches, apply the "expiring ≤ 3 days" filter → the rice batch (2 days) appears.

## Definition of Done for the sprint

- All 6 stories are `STATUS: done (sprint-04)`.
- `seed_kitchens`, `seed_ingredients` produce a usable demo dataset.
- Stock-receipt form passes Playwright at 375 px **and** 768 px (tablet).

## Risks

| Risk | Mitigation |
|---|---|
| Six stories in two weeks is tight. | 2.5 + 2.6 are the long ones (each ~2 days). If the sprint slips, defer 2.10's pre-work to Sprint 05. |
| Kitchen-staff-only role testing reveals missing permission checks. | Test fixture seeds a `kitchen_staff` user; every 2.6 view assertion runs both as `admin` (allowed) and as `member` (403). |
