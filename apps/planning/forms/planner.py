"""Form used by the admin weekly-planner HTMX modal."""

from __future__ import annotations

from django import forms

from apps.meals.models import Meal


class MealPlanCellForm(forms.Form):
    """One active meal + a planned quantity for a single planner cell."""

    meal = forms.ModelChoiceField(
        queryset=Meal.objects.filter(is_active=True).order_by("name"),
        empty_label="Choose a meal…",
    )
    planned_quantity = forms.IntegerField(min_value=0, initial=20)
