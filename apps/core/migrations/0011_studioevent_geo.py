from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_studioevent_visit_context"),
    ]

    operations = [
        migrations.AddField(
            model_name="studioevent",
            name="city",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="studioevent",
            name="country",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="studioevent",
            name="country_code",
            field=models.CharField(blank=True, db_index=True, max_length=2),
        ),
        migrations.AddField(
            model_name="studioevent",
            name="region",
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
