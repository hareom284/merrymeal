# Sprint 05 — Food safety + expiry alerts

**Weeks:** 9–10
**Primary epic:** [02 — Kitchen & inventory backbone](../../epics/02-kitchen-inventory.md)
**Sprint goal:** kitchen staff can record their daily food-safety checks in 2 minutes; admins get a morning email when stock is expiring; the admin dashboard shows the kitchen state at a glance.

---

## Stories pulled

| ID | Title | Track | Status | Detail |
|---|---|---|---|---|
| 2.7 | `food_safety` app: `FoodSafetyCheck` model | Backend | planned (sprint-05) | [stories/2.7-food-safety-model.md](stories/2.7-food-safety-model.md) |
| 2.8 | Daily food-safety check form (mobile-first) | FE + BE pair | planned (sprint-05) | [stories/2.8-safety-check-form.md](stories/2.8-safety-check-form.md) |
| 2.9 | Nightly expiry-alert job | Backend / Ops | planned (sprint-05) | [stories/2.9-expiry-alert-job.md](stories/2.9-expiry-alert-job.md) |
| 2.10 | "Today's stock at a glance" admin widget | FE + BE pair | planned (sprint-05) | [stories/2.10-stock-glance-widget.md](stories/2.10-stock-glance-widget.md) |

> **For executors:** each story file is a self-contained TDD plan with file paths, code, commands, and expected output. Pattern follows [Sprint 01's stories](../sprint-01/stories/). **Sprint backlog & spillover protocol:** see [backlog.md](backlog.md).

---

## Parallel tracks

### Backend track — Dev A
1. **2.7** model + admin (1 day).
2. **2.9** expiry-alert job: query, email template, Django-Q2 schedule, idempotency table, tests (2–3 days).

### Frontend track — Dev B
1. **2.8** daily-check form with per-check-type widgets and the "already-done-today" list at the top (2–3 days).

### Pair track — both devs, week 2
**2.10** admin "today's stock" widget. Backend builds the summary service; Frontend builds the cards.

---

## Day-by-day suggestion

| Day | Backend | Frontend |
|---|---|---|
| Mon w1 | Sprint planning. 2.7 model + admin. | Sprint planning. 2.8 form scaffold (each check type a separate component). |
| Tue w1 | 2.7 merged. Start 2.9 query + idempotency design. | 2.8 conditional rendering per check_type. |
| Wed w1 | 2.9 email template + service. | 2.8 Playwright at 375 px. |
| Thu w1 | 2.9 Django-Q2 schedule + integration test. | 2.8 in review. |
| Fri w1 | 2.9 in review. Mid-sprint demo: trigger the job manually, see email in outbox. | 2.8 merged. Mid-sprint demo. |
| Mon w2 | 2.9 merged. Pair-start 2.10 service. | Pair-start 2.10 cards. |
| Tue w2 | 2.10 service: kitchen_summary returns the 3 metrics per kitchen. | 2.10 template: card per kitchen with traffic-light colours. |
| Wed w2 | Unit tests for the summary service. | 2.10 Playwright at 1024 px. |
| Thu w2 | Bug-bash the alert job with edge cases (no batches, missing kitchen admin email). | 2.10 in review. |
| Fri w2 | **Sprint demo + retro.** | Same. |

---

## Demo agenda (Fri w2)

1. **Kitchen staff (tablet)** — open `/kitchen/safety/check/`, record one storage temp (4 °C), one cooking temp (75 °C), one hygiene pass. See the "already done today" list update.
2. **Admin (laptop)** — open `/dashboards/admin/kitchens/`, see two kitchens, each with: expiring count (Footscray = 1, St Kilda = 0), 24 h check pass-rate (100 %), no failures.
3. **Trigger the expiry job manually:** `python manage.py qcluster` (or call the task in a shell), see the email body in the dev outbox listing the rice batch from Sprint 04.
4. **Idempotency proof:** run the job again — no second email.

## Definition of Done for the sprint

- All 4 stories `STATUS: done (sprint-05)`.
- Django-Q2 schedule exists in a data migration so a fresh deploy picks it up.
- Idempotency of 2.9 has a dedicated unit test.

## Risks

| Risk | Mitigation |
|---|---|
| Django-Q2 schedule persistence on a fresh deploy. | Data migration creates the `Schedule` row via `update_or_create`. Verify on a clean DB. |
| Kitchen email contact missing (no field today). | For v1, the alert email goes to the first user with `role='admin'`. Add per-kitchen contact in a later epic if needed. |
| Tablet form on iPad Safari rendering. | Smoke test on a real iPad during the bug-bash day. |
