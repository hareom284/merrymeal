# Epic 07 — Hardening & nice-to-haves

> **Goal:** make the system production-grade for the long term — installable,
> private, fast, and accessibility-audited.

**Sprints:** **ongoing**. This epic has no fixed sprint allocation. Stories
move into a sprint **as soon as that sprint has ≥ 3 days of slack** or
**as soon as a real-world incident makes a story urgent**.
**Status:** backlog
**Source spec:** [Roadmap §6, Phase 7](../../superpowers/specs/2026-06-01-merrymeal-django-design.md)

---

## Why this epic exists

Epics 00–06 ship a working charity meal-delivery system. This one
hardens it for the next 18 months: when a volunteer's phone is in airplane
mode, when a journalist files a Freedom-of-Information request, when a
member complains the screen is too small to read, and when a hostile party
probes the public donate page.

**Pulling rule:** at every sprint-planning meeting, ask "do we have slack
for one of these?". If yes, pick the highest-impact unblocked story.

---

## Stories

### Story 7.1 — Service worker + PWA installability
**STATUS: backlog**

**As a** volunteer
**I want** to install MerryMeal as an app on my phone home screen and have the route screen open offline
**so that** poor signal mid-route does not cost a delivery.

**Acceptance criteria:**
- [ ] `manifest.json` served from `/static/manifest.json`. Icons in 192 px and 512 px.
- [ ] Service worker (`/service-worker.js`) caches:
      `base.html` shell, Tailwind CSS, HTMX, Alpine, and the volunteer "today" route once loaded.
- [ ] Installing the PWA on iOS Safari and Chrome Android both work.
- [ ] Mark-delivered actions queue offline via the IndexedDB pattern,
      replacing the v1 `localStorage` hack from Story 4.9.
- [ ] When connectivity returns, queued actions sync; user sees a "synced"
      toast per item.

**Technical notes:**
- New files: `static/src/service-worker.ts`, `static/src/sync-queue.ts`,
  `static/manifest.json`,
  `templates/_partials/pwa_head.html`,
  `apps/delivery/tests/test_offline_sync.py`.

**Mobile viewport:** required.
**Test strategy:** Playwright with `page.evaluate("...")` to enter / exit
offline mode + a manual physical-device test recorded in the PR.

---

### Story 7.2 — Field-level encryption for sensitive PII
**STATUS: backlog**

**As the** charity (legal / compliance)
**I want** DOB, dietary, and allergy data encrypted at rest at the column level
**so that** a DB dump leak still keeps personal health information confidential.

**Acceptance criteria:**
- [ ] `django-cryptography` (or `django-fernet-fields`) installed and
      configured with a key from `FIELD_KEY` env var.
- [ ] Encrypted columns: `users.dob`, `diet_preference_user.*`,
      `allergy_user.*`.
- [ ] Migration encrypts existing rows; reversible.
- [ ] Documented key-rotation procedure in `docs/security.md`.

**Technical notes:**
- New files: `apps/core/models/encrypted.py`,
  `docs/security.md`,
  `apps/accounts/migrations/<n>_encrypt_dob.py`.

**Mobile viewport:** N/A.
**Test strategy:** unit + a migration round-trip test.

---

### Story 7.3 — WCAG AA audit + remediation
**STATUS: backlog**

**As the** team
**I want** an external (or internal-but-blind-to-the-build) WCAG 2.1 AA
audit of the four highest-traffic flows
**so that** Margaret can use the app and we are defensible if questioned.

**Acceptance criteria:**
- [ ] Audit scope: login, member home, volunteer today, donate page.
- [ ] Findings logged as new stories with `STATUS: backlog`.
- [ ] All "must-fix" findings closed before this story is `done`.
- [ ] `axe-core` integrated into Playwright; CI fails on critical violations.

**Technical notes:**
- Hire or borrow an a11y auditor for 1–2 days.
- New file: `tests_e2e/a11y.spec.ts`.

**Mobile viewport:** required.
**Test strategy:** audit reports + Playwright a11y test.

---

### Story 7.4 — Performance budget enforcement in CI
**STATUS: backlog**

**As the** team
**I want** CI to fail if the login page's First Contentful Paint at
throttled-3G exceeds 1.5 s
**so that** mobile performance does not silently regress.

**Acceptance criteria:**
- [ ] Lighthouse CI runs on the login page, member home (logged in), and
      volunteer today (logged in) inside the Docker stack.
- [ ] Configured thresholds: FCP ≤ 1500 ms on Slow 3G profile,
      TTI ≤ 3000 ms, Total Blocking Time ≤ 200 ms.
- [ ] CI surfaces the Lighthouse report as an artifact.

**Technical notes:**
- `.github/workflows/lighthouse.yml`,
  `lighthouserc.json`,
  helper script to log in as a seeded user for the gated pages.

**Mobile viewport:** required.
**Test strategy:** Lighthouse CI itself.

---

### Story 7.5 — Penetration test + remediation
**STATUS: backlog**

**As the** charity
**I want** a third-party pen-test once Epic 05 is live
**so that** the donation page and the auth flows are validated by hostile
attention before going wide.

**Acceptance criteria:**
- [ ] External vendor selected (3 quotes documented in `docs/security.md`).
- [ ] Findings triaged: criticals fixed before sign-off, mediums become
      backlog stories with SLAs.
- [ ] HTTPS everywhere, HSTS preload, secure cookie audit passed.

**Technical notes:**
- Vendor-dependent.

**Mobile viewport:** N/A.
**Test strategy:** the test itself.

---

### Story 7.6 — Audit-log partitioning + archival
**STATUS: backlog**

**As a** DBA
**I want** audit logs partitioned by month and archived to S3 after 12 months
**so that** the live DB does not balloon under audit volume.

**Acceptance criteria:**
- [ ] MySQL native partitioning on the audit table (range by month).
- [ ] Django-Q2 monthly job: drop the month older than 12, having first
      dumped it to S3 as a Parquet file.
- [ ] Restore script in `scripts/restore_audit.py` documented in
      `docs/security.md`.

**Technical notes:**
- New files: migration to partition, `apps/dashboards/tasks/audit_archive.py`,
  `scripts/restore_audit.py`.

**Mobile viewport:** N/A.
**Test strategy:** integration test with a clock-mocked fixture covering
the boundary month.

---

### Story 7.7 — Mobile-first lint rule + PR-template checkbox
**STATUS: backlog**

**As the** team
**I want** a PR template that forces every contributor to tick "tested at 375 px"
**so that** mobile-first stays a habit, not a memory.

**Acceptance criteria:**
- [ ] `.github/pull_request_template.md` adds the checkbox.
- [ ] CI's Playwright job is renamed and badged so reviewers see "mobile-viewport ✓".

**Technical notes:**
- Files: `.github/pull_request_template.md`.

**Mobile viewport:** N/A (process).
**Test strategy:** open a PR; verify template renders.

---

### Story 7.8 — Backup + restore drill
**STATUS: backlog**

**As an** operations engineer
**I want** a documented backup + restore procedure I have run end-to-end at least once
**so that** a disaster does not become a panic.

**Acceptance criteria:**
- [ ] Nightly MySQL dump to S3 (encrypted bucket).
- [ ] S3 lifecycle rule: 30 days standard, then Glacier.
- [ ] `docs/backup-restore.md` written.
- [ ] Drill: drop a staging DB, restore from yesterday's backup, verify
      latest day's deliveries are present. Note the time it took.

**Technical notes:**
- Files: `scripts/backup.sh`, `scripts/restore.sh`, `docs/backup-restore.md`.

**Mobile viewport:** N/A.
**Test strategy:** the drill is the test.

---

## How to pull a story out of this epic

At sprint planning:

1. Open this file.
2. Find any `STATUS: backlog` story whose **dependencies are met** (Epic
   00–06 done? Vendor selected? Etc).
3. Discuss: highest impact per day-of-work?
4. Move it into the upcoming sprint by updating its `STATUS` to
   `planned (sprint-NN)` and listing it in `sprints/sprint-NN.md`.

There is no obligation to take one of these every sprint. The point is
that the list is visible and stays visible.
