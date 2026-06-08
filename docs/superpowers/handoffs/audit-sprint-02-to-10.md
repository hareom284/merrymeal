# Audit — Sprint 02 → Sprint 10

**Date:** 2026-06-09
**Branch audited:** `implement-sprint-02` at HEAD `d0c3b23` (post-Sprint 09 merge)
**Scope:** all 59 stories across Sprints 02 → 10 (Epics 01 → 06)
**Method:** 6 parallel read-only audit agents (5 sprint-pair audits + 1 cross-cutting)
**Tests passing at time of audit:** 625 / 627 (2 pre-existing skips)

This document is the consolidated gap report. It supersedes
`sprint-08-resume.md` (now removed) and complements
`sprint-10-resume.md`. Findings are ranked P0 → P4 by user impact.

---

## Executive verdict

| Sprint | Stories | Functionally complete | Real gap | Doc/test gap only |
|---|---|---|---|---|
| 02 + 03 | 12 | 11 | 1 (1.12 audit log) | 8 (e2e specs) |
| 04 + 05 | 10 | 10 | 0 | 10 (epic status doc; 2 e2e specs) |
| 06 | 8 | 7 | 1 (3.4 member view) | 4 (e2e + epic doc) |
| 07 + 08 | 14 | 12 | 2 (4.11 orphaned UI, 4.12 URL) | 0 |
| 09 + 10 | 15 (5.1–5.8 + 6.1–6.7) | 11 | 2 (5.3/5.4 wiring, 6.1 dead links) | 3 truly backlog (6.3/6.4/6.5) |
| **Total** | **59** | **51** | **6** | **23** |

51 / 59 stories are materially complete. 6 stories have **real** gaps that
affect users today. 3 stories (6.3 / 6.4 / 6.5) are truly backlog. The
remaining items are documentation drift or missing e2e harness, not
correctness issues.

---

## 🔴 P0 — Production-breaking (ship-blocking)

### P0-1 — Live donate POST returns a stub URL, Stripe Checkout never runs

`apps/donations/services/donate.py:18` imports `create_checkout_session`
from the **stub** module `apps.donations.services.stripe` (which returns
the literal string `"https://stripe.test/sess_stub"`) instead of the
real implementation at `apps.donations.services.stripe_checkout`.

Net effect: every live POST from `/donate/` redirects donors to
`https://stripe.test/sess_stub` — donations cannot be collected.

**Fix:** rewire the import; delete `apps/donations/services/stripe.py`
(or re-export from it). Add an integration test that asserts the donate
POST resolves to a real Stripe session URL.

**Files:**
- `apps/donations/services/donate.py:18`
- `apps/donations/services/stripe.py` (stub — delete)
- `apps/donations/services/stripe_checkout.py` (real — wire from donate)

### P0-2 — Admin approve/reject writes zero audit-log entries

`Application` and `User` are never registered with `django-auditlog`.
The approve/reject services in `apps/accounts/services/applications.py`
call `auditlog.context.set_actor(admin_user)` correctly, but with no
`auditlog.register(...)` for the model, no `LogEntry` rows are ever
written. Story 6.6 audit viewer will return an empty result for every
member-approval history.

**Fix:** one-liner — add `auditlog.register(Application)` and
`auditlog.register(User)` in `apps/accounts/apps.py::AccountsConfig.ready()`,
mirroring the donations / delivery apps that already do this.

**Files:**
- `apps/accounts/apps.py` (`AccountsConfig.ready()`)

---

## 🟠 P1 — Feature shipped but unreachable to users

### P1-3 — Member dashboard still renders mocked data

`apps/dashboards/views/member.py` returns hand-fabricated context
(`"Herb-roasted chicken"`, hardcoded `feedback_prompt` dict, week menu
strings) and `templates/dashboards/member.html` renders those mocks.
The real service `apps/dashboards/services/member_today.py::get_today_card`
exists, is unit-tested, and is **never called from any view**.

This is the root cause of the next two cascading gaps.

**Files:**
- `apps/dashboards/views/member.py` (view returns mocked context)
- `templates/dashboards/member.html` (template renders mocked vars)
- `apps/dashboards/tests/test_member_view.py` (asserts mocked strings)
- `apps/dashboards/services/member_today.py` (real service, orphaned)

### P1-4 — Stories 4.11 (feedback) + 4.12 (tracking) UI orphaned (cascade from P1-3)

Both stories shipped backend + service + test + view + URL correctly.
Both wrapped their UI inside `templates/dashboards/_member_today_card.html`
(4.12 adds the tracking pill, 4.11 wraps a feedback conditional around
it). That partial is **not `{% include %}`d by any production template**.

Margaret cannot see the 2-tap feedback prompt or the live tracking pill
on her dashboard, despite both features being fully implemented and
green in CI.

**Fix:** Resolves with P1-3 — once `member.html` includes the partial
and the view calls `get_today_card`, both features become reachable.

**Files:** same as P1-3.

### P1-5 — Admin home cards have 4 of 5 dead links

`apps/dashboards/services/admin_summary.py` builds five cards; each
card has a `link` field reverse-resolved from a named URL. Four of the
five fall back to `"#"` because the destination views were never
created:

- `dashboards:expiring_stock` — dead
- `dashboards:failed_deliveries_today` — dead
- `dashboards:unassigned_deliveries_today` — dead
- `dashboards:fs_failures_recent` — dead
- `dashboards:admin_applications` — only one that resolves

Cards render fine; admin clicks → nothing happens. Silent UX failure.

**Fix:** either (a) create the four filtered-list views/URLs per
Story 6.1 spec, or (b) point the cards at existing list pages
(e.g. the audit viewer with a pre-filled filter).

**Files:**
- `apps/dashboards/services/admin_summary.py:142-160`
- `apps/dashboards/urls/` (add 4 routes)
- `apps/dashboards/views/admin_home.py` (add 4 list views)

---

## 🟡 P2 — Stories not started (true backlog, expected)

These are real Sprint 10 stories not yet attempted. Status lines
correctly mark them. No code, no templates, no routes exist.

| Story | Title |
|---|---|
| 6.3 | Donor history page |
| 6.4 | Tax receipt printer-friendly page |
| 6.5 | Board report: CSV + PDF (weasyprint) |

Sprint 10 was always partial — 4 of 7 stories shipped (6.1, 6.2, 6.6,
6.7). These 3 are the explicit remainder. No urgency unless promised
externally.

---

## 🟢 P3 — Implementation deviations (documented or trivial)

### P3-7 — 5.7 cancel-subscription uses immediate `Subscription.delete`

`apps/donations/services/manage.py:200-205` calls
`stripe.Subscription.delete(subscription_id)` (immediate cancellation)
instead of the spec's preferred `cancel_at_period_end=True` (graceful
end-of-period cancellation). The deviation is documented in code.

Whether to "fix" depends on charity policy: graceful means the donor
keeps benefits to end-of-period; immediate means money stops now.
1-line change if you want graceful.

### P3-8 — 5.3 donate-page chips show placeholder copy

`templates/donations/donate.html:117-123` renders a single neutral
caption "Every donation funds meals for people in need." instead of
per-chip "≈ N meals" captions. The `meals_for` template filter (from
Story 5.6) exists and works on other pages but is not applied here.

Story 5.3 acceptance criterion explicitly required the per-chip count.

**Fix:** swap placeholder for `{{ chip.amount_cents|meals_for }}
meals` in each chip block. Reload Tailwind not required.

### P3-9 — 4.12 URL prefix wrong

Mounted at `/volunteer/member/delivery/<pk>/status/` instead of spec's
`/member/delivery/<pk>/status/`. Reverse name `delivery:tracking_status`
unchanged so callers are unaffected, but the URL itself is misleading
(it's a member endpoint, not a volunteer endpoint).

**Fix:** one-line move in `apps/delivery/urls.py:48`.

### P3-10 — 3.2 `find_serving_kitchen` helper never added

Story 3.4 required adding `find_serving_kitchen(member)` to
`apps/planning/services/assignment.py` for reuse. It was instead
inlined as `_nearest_kitchen_for` inside
`apps/dashboards/services/member_today.py`. Not reusable.

### P3-11 — 3.4 duplicates 3.5's allergen logic

`member_today.py` has its own ingredient/allergen flattening instead of
calling `apps/planning/services/allergen.py::meal_allergens_for_member`.
Functionally identical; violates the spec's "single integration point"
principle. Pure cleanup.

### P3-12 — Story 1.12 atomicity test missing

The approve/reject service wraps writes in `transaction.atomic()` and
defers email with `transaction.on_commit()` — correct. But no test
mocks a downstream write failure to assert rollback. Future regression
in transactional semantics would be invisible.

**Fix:** add one test in `apps/accounts/tests/test_approve_reject.py`
that patches `send_welcome_email` to raise inside the atomic block and
asserts no User / Application row was committed.

---

## 📄 P4 — Documentation drift, missing e2e harness, latent warnings

### P4-13 — Epic docs 01, 02, 03 stuck at `STATUS: backlog` for ~30 shipped stories

| Epic | Stories | Reality | Doc says |
|---|---|---|---|
| 01-identity-onboarding | 12 (1.1–1.12) | All shipped Sprint 02/03 | All `backlog` |
| 02-kitchen-inventory | 10 (2.1–2.10) | All shipped Sprint 04/05 | All `backlog` |
| 03-weekly-planning | 8 (3.1–3.8) | All shipped Sprint 06 | All `backlog` |

Bulk-update needed. Anyone reading the human-facing epic docs to plan
new work gets a completely wrong picture.

**Fix:** three `Edit` calls with `replace_all=true` on each file, plus
one commit per epic to keep history clean.

### P4-14 — ~13 Playwright specs missing

Stories with no `tests_e2e/<story>.spec.ts` file even though the spec
DoD requires one:

`1.6` landing, `1.7` `1.8` `1.9` application steps, `1.10` caregiver,
`1.11` admin queue, `1.12` approve, `2.6` stock receive, `2.8` safety
check, `3.4` member today, `3.6` planner diet warning, `3.8` caregiver
list, `6.1` admin home cards, `6.7` partner referral.

Server-side unit tests cover the happy paths so this is not a
correctness gap, but the mobile/responsive assertions documented in the
specs are uncovered.

### P4-15 — 5 existing Playwright specs are silent no-ops

`tests_e2e/donate.spec.ts`, `thanks.spec.ts`, `mark-failed.spec.ts`,
`feedback-2tap.spec.ts`, `mark-delivered.spec.ts` all gate their tests
behind environment variables — `E2E_SEED_DONATE_FIXTURE`,
`E2E_SEED_VOLUNTEER_FIXTURE`, `E2E_SEED_MEMBER_FIXTURE` — and the seed
fixtures themselves have never been built. CI skips all five silently.

This means the entire donation + volunteer-today happy paths are
**not** exercised by e2e in CI, despite the specs existing.

**Fix:** create `tests_e2e/seed.sh` (and the Django management
commands it invokes) so the env-var-gated specs actually run on PRs.

### P4-16 — `expiry_alerts` idempotency test silently skipped

`apps/kitchens/tests/test_expiry_alerts.py:50` —
`test_idempotent_within_same_day` is skipped with the rationale
`"ExpiryAlertLog savepoint/transaction interaction under investigation"`.

This is a real correctness property of the recurring daily expiry-alert
email job. The skip is hiding either a bug or a test-harness
limitation. Worth resolving before more retry logic lands on top.

### P4-17 — 3.7 validate-radius CI job missing

Spec DoD said *"Wired into CI as a non-blocking job"*. Implementation
instead added a comment to `.github/workflows/ci.yml` noting that the
django-Q schedule runs in the worker container at 02:30 Melbourne time
and deliberately doesn't have a CI counterpart.

Acceptable trade-off (worker-side cron is real), but worth flipping the
DoD to "deferred" rather than silently leaving it open.

### P4-18 — `django_q` retry/timeout warning on every command

Every `manage.py` invocation prints:

> `UserWarning: Retry and timeout are misconfigured. Set retry larger
> than timeout, failure to do so will cause the tasks to be retriggered
> before completion.`

Trivial `Q_CLUSTER` config tweak in `config/settings/base.py`.

### P4-19 — `AppConfig.ready()` querying the DB on import

Every startup prints:

> `RuntimeWarning: Accessing the database during app initialization is
> discouraged. To fix this warning, avoid executing queries in
> AppConfig.ready() or when your app modules are imported.`

Likely a signal-handler registration that touches the DB. Trace via a
git-grep for `.objects.` inside `apps/*/apps.py` and move the query out
of the import path.

### P4-20 — 5.7 `verify_token` lacks `select_for_update`

`apps/donations/services/manage.py` documents the gap in its docstring:
the magic-link token row could theoretically be consumed twice in a
narrow race window. `MagicLinkToken.token_id` is unique, so the
practical risk is contrived, but the lock should be added for
correctness.

---

## Drift that is acceptable (NOT gaps)

These items were flagged by audit agents but are intentional or
forward-compatible:

- `Ingredient` model gained `contains_allergens` M2M + `IngredientAllergy`
  through model (beyond Story 2.2's "schema only"). Added by Story 3.5
  allergen mapping — intentional.
- `Meal` gained `ingredients` and `diets` M2M fields (beyond Story 2.3's
  "schema only"). Added by Stories 2.4 + 3.5 — intentional.
- `MealIngredient.meal.related_name` is `meal_ingredients` instead of
  spec's `ingredients` — forced by `Meal.ingredients` M2M to avoid
  collision.
- `FoodSafetyCheck.meal_plan` FK string ref is `"planning.MealPlan"`
  (the model lives in `apps/planning/`) instead of spec's
  `"meals.MealPlan"`. Project re-org, not a bug.
- `CaregiverLink` reverse name `caregiver_links_as_member` instead of
  spec's `caregivers`. Locked schema; templates / services already
  adapted.
- `User` model has `full_name` only, no `first_name` / `last_name` /
  `phone`. All consumer templates derive short names via services
  (`member_display`, `volunteer_display`). Caregiver alert SMS uses
  `getattr(caregiver, "phone", "") or ""` and skips SMS when absent.

---

## Recommended remediation plan

### Wave A — P0 + P1 cluster (highest user value)

Fan out 4 parallel agents (each touches disjoint files):

1. **Fix P0-1**: rewire donate.py → stripe_checkout, delete stub,
   add integration test.
2. **Fix P0-2**: register `Application` + `User` with auditlog in
   `apps/accounts/apps.py`. Add a test that approve→ logentry exists.
3. **Fix P1-3 + P1-4 cluster**: rewrite `apps/dashboards/views/member.py`
   to call `get_today_card`; replace mocked context in `member.html`
   with `{% include "dashboards/_member_today_card.html" %}`; update
   `test_member_view.py`. Unblocks 4.11 + 4.12 in one shot.
4. **Fix P1-5**: add 4 admin-list views + URLs that the home cards
   already expect.

After Wave A the live site is correct, the audit viewer works, and the
member dashboard is real.

### Wave B — P3 polish (1–2 days, one agent, one PR)

Knock out P3-7, P3-8, P3-9, P3-10, P3-11, P3-12, P4-13, P4-18, P4-19
in a single sweep. All small, low-risk edits.

### Wave C — Test hygiene (1 agent)

Build the `tests_e2e/seed.sh` + seed management commands so the 5
gated specs actually run (P4-15). Investigate the expiry-alerts skip
(P4-16). Optionally add the missing Playwright specs (P4-14) story-by-
story.

### Wave D — Sprint 11 backlog

Stories 6.3 / 6.4 / 6.5 are real new features for whoever picks up
Sprint 11. Story specs already exist under
`docs/product/sprints/sprint-10/stories/`. Estimate ~1 sprint to
complete the remainder of Epic 06.

---

## Audit methodology (for the next person who runs one)

Each of 5 sprint-pair agents was given:

1. The list of story spec paths in its scope.
2. The list of apps in scope.
3. A list of known deviations to verify (from previous handoff notes).
4. Instruction to verify each "Files to create or modify" row, each
   acceptance criterion, each "Task breakdown" task, and each epic-doc
   status line.
5. Report format: `=== Story X.Y ===` block per story with bullet
   list of gaps, or `=== Story X.Y === OK`.
6. Time budget 5–10 minutes per agent.
7. Constraint: read-only, no fixes, no test runs (suite already
   known-green).

The 6th agent ran the cross-cutting sweep (`makemigrations --check`,
TODO grep, `test.skip` enumeration, commented-out routes, env audit,
epic-status drift, orphan files, dead URLs, doc obsolescence).

Total wall-clock for the audit: ~10 minutes (all 6 agents in
parallel).

---

## Pointers

- `CLAUDE.md` (repo root) — codebase orientation
- `README.md` — human setup
- `docs/product/sprints/sprint-XX/` — story specs (authoritative)
- `docs/product/epics/0X-*.md` — epic-level status (currently
  stale for epics 01, 02, 03 — see P4-13)
- `docs/superpowers/handoffs/sprint-10-resume.md` — in-flight
  Sprint 10 state from a prior session
