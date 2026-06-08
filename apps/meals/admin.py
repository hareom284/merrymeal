from django.contrib import admin

from apps.kitchens.models import MealIngredient
from apps.meals.models import Meal


class MealIngredientInline(admin.TabularInline):
    model = MealIngredient
    extra = 1
    autocomplete_fields = ("ingredient",)
    fields = ("ingredient", "quantity")
    verbose_name = "Ingredient"
    verbose_name_plural = "Ingredients"


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ("name", "prep_time_minutes", "cook_time_minutes", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    ordering = ("name",)
    inlines = [MealIngredientInline]
