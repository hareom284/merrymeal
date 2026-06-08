import datetime as dt

from django.db import transaction

from apps.delivery.models import Delivery, Route
from apps.planning.services import assign_meal_type


def create_delivery(
    *,
    member,
    member_address,
    meal_plan,
    volunteer,
    scheduled_date: dt.date,
    route: Route | None = None,
) -> Delivery:
    """Create a `Delivery` with `meal_type` auto-resolved from member geography.

    `meal_type` is set via
    `planning.services.assign_meal_type(member, kitchen=meal_plan.kitchen,
    scheduled_date=scheduled_date)` — keeps the fresh/frozen rule in one
    place (Story 3.2).

    Raises:
        ValueError: if `member.role != "member"` or
            `member_address.user_id != member.id`.
    """
    if member.role != "member":
        raise ValueError(
            f"create_delivery: `member` must have role='member', got {member.role!r}"
        )
    if member_address.user_id != member.id:
        raise ValueError(
            "create_delivery: `member_address` does not belong to `member`."
        )

    meal_type = assign_meal_type(
        member=member,
        kitchen=meal_plan.kitchen,
        service_date=scheduled_date,
    )

    with transaction.atomic():
        return Delivery.objects.create(
            route=route,
            meal_plan=meal_plan,
            volunteer=volunteer,
            member=member,
            member_address=member_address,
            meal_type=meal_type,
            status=Delivery.STATUS_PENDING,
            scheduled_date=scheduled_date,
        )
