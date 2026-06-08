# Sprint 07 — Delivery models + auto-assign

**Weeks:** 13–14
**Primary epic:** [04 — Volunteer & delivery flow](../../epics/04-delivery-flow.md)
**Sprint goal:** every model needed for delivery is in the DB; a single daily job turns the day's MealPlan + active members into Delivery rows packed into Routes assigned to available volunteers.

---

## Stories pulled

| ID | Title | Track | Status | Detail |
|---|---|---|---|---|
| 4.1 | `volunteers` app: `Availability` model | Backend | planned (sprint-07) | [stories/4.1-availability-model.md](stories/4.1-availability-model.md) |
| 4.2 | Volunteer availability editor (mobile) | FE + BE pair | planned (sprint-07) | [stories/4.2-availability-editor.md](stories/4.2-availability-editor.md) |
| 4.3 | `delivery` app: `Route` model | Backend | planned (sprint-07) | [stories/4.3-route-model.md](stories/4.3-route-model.md) |
| 4.4 | `Delivery` model | Backend | planned (sprint-07) | [stories/4.4-delivery-model.md](stories/4.4-delivery-model.md) |
| 4.5 | `DeliveryFeedback` model | Backend | planned (sprint-07) | [stories/4.5-delivery-feedback-model.md](stories/4.5-delivery-feedback-model.md) |
| 4.6 | Auto-assign: generate deliveries | Backend | planned (sprint-07) | [stories/4.6-generate-deliveries.md](stories/4.6-generate-deliveries.md) |
| 4.7 | Auto-assign: pack into routes | Backend | planned (sprint-07) | [stories/4.7-pack-routes.md](stories/4.7-pack-routes.md) |

> **For executors:** each story file is a self-contained TDD plan with file paths, code, commands, and expected output. Pattern follows [Sprint 01's stories](../sprint-01/stories/). **Sprint backlog & spillover protocol:** see [backlog.md](backlog.md).

> This is a **backend-heavy** sprint. The volunteer-facing UI ships next sprint.

---

## Parallel tracks

### Backend track — Dev A + Dev C
1. **4.1** + **4.3** + **4.4** + **4.5** — four small models (~1 day total).
2. **4.6** generate-deliveries service + task + idempotency tests (~2 days).
3. **4.7** pack-into-routes service + task (~2 days).

### Frontend track — Dev B
1. **4.2** availability editor (~2 days).
2. Pre-work on Sprint 08's volunteer "today" screen: wireframes at 375 px, static prototype against fixtures.

---

## Day-by-day suggestion

| Day | Backend | Frontend |
|---|---|---|
| Mon w1 | Sprint planning. 4.1 + 4.3 + 4.4 + 4.5 (model burst). | Sprint planning. Wireframe availability editor at 375 px. |
| Tue w1 | All 4 models merged. Start 4.6 — design idempotency strategy. | Build 4.2 grid; HTMX toggle endpoint. |
| Wed w1 | 4.6 happy path + 5 unit tests. | 4.2 mobile-viewport Playwright. |
| Thu w1 | 4.6 in review. Begin 4.7 — greedy-pack algorithm + tests. | 4.2 in review. |
| Fri w1 | 4.6 merged. Mid-sprint demo: run the task, count Delivery rows. | 4.2 merged. Begin Sprint 08 wireframes. |
| Mon w2 | 4.7 algorithm: chunk by 12 + sort-by-distance. | Static prototype of "today route" screen. |
| Tue w2 | 4.7 idempotency + unassigned-overflow handling. | Same. |
| Wed w2 | 4.7 in review. | Same — finalise tap targets, thumb-zone layout. |
| Thu w2 | 4.7 merged. Bug-bash with edge fixtures (0 volunteers, 100 deliveries, etc.). | Hand off the prototype to backend for joint review. |
| Fri w2 | **Sprint demo + retro.** | Same. |

---

## Demo agenda (Fri w2)

1. **Volunteer (phone)** — log in, open `/volunteer/availability/`, tick Mon morning, Wed morning, Fri afternoon. Three rows in `volunteer_availabilities`.
2. **Trigger the daily job manually** (`python manage.py shell` → call the service for "tomorrow's date"):
   - Show `Delivery` rows generated for every active member.
   - Show `Route` rows packing them by kitchen + chunked by 12.
   - Re-run the job → no duplicate rows.
3. **Edge case:** seed a 30-delivery dataset with 1 available volunteer; show 12 assigned + 18 left unassigned + a log line warning about the shortfall.

## Definition of Done for the sprint

- All 7 stories `STATUS: done (sprint-07)`.
- 4.6 + 4.7 each have at least 3 unit tests (happy path, idempotency, edge).
- Volunteer availability editor passes Playwright at 375 px.

## Risks

| Risk | Mitigation |
|---|---|
| Pack-into-routes ordering becomes a debate ("should we minimise drive time?"). | v1 = greedy nearest from kitchen, chunked at 12. Document that real VRP is out of scope; Story 4.15 (Leaflet map) and a routing-API integration are Epic 07 fodder. |
| The daily job timing (04:00 / 04:30) doesn't suit operational reality. | Make the schedule a `SCHEDULE_TIME_*` setting; the demo doesn't need to run at 04:00 — manually triggered is fine. |
| Generating Delivery rows for every member every day in a year scales poorly. | At charity volume (≤ 500 members), this is fine. Document a "switch to per-active-week" optimisation if usage doubles. |
