# Sprint 09 — Donations + Stripe Checkout

**Weeks:** 17–18
**Primary epic:** [05 — Donations & campaigns](../../epics/05-donations.md)
**Sprint goal:** a stranger can give $50 via Apple Pay in under 30 seconds, receive a receipt, and be told "your $50 = 17 meals". Recurring donors can manage subscriptions.

---

## Stories pulled

| ID | Title | Track | Status | Detail |
|---|---|---|---|---|
| 5.1 | `donations` app: `Campaign` model | Backend | planned (sprint-09) | [stories/5.1-campaign-model.md](stories/5.1-campaign-model.md) |
| 5.2 | `Donation` model | Backend | planned (sprint-09) | [stories/5.2-donation-model.md](stories/5.2-donation-model.md) |
| 5.3 | Public donate page (mobile-first) | FE + BE pair | planned (sprint-09) | [stories/5.3-public-donate-page.md](stories/5.3-public-donate-page.md) |
| 5.4 | Stripe Checkout integration | Backend | planned (sprint-09) | [stories/5.4-stripe-checkout.md](stories/5.4-stripe-checkout.md) |
| 5.5 | Thank-you page + receipt email | FE + BE pair | planned (sprint-09) | [stories/5.5-thanks-receipt.md](stories/5.5-thanks-receipt.md) |
| 5.6 | Donor impact view | FE + BE pair | planned (sprint-09) | [stories/5.6-donor-impact.md](stories/5.6-donor-impact.md) |
| 5.7 | Recurring-donation management page | FE + BE pair | planned (sprint-09) | [stories/5.7-recurring-management.md](stories/5.7-recurring-management.md) |
| 5.8 | Admin campaign-progress card | FE + BE pair | planned (sprint-09) | [stories/5.8-admin-campaign-progress.md](stories/5.8-admin-campaign-progress.md) |

> **For executors:** each story file is a self-contained TDD plan with file paths, code, commands, and expected output. Pattern follows [Sprint 01's stories](../sprint-01/stories/). **Sprint backlog & spillover protocol:** see [backlog.md](backlog.md).

---

## Parallel tracks

### Backend track — Dev A
1. **5.1** + **5.2** models (½ day).
2. **5.4** Stripe Checkout + webhook (~3 days).
3. **5.7** management-page service + magic-link tokens (~1½ days).

### Frontend track — Dev B
1. **5.3** donate page at 375 px (~2 days).
2. **5.5** thank-you + receipt email templates (~1 day).
3. **5.6** impact view + chip captions (~½ day).
4. **5.7** UI (~1½ days, pair with backend).
5. **5.8** progress card (~1 day).

### Admin / ops track — Dev C
- Set up the charity's Stripe account in test mode + dev webhook with `stripe listen`.
- Define the v1 campaigns (e.g. "General fund", "Winter appeal 2026"); load via a data migration.
- Verify Apple Pay / Google Pay show up on the demo phone.

---

## Day-by-day suggestion

| Day | Backend | Frontend | Admin/Ops |
|---|---|---|---|
| Mon w1 | Sprint planning. 5.1 + 5.2 models. | Sprint planning. Wireframe donate page at 375 px. | Sprint planning. Stripe test creds + `stripe listen` running locally. |
| Tue w1 | Start 5.4 service: `create_checkout_session`. | 5.3 template + form. | Confirm Apple Pay shows on real iPhone. |
| Wed w1 | 5.4 webhook + signature verification. | 5.3 Playwright at 375 px. | Verify dj-stripe migrations. |
| Thu w1 | 5.4 unit tests (mock Stripe SDK + webhook). | 5.3 in review. | Help debug webhook signature. |
| Fri w1 | 5.4 in review. Mid-sprint demo: end-to-end test charge using Stripe CLI trigger. | Mid-sprint demo of donate page on phone. | Same. |
| Mon w2 | 5.4 merged. Start 5.7 magic-link service. | 5.5 + 5.6 templates. | Begin pre-work for Sprint 10 (CSV/PDF library decision). |
| Tue w2 | 5.7 cancel-subscription via Stripe API. | 5.7 UI (request page + list page). | Help Sprint 10 wireframes. |
| Wed w2 | 5.7 in review. | 5.8 progress card. | Same. |
| Thu w2 | Bug-bash with real card + Stripe CLI re-trigger (idempotency check). | 5.8 in review. | Same. |
| Fri w2 | **Sprint demo + retro.** | Same. | Same. |

---

## Demo agenda (Fri w2)

1. **Stranger (real phone, real Apple Pay test card)** — opens `/donate/`, taps $50, taps **Donate**, biometric, confirmed. Total stopwatch: under 30 seconds.
2. Thank-you page renders: "Your $50 ≈ 17 meals".
3. Receipt email lands in inbox.
4. **Stripe CLI** re-fires the webhook — no double-count (idempotency test).
5. Donor opens `/donate/manage/`, requests a magic link, opens the email, lands on the manage page, cancels (cancellation flows back via webhook).
6. Admin opens `/admin/campaigns/`, sees the bar tick to $50.

## Definition of Done for the sprint

- All 8 stories `STATUS: done (sprint-09)`.
- Webhook idempotency has a unit test (re-fire same event → no second row).
- Receipt emails render correctly in Gmail iOS + Outlook desktop (litmus / dev inbox check).
- No Stripe secret key committed (CI secret scanner enforced).

## Risks

| Risk | Mitigation |
|---|---|
| Charity does not yet have a Stripe account by start of sprint. | Admin/Ops track unblocks this in week 0 (during Sprint 08 close-out). |
| Webhook signature verification subtle bugs. | Use dj-stripe's signed-payload helper rather than rolling our own. Test with `stripe trigger`. |
| Apple Pay only shows on HTTPS in production. | Use `stripe.com`-hosted Checkout — Stripe handles wallet detection. Dev tunnel via `stripe listen --forward-to` if needed. |
| Magic-link tokens persist on shared devices. | 30-minute expiry; single-use enforced server-side. |
