from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.dietary.models import UserAllergy, UserDietPreference

from .models import Address, CaregiverLink, City, User


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0
    fields = ("label", "postal_code", "city", "latitude", "longitude")
    autocomplete_fields = ("city",)


class CaregiverLinkAsMemberInline(admin.TabularInline):
    """Shows caregivers attached to this user (when this user is the member)."""

    model = CaregiverLink
    fk_name = "member"
    extra = 0
    verbose_name = "Caregiver attached (this user is the member)"
    verbose_name_plural = "Caregivers attached (this user is the member)"
    autocomplete_fields = ("caregiver",)


class CaregiverLinkAsCaregiverInline(admin.TabularInline):
    """Shows members this user is a caregiver for."""

    model = CaregiverLink
    fk_name = "caregiver"
    extra = 0
    verbose_name = "Member I care for (this user is the caregiver)"
    verbose_name_plural = "Members I care for (this user is the caregiver)"
    autocomplete_fields = ("member",)


class UserDietPreferenceInline(admin.TabularInline):
    model = UserDietPreference
    extra = 0
    autocomplete_fields = ("diet_preference",)


class UserAllergyInline(admin.TabularInline):
    model = UserAllergy
    extra = 0
    autocomplete_fields = ("allergy",)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("email", "full_name", "role", "is_active", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("email", "full_name")
    ordering = ("email",)
    inlines = [
        AddressInline,
        CaregiverLinkAsMemberInline,
        CaregiverLinkAsCaregiverInline,
        UserDietPreferenceInline,
        UserAllergyInline,
    ]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("full_name", "dob", "role")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "role", "password1", "password2"),
            },
        ),
    )


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")
    search_fields = ("name",)
    ordering = ("name",)
