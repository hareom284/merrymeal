# Sprint 08 — Volunteer mobile UI + proof of delivery (**mobile-critical**)

**Weeks:** 15–16
**Primary epic:** [04 — Volunteer & delivery flow](../../epics/04-delivery-flow.md)
**Sprint goal:** a real volunteer on a real phone runs a real route end-to-end: route loads, taps "Mark delivered", camera opens, photo uploads, member's tracking page updates, caregiver gets a text on failure.

This is the most important sprint in the roadmap from an end-user UX perspective. Treat it with care.

---

## Stories pulled

| ID | Title | Track | Status | Detail |
|---|---|---|---|---|
| 4.8 | Volunteer "today" route screen | FE + BE pair | planned (sprint-08) | [stories/4.8-volunteer-today-screen.md](stories/4.8-volunteer-today-screen.md) |
| 4.9 | Mark-delivered with POD photo | FE + BE pair | planned (sprint-08) | [stories/4.9-mark-delivered-pod.md](stories/4.9-mark-delivered-pod.md) |
| 4.10 | Mark-failed with reason | FE + BE pair | planned (sprint-08) | [stories/4.10-mark-failed-reason.md](stories/4.10-mark-failed-reason.md) |
| 4.11 | 2-tap meal feedback (member) | FE + BE pair | planned (sprint-08) | [stories/4.11-feedback-2tap.md](stories/4.11-feedback-2tap.md) |
| 4.12 | Member tracking page | FE | planned (sprint-08) | [stories/4.12-member-tracking.md](stories/4.12-member-tracking.md) |
| 4.13 | Caregiver alert on failed delivery | Backend / Ops | planned (sprint-08) | [stories/4.13-caregiver-alert.md](stories/4.13-caregiver-alert.md) |
| 4.14 | Admin reassignment widget | FE + BE pair | planned (sprint-08) | [stories/4.14-admin-reassign.md](stories/4.14-admin-reassign.md) |

> **For executors:** each story file is a self-contained TDD plan with file paths, code, commands, and expected output. Pattern follows [Sprint 01's stories](../sprint-01/stories/). **Sprint backlog & spillover protocol:** see [backlog.md](backlog.md).

---

## Parallel tracks

### Frontend track — Dev B (lead)
Owns 4.8 → 4.9 → 4.10 → 4.11 → 4.12. The volunteer flow demands mobile-first discipline; Dev B should pair with Dev A on backend endpoints.

### Backend track — Dev A
Owns 4.13 (caregiver alert) end-to-end. Wraps Twilio behind an SMS abstraction. Builds the post-save signal on Delivery. Helps Dev B with the mark-delivered S3 upload pipeline (Story 4.9).

### Admin / ops track — Dev C
Owns 4.14 (reassignment widget) + sets up Twilio credentials in `.env.example` + a sandbox-Twilio account for dev. Helps with iOS Safari camera quirks during bug-bash days.

---

## Day-by-day suggestion

| Day | Frontend | Backend | Admin/Ops |
|---|---|---|---|
| Mon w1 | Sprint planning. 4.8 layout against fixtures. | Sprint planning. SMS abstraction + Twilio sandbox. | Sprint planning. Stand up Twilio dev creds + IAM for S3 bucket. |
| Tue w1 | 4.8 stop-card iteration; bottom-anchored CTA at 375 px. | 4.13 signal + email template. | 4.14 reassign service + modal. |
| Wed w1 | 4.8 Playwright happy path. | 4.13 SMS template + integration test with fake backend. | 4.14 admin reassign view + Playwright. |
| Thu w1 | 4.9 mark-delivered endpoint + camera capture + S3 upload. | 4.13 in review. | 4.14 in review. |
| Fri w1 | 4.9 offline queue + localStorage retry. | Pair with FE on S3 upload edge cases. | Mid-sprint demo + bug-bash on real phones. |
| Mon w2 | 4.9 in review. Start 4.10 mark-failed + reasons. | 4.13 merged. Help FE on 4.10's signal trigger. | 4.14 merged. Begin pre-work for Sprint 09 (Stripe sandbox). |
| Tue w2 | 4.10 in review. Start 4.11 feedback chips. | Help with audit-log entries on 4.10. | Same. |
| Wed w2 | 4.11 in review. Start 4.12 tracking polling. | Same. | Same. |
| Thu w2 | 4.12 in review. Full bug-bash on physical devices. | Same. | Same. |
| Fri w2 | **Sprint demo + retro.** | Same. | Same. |

---

## Demo agenda (Fri w2)

Run this **on a real phone**, not in a desktop emulator.

1. Sarah opens `/volunteer/today/`. Sees 4 stops.
2. Taps stop 1 "Mark delivered" → camera opens → photo taken → uploaded → screen advances.
3. Margaret (laptop next to phone) refreshes her dashboard → sees "Delivered ✓ at 09:14".
4. Sarah at stop 3 taps "Couldn't deliver" → "No answer" → submits.
5. Margaret's daughter (third phone) gets an email **and** a text within 30 seconds.
6. Margaret rates yesterday's meal: ★★★★☆ + "Loved it".
7. Admin opens `/admin/today/`, reassigns stop 3 to a different volunteer for tomorrow.
8. **Offline test:** put Sarah's phone in airplane mode at stop 4. Tap mark-delivered. See "queued — will retry" badge. Re-enable signal. See sync toast.

## Definition of Done for the sprint

- All 7 stories `STATUS: done (sprint-08)`.
- Demo above runs successfully on a real iPhone **and** a real Android.
- S3 bucket configured in prod (with lifecycle rule: photos retained 180 days then deleted).
- SMS abstraction has a console backend that all tests use; Twilio backend is only wired in `prod.py`.

## Risks

| Risk | Mitigation |
|---|---|
| iOS Safari camera quirks (HEIC files, orientation). | During bug-bash days, test on at least one real iPhone. Server-side: convert HEIC → JPEG via Pillow + pyheif. |
| Geolocation prompt UX (gets dismissed). | Story 4.9 explicitly tolerates `null` lat/lng — never block delivery on geolocation. |
| Twilio bill spike on failed-delivery floods. | Rate-limit alerts per (member, day) to 1 SMS; subsequent failures only email. |
| Offline queue bugs eat a delivery. | Story 7.1 (PWA, real IndexedDB) supersedes; the v1 localStorage hack is acceptable for ≤ 1 KB queue. Log every queued action server-side too. |
