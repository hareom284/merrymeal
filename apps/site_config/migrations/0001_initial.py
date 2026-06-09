from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="OrgSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(default="MerryMeal", max_length=120)),
                (
                    "tagline",
                    models.CharField(
                        blank=True,
                        help_text="One-line strapline used in marketing and email footers.",
                        max_length=240,
                    ),
                ),
                (
                    "address",
                    models.TextField(
                        blank=True, help_text="Postal address — multi-line OK."
                    ),
                ),
                (
                    "phone",
                    models.CharField(
                        blank=True,
                        help_text="Office phone in international format.",
                        max_length=40,
                    ),
                ),
                (
                    "contact_email",
                    models.EmailField(
                        blank=True,
                        help_text="Public contact address for members and donors.",
                        max_length=254,
                    ),
                ),
                (
                    "office_email",
                    models.EmailField(
                        blank=True,
                        help_text="Internal address for failure alerts and admin reports.",
                        max_length=254,
                    ),
                ),
                (
                    "logo",
                    models.ImageField(
                        blank=True,
                        help_text=(
                            "Square PNG/SVG, 512×512 recommended. Falls back to the "
                            "bundled static/img/logo.png when not set."
                        ),
                        null=True,
                        upload_to="org/",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Organisation settings",
                "verbose_name_plural": "Organisation settings",
            },
        ),
    ]
