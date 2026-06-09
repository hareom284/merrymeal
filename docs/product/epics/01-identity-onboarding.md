# Epic 01 — Identity & onboarding

> **Goal:** a visitor can apply to become a member; an admin can approve them.
> By the end of this epic, the system has real people in it for the first time.

**Sprints:** 2 (Sprint 02 + Sprint 03)
**Status:** not started
**Depends on:** Epic 00 done.
**Source spec:** [Roadmap §6, Phase 1](../../superpowers/specs/2026-06-01-merrymeal-django-design.md)

---

## Why this epic exists

The charity currently runs intake on a paper form + phone calls. Margaret's
daughter spent 40 minutes on the phone to get her enrolled. After this epic
the same enrolment takes 5 minutes online, and admins approve from a queue
instead of a spreadsheet.

This epic also seats every supporting data model the rest of the system
needs: `Partner` (referring organisations), `Address` + `City` (delivery
locations), `DietPreference` + `Allergy` (used by the meal-planner to flag
unsafe meals).

---

## Personas in scope

- **Member (applicant)** — Margaret, 84, low vision, on a phone.
- **Caregiver-on-behalf** — Margaret's daughter, applying for Margaret.
- **Partner referrer** — a social worker at a referring charity submitting a member on behalf of a client.
- **Admin** — operations staff who approves or rejects applications.

---

## Stories

### Story 1.1 — `City` model + admin
**STATUS: done (sprint-02/03)**

**As an** admin
**I want** a list of cities to choose from when creating addresses
**so that** members and kitchens share a controlled city vocabulary instead of free-text typos.

**Acceptance criteria:**
- [ ] `apps/accounts/models/cities.py::City` with `name`, plus `TimeStampedModel` + soft delete.
- [ ] Django admin: list, search by name, create/edit/delete.
- [ ] Migration creates the `cities` table matching the schema.
- [ ] A management command `seed_cities` populates 5 starter cities
      (Melbourne, Geelong, Ballarat, Bendigo, Frankston).

**Technical notes:**
- Files: `apps/accounts/models/cities.py`, `apps/accounts/admin.py` (extend),
  `apps/accounts/management/commands/seed_cities.py`,
  `apps/accounts/tests/test_cities.py`.
- DB tables touched: `cities`.

**Mobile viewport:** N/A (admin only).
**Test strategy:** model unit tests + admin smoke test.

---

### Story 1.2 — `Address` model with lat/lng
**STATUS: done (sprint-02/03)**

**As a** member
**I want** to register one or more delivery addresses
**so that** I can be served at home and, e.g., my daughter's house when I'm visiting.

**Acceptance criteria:**
- [ ] `apps/accounts/models/addresses.py::Address` matching the
      `user_addresses` schema: `user_id`, `label`, `postal_code`, `city_id`,
      `latitude`, `longitude`.
- [ ] A user may have many addresses (no unique constraint on `user_id`).
- [ ] `latitude` / `longitude` are `DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)`.
- [ ] Django admin lists addresses inline on the User change page.

**Technical notes:**
- Files: `apps/accounts/models/addresses.py`, `apps/accounts/admin.py`,
  `apps/accounts/tests/test_addresses.py`.
- DB tables touched: `user_addresses`.
- **Do not** geocode here. Geocoding (turning postcode → lat/lng) lands in
  Story 1.10. For now, an address may be saved with null lat/lng.

**Mobile viewport:** N/A.
**Test strategy:** model unit tests; admin smoke test.

---

### Story 1.3 — `CaregiverLink` model
**STATUS: done (sprint-02/03)**

**As a** caregiver
**I want** to be linked to the members I look after, with a recorded relationship type
**so that** I see only their data and the system can notify me when their delivery fails.

**Acceptance criteria:**
- [ ] `apps/accounts/models/caregiver_links.py::CaregiverLink` matching
      `member_caregivers`: `member_id`, `caregiver_id`, `relationship` enum.
- [ ] Unique constraint on (`member_id`, `caregiver_id`).
- [ ] Validation: `member.role == 'member'` and `caregiver.role == 'caregiver'`.
- [ ] Django admin lists caregiver links inline on User.

**Technical notes:**
- Files: `apps/accounts/models/caregiver_links.py`,
  `apps/accounts/services/caregiver_links.py` for the link-creating service,
  `apps/accounts/tests/test_caregiver_links.py`.
- DB tables touched: `member_caregivers`.

**Mobile viewport:** N/A (UI lands in later stories).
**Test strategy:** model + service unit tests covering the role-validation paths.

---

### Story 1.4 — `partners` app: `Partner` model + admin CRUD
**STATUS: done (sprint-02/03)**

**As an** admin
**I want** to manage charities, restaurants, suppliers, and corporate partners
**so that** members can be linked to a referring organisation and kitchens can be linked to their operator.

**Acceptance criteria:**
- [ ] New app: `apps/partners/`.
- [ ] `apps/partners/models/partners.py::Partner` matching the `partners` schema.
- [ ] Django admin CRUD with `type` filter.
- [ ] `User.partner` FK now formally added (Story 0.5 left this commented).
      Migration adds the FK from `users.partner_id` → `partners.id`, nullable.

**Technical notes:**
- Files: `apps/partners/{__init__,apps,admin,models/__init__,models/partners,tests/test_partners}.py`.
- `INSTALLED_APPS` updated in `config/settings/base.py`.
- DB tables touched: `partners`, `users` (add FK).

**Mobile viewport:** N/A.
**Test strategy:** model + admin smoke test.

---

### Story 1.5 — `dietary` app: `DietPreference` and `Allergy` (M2M scaffolding)
**STATUS: done (sprint-02/03)**

**As an** admin
**I want** a controlled list of diet preferences and allergies
**so that** members can declare them and the planner can flag unsafe meals later.

**Acceptance criteria:**
- [ ] New app `apps/dietary/` with models `DietPreference`, `Allergy`,
      `UserDietPreference`, `UserAllergy` matching the schema.
- [ ] Composite PK on the through tables, matching schema.
- [ ] Management command `seed_dietary` seeds: vegetarian, vegan, halal,
      kosher, gluten-free, diabetic-friendly, low-sodium, pureed; allergies:
      peanut, tree nut, dairy, egg, soy, shellfish, gluten.
- [ ] Django admin CRUD for both, listed inline on User.

**Technical notes:**
- Files: `apps/dietary/{__init__,apps,admin,models/__init__,models/diet,models/allergy,management/commands/seed_dietary,tests/test_dietary}.py`.
- DB tables touched: `diet_preferences`, `diet_preference_user`, `allergies`, `allergy_user`.

**Mobile viewport:** N/A.
**Test strategy:** unit tests for the seed command (idempotent) + model unit tests.

---

### Story 1.6 — Public landing page
**STATUS: done (sprint-02/03)**

**As a** visitor (member or caregiver)
**I want** a clear landing page with one "Apply" button
**so that** I do not have to read marketing copy to find the entry point.

**Acceptance criteria:**
- [ ] Route `/` renders the landing page.
- [ ] Single full-width hero: charity tagline + "Apply for meals" button.
- [ ] Three short cards: "For members", "For caregivers", "For volunteers"
      with one-line descriptions and a secondary link.
- [ ] No login required to view.
- [ ] Mobile-first at 375 px — hero stacks above the cards; cards stack
      vertically below 768 px.
- [ ] WCAG AA contrast on every text block; tested with the
      `axe` browser plugin and the result documented in the PR.

**Technical notes:**
- Files: `apps/dashboards/views/landing.py`,
  `templates/dashboards/landing.html`, `config/urls.py` route.
- No DB tables touched.

**Mobile viewport:** required.
**Test strategy:** Playwright at 375 px asserts the hero CTA is visible without scrolling.

---

### Story 1.7 — Member application — step 1 (contact)
**STATUS: done (sprint-02/03)**

**As a** prospective member
**I want** to start an application by giving my contact details
**so that** I can be reached without phoning the office.

**Acceptance criteria:**
- [ ] Route `/apply/` shows step 1.
- [ ] Fields: full name, email (unique), DOB, phone (optional).
- [ ] Inline validation errors at 375 px (no field clipping).
- [ ] On submit, an `Application` row (see technical notes) is created in
      `draft` state with a session token; the visitor is redirected to step 2.
- [ ] The progress indicator shows "Step 1 of 3".

**Technical notes:**
- Files: `apps/accounts/models/applications.py::Application` (new — not in
  the SQL schema; this is the working draft before approval),
  `apps/accounts/forms/application.py::ApplicationContactForm`,
  `apps/accounts/views/application.py::application_step_1`,
  `apps/accounts/services/applications.py::create_draft_application`,
  `templates/accounts/application/step_1.html`,
  `templates/accounts/application/_progress.html`,
  `apps/accounts/tests/test_application_step_1.py`.
- Email must not collide with an existing `users.email`.
- DB tables touched: new `applications` table (migration); no `users` write yet.

**Mobile viewport:** required. 18 px base font for the form.
**Test strategy:**
- Unit: form validation (duplicate email, missing field, bad email format).
- Playwright at 375 px: happy path through the form; field errors visible.

---

### Story 1.8 — Member application — step 2 (address)
**STATUS: done (sprint-02/03)**

**As a** prospective member
**I want** to enter my delivery address with city + postcode
**so that** the charity knows where to deliver.

**Acceptance criteria:**
- [ ] Route `/apply/address/` (continues the application from step 1).
- [ ] Fields: address label (default "Home"), street line, postcode, city (dropdown from `City` rows).
- [ ] Map preview is **out of scope** for this story.
- [ ] On submit, an `Address` row is created and linked to the draft
      application (not yet to a `User` — the user is only created on approval).
- [ ] Progress indicator shows "Step 2 of 3".

**Technical notes:**
- Files: `apps/accounts/forms/application.py::ApplicationAddressForm`,
  `apps/accounts/views/application.py::application_step_2`,
  `templates/accounts/application/step_2.html`,
  `apps/accounts/tests/test_application_step_2.py`.
- The address sits on the `Application` row until approval (Story 1.11)
  copies it onto the new `User`'s `Address`.
- DB tables touched: `applications` (UPDATE).

**Mobile viewport:** required.
**Test strategy:** unit (form) + Playwright happy path.

---

### Story 1.9 — Member application — step 3 (dietary + allergies)
**STATUS: done (sprint-02/03)**

**As a** prospective member
**I want** to declare my diet preferences and allergies up-front
**so that** the kitchen never serves me food I cannot eat.

**Acceptance criteria:**
- [ ] Route `/apply/dietary/`.
- [ ] Multi-select chips for diet preferences (from `DietPreference`) and
      allergies (from `Allergy`).
- [ ] Touch targets ≥ 44 px.
- [ ] "I don't have any" toggle for each section.
- [ ] On submit, the application moves to `submitted` state and a
      confirmation screen renders.
- [ ] The applicant receives an email: "We've got it. We'll be in touch in
      3–5 business days."

**Technical notes:**
- Files: `apps/accounts/forms/application.py::ApplicationDietaryForm`,
  `apps/accounts/views/application.py::application_step_3`,
  `apps/accounts/services/applications.py::submit_application`,
  `templates/accounts/application/step_3.html`,
  `templates/accounts/emails/application_received.{html,txt}`,
  `apps/accounts/tests/test_application_step_3.py`.
- DB tables touched: `applications`. (The eventual `diet_preference_user`
  and `allergy_user` writes happen on approval — Story 1.11.)

**Mobile viewport:** required.
**Test strategy:** unit (form + service) + Playwright happy path + email
asserted via `django.core.mail.outbox`.

---

### Story 1.10 — Caregiver-on-behalf application
**STATUS: done (sprint-02/03)**

**As a** caregiver
**I want** to apply on behalf of someone I look after, declaring the relationship
**so that** I can enrol my elderly relative who can't use a computer.

**Acceptance criteria:**
- [ ] Toggle on step 1: "I'm applying for someone else".
- [ ] When toggled on, step 1 collects the **caregiver's** contact details
      AND the **member's** contact details.
- [ ] An extra "relationship" dropdown (family / friend / nurse /
      social_worker / other) appears.
- [ ] On approval (Story 1.11), **two** `User` rows are created and linked
      via `CaregiverLink`.
- [ ] If the caregiver already has an account (email matches existing
      `users.email`), no duplicate caregiver is created — the link is added
      to the existing caregiver account, and the form prompts the caregiver
      to log in.

**Technical notes:**
- Files: extend `apps/accounts/forms/application.py` and
  `apps/accounts/services/applications.py::submit_application` /
  `approve_application`.
- DB tables touched (on approval): `users` (×2), `member_caregivers`.
- Add an "applying_for_other" boolean to the `applications` table.

**Mobile viewport:** required.
**Test strategy:** unit covering both branches (new caregiver vs existing caregiver) + Playwright.

---

### Story 1.11 — Admin approval queue list view
**STATUS: done (sprint-02/03)**

**As an** admin
**I want** to see a list of submitted applications, newest first
**so that** I know what is waiting for me.

**Acceptance criteria:**
- [ ] Route `/admin/applications/` (NOT inside the Django admin — a
      dedicated tailored screen).
- [ ] Lists `submitted` applications: name, email, suburb, dietary chips,
      submitted-at, "applying for other" badge if applicable.
- [ ] Filter by city + by "has allergies".
- [ ] Click row → application detail (Story 1.12).
- [ ] Restricted by `@role_required('admin')`.

**Technical notes:**
- Files: `apps/dashboards/views/admin_applications.py`,
  `apps/dashboards/urls.py`, `templates/dashboards/admin/applications_list.html`,
  `apps/dashboards/tests/test_admin_applications.py`.
- DB tables touched: read-only on `applications`.

**Mobile viewport:** mobile-readable but desktop-primary (admins on laptops).
**Test strategy:** unit + Playwright at 1024 px happy path.

---

### Story 1.12 — Admin approve / reject action
**STATUS: done (sprint-02/03)**

**As an** admin
**I want** to approve or reject an application with one click
**so that** I can clear the queue in under five minutes.

**Acceptance criteria:**
- [ ] Application detail page shows everything the applicant submitted.
- [ ] "Approve" button (primary):
  - Creates `User` row(s) with `role='member'` (and caregiver if applicable).
  - Creates `Address` row.
  - Creates `UserDietPreference` and `UserAllergy` rows.
  - Creates `CaregiverLink` row if applying for other.
  - Sends a "welcome — set your password" email with a one-time link.
  - Updates the application to `approved` state, records `approved_by` and `approved_at`.
- [ ] "Reject" button (secondary) requires a reason; sends a polite rejection email.
- [ ] **Atomic:** all the DB writes happen in one transaction. If any one fails, no rows are created.
- [ ] Audit log entry recorded.

**Technical notes:**
- Files: `apps/accounts/services/applications.py::approve_application`,
  `reject_application`; extend `apps/dashboards/views/admin_applications.py`;
  `templates/accounts/emails/welcome_set_password.{html,txt}`,
  `templates/accounts/emails/application_rejected.{html,txt}`.
- DB tables touched: `users`, `user_addresses`, `diet_preference_user`,
  `allergy_user`, `member_caregivers`, `applications`, plus the audit log.

**Mobile viewport:** mobile-readable, desktop-primary.
**Test strategy:**
- Unit: service-level tests for approve (member-only path AND
  caregiver+member path), reject, transaction atomicity (force one write
  to fail and assert nothing committed).
- Playwright: approve → applicant receives email → can log in.

---

## Backlog (not in sprint 02 / 03 yet)

- **1.13 — Member self-service profile edit** (own contact info, addresses,
  dietary). Lands in Sprint 06 or earlier if there is capacity.
- **1.14 — Caregiver self-service: add a new member link** to an existing
  member. Stretch goal.
- **1.15 — Partner referral form** (a public form that lets a partner
  submit a member on behalf of their client; lands in Epic 06).
- **1.16 — "Forgot your address?" lookup by postcode** — small UX polish.

---

## Demo for end of Epic 01

A teammate plays "Margaret's daughter":

1. Visits `/`, taps **Apply for meals**.
2. Toggles "applying for someone else", completes all three steps using her
   mum's details.
3. Receives "we got it" email.
4. Another teammate plays the admin: opens `/admin/applications/`, sees the
   application, clicks **Approve**.
5. Margaret receives a welcome email, clicks the link, sets a password, logs in.
6. Margaret sees her (empty) dashboard.
