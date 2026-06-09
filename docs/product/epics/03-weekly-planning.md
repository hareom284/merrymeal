# Epic 03 — Weekly meal planning

> **Goal:** admins plan the week; members see what's coming. The 10 km rule
> and the frozen-weekend rule are enforced automatically.

**Sprints:** 1 (Sprint 06) — single sprint, but ambitious. If it slips, the
overflow stories move to Sprint 07.
**Status:** not started
**Depends on:** Epic 01 (Users + Addresses + Dietary), Epic 02 (Kitchens + Meals + Ingredients).
**Source spec:** [Roadmap §6, Phase 3](../../superpowers/specs/2026-06-01-merrymeal-django-design.md)

---

## Why this epic exists

Today the dietitian writes the week's menu in a spreadsheet and pastes it
into an email. By the end of this epic, the menu lives in the database, the
**frozen vs fresh** decision is made automatically per (member, kitchen,
day), and every member's dashboard shows the right plate for the right day
with their allergens highlighted.

This is the first epic where end-users (members) see something different
every day. It's also the first epic that exercises the Haversine helper
shipped in Epic 00 in anger.

---

## Personas in scope

- **Admin / dietitian** — desktop, plans the week.
- **Member** — phone, sees today's meal.
- **Caregiver** — phone, sees a list of cared-for members and each member's today card.

---

## Stories

### Story 3.1 — `planning` app: `MealPlan` model
**STATUS: done (sprint-06)**

**As an** admin
**I want** to schedule one meal per (kitchen, service date)
**so that** delivery and inventory have a single source of truth for what is being cooked when and where.

**Acceptance criteria:**
- [ ] New app `apps/planning/`.
- [ ] `apps/planning/models/meal_plans.py::MealPlan` matching schema:
      `meal_id`, `kitchen_id`, `service_date`, `day_of_week`, `meal_type`
      (`fresh` / `frozen`), `planned_quantity`, `published_by`, `created_at`.
- [ ] Unique constraint on (`kitchen_id`, `service_date`) — one plan per
      kitchen per day.
- [ ] Django admin CRUD with filters by kitchen + week.

**Technical notes:**
- Files: `apps/planning/{__init__,apps,admin,models/__init__,models/meal_plans,tests/test_meal_plans}.py`.
- `INSTALLED_APPS` updated.
- DB tables touched: `meal_plans`.

**Mobile viewport:** N/A (UI is admin-side and lands in Story 3.3).
**Test strategy:** model + unique-constraint test.

---

### Story 3.2 — `planning.services.assign_meal_type(member, kitchen, service_date)`
**STATUS: done (sprint-06)**

**As a** backend developer
**I want** a single function that returns `fresh` or `frozen` for a
(member, kitchen, service_date) tuple
**so that** every place in the codebase that asks "what does Margaret get?"
gets the same answer.

**Acceptance criteria:**
- [ ] `apps/planning/services/assignment.py::assign_meal_type(member, kitchen, service_date) -> Literal['fresh', 'frozen']`.
- [ ] Logic:
  - If `service_date.weekday()` ∈ {5, 6} (Sat, Sun) → `frozen`.
  - Else: compute `haversine_km(member.primary_address.lat/lng, kitchen.lat/lng)`.
    - ≤ `kitchen.service_radius_km` → `fresh`.
    - else → `frozen`.
- [ ] If the member has no address with lat/lng, raise
      `AddressMissingError` (a domain exception). Callers handle.
- [ ] Pure function (no DB writes).

**Technical notes:**
- Files: `apps/planning/services/assignment.py`,
  `apps/planning/tests/test_assignment.py`.
- DB tables touched: read-only (member, address, kitchen).

**Mobile viewport:** N/A.
**Test strategy:** unit tests covering: (a) weekday inside radius → fresh,
(b) weekday outside radius → frozen, (c) weekend regardless of radius →
frozen, (d) edge: exactly at radius → fresh, (e) no address → raises.

---

### Story 3.3 — Admin weekly planner UI
**STATUS: done (sprint-06)**

**As an** admin
**I want** a one-screen grid of (kitchen × day) cells where I drop a meal
**so that** I can plan a whole week in five minutes per kitchen.

**Acceptance criteria:**
- [ ] Route `/admin/planner/`.
- [ ] Default to **next week** (Mon–Sun); URL accepts `?week=YYYY-MM-DD`
      to navigate.
- [ ] Grid: kitchens down the left, days across the top.
- [ ] Each cell shows the current meal (if any) and a "Set meal" button.
- [ ] "Set meal" opens an HTMX modal: meal dropdown + planned quantity.
- [ ] Saving creates or updates the `MealPlan` row for that (kitchen,
      date). `meal_type` is set automatically: `frozen` on Sat/Sun, else
      `fresh` (the per-member outside-radius case is applied at delivery
      generation time, not at planning time — see Story 3.4).
- [ ] Restricted to `admin`.
- [ ] Desktop-primary; mobile-readable.

**Technical notes:**
- Files: `apps/planning/views/admin_planner.py`,
  `apps/planning/forms/planner.py`,
  `apps/planning/urls.py`,
  `templates/planning/admin/planner.html`,
  `templates/planning/admin/_cell_form.html` (HTMX partial),
  `apps/planning/tests/test_admin_planner.py`.
- DB tables touched: `meal_plans` (read/write).

**Mobile viewport:** mobile-readable, desktop-primary.
**Test strategy:** unit + Playwright at 1280 px happy path.

---

### Story 3.4 — Member dashboard: "today's meal" card
**STATUS: done (sprint-06)**

**As a** member
**I want** to see today's meal — name, photo, key ingredients, and any of
my allergens flagged in red
**so that** I know what to expect and trust that the kitchen knows my needs.

**Acceptance criteria:**
- [ ] Route `/dashboard/` (when `request.user.role == 'member'`).
- [ ] Shows a single card:
  - Meal name (`font-display`, large).
  - Optional photo (use a placeholder if none).
  - Bullet list of key ingredients.
  - If any ingredient maps to one of the member's allergies, a red badge:
    "⚠ Contains <allergen>".
  - Delivery status badge: pending / out for delivery / delivered (from
    Epic 04 once it lands; until then, show "Planned" + service_date).
- [ ] Mobile-first at 375 px with 18 px body font.
- [ ] If there is no plan for today, show a friendly "No meal scheduled
      today — your next is on <date>".

**Technical notes:**
- Files: `apps/dashboards/views/member_home.py`,
  `apps/dashboards/services/member_today.py::get_today_card(member)`,
  `templates/dashboards/member/home.html`,
  `apps/dashboards/tests/test_member_home.py`.
- The allergen flag depends on Story 3.5.
- DB tables touched: read-only.

**Mobile viewport:** required. 18 px base font.
**Test strategy:** unit + Playwright at 375 px for both "has meal today"
and "no meal today" paths.

---

### Story 3.5 — Allergen mapping (ingredient → allergen)
**STATUS: done (sprint-06)**

**As a** dietitian
**I want** ingredients to declare which allergens they contain
**so that** the planner / dashboard can flag dangerous meals without me hand-checking every recipe.

**Acceptance criteria:**
- [ ] New M2M `Ingredient.contains_allergens` (M2M to
      `dietary.Allergy`).
- [ ] Migration adds the join table.
- [ ] `seed_dietary` (Story 1.5) extended to mark obvious mappings (peanut
      ingredient → peanut allergy, etc.).
- [ ] `apps/planning/services/allergen.py::meal_allergens_for_member(meal, member) -> list[Allergy]`
      returns the intersection of the meal's ingredient allergens and the
      member's declared allergies.
- [ ] Used by Story 3.4's "today" card.

**Technical notes:**
- Files: extend `apps/kitchens/models/ingredients.py`,
  `apps/planning/services/allergen.py`,
  `apps/planning/tests/test_allergen.py`,
  extend `apps/dietary/management/commands/seed_dietary.py`.
- DB tables touched: new through table `ingredient_allergy`.

**Mobile viewport:** N/A.
**Test strategy:** unit covering: empty intersection → empty list; one
match → one allergen; multiple matches → de-duplicated list.

---

### Story 3.6 — Diet-coverage warning ("no halal Thursday")
**STATUS: done (sprint-06)**

**As an** admin
**I want** the planner to warn me if a day's meal is incompatible with any
member's declared diet
**so that** I do not publish a week that leaves a halal member without a
suitable meal.

**Acceptance criteria:**
- [ ] On the admin planner (Story 3.3), each cell shows a yellow badge
      with a count when the planned meal is incompatible with one or more
      member diets currently being served by that kitchen on that day.
- [ ] Hover/tap reveals: "12 members are halal — this meal is not halal".
- [ ] An "Override (acknowledged)" link lets the admin dismiss the
      warning; the dismissal is recorded on the `MealPlan` row.
- [ ] Compatibility logic for v1: a meal is "compatible" with a diet if
      the meal has been tagged with that diet (new M2M `Meal.diets`).

**Technical notes:**
- Files: new M2M on `Meal`; new field `MealPlan.warnings_acknowledged_by`;
  `apps/planning/services/coverage.py::diet_warnings(meal_plan) -> dict[Diet, int]`;
  extend admin planner view + template.
- DB tables touched: new `meal_diet` table; new column on `meal_plans`.

**Mobile viewport:** mobile-readable, desktop-primary.
**Test strategy:** unit + Playwright at 1280 px.

---

### Story 3.7 — `validate_radius_assignments` management command (CI guard)
**STATUS: done (sprint-06)**

**As the** team
**I want** a command that walks every active member's address and asserts
that, given each kitchen they are assigned to, the fresh/frozen decision
matches `assign_meal_type` today
**so that** silent drift (someone hand-edits a `MealPlan`, an address
changes after a member moves) does not lead to wrong deliveries.

**Acceptance criteria:**
- [ ] `python manage.py validate_radius_assignments` exits 0 if every
      active member is consistent, exits 1 otherwise.
- [ ] Output lists every inconsistency: member, kitchen, expected, actual.
- [ ] Wired into the nightly Django-Q2 schedule; failures email an admin.
- [ ] Wired into CI as a non-blocking job (for now) — output appears in
      the PR check log.

**Technical notes:**
- Files: `apps/planning/management/commands/validate_radius_assignments.py`,
  `apps/planning/tasks/validate.py`,
  `apps/planning/tests/test_validate_command.py`.
- DB tables touched: read-only.

**Mobile viewport:** N/A.
**Test strategy:** unit fixtures that contain a deliberately-wrong row;
assert command exit code = 1 and stdout names the row.

---

### Story 3.8 — Caregiver multi-member view
**STATUS: done (sprint-06)**

**As a** caregiver looking after two or more people
**I want** one screen listing every member I look after with each one's "today" card summary
**so that** I do not have to log in as each member.

**Acceptance criteria:**
- [ ] Route `/dashboard/` (when `request.user.role == 'caregiver'`).
- [ ] Lists each linked `member` via `member_caregivers`; each row shows:
      member name + photo, today's meal name (or "no meal today"), any
      allergen flag, delivery status (placeholder until Epic 04).
- [ ] Tapping a row drills into a member-detail page (a stripped-down
      version of the member home).
- [ ] Mobile-first at 375 px.

**Technical notes:**
- Files: `apps/dashboards/views/caregiver_home.py`,
  `apps/dashboards/services/caregiver_today.py`,
  `templates/dashboards/caregiver/home.html`,
  `apps/dashboards/tests/test_caregiver_home.py`.
- Reuses Story 3.4's services.
- DB tables touched: read-only.

**Mobile viewport:** required.
**Test strategy:** unit + Playwright at 375 px for 0 / 1 / 3 linked members.

---

## Backlog (not in sprint 06 yet)

- **3.9 — "Next 7 days" forecast card** on the member dashboard. Stretch
  goal; trades sprint-06 capacity with Story 3.6.
- **3.10 — Bulk-clone last week** ("copy last week to this week" admin
  shortcut). Easy win; moves to whichever sprint has 2 hours of slack.
- **3.11 — Meal photo upload** on `Meal`. Story 3.4 currently uses a
  placeholder.

---

## Demo for end of Epic 03

A teammate plays the dietitian:

1. Opens `/admin/planner/?week=<next monday>`.
2. Drops a meal into every Mon–Fri cell for two kitchens. The Sat/Sun cells
   auto-default to a frozen meal.
3. Sees one yellow warning ("3 halal members in kitchen A on Wednesday")
   and either swaps the meal or acknowledges.
4. Another teammate logs in as Margaret (member): sees Wednesday's card
   with "⚠ Contains shellfish" because Margaret has shellfish allergy.
5. Margaret's daughter logs in as caregiver: sees Margaret + one more
   member, each with the right today card.
6. CI run includes `validate_radius_assignments` — green.
