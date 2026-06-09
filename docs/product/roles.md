# Role walkthrough — how each user role uses MerryMeal

> **Audience:** new devs, the supervisor, anyone giving a stakeholder demo.
> A practical map from role to journey, with the URLs and decisions that
> make each flow click. Keep it in sync with `apps/accounts/models/users.py::ROLE_CHOICES`
> and `apps/dashboards/services/navigation.py`.

MerryMeal has **six user roles** plus one organisational association
(`partner`) that isn't a role. Mobile-first; everyone signs in via
`/accounts/login/` (email + password). Sign-up paths differ per role.

| Role | Who they are | How they get in | Lives at |
|---|---|---|---|
| **Member** | A senior receiving meals | Public `/apply/`, admin approves | `/dashboard/` |
| **Caregiver** | Family / support person managing one or more members | Member's intake form links a caregiver email; magic-link sign-in | `/dashboard/` (caregiver variant) |
| **Volunteer** | Drives the meal runs | Admin invites + sets `role=volunteer` | `/volunteer/today/` |
| **Kitchen staff** | Receives stock, runs food-safety checks | Admin invites | `/kitchen/` |
| **Admin** | Charity ops — approves, dispatches, audits | Seeded via `seed_admin`, then admin invites peers | `/admin/home/` |
| **Donor** | Gives money one-off or monthly | No signup needed; `/donate/` works anonymously. Magic-link `/donate/manage/` for recurring donors | `/donate/` |

A 7th association — **partner** — isn't a role; it's an org (community
centre, hospital ward) that *refers* members via `/partners/<slug>/`.
Their referral becomes an application like any other and the resulting
member carries the `partner` FK so partner-outcomes reports can roll up.

---

## 1. Member — the recipient

**Core promise:** "What's my meal today? When's it coming? Who do I call?"

### Daily journey

1. **Apply once** at `/apply/` — name, address, dietary needs,
   caregiver email (optional). Status = `pending`.
2. Admin approves → member gets an email with a **password-setup magic
   link** (signed token, single-use, SHA-256 hashed in DB).
3. Member signs in → lands on `/dashboard/`. Sees:
   - **Today's meal card** (name, photo, expected delivery window)
   - **This week's menu** at `/menu/`
   - **Track delivery** at `/track/` — live status (assigned →
     en-route → delivered/failed)
   - **2-tap feedback** after each delivery (👍 / 👎) — drives the
     partner-outcomes report
4. **Help** at `/help/` — phone, FAQ, "I missed a delivery" guidance.
5. **Profile** at `/profile/` — update address, dietary preferences
   (`/profile/dietary/`), sign out.

### What members CAN'T do

- Pause / change deliveries themselves (must call the office)
- Edit other members
- See pricing / donations (members never see money)

### Nav

Home · Menu · Profile · Help

---

## 2. Caregiver — proxy for a member

**Core promise:** "Is Mum's meal on the way? Did she get it?"

### Daily journey

1. Receives an SMS/email when admin approves a member who listed them
   as caregiver.
2. Signs in → `/dashboard/` shows a **list of linked members**.
3. Click a member → `/dashboard/member/<pk>/` (read-only mirror of
   that member's today card + track-delivery page).
4. Gets a **failure alert** if a delivery was marked "couldn't deliver"
   and no other caregiver/office picked it up within the SLA
   (Story 4.13).
5. Can `/donate/` directly — caregivers are often donors too.

### What caregivers CAN'T do

- Edit a member's dietary needs (member or admin only)
- Reassign deliveries
- See other unrelated members

### Nav

Members · Donate

---

## 3. Volunteer — delivery driver

**Core promise:** "What's my run today? Mark each stop done. Flag what
couldn't be delivered."

### Daily journey

1. **Sets availability** at `/volunteer/availability/` (7 days × 3
   slots — Mon-Sun morning/midday/evening). Admin's dispatcher only
   assigns volunteers whose slots overlap with the kitchen's run
   window.
2. Morning of: opens `/volunteer/today/` → ordered list of stops,
   member name + address + a "Mark delivered" button per row.
3. **Mark delivered:** take a POD photo (HEIC auto-converts to JPEG
   on iPhone via `pyheif`) → status flips to `delivered` →
   caregiver-alert is dismissed.
4. **Couldn't deliver:** bottom sheet → pick a reason (no answer,
   address wrong, member declined) → status `failed` → triggers the
   caregiver alert + admin attention card.
5. After the run: log out. The next route appears tomorrow.

### What volunteers CAN'T do

- See deliveries that aren't theirs
- Reassign their own route (admin only)
- Change member contact info

### Nav

Today · When

---

## 4. Kitchen staff — receiving + food safety

**Core promise:** "Log every delivery in, check the fridge temps,
fail-fast if something's off."

### Daily journey

1. **Receive stock** at `/kitchen/` — scan or type ingredient +
   quantity + expiry → creates a stock movement, drives the
   **expiring stock** attention card on the admin home.
2. **Food-safety checks** at `/kitchen/safety/` — three types: fridge
   temp, freezer temp, hand-wash log. Temp checks auto-derive
   pass/fail from thresholds
   (`apps/food_safety/services/checks.py::record_check`). A fail
   surfaces on the admin attention card.
3. Audit-logged via `django-auditlog`; corrections happen via a
   **new** check that supersedes the previous one — there's no edit /
   delete UI by design (compliance artefact).

### What kitchen staff CAN'T do

- See deliveries, members, donations
- Access the admin home
- Edit historical food-safety records

### Nav

Receive · Safety

---

## 5. Admin — runs the charity

**Core promise:** "What needs attention right now? Approve, dispatch,
audit."

### Daily journey

1. Lands on **`/admin/home/`** — the attention cards (pending
   applications, failed deliveries, unassigned routes, expiring stock,
   food-safety fails). Refreshes every 5 minutes via HTMX.
2. **Approvals:** `/admin/applications/` → click a pending → review
   → approve / reject. Approval issues the member's setup token + sends
   the welcome email.
3. **Today's deliveries:** `/admin/today/` → reassign any stop to a
   different volunteer via the Reassign modal.
4. **Kitchens dashboard:** `/admin/kitchens/` → one card per kitchen
   with stock level, today's meal plan, recent safety checks.
5. **Settings:** `/admin/settings/` (`site_config`) → charity name,
   ABN, address, office phone — every email + receipt + footer reads
   from here, so no hardcoded brand.
6. **Audit viewer:** `/admin/audit/` → every state change with actor,
   timestamp, before/after diff.
7. **Donor history + campaigns:** `/admin/donors/`, `/admin/campaigns/`
   → see who gave what, FY receipts.
8. **Profile:** `/admin/profile/` — sign out, change password.

### What admins CAN do (that nobody else can)

- Approve / reject applications
- Reassign deliveries
- Create / edit campaigns
- Issue partner referral codes
- Edit site config (charity branding)
- View the audit log

### Nav

Home · Applications · Kitchens · Today · Audit · Settings · Profile

---

## 6. Donor — gives money

**Core promise:** "Give once or monthly, get a receipt, optionally
manage my recurring gift."

### Journey (no signup required)

1. Visit `/donate/` → pick an amount, fill name + email + (optional)
   tick "make this monthly".
2. Redirected to **Stripe Checkout** (live HTTPS in prod, or via
   `stripe listen` / ngrok in dev).
3. Pay → land on `/donate/thanks/` → status flips to `succeeded` when
   Stripe webhook fires.
4. Receipt PDF (WeasyPrint, charity ABN + address from `site_config`)
   emailed automatically.
5. **Recurring donors only:** request a magic-link at `/donate/manage/`
   → email arrives → click → `/donate/manage/<token>/` → cancel or
   change card.
6. Annual FY tax receipt rolls up all gifts in the year
   (`/donate/fy-receipt/`).

### What donors CAN'T do

- See other people's donations
- Edit a one-off gift (it's done)
- Refund themselves (must call the office)

### Nav (only if they sign in as a donor)

My donations · Donate

---

## How the roles connect

```
                    Partner refers
        Caregiver ←——————————————→ Member ←——→ Admin
            ↑                       ↑           ↓ approves, dispatches
            └————— alerted on ——————┤           ↓
                  failed delivery   │      Kitchen staff
                                    │      ↓ stocks, safety-checks
                                  Volunteer
                                  delivers
                                                ↑
                               Donor ——————— funds —┘
```

- **Admin** is the only role that can *write* across other apps
  (approve members, edit kitchens, reassign routes, edit site config).
- **Member + Caregiver + Volunteer + Kitchen staff** each see ONLY
  their own slice.
- **Donor** is the lightest role — it doesn't even require a `User`
  row for a one-off gift; the `Donation` is keyed by `donor_email`.
- **Audit log** records every admin write so the board can see who
  did what.

---

## Local demo recipe

```bash
DJANGO_ADMIN_PASSWORD=admin1234 python manage.py seed_all
scripts/stripe_dev.sh dev
```

Then in three browser tabs:

| Tab | URL | Login |
|---|---|---|
| Admin | `http://localhost:8000/admin/home/` | `admin@merrymeal.local` / `admin1234` |
| Member | `http://localhost:8000/dashboard/` | one of the seeded `member-*@test.merrymeal.local` users |
| Volunteer | `http://localhost:8000/volunteer/today/` | one of the seeded `volunteer-*@test.merrymeal.local` users |

Generate today's deliveries first (the seeders create members +
volunteers but not the daily `Delivery` rows):

```bash
python manage.py shell -c "from apps.delivery.services.dispatch import generate_deliveries_for_date; from django.utils import timezone; print(generate_deliveries_for_date(timezone.localdate()))"
```

For donations, see `scripts/stripe_dev.sh` — `dev` starts the webhook
forwarder alongside `runserver`, `card` prints the test card numbers,
`trigger success|renew|cancel` fires fake events.

---

## Where to look in code

| Concern | File |
|---|---|
| Role choices | `apps/accounts/models/users.py::ROLE_CHOICES` |
| Per-role nav | `apps/dashboards/services/navigation.py::NAV_ITEMS_BY_ROLE` |
| Role gate decorator | `apps/core/decorators.py::role_required` |
| Member dashboard | `apps/dashboards/views/member_dashboard.py` |
| Caregiver dashboard | `apps/dashboards/views/caregiver_dashboard.py` |
| Volunteer today | `apps/delivery/views/volunteer_today.py` |
| Kitchen receive | `apps/kitchens/views/stock.py` |
| Admin home | `apps/dashboards/views/admin_home.py` |
| Donate page | `apps/donations/views/donate.py` |
| Stripe webhook | `apps/donations/views/checkout.py` |
