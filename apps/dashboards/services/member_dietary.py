"""Replace a member's `diet_preferences` and `allergies` M2Ms.

Owns the multi-table write the view triggers when a member edits their
dietary profile. Wraps both M2M diffs in one ``transaction.atomic()``
so the user never lands in a half-updated state. Computes a minimal
add/remove diff instead of delete-all-then-insert so audit history
stays meaningful (existing through-rows that should remain are
preserved).
"""
from __future__ import annotations

from collections.abc import Iterable

from django.db import transaction

from apps.dietary.models import UserAllergy, UserDietPreference


def update_member_dietary(
    *,
    user,
    diet_preference_ids: Iterable[int],
    allergy_ids: Iterable[int],
) -> None:
    diet_target = {int(i) for i in diet_preference_ids}
    allergy_target = {int(i) for i in allergy_ids}

    with transaction.atomic():
        _sync_links(
            through=UserDietPreference,
            user=user,
            fk_attr="diet_preference_id",
            target_ids=diet_target,
        )
        _sync_links(
            through=UserAllergy,
            user=user,
            fk_attr="allergy_id",
            target_ids=allergy_target,
        )


def _sync_links(*, through, user, fk_attr: str, target_ids: set[int]) -> None:
    current = set(
        through.objects.filter(user=user).values_list(fk_attr, flat=True)
    )
    to_add = target_ids - current
    to_remove = current - target_ids

    if to_remove:
        through.objects.filter(user=user, **{f"{fk_attr}__in": to_remove}).delete()
    if to_add:
        through.objects.bulk_create(
            [through(user=user, **{fk_attr: pid}) for pid in to_add],
            ignore_conflicts=True,
        )
