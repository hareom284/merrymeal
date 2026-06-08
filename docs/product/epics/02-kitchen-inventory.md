# Epic 02 — Kitchen & inventory backbone

> **Goal:** the operational backbone exists. Admins can model real-world
> kitchen state — what we have in stock, when it expires, what dishes we
> can cook from it, and whether we are following food-safety rules.

**Sprints:** 2 (Sprint 04 + Sprint 05)
**Status:** not started
**Depends on:** Epic 00, Epic 01 (`Partner` model exists by Story 1.4).
**Source spec:** [Roadmap §6, Phase 2](../../superpowers/specs/2026-06-01-merrymeal-django-design.md)

---

## Why this epic exists

The schema reassessment identified three real-world problems we are not
allowed to ignore: food safety (storage / cooking temperature, hygiene
records), ingredient expiry (no one wants to serve Margaret expired
stock), and the operational reality that kitchens have geographic limits.

This epic builds the data models and the daily UI that make those
constraints enforceable. **Without this epic, planning has nothing to plan.**

---

## Personas in scope

- **Kitchen staff** — cook, on a tablet. Records food-safety checks.
- **Admin** — operations. Sets up kitchens, ingredients, recipes; records stock receipts.

---

## Stories

### Story 2.1 — `kitchens` app: `Kitchen` model
**STATUS: backlog**

**As an** admin
**I want** to register the kitchens we use (own + outsourced) with their location and service radius
**so that** later, planning can decide who gets fresh vs frozen meals based on the 10 km rule.

**Acceptance criteria:**
- [ ] New app `apps/kitchens/`.
- [ ] `apps/kitchens/models/kitchens.py::Kitchen` matching schema:
      `name`, `partner_id` (FK, nullable), `is_outsourced` bool, `latitude`,
      `longitude`, `service_radius_km` (default 10.00).
- [ ] Django admin CRUD; list view shows lat/lng and radius.
- [ ] Admin form validation: lat in [-90, 90], lng in [-180, 180].

**Technical notes:**
- Files: `apps/kitchens/{__init__,apps,admin,models/__init__,models/kitchens,tests/test_kitchens}.py`.
- `INSTALLED_APPS` updated.
- DB tables touched: `kitchens`.

**Mobile viewport:** N/A.
**Test strategy:** model + admin smoke test.

---

### Story 2.2 — `Ingredient` model
**STATUS: backlog**

**As an** admin
**I want** to maintain a catalogue of ingredients with units of measure
**so that** recipes and stock can reference the same names without typos.

**Acceptance criteria:**
- [ ] `apps/kitchens/models/ingredients.py::Ingredient` with `name`, `unit`
      (`g`, `kg`, `ml`, `l`, `unit`) matching schema.
- [ ] Django admin CRUD, search by name.
- [ ] Management command `seed_ingredients` populates 30 common ingredients.

**Technical notes:**
- Files: `apps/kitchens/models/ingredients.py`,
  `apps/kitchens/management/commands/seed_ingredients.py`,
  `apps/kitchens/tests/test_ingredients.py`.
- DB tables touched: `ingredients`.

**Mobile viewport:** N/A.
**Test strategy:** model + idempotent-seed test.

---

### Story 2.3 — `meals` app: `Meal` (recipe) model
**STATUS: backlog**

**As an** admin / dietitian
**I want** to maintain a list of meals (recipes) with prep + cook times
**so that** the planner has a menu to schedule from.

**Acceptance criteria:**
- [ ] New app `apps/meals/`.
- [ ] `apps/meals/models/meals.py::Meal` matching schema: `name`,
      `description`, `prep_time_minutes`, `cook_time_minutes`, `is_active`,
      timestamps + soft delete via `core`.
- [ ] Django admin CRUD; list shows active/inactive filter.

**Technical notes:**
- Files: `apps/meals/{__init__,apps,admin,models/__init__,models/meals,tests/test_meals}.py`.
- DB tables touched: `meals`.

**Mobile viewport:** N/A.
**Test strategy:** model + admin smoke test.

---

### Story 2.4 — `MealIngredient` through-model + admin inline
**STATUS: backlog**

**As an** admin
**I want** to associate ingredients with a recipe, including quantity
**so that** stock-consumption planning becomes possible later.

**Acceptance criteria:**
- [ ] `apps/kitchens/models/meal_ingredients.py::MealIngredient` matching schema
      (`meal_id`, `ingredient_id`, `quantity`, unique on the pair).
- [ ] Inline on the Meal admin page.
- [ ] Validation: `quantity > 0`.

**Technical notes:**
- Files: `apps/kitchens/models/meal_ingredients.py`,
  `apps/meals/admin.py` (extends), `apps/kitchens/tests/test_meal_ingredients.py`.
- DB tables touched: `meal_ingredients`.

**Mobile viewport:** N/A.
**Test strategy:** model + admin inline integration test.

---

### Story 2.5 — `IngredientBatch` model (expiration tracking)
**STATUS: backlog**

**As an** admin
**I want** to record incoming stock as batches with expiry dates per kitchen
**so that** I can prevent serving expired ingredients and forecast waste.

**Acceptance criteria:**
- [ ] `apps/kitchens/models/ingredient_batches.py::IngredientBatch`
      matching schema: `ingredient_id`, `kitchen_id`, `lot_number`,
      `quantity`, `received_at`, `expiration_date`.
- [ ] Index on `expiration_date` (already in SQL schema).
- [ ] Django admin CRUD; filter by kitchen, expiry date range.
- [ ] Custom admin list view: "expiring in ≤ 3 days" quick filter.

**Technical notes:**
- Files: `apps/kitchens/models/ingredient_batches.py`,
  `apps/kitchens/admin.py`, `apps/kitchens/tests/test_batches.py`.
- DB tables touched: `ingredient_batches`.

**Mobile viewport:** N/A.
**Test strategy:** model + admin filter test.

---

### Story 2.6 — Stock receipt UI (mobile-readable)
**STATUS: backlog**

**As a** kitchen staff member
**I want** a single screen to record a new batch (ingredient, quantity, expiry, lot)
**so that** I do not have to learn the Django admin to log stock arrivals.

**Acceptance criteria:**
- [ ] Route `/kitchen/stock/receive/`.
- [ ] Form: kitchen (auto-set if user has only one), ingredient, quantity,
      received-at (default today), expiration-date (required), lot number (optional).
- [ ] On submit: an `IngredientBatch` row is created; a success toast and
      "Receive another?" CTA appear.
- [ ] Restricted by `@role_required('kitchen_staff', 'admin')`.
- [ ] Mobile-first at 375 px — tablet-friendly layout adds a wider second
      column at `md:`.

**Technical notes:**
- Files: `apps/kitchens/views/stock.py`, `apps/kitchens/forms/stock.py`,
  `apps/kitchens/services/stock.py::receive_batch`,
  `apps/kitchens/urls.py`, `templates/kitchens/stock/receive.html`,
  `apps/kitchens/tests/test_stock_receive.py`.
- DB tables touched: `ingredient_batches`.

**Mobile viewport:** required (kitchens often use tablets, but build at 375 px first).
**Test strategy:** unit (service + form) + Playwright happy path.

---

### Story 2.7 — `food_safety` app: `FoodSafetyCheck` model
**STATUS: backlog**

**As a** kitchen staff member
**I want** to record food-safety checks with the result and (where relevant) temperature
**so that** audits have evidence and a failed check can block a meal plan.

**Acceptance criteria:**
- [ ] New app `apps/food_safety/`.
- [ ] `apps/food_safety/models/checks.py::FoodSafetyCheck` matching schema:
      `kitchen_id`, `meal_plan_id` (nullable — populated later in Epic 03),
      `check_type` enum (`storage_temp`, `cooking_temp`, `cold_chain`,
      `hygiene`, `cleaning`, `pest_control`), `temperature_celsius`
      (nullable), `result` enum (`pass`, `fail`), `checked_by`, `checked_at`,
      `notes`.
- [ ] Django admin CRUD with filters by kitchen and result.

**Technical notes:**
- Files: `apps/food_safety/{__init__,apps,admin,models/__init__,models/checks,tests/test_checks}.py`.
- DB tables touched: `food_safety_checks`.

**Mobile viewport:** N/A (UI lands in Story 2.8).
**Test strategy:** model + admin smoke test.

---

### Story 2.8 — Daily food-safety check form (mobile-first)
**STATUS: backlog**

**As a** kitchen staff member
**I want** a one-screen form on my tablet/phone to log today's safety checks
**so that** compliance is a 2-minute habit, not a paperwork chore.

**Acceptance criteria:**
- [ ] Route `/kitchen/safety/check/`.
- [ ] One form per check type with the right widget:
  - `storage_temp`, `cooking_temp`, `cold_chain` → temperature input (°C, decimal).
  - `hygiene`, `cleaning`, `pest_control` → pass/fail radio buttons + notes textarea.
- [ ] Auto-fills `checked_by = request.user` and `checked_at = now()`.
- [ ] On submit, a green toast confirms the row was saved; the page shows
      today's already-completed checks as a list at the top.
- [ ] Mobile-first at 375 px with 44 px touch targets.

**Technical notes:**
- Files: `apps/food_safety/views/check.py`,
  `apps/food_safety/forms/check.py`,
  `apps/food_safety/services/checks.py::record_check`,
  `apps/food_safety/urls.py`,
  `templates/food_safety/check.html`,
  `apps/food_safety/tests/test_check_view.py`.
- DB tables touched: `food_safety_checks`.

**Mobile viewport:** required.
**Test strategy:** unit + Playwright at 375 px.

---

### Story 2.9 — Nightly job: alert on expiring batches (≤ 3 days)
**STATUS: backlog**

**As an** admin
**I want** an email every morning listing batches expiring within 3 days
**so that** I can repurpose or discard them before they hit a member's meal.

**Acceptance criteria:**
- [ ] Django-Q2 scheduled task runs daily at 06:00 Melbourne time.
- [ ] Task queries `IngredientBatch` where `expiration_date <= today + 3
      days` and the batch's `quantity > 0` (not yet exhausted).
- [ ] Sends one email per kitchen to that kitchen's admin contact, grouped
      by ingredient.
- [ ] If no batches are expiring, no email is sent (avoid noise).
- [ ] Idempotent: running the task twice on the same day does not send
      duplicate emails (track a `last_sent_date` per kitchen in a small
      `alert_log` table or in cache).

**Technical notes:**
- Files: `apps/kitchens/tasks/expiry_alerts.py`,
  `apps/kitchens/services/expiry.py::find_expiring_batches(kitchen, within_days)`,
  `templates/kitchens/emails/expiring_batches.{html,txt}`,
  `apps/kitchens/tests/test_expiry_alerts.py`.
- DB tables touched: read `ingredient_batches`; write a small `alert_log` (new table — migration).
- Schedule the task via Django-Q2 admin or a `Schedule.objects.update_or_create(...)` data migration.

**Mobile viewport:** N/A (email + admin).
**Test strategy:**
- Unit: service returns the right batches for a contrived dataset.
- Unit: idempotency — call task twice in one day, assert only one email.
- Integration: `django.core.mail.outbox` contains the expected email body.

---

### Story 2.10 — "Today's stock at a glance" admin widget
**STATUS: backlog**

**As an** admin
**I want** a single dashboard card showing each kitchen's:
- batches expiring within 3 days (count + link)
- last 24 h food-safety check pass-rate
- last food-safety failure (if any) with link

**so that** I open one screen each morning and know whether anything needs intervention.

**Acceptance criteria:**
- [ ] `/dashboards/admin/kitchens/` shows a card per kitchen with the three metrics above.
- [ ] Mobile-readable; desktop-primary layout.
- [ ] Each metric is a link to the underlying filtered list.

**Technical notes:**
- Files: `apps/dashboards/views/admin_kitchens.py`,
  `apps/dashboards/services/kitchen_summary.py`,
  `templates/dashboards/admin/kitchens.html`,
  `apps/dashboards/tests/test_admin_kitchens.py`.
- DB tables touched: read-only.

**Mobile viewport:** mobile-readable, desktop-primary.
**Test strategy:** unit + Playwright at 1024 px.

---

## Backlog (not in sprint 04 / 05 yet)

- **2.11 — Stock deduction on cook** — when a meal plan moves from
  `planned` to `prepared`, deduct ingredient quantities from the oldest
  matching batch (FEFO). Lands in Epic 03 if scheduling permits, otherwise
  Sprint 11+.
- **2.12 — Batch waste tracking** — a "discard" button on a batch records
  the reason (expired / contaminated / damaged) for waste reporting.
- **2.13 — Supplier model** — currently `partners.type = 'supplier'`
  suffices; promote to a sub-model if supplier-specific fields appear.
- **2.14 — Allergen → ingredient map** — needed by the planner to flag
  meals containing a member's allergen. Owns the
  `ingredients.contains_allergens` mapping. Likely moves into Epic 03.

---

## Demo for end of Epic 02

A teammate plays the cook:

1. Logs in as a `kitchen_staff` user.
2. Records three stock receipts in under 90 seconds.
3. Logs today's three temperature checks and a hygiene pass.
4. The admin logs in and sees, on `/dashboards/admin/kitchens/`, all three
   counts updated. The next morning, an email arrives in the dev outbox
   listing one batch expiring in 2 days.
