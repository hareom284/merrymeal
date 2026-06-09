"""Form for the admin CRUD page."""
from __future__ import annotations

from django import forms

from apps.site_config.models import OrgSettings


class OrgSettingsForm(forms.ModelForm):
    class Meta:
        model = OrgSettings
        fields = [
            "name",
            "tagline",
            "address",
            "phone",
            "contact_email",
            "office_email",
            "logo",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "tagline": forms.TextInput(),
        }

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if not logo:
            return logo
        # 2 MB hard cap — a square PNG/SVG of the charity logo should
        # never approach this; the limit protects MEDIA_ROOT from a
        # mis-uploaded camera-phone JPEG.
        max_bytes = 2 * 1024 * 1024
        if hasattr(logo, "size") and logo.size > max_bytes:
            raise forms.ValidationError(
                f"Logo file is too large ({logo.size // 1024} KB). "
                f"Please upload a file under 2 MB."
            )
        return logo
