from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_inquiry_brief_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="NewsletterSignup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Newsletter signup",
                "verbose_name_plural": "Newsletter signups",
                "ordering": ["-created_at"],
            },
        ),
    ]
