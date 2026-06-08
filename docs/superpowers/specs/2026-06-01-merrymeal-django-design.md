# MerryMeal — Django Platform Roadmap (Mobile-First)

**Status:** Draft v1 — design / roadmap spec
**Date:** 2026-06-01
**Owner:** Hare Om
**Source artefacts:** `merrymeal_schema_corrected.sql`, `docs/requirement.md`, `index.html` (interactive prototype)

This document is the **planning roadmap** for turning the existing MerryMeal SQL schema and prototype into a working Django web platform. It does not implement anything. Each phase listed in section §6 becomes its own brainstorm → spec → plan → build cycle later.

---

## 1. Goal & non-goals

### Goal
Ship a single mobile-first Django web application that replaces the charity's phone-and-spreadsheet operations across five workflows:

1. Member application & meal tracking
2. Caregiver oversight of one or more members
3. Volunteer daily delivery
4. Partner referral & outcome tracking
5. Donor giving + admin operations (planning, kitchen, food safety, reporting)

### Non-goals (v1)
- Native iOS / Android apps — web-responsive only.
- Member-customised menu ordering — menus are dietitian-set.
- Multi-language UI — English only.
- Live chat — email + phone fallback.
- Payroll / volunteer reimbursement.

These mirror requirement.md §8 and are out of scope for the roadmap.

---

## 2. Stack & key technical decisions

| Concern | Choice | Rationale |
|---|---|---|
| Framework | Django 5.x (LTS) | Built-in admin, ORM matches the schema, mature ecosystem |
| UI | Server-rendered templates + **HTMX** + **Alpine.js** (light) | App-like feel without an SPA; one codebase, one deploy |
| CSS | **Tailwind CSS** (mobile-first by default) | Utility classes encode the mobile-first discipline |
| Database | **MySQL 8** | The schema is already authored for MySQL/InnoDB |
| Auth | Custom user model extending `AbstractUser` | Maps directly to the `users` table (role, dob, partner_id, soft delete) |
| Geo (10 km rule) | Raw Haversine in a queryset method | Avoids PostGIS dependency on MySQL |
| Payments | Stripe via `dj-stripe` | Standard charity-friendly flow, supports recurring |
| Background jobs | Django-Q2 (Redis broker) | Lighter than Celery; sufficient for our job volume |
| File storage | `django-storages` → S3 | Proof-of-delivery photos, partner MOUs |
| Testing | pytest-django + factory-boy + Playwright | TDD discipline; Playwright runs in mobile viewport |
| Containerisation | Docker + docker-compose | Web, MySQL, Redis, worker as one stack |
| Deployment v1 | Single VPS (Hetzner / Fly) behind Nginx + Gunicorn | Cheap, simple, sufficient for charity scale |

### Decisions deliberately deferred
- **PWA / service worker offline mode** — deferred to phase 7. The volunteer-offline use case is real (patchy coverage) but adds complexity; ship mobile-responsive first, add offline once the delivery flow stabilises.
- **PostGIS** — only revisit if route optimisation needs proper geo queries.
- **Multi-tenant kitchens** — kitchens belong to partners; no separate tenancy layer in v1.

---

## 3. Mobile-first design strategy

Mobile-first is not just "make it responsive." It is a **discipline** that shapes every UI decision.

### Principles
1. **Design at 375 px viewport first.** Layer up to `md:` / `lg:` for tablet/desktop using Tailwind breakpoints. Never the reverse.
2. **Single-column on mobile.** Cards stack vertically. Grids only appear at `md:` and up.
3. **Big touch targets — minimum 44 × 44 px.** WCAG AA. Margaret (84, low vision) and Sarah (volunteer on a bike) cannot tap small links.
4. **Thumb-zone navigation.** Primary actions live in the bottom 1/3 of the screen on mobile, not the top. Bottom-anchored "Mark Delivered" for volunteers.
5. **One screen, one job.** Each page does one thing. Multi-step flows use page transitions, not modals stacked on modals.
6. **HTMX partial swaps** for interactivity — no full page reload when rating a meal, marking a delivery, or updating availability.
7. **Progressive enhancement.** Pages must function with HTMX disabled. Forms POST traditionally as a fallback.
8. **Accessibility baseline.** WCAG AA. `prefers-reduced-motion` honoured. Large-text mode toggle for members.
9. **Performance budget.** First Contentful Paint < 1.5 s on a throttled 3G simulation. Tailwind purged, images lazy-loaded, no client-side framework bundle.
10. **Photo/proof flows use the device camera** via `<input type="file" capture="environment">`.

### Per-role mobile considerations
- **Member (elderly).** Bigger base font (18 px), generous line-height, high contrast, "call us" button always visible.
- **Caregiver.** Compact list of cared-for members; tap a card to drill into one person.
- **Volunteer.** Map + list of stops, swipe-to-mark-delivered, offline-capable map tiles (phase 7).
- **Partner.** Quick referral form, 4 fields max above the fold.
- **Donor.** One-page donate flow, Apple Pay / Google Pay first, card second.
- **Admin.** Mobile-readable but desktop-primary for planning screens (the only role that gets a desktop-leaning UI).

---

## 4. Django app decomposition

One Django app per bounded context. Each owns its own tables, urls, templates, and tests. Cross-app references are by FK only — no shared model imports across app boundaries except via well-defined services.

```
merrymeal/
├── apps/
│   ├── core/          # base models, Haversine helpers, audit log, role decorator
│   ├── accounts/      # users, addresses, cities, member_caregivers
│   ├── partners/      # partners (charity/restaurant/supplier/corporate)
│   ├── dietary/       # diet_preferences, allergies (+ M2M through tables)
│   ├── kitchens/      # kitchens, ingredients, meal_ingredients, ingredient_batches
│   ├── meals/         # meals (recipes)
│   ├── food_safety/   # food_safety_checks
│   ├── planning/      # meal_plans (Mon–Fri fresh + frozen-weekend rule)
│   ├── volunteers/    # volunteer_availabilities
│   ├── delivery/      # routes, deliveries, delivery_feedback
│   ├── donations/     # campaigns, donations (Stripe)
│   └── dashboards/    # role home pages, admin reports (no own tables)
├── config/            # settings/{dev,prod,test}.py, urls.py, wsgi.py
├── templates/         # base.html, partials/ (HTMX fragments)
├── static/            # tailwind src + compiled, htmx.min.js, alpine.min.js
├── tests/
└── compose.yaml
```

### Table → app mapping (all 20 schema tables)

| Schema table | Django app | Django model |
|---|---|---|
| `users` | accounts | `User` (extends AbstractUser) |
| `user_addresses` | accounts | `Address` |
| `cities` | accounts | `City` |
| `member_caregivers` | accounts | `CaregiverLink` |
| `partners` | partners | `Partner` |
| `diet_preferences` | dietary | `DietPreference` |
| `diet_preference_user` | dietary | `UserDietPreference` (through) |
| `allergies` | dietary | `Allergy` |
| `allergy_user` | dietary | `UserAllergy` (through) |
| `kitchens` | kitchens | `Kitchen` |
| `ingredients` | kitchens | `Ingredient` |
| `meal_ingredients` | kitchens | `MealIngredient` (through) |
| `ingredient_batches` | kitchens | `IngredientBatch` |
| `meals` | meals | `Meal` |
| `food_safety_checks` | food_safety | `FoodSafetyCheck` |
| `meal_plans` | planning | `MealPlan` |
| `volunteer_availabilities` | volunteers | `Availability` |
| `routes` | delivery | `Route` |
| `deliveries` | delivery | `Delivery` |
| `delivery_feedback` | delivery | `DeliveryFeedback` |
| `campaigns` | donations | `Campaign` |
| `donations` | donations | `Donation` |

### Cross-app dependency rules
- `core` depends on nothing (only Django).
- `accounts` depends on `core`.
- `partners` depends on `core`.
- `dietary` depends on `accounts`.
- `kitchens` depends on `partners`.
- `meals` depends on `core`.
- `food_safety` depends on `kitchens`, `accounts`.
- `planning` depends on `meals`, `kitchens`, `accounts`.
- `volunteers` depends on `accounts`.
- `delivery` depends on `planning`, `accounts`, `volunteers`.
- `donations` depends on `partners`, `accounts`.
- `dashboards` depends on everything (read-only).

If a future change tries to add a back-edge (e.g. `accounts` importing from `delivery`), the dependency rule is violated and we need a service layer instead.

---

## 5. Cross-cutting concerns

### Roles & permissions
Schema defines six roles on `users.role`: `member`, `volunteer`, `caregiver`, `donor`, `kitchen_staff`, `admin`. We map them to:
- Django **groups** (one group per role) for broad permission grouping.
- A custom `@role_required('admin', 'kitchen_staff')` decorator for view-level checks.
- Object-level permissions only where needed (e.g. a member can only see their own deliveries).
- `is_staff` / `is_superuser` reserved for the Django admin site, not used for app role gating.

### Soft delete
The schema uses `deleted_at` on `users`, `cities`, `meals`. We provide a `SoftDeleteModel` base in `core` with:
- Default manager excludes soft-deleted rows.
- `all_objects` manager includes them.
- `instance.delete()` sets `deleted_at` rather than removing the row.

### The 10 km rule
`Kitchen.service_radius_km` defaults to 10. For each `(member, kitchen)` pair we compute great-circle distance via Haversine in SQL:
- Members **inside** radius → `MealPlan.meal_type = 'fresh'` on Mon–Fri.
- Members **outside** radius **or** weekend → `MealPlan.meal_type = 'frozen'`.

This logic lives in `planning/services.py::assign_meal_type(member, kitchen, service_date)`. A Django management command `validate_radius_assignments` runs in CI to catch drift.

### Audit log
Sensitive tables are tracked with `django-auditlog`:
- `accounts.User` (role, contact info)
- `accounts.Address` (PII)
- `dietary.UserDietPreference`, `dietary.UserAllergy`
- `planning.MealPlan`
- `delivery.Delivery` (status changes)

This answers the requirement-doc story: *"who changed Margaret's diet?"*

### Privacy & data protection
- Email + names: stored plain, indexed.
- DOB, dietary, allergy data: encrypted at rest via `django-cryptography` on the column.
- Delivery photos: signed S3 URLs only; never public.
- HTTPS enforced (Nginx + HSTS).
- Session cookies: `HttpOnly`, `Secure`, `SameSite=Lax`.

### Money
All monetary amounts in **integer cents** (matches `donations.amount_cents`, `campaigns.goal_cents`). Never floats. Display formatting via a template tag.

### Time zones
Application time zone = Australia/Melbourne (charity assumed local). All timestamps stored UTC. `service_date` is a local-date field.

---

## 6. Phased build plan

Each phase is a deployable increment. Each will become its own brainstorm → spec → implementation-plan cycle.

### Phase 0 — Foundation (≈ 1 sprint)
**Goal:** an empty but production-shaped Django app a developer can clone, run, and deploy.
- `django-admin startproject` with split settings (`dev`, `prod`, `test`).
- `docker-compose` with `web`, `mysql`, `redis`, `worker`.
- `core` app with `TimeStampedModel`, `SoftDeleteModel`, Haversine helper, `@role_required` decorator.
- `accounts.User` custom model + auth flows (login, logout, password reset).
- Tailwind build pipeline (`tailwindcss` CLI) + HTMX + Alpine.js wired into `base.html`.
- pytest + factory-boy + Playwright (mobile viewport) scaffolding.
- CI: ruff, pytest, Playwright smoke test, mypy (optional).
- **Deliverable:** mobile-first login screen, deploys from `main`, CI green.

### Phase 1 — Identity & onboarding (≈ 1–2 sprints)
**Goal:** a person can apply to become a member; an admin can approve them.
- Finish `accounts`: `Address`, `City`, `CaregiverLink`.
- `partners` app + partner CRUD in Django admin.
- `dietary` app + management commands to seed common diets/allergies.
- Public landing page + 3-step "Apply" form (member story §6).
- Caregiver-on-behalf application flow.
- Admin approval queue.
- **Deliverable:** end-to-end: visitor lands → applies → admin approves → user can log in.

### Phase 2 — Kitchen & inventory backbone (≈ 1–2 sprints)
**Goal:** the operational backbone exists; admins can model real-world kitchen state.
- `kitchens` (kitchens, ingredients, meal_ingredients, ingredient_batches).
- `meals` (recipes with prep/cook time).
- `food_safety` checks (storage temp, cooking temp, cold chain, hygiene, cleaning, pest control).
- Job: nightly check for batches expiring in ≤ 3 days → emails admin.
- Admin UI to record stock receipts, run safety checks.
- **Deliverable:** admin can model their full kitchen and see the expiring-stock alert.

### Phase 3 — Weekly meal planning (≈ 1 sprint)
**Goal:** admins plan the week; members see what's coming.
- `planning.MealPlan` + the 10 km Haversine rule.
- Admin weekly menu planner (desktop-primary, still mobile-readable).
- Member dashboard: "today's meal" card with name, photo, ingredients, allergens flagged against the member's profile.
- Diet-coverage warnings ("no halal Thursday").
- **Deliverable:** admin publishes a week, every member's dashboard updates.

### Phase 4 — Volunteer & delivery flow (≈ 2 sprints) — **mobile-critical**
**Goal:** the daily dispatch loop works end-to-end on a phone.
- `volunteers.Availability` (recurring weekly slots).
- `delivery.Route` + `delivery.Delivery` + `delivery.DeliveryFeedback`.
- Auto-assign service: matches volunteers to routes by proximity + availability.
- Volunteer mobile UI: route map, list of stops, special instructions, swipe-to-mark-delivered, proof-of-delivery photo.
- Member tracking page: live status, volunteer name + photo.
- Caregiver notification (email/SMS) on `failed` delivery.
- 2-tap meal feedback (stars + tag chips).
- **Deliverable:** a full day's dispatch runs through the system; <15 min of admin work per day.

### Phase 5 — Donations & campaigns (≈ 1 sprint)
**Goal:** a stranger can donate in under 30 seconds.
- `donations.Campaign` + `donations.Donation`.
- Stripe Checkout integration (one-time + recurring).
- Public donate page (no account required).
- Receipt email + monthly subscription management.
- Donor impact view ("your $50 = 17 meals").
- **Deliverable:** money flows in; donor sees impact; admin sees campaign progress.

### Phase 6 — Dashboards & reporting (≈ 1 sprint)
**Goal:** admins, partners, and donors all have one screen that tells them what matters.
- Admin home: "what needs attention now" (pending applications, expiring stock, failed deliveries, unassigned routes).
- Partner outcome view: their referred members' status, ratings, retention.
- Donor history view + tax receipts.
- One-click CSV / PDF exports (board report).
- Audit log viewer for admins.
- **Deliverable:** monthly board report generated in one click.

### Phase 7 — Hardening & nice-to-haves (ongoing)
- Service worker / PWA installable + offline route caching for volunteers.
- Field-level encryption for sensitive data.
- Pen-test + WCAG AA audit.
- Performance budget enforcement in CI.

### Phase sequencing rationale
- Foundation → Identity is non-negotiable: nothing else works without a user.
- Kitchen & inventory **before** planning: a meal plan references a meal and a kitchen, so those tables must exist first.
- Planning **before** delivery: a delivery references a `meal_plan_id`.
- Donations is independent and could move earlier if fundraising is urgent.
- Dashboards last because they aggregate across every other app.

---

## 7. Risks & open questions

| Risk | Mitigation |
|---|---|
| Mobile-first discipline drifts as desktop-leaning admins join | Lint rule + PR template checkbox: "tested at 375 px"; Playwright runs in mobile viewport in CI |
| 10 km radius logic gets out of sync with member addresses changing | `validate_radius_assignments` management command in nightly job |
| Audit log volume bloats DB | Partition by month after 12 months; archive to S3 |
| Stripe PCI scope | Use Stripe Checkout (hosted) — we never touch card data |
| Donor abandonment on multi-step form | One-page donate flow, Apple/Google Pay first |
| Volunteer offline gaps in phase 4 (no service worker yet) | Forms queue in `localStorage`, retry on reconnect — interim mitigation until phase 7 |
| Schema MySQL vs Django convention drift | Run `python manage.py inspectdb` against the schema in phase 0 and diff against authored models |

### Open questions for stakeholder confirmation
1. Is **MySQL 8** the production target, or should we move to Postgres for PostGIS later? (Currently: stay on MySQL.)
2. Does the charity have an existing Stripe account, or do we provision one? (Affects phase 5 sequencing.)
3. SMS provider for caregiver alerts — Twilio? (Affects phase 4.)
4. Hosting region — Australian-region S3 + VPS for data residency? (Likely yes.)
5. Should the existing `index.html` prototype be treated as **visual reference only**, or do you want pixel-level fidelity?
6. Confirm operating time zone (this doc assumes `Australia/Melbourne`).
7. Sprint length assumed in phasing (≈ 2 weeks) — confirm or adjust phase estimates.

---

## 8. Definition of done for this roadmap

This roadmap is "done" when:
- [x] Stack chosen and justified.
- [x] All 20 schema tables mapped to Django apps.
- [x] Mobile-first principles enumerated.
- [x] Phases sized, sequenced, and each with a clear deliverable.
- [x] Cross-cutting concerns (auth, roles, soft delete, geo, privacy, money) named with a chosen approach.
- [x] Risks and open questions surfaced.
- [ ] Stakeholder (Hare Om) signs off in writing.
- [ ] Phase 0 brainstorm starts.

---

## 9. Next step

Once this roadmap is approved, the **next action is to brainstorm Phase 0** (Foundation) in detail and produce its own implementation plan via the `superpowers:writing-plans` skill. Do not start writing code from this document — it is a map, not an implementation.
