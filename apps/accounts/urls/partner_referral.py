"""Story 6.7 — URL patterns for the public partner referral form.

Mounted in ``config.urls`` under the ``partners/`` prefix so the
public URL is ``/partners/refer/``.
"""

from django.urls import path

from apps.accounts.views.partner_referral import (
    partner_referral_form,
    partner_referral_thanks,
)

urlpatterns = [
    path("refer/", partner_referral_form, name="partner_referral_form"),
    path(
        "refer/thanks/",
        partner_referral_thanks,
        name="partner_referral_thanks",
    ),
]
