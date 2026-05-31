from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """Data-layer manager for the User model.

    The two `create_*` methods exist because Django's `createsuperuser`
    management command and the AbstractBaseUser contract require them on
    `User._default_manager`. App code should **not** call them directly —
    use `apps.accounts.services.create_user` instead.
    """

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def create_user(self, email, password, full_name, role, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, role=role, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, full_name="Admin", role="admin", **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, full_name, role, **extra)
