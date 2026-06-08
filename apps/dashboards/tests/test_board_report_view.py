"""Story 6.5 — board report view (auth, formats, fallback)."""
from __future__ import annotations

import datetime as dt

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.dashboards.services import board_report_pdf


@pytest.fixture
def admin_user(db):
    return UserFactory(email="admin@mm.com", role="admin")


def _url(**params) -> str:
    """Build the report URL via ``reverse`` so an upstream URL move
    doesn't silently break the test."""
    base = reverse("dashboards:board_report")
    if not params:
        return base
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{base}?{qs}"


@pytest.mark.django_db
class TestAccess:
    def test_anonymous_is_redirected_to_login(self, client):
        response = client.get(_url(year=2026, month=6))
        # ``role_required`` redirects anonymous users (302) and 403s
        # logged-in non-admins. Either is acceptable here.
        assert response.status_code in (302, 403)

    def test_non_admin_is_forbidden(self, client, db):
        member = UserFactory(email="member@mm.com", role="member")
        client.force_login(member)
        response = client.get(_url(year=2026, month=6))
        assert response.status_code == 403


@pytest.mark.django_db
class TestHtmlDefault:
    def test_admin_gets_html_by_default(self, client, admin_user):
        client.force_login(admin_user)
        response = client.get(_url(year=2026, month=6))
        assert response.status_code == 200
        assert response["Content-Type"].startswith("text/html")
        body = response.content
        # Letterhead and period label both rendered.
        assert b"MerryMeal" in body
        assert b"June 2026" in body
        # Headline metric labels.
        assert b"Donations" in body
        assert b"Deliveries" in body
        assert b"Membership" in body

    def test_default_month_is_current_month(self, client, admin_user):
        client.force_login(admin_user)
        response = client.get(_url())  # no year/month
        assert response.status_code == 200
        today = timezone.localdate()
        expected = dt.date(today.year, today.month, 1).strftime("%B %Y")
        assert expected.encode() in response.content


@pytest.mark.django_db
class TestCsv:
    def test_csv_format_attaches_with_correct_filename(self, client, admin_user):
        client.force_login(admin_user)
        response = client.get(_url(year=2026, month=6, format="csv"))
        assert response.status_code == 200
        assert response["Content-Type"].startswith("text/csv")
        cd = response["Content-Disposition"]
        assert "attachment" in cd
        assert "board-report-2026-06.csv" in cd
        # BOM byte sequence at the start of the body.
        assert response.content.startswith(b"\xef\xbb\xbf")


@pytest.mark.django_db
class TestPdfFallback:
    def test_pdf_falls_back_to_html_when_weasyprint_unavailable(
        self, client, admin_user, monkeypatch
    ):
        # Force the unavailable branch even on machines where the
        # native libs happen to be installed.
        monkeypatch.setattr(board_report_pdf, "WEASYPRINT_AVAILABLE", False)
        monkeypatch.setattr(board_report_pdf, "_weasyprint", None)
        client.force_login(admin_user)
        response = client.get(_url(year=2026, month=6, format="pdf"))
        assert response.status_code == 200
        # HTML, not PDF — the fallback path.
        assert response["Content-Type"].startswith("text/html")
        # Banner present so the admin knows why they got HTML back.
        assert b"PDF rendering is unavailable" in response.content

    def test_pdf_returns_application_pdf_when_engine_works(
        self, client, admin_user, monkeypatch
    ):
        # Pretend WeasyPrint is available and have it return canned bytes.
        class _StubHTML:
            def __init__(self, *a, **kw):
                pass

            def write_pdf(self):
                return b"%PDF-1.4 stub"

        class _StubModule:
            HTML = _StubHTML

        monkeypatch.setattr(board_report_pdf, "WEASYPRINT_AVAILABLE", True)
        monkeypatch.setattr(board_report_pdf, "_weasyprint", _StubModule)
        client.force_login(admin_user)
        response = client.get(_url(year=2026, month=6, format="pdf"))
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert response.content.startswith(b"%PDF-")
        cd = response["Content-Disposition"]
        assert "board-report-2026-06.pdf" in cd


@pytest.mark.django_db
class TestValidation:
    def test_bad_month_returns_400(self, client, admin_user):
        client.force_login(admin_user)
        assert client.get(_url(year=2026, month=13)).status_code == 400
        assert client.get(_url(year=2026, month=0)).status_code == 400

    def test_bad_year_returns_400(self, client, admin_user):
        client.force_login(admin_user)
        assert client.get(_url(year=1900, month=6)).status_code == 400

    def test_non_integer_month_returns_400(self, client, admin_user):
        client.force_login(admin_user)
        assert client.get(_url(year=2026, month="June")).status_code == 400

    def test_unknown_format_returns_400(self, client, admin_user):
        client.force_login(admin_user)
        assert client.get(_url(year=2026, month=6, format="xml")).status_code == 400
