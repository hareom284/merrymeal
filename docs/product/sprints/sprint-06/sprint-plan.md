# Sprint 06 — Weekly meal planning

**Weeks:** 11–12
**Primary epic:** [03 — Weekly meal planning](../../epics/03-weekly-planning.md)
**Sprint goal:** an admin can plan a week; every member sees today's meal with their allergens flagged; the 10 km / frozen-weekend rule is enforced; the system warns on diet-coverage gaps.

---

## Stories pulled

| ID | Title | Track | Status | Detail |
|---|---|---|---|---|
| 3.1 | `planning` app: `MealPlan` model | Backend | planned (sprint-06) | [stories/3.1-meal-plan-model.md](stories/3.1-meal-plan-model.md) |
| 3.2 | `assign_meal_type` service | Backend | planned (sprint-06) | [stories/3.2-assign-meal-type-service.md](stories/3.2-assign-meal-type-service.md) |
| 3.3 | Admin weekly planner UI | FE + BE pair | planned (sprint-06) | [stories/3.3-admin-weekly-planner.md](stories/3.3-admin-weekly-planner.md) |
| 3.4 | Member dashboard: today's meal card | FE + BE pair | planned (sprint-06) | [stories/3.4-member-today-card.md](stories/3.4-member-today-card.md) |
| 3.5 | Allergen mapping (Ingredient → Allergy) | Backend | planned (sprint-06) | [stories/3.5-allergen-mapping.md](stories/3.5-allergen-mapping.md) |
| 3.6 | Diet-coverage warning | FE + BE pair (stretch) | planned (sprint-06) | [stories/3.6-diet-coverage-warning.md](stories/3.6-diet-coverage-warning.md) |
| 3.7 | `validate_radius_assignments` command | Backend / Ops | planned (sprint-06) | [stories/3.7-validate-radius-command.md](stories/3.7-validate-radius-command.md) |
| 3.8 | Caregiver multi-member view | FE + BE pair | planned (sprint-06) | [stories/3.8-caregiver-multi-member.md](stories/3.8-caregiver-multi-member.md) |

> **For executors:** each story file is a self-contained TDD plan with file paths, code, commands, and expected output. Pattern follows [Sprint 01's stories](../sprint-01/stories/). **Sprint backlog & spillover protocol:** see [backlog.md](backlog.md).

> **Stretch flag:** Story 3.6 is the most likely to slip. If the sprint is
> at risk on Thursday of week 2, drop 3.6 → Sprint 07 backlog and finish
> the rest cleanly.

---

## Parallel tracks

### Backend track — Dev A
1. **3.1** MealPlan model (½ day).
2. **3.2** assign_meal_type service + tests (1 day).
3. **3.5** Allergen mapping + meal_allergens_for_member service (1 day).
4. **3.7** validate_radius_assignments command + task (1½ days).
5. Pair on **3.3** backend (planner view + grid query) — 2 days.

### Frontend track — Dev B
1. **3.3** Admin planner grid template + HTMX modal (~3 days).
2. **3.4** Member today card template + service consumer (~1½ days).
3. **3.8** Caregiver multi-member view (~1½ days, mostly re-uses 3.4).

### Pair track — both, mid-sprint
**3.6** diet-coverage warning (stretch) — 2 days if pulled in.

---

## Day-by-day suggestion

| Day | Backend | Frontend |
|---|---|---|
| Mon w1 | Sprint planning. 3.1 model. | Sprint planning. Wireframe planner grid. |
| Tue w1 | 3.2 service + 5 unit tests covering the matrix. | Static grid layout at 1280 px. |
| Wed w1 | 3.5 allergen M2M migration + service. | Hook grid to a mocked view. |
| Thu w1 | 3.5 merged. Start 3.3 backend (grid query). | 3.3 HTMX modal for cell edit. |
| Fri w1 | 3.3 backend in review. Mid-sprint demo of grid. | Mid-sprint demo. |
| Mon w2 | 3.3 merged. Start 3.7 command. | Start 3.4 today card. |
| Tue w2 | 3.7 + nightly task wiring + email. | 3.4 with allergen flag (consumes Story 3.5). |
| Wed w2 | Decide: pull 3.6 or hold? If hold, start helping FE. | 3.4 Playwright at 375 px. |
| Thu w2 | 3.6 backend service (if go) OR review/QA day. | 3.6 yellow badge UI OR 3.8 caregiver list. |
| Fri w2 | **Sprint demo + retro.** | Same. |

---

## Demo agenda (Fri w2)

1. **Admin (laptop)** — open `/admin/planner/?week=<next Monday>`. Two kitchens. Drop a Meal into each weekday cell. Sat/Sun auto-set to a frozen meal.
   - If 3.6 landed: a yellow "3 halal members in kitchen A on Wed" badge appears; admin swaps Wednesday's meal to a halal-tagged option; warning clears.
2. **Member (phone)** — log in as Margaret (member with shellfish allergy). Today's meal card shows the planned meal with "⚠ Contains shellfish" if applicable.
3. **Caregiver (phone)** — log in as Margaret's daughter, see Margaret in a list with today card preview.
4. **CI** — show the `validate_radius_assignments` command output in CI logs.

## Definition of Done for the sprint

- All non-stretch stories `STATUS: done (sprint-06)`. 3.6 either done or formally moved to Sprint 07.
- Five `assign_meal_type` unit-test cases pass (weekday in radius / out / weekend / boundary / no-address).
- `validate_radius_assignments` runs in CI (non-blocking) and as a nightly Django-Q2 task.

## Risks

| Risk | Mitigation |
|---|---|
| The planner grid HTMX modal becomes fiddly. | Build the modal as a separate template partial; if HTMX integration drags, fall back to a normal form submission for v1. |
| Allergen seed mappings are incomplete. | The seed is best-effort; missing mappings show no flag but never crash. Add a `--audit` flag to `seed_dietary` that prints ingredients with no allergen tagged. |
| 3.6 yellow-badge query is expensive on large datasets. | For v1, the planner only ever displays the current week; the query is bounded. Profile on a 1000-member fixture in week 2. |
