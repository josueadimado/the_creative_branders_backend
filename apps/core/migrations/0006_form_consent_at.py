# Stores the time a visitor agreed we may use their form details.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_inquirymessage_reviewed"),
    ]

    operations = [
        migrations.AddField(
            model_name="inquirymessage",
            name="consent_at",
            field=models.DateTimeField(
                blank=True,
                help_text="When the visitor agreed we may use these details to reply.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="waitlistsignup",
            name="consent_at",
            field=models.DateTimeField(
                blank=True,
                help_text="When the visitor agreed we may use these details to reply.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="newslettersignup",
            name="consent_at",
            field=models.DateTimeField(
                blank=True,
                help_text="When the visitor agreed we may use these details to reply.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="academyinterest",
            name="consent_at",
            field=models.DateTimeField(
                blank=True,
                help_text="When the visitor agreed we may use these details to reply.",
                null=True,
            ),
        ),
    ]
