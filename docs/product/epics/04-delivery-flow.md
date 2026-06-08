# Epic 04 — Volunteer & delivery flow (mobile-critical)

> **Goal:** the daily dispatch loop works end-to-end on a phone. A volunteer
> opens the app on their bike, sees the route, taps stops as delivered, and
> a member's caregiver gets notified when a delivery fails.

**Sprints:** 2 (Sprint 07 + Sprint 08)
**Status:** not started
**Depends on:** Epic 01 (Users), Epic 03 (MealPlan exists for deliveries to reference).
**Source spec:** [Roadmap §6, Phase 4](../../superpowers/specs/2026-06-01-merrymeal-django-design.md)

---

## Why this epic exists

The volunteer experience is where mobile-first stops being a slogan and
becomes the difference between a delivered meal and an undelivered one.
Sarah is on a bike. The wind is up. She has 14 stops. The app needs to be
tappable, readable in sun, forgiving of one-handed use, and resilient when
signal drops between addresses.

By the end of this epic, the charity can replace the daily phone-and-WhatsApp
dispatch with a system that auto-assigns routes, gives every volunteer a
single-screen day, captures proof of delivery, and alerts a caregiver
within seconds of a failed delivery.

---

## Personas in scope

- **Volunteer** — Sarah, phone, often outdoors, sometimes patchy signal.
- **Member** — wants to know if today's meal is on the way.
- **Caregiver** — wants to be told immediately if today's meal did not arrive.
- **Admin** — needs to be able to override an assignment (sick volunteer, last-minute add).

---

## Stories

### Story 4.1 — `volunteers` app: `Availability` model
**STATUS: done (sprint-07)**

**As a** volunteer
**I want** to declare which days and times of the week I am available
**so that** the auto-assigner knows when to count me in.

**Acceptance criteria:**
- [ ] New app `apps/volunteers/`.
- [ ] `apps/volunteers/models/availabilities.py::Availability` matching
      schema (`volunteer_id`, `day_of_week`, `day_phrase`).
- [ ] Validation: `volunteer.role == 'volunteer'`.
- [ ] No unique constraint — a volunteer may be available `mon morning`
      AND `mon afternoon`.

**Technical notes:**
- Files: `apps/volunteers/{__init__,apps,admin,models/__init__,models/availabilities,tests/test_availabilities}.py`.
- DB tables touched: `volunteer_availabilities`.

**Mobile viewport:** N/A (UI in Story 4.2).
**Test strategy:** model + role-validation tests.

---

### Story 4.2 — Volunteer availability editor (mobile)
**STATUS: done (sprint-07)**

**As a** volunteer
**I want** a simple grid (days × morning/afternoon/evening) on my phone
**so that** I can update my availability in 30 seconds before bed.

**Acceptance criteria:**
- [ ] Route `/volunteer/availability/`.
- [ ] 7-row × 3-column grid of toggleable cells.
- [ ] Tap a cell → row added/removed via HTMX, no full reload.
- [ ] Mobile-first at 375 px, cells ≥ 44 × 44 px.

**Technical notes:**
- Files: `apps/volunteers/views/availability.py`,
  `apps/volunteers/services/availability.py::toggle_slot`,
  `apps/volunteers/urls.py`,
  `templates/volunteers/availability.html`,
  `templates/volunteers/_slot_cell.html` (HTMX),
  `apps/volunteers/tests/test_availability_view.py`.
- DB tables touched: `volunteer_availabilities`.

**Mobile viewport:** required.
**Test strategy:** unit (toggle service) + Playwright at 375 px.

---

### Story 4.3 — `delivery` app: `Route` model
**STATUS: done (sprint-07)**

**As a** developer
**I want** a `Route` model representing "one volunteer's deliveries on one day"
**so that** the system has a unit to assign, dispatch, and report on.

**Acceptance criteria:**
- [ ] New app `apps/delivery/`.
- [ ] `apps/delivery/models/routes.py::Route` matching schema:
      `volunteer_id`, `route_date`, `status` (`planned`, `in_progress`,
      `completed`, `cancelled`).
- [ ] Admin CRUD + filter by date + volunteer.

**Technical notes:**
- Files: `apps/delivery/{__init__,apps,admin,models/__init__,models/routes,tests/test_routes}.py`.
- DB tables touched: `routes`.

**Mobile viewport:** N/A.
**Test strategy:** model + admin smoke.

---

### Story 4.4 — `Delivery` model
**STATUS: done (sprint-07)**

**As a** developer
**I want** a `Delivery` row per (member, meal_plan, scheduled_date)
**so that** the system has the smallest unit of "did Margaret get her meal today?".

**Acceptance criteria:**
- [ ] `apps/delivery/models/deliveries.py::Delivery` matching schema:
      `route_id` (nullable), `meal_plan_id`, `volunteer_id`, `member_id`,
      `member_address_id`, `meal_type` (`fresh`/`frozen`), `status`
      (`pending`, `out_for_delivery`, `delivered`, `failed`),
      `scheduled_date`, `delivered_time`, `latitude`, `longitude`,
      `photo` URL.
- [ ] `meal_type` is auto-set on creation via
      `planning.services.assign_meal_type(member, meal_plan.kitchen, scheduled_date)` (from Story 3.2).
- [ ] Admin list with filters by status + date.

**Technical notes:**
- Files: `apps/delivery/models/deliveries.py`,
  `apps/delivery/services/deliveries.py::create_delivery`,
  `apps/delivery/tests/test_deliveries.py`.
- DB tables touched: `deliveries`.

**Mobile viewport:** N/A.
**Test strategy:** unit covering `meal_type` auto-assignment.

---

### Story 4.5 — `DeliveryFeedback` model
**STATUS: done (sprint-07)**

**As a** member
**I want** to rate the meal I received and add an optional note
**so that** the kitchen knows what's working.

**Acceptance criteria:**
- [ ] `apps/delivery/models/feedback.py::DeliveryFeedback` matching schema:
      `delivery_id` (unique), `rating` (1–5), `note`.
- [ ] One feedback per delivery (true 1:1).

**Technical notes:**
- Files: `apps/delivery/models/feedback.py`,
  `apps/delivery/tests/test_feedback.py`.
- DB tables touched: `delivery_feedback`.
- UI lands in Story 4.11.

**Mobile viewport:** N/A.
**Test strategy:** unit covering the 1:1 constraint.

---

### Story 4.6 — Auto-assign service: generate today's deliveries
**STATUS: done (sprint-07)**

**As an** admin
**I want** a job that turns "today's `MealPlan` × every active member" into one `Delivery` row per member
**so that** I do not hand-build the day's delivery list.

**Acceptance criteria:**
- [ ] `apps/delivery/services/dispatch.py::generate_deliveries_for_date(date)` is idempotent.
- [ ] For each active member with at least one address:
  - Find their `primary_address`.
  - Find the closest active `Kitchen` (Haversine).
  - Find the `MealPlan` for (that kitchen, that date). Skip if none.
  - Create a `Delivery` in `pending` state via Story 4.4's service.
- [ ] Wired to Django-Q2: runs at 04:00 Melbourne time daily.
- [ ] Idempotency: re-running on the same date does not duplicate
      deliveries (unique on `member_id` + `scheduled_date`).

**Technical notes:**
- Files: `apps/delivery/services/dispatch.py`,
  `apps/delivery/tasks/generate_deliveries.py`,
  `apps/delivery/tests/test_dispatch.py`.
- DB tables touched: `deliveries` (write).

**Mobile viewport:** N/A.
**Test strategy:**
- Unit: 3 members × 1 plan → 3 deliveries; re-run → still 3.
- Unit: member with no address → skipped, no row, log line emitted.
- Unit: weekend run → all deliveries get `meal_type='frozen'`.

---

### Story 4.7 — Auto-assign service: pack today's deliveries into routes
**STATUS: done (sprint-07)**

**As an** admin
**I want** today's `pending` deliveries grouped into `Route`s assigned to available volunteers, balanced by proximity
**so that** the daily dispatch happens without human intervention 95% of the time.

**Acceptance criteria:**
- [ ] `apps/delivery/services/dispatch.py::assign_routes_for_date(date)`.
- [ ] For each kitchen-date pair with pending deliveries:
  - Find volunteers whose `Availability` overlaps with that day + phrase
    (`morning` for v1).
  - Greedy-pack: sort deliveries by distance from kitchen; chunk into
    routes of ≤ 12 deliveries per volunteer.
  - Create a `Route` per chunk; set `Delivery.route_id` and
    `Delivery.volunteer_id`; set `Route.status='planned'`.
- [ ] Idempotent: re-running for the same date does not double-assign.
- [ ] Edge case: too many deliveries for available volunteers → unassigned
      deliveries surface on the admin "needs attention" widget (Epic 06).
- [ ] Runs daily at 04:30 Melbourne time after Story 4.6.

**Technical notes:**
- Files: extend `apps/delivery/services/dispatch.py`,
  `apps/delivery/tasks/assign_routes.py`,
  `apps/delivery/tests/test_assign_routes.py`.
- For v1, "balanced by proximity" = sort by Haversine from kitchen and
  pack greedily. Proper VRP (vehicle routing problem) is **out of scope**.

**Mobile viewport:** N/A.
**Test strategy:**
- Unit covering: 6 deliveries / 2 volunteers → 2 routes of 3.
- Unit covering: 30 deliveries / 1 volunteer → route capped at 12, 18 unassigned.
- Unit covering: no available volunteers → all deliveries remain unassigned, no exception.

---

### Story 4.8 — Volunteer "today" route screen (mobile)
**STATUS: done (sprint-08)**

**As a** volunteer
**I want** one screen with my route for today: pickup info at the top, then a list of stops in order, with a "Mark delivered" button anchored at the bottom of the screen for the current stop
**so that** I can drive/cycle with one thumb.

**Acceptance criteria:**
- [ ] Route `/volunteer/today/`.
- [ ] Top card: kitchen name + address + pickup time (5 minutes before route start).
- [ ] List of stops in greedy-nearest order; current stop is highlighted.
- [ ] Each stop card shows: member's first name + initial, address,
      special instructions, allergen warning (re-using Epic 03 logic).
- [ ] Bottom-anchored CTA "Mark <name> delivered" (thumb-zone).
- [ ] Tapping a stop reveals the address + phone in expanded form.
- [ ] Restricted to `volunteer` role; volunteer sees only their own route.

**Technical notes:**
- Files: `apps/delivery/views/volunteer_today.py`,
  `apps/delivery/services/volunteer_today.py::get_today_route(user)`,
  `templates/delivery/volunteer/today.html`,
  `templates/delivery/volunteer/_stop_card.html`,
  `apps/delivery/tests/test_volunteer_today.py`.

**Mobile viewport:** **the** mobile screen of this app. 18 px base font.
**Test strategy:**
- Unit: volunteer with 3 stops, 1 already delivered → screen shows 2 left, current = next pending.
- Playwright at 375 × 667 px: page loads, no horizontal scroll, "Mark
  delivered" button is in bottom 1/3 of the screen, ≥ 44 px tall.

---

### Story 4.9 — Mark-delivered with proof-of-delivery photo
**STATUS: done (sprint-08)**

**As a** volunteer
**I want** to tap "Mark delivered", take a photo (via the phone camera), and move to the next stop
**so that** the system has proof and the member's caregiver sees a green tick within seconds.

**Acceptance criteria:**
- [ ] Tap "Mark delivered" → mobile camera opens (`<input type="file" capture="environment">`).
- [ ] Photo uploads to S3 via `django-storages`; URL stored on `Delivery.photo`.
- [ ] `Delivery.status = 'delivered'`, `delivered_time = now()`,
      `latitude`/`longitude` from the browser Geolocation API (if denied,
      saved as null, no error).
- [ ] After upload, the screen auto-advances to the next stop.
- [ ] If the upload fails (no signal), the action is queued in
      `localStorage` and retried; the stop card shows a "queued — will
      retry" badge in the meantime. Offline sync is interim until full PWA
      (Epic 07).

**Technical notes:**
- Files: extend `apps/delivery/views/volunteer_today.py` with
  `mark_delivered` view (HTMX endpoint),
  `apps/delivery/services/mark_delivered.py`,
  `static/src/volunteer-offline.js` (queue + retry),
  `apps/delivery/tests/test_mark_delivered.py`.
- S3 bucket + IAM via `django-storages` config in `prod.py`.
- DB tables touched: `deliveries` (UPDATE).
- Audit log entry on status change.

**Mobile viewport:** required.
**Test strategy:**
- Unit: mark_delivered sets status, time, audit row.
- Playwright at 375 px: full happy path with a stubbed file input.
- Manual: physical device test (sprint demo).

---

### Story 4.10 — Mark-failed with reason
**STATUS: done (sprint-08)**

**As a** volunteer
**I want** to mark a delivery as failed with a reason (not home / no answer / refused / address wrong)
**so that** the caregiver is notified and the admin can follow up.

**Acceptance criteria:**
- [ ] On the stop card, a small "Couldn't deliver" link (less visually
      prominent than the green CTA — failure should not be the easy default).
- [ ] Tap → bottom sheet with four reason chips + a notes textarea.
- [ ] Sets `Delivery.status='failed'` + writes `notes` to a new column
      `Delivery.failure_reason`.
- [ ] Triggers Story 4.13's caregiver-alert side effect.
- [ ] Audit log entry.

**Technical notes:**
- Files: extend `apps/delivery/views/volunteer_today.py` with
  `mark_failed`, extend templates, migration adds `failure_reason`.
- DB tables touched: `deliveries` (UPDATE).

**Mobile viewport:** required.
**Test strategy:** unit + Playwright at 375 px.

---

### Story 4.11 — 2-tap meal feedback (member)
**STATUS: done (sprint-08)**

**As a** member
**I want** to rate the meal I just received with two taps — stars + one of a few tag chips
**so that** I can give feedback without typing.

**Acceptance criteria:**
- [ ] After a delivery is marked `delivered`, the member's "today" card
      shows a feedback prompt.
- [ ] Tap one of 5 stars; then tap one or more chip tags (Great, Bland,
      Too cold, Too small, Loved it).
- [ ] On submit, `DeliveryFeedback` row created; thank-you card replaces
      the prompt.
- [ ] Tags map to enum values stored in `DeliveryFeedback.note` (JSON-encoded list).
- [ ] Mobile-first at 375 px; touch targets ≥ 44 px.

**Technical notes:**
- Files: `apps/delivery/views/feedback.py`,
  `apps/delivery/forms/feedback.py`,
  `apps/delivery/services/feedback.py::record_feedback`,
  `templates/delivery/member/_feedback_card.html`,
  `apps/delivery/tests/test_feedback_view.py`.

**Mobile viewport:** required.
**Test strategy:** unit + Playwright at 375 px.

---

### Story 4.12 — Member tracking page ("is it on the way?")
**STATUS: done (sprint-08)**

**As a** member or caregiver
**I want** to refresh a page and see whether today's meal is pending, on the way, or delivered
**so that** I do not have to phone anyone to find out.

**Acceptance criteria:**
- [ ] On the member home (Story 3.4), the today card displays the live
      `Delivery.status` plus the volunteer's first name + last initial when
      the status is `out_for_delivery`.
- [ ] HTMX polls every 60 seconds while status is `pending` or `out_for_delivery`.
- [ ] When status flips to `delivered`, polling stops and a "Delivered ✓
      at HH:mm" badge appears.

**Technical notes:**
- Files: extend `apps/dashboards/views/member_home.py`, add HTMX `hx-get`
  + `hx-trigger="every 60s"`,
  `apps/dashboards/tests/test_member_tracking.py`.

**Mobile viewport:** required.
**Test strategy:** unit + Playwright at 375 px.

---

### Story 4.13 — Caregiver alert on failed delivery (email + SMS)
**STATUS: done (sprint-08)**

**As a** caregiver
**I want** an email AND text within 60 seconds of a member's delivery failing
**so that** I can step in (call, drop by, redeliver tomorrow).

**Acceptance criteria:**
- [ ] When a `Delivery.status` transitions to `failed`, a Django signal
      enqueues an email + SMS task per linked caregiver.
- [ ] Email + SMS contain: member's name, scheduled date, the reason, and
      a link to call the volunteer (if the volunteer consented to share
      their phone) OR a link to call the charity office.
- [ ] SMS provider abstraction: `apps/core/services/sms.py::send_sms(to, body)`.
      v1 implementation uses Twilio in prod and a console backend in dev / test.
- [ ] If a member has no linked caregiver, the office email address is the fallback.

**Technical notes:**
- Files: `apps/core/services/sms.py`,
  `apps/delivery/services/alerts.py::notify_caregivers_of_failure`,
  `apps/delivery/signals.py` (post-save on Delivery status change),
  `templates/delivery/emails/delivery_failed.{html,txt}`,
  `apps/delivery/tests/test_caregiver_alert.py`.
- New settings: `TWILIO_*` in `.env.example`, `SMS_BACKEND` setting (dev=console).
- DB tables touched: read-only.

**Mobile viewport:** N/A (notifications).
**Test strategy:** unit using `django.core.mail.outbox` + a fake SMS backend.

---

### Story 4.14 — Admin reassignment widget
**STATUS: done (sprint-08)**

**As an** admin
**I want** to reassign a delivery to a different volunteer at any time
**so that** sick days and last-minute add-ons do not break the day.

**Acceptance criteria:**
- [ ] On the admin's "today" widget (Epic 06 will polish; for now a basic
      list at `/admin/today/`), each delivery has a "Reassign" button.
- [ ] Picker lists available volunteers; on save, `Delivery.volunteer_id`
      and `route_id` updated and an audit-log row written.
- [ ] The previous volunteer's `today` screen reflects the change on next poll.

**Technical notes:**
- Files: `apps/delivery/views/admin_reassign.py`,
  `apps/delivery/services/reassign.py`,
  `templates/delivery/admin/_reassign_modal.html`,
  `apps/delivery/tests/test_admin_reassign.py`.

**Mobile viewport:** mobile-readable; desktop-primary.
**Test strategy:** unit + Playwright at 1024 px.

---

## Backlog (not in sprint 07 / 08 yet)

- **4.15 — Volunteer route map** — Leaflet + OSM tiles. Stretch goal.
- **4.16 — Volunteer pickup confirmation** — tap when stock is collected
  from kitchen, sets `Route.status='in_progress'`. Add when the volunteer
  is reading the route screen reliably.
- **4.17 — Swipe-to-mark-delivered** — gesture polish on top of Story 4.9.
- **4.18 — Volunteer settings: phone visibility consent**.

---

## Demo for end of Epic 04

A teammate plays Sarah (volunteer) on a phone:

1. Logs in at 06:30. Opens `/volunteer/today/`. Sees 4 stops.
2. Drives to kitchen, taps the first stop expanded view, drives to Margaret.
3. Taps "Mark Margaret delivered", camera opens, takes photo, photo uploads.
4. Screen advances to stop 2.
5. At stop 3, no one home — taps "Couldn't deliver", chooses "No answer".
6. Within 30 seconds, Margaret's daughter receives a text and an email.
7. The admin opens `/admin/today/`, sees stop 3 as failed, and reassigns
   it to a different volunteer for redelivery tomorrow.

**Bonus:** turn off wifi during stop 4; the mark-delivered queues in
`localStorage`, then syncs when wifi is back.
