# MerryMeal — Product Backlog

> **Audience:** developers building MerryMeal **without AI tools**. Every story
> in here is self-contained: read it, build it, ship it. You should not need
> to consult any other document to finish a story.

**Sprint length:** 2 weeks
**Team size:** 2–3 developers (split across **Backend** and **Frontend** tracks)
**Definition of "done":** see [Definition of Done](#definition-of-done) below.

---

## 1. How to read this folder

```
docs/product/
├── README.md                       ← you are here (master index)
├── epics/                          ← one file per epic. Acceptance criteria, links to detailed stories.
│   ├── 00-foundation.md
│   ├── 01-identity-onboarding.md
│   ├── 02-kitchen-inventory.md
│   ├── 03-weekly-planning.md
│   ├── 04-delivery-flow.md
│   ├── 05-donations.md
│   ├── 06-dashboards.md
│   └── 07-hardening.md
└── sprints/                        ← one FOLDER per sprint.
    ├── sprint-01/
    │   ├── sprint-plan.md          ← sprint goal, stories pulled, tracks, demo agenda
    │   ├── backlog.md              ← stretch goals, spillover protocol, retro notes
    │   └── stories/                ← one file per detailed, AI-executable story
    │       ├── 0.9-docker-compose.md
    │       ├── 0.10-github-actions-ci.md
    │       └── ...
    ├── sprint-02/
    │   └── ... (same shape)
    └── ...
```

### The three layers — which file answers which question?

| Question | Read |
|---|---|
| "What is this whole epic for?" | `epics/0N-*.md` |
| "Which stories ship this sprint, in which order, on which day?" | `sprints/sprint-NN/sprint-plan.md` |
| "How do I actually build this one story?" | `sprints/sprint-NN/stories/<id>-<slug>.md` |
| "What's the protocol if a story slips?" | `sprints/sprint-NN/backlog.md` |

### Story files are "AI-executable"

Each story file in `sprints/sprint-NN/stories/` is a self-contained TDD plan:
exact file paths, code blocks for tests and implementation, exact shell
commands with expected output, and a Definition of Done checklist. Hand any
story file to a developer **or** to an AI coding agent — they need no other
context to ship it.

Format follows the `superpowers:writing-plans` convention. Steps use checkbox
syntax (`- [ ]`) so the executor can tick off progress.

### Hierarchy

```
Epic         A multi-sprint outcome. Example: "Volunteer & delivery flow".
  ↓
Sprint       2 weeks of work. Pulls stories from one or two epics.
  ↓
Story        One user-facing change a single dev can finish in ≤ 3 days.
  ↓
Task         Sub-steps inside a story (not tracked formally — left to the dev).
```

Stories are numbered `<epic>.<story>`. Example: `4.7` = Epic 4, Story 7.
This ID never changes once published, even if a story is moved between sprints.

### Three flavours of "work"

| Where it lives | What it is |
|---|---|
| `epics/` | Stories grouped by *outcome* (the **what** + the **why**). |
| `sprints/` | Stories grouped by *time-box* (the **when**). Same story IDs as in epics. |
| **Backlog** | Any story not assigned to a sprint yet. Listed at the bottom of each epic file under "Backlog". |

A story moves **out of an epic's Backlog into a sprint** during sprint planning.
A story stays in the epic file forever — sprints just *point* at it.

---

## 2. The user roles you are building for

The schema (`merrymeal_schema_corrected.sql`) defines six roles. Every story
states which role(s) it is for. Know these by heart:

| Role | Real-world person | Primary device |
|---|---|---|
| **member** | Elderly person (e.g. *Margaret, 84*) receiving meals | Phone, low vision, prefers big text |
| **caregiver** | Family or social worker overseeing 1+ members | Phone first, occasionally desktop |
| **volunteer** | Driver/cyclist delivering meals (e.g. *Sarah*) | Phone, often outdoors, patchy signal |
| **partner** | Charity, restaurant, supplier, corporate sponsor staff | Desktop primary, phone secondary |
| **donor** | Anyone giving money. May not have an account at all. | Phone first (mobile checkout) |
| **kitchen_staff** | Cooks recording food-safety checks, batches, stock | Tablet primary |
| **admin** | MerryMeal operations staff | Desktop primary (the only desktop-first role) |

**Mobile-first is not optional.** Build every screen for 375 px viewport first.
Layer up to `md:` / `lg:` for tablet/desktop using Tailwind breakpoints.
The only exceptions are noted explicitly in admin-facing stories.

---

## 3. Sprint cadence (2 weeks)

| Day | Ceremony | Owner | Output |
|---|---|---|---|
| Mon (week 1) | **Sprint planning** | Team lead | Pull stories from epic backlog into `sprints/sprint-NN.md`. Confirm Definition of Ready for each. |
| Daily | **Stand-up** (15 min) | Team | What I did / what I'll do / where I'm stuck. |
| Wed (week 2) | **Story review** (mid-sprint) | Team | Demo any story that is "done dev work, awaiting review". |
| Fri (week 2) | **Sprint demo + retro** | Team | Demo every shippable story. Retro: what to keep / drop / try. |

### Parallel tracks

Each sprint splits stories into two tracks so 2–3 devs can work without
stepping on each other:

- **Backend track** — models, migrations, services, management commands,
  background jobs, tests for those layers.
- **Frontend track** — templates, HTMX partials, Tailwind tweaks, Alpine
  interactions, Playwright tests at 375 px viewport.

A few sprints have a third **Admin/Ops** mini-track (Django admin
customisation, seed data, CI). Sprint files spell out which stories go in
which track.

### Branching & PRs

- One branch per story: `epic-<N>/story-<NN>-<short-slug>` (e.g.
  `epic-1/story-03-application-step-1`).
- Open PR against `main` when the story meets Definition of Done.
- PR title: `[<story-id>] <story title>`. Example:
  `[1.3] Member application — step 1 (contact details)`.
- PR description must include the **acceptance-criteria checklist** copied
  from the story, ticked off.
- One reviewer (any teammate). Merge to `main`. Deploy from `main`.

---

## 4. Story status

Each story carries a status badge in its epic file:

| Badge | Meaning |
|---|---|
| `STATUS: backlog` | Not yet pulled into a sprint. |
| `STATUS: planned (sprint-NN)` | Assigned to a sprint but work has not started. |
| `STATUS: in-progress (@dev)` | A dev has picked it up. Their name in `@dev`. |
| `STATUS: review` | Dev work complete; PR open; awaiting review. |
| `STATUS: done (sprint-NN)` | Merged to `main` in that sprint. |
| `STATUS: blocked (reason)` | Cannot progress. Reason must be one sentence. |

Update the badge in the epic file when status changes. Sprint files
mirror the latest status.

---

## 5. Definition of Ready (DoR)

A story is "ready" to be pulled into a sprint when **all** of the following
are true. If any are missing, sprint planning rejects the story and sends
it back to the backlog.

- [ ] The story has a clear **user story sentence** (`As a … I want … so that …`).
- [ ] **Acceptance criteria** are written as a checklist with no "TBD".
- [ ] **Technical notes** list every file that must be created or modified.
- [ ] **DB tables touched** are listed (matches `merrymeal_schema_corrected.sql`).
- [ ] **Mobile viewport** behaviour is described (or marked "desktop-only — admin").
- [ ] **Test strategy** is named (unit / integration / Playwright / manual).
- [ ] The story can be completed by **one developer in ≤ 3 days**. Bigger? Split it.
- [ ] Story has no unresolved dependencies on stories not yet in `done`.

## 6. Definition of Done (DoD)

A story is "done" when **all** of the following are true. PR is blocked
from merging until every box is ticked.

- [ ] Every acceptance criterion in the story is verifiably true.
- [ ] `pytest` passes locally (and in CI).
- [ ] `ruff check .` passes with no errors.
- [ ] If the story touches UI: a Playwright test at **375 × 667 px** (iPhone SE
      viewport) covers the happy path.
- [ ] If the story touches UI: manually verified at 375 px and 1024 px.
- [ ] If the story adds a model or migration: `python manage.py makemigrations
      --check` passes (no drift) and `migrate` runs clean against an empty DB.
- [ ] If the story changes auth, permissions, or audited tables: an audit-log
      entry is written (see [`docs/superpowers/specs/...`](../superpowers/specs/2026-06-01-merrymeal-django-design.md) §5).
- [ ] README or in-app help updated **only if behaviour changed for the user**.
      Do not write internal-only docs as part of a story.
- [ ] PR reviewed by one teammate and merged to `main`.
- [ ] Story badge updated to `STATUS: done (sprint-NN)` in the epic file.

> **Why these specific checks?** The roadmap spec
> ([§3 Mobile-first](../superpowers/specs/2026-06-01-merrymeal-django-design.md))
> says we are building for Margaret (low vision) and Sarah (volunteer on a
> bike). Skipping the 375 px check is the single fastest way to ship something
> they cannot use.

---

## 7. The Epics at a glance

| # | Epic | Sprints | Status | One-line goal |
|---|---|---|---|---|
| 00 | [Foundation](epics/00-foundation.md) | 1 | partially done | An empty but production-shaped Django app a dev can clone, run, deploy. |
| 01 | [Identity & onboarding](epics/01-identity-onboarding.md) | 2 | not started | A visitor can apply to be a member; an admin can approve them. |
| 02 | [Kitchen & inventory backbone](epics/02-kitchen-inventory.md) | 2 | not started | Admins can model real-world kitchen state, including expiring stock & safety checks. |
| 03 | [Weekly meal planning](epics/03-weekly-planning.md) | 1 | not started | Admins plan the week; members see what's coming. 10 km / frozen-weekend rule enforced. |
| 04 | [Volunteer & delivery flow](epics/04-delivery-flow.md) | 2 | not started | The daily dispatch loop works end-to-end on a phone. **Mobile-critical.** |
| 05 | [Donations & campaigns](epics/05-donations.md) | 1 | not started | A stranger can donate in under 30 seconds. |
| 06 | [Dashboards & reporting](epics/06-dashboards.md) | 1 | not started | Admins, partners, donors each get one screen telling them what matters. |
| 07 | [Hardening & nice-to-haves](epics/07-hardening.md) | ongoing | backlog | PWA, encryption, pen-test, perf budget. Pulled into sprints opportunistically. |

**Total core sprints: 10** (≈ 20 weeks ≈ 5 months at one team running 2-week sprints).

## 8. Sprint plan at a glance

| Sprint | Weeks | Primary epic(s) | Sprint goal |
|---|---|---|---|
| [01](sprints/sprint-01/sprint-plan.md) | 1–2 | Epic 00 | Finish foundation: Docker, CI, Playwright scaffolding. |
| [02](sprints/sprint-02/sprint-plan.md) | 3–4 | Epic 01 | Identity models + landing page. |
| [03](sprints/sprint-03/sprint-plan.md) | 5–6 | Epic 01 | Member application flow + admin approval queue. |
| [04](sprints/sprint-04/sprint-plan.md) | 7–8 | Epic 02 | Kitchens, ingredients, meals, recipes. |
| [05](sprints/sprint-05/sprint-plan.md) | 9–10 | Epic 02 | Stock batches, food-safety checks, expiry alert job. |
| [06](sprints/sprint-06/sprint-plan.md) | 11–12 | Epic 03 | Weekly planner + 10 km / frozen rule + member "today" card. |
| [07](sprints/sprint-07/sprint-plan.md) | 13–14 | Epic 04 | Availability, routes, deliveries, auto-assign service. |
| [08](sprints/sprint-08/sprint-plan.md) | 15–16 | Epic 04 | Volunteer mobile UI, POD photo, feedback, caregiver alerts. |
| [09](sprints/sprint-09/sprint-plan.md) | 17–18 | Epic 05 | Donations + Stripe Checkout + donor impact. |
| [10](sprints/sprint-10/sprint-plan.md) | 19–20 | Epic 06 | Dashboards, exports, audit viewer. |

After sprint 10, the team pulls from Epic 07 (hardening) and any backlog
items that emerged during the build.

---

## 9. Cross-cutting rules every story must respect

Pulled from the roadmap spec
([§5](../superpowers/specs/2026-06-01-merrymeal-django-design.md)). If a
story would violate one of these, **flag it in the PR**, don't silently
break the rule.

- **Models are schema-only.** Fields, `Meta`, `__str__`, choices. Nothing else.
  All state-changing logic lives in `apps/<name>/services/`.
- **Soft delete** via `core.SoftDeleteModel` for `users`, `cities`, `meals`.
- **Money** is integer cents. Never floats.
- **Time zone** is `Australia/Melbourne`. All timestamps stored UTC.
- **Roles** map to Django groups + a `@role_required(...)` decorator.
- **Object permissions:** a member sees only their own deliveries; a
  volunteer only their own routes; a caregiver only members they are linked
  to via `member_caregivers`.
- **Audit log** entries written for changes to `users`, `user_addresses`,
  `diet_preference_user`, `allergy_user`, `meal_plans`, `deliveries`.
- **HTMX progressive enhancement:** every form must work with HTMX disabled.
- **Mobile-first:** 375 px design first, layer up. Touch targets ≥ 44 × 44 px.

---

## 10. Glossary

| Term | Meaning in this codebase |
|---|---|
| **Member** | A `users` row with `role='member'` who receives meals. |
| **Caregiver** | A `users` row with `role='caregiver'` linked to one or more members via `member_caregivers`. |
| **Volunteer** | A `users` row with `role='volunteer'` who delivers meals. |
| **Partner** | A `partners` row (charity, restaurant, supplier, corporate). |
| **Kitchen** | A `kitchens` row. Has lat/lng and a `service_radius_km` (default 10). |
| **The 10 km rule** | Members **inside** kitchen radius get **fresh** meals Mon–Fri. Members **outside** the radius OR weekend deliveries get **frozen**. Computed by Haversine in `apps/planning/services.py`. |
| **Service date** | The local Melbourne date a meal is intended to be eaten. Stored as a `DATE`, not a `DATETIME`. |
| **Route** | A `routes` row: one volunteer + one date + a status. Has many deliveries. |
| **POD** | Proof of delivery — the photo uploaded by the volunteer at delivery time. |
| **Allergen flag** | A red badge shown on a member's "today" card if their `allergy_user` rows intersect with the meal's `meal_ingredients` (via the ingredient → allergen map). |

---

## 11. Source documents

This backlog is derived from — and stays consistent with — the following
authoritative documents:

- **Roadmap spec:** [`docs/superpowers/specs/2026-06-01-merrymeal-django-design.md`](../superpowers/specs/2026-06-01-merrymeal-django-design.md)
- **DB schema:** [`merrymeal_schema_corrected.sql`](../../merrymeal_schema_corrected.sql)
- **Phase 0 implementation plan:** [`docs/superpowers/plans/2026-06-01-phase-0-foundation.md`](../superpowers/plans/2026-06-01-phase-0-foundation.md)
- **README (setup, stack, layering):** [`README.md`](../../README.md)

If you find a contradiction between this backlog and one of those documents,
**the source document wins** — please open a PR fixing this backlog and
flag it at the next stand-up.
