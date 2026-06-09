# Sprint 12 — Member self-service screens

**Status:** approved (verbal, 2026-06-09)
**Sprint focus:** ship the 8 member-role screens shown in the user's
mockups that aren't yet built. One follow-up sprint (13) handles the
single schema-touching story (MealPause).

## Goal

A logged-in member can navigate the whole app from a thumb-reachable
4-tab bottom nav, see their profile, view the weekly menu, read
notifications, track today's delivery, rate yesterday's meal, and get
help — all without the dashboard hardcoding dead `href="#"` links.

## Scope rules (decisions captured)

| Decision | Choice | Cost saved |
|---|---|---|
| Track delivery map | **Static Mapbox snapshot**, refresh every 60s | Avoids JS SDK + GPS streaming |
| Notifications source | **Synthesized from existing data** at request time | No new model, no signals |
| Pause deliveries scope | **Form + record only** (no planning integration) | Deferred to sprint 13 |
| Bottom nav | **Home / Menu / Profile / Help** (mockup-faithful) | Sign-out moves into Profile; Donate drops from member nav |

## Stories (sprint 12, ordered for execution)

1. **12.1 — Restructure member bottom nav to Home / Menu / Profile / Help**
   Update `apps/dashboards/services/navigation.py::_MEMBER_NAV`. New
   icons: `menu` (utensils), `profile` (user), `help` (life-ring).
   Routes that don't exist yet stub to `dashboards:member` so taps
   never 404; each subsequent story repoints its tab.

2. **12.2 — Landing page redesign**
   New copy ("Warm meals delivered with a friendly smile."), Apply +
   Donate primary CTAs, "5,000+ MEALS DAILY" chip in brand header,
   "How it works — Three caring steps" section. Replaces the current
   role-picker design at `templates/dashboards/landing.html`. Anonymous
   only — authenticated users still redirect to `/dashboard/`.

3. **12.3 — Help & contact page**
   `GET /help/` → `dashboards:help`. Static template with phone CTA,
   3 quick-action links (Pause deliveries, Change delivery time, Update
   dietary needs — each linking to the relevant page or `mailto:` if not
   yet built), 4 FAQ accordions, Email + Chat buttons (Chat = `mailto:`
   for v1). Repoints the Help nav tab.

4. **12.4 — My profile page (read-only)**
   `GET /profile/` → `dashboards:member_profile`. Renders user's
   personal block (name/phone/address/DOB), Diet chips (existing
   DietPreference m2m), Allergy red pills (existing Allergy m2m),
   Emergency contact (existing CaregiverLink first row), reassessment
   countdown banner, Sign-out form. Read-only; "Edit" button is a stub.
   Repoints the Profile nav tab.

5. **12.5 — Standalone weekly menu page**
   `GET /menu/` → `dashboards:weekly_menu`. Reuses the existing
   `build_member_dashboard_context()` week-menu data with a
   richer per-day card (ingredients, allergens, delivery state).
   Repoints the Menu nav tab. Also fixes the "See full week" dead
   link on the dashboard.

6. **12.6 — Notifications page (synthesized)**
   `GET /notifications/` → `dashboards:notifications`. New service
   `build_member_notifications(user)` queries today's Delivery,
   DeliveryFeedback presence, member's `partner.reassessment_date`,
   tomorrow's MealPlan; returns a list of `{kind, title, body, when,
   icon, url}` dicts. "Mark read" is a no-op POST that returns 204
   (since synthesized; nothing to mark). Topbar bell becomes a link.

7. **12.7 — Track delivery page (Mapbox static)**
   `GET /track/` → `delivery:member_track`. Renders today's Delivery
   with ETA banner, status pill, progress timeline, meal card, Call +
   Message buttons (`tel:` / `sms:` links to volunteer phone if
   available, else hidden). Map area = `<img>` from Mapbox Static Images
   API centered on the volunteer's last known location (use kitchen
   coords as fallback). `MAPBOX_TOKEN` env var. Service:
   `apps/delivery/services/map_snapshot.py::static_map_url(lat, lon)`.

8. **12.8 — Rate meal standalone page**
   `GET /rate/<delivery_id>/` → `delivery:rate_meal`. Wraps the existing
   `_feedback_card.html` partial in a full-page chrome (back button,
   "Rate your meal" title, meal info card on top, Submit + Skip
   buttons). Reuses the existing feedback service. Links from
   Notifications "How was lunch yesterday?" item and the dashboard's
   feedback CTA gains a "Open full page" affordance.

## Stories (deferred to sprint 13)

9. **13.1 — Pause deliveries (model + form + dashboard banner)**
   New `MealPause(user, reason, starts_on, ends_on, created_at)` model.
   `GET /profile/pause/` form with reason radios (Travelling / Hospital /
   Family / Other) and duration chips (1 week / 2 weeks / Pick date).
   POST creates the row and redirects to dashboard. Dashboard hero shows
   "Paused until 28 Oct · Resume" banner when an active pause exists.
   **NOT integrated with planning** — admin sees the flag and manually
   cancels MealPlans. Planning-integration story is its own follow-up.

## File map (new files, sprint 12)

```
apps/dashboards/services/notifications.py      # 12.6
apps/dashboards/services/profile.py            # 12.4
apps/dashboards/services/weekly_menu.py        # 12.5 (or fold into member_dashboard.py)
apps/dashboards/views/help.py                  # 12.3
apps/dashboards/views/profile.py               # 12.4
apps/dashboards/views/weekly_menu.py           # 12.5
apps/dashboards/views/notifications.py         # 12.6
apps/dashboards/urls/member.py                 # extend with help/profile/menu/notifications
apps/delivery/services/map_snapshot.py         # 12.7
apps/delivery/views/track.py                   # 12.7 (member-facing)
apps/delivery/views/rate.py                    # 12.8

templates/dashboards/landing.html              # 12.2 (rewrite)
templates/dashboards/help.html                 # 12.3
templates/dashboards/profile.html              # 12.4
templates/dashboards/weekly_menu.html          # 12.5
templates/dashboards/notifications.html        # 12.6
templates/delivery/member/track.html           # 12.7
templates/delivery/member/rate.html            # 12.8

templates/_partials/nav_icon.html              # add menu/profile/help icons

apps/dashboards/tests/test_help.py             # 12.3
apps/dashboards/tests/test_profile.py          # 12.4
apps/dashboards/tests/test_weekly_menu.py      # 12.5
apps/dashboards/tests/test_notifications.py    # 12.6 (extend)
apps/delivery/tests/test_map_snapshot.py       # 12.7
apps/delivery/tests/test_member_track.py       # 12.7
apps/delivery/tests/test_rate_meal_page.py     # 12.8
```

## Tests strategy

Per story: pytest + Django test client. Each view test checks:
auth required, page renders 200, key copy appears, dead `href="#"`
absent from rendered HTML. Service tests cover edge cases (no delivery
today, no allergies, multiple pauses, etc.). Mapbox URL builder
covered by a pure-Python unit test (no network).

## Out of scope (explicit)

- Real live map / GPS streaming
- Push notifications / browser notifications API
- Notification mark-read persistence
- Pause integration with planning service
- Editing profile fields (just read-only for v1; edit form is sprint 14+)
- Chat (uses `mailto:` for v1)
- PWA / offline support (sprint 11 owns that)
