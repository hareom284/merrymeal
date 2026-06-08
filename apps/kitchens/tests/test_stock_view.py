from datetime import date, timedelta

import pytest
from django.urls import reverse

from apps.accounts.services.users import create_user
from apps.kitchens.models import IngredientBatch
from apps.kitchens.tests.factories import IngredientFactory, KitchenFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_user():
    return create_user(
        email="cook@example.com",
        password="testpass123",
        full_name="Cook",
        role="kitchen_staff",
    )


@pytest.fixture
def member_user():
    return create_user(
        email="m@example.com",
        password="testpass123",
        full_name="M",
        role="member",
    )


class TestStockReceiveView:
    def test_anonymous_redirected_to_login(self, client):
        resp = client.get(reverse("kitchens:stock_receive"))
        assert resp.status_code == 302
        assert "/accounts/login/" in resp["Location"]

    def test_member_forbidden(self, client, member_user):
        client.force_login(member_user)
        resp = client.get(reverse("kitchens:stock_receive"))
        assert resp.status_code == 403

    def test_staff_can_get_form(self, client, staff_user):
        client.force_login(staff_user)
        KitchenFactory()
        resp = client.get(reverse("kitchens:stock_receive"))
        assert resp.status_code == 200
        assert b"Receive stock" in resp.content

    def test_post_creates_batch_and_redirects(self, client, staff_user):
        client.force_login(staff_user)
        kitchen = KitchenFactory()
        ing = IngredientFactory()
        resp = client.post(
            reverse("kitchens:stock_receive"),
            data={
                "kitchen": kitchen.pk,
                "ingredient": ing.pk,
                "quantity": "5.00",
                "received_at": str(date.today()),
                "expiration_date": str(date.today() + timedelta(days=7)),
                "lot_number": "LOT-A",
            },
        )
        assert resp.status_code == 302
        assert "created=" in resp["Location"]
        assert IngredientBatch.objects.count() == 1

    def test_success_toast_renders_on_created_query(self, client, staff_user):
        client.force_login(staff_user)
        KitchenFactory()
        resp = client.get(reverse("kitchens:stock_receive") + "?created=1")
        assert resp.status_code == 200
        assert b"Receive another" in resp.content
