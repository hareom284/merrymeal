# Sprint 03 — Application flow + admin approval

**Weeks:** 5–6
**Primary epic:** [01 — Identity & onboarding](../../epics/01-identity-onboarding.md)
**Sprint goal:** a visitor can complete a 3-step application (themselves or on behalf of someone else); an admin can approve or reject from a queue; the new member gets a welcome email and can log in.

---

## Stories pulled

| ID | Title | Track | Status | Detail |
|---|---|---|---|---|
| 1.7 | Application — step 1 (contact) | FE + BE pair | planned (sprint-03) | [stories/1.7-application-step-1.md](stories/1.7-application-step-1.md) |
| 1.8 | Application — step 2 (address) | FE + BE pair | planned (sprint-03) | [stories/1.8-application-step-2.md](stories/1.8-application-step-2.md) |
| 1.9 | Application — step 3 (dietary + allergies) | FE + BE pair | planned (sprint-03) | [stories/1.9-application-step-3.md](stories/1.9-application-step-3.md) |
| 1.10 | Caregiver-on-behalf application | FE + BE pair | planned (sprint-03) | [stories/1.10-caregiver-on-behalf.md](stories/1.10-caregiver-on-behalf.md) |
| 1.11 | Admin approval queue list view | FE | planned (sprint-03) | [stories/1.11-admin-approval-queue.md](stories/1.11-admin-approval-queue.md) |
| 1.12 | Admin approve / reject action | FE + BE | planned (sprint-03) | [stories/1.12-admin-approve-reject.md](stories/1.12-admin-approve-reject.md) |

> **For executors:** each story file is a self-contained TDD plan with file paths, code, commands, and expected output. Pattern follows [Sprint 01's stories](../sprint-01/stories/). **Sprint backlog & spillover protocol:** see [backlog.md](backlog.md).

---

## Parallel tracks

This sprint is best run as **two pair-programmed tracks** (because every story crosses the layers):

### Pair 1 — Applicant flow (1.7 → 1.8 → 1.9 → 1.10)
Backend (Dev A) builds the `Application` model + forms + services. Frontend (Dev B) builds the templates + Playwright tests in parallel against fixtures, then wires them together story-by-story.

### Pair 2 — Admin approval (1.11 → 1.12)
Dev C (or Dev B picking up after 1.9) builds the admin list view + approve/reject action. Depends on the `Application` model from 1.7 existing.

If only 2 devs: do Pair 1 first (week 1 + half of week 2), then both swarm Pair 2.

---

## Day-by-day suggestion (2-pair model)

| Day | Pair 1 (applicant) | Pair 2 (admin) |
|---|---|---|
| Mon w1 | Sprint planning. 1.7 model + migration. | Sprint planning. Wireframe admin queue at 1024 px. |
| Tue w1 | 1.7 form + view + Playwright. | Wait on 1.7 — meanwhile prep 1.11 template + filters logic. |
| Wed w1 | 1.7 merged. Start 1.8. | 1.11 view scaffold against a hand-seeded `Application`. |
| Thu w1 | 1.8 merged. Start 1.9. | 1.11 in review. |
| Fri w1 | 1.9 in review. Mid-sprint demo of the 3-step flow on a phone. | 1.11 merged. Mid-sprint demo. |
| Mon w2 | 1.9 merged. Start 1.10. | Start 1.12 approve service (transaction + email + audit log). |
| Tue w2 | 1.10 in review. | 1.12 reject path. |
| Wed w2 | 1.10 merged. | 1.12 view + buttons + Playwright. |
| Thu w2 | Bug-bash applicant flow on real phones. | 1.12 in review. |
| Fri w2 | **Sprint demo + retro.** | Same. |

---

## Demo agenda (Fri w2)

1. **Margaret's daughter on a phone:** opens `/`, taps "Apply for meals", toggles "I'm applying for someone else", completes all 3 steps.
2. **Inbox check:** confirmation email arrives.
3. **Admin on a laptop:** opens `/admin/applications/`, filters by city, opens the application, clicks **Approve**.
4. **Margaret receives:** welcome email, clicks the magic set-password link, sets a password, logs in, sees her empty dashboard.
5. **Audit log:** admin can see the approval row (the audit-log viewer UI is in Epic 06, but the row should already be written).

## Definition of Done for the sprint

- Every story above is `STATUS: done (sprint-03)`.
- The applicant flow has a passing Playwright test at 375 × 667 px.
- The admin flow has a passing Playwright test at 1024 px.
- Transaction atomicity on approve has a dedicated unit test.

## Risks

| Risk | Mitigation |
|---|---|
| The `Application` model adds yet another "person" row alongside `users`; risk of confusion. | Internal naming convention: **Application** = draft, **User** = approved. Document in `apps/accounts/models/applications.py` module docstring. |
| Magic set-password link UX (token expiry, abuse). | Use `django.core.signing` with 7-day expiry; single-use enforced by storing the token hash in a `password_reset_tokens` table and deleting on first use. |
| Caregiver-on-behalf duplicates an existing caregiver account. | Story 1.10 acceptance criteria explicitly cover the "existing caregiver" branch with a unit test. |
