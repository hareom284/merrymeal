import pytest
from django.contrib import admin as django_admin

from apps.accounts.tests.factories import UserFactory
from apps.partners.models import Partner
from apps.partners.tests.factories import PartnerFactory


@pytest.mark.django_db
def test_partner_can_be_created():
    p = Partner.objects.create(legal_name="Helping Hands Charity", type="charity")
    assert p.pk is not None
    assert p.legal_name == "Helping Hands Charity"
    assert p.type == "charity"
    assert p.created_at is not None
    assert p.updated_at is not None


@pytest.mark.django_db
def test_partner_db_table_is_partners():
    assert Partner._meta.db_table == "partners"


@pytest.mark.django_db
def test_partner_type_choices_match_schema():
    field = Partner._meta.get_field("type")
    values = {c[0] for c in field.choices}
    assert values == {"charity", "restaurant", "supplier", "corporate"}


@pytest.mark.django_db
def test_partner_str_returns_legal_name():
    p = PartnerFactory(legal_name="ACME Corp", type="corporate")
    assert str(p) == "ACME Corp"


def test_partner_is_registered_in_django_admin():
    assert Partner in django_admin.site._registry
    p_admin = django_admin.site._registry[Partner]
    assert "legal_name" in p_admin.list_display
    assert "type" in p_admin.list_display
    assert "type" in p_admin.list_filter
    assert "legal_name" in p_admin.search_fields


@pytest.mark.django_db
def test_user_partner_is_a_real_foreignkey():
    from django.db import models as djmodels

    from apps.accounts.models import User

    field = User._meta.get_field("partner")
    assert isinstance(field, djmodels.ForeignKey)
    assert field.related_model is Partner
    assert field.null is True
    assert field.db_column == "partner_id"


@pytest.mark.django_db
def test_user_can_be_attached_to_a_partner():
    partner = PartnerFactory(legal_name="St. John Ambulance", type="charity")
    user = UserFactory(partner=partner)
    user.refresh_from_db()
    assert user.partner_id == partner.pk
    assert user.partner.legal_name == "St. John Ambulance"


@pytest.mark.django_db
def test_many_users_can_share_one_partner():
    partner = PartnerFactory()
    UserFactory(email="a@example.com", partner=partner)
    UserFactory(email="b@example.com", partner=partner)
    assert partner.users.count() == 2


@pytest.mark.django_db
def test_deleting_partner_with_users_is_protected():
    partner = PartnerFactory()
    UserFactory(partner=partner)
    from django.db.models.deletion import ProtectedError
    with pytest.raises(ProtectedError):
        partner.delete()


@pytest.mark.django_db
def test_user_without_partner_is_allowed():
    user = UserFactory()
    assert user.partner_id is None
