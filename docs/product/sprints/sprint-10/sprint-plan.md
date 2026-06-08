# Sprint 10 — Dashboards, reports, audit viewer

**Weeks:** 19–20
**Primary epic:** [06 — Dashboards & reporting](../../epics/06-dashboards.md)
**Sprint goal:** every role has one home screen that surfaces what matters; admin can pull a board-quality monthly report in one click; the audit log is searchable.

---

## Stories pulled

| ID | Title | Track | Status | Detail |
|---|---|---|---|---|
| 6.1 | Admin home: "what needs attention now" | FE + BE pair | planned (sprint-10) | [stories/6.1-admin-home-attention.md](stories/6.1-admin-home-attention.md) |
| 6.2 | Partner outcomes view | FE + BE pair | planned (sprint-10) | [stories/6.2-partner-outcomes.md](stories/6.2-partner-outcomes.md) |
| 6.3 | Donor history page | FE + BE pair | planned (sprint-10) | [stories/6.3-donor-history.md](stories/6.3-donor-history.md) |
| 6.4 | Tax receipt printer-friendly page | FE + BE pair | planned (sprint-10) | [stories/6.4-tax-receipt.md](stories/6.4-tax-receipt.md) |
| 6.5 | Board report: CSV + PDF | Backend / Ops | planned (sprint-10) | [stories/6.5-board-report.md](stories/6.5-board-report.md) |
| 6.6 | Audit log viewer | FE + BE pair | planned (sprint-10) | [stories/6.6-audit-viewer.md](stories/6.6-audit-viewer.md) |
| 6.7 | Partner referral form (public) | FE + BE pair | planned (sprint-10) | [stories/6.7-partner-referral-form.md](stories/6.7-partner-referral-form.md) |

> **For executors:** each story file is a self-contained TDD plan with file paths, code, commands, and expected output. Pattern follows [Sprint 01's stories](../sprint-01/stories/). **Sprint backlog & spillover protocol:** see [backlog.md](backlog.md).

---

## Parallel tracks

### Backend track — Dev A
1. Aggregation services for each dashboard: admin_summary, partner_outcomes, donor_history, campaign_progress (~3 days total).
2. **6.5** board-report PDF generation: pick `weasyprint` (preferred) or `xhtml2pdf`. Build the data-collection + rendering pipeline (~2 days).

### Frontend track — Dev B
1. **6.1** admin home cards (~2 days).
2. **6.2** partner outcomes table + CSV export button (~1 day).
3. **6.3** + **6.4** donor pages (~1½ days).
4. **6.6** audit viewer UI (~1 day).

### Admin / ops + content — Dev C
1. **6.7** partner referral form (public, mostly mirrors Story 1.10) (~1½ days).
2. Final polish: navigation between dashboards, consistent breadcrumbs, terminology audit ("Donor" vs "Supporter", etc.).

---

## Day-by-day suggestion

| Day | Backend | Frontend | Admin/Ops |
|---|---|---|---|
| Mon w1 | Sprint planning. Sketch admin_summary service. | Sprint planning. Build 6.1 card scaffold. | Sprint planning. Wireframe 6.7. |
| Tue w1 | admin_summary + tests. | 6.1 cards consume real data. | 6.7 form + view. |
| Wed w1 | partner_outcomes service. | 6.2 table + CSV export. | 6.7 in review. |
| Thu w1 | donor_history service. | 6.3 + 6.4. | Polish: nav, breadcrumbs. |
| Fri w1 | 6.5 PDF spike: render hello-world weasyprint inside Docker. | 6.4 print CSS. | Mid-sprint demo. |
| Mon w2 | 6.5 data collection (each metric for a month). | 6.6 audit viewer template. | Help Dev A with weasyprint quirks. |
| Tue w2 | 6.5 PDF template. | 6.6 filters + diff panel. | Same. |
| Wed w2 | 6.5 in review (rate-limit + audit-log entry). | 6.6 in review. | Same. |
| Thu w2 | Bug-bash. Verify partner permission isolation (Story 6.2). | Bug-bash + accessibility check on all new screens. | Same. |
| Fri w2 | **Sprint demo + retro.** | Same. | Same. |

---

## Demo agenda (Fri w2)

1. **Admin (laptop)** — open `/admin/home/`. Three cards: 2 pending apps, 1 expiring batch, 0 failed deliveries.
2. Click "Generate this month's board report" → PDF downloads.
3. **Partner (laptop)** — log in as a `partner` user for "Northcote Community Centre". See `/partner/outcomes/` with 8 members, 75 % retention, average rating 4.2. Export CSV.
4. **Public partner referrer** — open `/partners/refer/` (no login). Submit a referral. Admin sees it appear in the queue tagged with the partner.
5. **Donor (phone)** — open `/donor/history/`. See 3 donations totalling $130. Tap "Tax receipt FY 2026" → printable page renders.
6. **Admin (laptop)** — open `/admin/audit/`. Filter by `margaret@example.com`. See every change on her row with the before/after diff.

## Definition of Done for the sprint

- All 7 stories `STATUS: done (sprint-10)`.
- Permission isolation in Story 6.2 has a dedicated unit test (cross-partner attempt → empty).
- Board report PDF renders correctly in Docker (CI test).
- Audit viewer is read-only — no UI path to mutate.

## Risks

| Risk | Mitigation |
|---|---|
| `weasyprint` dependency on system libraries inside Alpine. | Use Debian-slim base in `Dockerfile`; pre-install `libpango`, `libcairo2`. |
| Board-report numbers disagree with admin's manual spreadsheet. | Spend the bug-bash day cross-checking against the charity's last manual board pack. |
| Audit log has too many entries for a fast search. | Stick to indexed search (object_id + actor email). Performance hardening lands in Epic 07. |

---

## What's next (after Sprint 10)

The "v1 core" is shipped. The next sprints pull from:

1. **Epic 07 — Hardening** (PWA / encryption / WCAG / perf budget) — recommended Sprint 11.
2. **Backlog stories** that emerged during Sprints 01–10. Refer to each
   epic's "Backlog" section.

Sprint planning for Sprint 11 should begin with a **retrospective on the whole roadmap**: which estimates were wrong, which acceptance criteria were unclear, which stories were too big.
