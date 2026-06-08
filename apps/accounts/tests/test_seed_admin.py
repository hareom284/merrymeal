import pytest
from django.core.management import call_command

from apps.accounts.models import User

ADMIN_EMAIL = "admin@merrymeal.freebarcodeqr.com"


@pytest.mark.django_db
def test_seed_admin_creates_superuser_when_missing(monkeypatch):
    monkeypatch.setenv("DJANGO_ADMIN_PASSWORD", "first-pass-1234")
    assert User.all_objects.filter(email=ADMIN_EMAIL).count() == 0

    call_command("seed_admin")

    user = User.objects.get(email=ADMIN_EMAIL)
    assert user.role == "admin"
    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.is_active is True
    assert user.full_name == "Site Admin"
    assert user.check_password("first-pass-1234")


@pytest.mark.django_db
def test_seed_admin_is_idempotent(monkeypatch):
    monkeypatch.setenv("DJANGO_ADMIN_PASSWORD", "stable-pass-1234")
    call_command("seed_admin")
    call_command("seed_admin")
    assert User.all_objects.filter(email=ADMIN_EMAIL).count() == 1


@pytest.mark.django_db
def test_seed_admin_rotates_password_when_env_changes(monkeypatch):
    monkeypatch.setenv("DJANGO_ADMIN_PASSWORD", "old-pass-1234")
    call_command("seed_admin")

    monkeypatch.setenv("DJANGO_ADMIN_PASSWORD", "new-pass-5678")
    call_command("seed_admin")

    user = User.objects.get(email=ADMIN_EMAIL)
    assert user.check_password("new-pass-5678")
    assert not user.check_password("old-pass-1234")


@pytest.mark.django_db
def test_seed_admin_preserves_password_when_env_unset(monkeypatch):
    monkeypatch.setenv("DJANGO_ADMIN_PASSWORD", "kept-pass-1234")
    call_command("seed_admin")

    monkeypatch.delenv("DJANGO_ADMIN_PASSWORD", raising=False)
    call_command("seed_admin")

    user = User.objects.get(email=ADMIN_EMAIL)
    assert user.check_password("kept-pass-1234")


@pytest.mark.django_db
def test_seed_admin_revives_soft_deleted_admin(monkeypatch):
    monkeypatch.setenv("DJANGO_ADMIN_PASSWORD", "revive-pass-1234")
    call_command("seed_admin")

    user = User.objects.get(email=ADMIN_EMAIL)
    from django.utils import timezone

    user.deleted_at = timezone.now()
    user.is_active = False
    user.save()
    assert User.objects.filter(email=ADMIN_EMAIL).count() == 0

    call_command("seed_admin")

    user.refresh_from_db()
    assert user.deleted_at is None
    assert user.is_active is True


@pytest.mark.django_db
def test_seed_admin_honours_email_override(monkeypatch):
    monkeypatch.setenv("DJANGO_ADMIN_EMAIL", "other-admin@example.org")
    monkeypatch.setenv("DJANGO_ADMIN_PASSWORD", "override-pass-1234")

    call_command("seed_admin")

    assert User.objects.filter(email="other-admin@example.org").exists()
