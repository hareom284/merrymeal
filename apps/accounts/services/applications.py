from datetime import date

from apps.accounts.models import Application, User


def create_draft_application(
    *,
    full_name: str,
    email: str,
    dob,
    phone: str | None = None,
    applying_for_other: bool = False,
    caregiver_full_name: str | None = None,
    caregiver_email: str | None = None,
    caregiver_phone: str | None = None,
    relationship: str | None = None,
) -> Application:
    """Create the step-1 draft row.

    Rules:
    - The member's email must not collide with any existing `users.email`
      (case-insensitive). A second pending draft with the same email is
      allowed: the latest draft is what step 2/3 continue to fill out.
    """
    email_norm = email.strip().lower()
    if User.objects.filter(email__iexact=email_norm).exists():
        raise ValueError(f"A user with email {email_norm} already exists")

    caregiver_email_norm = (caregiver_email or "").strip().lower() or None
    caregiver_full_name_norm = (caregiver_full_name or "").strip() or None
    caregiver_phone_norm = (caregiver_phone or "").strip() or None

    return Application.objects.create(
        full_name=full_name.strip(),
        email=email_norm,
        dob=dob if isinstance(dob, date) else dob,
        phone=(phone or "").strip() or None,
        applying_for_other=bool(applying_for_other),
        caregiver_full_name=caregiver_full_name_norm,
        caregiver_email=caregiver_email_norm,
        caregiver_phone=caregiver_phone_norm,
        relationship=relationship or None,
        status=Application.STATUS_DRAFT,
    )


def update_application_address(
    *,
    application: Application,
    label: str,
    street: str,
    postal_code: str,
    city,
) -> Application:
    """Step 2 — write the address fields onto the existing draft row.

    Raises:
        ValueError: if the application is not in `draft` state.
    """
    if application.status != Application.STATUS_DRAFT:
        raise ValueError(
            f"Application {application.id} is not in draft state "
            f"(status={application.status})"
        )
    application.address_label = (label or "Home").strip()
    application.street = street.strip()
    application.postal_code = postal_code.strip()
    application.city_id = city.id
    application.save(update_fields=[
        "address_label", "street", "postal_code", "city_id", "updated_at",
    ])
    return application


def submit_application(
    *,
    application_id: int,
    dietary_ids: list,
    allergy_ids: list,
) -> Application:
    """Step 3 — transitions a draft to submitted, writes the selected
    dietary/allergy ids, and dispatches the confirmation email.
    """

    from apps.dietary.models import Allergy, DietPreference

    try:
        application = Application.objects.get(id=application_id)
    except Application.DoesNotExist as exc:
        raise ValueError(f"Application {application_id} not found") from exc

    if application.status != Application.STATUS_DRAFT:
        raise ValueError(
            f"Application {application.id} is not in draft state "
            f"(status={application.status})"
        )

    diet_ids = [int(x) for x in (dietary_ids or [])]
    allergy_id_list = [int(x) for x in (allergy_ids or [])]

    known_diet = set(
        DietPreference.objects.filter(id__in=diet_ids).values_list("id", flat=True)
    )
    unknown_diet = [x for x in diet_ids if x not in known_diet]
    if unknown_diet:
        raise ValueError(f"Unknown diet preference ids: {unknown_diet}")

    known_allergy = set(
        Allergy.objects.filter(id__in=allergy_id_list).values_list("id", flat=True)
    )
    unknown_allergy = [x for x in allergy_id_list if x not in known_allergy]
    if unknown_allergy:
        raise ValueError(f"Unknown allergy ids: {unknown_allergy}")

    application.dietary_ids = diet_ids
    application.allergy_ids = allergy_id_list
    application.status = Application.STATUS_SUBMITTED
    application.save(update_fields=[
        "dietary_ids", "allergy_ids", "status", "updated_at",
    ])

    _send_confirmation_email(application)
    return application


def _send_confirmation_email(application: Application) -> None:
    from django.core.mail import EmailMultiAlternatives
    from django.utils import timezone

    from apps.site_config.email_context import render_email as render_to_string

    ctx = {
        "application": application,
        "applicant_first_name": application.full_name.split()[0],
        "sent_at": timezone.now(),
    }
    subject = "We've got your MerryMeal application"
    text_body = render_to_string("accounts/emails/application_received.txt", ctx)
    html_body = render_to_string("accounts/emails/application_received.html", ctx)

    cc = []
    if application.applying_for_other and application.caregiver_email:
        cc.append(application.caregiver_email)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        to=[application.email],
        cc=cc or None,
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()


def approve_application(application: Application, admin_user) -> User:
    """Approve a submitted application and explode it into real rows.

    All writes are atomic. The welcome email is dispatched on commit so a
    rollback (any exception in the block) silently drops the message.
    """
    from auditlog.context import set_actor
    from django.db import transaction
    from django.utils import timezone

    from apps.accounts.services.tokens import issue_password_setup_token

    if application.status != Application.STATUS_SUBMITTED:
        raise ValueError(
            f"Application {application.id} is not submitted (status={application.status})"
        )

    with set_actor(admin_user), transaction.atomic():
        member = _create_member_user(application)
        caregiver, caregiver_was_existing = _create_or_reuse_caregiver(application)
        _create_member_address(member, application)
        _attach_diet_and_allergies(member, application)
        if caregiver is not None:
            _link_caregiver(member, caregiver, application.relationship)

        application.status = Application.STATUS_APPROVED
        application.approved_by = admin_user.id
        application.approved_at = timezone.now()
        application.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

        token = issue_password_setup_token(member)

        transaction.on_commit(
            lambda: _send_welcome_email(
                member=member,
                application=application,
                token=token,
                caregiver=caregiver,
                caregiver_was_existing=caregiver_was_existing,
            )
        )

    return member


def _create_member_user(application: Application) -> User:
    import secrets

    from apps.accounts.services.users import create_user

    user = create_user(
        email=application.email,
        password=secrets.token_urlsafe(32),
        full_name=application.full_name,
        role="member",
        is_active=False,
        dob=application.dob,
    )
    # Story 6.7 — propagate the referring charity onto the new member so
    # Story 6.2 retention counts attribute the member to the partner.
    if application.partner_id is not None:
        user.partner_id = application.partner_id
        user.set_unusable_password()
        user.save(update_fields=["password", "partner"])
    else:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


def _create_or_reuse_caregiver(application: Application):
    import secrets

    from apps.accounts.services.users import create_user

    if not application.applying_for_other:
        return None, False

    email_norm = (application.caregiver_email or "").strip().lower()
    if not email_norm:
        return None, False

    existing = User.objects.filter(email__iexact=email_norm).first()
    if existing is not None:
        return existing, True

    caregiver = create_user(
        email=email_norm,
        password=secrets.token_urlsafe(32),
        full_name=application.caregiver_full_name or email_norm,
        role="caregiver",
        is_active=False,
    )
    caregiver.set_unusable_password()
    caregiver.save(update_fields=["password"])
    return caregiver, False


def _create_member_address(member: User, application: Application):
    from apps.accounts.models import Address

    if not application.city_id:
        raise ValueError("Application has no city_id; address cannot be created")

    return Address.objects.create(
        user=member,
        label=application.address_label or "Home",
        postal_code=application.postal_code or "",
        city_id=application.city_id,
    )


def _attach_diet_and_allergies(member: User, application: Application) -> None:
    from apps.dietary.models import UserAllergy, UserDietPreference

    diet_ids = application.dietary_ids or []
    if diet_ids:
        UserDietPreference.objects.bulk_create(
            [
                UserDietPreference(user=member, diet_preference_id=pid)
                for pid in diet_ids
            ],
            ignore_conflicts=True,
        )

    allergy_ids = application.allergy_ids or []
    if allergy_ids:
        UserAllergy.objects.bulk_create(
            [UserAllergy(user=member, allergy_id=aid) for aid in allergy_ids],
            ignore_conflicts=True,
        )


def _link_caregiver(member: User, caregiver: User, relationship: str | None) -> None:
    from apps.accounts.models import CaregiverLink

    CaregiverLink.objects.get_or_create(
        member=member,
        caregiver=caregiver,
        defaults={"relationship": relationship or "other"},
    )


def _send_welcome_email(
    *,
    member: User,
    application: Application,
    token: str,
    caregiver,
    caregiver_was_existing: bool,
) -> None:
    from django.conf import settings
    from django.core.mail import EmailMultiAlternatives

    from apps.site_config.email_context import render_email as render_to_string

    base = getattr(settings, "SITE_URL", "http://localhost:8000").rstrip("/")
    setup_url = f"{base}/accounts/set-password/?token={token}"

    ctx = {
        "member": member,
        "first_name": member.full_name.split()[0],
        "setup_url": setup_url,
        "caregiver": caregiver,
        "caregiver_was_existing": caregiver_was_existing,
    }

    subject = "Welcome to MerryMeal — set your password"
    text_body = render_to_string("accounts/emails/welcome_set_password.txt", ctx)
    html_body = render_to_string("accounts/emails/welcome_set_password.html", ctx)

    cc = []
    if caregiver is not None and caregiver.email != member.email:
        cc.append(caregiver.email)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        to=[member.email],
        cc=cc or None,
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)


def create_partner_referral(
    *,
    partner,
    partner_contact_name: str,
    partner_contact_email: str,
    member_full_name: str,
    member_email: str,
    member_dob,
    member_phone: str | None = None,
) -> Application:
    """Story 6.7 — persist a partner-submitted referral as a SUBMITTED
    application.

    Unlike :func:`create_draft_application`, this skips the multi-step
    wizard: the social worker fills a single public form and the row
    lands ready for an admin to triage. The referring partner is stored
    on the FK so an approval can copy it onto the resulting User.

    The social worker's name and email are stored on
    ``Application.metadata`` rather than as dedicated columns to avoid
    schema churn — Story 7.x admin search can promote them later if
    needed.
    """

    member_email_norm = (member_email or "").strip().lower()
    if member_email_norm and User.objects.filter(
        email__iexact=member_email_norm
    ).exists():
        raise ValueError(
            f"A user with email {member_email_norm} already exists"
        )

    return Application.objects.create(
        full_name=member_full_name.strip(),
        email=member_email_norm,
        dob=member_dob,
        phone=(member_phone or "").strip() or None,
        status=Application.STATUS_SUBMITTED,
        partner=partner,
        metadata={
            "partner_contact_name": partner_contact_name.strip(),
            "partner_contact_email": (
                partner_contact_email or ""
            ).strip().lower(),
        },
    )


def reject_application(application: Application, admin_user, *, reason: str) -> Application:
    from auditlog.context import set_actor
    from django.db import transaction
    from django.utils import timezone

    reason_clean = (reason or "").strip()
    if not reason_clean:
        raise ValueError("Rejection reason is required")

    with set_actor(admin_user), transaction.atomic():
        application.status = Application.STATUS_REJECTED
        application.rejected_reason = reason_clean
        application.approved_by = admin_user.id
        application.approved_at = timezone.now()
        application.save(
            update_fields=[
                "status",
                "rejected_reason",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )

        transaction.on_commit(
            lambda: _send_rejection_email(application=application, reason=reason_clean)
        )

    return application


def _send_rejection_email(*, application: Application, reason: str) -> None:
    from django.core.mail import EmailMultiAlternatives

    from apps.site_config.email_context import render_email as render_to_string

    ctx = {
        "application": application,
        "first_name": application.full_name.split()[0],
        "reason": reason,
    }
    subject = "Update on your MerryMeal application"
    text_body = render_to_string("accounts/emails/application_rejected.txt", ctx)
    html_body = render_to_string("accounts/emails/application_rejected.html", ctx)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        to=[application.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)
