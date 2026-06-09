"""Read-only profile context builder (Story 12.4).

Pulls every datum the My profile page renders, so the view stays a
single ``form.cleaned_data → service(...) → render`` line. Returns a
plain dict (no dataclass) for the same reason the dashboard does:
templates iterate keys, not attributes.
"""
from apps.accounts.models.caregiver_links import CaregiverLink


def build_member_profile_context(user) -> dict:
    """Return everything the profile template needs for ``user``.

    Missing data (no address, no allergies, etc.) returns ``None`` /
    empty list — the template gates each block on truthiness so the
    page degrades gracefully for sparse accounts.
    """
    address = user.addresses.select_related("city").first()
    diet_prefs = list(user.diet_preferences.order_by("name"))
    allergies = list(user.allergies.order_by("name"))

    caregiver_link = (
        CaregiverLink.objects.select_related("caregiver")
        .filter(member=user)
        .order_by("id")
        .first()
    )

    return {
        "member": user,
        "address": address,
        "diet_preferences": diet_prefs,
        "allergies": allergies,
        "caregiver_link": caregiver_link,
    }
