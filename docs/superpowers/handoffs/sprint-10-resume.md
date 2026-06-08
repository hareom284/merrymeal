# Sprint 10 — Resume notes for the next AI session

**Last updated:** 2026-06-09 (sprint-10 COMPLETE — all 7 stories shipped)
**Branch state:** Sprint 10 fully done. All 7 stories committed on
`worktree-implement-sprint-10` and merged into `implement-sprint-02`.
Sprint 9 (donations) was a prerequisite for 6.3/6.4/6.5 and landed
mid-sprint via a parallel session.

## What shipped

| Story | Commit | Tests |
|---|---|---|
| 6.1 — Admin home attention cards | `88e70d0` | 16 |
| 6.6 — Audit log viewer (read-only) | `af38796` | 13 |
| 6.2 — Partner outcomes + CSV export | `0c28714` | 13 |
| 6.7 — Public partner referral form | `ba1563d` | 12 |
| (first partial merge into integration branch) | `9ae36cb` | — |
| 6.3 — Donor history page | `c51d8f8` | 12 |
| 6.4 — FY tax receipt (printer-friendly) | `c3eb553` | 22 |
| 6.5 — Board report CSV + PDF | `c8a22f4` | 28 (+1 weasyprint skip) |

Full suite at sprint close: **687 passed, 3 skipped** (2 pre-existing +
1 `pytest.importorskip("weasyprint")`).

## What you'll find that's worth knowing

### New decorator (added during 6.2)

`apps.core.decorators.partner_required` — gates on
`request.user.partner_id is not None`. Reach for it instead of
`role_required("partner")` (no such role).

### Schema additions

- `apps/accounts/migrations/0006_application_metadata_application_partner.py`
  — added `Application.partner` FK (nullable, PROTECT,
  `related_name="referred_applications"`) and `Application.metadata`
  JSONField. The partner referral form (6.7) writes to both;
  `_create_member_user` in `apps/accounts/services/applications.py`
  copies `partner` onto the new User on approval.

### Read-only admin pattern (audit viewer)

`apps/dashboards/admin.py::ReadOnlyLogEntryAdmin` subclasses
`admin.ModelAdmin` directly (NOT `auditlog.admin.LogEntryAdmin` — its
permission methods call `request.resolver_match` and crash when
`request=None`). Copy this pattern for any other read-only admin.

### FY helper for AU tax periods (added during 6.4)

`apps.dashboards.services.fy::fy_period(fy)` returns `(start_date, end_date)`
for the named Australian financial year (1 Jul → 30 Jun, named for the
closing calendar year). Boundary handling is timezone-aware — a donation
at 23:59:59 Melbourne on 30 June belongs to that FY even though it's
stored as UTC.

### Board report — production prereq

`apps/dashboards/services/board_report_pdf.py` imports `weasyprint`
behind a `try/except` and exposes `WEASYPRINT_AVAILABLE`. The view
returns the HTML page with a "PDF unavailable — File → Print → Save as
PDF" banner when the import or engine fails. The production Docker image
installs `libpango`, `libcairo2`, etc. — confirm before relying on the
PDF-format endpoint in prod.

### Settings additions (6.4)

`config/settings/base.py` reads two new env vars: `MERRYMEAL_ABN` and
`MERRYMEAL_ADDRESS` (both default to the existing `DONATIONS_CHARITY_*`
values so the page works without env changes). Update both to real
values once the accountant supplies the registered ABN.

### Parallel-agent file collisions observed

This sprint dispatched 6 agents across 2 rounds with very few clashes:
- `apps/dashboards/urls/admin.py` — 6.1, 6.6, 6.5 all added routes here.
  Each appended cleanly.
- `apps/dashboards/urls/__init__.py` — 6.2, 6.3 added new includes.
  Merged cleanly because each added its own line.
- `apps/dashboards/views/donor_history.py` + `apps/dashboards/urls/donor.py`
  — story 6.3 created these; story 6.4 EXTENDED them with the
  `fy_receipt` view and route. Worked because 6.4 ran after 6.3 finished.
  6.3's commit message flags this as a paired delivery.

### Mid-sprint agent crash recovery

Agent for 6.4 died with a socket error after writing the service +
tests + view but BEFORE the template. The orchestrator (this session)
read the view's render context, wrote the template by hand, and the
22 existing tests passed first try. Pattern is recorded so future
sessions know: when a subagent dies mid-implementation, check
`git status -s` and `pytest -q --tb=line` of the orphaned tests —
the missing piece is usually small.

### Worktree state on disk

The git worktree at `.claude/worktrees/implement-sprint-10` was created
via `EnterWorktree` (native tool — preferred). It can be removed once
the merge sticks:

```bash
git worktree remove .claude/worktrees/implement-sprint-10
git branch -d worktree-implement-sprint-10
```

## Sprint 11 (next) — what to load first

Epic 07 — Hardening: PWA shell, encryption-at-rest review, WCAG 2.2 AA
audit, performance budget. There's no sprint-11 doc folder yet. The
next AI session should propose one with the user before implementing —
sprint 11 is the v1 release polish phase, so the user may want a
roadmap retro first.

## Useful commands for the next session

```bash
# Confirm sprint 10 is fully merged
git log --oneline | grep -E "\[6\.[1-7]\]" | head -7

# Run dashboards suite (story-scoped is much faster than full sweep)
DJANGO_SETTINGS_MODULE=config.settings.test python3 -m pytest apps/dashboards -q

# Quick "what's the current state" check
DJANGO_SETTINGS_MODULE=config.settings.test python3 -m pytest -q | tail -3
ruff check apps templates
python3 scripts/check_env_example.py
```
