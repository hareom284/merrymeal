from django import forms

from apps.dietary.models import Allergy, DietPreference


class MemberDietaryForm(forms.Form):
    diet_preferences = forms.ModelMultipleChoiceField(
        queryset=DietPreference.objects.all().order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Diet preferences",
    )
    allergies = forms.ModelMultipleChoiceField(
        queryset=Allergy.objects.all().order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Allergies",
    )

    @classmethod
    def for_user(cls, user, data=None):
        if data is not None:
            return cls(data)
        return cls(
            initial={
                "diet_preferences": list(
                    user.diet_preferences.values_list("pk", flat=True)
                ),
                "allergies": list(user.allergies.values_list("pk", flat=True)),
            }
        )
