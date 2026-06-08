from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.accounts.managers import UserManager
from apps.core.managers import AllObjectsManager


class User(AbstractBaseUser, PermissionsMixin):
    """Schema only — fields, choices, Meta. No business logic, no managers
    defined inline. See:
      - apps.accounts.managers for the UserManager
      - apps.accounts.services  for create_user, delete_user, sign_in, ...
    """

    ROLE_CHOICES = [
        ("member", "Member"),
        ("volunteer", "Volunteer"),
        ("caregiver", "Caregiver"),
        ("donor", "Donor"),
        ("kitchen_staff", "Kitchen staff"),
        ("admin", "Admin"),
    ]

    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    dob = models.DateField(null=True, blank=True)
    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="partner_id",
        related_name="users",
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()
    all_objects = AllObjectsManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "role"]

    class Meta:
        app_label = "accounts"
        db_table = "users"

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"
