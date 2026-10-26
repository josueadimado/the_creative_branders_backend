# Stores how each form visitor arrived: campaign tags, first page, and referrer.

from django.db import migrations, models

FIELDS = [
    ("utm_source", 120),
    ("utm_medium", 120),
    ("utm_campaign", 160),
    ("utm_content", 160),
    ("landing_page", 300),
    ("referrer", 300),
]
MODELS = ["inquirymessage", "waitlistsignup", "newslettersignup", "academyinterest"]


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_inquirymessage_budget_currency"),
    ]

    operations = [
        migrations.AddField(
            model_name=model,
            name=name,
            field=models.CharField(blank=True, max_length=length),
        )
        for model in MODELS
        for name, length in FIELDS
    ]
