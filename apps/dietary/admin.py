from django.contrib import admin

from .models import Allergy, DietPreference


@admin.register(DietPreference)
class DietPreferenceAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Allergy)
class AllergyAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)
