"""Singleton ``OrgSettings`` row that the admin can edit from the UI.

One row per deployment — name, address, phone, contact email, logo.
The singleton pattern lives in the manager (``current()`` returns the
row, creating it from defaults on first call) so callers never have
to worry about which PK to use.

These fields are intentionally NOT stored as Django settings: settings
are static, set once at boot from ``.env``, and changing them requires
a deploy. The whole point of this model is that a non-technical admin
can change the office phone or charity address from a CRUD page
without touching code.
"""
from __future__ import annotations

from django.db import models


class OrgSettingsManager(models.Manager):
    """Returns the singleton row, seeding it from sensible defaults
    on first access. Cheap to call — one ``get_or_create`` query."""

    def current(self) -> OrgSettings:
        obj, _ = self.get_or_create(pk=1, defaults={
            "name": "MerryMeal",
            "tagline": "Warm meals delivered with a friendly smile.",
            "address": "No. 12, 35th Street, Kyauktada Township,\nYangon 11182, Myanmar",
            "phone": "+95 9 123 456 789",
            "contact_email": "hello@merrymeal.org",
            "office_email": "office@merrymeal.org",
        })
        return obj


class OrgSettings(models.Model):
    """Charity-level configuration editable at runtime.

    Schema convention: every field has a sensible non-empty default
    so templates that read ``{{ org.phone }}`` never render blank
    even before an admin has touched the page.
    """

    name = models.CharField(max_length=120, default="MerryMeal")
    tagline = models.CharField(
        max_length=240,
        blank=True,
        help_text="One-line strapline used in marketing and email footers.",
    )
    address = models.TextField(
        blank=True,
        help_text="Postal address — multi-line OK.",
    )
    phone = models.CharField(
        max_length=40,
        blank=True,
        help_text="Office phone in international format.",
    )
    contact_email = models.EmailField(
        blank=True,
        help_text="Public contact address for members and donors.",
    )
    office_email = models.EmailField(
        blank=True,
        help_text="Internal address for failure alerts and admin reports.",
    )
    logo = models.ImageField(
        upload_to="org/",
        blank=True,
        null=True,
        help_text=(
            "Square PNG/SVG, 512×512 recommended. Falls back to the "
            "bundled static/img/logo.png when not set."
        ),
    )
    updated_at = models.DateTimeField(auto_now=True)

    objects = OrgSettingsManager()

    class Meta:
        verbose_name = "Organisation settings"
        verbose_name_plural = "Organisation settings"

    def __str__(self) -> str:
        return self.name or "Organisation settings"

    @property
    def logo_url(self) -> str:
        """Uploaded logo URL if set, else the static fallback. Templates
        should just use ``{{ org.logo_url }}`` and not branch on
        whether a custom upload exists."""
        if self.logo and hasattr(self.logo, "url"):
            return self.logo.url
        from django.templatetags.static import static
        return static("img/logo.png")
