# Epic 05 — Donations & campaigns

> **Goal:** a stranger can donate in under 30 seconds. Recurring donors stay
> on a charity rail. Admin sees campaign progress.

**Sprints:** 1 (Sprint 09)
**Status:** not started
**Depends on:** Epic 00 only (donations can ship independently of meal flow).
Could even move earlier if fundraising is the urgent constraint.
**Source spec:** [Roadmap §6, Phase 5](../../superpowers/specs/2026-06-01-merrymeal-django-design.md)

---

## Why this epic exists

The charity's current donation channel is a manual bank-transfer page; we
estimate it loses 60–70 % of would-be donors before completion. Stripe
Checkout (hosted) lets us hand off PCI scope, accept Apple Pay / Google
Pay from a mobile, and recover that pipeline in a single sprint.

---

## Personas in scope

- **Donor** — Anyone with $10 to spare. May not have a MerryMeal account.
- **Admin** — wants to see how a campaign is tracking and pull a list of receipts at tax time.
- **Partner** — corporate sponsor whose name appears on campaign-attribution reports.

---

## Stories

### Story 5.1 — `donations` app: `Campaign` model
**STATUS: backlog**

**As an** admin
**I want** to define campaigns with a goal, start/end dates, and a partner attribution
**so that** donations can be grouped and partner sponsorship recognised.

**Acceptance criteria:**
- [ ] New app `apps/donations/`.
- [ ] `apps/donations/models/campaigns.py::Campaign` matching schema:
      `name`, `goal_cents`, `start_at`, `end_at`, `is_active`, `partner_id`.
- [ ] Django admin CRUD, list shows progress bar (raised / goal).
- [ ] Money fields **always integer cents** (no floats).

**Technical notes:**
- Files: `apps/donations/{__init__,apps,admin,models/__init__,models/campaigns,tests/test_campaigns}.py`.
- DB tables touched: `campaigns`.

**Mobile viewport:** N/A.
**Test strategy:** model + admin smoke.

---

### Story 5.2 — `Donation` model
**STATUS: backlog**

**As a** developer
**I want** a `Donation` row per pledge with payment status
**so that** the system has one source of truth for raised money.

**Acceptance criteria:**
- [ ] `apps/donations/models/donations.py::Donation` matching schema:
      `donor_id`, `campaign_id`, `amount_cents`, `payment_type` enum,
      `status` enum (`pending`, `completed`, `failed`, `refunded`),
      `transaction_id`.
- [ ] Admin list with filters by campaign + status, sort by amount desc.

**Technical notes:**
- Files: `apps/donations/models/donations.py`,
  `apps/donations/tests/test_donations.py`.
- DB tables touched: `donations`.

**Mobile viewport:** N/A.
**Test strategy:** model + admin smoke.

---

### Story 5.3 — Public donate page (mobile-first)
**STATUS: backlog**

**As a** stranger
**I want** to give money in under 30 seconds without creating an account
**so that** the donation happens before I second-guess.

**Acceptance criteria:**
- [ ] Route `/donate/` (public, no login).
- [ ] Hero with campaign title + progress bar (from Story 5.1) if `?campaign=<slug>` is present; otherwise default to "General fund".
- [ ] Amount selector: $20 / $50 / $100 / custom chips.
- [ ] Toggle: "Make this monthly".
- [ ] Email field (required; donor identity for receipts).
- [ ] Big "Donate" CTA. On tap → Stripe Checkout session (Story 5.4).
- [ ] Mobile-first at 375 px. Apple Pay / Google Pay are *the* primary
      payment methods on mobile — Stripe Checkout handles this when the
      browser supports it.

**Technical notes:**
- Files: `apps/donations/views/donate.py`,
  `apps/donations/forms/donate.py`,
  `templates/donations/donate.html`,
  `apps/donations/tests/test_donate_page.py`.

**Mobile viewport:** required.
**Test strategy:** unit (form) + Playwright at 375 px.

---

### Story 5.4 — Stripe Checkout integration (one-time + recurring)
**STATUS: backlog**

**As a** developer
**I want** to start a Stripe Checkout session for one-time or recurring donations
**so that** we hand off PCI scope and inherit Stripe's wallet support.

**Acceptance criteria:**
- [ ] `apps/donations/services/stripe.py::create_checkout_session(donation_id, recurring: bool)`
      returns a Stripe URL.
- [ ] On tap "Donate", a `Donation` row is created in `pending` state and
      the user is redirected to the Stripe URL.
- [ ] Success URL → `/donate/thanks/?session_id=<sid>`; cancel URL →
      `/donate/?cancelled=1`.
- [ ] Stripe **webhook** `/stripe/webhook/` updates `Donation.status`
      and `transaction_id` based on `checkout.session.completed` and
      `invoice.paid` events. Signature verified using the webhook secret
      from `STRIPE_WEBHOOK_SECRET` in `.env`.
- [ ] One-time → `payment_type='card'`, `status='completed'`.
      Recurring → first invoice creates a `Donation`; subsequent invoices
      create new `Donation` rows linked to the same Stripe subscription.

**Technical notes:**
- Files: `apps/donations/services/stripe.py`,
  `apps/donations/views/checkout.py` (start + return + webhook),
  `apps/donations/tests/test_stripe_service.py`,
  `apps/donations/tests/test_webhook.py`.
- Use `dj-stripe` to manage the Stripe SDK + webhook signing.
- New env vars: `STRIPE_PUBLISHABLE_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`.
- DB tables touched: `donations` (write), plus dj-stripe's tables.

**Mobile viewport:** Stripe-hosted (their problem).
**Test strategy:**
- Unit: service builds the right Stripe params (mock the Stripe SDK).
- Unit: webhook with a valid signature updates the row; bad signature →
  401 and no DB change.
- Manual: end-to-end with Stripe CLI's `stripe trigger` in dev.

---

### Story 5.5 — Thank-you page + receipt email
**STATUS: backlog**

**As a** donor
**I want** an immediate "thank you" page and an emailed receipt
**so that** I have evidence for my tax return.

**Acceptance criteria:**
- [ ] `/donate/thanks/` shows: amount, campaign, receipt number, "we
      emailed you a copy".
- [ ] Receipt email sent on `Donation.status='completed'`. Includes:
      amount in dollars (formatted from cents), campaign name, charity
      ABN + address (from settings), one-line donor impact ("your $50 = 17 meals").
- [ ] Receipt email PDF attachment is **out of scope for v1**; HTML email
      with a clear "you can print this for your records" line is enough.

**Technical notes:**
- Files: `apps/donations/views/thanks.py`,
  `templates/donations/thanks.html`,
  `templates/donations/emails/receipt.{html,txt}`,
  `apps/donations/tests/test_receipt.py`.
- Receipt number = `D<year>-<zero-padded incremental>`.

**Mobile viewport:** required.
**Test strategy:** unit + Playwright at 375 px + `outbox` assertion.

---

### Story 5.6 — Donor impact view ("your $50 = 17 meals")
**STATUS: backlog**

**As a** donor
**I want** to see what my money paid for
**so that** I feel my donation mattered and consider giving again.

**Acceptance criteria:**
- [ ] On the thank-you page AND in the receipt email, an "Impact" line:
      "<dollars> ≈ <meals> meals delivered".
- [ ] `MEAL_COST_CENTS` setting (default 300 = $3) is the conversion factor.
- [ ] On the public donate page, hovering over an amount chip shows the
      same conversion as a small caption.

**Technical notes:**
- Files: `apps/donations/services/impact.py::meals_for_amount(amount_cents) -> int`,
  extend templates, `apps/donations/tests/test_impact.py`.

**Mobile viewport:** required.
**Test strategy:** unit covering: $30 → 10 meals, $1 → 0 meals (floor), boundary at $3.

---

### Story 5.7 — Recurring-donation management page
**STATUS: backlog**

**As a** recurring donor
**I want** to manage or cancel my subscription
**so that** I do not have to email the charity to stop giving.

**Acceptance criteria:**
- [ ] Route `/donate/manage/`. Public form: email + send-link button.
- [ ] Magic-link email contains a signed token (`django.core.signing`)
      that authenticates the donor for 30 minutes.
- [ ] Magic-link page lists active subscriptions: amount, next charge date.
- [ ] "Cancel subscription" button calls Stripe's API to cancel; on
      webhook receipt, the local row is marked `cancelled`.

**Technical notes:**
- Files: `apps/donations/views/manage.py`,
  `apps/donations/services/manage.py`,
  `templates/donations/manage_request.html`,
  `templates/donations/manage_list.html`,
  `apps/donations/tests/test_manage.py`.
- Token expiry: 30 min.

**Mobile viewport:** required.
**Test strategy:** unit (token), Playwright at 375 px.

---

### Story 5.8 — Admin campaign-progress card
**STATUS: backlog**

**As an** admin
**I want** a live progress card per active campaign on my dashboard
**so that** I know whether to push harder this week.

**Acceptance criteria:**
- [ ] Route `/admin/campaigns/` lists active campaigns with progress bar +
      raised / goal in dollars + days remaining.
- [ ] Each card links to a detail page with a paginated list of donations.
- [ ] CSV export of donations per campaign (re-used in Epic 06).

**Technical notes:**
- Files: `apps/dashboards/views/admin_campaigns.py`,
  `apps/dashboards/services/campaign_progress.py`,
  `templates/dashboards/admin/campaigns.html`,
  `apps/dashboards/tests/test_admin_campaigns.py`.

**Mobile viewport:** mobile-readable; desktop-primary.
**Test strategy:** unit + Playwright at 1024 px.

---

## Backlog (not in sprint 09 yet)

- **5.9 — Donor login + history page** — currently anonymous donations
  work; turn this on once first-time donors ask for it. Mostly lands
  alongside Epic 06.
- **5.10 — PDF tax receipts** — for end-of-financial-year. Sprint 11+.
- **5.11 — Gift Aid / employer matching** — once we know which markets matter.
- **5.12 — In-honour / in-memory donations** — UX polish on Story 5.3.

---

## Demo for end of Epic 05

1. A teammate opens `/donate/` on a phone, taps $50, taps "Donate", taps
   Apple Pay, biometrically confirms. Total elapsed: < 30 seconds.
2. The thank-you page renders with "Your $50 = 17 meals".
3. The receipt email lands in the dev outbox.
4. The admin opens `/admin/campaigns/` and sees the campaign bar tick up by $50.
5. The Stripe CLI re-fires the webhook — the row is **not** double-counted
   (idempotency via `transaction_id` uniqueness).
