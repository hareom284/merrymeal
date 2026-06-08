# Generated for story 3.5 — Ingredient → Allergy mapping.
#
# Join table `ingredient_allergy` is singular both sides for consistency with
# `allergy_user` and `diet_preference_user`. The dietitian seeds obvious
# mappings via `seed_dietary` (substring match) and curates the rest via admin.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dietary", "0001_initial"),
        ("kitchens", "0006_schedule_expiry_alerts"),
    ]

    operations = [
        migrations.CreateModel(
            name="IngredientAllergy",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "allergy",
                    models.ForeignKey(
                        db_column="allergy_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="dietary.allergy",
                    ),
                ),
                (
                    "ingredient",
                    models.ForeignKey(
                        db_column="ingredient_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="kitchens.ingredient",
                    ),
                ),
            ],
            options={
                "db_table": "ingredient_allergy",
            },
        ),
        migrations.AddField(
            model_name="ingredient",
            name="contains_allergens",
            field=models.ManyToManyField(
                blank=True,
                related_name="ingredients",
                through="kitchens.IngredientAllergy",
                to="dietary.allergy",
            ),
        ),
        migrations.AddConstraint(
            model_name="ingredientallergy",
            constraint=models.UniqueConstraint(
                fields=("ingredient", "allergy"),
                name="uq_ingredient_allergy",
            ),
        ),
    ]
