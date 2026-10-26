from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_newslettersignup"),
    ]

    operations = [
        migrations.AddField(
            model_name="inquirymessage",
            name="reviewed",
            field=models.BooleanField(default=False),
        ),
    ]
