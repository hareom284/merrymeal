# Sprint 02 — Identity foundations

**Weeks:** 3–4
**Primary epic:** [01 — Identity & onboarding](../../epics/01-identity-onboarding.md)
**Sprint goal:** every model that supports an application exists in the DB, admin can manage them, and the public landing page is live.

---

## Stories pulled

| ID | Title | Track | Status | Detail |
|---|---|---|---|---|
| 1.1 | `City` model + admin | Backend | planned (sprint-02) | [stories/1.1-city-model.md](stories/1.1-city-model.md) |
| 1.2 | `Address` model with lat/lng | Backend | planned (sprint-02) | [stories/1.2-address-model.md](stories/1.2-address-model.md) |
| 1.3 | `CaregiverLink` model | Backend | planned (sprint-02) | [stories/1.3-caregiver-link.md](stories/1.3-caregiver-link.md) |
| 1.4 | `partners` app: `Partner` model + admin CRUD | Backend | planned (sprint-02) | [stories/1.4-partner-app.md](stories/1.4-partner-app.md) |
| 1.5 | `dietary` app: `DietPreference` + `Allergy` | Backend | planned (sprint-02) | [stories/1.5-dietary-app.md](stories/1.5-dietary-app.md) |
| 1.6 | Public landing page | Frontend | planned (sprint-02) | [stories/1.6-landing-page.md](stories/1.6-landing-page.md) |

> **For executors:** each story file is a self-contained TDD plan with file paths, code, commands, and expected output. Pattern follows [Sprint 01's stories](../sprint-01/stories/). **Sprint backlog & spillover protocol:** see [backlog.md](backlog.md).

---

## Parallel tracks

### Backend track — Dev A
Stories 1.1 → 1.2 → 1.3 → 1.4 → 1.5 in **that order** — each depends on the previous app/model existing.

The `users.partner_id` FK turn-on inside 1.4 requires a migration that touches existing data (the dev DB has a superuser). Plan to dump and reload the dev DB or write the migration to be backwards-compatible.

### Frontend track — Dev B
Story 1.6 (landing page) is fully independent of the backend track and can ship in week 1 of the sprint. Dev B then pair-reviews backend PRs for week 2 and prepares Sprint 03 ground (Application flow templates).

### Admin / ops mini-track — Dev C (if available)
Help Dev A with seed-data commands (`seed_cities`, `seed_dietary`). Verify the Django admin UX feels right for an admin who has to use it daily.

---

## Day-by-day suggestion

| Day | Backend | Frontend |
|---|---|---|
| Mon w1 | Sprint planning. Pick up 1.1 City. | Sprint planning. Wireframe landing page at 375 px and 1024 px. |
| Tue w1 | 1.1 done. Start 1.2 Address. | Begin 1.6 markup. |
| Wed w1 | 1.2 done (no geocoding). Start 1.3 CaregiverLink. | 1.6 content + responsive tweaks. |
| Thu w1 | 1.3 done. Start 1.4 Partner. | Run axe a11y plugin against 1.6 page; record findings in PR. |
| Fri w1 | 1.4 in review. | 1.6 in review. Mid-sprint demo. |
| Mon w2 | Land 1.4 (incl. `users.partner_id` migration). Start 1.5 dietary app. | Land 1.6. |
| Tue w2 | 1.5 models + seed. | Begin pre-work for Sprint 03 (template skeleton for 3-step form). |
| Wed w2 | 1.5 admin inline + `seed_dietary` command. | Same. |
| Thu w2 | 1.5 in review. Polish admin pages. | Same. |
| Fri w2 | **Sprint demo + retro.** | Same. |

---

## Demo agenda (Fri w2)

1. Show admin landing at `/admin/` → tour each new model: City, Address (inline on User), CaregiverLink (inline on User), Partner, DietPreference, Allergy.
2. Run `python manage.py seed_cities` and `seed_dietary` from scratch on a clean DB.
3. Show landing page at 375 px (phone preview) AND 1024 px (laptop).
4. Show axe a11y plugin output for the landing page — no critical violations.

## Definition of Done for the sprint

- Every story above is `STATUS: done (sprint-02)`.
- Migrations apply cleanly on a fresh `docker compose up`.
- Landing page passes axe critical-violations check.

## Risks

| Risk | Mitigation |
|---|---|
| `users.partner_id` migration breaks the existing superuser. | Migration sets default NULL; pre-existing rows are fine. Smoke-test on a fresh and a populated dev DB before merge. |
| Landing-page copy bikeshedding. | Use the same hero copy as `index.html` prototype; defer wordsmithing to a follow-up issue. |
