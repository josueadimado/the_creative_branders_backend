# Stores whether a budget was given in cedis or dollars.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_form_consent_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="inquirymessage",
            name="budget_currency",
            field=models.CharField(blank=True, max_length=3),
        ),
    ]
