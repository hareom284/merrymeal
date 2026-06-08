# Epic 06 — Dashboards & reporting

> **Goal:** every role has one screen that tells them what matters today,
> and the admin can pull a board-quality report in one click.

**Sprints:** 1 (Sprint 10)
**Status:** not started
**Depends on:** All previous epics. This is the aggregation layer.
**Source spec:** [Roadmap §6, Phase 6](../../superpowers/specs/2026-06-01-merrymeal-django-design.md)

---

## Why this epic exists

After Epics 01–05 the data exists, but it is scattered: admins still bounce
between `/admin/applications/`, `/admin/today/`, `/admin/campaigns/`,
`/dashboards/admin/kitchens/`. This epic consolidates them.

It also closes the loop with two external stakeholders we haven't yet
served:
- **Partners** (e.g. a referring social-work agency) need an outcome view
  of "did the people we sent end up okay?".
- **Donors** with accounts need a history page and tax receipts.

And finally, **audit log read access** lives here — answering the
requirement-doc story *"who changed Margaret's diet?"*.

---

## Personas in scope

- **Admin** — operations, on a laptop.
- **Partner** — corporate / charity sponsor.
- **Donor** — recurring donor with an account.

---

## Stories

### Story 6.1 — Admin home: "what needs attention now"
**STATUS: done (sprint-10)**

**As an** admin
**I want** one screen that surfaces every actionable thing
**so that** I do not have to remember which queue I have not checked.

**Acceptance criteria:**
- [ ] Route `/admin/home/` (also reachable as `/` for users with `role='admin'`).
- [ ] Sections (each is a card with a count + link):
  - **Pending applications** — count of `submitted` applications (Epic 01).
  - **Expiring stock** — batches expiring ≤ 3 days, grouped by kitchen (Epic 02).
  - **Failed deliveries today** — count + link to the list (Epic 04).
  - **Unassigned deliveries today** — count (Epic 04 Story 4.7's overflow).
  - **Recent food-safety failures** — last 24 h, link to detail (Epic 02).
- [ ] Each card is colour-coded by severity (green = 0, yellow = ≥ 1,
      red = exceeds a per-card threshold defined in the view).
- [ ] Cards refresh via HTMX every 5 minutes.

**Technical notes:**
- Files: `apps/dashboards/views/admin_home.py`,
  `apps/dashboards/services/admin_summary.py`,
  `templates/dashboards/admin/home.html`,
  `templates/dashboards/admin/_attention_card.html`,
  `apps/dashboards/tests/test_admin_home.py`.

**Mobile viewport:** mobile-readable; desktop-primary.
**Test strategy:** unit per section + Playwright at 1024 px.

---

### Story 6.2 — Partner outcomes view
**STATUS: done (sprint-10)**

**As a** partner staff member
**I want** to see the members our organisation has referred to MerryMeal,
their current status, average rating, and retention
**so that** I can report back to my own board.

**Acceptance criteria:**
- [ ] Route `/partner/outcomes/`, gated by `@role_required('partner')` AND
      `user.partner_id IS NOT NULL`. A partner user only sees rows for
      their own `Partner`.
- [ ] Table of referred members: name, suburb, status (active /
      inactive), enrolment date, last delivery date, average meal rating
      (from `delivery_feedback`).
- [ ] Aggregate header: total referred, currently active, % retention at 90 days.
- [ ] CSV export.

**Technical notes:**
- Files: `apps/dashboards/views/partner_outcomes.py`,
  `apps/dashboards/services/partner_outcomes.py`,
  `templates/dashboards/partner/outcomes.html`,
  `apps/dashboards/tests/test_partner_outcomes.py`.
- "Referred by" = `users.partner_id`.
- Object-level permission: a partner user **must not** see members of
  another partner. The service filters by `partner_id`. Verified in tests.

**Mobile viewport:** mobile-readable; desktop-primary.
**Test strategy:**
- Unit: a partner user fetching `/partner/outcomes/` sees only their rows.
- Unit: cross-partner access attempt → empty result, no 500.
- Playwright at 1024 px.

---

### Story 6.3 — Donor history page (signed-in donor)
**STATUS: backlog**

**As a** logged-in donor
**I want** to see my donation history with downloadable receipts
**so that** I can manage my giving without phoning the office.

**Acceptance criteria:**
- [ ] Route `/donor/history/`, gated by `@role_required('donor')`.
- [ ] Lists each `Donation` (completed and refunded) with date, amount,
      campaign, status, "Download receipt" link (HTML for now;
      PDF deferred to backlog 5.10).
- [ ] Aggregate header: total given this calendar year, total given lifetime.

**Technical notes:**
- Files: `apps/dashboards/views/donor_history.py`,
  `apps/dashboards/services/donor_history.py`,
  `templates/dashboards/donor/history.html`,
  `apps/dashboards/tests/test_donor_history.py`.

**Mobile viewport:** required.
**Test strategy:** unit + Playwright at 375 px.

---

### Story 6.4 — Tax receipt printer-friendly page
**STATUS: backlog**

**As a** donor at tax time
**I want** a printable summary of every donation I made in a financial year
**so that** I have one page for my tax return.

**Acceptance criteria:**
- [ ] Route `/donor/receipts/<fy>/` (e.g. `/donor/receipts/2026/` for
      FY 2025–26 in Australia).
- [ ] Page lists each donation in the FY, summed total at the top,
      charity ABN + address footer.
- [ ] `print` CSS reduces to clean A4 layout.
- [ ] Same data is available as JSON at `?format=json` for accountants.

**Technical notes:**
- Files: extend `apps/dashboards/views/donor_history.py` with the FY view,
  `templates/dashboards/donor/fy_receipt.html`,
  `static/src/print.css`,
  `apps/dashboards/tests/test_fy_receipt.py`.

**Mobile viewport:** N/A (print).
**Test strategy:** unit + Playwright print emulation.

---

### Story 6.5 — Board report: CSV + PDF (one-click monthly export)
**STATUS: backlog**

**As an** admin
**I want** to click one button and download a monthly board pack
**so that** I do not spend Sunday afternoon assembling numbers.

**Acceptance criteria:**
- [ ] Route `/admin/reports/board/?month=YYYY-MM`.
- [ ] One CSV with sheets (or one .zip of CSVs): meals delivered (by
      kitchen × day), donations (per campaign), volunteer hours / route
      count, failed deliveries, food-safety check pass-rate.
- [ ] PDF version of the same numbers as a one-page summary, generated
      with `weasyprint` or `xhtml2pdf` — pick whichever has a working pin
      on Python 3.12.
- [ ] Rate-limited: generation is rate-limited per admin (max 5 / minute).
- [ ] Audit-log entry on generation (who pulled which report when).

**Technical notes:**
- Files: `apps/dashboards/views/board_report.py`,
  `apps/dashboards/services/board_report.py`,
  `apps/dashboards/services/pdf.py`,
  `apps/dashboards/tests/test_board_report.py`.

**Mobile viewport:** desktop-primary.
**Test strategy:** unit on each numeric query; integration test that the
generated PDF parses and contains the expected headings.

---

### Story 6.6 — Audit log viewer
**STATUS: done (sprint-10)**

**As an** admin
**I want** to search the audit log by user, by table, and by date range
**so that** I can answer "who changed Margaret's diet on 12 March?".

**Acceptance criteria:**
- [ ] Route `/admin/audit/`.
- [ ] Filters: user (free-text email match), object type, date range, action.
- [ ] Pagination (50 / page).
- [ ] Row reveals the **before / after** diff in a collapsible panel.
- [ ] Read-only — no admin can edit or delete audit rows from the UI.

**Technical notes:**
- Files: `apps/dashboards/views/audit.py`,
  `templates/dashboards/admin/audit.html`,
  `apps/dashboards/tests/test_audit.py`.
- Reads from `django-auditlog`'s tables; do not write to them.

**Mobile viewport:** mobile-readable; desktop-primary.
**Test strategy:** unit covering filter combinations; Playwright at 1024 px.

---

### Story 6.7 — Partner referral form (public)
**STATUS: done (sprint-10)**

**As a** social worker at a referring agency
**I want** a public form to submit a member on behalf of my client, attributed to my organisation
**so that** the charity can see referral volume per partner.

**Acceptance criteria:**
- [ ] Route `/partners/refer/` (public, no login).
- [ ] Form mirrors Story 1.10 (caregiver-on-behalf) PLUS:
  - "Your organisation" dropdown (from `Partner` rows of type `charity`).
  - "Your name + email" so the partner contact can be confirmed.
- [ ] Submitted application is tagged with `partner_id`.
- [ ] On approval, the resulting `Member` row carries `partner_id` so
      Story 6.2 can count it.

**Technical notes:**
- Files: `apps/accounts/views/partner_referral.py`,
  `apps/accounts/forms/partner_referral.py`,
  `templates/accounts/application/partner_referral.html`,
  `apps/accounts/tests/test_partner_referral.py`.

**Mobile viewport:** required.
**Test strategy:** unit + Playwright at 375 px.

---

## Backlog (not in sprint 10 yet)

- **6.8 — Kitchen-staff dashboard** with today's plan + safety-check
  checklist (low priority because Story 2.10 already covers the basics).
- **6.9 — Volunteer profile / stats page** (deliveries to date, kilometres
  travelled, member thank-you notes). Morale builder.
- **6.10 — Donor leaderboard** (opt-in). Sensitive UX — defer until donor
  retention data justifies it.

---

## Demo for end of Epic 06

1. The admin opens `/admin/home/` first thing Monday. Three yellow cards.
2. Clicks "Failed deliveries today" → resolves a redelivery.
3. Generates the previous-month board PDF for tonight's board meeting (single click).
4. A partner contact at the referring agency logs in, views `/partner/outcomes/`,
   sees the 23 members they referred this quarter and their retention rate.
5. A donor with an account logs in, downloads their FY receipt page,
   prints it from the browser — perfectly formatted A4.
6. An admin searches the audit log for `margaret@example.com` and finds the
   row showing the dietitian updated her diet on 12 March, with the diff.
