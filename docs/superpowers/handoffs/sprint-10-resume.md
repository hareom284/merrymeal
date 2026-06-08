# Sprint 10 — Resume notes for the next AI session

**Last updated:** 2026-06-09 (sprint-10 partial merge → `implement-sprint-02`)
**Branch state:** sprint-10 stories 6.1, 6.2, 6.6, 6.7 merged into
`implement-sprint-02` at commit `9ae36cb`. Stories 6.3, 6.4, 6.5 are
deferred — they require Sprint 9 (donations app) which is being worked
on in parallel and not yet on main.

## What's done on this branch

| Story | Commit | Tests |
|---|---|---|
| 6.1 — Admin home attention cards | `88e70d0` | 16 |
| 6.6 — Audit log viewer (read-only) | `af38796` | 13 |
| 6.2 — Partner outcomes + CSV export | `0c28714` | 13 |
| 6.7 — Public partner referral form | `ba1563d` | 12 |
| epic-06 status updates | `1a5eda6` | — |
| merge into integration branch | `9ae36cb` | — |

Full suite: **509 passed, 2 pre-existing skips** as of merge.

## What's blocked (and on what)

- **6.3 Donor history** — needs `apps.donations.Donation` model.
- **6.4 Tax receipt** — reuses 6.3's service.
- **6.5 Board report PDF** — needs donation totals + `weasyprint` system
  deps in the Docker image. Non-donation metrics could be stubbed, but the
  spec's primary value is the financial export, so wait for sprint 9.

All three depend on Sprint 9 (Epic 05 — donations). Once sprint 9 merges
to `main`:

```bash
git checkout implement-sprint-02
git merge main          # pull sprint 9 in
# Then dispatch 3 parallel agents for 6.3, 6.4, 6.5
# (6.4 depends on 6.3's service — do 6.3 first, then 6.4 + 6.5 parallel)
```

## How to resume — recipe

1. `cd /Users/hareom284/Documents/Harry/merrymeal && git checkout implement-sprint-02 && git pull`
2. Confirm sprint 9 is in main: `git log --oneline | grep -E "donat|stripe|5\.[1-8]" | head -5`. If empty, sprint 9 isn't ready; do something else.
3. Read each remaining story spec: `docs/product/sprints/sprint-10/stories/6.{3,4,5}-*.md`.
4. Follow the substitution catalog in `CLAUDE.md` while implementing — story specs use the spec-side names (`apps.deliveries`, `UserAddress`, `MemberFactory`, etc.); the real names are different.
5. Per-story commit with `[6.X]` tag, then update `STATUS: done (sprint-10)` in `docs/product/epics/06-dashboards.md` for each.
6. When all 7 done, update this handoff doc and bump sprint 11 status in `CLAUDE.md`.

## What you'll find that's worth knowing

### New decorator (added during 6.2)

`apps.core.decorators.partner_required` — gates on `request.user.partner_id is not None`. Reach for it instead of `role_required("partner")` (no such role).

### Schema additions (worth flagging if you touch related code)

- `apps/accounts/migrations/0006_application_metadata_application_partner.py`
  added `Application.partner` FK (nullable, PROTECT, related_name="referred_applications") and `Application.metadata` JSONField. Partner referral form (6.7) writes to both; `_create_member_user` in `apps/accounts/services/applications.py` copies `partner` onto the new User on approval.

### Read-only admin pattern (audit viewer)

`apps/dashboards/admin.py::ReadOnlyLogEntryAdmin` subclasses `admin.ModelAdmin` directly (NOT `auditlog.admin.LogEntryAdmin` — its permission methods call `request.resolver_match` and crash when `request=None`). If you need another read-only admin, copy this pattern.

### Parallel-agent file collisions seen this sprint

The only file 4 agents tried to touch concurrently was `apps/dashboards/urls/admin.py` (both 6.1 and 6.6 add routes). Merge was clean because each appended its own block. For future sprints: if you dispatch more than 2 agents that all add admin routes, have one agent own the file and the others tell that agent what URL patterns to add.

### Worktree state on disk

A git worktree was created at `.claude/worktrees/implement-sprint-10` on branch `worktree-implement-sprint-10`. Sprint 10's commits were made there and merged via `git merge --no-ff worktree-implement-sprint-10`. The worktree can be removed once you confirm the merge sticks:

```bash
git worktree remove .claude/worktrees/implement-sprint-10
git branch -d worktree-implement-sprint-10
```

## Sprint 11 (next) — what to load first

Epic 07 — Hardening: PWA shell, encryption-at-rest review, WCAG 2.2 AA audit, performance budget. There's no sprint-11 doc folder yet; the next AI session should propose one with the user before implementing.
