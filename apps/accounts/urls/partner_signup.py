"""URL patterns for the public partner-org signup form.

Mounted in ``config.urls`` under the ``apply-partner/`` prefix so the
public URLs are ``/apply-partner/`` (form) and
``/apply-partner/thanks/`` (thank-you page).
"""

from django.urls import path

from apps.accounts.views.partner_signup import (
    partner_signup_form,
    partner_signup_thanks,
)

urlpatterns = [
    path("", partner_signup_form, name="partner_signup_form"),
    path("thanks/", partner_signup_thanks, name="partner_signup_thanks"),
]
