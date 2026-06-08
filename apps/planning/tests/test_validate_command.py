import datetime as dt
from io import StringIO

import pytest
from django.core.management import call_command

from apps.accounts.tests.factories import UserAddressFactory, UserFactory
from apps.kitchens.tests.factories import KitchenFactory
from apps.meals.tests.factories import MealFactory
from apps.planning.tests.factories import MealPlanFactory


@pytest.fixture
def freezer(monkeypatch):
    """Lightweight date-pinning fixture.

    The project declares pytest-freezer in requirements.txt but a local
    Homebrew Python 3.12 install may not have it pulled in yet (PEP-668
    makes ad-hoc installs awkward). This fixture mimics the small slice
    of the freezegun / pytest-freezer API the validate_radius_assignments
    tests need — namely `freezer.move_to("YYYY-MM-DD")` patching the
    things `validate_radius_assignments` consults to read "today":
    `django.utils.timezone.localdate` (Melbourne local date).
    """

    class _Freezer:
        def move_to(self, iso: str) -> None:
            target = dt.date.fromisoformat(iso)
            import django.utils.timezone as tz

            monkeypatch.setattr(tz, "localdate", lambda: target)

    return _Freezer()


@pytest.mark.django_db
class TestValidateRadiusCommand:
    def test_exit_zero_when_all_consistent(self, freezer):
        freezer.move_to("2026-06-03")  # Wednesday — weekday
        kitchen = KitchenFactory(
            latitude=-37.81, longitude=144.96, service_radius_km=10
        )
        member = UserFactory(role="member")
        UserAddressFactory(user=member, latitude=-37.82, longitude=144.97)
        # Plan: kitchen-wide fresh on Wed — matches the rule.
        MealPlanFactory(
            kitchen=kitchen,
            meal=MealFactory(),
            service_date=dt.date(2026, 6, 3),
            meal_type="fresh",
        )
        out = StringIO()
        with pytest.raises(SystemExit) as exc:
            call_command("validate_radius_assignments", stdout=out)
        assert exc.value.code == 0
        assert "OK" in out.getvalue()

    def test_exit_one_when_a_plan_is_wrong(self, freezer):
        freezer.move_to("2026-06-06")  # Saturday — must be frozen
        kitchen = KitchenFactory(latitude=-37.81, longitude=144.96)
        UserAddressFactory(
            user=UserFactory(role="member"),
            latitude=-37.82,
            longitude=144.97,
        )
        # Plan says fresh on Saturday — wrong.
        MealPlanFactory(
            kitchen=kitchen,
            meal=MealFactory(),
            service_date=dt.date(2026, 6, 6),
            meal_type="fresh",
        )
        out = StringIO()
        with pytest.raises(SystemExit) as exc:
            call_command("validate_radius_assignments", stdout=out)
        assert exc.value.code == 1
        assert "expected=frozen" in out.getvalue()

    def test_date_flag_overrides_today(self, freezer):
        freezer.move_to("2026-06-03")
        kitchen = KitchenFactory(latitude=-37.81, longitude=144.96)
        UserAddressFactory(
            user=UserFactory(role="member"),
            latitude=-37.82,
            longitude=144.97,
        )
        MealPlanFactory(
            kitchen=kitchen,
            meal=MealFactory(),
            service_date=dt.date(2026, 6, 7),  # Sunday
            meal_type="fresh",
        )
        out = StringIO()
        with pytest.raises(SystemExit) as exc:
            call_command(
                "validate_radius_assignments", "--date", "2026-06-07", stdout=out
            )
        assert exc.value.code == 1
        assert "expected=frozen" in out.getvalue()

    def test_skips_members_without_addresses(self, freezer):
        freezer.move_to("2026-06-03")
        UserFactory(role="member")  # no address
        out = StringIO()
        with pytest.raises(SystemExit) as exc:
            call_command("validate_radius_assignments", stdout=out)
        # No plans, no inconsistencies, but the skipped count must show.
        assert exc.value.code == 0
        assert "skipped" in out.getvalue().lower()

    def test_quiet_suppresses_per_member_output(self, freezer):
        freezer.move_to("2026-06-06")  # Saturday — must be frozen
        kitchen = KitchenFactory(latitude=-37.81, longitude=144.96)
        UserAddressFactory(
            user=UserFactory(role="member"),
            latitude=-37.82,
            longitude=144.97,
        )
        MealPlanFactory(
            kitchen=kitchen,
            meal=MealFactory(),
            service_date=dt.date(2026, 6, 6),
            meal_type="fresh",
        )
        out = StringIO()
        with pytest.raises(SystemExit) as exc:
            call_command("validate_radius_assignments", "--quiet", stdout=out)
        assert exc.value.code == 1
        # Per-member detail line suppressed.
        assert "expected=" not in out.getvalue()
        # Summary still emitted.
        assert "FAIL" in out.getvalue()


@pytest.mark.django_db
def test_task_emails_admin_on_failure(monkeypatch, settings, freezer):
    freezer.move_to("2026-06-06")
    settings.ADMIN_EMAIL = "admin@example.test"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    from django.core import mail

    kitchen = KitchenFactory(latitude=-37.81, longitude=144.96)
    UserAddressFactory(
        user=UserFactory(role="member"), latitude=-37.82, longitude=144.97
    )
    MealPlanFactory(
        kitchen=kitchen,
        meal=MealFactory(),
        service_date=dt.date(2026, 6, 6),
        meal_type="fresh",
    )
    from apps.planning.tasks.validate import run_nightly_validation

    code = run_nightly_validation()
    assert code == 1
    assert any(
        "validate_radius_assignments" in m.subject for m in mail.outbox
    )
