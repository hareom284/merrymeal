from apps.accounts.models import CaregiverLink, User


def link_caregiver(
    *, member: User, caregiver: User, relationship: str
) -> CaregiverLink:
    """Create a CaregiverLink after validating both sides have the right role.

    Raises:
        ValueError: if `member.role` != 'member' or
                    `caregiver.role` != 'caregiver'.
    """
    if member.role != "member":
        raise ValueError(
            f"`member` must have role='member', got role='{member.role}'."
        )
    if caregiver.role != "caregiver":
        raise ValueError(
            f"`caregiver` must have role='caregiver', got role='{caregiver.role}'."
        )
    return CaregiverLink.objects.create(
        member=member, caregiver=caregiver, relationship=relationship
    )
